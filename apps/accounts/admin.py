from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Dodaj phone_number do panelu admina
    fieldsets = UserAdmin.fieldsets + (
        ('Dodatkowe informacje', {'fields': ('phone_number',)}),
    )
