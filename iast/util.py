"""Miscellaneous utilities."""


__all__ = [
    'trim',
]


from textwrap import dedent


def trim(text):
    """Like textwrap.dedent, but also eliminate leading and trailing
    lines if they are whitespace or empty.
    
    This is useful for writing code as triple-quoted multi-line
    strings.
    """
    lines = text.split('\n')
    if len(lines) > 0:
        if len(lines[0]) == 0 or lines[0].isspace():
            lines = lines[1 : ]
    if len(lines) > 0:
        if len(lines[-1]) == 0 or lines[-1].isspace():
            lines = lines[ : -1]
    
    return dedent('\n'.join(lines))
