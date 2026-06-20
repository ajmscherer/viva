# Copyright (c) 2026 Alexandre Scherer
# See LICENSE and COMMERCIAL-LICENSE.md

"""
Viva parser backends.

The default grammar lives in `grammars/viva.lark` and is loaded automatically
by `LarkParser`. You can pass a custom grammar when instantiating it:

    from viva.parsers.lark_parser import LarkParser
    p = LarkParser()                    # default grammar
    p = LarkParser(grammar=my_grammar)  # custom

Users who want to depend on a specific backend can import directly:

    from viva.parsers.lark_parser import LarkParser
    from viva.parsers.base import Parser

Most users should just use the top-level functions:

    from viva import parse, get_parse_tree, generateFlowEngine
"""

from .base import Parser, ParseTree
from .lark_parser import LarkParser

__all__ = ["Parser", "ParseTree", "LarkParser"]
