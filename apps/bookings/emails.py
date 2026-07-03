import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)

def send_booking_confirmation_to_client(appointment):
    try:
        html_message = render_to_string('emails/booking_confirmation_client.html', {'appointment': appointment})
        send_mail(
            subject='Potwierdzenie rezerwacji od Royal Beauty',
            message='Dziękujemy za rezerwację! Szczegóły w załączonym e-mailu.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.client_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent booking confirmation email to client: {appointment.client_email} for reservation({appointment.id})")
    except Exception as e:
        logger.error(f"Error sending confirmation email to the client {appointment.client_email}, reservation({appointment.id}): {e}")


def send_booking_notification_to_salon(appointment):
    try:
        html_message = render_to_string('emails/booking_notification_salon.html', {'appointment': appointment})
        send_mail(
            subject=f'Nowa rezerwacja: {appointment.client_name}',
            message='Nowa rezerwacja została dokonana. Szczegóły w załączonym e-mailu.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.SALON_EMAIL],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent booking notification email to salon: {settings.SALON_EMAIL} for reservation({appointment.id})")
    except Exception as e:
        logger.error(f"Error sending notification email to the salon {settings.SALON_EMAIL}, reservation({appointment.id}): {e}")


def send_confirmation_email(appointment):
    try:
        html_message = render_to_string('emails/booking_confirmed_client.html', {'appointment': appointment})
        send_mail(
            subject='Twoja wizyta została potwierdzona — Royal Beauty',
            message='Twoja wizyta została potwierdzona przez salon. Szczegóły w załączonym e-mailu.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.client_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent confirmation email to client: {appointment.client_email} for reservation({appointment.id})")
    except Exception as e:
        logger.error(f"Error sending confirmation email to the client {appointment.client_email}, reservation({appointment.id}): {e}")
        