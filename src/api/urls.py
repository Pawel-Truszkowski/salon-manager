from django.urls import path
from api.views import ServiceListView, AvailableSlots

urlpatterns = [
    path('services/', ServiceListView.as_view(), name='api-services'),
    path('available-slots/', AvailableSlots.as_view(), name='api-available-slots'),
]
