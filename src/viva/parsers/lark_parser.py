# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

"""
Lark-based implementation of the Viva Parser interface.

The default grammar lives in src/viva/grammars/viva.lark and is loaded
automatically. You can pass a custom grammar string to the constructor
if needed.

This module is the *only* place in the Viva codebase that should import
from the 'lark' package. All other code should go through the abstract
Parser interface defined in base.py.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lark import Lark, Transformer, v_args
from lark.exceptions import VisitError

from .base import ParseTree, Parser
from ..nodes import EventDecl, FlowDecl, LifeDecl, Program


SCALE_FACTORS = [
    ("thousand", "k", 1e3),
    ("million", "m", 1e6),
    ("billion", "b", 1e9),
    ("trillion", "t", 1e12),
]


def _validate_amount_format(s: str) -> None:
    """Raise if thousand separators (, or _) are used incorrectly.

    Rules:
    - Only one type of separator may be used in a number (no mixing "," and "_").
    - When separators are present:
      - The first group (before the first separator) must have 1-3 digits.
      - Every subsequent group must have exactly 3 digits.
    """
    orig = str(s).strip()
    check = orig.lower().lstrip("+-")
    # strip optional k/m suffix for the check
    if check.endswith(("k", "m")):
        check = check[:-1].rstrip()
    # integer part only
    int_part = check.split(".")[0]
    if not any(sep in int_part for sep in ",_"):
        return

    # Reject mixing different separator types (e.g. "1,000_000")
    used_seps = {c for c in int_part if c in ",_"}
    if len(used_seps) > 1:
        raise ValueError(
            f"bad number literal {orig!r}: cannot mix different thousand separators "
            "(use only ',' or only '_', e.g. 1,000,000 or 1_000_000, not 1,000_000)"
        )

    groups = re.split(r"[,_]", int_part)
    if len(groups[0]) < 1 or len(groups[0]) > 3 or not groups[0].isdigit():
        raise ValueError(
            f"bad number literal {orig!r}: first digit group must be 1-3 digits when using separators"
        )
    for g in groups[1:]:
        if len(g) != 3 or not g.isdigit():
            raise ValueError(
                f"bad number literal {orig!r}: separators must be followed by exactly 3 digits "
                "(e.g. 1,000,000 or 1_234_567, not 1,00,000 or 1,2345)"
            )


def _convert_str2amount(value: float | int | str, unit: str | None = None) -> float:
    """Elegantly parse human-friendly amount strings into a float.

    Understands:
        plain numbers with , _ separators
        "3m", "3 million", "3M", "3 Million" → 3_000_000
        "4.2k", "4.2 thousand" → 4200
        "2b", "2 billion" → 2_000_000_000
        "1t", "1 trillion" → 1_000_000_000_000
        etc.

    - Strips thousand separators (both "," and "_").
    - Supports k/m/b/t and full words thousand/million/billion/trillion (case-insensitive),
      either attached or as separate UNIT token.
    - Used for flow amounts and "until ... total" caps.
    """
    if isinstance(value, (int, float)):
        val = float(value)
    else:
        orig = str(value).strip()
        _validate_amount_format(orig)
        s = orig
        # Detect and strip unit suffix (k/m/b/t or full words) if not provided separately
        if unit is None:
            s_lower = s.lower()
            for word, short, _ in SCALE_FACTORS:
                if s_lower.endswith(word):
                    unit = short
                    s = s[: -len(word)].rstrip()
                    break
            else:
                if s_lower.endswith(("k", "m", "b", "t")):
                    unit = s_lower[-1]
                    s = s[:-1].rstrip()
                else:
                    unit = None
        # Remove thousand separators
        s = s.replace(",", "").replace("_", "")
        val = float(s) if s else 0.0

    if unit:
        u = str(unit).lower().strip()
        for word, short, factor in SCALE_FACTORS:
            if u == word or u == short:
                val *= factor
                break
    return val


class LarkParser(Parser):
    """
    Concrete implementation of Parser that uses the Lark parsing library.

    By default it loads the grammar from `src/viva/grammars/viva.lark`.
    A custom grammar string can be passed to the constructor.
    """

    def __init__(self, grammar: str | None = None):
        if grammar is None:
            grammar_path = Path(__file__).parent.parent / "grammars" / "viva.lark"
            grammar = grammar_path.read_text(encoding="utf-8")

        self._lark = Lark(
            grammar,
            start="program",
            parser="earley",
            propagate_positions=True,
        )
        self._transformer = _VivaTransformer()

    def parse(self, source: str) -> Program:
        """Parse Viva source using Lark and return the Program AST."""
        tree = self._lark.parse(source)
        try:
            prog = self._transformer.transform(tree)
        except VisitError as e:
            if isinstance(getattr(e, "orig_exc", None), ValueError):
                msg = str(e.orig_exc)
                if (
                    "bad number literal" in msg
                    or "amount format" in msg
                    or "separators" in msg
                ):
                    raise ValueError(msg) from None
            raise
        except ValueError as e:
            # Turn amount format errors (and similar) into clear messages
            # without the full Lark traceback.
            msg = str(e)
            if (
                "bad number literal" in msg
                or "amount format" in msg
                or "separators" in msg
            ):
                raise ValueError(msg) from None
            raise
        # Enforce that recurring durations require explicit period (per year/month)
        for f in prog.flows:
            has_recurring_duration = any(
                m.get("kind") in ("for", "after_years", "starting_at_age")
                or (m.get("kind") == "until" and not m.get("is_total"))
                for m in f.modifiers
            )
            if has_recurring_duration and f.period is None:
                raise ValueError(
                    f"Syntax error in flow '{f.name}': flows with duration ('for', 'after', 'starting at age', or 'until' event) "
                    "must specify a period ('per year' or 'per month'). One-time payments should not use 'for'."
                )
        # Semantic validation (undeclared lives/events, etc.)
        try:
            # Import inside to avoid circular import issues at module load
            from ..interpreter import _validate_program

            _validate_program(prog)
        except Exception:
            # If validation fails or import issue, re-raise the original semantic error
            # (the function itself raises ValueError for undeclared refs)
            raise
        return prog

    def get_parse_tree(self, source: str) -> ParseTree:
        """
        Return the raw Lark Tree (syntactic / concrete parse tree).

        Useful for debugging and for displaying syntactic trees
        (call .pretty() on the result).
        """
        return self._lark.parse(source)


@v_args(inline=True)
class _VivaTransformer(Transformer):
    """
    Internal transformer that converts a raw Lark Tree into our
    backend-independent Program AST.
    """

    def program(self, *decls: Any) -> Program:
        prog = Program()
        for d in decls:
            if isinstance(d, LifeDecl):
                prog.lives.append(d)
            elif isinstance(d, EventDecl):
                prog.events.append(d)
            elif isinstance(d, FlowDecl):
                prog.flows.append(d)
        return prog

    def life_decl(self, name, typ, yr, mort=None) -> LifeDecl:
        if mort:
            mortality_table = str(mort)
        else:
            g = str(typ).lower()
            if g in ("woman", "female"):
                mortality_table = "SSA_2023_female"
            else:
                mortality_table = "SSA_2023_male"
        return LifeDecl(
            name=str(name),
            typ=str(typ),
            birth_year=int(yr),
            mortality_table=mortality_table,
        )

    def life_type(self, tok):
        return str(tok)

    def mortality(self, name):
        return str(name)

    def year(self, tok):
        return int(tok)

    def event_decl(self, name, *details) -> EventDecl:
        ev = EventDecl(name=str(name))
        for det in details:
            if det.get("_type") == "time":
                ev.time_window = det
            elif det.get("_type") == "prob":
                ev.probability = det
        # If no probability at all, treat as certain (100%)
        if ev.probability is None:
            ev.probability = {"kind": "certain", "pct": 100.0}
        return ev

    def event_detail(self, item):
        return item

    def time_window(self, item):
        return {"_type": "time", **item}

    def relative_future(self, n):
        return {"kind": "relative_future", "years": int(n)}

    def absolute_year(self, yr):
        return {"kind": "absolute_year", "year": int(yr)}

    def person_age(self, *parts):
        # NAME APOS_S "age" NUMBER
        name = str(parts[0])
        num = parts[-1]
        return {"kind": "at_age", "target": name, "age": float(num)}

    def at_age(self, *parts):
        for p in parts:
            if isinstance(p, dict):
                return {"kind": "at_age", **p}
        # bare "at age N"
        n = parts[-1]
        return {"kind": "at_age", "age": float(n)}

    def after_target(self, *parts):
        if len(parts) == 1:
            return {"event": str(parts[0])}
        # NAME . DEATH/BIRTH or NAME APOS_S DEATH/BIRTH (2 or 3 parts)
        name = str(parts[0])
        if len(parts) == 2:
            suffix = str(parts[1]).lower()
        else:
            suffix = str(parts[2]).lower()
        if suffix == "birth":
            return {"target": name, "attr": "birth"}
        else:
            return {"target": name, "attr": "death"}

    def in_after(self, n, tgt):
        return self._build_after(n, tgt)

    def bare_after(self, n, tgt):
        return self._build_after(n, tgt)

    def _build_after(self, n, tgt):
        d = {"kind": "after_event", "years": int(n)}
        if isinstance(tgt, dict):
            if tgt.get("attr") in ("death", "birth"):
                d.update(tgt)
            else:
                d["event"] = tgt.get("event")
        else:
            d["event"] = str(tgt)
        return d

    def starting_at_age(self, *parts):
        for p in parts:
            if isinstance(p, dict):
                d = dict(p)
                d["kind"] = "starting_at_age"
                return d
        # bare "starting at age N"
        n = parts[-1]
        return {"kind": "starting_at_age", "age": float(n)}

    def probability(self, *parts):
        # With literals elided, we mostly get the NUMBER token(s) and occasional "per"/"year"
        nums = [
            float(p)
            for p in parts
            if isinstance(p, (int, float))
            or (isinstance(p, str) and p.replace(".", "").isdigit())
        ]
        pct = nums[0] if nums else 100.0
        has_per_year = any(str(p).lower() in ("per", "year") for p in parts)
        if has_per_year:
            kind = "per_year"
        else:
            kind = "simple"
        return {"_type": "prob", "kind": kind, "pct": pct}

    def flow_decl(self, name, famount, *mods) -> FlowDecl:
        amt, per = famount
        modifiers = []
        for m in mods:
            if isinstance(m, list):
                modifiers.extend(m)
            else:
                modifiers.append(m)
        return FlowDecl(name=str(name), amount=amt, period=per, modifiers=modifiers)

    def flow_amount(self, snum, *rest):
        unit = None
        per = None
        if rest:
            first = str(rest[0]).lower()
            for word, short, _ in SCALE_FACTORS:
                if first == word or first == short:
                    unit = first
                    if len(rest) > 1:
                        per = rest[1]
                    break
            else:
                per = rest[0]
        val = _convert_str2amount(snum, unit)
        period = str(per) if per else None
        return val, period

    def per_month(self, *parts):
        return "month"

    def per_year(self, *parts):
        return "year"

    def frequency(self, *parts):
        if len(parts) == 0:
            return None
        if len(parts) == 1:
            f = str(parts[0]).lower()
        else:
            f = str(parts[1]).lower()
        if f in ("monthly", "month"):
            return "month"
        if f in ("annually", "year"):
            return "year"
        return f

    def flow_modifier(self, mod):
        return mod

    def upon_mod(self, target):
        return {"kind": "upon", **target}

    def upon_target(self, *parts):
        if len(parts) == 1:
            return {"target": str(parts[0])}
        # NAME . DEATH/BIRTH or NAME APOS_S DEATH/BIRTH
        name = str(parts[0])
        if len(parts) == 2:
            suffix = str(parts[1]).lower()
        else:
            suffix = str(parts[2]).lower()
        return {"target": name, "attr": suffix}

    def until_mod(self, target):
        return {"kind": "until", **target}

    def until_target(self, *parts):
        if len(parts) == 1:
            p = parts[0]
            if isinstance(p, dict):
                # forwarded from subrule like total_target
                return p
            if isinstance(p, int):
                return {"target": p, "is_year": True}
            return {"target": str(p)}
        # death/birth case (NAME . DEATH/BIRTH or NAME APOS_S DEATH/BIRTH)
        if len(parts) in (2, 3):
            last = parts[-1]
            suffix = (
                last.lower()
                if isinstance(last, str)
                else getattr(last, "type", "").lower()
            )
            if suffix in ("death", "birth"):
                return {"target": str(parts[0]), "attr": suffix}
        # fallback: if first child is already processed dict, use it
        p = parts[0]
        if isinstance(p, dict):
            return p
        return {"target": str(p)}

    def total_target(self, num, *rest):
        """Handle 'NUMBER total' and 'NUMBER UNIT total' cases.

        Supports bare large numbers like 1000000 as well as 1m total etc.
        """
        unit = None
        for p in rest:
            if isinstance(p, str):
                pl = p.lower()
                for word, short, _ in SCALE_FACTORS:
                    if pl == word or pl == short:
                        unit = p
                        break
                    unit = p
                    break
        return {"target": _convert_str2amount(num, unit), "is_total": True}

    def for_mod(self, target):
        return {"kind": "for", **target}

    def for_target(self, *parts):
        if len(parts) == 0:
            return {"life": True}
        if len(parts) == 1 and (
            str(parts[0]) == "life" or getattr(parts[0], "type", "") == "LIFE"
        ):
            return {"life": True}
        n = parts[0]
        return {"years": int(n)}

    def starting_mod(self, n):
        return {"kind": "starting_at_age", "age": float(n)}

    def from_mod(self, tgt):
        return tgt

    def from_year(self, yr):
        return {"kind": "from_year", "year": yr}

    def from_target(self, tgt):
        return tgt

    def from_birth(self, tgt):
        return tgt

    def dot_birth(self, name, _b):
        return {"kind": "from_birth", "target": str(name), "attr": "birth"}

    def apos_birth(self, name, _apos, _b):
        return {"kind": "from_birth", "target": str(name), "attr": "birth"}

    def dot_death(self, name, _d):
        return {"kind": "from_death", "target": str(name), "attr": "death"}

    def apos_death(self, name, _apos, _d):
        return {"kind": "from_death", "target": str(name), "attr": "death"}

    def from_to_mod(self, from_yr, to_yr):
        return [
            {"kind": "from_year", "year": from_yr},
            {"kind": "until", "target": to_yr, "is_year": True},
        ]

    def from_until_mod(self, from_yr, to_yr):
        return [
            {"kind": "from_year", "year": from_yr},
            {"kind": "until", "target": to_yr, "is_year": True},
        ]

    def after_mod(self, n):
        return {"kind": "after_years", "years": int(n)}

    def to_mod(self, yr):
        return {"kind": "until", "target": yr, "is_year": True}

    def life_ref(self, *parts):
        name = str(parts[0])
        if len(parts) == 2:
            suf = str(parts[1]).lower()
        else:
            suf = str(parts[2]).lower()
        return {"kind": "absolute_life", "target": name, "attr": suf}

    def period(self, tok):
        return str(tok)

    def MONTH(self, tok):
        return "month"

    def YEAR_PERIOD(self, tok):
        return "year"

    def LIFE(self, tok):
        return "life"

    # Terminals
    def NAME(self, tok):
        return str(tok)

    def YEAR(self, tok):
        return int(tok)

    def NUMBER(self, tok):
        return _convert_str2amount(tok)

    def SIGNED_NUMBER(self, tok):
        return _convert_str2amount(tok)

    def UNIT(self, tok):
        return str(tok)

    def __default__(self, data, children, meta):
        return children[0] if children else data
