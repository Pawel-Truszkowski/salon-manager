from django.urls import path
from api.views import ServiceListView

urlpatterns = [
    path('services/', ServiceListView.as_view(), name='api-services'),
]
