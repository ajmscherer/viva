# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

"""
Viva Abstract Syntax Tree (AST) node definitions.

These classes are independent of any particular parser backend.
They represent the structured meaning of a Viva program.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LifeDecl:
    name: str
    typ: str
    birth_year: int  # year only (MVP)
    mortality_table: str | None = (
        None  # e.g. "SSA_2023_male", or None -> default assigned later
    )


@dataclass
class EventDecl:
    name: str
    time_window: dict[str, Any] | None = None
    probability: dict[str, Any] | None = None


@dataclass
class FlowDecl:
    name: str
    amount: float  # already scaled (k/m applied)
    period: str | None = None  # "year" | "month" | None (one-time)
    modifiers: list[dict[str, Any]] = field(default_factory=list)
    # modifiers examples:
    # {"kind": "upon", "target": "child_birth"}
    # {"kind": "upon", "target": "Paul", "attr": "death"}
    # {"kind": "until", "target": "retirement"}   # event name
    # {"kind": "until", "target": 100000.0, "is_total": True}
    # {"kind": "for", "years": 20}
    # {"kind": "for", "life": True}
    # {"kind": "starting_at_age", "age": 80}
    # {"kind": "from_year", "year": 2027}
    # {"kind": "after_years", "years": 4}
    # {"kind": "until", "target": 2031, "is_year": True}  # from "until year" or "to year"


@dataclass
class Program:
    lives: list[LifeDecl] = field(default_factory=list)
    events: list[EventDecl] = field(default_factory=list)
    flows: list[FlowDecl] = field(default_factory=list)
