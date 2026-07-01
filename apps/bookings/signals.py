from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Appointment
from .emails import send_booking_confirmation_to_client, send_booking_notification_to_salon 


@receiver(post_save, sender=Appointment)
def send_booking_emails(sender, instance, created, **kwargs):
    if created:
        send_booking_confirmation_to_client(instance)
        send_booking_notification_to_salon(instance)