import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.services.models import Employee, Service

from .emails import (
    send_cancellation_email_to_client,
    send_cancellation_notification_to_salon,
    send_confirmation_email,
)


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

    client_name = models.CharField(max_length=100)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=15)
    notes = models.TextField(blank=True)

    cancellation_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_name} — {self.service} {self.date_time:%d.%m.%Y %H:%M}"

    def confirm(self):
        if self.status == self.Status.CONFIRMED:
            return False
        self.status = self.Status.CONFIRMED
        self.save(update_fields=['status'])
        send_confirmation_email(self)
        return True

    def complete(self):
        if self.status != self.Status.CONFIRMED:
            raise ValueError("Only confirmed appointments can be completed.")
        self.status = self.Status.COMPLETED
        self.save(update_fields=['status'])

    @property
    def can_be_cancelled(self):
        return self.status in (self.Status.PENDING, self.Status.CONFIRMED) and self.date_time > timezone.now()

    def cancel(self):
        if not self.can_be_cancelled:
            return False
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status'])
        send_cancellation_email_to_client(self)
        send_cancellation_notification_to_salon(self)
        return True

    def get_cancel_url(self):
        return f"{settings.SITE_URL}{reverse('cancel_booking', args=[self.cancellation_token])}"
