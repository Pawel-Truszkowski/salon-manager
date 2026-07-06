from django.db import models

from apps.services.models import Service, Employee

from .emails import send_confirmation_email


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
