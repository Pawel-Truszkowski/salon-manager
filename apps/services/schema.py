"""JSON-LD built from the database, so structured data always matches what the page shows."""

import json

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
