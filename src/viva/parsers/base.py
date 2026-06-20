# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

"""
Abstract base interface for Viva parsers.

This allows the rest of the Viva codebase (and users) to depend only on
this interface, not on any specific parsing library (currently Lark).

A concrete implementation (e.g. LarkParser) must implement all abstract
methods and return the same AST types defined in viva.nodes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from ..nodes import Program


@runtime_checkable
class ParseTree(Protocol):
    """
    Protocol that raw syntactic trees should satisfy.

    The main method used across the project and documentation is .pretty().
    Different backends may return objects with additional attributes
    (e.g. .children, .data), but only .pretty() is guaranteed by this protocol.

    This allows type checkers to understand get_parse_tree() without
    importing Lark or any other specific library in user code.
    """

    def pretty(self, indent_str: str = "  ") -> str:
        """Return a pretty-printed string representation of the tree."""
        ...


class Parser(ABC):
    """
    Abstract interface for a Viva parser.

    Implementations must be able to turn Viva source text into the
    high-level Program AST, and expose the raw syntactic tree
    for debugging / visualization (e.g. for "syntactic tree" diagrams).

    See viva.parsers.lark_parser.LarkParser for the current implementation.
    """

    @abstractmethod
    def parse(self, source: str) -> Program:
        """
        Parse Viva source code and return a fully constructed Program AST.

        This is the main entry point used by generateFlowEngine() and most users.
        """
        raise NotImplementedError

    @abstractmethod
    def get_parse_tree(self, source: str) -> ParseTree:
        """
        Return the raw concrete syntactic tree produced by the underlying
        parser (before any transformation to the high-level AST).

        This is primarily for debugging, grammar exploration, and
        generating "syntactic tree" visualizations (call .pretty() on it).

        The returned value satisfies the ParseTree protocol (has .pretty()).
        The concrete runtime type depends on the backend (e.g. lark.Tree).

        Callers should prefer .pretty() or the protocol methods rather than
        assuming a specific class.
        """
        raise NotImplementedError
