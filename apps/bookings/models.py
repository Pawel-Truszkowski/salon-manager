import re
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.services.models import Employee, Service

from .emails import (
    send_cancellation_email_to_client,
    send_cancellation_notification_to_salon,
    send_cancelled_by_salon_email,
    send_confirmation_email,
    send_rescheduled_email,
)


def normalize_phone(phone):
    """Digits only, without the Polish prefix: "+48 793-355-756" -> "793355756".

    The same number typed differently on the website and in the panel must find the same client.
    """
    digits = re.sub(r'\D', '', phone or '')
    for prefix in ('0048', '48'):
        if digits.startswith(prefix) and len(digits) == len(prefix) + 9:
            return digits[len(prefix) :]
    return digits


class Client(models.Model):
    """The salon's client file: contact details typed once, the visit history, private notes.

    One client per phone number (`normalize_phone`). Appointments link to it on save (`Appointment.save`)
    but keep their own copy of name/phone/e-mail: that is what the client gave for that visit and what
    its e-mails use.
    """

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True)
    # Seen only by the salon (allergies, preferred lash curl...), never sent to the client
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)

    @property
    def phone_display(self):
        """ "793 355 756" for Polish numbers, as typed for others."""
        if len(self.phone) == 9:
            return f'{self.phone[:3]} {self.phone[3:6]} {self.phone[6:]}'
        return self.phone

    @classmethod
    def for_booking(cls, name, phone, email=''):
        """The client with this phone number, created on the first booking.

        An existing client keeps the details the salon has (a website form can't overwrite them);
        only a missing e-mail is filled in.
        """
        phone = normalize_phone(phone)
        if not phone:
            return None
        client, created = cls.objects.get_or_create(phone=phone, defaults={'name': name, 'email': email})
        if not created and email and not client.email:
            client.email = email
            client.save(update_fields=['email', 'updated_at'])
        return client


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Oczekująca'
        CONFIRMED = 'confirmed', 'Potwierdzona'
        COMPLETED = 'completed', 'Zrealizowana'
        CANCELLED = 'cancelled', 'Anulowana'

    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='appointments',
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='appointments',
    )
    date_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointments',
    )
    client_name = models.CharField(max_length=100)
    # Optional only for appointments added in the panel (phone bookings); BookingForm requires it on the website
    client_email = models.EmailField(blank=True)
    client_phone = models.CharField(max_length=15)
    notes = models.TextField(blank=True)

    cancellation_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    def __str__(self):
        return f"{self.client_name} — {self.service} {self.date_time:%d.%m.%Y %H:%M}"

    def save(self, *args, **kwargs):
        # Every booking path (website, panel, admin) lands in the client file
        if self.client_id is None:
            self.client = Client.for_booking(self.client_name, self.client_phone, self.client_email)
            if self.client and kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = {*kwargs['update_fields'], 'client'}
        super().save(*args, **kwargs)

    def confirm(self):
        if self.status == self.Status.CONFIRMED:
            return False
        self.status = self.Status.CONFIRMED
        self.save()
        send_confirmation_email(self)
        return True

    def complete(self):
        if self.status != self.Status.CONFIRMED:
            raise ValueError("Only confirmed appointments can be completed.")
        self.status = self.Status.COMPLETED
        self.save()

    @property
    def can_be_cancelled(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED) and self.date_time > timezone.now()

    def cancel(self, by_salon=False):
        if not self.can_be_cancelled:
            return False
        self.status = self.Status.CANCELLED
        self.save()
        if by_salon:
            send_cancelled_by_salon_email(self)
        else:
            send_cancellation_email_to_client(self)
            send_cancellation_notification_to_salon(self)
        return True

    @property
    def can_be_rescheduled(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED)

    def reschedule(self, new_date_time, employee=None):
        if not self.can_be_rescheduled:
            raise ValueError("Only pending or confirmed appointments can be rescheduled.")
        self.date_time = new_date_time
        if employee is not None:
            self.employee = employee
        self.save()
        send_rescheduled_email(self)

    def get_cancel_url(self):
        return f"{settings.SITE_URL}{reverse('cancel_booking', args=[self.cancellation_token])}"
