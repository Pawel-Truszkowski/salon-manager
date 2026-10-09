import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _send_to_client(appointment, *, template, subject, message, kind):
    # Appointments added in the panel (e.g. booked by phone) may have no e-mail address
    if not appointment.client_email:
        logger.info(f"Skipped {kind} email for reservation({appointment.id}): client has no e-mail address")
        return
    try:
        html_message = render_to_string(
            template,
            {
                'appointment': appointment,
                'cancel_url': appointment.get_cancel_url(),
            },
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[appointment.client_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent {kind} email to client: {appointment.client_email} for reservation({appointment.id})")
    except Exception as e:
        logger.error(
            f"Error sending {kind} email to the client {appointment.client_email}, reservation({appointment.id}): {e}"
        )


def _send_to_salon(appointment, *, template, subject, message, kind):
    try:
        html_message = render_to_string(template, {'appointment': appointment})
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.SALON_EMAIL],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent {kind} email to salon: {settings.SALON_EMAIL} for reservation({appointment.id})")
    except Exception as e:
        logger.error(
            f"Error sending {kind} email to the salon {settings.SALON_EMAIL}, reservation({appointment.id}): {e}"
        )


def send_booking_confirmation_to_client(appointment):
    _send_to_client(
        appointment,
        template='emails/booking_confirmation_client.html',
        subject='Potwierdzenie rezerwacji od Royal Beauty',
        message='Dziękujemy za rezerwację! Szczegóły w załączonym e-mailu.',
        kind='booking confirmation',
    )


def send_booking_notification_to_salon(appointment):
    _send_to_salon(
        appointment,
        template='emails/booking_notification_salon.html',
        subject=f'Nowa rezerwacja: {appointment.client_name}',
        message='Nowa rezerwacja została dokonana. Szczegóły w załączonym e-mailu.',
        kind='booking notification',
    )


def send_confirmation_email(appointment):
    _send_to_client(
        appointment,
        template='emails/booking_confirmed_client.html',
        subject='Twoja wizyta została potwierdzona — Royal Beauty',
        message='Twoja wizyta została potwierdzona przez salon. Szczegóły w załączonym e-mailu.',
        kind='confirmation',
    )


def send_cancellation_email_to_client(appointment):
    _send_to_client(
        appointment,
        template='emails/booking_cancelled_client.html',
        subject='Twoja wizyta została odwołana — Royal Beauty',
        message='Twoja wizyta została odwołana. Zapraszamy do dokonania nowej rezerwacji.',
        kind='cancellation',
    )


def send_cancelled_by_salon_email(appointment):
    _send_to_client(
        appointment,
        template='emails/booking_cancelled_by_salon_client.html',
        subject='Twoja wizyta została odwołana przez salon — Royal Beauty',
        message='Niestety musimy odwołać Twoją wizytę. Szczegóły w załączonym e-mailu.',
        kind='cancelled by salon',
    )


def send_rescheduled_email(appointment):
    _send_to_client(
        appointment,
        template='emails/booking_rescheduled_client.html',
        subject='Zmiana terminu Twojej wizyty — Royal Beauty',
        message='Termin Twojej wizyty został zmieniony. Szczegóły w załączonym e-mailu.',
        kind='rescheduled',
    )


def send_cancellation_notification_to_salon(appointment):
    _send_to_salon(
        appointment,
        template='emails/booking_cancellation_notification_salon.html',
        subject=f'Wizyta odwołana: {appointment.client_name}',
        message='Klientka odwołała wizytę. Szczegóły w załączonym e-mailu.',
        kind='cancellation notification',
    )
