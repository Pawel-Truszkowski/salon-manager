from django.urls import path
from apps.api.views import ServiceListView, EmployeeListView, AvailableSlots, AvailableDates

urlpatterns = [
    path('services/', ServiceListView.as_view(), name='api-services'),
    path('employees/', EmployeeListView.as_view(), name='api-employees'),
    path('available-slots/', AvailableSlots.as_view(), name='api-available-slots'),
    path('available-dates/', AvailableDates.as_view(), name='api-available-dates'),
]
