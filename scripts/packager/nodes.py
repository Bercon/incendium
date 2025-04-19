from dataclasses import dataclass

class Node:
    """Represents a node in the abstract syntax tree"""

@dataclass
class Block(Node):
    """
    Represents a list of statements in the abstract syntax tree.
    """
    statements: list[Node]

@dataclass
class UnparsedCode(Node):
    """Represents an unparsed code in the abstract syntax tree"""
    unparsed: str

@dataclass
class Alternative(Node):
    """
    Represents a list of alternative expressions in the abstract syntax tree.
    Created using magic comments.
    """
    alternatives: list[Block]

@dataclass
class Reorder(Node):
    """
    Represents a list of statements that can be freely reordered in the abstract syntax tree.
    Created using magic comments.
    """
    statements: list[Block]

@dataclass
class IfDef(Node):
    """
    Represents a list of statements that can be disabled with a flag.
    Created using magic comments.
    """
    statements: list[Block]
    flag: str

@dataclass
class Comment(Node):
    """
    Represents a normal comment.
    """
    comment: str
