from django.core.mail import send_mail
from django.conf import settings


def _send_emails(booking):
    specialist_name = booking.employee.first_name if booking.employee else 'naszą specjalistką'

    # To Client
    if booking.client_email:
        send_mail(
            subject='Potwierdzenie rezerwacji od Royal Beauty',
            message=(
                f'Cześć {booking.client_name},\n\n'
                f'Dziękujemy za rezerwację!\n\n'
                f'Usługa:       {booking.service.name}\n'
                f'Specjalistka: {specialist_name}\n'
                f'Data:         {booking.date_time.date().strftime("%d.%m.%Y")}\n'
                f'Godzina:      {booking.date_time.time().strftime("%H:%M")}\n\n'
                f'Potwierdzimy termin w ciągu 24 godzin.\n\n'
                f'Zespół Royal Beauty'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.client_email],
        )

    # To Salon
    send_mail(
        subject=f'Nowa rezerwacja: {booking.client_name}',
        message=(
            f'Klientka:     {booking.client_name}\n'
            f'Telefon:      {booking.client_phone}\n'
            f'Usługa:       {booking.service.name}\n'
            f'Specjalistka: {specialist_name}\n'
            f'Data:         {booking.date_time.date()} {booking.date_time.time().strftime("%H:%M")}\n'
            f'Uwagi:        {booking.notes or "—"}'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.OWNER_EMAIL],
    )
