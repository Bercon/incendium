

from dataclasses import dataclass
from functools import singledispatch

from packager import nodes

def format(node: nodes.Node, pretty: bool = False, debug: bool = False, comments: bool = False, flags: dict = {}) -> str:
    return Formatter(pretty=pretty, debug=debug, comments=comments, flags=flags).format(node)

@dataclass
class Formatter:
    pretty: bool
    debug: bool
    comments: bool
    flags: dict
    indent = 0

    def format(self, node: nodes.Block) -> str:
        tokens = _traverse(node, self)
        s = ""
        for t in tokens:
            s += t
        return s


# This used to be a singledispatchmethod of Formatter, but for some reason,
# @singledispatchmethod are far slower than @singledispatch
@singledispatch
def _traverse(node: nodes.Node, fmt: Formatter):
    raise TypeError("Unkown node", node)


@_traverse.register
def _(node: nodes.UnparsedCode, fmt: Formatter):
    if fmt.debug:
        yield '  ' * fmt.indent
        yield '[Code]: '
    yield node.unparsed
    if fmt.pretty:
        yield '\n'


@_traverse.register
def _(node: nodes.Block, fmt: Formatter):
    if fmt.debug:
        yield '  ' * fmt.indent
        yield '[Block]:\n'
    for n in node.statements:
        yield from _traverse(n, fmt)


@_traverse.register
def _(node: nodes.Reorder, fmt: Formatter):
    if fmt.debug:
        yield '  ' * fmt.indent
        yield '[Reorder]:\n'
        fmt.indent += 1
    for n in node.statements:
        yield from _traverse(n, fmt)
    if fmt.debug: fmt.indent -= 1


@_traverse.register
def _(node: nodes.Alternative, fmt: Formatter):
    if fmt.debug:
        yield '  ' * fmt.indent
        yield '[Alternative]:\n'
        fmt.indent += 1
    yield from _traverse(node.alternatives[0], fmt)
    if fmt.debug: fmt.indent -= 1


@_traverse.register
def _(node: nodes.IfDef, fmt: Formatter):
    enabled = fmt.flags.get(node.flag, False)
    if fmt.debug:
        yield '  ' * fmt.indent
        yield f'[IfDef "{node.flag}" ({enabled})]:\n'
    if not enabled:
        yield ''
    else:
        for n in node.statements:
            yield from _traverse(n, fmt)


@_traverse.register
def _(node: nodes.Comment, fmt: Formatter):
    if fmt.debug: yield '[Comment]: '
    if fmt.comments: yield node.comment + '\n'
    else: yield ''
