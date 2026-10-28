from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from apps.bookings.views import cancel_booking, submit_booking
from apps.services.views import category_detail, guide_detail, guide_list, home, llms_txt
from config.sitemaps import CategorySitemap, GuideSitemap, StaticViewSitemap

sitemaps = {'static': StaticViewSitemap, 'categories': CategorySitemap, 'guides': GuideSitemap}

urlpatterns = [
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('llms.txt', llms_txt),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls')),
    path('panel/', include('apps.panel.urls')),
    path('', home, name='home'),
    path('uslugi/<slug:slug>/', category_detail, name='category_detail'),
    path('poradniki/', guide_list, name='guide_list'),
    path('poradniki/<slug:slug>/', guide_detail, name='guide_detail'),
    path('bookings/', submit_booking, name='submit_booking'),
    path('bookings/cancel/<uuid:token>/', cancel_booking, name='cancel_booking'),
    path('polityka-prywatnosci/', TemplateView.as_view(template_name='legal/privacy.html'), name='privacy'),
    path('regulamin/', TemplateView.as_view(template_name='legal/terms.html'), name='terms'),
]
