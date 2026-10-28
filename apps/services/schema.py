"""JSON-LD built from the database, so structured data always matches what the page shows."""

import json

from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe


def jsonld(data):
    """`data` as JSON for a <script type="application/ld+json"> tag, safe to output unescaped."""
    # Same escaping as Django's json_script: "</script>" or "<!--" inside the text can't break out of the tag
    text = json.dumps(data, ensure_ascii=False, indent=2)
    return mark_safe(text.replace('<', '\\u003C').replace('>', '\\u003E').replace('&', '\\u0026'))


def service_offer(service):
    """One price-list row as a schema.org `Offer` of a `Service`."""
    # Prices as strings: json can't dump Decimal, and a float would print "80.0"
    offer = {'@type': 'Offer', 'priceCurrency': 'PLN', 'itemOffered': {'@type': 'Service', 'name': service.name}}
    if service.price_is_from:
        # "od 170 zł" is only the lowest price (depends on the area), not the price of the service
        offer['priceSpecification'] = {
            '@type': 'PriceSpecification',
            'minPrice': str(service.price),
            'priceCurrency': 'PLN',
        }
    else:
        offer['price'] = str(service.price)  # a free consultation is just "0.00"
    return offer


def offer_catalog_jsonld(price_list, site_url):
    """The price list as `hasOfferCatalog` of the salon from base.html (same `@id`, so search engines merge them).

    `price_list` is `apps.services.views.build_price_list()`: one `OfferCatalog` per category, in page order.
    """
    data = {
        '@context': 'https://schema.org',
        '@type': 'BeautySalon',
        '@id': f'{site_url}/#salon',
        'hasOfferCatalog': {
            '@type': 'OfferCatalog',
            'name': 'Cennik',
            'url': f'{site_url}/#cennik',
            'itemListElement': [
                {
                    '@type': 'OfferCatalog',
                    'name': group['category'].name,
                    'itemListElement': [service_offer(service) for service in group['services']],
                }
                for group in price_list
            ],
        },
    }
    return jsonld(data)


def category_page_jsonld(category, services, site_url, page_url):
    """`Service` (with its price list, provided by the salon from base.html) and `BreadcrumbList` of a category page."""
    data = {
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'Service',
                '@id': f'{page_url}#service',
                'name': category.name,
                'serviceType': category.name,
                'url': page_url,
                'provider': {'@id': f'{site_url}/#salon'},
                'areaServed': {'@type': 'City', 'name': 'Wrocław'},
                'hasOfferCatalog': {
                    '@type': 'OfferCatalog',
                    'name': f'Cennik: {category.name}',
                    'itemListElement': [service_offer(service) for service in services],
                },
            },
            {
                '@type': 'BreadcrumbList',
                'itemListElement': [
                    {'@type': 'ListItem', 'position': 1, 'name': 'Royal Beauty', 'item': f'{site_url}/'},
                    {'@type': 'ListItem', 'position': 2, 'name': category.name, 'item': page_url},
                ],
            },
        ],
    }
    return jsonld(data)


def guide_jsonld(guide, site_url, page_url, category_page_url=None):
    """`BlogPosting` by Paulina (the same `@id` as `founder` in base.html) and `BreadcrumbList` of a guide."""
    breadcrumbs = [
        {'@type': 'ListItem', 'position': 1, 'name': 'Royal Beauty', 'item': f'{site_url}/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Poradniki', 'item': f'{site_url}{reverse("guide_list")}'},
        {'@type': 'ListItem', 'position': 3, 'name': guide.h1, 'item': page_url},
    ]
    article = {
        '@type': 'BlogPosting',
        '@id': f'{page_url}#article',
        'headline': guide.h1,
        'description': guide.meta_description,
        'url': page_url,
        'mainEntityOfPage': page_url,
        'inLanguage': 'pl-PL',
        'datePublished': guide.published.isoformat(),
        'dateModified': guide.updated.isoformat(),
        'image': f'{site_url}{static("img/og-salon.jpg")}',
        'author': {
            '@type': 'Person',
            '@id': f'{site_url}/#paulina',
            'name': 'Paulina Truszkowska',
            'jobTitle': 'Kosmetolog',
            'url': f'{site_url}/#o-nas',
        },
        'publisher': {'@id': f'{site_url}/#salon'},
    }
    if category_page_url:
        article['about'] = {'@id': f'{category_page_url}#service'}
    data = {
        '@context': 'https://schema.org',
        '@graph': [article, {'@type': 'BreadcrumbList', 'itemListElement': breadcrumbs}],
    }
    return jsonld(data)
