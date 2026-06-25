from django.contrib import admin

from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('service', 'employee', 'date_time', 'status', 'client_name', 'client_email', 'client_phone')
    list_filter = ('status', 'service', 'employee')
    search_fields = ('client_name', 'client_email', 'client_phone')
