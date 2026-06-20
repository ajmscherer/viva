# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

"""
Viva Interpreter.

Contains the simulation logic that turns a parsed Program AST
into a list of dated cash flow events.

This is separated from the parser so that different parsing backends
can be used while sharing the same execution/simulation engine.
"""

from __future__ import annotations

import random
from datetime import date
from typing import Any, Callable, get_args, get_origin, overload

from .nodes import Program
from .life import Life, create_life


class FlowEngine:
    """Returned by generateFlowEngine(). Provides access to the factored simulation model.

    Read-only properties:
      - params: dict of random variable names -> type
      - param_distribs: dict of rv_name -> callable(seed=None) -> value
      - getFlows: callable(dict or **kwargs) -> list[dict]
        (only accepts keys from .params with matching types; raises ValueError/TypeError otherwise)
      - drawParamRealization: callable(seed=None) -> dict
      - drawFlows: callable(seed=None) -> list[dict]
    """

    def __init__(
        self,
        params: dict[str, Any],
        param_distribs: dict[str, Callable[..., Any]],
        getFlows: Callable[..., list[dict[str, Any]]],
        drawParamRealization: Callable[..., dict[str, Any]],
        drawFlows: Callable[..., list[dict[str, Any]]],
    ):
        self._params = params
        self._param_distribs = param_distribs
        self._getFlows = getFlows
        self._drawParamRealization = drawParamRealization
        self._drawFlows = drawFlows

    @property
    def params(self) -> dict[str, Any]:
        return self._params

    @property
    def param_distribs(self) -> dict[str, Callable[..., Any]]:
        return self._param_distribs

    @property
    def getFlows(self) -> Callable[..., list[dict[str, Any]]]:
        return self._getFlows

    @property
    def drawParamRealization(self) -> Callable[..., dict[str, Any]]:
        return self._drawParamRealization

    @property
    def drawFlows(self) -> Callable[..., list[dict[str, Any]]]:
        return self._drawFlows


def _validate_program(program: Program) -> None:
    """Semantic validation of the parsed program.

    Checks that all referenced lives and events actually exist.
    Raises ValueError with a clear message on problems.
    """
    declared_lives = {ld.name for ld in program.lives}
    declared_events = {ev.name for ev in program.events}

    referenced_lives: set[str] = set()
    referenced_events: set[str] = set()

    # Collect references from event time windows
    for ev in program.events:
        tw = ev.time_window or {}
        kind = tw.get("kind")
        if kind == "after_event":
            tgt = tw.get("target")
            attr = tw.get("attr")
            evt = tw.get("event")
            if attr in ("death", "birth") and tgt:
                referenced_lives.add(tgt)
            elif evt:
                referenced_events.add(str(evt))
        elif kind == "absolute_life":
            tgt = tw.get("target")
            if tgt:
                referenced_lives.add(tgt)
        elif kind in ("at_age", "starting_at_age"):
            tgt = tw.get("target")
            if tgt:
                referenced_lives.add(tgt)

    # Collect references from flow modifiers
    for fl in program.flows:
        for m in fl.modifiers:
            kind = m.get("kind")
            tgt = m.get("target")
            attr = m.get("attr")

            if attr in ("death", "birth") and isinstance(tgt, str):
                referenced_lives.add(tgt)
            elif kind == "upon" and not attr and isinstance(tgt, str):
                referenced_events.add(tgt)
            elif (
                kind == "until"
                and not m.get("is_year")
                and not m.get("is_total")
                and isinstance(tgt, str)
            ):
                referenced_events.add(tgt)

    # Report errors
    for ref in referenced_lives:
        if ref not in declared_lives:
            raise ValueError(f"Undeclared life referenced: '{ref}'")

    for ref in referenced_events:
        if ref not in declared_events:
            raise ValueError(f"Undeclared event referenced: '{ref}'")


def generateFlowEngine(
    source: str,
    *,
    start_year: int = 2025,
    horizon_years: int = 40,
) -> FlowEngine:
    """
    Parse the given Viva source and return a FlowEngine object.

    The returned FlowEngine has read-only properties:
      - params: dict of random variable names -> type
      - param_distribs: dict of rv_name -> callable(seed=None) -> value
      - getFlows: callable(dict or **kwargs) -> list[dict]
        (validates against .params; raises on unknown keys or bad types)
      - drawParamRealization: callable(seed=None) -> dict
      - drawFlows: callable(seed=None) -> list[dict]

    This is the preferred interface for using the factored simulation model.
    """
    # Lazy import to avoid circular dependency with parser.py facade
    from .parser import parse

    program: Program = parse(source)
    _validate_program(program)

    # Resolve relative years (deterministic)
    def _resolve_year(y):
        if isinstance(y, int) and y < 100:
            return start_year + (y - 1)
        return y

    for ev in program.events:
        if ev.time_window and ev.time_window.get("kind") == "absolute_year":
            y = ev.time_window.get("year")
            ev.time_window["year"] = _resolve_year(y)

    for fl in program.flows:
        for m in fl.modifiers:
            if m.get("kind") == "from_year":
                m["year"] = _resolve_year(m.get("year"))
            elif m.get("kind") == "until" and m.get("is_year"):
                m["target"] = _resolve_year(m.get("target"))

    # Create Life objects
    life_objs: dict[str, Life] = {}
    for ld in program.lives:
        tname = ld.mortality_table
        if not tname or tname == "SSA_2023":
            g = ld.typ.lower()
            tname = "SSA_2023_female" if g in ("woman", "female") else "SSA_2023_male"
        life_objs[ld.name] = create_life(ld.name, ld.typ, ld.birth_year, tname)

    lives = life_objs

    # Map from stochastic event name to its fixed year (for absolute_year cases)
    fixed_event_years: dict[str, int] = {}
    for ev in program.events:
        tw = ev.time_window or {}
        if tw.get("kind") == "absolute_year":
            y = tw.get("year")
            fixed_event_years[ev.name] = int(y) if y is not None else 0

    # --- Discover random parameters (params) ---
    params: dict[str, Any] = {}
    distrib: dict[str, Callable[..., Any]] = {}

    # 1. Death years for each life (always considered random via mortality table)
    for lname, life in lives.items():
        rv_name = f"{lname}_death"
        params[rv_name] = int

        def _make_death_distrib(life_obj=life, life_name=lname):
            def _sample(seed: int | None = None):
                rng = random.Random(seed)
                dseed = rng.randint(0, 2**32 - 1)
                death_start = max(start_year, life_obj.birth_year)
                return life_obj.generate_random_death_year(
                    start_year=death_start, seed=dseed
                )

            return _sample

        distrib[rv_name] = _make_death_distrib()

    # 2. Stochastic events (the value stored in realizations / passed to getFlows)
    # - relative_future → int | None   (the year it fires, or None)
    # - all other stochastic (absolute_year<100%, after_event<100%, pure prob) → bool (did it fire?)
    for ev in program.events:
        tw = ev.time_window or {}
        prob = (ev.probability or {}).get("pct", 100.0)
        kind = tw.get("kind")

        is_stochastic = False
        if prob < 100.0:
            is_stochastic = True
        if kind in ("relative_future",):
            is_stochastic = True

        if is_stochastic:
            rv_name = ev.name

            if kind == "relative_future":
                # distrib directly returns the year it fires, or None
                params[rv_name] = int | None
            else:
                # absolute_year (stoch), after_event (stoch), "probability X% per year",
                # etc.  → the realization is a bool "did the event fire?"
                params[rv_name] = bool

            def _make_event_distrib(p=prob, tw_kind=kind, tw=tw):
                def _sample(seed: int | None = None):
                    rng = random.Random(seed)
                    if tw_kind == "relative_future":
                        n = tw.get("years", 0)
                        for i in range(n):
                            y = start_year + i
                            if rng.random() < (p / 100.0):
                                return y
                        return None
                    if tw_kind == "absolute_year":
                        return rng.random() < (p / 100.0)
                    return rng.random() < (p / 100.0)

                return _sample

            distrib[rv_name] = _make_event_distrib()

    def _type_matches(val: Any, expected: Any) -> bool:
        """Runtime type check for values passed via getFlows against .params types.

        Supports the simple types we declare: int, bool, int | None (and similar unions).
        """
        if expected is int:
            # bool is subclass of int; exclude it for death-year params etc.
            return isinstance(val, int) and not isinstance(val, bool)
        if expected is bool:
            return isinstance(val, bool)

        # Handle union types like int | None
        origin = get_origin(expected)
        if origin is not None:
            for arg in get_args(expected):
                if arg is type(None):
                    if val is None:
                        return True
                elif _type_matches(val, arg):
                    return True
            return False

        try:
            return isinstance(val, expected)
        except TypeError:
            return False

    # --- Define the flows function (deterministic given realizations) ---
    @overload
    def flows(realizations: dict[str, Any]) -> list[dict[str, Any]]: ...

    @overload
    def flows(**realizations: Any) -> list[dict[str, Any]]: ...

    def flows(
        realizations: dict[str, Any] | None = None, **kwargs: Any
    ) -> list[dict[str, Any]]:
        """
        Given a dictionary of realized random values (keys match params in .params),
        return the list of dated cash flows.

        Also supports keyword arguments directly for convenience:

            engine.getFlows({"life_death": 2075, "uni": 2032})
            engine.getFlows(life_death=2075, uni=2032)
            engine.getFlows(**my_realization_dict)

        Both calling styles are supported (and can be mixed; kwargs override).

        Unknown keys or values of the wrong type raise ValueError / TypeError.
        """
        if realizations is None:
            realizations = kwargs
        elif kwargs:
            realizations = {**realizations, **kwargs}

        # Validate provided realizations: keys must exist in params and values must have
        # the declared type. (Unknown keys or wrong types are programmer errors.)
        for rv_name, value in realizations.items():
            if rv_name not in params:
                valid = ", ".join(sorted(params.keys()))
                raise ValueError(
                    f"Unknown parameter '{rv_name}' passed to getFlows(). "
                    f"Valid parameters are: {valid}"
                )
            expected = params[rv_name]
            if not _type_matches(value, expected):
                raise TypeError(
                    f"getFlows() parameter '{rv_name}' got {value!r} "
                    f"(type {type(value).__name__}), expected {expected}"
                )

        deaths: dict[str, int] = {}
        realized: dict[str, int] = {}

        # 1. Deterministic absolute-year events (no RV exposed, prob==100%) are always realized.
        for ev_name, y in fixed_event_years.items():
            if ev_name not in params or params.get(ev_name) is not bool:
                realized[ev_name] = y

        # 2. Apply caller-provided realizations (stoch deaths + stoch events)
        for rv_name, value in realizations.items():
            if rv_name.endswith("_death"):
                life_name = rv_name[:-6]
                deaths[life_name] = value
            else:
                if isinstance(value, bool):
                    if value and rv_name in fixed_event_years:
                        realized[rv_name] = fixed_event_years[rv_name]
                else:
                    if value is not None:
                        realized[rv_name] = value

        # 3. Resolve additional deterministic events (at_age, certain after_event, absolute_life)
        #    and fired stochastic after-events when their base is known.
        def _try_resolve_event(ev):
            if ev.name in realized:
                return False
            tw = ev.time_window or {}
            kind = tw.get("kind")

            if kind == "at_age":
                if lives:
                    age = int(tw.get("age", 0))
                    if "target" in tw:
                        tgt = tw["target"]
                        life = lives.get(tgt) or next(iter(lives.values()))
                    else:
                        life = next(iter(lives.values()))
                    y = life.birth_year + age
                    realized[ev.name] = y
                    return True
            elif kind == "starting_at_age":
                if lives:
                    age = int(tw.get("age", 0))
                    if "target" in tw:
                        tgt = tw["target"]
                        life = lives.get(tgt) or next(iter(lives.values()))
                    else:
                        life = next(iter(lives.values()))
                    y = life.birth_year + age
                    realized[ev.name] = y
                    return True
            elif kind == "absolute_life":
                tgt = tw.get("target")
                attr = tw.get("attr")
                if attr == "birth" and tgt in lives:
                    realized[ev.name] = lives[tgt].birth_year
                    return True
                if attr == "death" and tgt in deaths:
                    realized[ev.name] = deaths[tgt]
                    return True
            elif kind == "after_event":
                base = None
                offset = int(tw.get("years", 0))
                if tw.get("attr") == "death":
                    tgt = tw.get("target")
                    if isinstance(tgt, str) and tgt in deaths:
                        base = deaths[tgt]
                elif tw.get("attr") == "birth":
                    tgt = tw.get("target")
                    if isinstance(tgt, str) and tgt in lives:
                        base = lives[tgt].birth_year
                else:
                    tevt = tw.get("event")
                    if isinstance(tevt, str) and tevt in realized:
                        base = realized[tevt]
                if base is not None:
                    y = base + offset
                    realized[ev.name] = y
                    return True
            return False

        # First pass for certain events
        for ev in program.events:
            p = (ev.probability or {}).get("pct", 100.0)
            if p >= 100.0:
                _try_resolve_event(ev)

        # Handle cases where a stochastic bool fired for an after_event etc.
        for rv_name, value in realizations.items():
            if isinstance(value, bool) and value:
                for ev in program.events:
                    if ev.name == rv_name:
                        _try_resolve_event(ev)
                        break

        # One more pass in case of chains
        for ev in program.events:
            _try_resolve_event(ev)

        out: list[dict] = []

        def _get_trigger_year(flow):
            starts: list[int] = []
            has_explicit_start = False
            for m in flow.modifiers:
                if m["kind"] == "upon":
                    has_explicit_start = True
                    tgt = m.get("target")
                    if m.get("attr") == "death":
                        if tgt in deaths:
                            dy = deaths[tgt]
                            if dy >= start_year:
                                starts.append(dy)
                    elif m.get("attr") == "birth":
                        if tgt in lives:
                            by = lives[tgt].birth_year
                            if by >= start_year:
                                starts.append(by)
                    else:
                        if tgt in realized:
                            starts.append(realized[tgt])
                elif m["kind"] in ("from_year", "from_death", "from_birth"):
                    has_explicit_start = True
                    if m["kind"] == "from_year":
                        starts.append(m["year"])
                    elif m["kind"] == "from_death":
                        tgt = m.get("target")
                        if m.get("attr") == "death" and tgt in deaths:
                            dy = deaths[tgt]
                            if dy >= start_year:
                                starts.append(dy)
                    elif m["kind"] == "from_birth":
                        tgt = m.get("target")
                        if m.get("attr") == "birth" and tgt in lives:
                            starts.append(lives[tgt].birth_year)

            if not starts:
                if not has_explicit_start:
                    starts = [start_year]
                else:
                    starts = []
            after = None
            for m in flow.modifiers:
                if m["kind"] == "after_years":
                    after = m["years"]
                    break
            if after is not None:
                starts = [s + after for s in starts]
            for m in flow.modifiers:
                if m["kind"] == "starting_at_age":
                    if lives:
                        life = list(lives.values())[0]
                        birth = getattr(life, "birth_year", getattr(life, "born", 0))
                        offset_y = birth + int(m["age"])
                        starts = [max(s, offset_y) for s in starts]
            return starts

        def _get_end_year(flow, s_year):
            for m in flow.modifiers:
                if m["kind"] == "for":
                    if m.get("life"):
                        life_name = None
                        for mm in flow.modifiers:
                            if mm.get("target") in deaths:
                                life_name = mm["target"]
                                break
                        if life_name is None and lives:
                            life_name = list(lives.keys())[0]
                        if life_name in deaths:
                            dy = deaths[life_name]
                            return max(dy, s_year)
                        return s_year + 100
                    if "years" in m:
                        return s_year + m["years"] - 1
                if m["kind"] == "until":
                    if m.get("is_total"):
                        return None
                    tgt = m.get("target")
                    if m.get("is_year"):
                        return tgt
                    if m.get("attr") == "death":
                        if isinstance(tgt, str) and tgt in deaths:
                            return max(deaths[tgt], s_year)
                        return None
                    elif m.get("attr") == "birth":
                        if isinstance(tgt, str) and tgt in lives:
                            return lives[tgt].birth_year
                        return None
                    if isinstance(tgt, str) and tgt in realized:
                        return realized[tgt]
                    if isinstance(tgt, str) and tgt in deaths:
                        return max(deaths[tgt], s_year)
            return None

        for flow in program.flows:
            starts = _get_trigger_year(flow)
            base_amt = flow.amount
            if flow.period == "month":
                base_amt *= 12.0

            is_cap = any(
                m.get("is_total") for m in flow.modifiers if m["kind"] == "until"
            )
            cap_val = None
            for m in flow.modifiers:
                if m.get("is_total"):
                    cap_val = m["target"]
                    break

            one_time = flow.period is None

            for s in starts:
                end = _get_end_year(flow, s)
                cumul = 0.0
                y = max(s, start_year)
                horizon_end = start_year + horizon_years
                while y < horizon_end and (end is None or y <= end):
                    amt = base_amt
                    if is_cap and cap_val is not None and cumul + abs(amt) > cap_val:
                        break
                    out.append(
                        {
                            "date": date(y, 1, 1),
                            "name": flow.name,
                            "amount": float(amt),
                            "currency": "USD",
                        }
                    )
                    cumul += abs(amt) if is_cap else 0.0
                    if one_time:
                        break
                    y += 1

        out.sort(key=lambda e: (e["date"], e["name"], -e["amount"]))
        return out

    def draw_realizations(seed: int | None = None):
        """Draw a full set of realizations. If seed given, derive independent sub-seeds for each RV."""
        if seed is None:
            return {rv: distrib[rv](seed=None) for rv in params}
        master = random.Random(seed)
        out = {}
        for rv_name in params:
            subseed = master.randint(0, 2**32 - 1)
            out[rv_name] = distrib[rv_name](seed=subseed)
        return out

    def draw_flows(seed: int | None = None) -> list[dict]:
        """Convenience: draw realizations then compute flows. Seed controls whole draw."""
        kwargs = draw_realizations(seed)
        return flows(kwargs)

    return FlowEngine(
        params=params,
        param_distribs=distrib,
        getFlows=flows,
        drawParamRealization=draw_realizations,
        drawFlows=draw_flows,
    )
