import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)

def send_booking_confirmation_to_client(booking):
    try:
        html_message = render_to_string('emails/booking_confirmation_client.html', {'booking': booking})
        send_mail(
            subject='Potwierdzenie rezerwacji od Royal Beauty',
            message='Dziękujemy za rezerwację! Szczegóły w załączonym e-mailu.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.client_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent booking confirmation email to client: {booking.client_email} for reservation({booking.id})")
    except Exception as e:
        logger.error(f"Error sending confirmation email to the client {booking.client_email}, reservation({booking.id}): {e}")


def send_booking_notification_to_salon(booking):

    try:
        html_message = render_to_string('emails/booking_notification_salon.html', {'booking': booking})
        send_mail(
            subject=f'Nowa rezerwacja: {booking.client_name}',
            message='Nowa rezerwacja została dokonana. Szczegóły w załączonym e-mailu.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.SALON_EMAIL],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Sent booking notification email to salon: {settings.SALON_EMAIL} for reservation({booking.id})")
    except Exception as e:
        logger.error(f"Error sending notification email to the salon {settings.SALON_EMAIL}, reservation({booking.id}): {e}")


# def _send_emails(booking):
#     specialist_name = booking.employee.first_name if booking.employee else 'naszą specjalistką'

#     # To Client
#     if booking.client_email:
#         send_mail(
#             subject='Potwierdzenie rezerwacji od Royal Beauty',
#             message=(
#                 f'Cześć {booking.client_name},\n\n'
#                 f'Dziękujemy za rezerwację!\n\n'
#                 f'Usługa:       {booking.service.name}\n'
#                 f'Specjalistka: {specialist_name}\n'
#                 f'Data:         {booking.date_time.date().strftime("%d.%m.%Y")}\n'
#                 f'Godzina:      {booking.date_time.time().strftime("%H:%M")}\n\n'
#                 f'Potwierdzimy termin w ciągu 24 godzin.\n\n'
#                 f'Zespół Royal Beauty'
#             ),
#             from_email=settings.DEFAULT_FROM_EMAIL,
#             recipient_list=[booking.client_email],
#         )

#     # To Salon
#     send_mail(
#         subject=f'Nowa rezerwacja: {booking.client_name}',
#         message=(
#             f'Klientka:     {booking.client_name}\n'
#             f'Telefon:      {booking.client_phone}\n'
#             f'Usługa:       {booking.service.name}\n'
#             f'Specjalistka: {specialist_name}\n'
#             f'Data:         {booking.date_time.date()} {booking.date_time.time().strftime("%H:%M")}\n'
#             f'Uwagi:        {booking.notes or "—"}'
#         ),
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         recipient_list=[settings.OWNER_EMAIL],
#     )

