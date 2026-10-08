OWNER_GROUP = 'Właściciel'


def is_owner(user):
    """Salon owner: full business control in the panel. Superusers are treated as owners too."""
    if not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=OWNER_GROUP).exists()


def get_employee(user):
    """The `Employee` linked to this account, or None."""
    if not user.is_authenticated:
        return None
    from apps.services.models import Employee

    return Employee.objects.filter(user=user).first()


def has_panel_access(user):
    return is_owner(user) or get_employee(user) is not None
