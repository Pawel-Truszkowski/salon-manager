from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Phone number'
    )

    def __str__(self):
        return self.email
