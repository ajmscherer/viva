# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

"""
Viva package public API.
"""

__version__ = "0.1.0"

from .parser import (
    parse,
    get_parse_tree,
    generateFlowEngine,
    set_default_parser,
    get_default_parser,
    Program,
    LifeDecl,
    EventDecl,
    FlowDecl,
    Parser,
    ParseTree,
    LarkParser,
)
from .interpreter import FlowEngine
from .life import (
    Life,
    Table,
    get_available_tables,
    get_table,
    get_default_table,
    create_life,
    register_table,
)

# FlowEngine (see interpreter.py):
#   generateFlowEngine(source, ...) returns a FlowEngine with:
#     .params, .param_distribs, .getFlows, .drawParamRealization, .drawFlows
#   This enables direct statistical control and MC checks on the random variables.
#   No more seed overload on generateFlowEngine itself.

__all__ = [
    "parse",
    "get_parse_tree",
    "generateFlowEngine",
    "FlowEngine",
    "set_default_parser",
    "get_default_parser",
    "Program",
    "LifeDecl",
    "EventDecl",
    "FlowDecl",
    "Parser",
    "ParseTree",
    "LarkParser",
    "Life",
    "Table",
    "get_available_tables",
    "get_table",
    "get_default_table",
    "create_life",
    "register_table",
]
