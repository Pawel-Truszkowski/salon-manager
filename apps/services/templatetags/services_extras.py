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


@register.filter
def pl_plural(count, forms):
    """Polish noun form for a count: `{{ 16|pl_plural:"opinia,opinie,opinii" }}` -> "opinii"."""
    one, few, many = forms.split(',')
    count = int(count)
    if count == 1:
        return one
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return few
    return many


@register.filter
def rating(value):
    """A star rating the Polish way, with a decimal comma: 4.9 -> "4,9", 5 -> "5,0"."""
    return f'{float(value):.1f}'.replace('.', ',')


@register.filter
def without_category(name, category_name):
    """Service name without its repeated category: "Depilacja laserowa – pachy" -> "Pachy" (category pages).

    Names that don't start with "<category> – " stay as they are ("Henna brwi" in "Rzęsy i brwi").
    """
    prefix = f'{category_name} – '
    if name.lower().startswith(prefix.lower()) and len(name) > len(prefix):
        rest = name[len(prefix) :]
        return rest[0].upper() + rest[1:]
    return name
