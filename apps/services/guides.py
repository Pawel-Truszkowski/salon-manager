"""Guides (/poradniki/<slug>/): a few articles answering what clients ask, for search and AI answer engines.

Like the category pages, the text is a template (`templates/guides/<slug>.html`) and the metadata lives here:
with a handful of articles a database model and a panel editor would only add moving parts. Each guide links
to its category page and the category page lists its guides, so the two support each other in search.
"""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Guide:
    slug: str
    title: str  # <title> and the headline in JSON-LD
    meta_description: str  # ≤155 characters
    h1: str
    lead: str  # one-sentence summary under the H1 and on the list page
    category_slug: str  # the category page it belongs to
    published: date
    modified: date | None = None  # set when the text changes in substance: it is the sitemap's <lastmod>

    @property
    def updated(self):
        return self.modified or self.published


GUIDES = {
    guide.slug: guide
    for guide in [
        Guide(
            slug='laser-czy-wosk',
            title='Depilacja laserowa czy woskiem? Porównanie | Royal Beauty Wrocław',
            meta_description=(
                'Laser diodowy czy wosk: jak długo trwa efekt, ile kosztuje w dłuższym czasie, co boli bardziej '
                'i komu który sposób pasuje. Porównanie kosmetologa.'
            ),
            h1='Depilacja laserowa czy woskiem?',
            lead='Wosk daje gładką skórę od razu i na kilka tygodni, laser po serii zabiegów na lata. '
            'Porównujemy efekt, koszt, ból i to, komu który sposób pasuje.',
            category_slug='depilacja-laserowa',
            published=date(2026, 10, 27),
        ),
        Guide(
            slug='pielegnacja-rzes-po-przedluzaniu',
            title='Pielęgnacja rzęs po przedłużaniu: 10 zasad | Royal Beauty Wrocław',
            meta_description=(
                'Jak dbać o przedłużone rzęsy, żeby wytrzymały do uzupełnienia: pierwsza doba, demakijaż, '
                'czesanie, sen, czego unikać. Praktyczny poradnik kosmetologa.'
            ),
            h1='Pielęgnacja rzęs po przedłużaniu',
            lead='Jak dbać o przedłużone rzęsy, żeby wyglądały pełnie aż do uzupełnienia i nie osłabiały naturalnych.',
            category_slug='rzesy-i-brwi',
            published=date(2026, 10, 27),
        ),
        Guide(
            slug='przygotowanie-do-mezoterapii-mikroiglowej',
            title='Jak przygotować się do mezoterapii mikroigłowej | Royal Beauty Wrocław',
            meta_description=(
                'Co odstawić przed mezoterapią mikroigłową, kiedy jej nie robić, jak wygląda zabieg i jak dbać '
                'o skórę po nim. Poradnik kosmetologa z Wrocławia.'
            ),
            h1='Jak przygotować się do mezoterapii mikroigłowej',
            lead='Co odstawić przed zabiegiem, jak on wygląda i jak dbać o skórę po nim, żeby efekt był jak najlepszy.',
            category_slug='zabiegi-kosmetyczne',
            published=date(2026, 10, 27),
        ),
    ]
}


def guides_for(category_slug):
    """Guides that belong to a category page, in the order of `GUIDES`."""
    return [guide for guide in GUIDES.values() if guide.category_slug == category_slug]
