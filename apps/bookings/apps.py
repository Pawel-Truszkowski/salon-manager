from django.apps import AppConfig


class BookingsConfig(AppConfig):
    name = 'apps.bookings'
    label = 'bookings'

    def ready(self):
        import apps.bookings.checks  # noqa: F401
        import apps.bookings.signals  # noqa: F401
