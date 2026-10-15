from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class ServiceCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in minutes")

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    bio = models.TextField()
    services = models.ManyToManyField(Service, related_name='employees')
    # Panel login account; an employee without one simply can't sign in to /panel/
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee',
    )

    def __str__(self):
        return f"{self.first_name}"


class Schedule(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ('employee', 'date', 'start_time')

    def __str__(self):
        return f"{self.employee} - {self.date} {self.start_time}-{self.end_time}"


class WeeklyScheduleEntry(models.Model):
    """One working block in an employee's weekly template, e.g. "Monday 09:00-17:00".

    Several entries on the same weekday = split shift. Concrete `Schedule` rows are generated from these.
    """

    class WeekDay(models.IntegerChoices):
        MONDAY = 0, "poniedziałek"
        TUESDAY = 1, "wtorek"
        WEDNESDAY = 2, "środa"
        THURSDAY = 3, "czwartek"
        FRIDAY = 4, "piątek"
        SATURDAY = 5, "sobota"
        SUNDAY = 6, "niedziela"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='weekly_schedule')
    weekday = models.IntegerField(choices=WeekDay.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['employee', 'weekday', 'start_time']
        constraints = [
            models.UniqueConstraint(fields=['employee', 'weekday', 'start_time'], name='unique_weekly_schedule_entry'),
        ]

    def __str__(self):
        return f"{self.employee} – {self.get_weekday_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"

    def clean(self):
        # Either time may be None here if its own field validation already failed
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({'end_time': 'Godzina zakończenia musi być późniejsza niż rozpoczęcia.'})


class TimeBlock(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='time_blocks')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.employee} - {self.date} {self.start_time}-{self.end_time} (blocked)"
