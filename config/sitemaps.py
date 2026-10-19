from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    changefreq = 'monthly'

    def items(self):
        return ['home', 'privacy', 'terms']

    def priority(self, item):
        return 1.0 if item == 'home' else 0.3

    def location(self, item):
        return reverse(item)
