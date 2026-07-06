from django.contrib import admin, messages

from .emails import send_confirmation_email
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('service', 'employee', 'date_time', 'status', 'client_name', 'client_email', 'client_phone')
    list_filter = ('status', 'service', 'employee')
    search_fields = ('client_name', 'client_email', 'client_phone')
    actions = ['confirm_appointments', 'complete_appointments']

    def save_model(self, request, obj, form, change):
        newly_confirmed = change and 'status' in form.changed_data and obj.status == Appointment.Status.CONFIRMED
        super().save_model(request, obj, form, change)
        if newly_confirmed:
            send_confirmation_email(obj)

    @admin.action(description='Potwierdź zaznaczone wizyty')
    def confirm_appointments(modeladmin, request, queryset):
        confirmed_count = 0
        for appointment in queryset:
            if appointment.confirm():
                confirmed_count += 1
        modeladmin.message_user(request, f"Successfully confirmed {confirmed_count} appointments.", messages.SUCCESS)
        
    @admin.action(description='Zaznaczone wizyty zostały zrealizowane')
    def complete_appointments(modeladmin, request, queryset):
        completed_count = 0
        for appointment in queryset:
            try:
                appointment.complete()
                completed_count += 1
            except ValueError:
                modeladmin.message_user(request, f"Appointment {appointment} is not confirmed and cannot be completed.", messages.ERROR)
        modeladmin.message_user(request, f"Successfully marked {completed_count} appointments as completed.", messages.SUCCESS)
