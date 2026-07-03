from django.contrib import admin, messages

from .emails import send_confirmation_email
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('service', 'employee', 'date_time', 'status', 'client_name', 'client_email', 'client_phone')
    list_filter = ('status', 'service', 'employee')
    search_fields = ('client_name', 'client_email', 'client_phone')
    actions = ['confirm_appointments']

    def save_model(self, request, obj, form, change):
        newly_confirmed = change and 'status' in form.changed_data and obj.status == 'confirmed'
        super().save_model(request, obj, form, change)
        if newly_confirmed:
            send_confirmation_email(obj)

    @admin.action(description='Confirm selected appointments')
    def confirm_appointments(modeladmin, request, queryset):
        confirmed_count = 0
        for appointment in queryset:
            if appointment.confirm():
                confirmed_count += 1
        modeladmin.message_user(request, f"Successfully confirmed {confirmed_count} appointments.", messages.SUCCESS)
