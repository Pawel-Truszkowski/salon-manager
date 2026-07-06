from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from config.sitemaps import StaticViewSitemap

from apps.services.views import home
from apps.bookings.views import submit_booking

sitemaps = {'static': StaticViewSitemap}

urlpatterns = [
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),
    
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls')),
    path('', home, name='home'),
    path('bookings/', submit_booking, name='submit_booking'),
]
