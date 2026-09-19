"""Fills a prompt template's `{name}` slots without str.format's failure
modes. Templates are admin-edited in the dashboard, so a stray `{` or an
unknown `{placeholder}` must not crash generation: known names are
substituted, `{{` / `}}` become literal braces (the seeded templates use them
around JSON examples), and anything else is left exactly as written.
"""
import re

_TOKEN = re.compile(r"\{\{|\}\}|\{([A-Za-z_][A-Za-z0-9_]*)\}")


def render_prompt(template: str, variables: dict[str, str]) -> str:
    def substitute(match: re.Match[str]) -> str:
        token = match.group(0)
        if token == "{{":
            return "{"
        if token == "}}":
            return "}"
        name = match.group(1)
        return variables.get(name, token)

    return _TOKEN.sub(substitute, template)
