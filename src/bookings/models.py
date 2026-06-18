from django.db import models

from services.models import Service, Employee


class Appointment(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Oczekująca'),
        ('confirmed', 'Potwierdzona'),
        ('completed', 'Zrealizowana'),
        ('cancelled', 'Anulowana'),
    ]

    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name='appointments',
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name='appointments',
    )
    date_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )

    client_name = models.CharField(max_length=100)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=15)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client_name} — {self.service} {self.date_time:%d.%m.%Y %H:%M}"
