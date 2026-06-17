from django.contrib import admin
from .models import Service, Employee, Schedule


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'duration')
    search_fields = ('name', 'category')

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email')
    search_fields = ('first_name', 'last_name', 'email')
    filter_horizontal = ('services',)
    
@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'start_time', 'end_time')
    list_filter = ('employee', 'date')
    search_fields = ('employee__first_name', 'employee__last_name')