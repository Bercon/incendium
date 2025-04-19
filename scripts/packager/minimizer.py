import re

def remove_spaces(input_string):
    result = []
    i = 0

    skip = [
        "var ",
        "function ",
        "fn ",
        "struct ",
        "return ",
        "else ",
        "else if",
        "const ",
        "class ",
        "await ",
        "async ",
        "canvas ",
        "<body ",
        "<p id",
        "<p style",
        "\" id=B",
        '<div id="B" ',
        '<div style',
        # " = new ", # For Brotli dict. TODO: Might not actually improve things...
        "new ",
        "NO SMOKE WITHOUT"
    ]

    while i < len(input_string):
        found = False
        for s in skip:
            if input_string[i:i+len(s)] == s:
                result.append(s)
                i += len(s)
                found = True
                break
        if found: continue
        if input_string[i] != " ":
            result.append(input_string[i])
        i += 1

    return ''.join(result)


def minimize(code):
    code = remove_spaces(code)
    return code
