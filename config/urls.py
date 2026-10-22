from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from apps.bookings.views import cancel_booking, submit_booking
from apps.services.views import home
from config.sitemaps import StaticViewSitemap

sitemaps = {'static': StaticViewSitemap}

urlpatterns = [
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('llms.txt', TemplateView.as_view(template_name="llms.txt", content_type="text/plain; charset=utf-8")),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),
    path('admin/', admin.site.urls),
    path('api/', include('apps.api.urls')),
    path('panel/', include('apps.panel.urls')),
    path('', home, name='home'),
    path('bookings/', submit_booking, name='submit_booking'),
    path('bookings/cancel/<uuid:token>/', cancel_booking, name='cancel_booking'),
    path('polityka-prywatnosci/', TemplateView.as_view(template_name='legal/privacy.html'), name='privacy'),
    path('regulamin/', TemplateView.as_view(template_name='legal/terms.html'), name='terms'),
]
