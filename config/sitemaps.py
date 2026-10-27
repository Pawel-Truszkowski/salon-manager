from django.contrib.sitemaps import Sitemap
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone

from apps.services.category_pages import page_categories
from apps.services.models import Service
from config.context_processors import LEGAL_EFFECTIVE_DATE


class StaticViewSitemap(Sitemap):
    changefreq = 'monthly'

    def items(self):
        return ['home', 'privacy', 'terms']

    def priority(self, item):
        return 1.0 if item == 'home' else 0.3

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        if item == 'home':
            # The price list is what changes on the home page; None (empty catalog) = no <lastmod>.
            # A date, like the legal pages: Django compares all items' lastmod for the Last-Modified header
            last = Service.objects.aggregate(last=Max('updated_at'))['last']
            return timezone.localdate(last) if last else None
        return LEGAL_EFFECTIVE_DATE


class CategorySitemap(Sitemap):
    """/uslugi/<slug>/ pages; <lastmod> = the latest change of their services (price list, descriptions)."""

    changefreq = 'monthly'
    priority = 0.8

    def items(self):
        return page_categories().annotate(last_change=Max('services__updated_at')).order_by('order')

    def lastmod(self, category):
        return timezone.localdate(category.last_change) if category.last_change else None
