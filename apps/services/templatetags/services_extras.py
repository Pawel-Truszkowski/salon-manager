from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def description_html(text):
    """Service description as HTML: each line is a paragraph, consecutive lines starting with "- " form one <ul>.

    The salon writes descriptions in the panel as plain text ("Zabieg obejmuje:" followed by "- item" lines).
    """
    html, items = [], []
    for line in (text or '').splitlines():
        line = line.strip()
        if line.startswith('- '):
            items.append(f'<li>{escape(line[2:].strip())}</li>')
            continue
        if items:
            html.append(f'<ul>{"".join(items)}</ul>')
            items = []
        if line:
            html.append(f'<p>{escape(line)}</p>')
    if items:
        html.append(f'<ul>{"".join(items)}</ul>')
    return mark_safe(''.join(html))
