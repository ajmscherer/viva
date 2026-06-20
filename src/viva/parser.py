# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

"""
Public parsing API for Viva (MVP).

This module provides the main entry points:

- parse(source) -> Program
- get_parse_tree(source) -> raw syntactic tree (for visualization/debugging)
- generateFlowEngine(source, ...) -> FlowEngine (factored model with params, param_distribs, getFlows, drawParamRealization, drawFlows)
- set_default_parser() / get_default_parser() for swapping backends globally

It uses the abstract Parser interface (see viva.parsers) under the hood.
The default implementation is LarkParser (using the grammar in
src/viva/grammars/viva.lark), but you can replace it at runtime
with any other class that implements viva.parsers.base.Parser.

You can also instantiate LarkParser with a custom grammar string:
    LarkParser(grammar=my_grammar_string)


This design allows the Viva core to remain independent of any specific
parsing library (Lark today, possibly a custom implementation in the future).
"""

from __future__ import annotations

from .nodes import EventDecl, FlowDecl, LifeDecl, Program
from .interpreter import FlowEngine, generateFlowEngine
from .parsers.base import Parser, ParseTree
from .parsers.lark_parser import LarkParser

# The default parser instance used by parse(), get_parse_tree(), and generateFlowEngine().
_default_parser: Parser = LarkParser()


def set_default_parser(parser: Parser) -> None:
    """
    Globally replace the default parser implementation.

    This affects all subsequent calls to parse(), get_parse_tree(),
    and generateFlowEngine() (unless they explicitly pass a parser instance).

    Example:
        from viva.parsers.base import Parser
        from my_custom_parser import MyVivaParser

        set_default_parser(MyVivaParser())

    Useful for testing, benchmarking, or switching to a pure-Python
    implementation that has no external dependencies.
    """
    if not isinstance(parser, Parser):
        raise TypeError(f"Expected a Parser instance, got {type(parser)}")
    global _default_parser
    _default_parser = parser


def get_default_parser() -> Parser:
    """Return the currently active default parser."""
    return _default_parser


def parse(source: str) -> Program:
    """
    Parse Viva source code into a Program AST using the default parser.

    This is the recommended high-level entry point for most users.
    """
    return _default_parser.parse(source)


def get_parse_tree(source: str) -> ParseTree:
    """
    Return the raw concrete syntactic tree for the given source
    using the default parser.

    Primarily useful for debugging the grammar and for generating
    "syntactic tree" visualizations (call .pretty() on the result).

    The returned object satisfies the ParseTree protocol (has .pretty()).
    The concrete type depends on the active backend (e.g. lark.Tree).
    """
    return _default_parser.get_parse_tree(source)


# Re-export the interface and concrete implementation for advanced users
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
]
