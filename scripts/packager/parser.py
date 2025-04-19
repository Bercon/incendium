import pyparsing as pp
from packager import nodes, minimizer


block = pp.Forward()
alternative = pp.Forward()
reorder = pp.Forward()
ifdef_endif = pp.Forward()

# General stuff

end_of_line = pp.Suppress(pp.LineEnd())
comment_start = pp.Suppress(pp.Literal("//"))

# Comments and magic comments

alternative_start = pp.Suppress(pp.Keyword("// #alternative"))
alternative_or = pp.Suppress(pp.Keyword("// #or"))
alternative_end = pp.Suppress(pp.Keyword("// #endalternative"))

reorder_start =  pp.Suppress(pp.Keyword("// #reorder"))
reorder_and =  pp.Suppress(pp.Keyword("// #and"))
reorder_end = pp.Suppress(pp.Keyword("// #endreorder"))

ifdef =  pp.Suppress(pp.Keyword("// #ifdef")) + pp.Word(pp.alphas)
endif = pp.Suppress(pp.Keyword("// #endif"))

magic_comment = alternative_start | alternative_or | alternative_end \
    | reorder_start | reorder_and | reorder_end \
    | ifdef | endif

normal_comment = ~magic_comment + (pp.Suppress(pp.Literal("//")) + pp.rest_of_line)

# Magic comment logic

alternative <<= (
    alternative_start
    + block
    + pp.ZeroOrMore(alternative_or + block)
    + alternative_end
)

reorder <<= (
    reorder_start
    + block
    + pp.ZeroOrMore(reorder_and + block)
    + reorder_end
)

ifdef_endif <<= (
    ifdef
    + block
    + endif
)

# Unparsed code blocks

code_char = pp.CharsNotIn("\n/")
slash = pp.Literal("/") + ~pp.Literal("/")
code_element = slash | code_char
unparsed_code = pp.OneOrMore(code_element, stop_on=(comment_start | end_of_line))

block <<= pp.OneOrMore(alternative | reorder | ifdef_endif | normal_comment | unparsed_code | end_of_line)

# Parsing
alternative.setParseAction(lambda tokens: nodes.Alternative(alternatives=tokens.asList()))
reorder.setParseAction(lambda tokens: nodes.Reorder(statements=tokens.asList()))
def parse_ifdef_endif(tokens):
    t = tokens.asList()
    return nodes.IfDef(flag=t[0], statements=t[1:])
ifdef_endif.setParseAction(parse_ifdef_endif)
normal_comment.setParseAction(lambda tokens: nodes.Comment(comment=" ".join(tokens)))
unparsed_code.setParseAction(lambda tokens: nodes.UnparsedCode(unparsed=minimizer.minimize("".join(tokens))))
block.setParseAction(lambda tokens: nodes.Block(statements=tokens.asList()))

def parse_document(document: str) -> nodes.Block:
    return block.parse_string(document, parse_all=True)[0]
