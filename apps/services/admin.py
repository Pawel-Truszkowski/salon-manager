from django.contrib import admin

from .models import Employee, Equipment, EquipmentRental, Schedule, Service, ServiceCategory, TimeBlock


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'order')
    list_editable = ('order',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'duration', 'required_equipment')
    search_fields = ('name', 'category')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email')
    search_fields = ('first_name', 'last_name', 'email')
    filter_horizontal = ('services',)
    autocomplete_fields = ('user',)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'date', 'start_time', 'end_time')
    list_filter = ('employee', 'date')
    search_fields = ('employee__first_name', 'employee__last_name')


@admin.register(TimeBlock)
class TimeBlockAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'date', 'start_time', 'end_time', 'reason')
    list_filter = ('employee', 'date')
    search_fields = ('employee__first_name', 'employee__last_name', 'reason')


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')


@admin.register(EquipmentRental)
class EquipmentRentalAdmin(admin.ModelAdmin):
    list_display = ('id', 'equipment', 'date_from', 'date_to')
    list_filter = ('equipment',)
