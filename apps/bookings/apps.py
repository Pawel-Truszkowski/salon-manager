from django.apps import AppConfig


class BookingsConfig(AppConfig):
    name = 'apps.bookings'
    label = 'bookings'

    def ready(self):
        import apps.bookings.signals  # noqa: F401
