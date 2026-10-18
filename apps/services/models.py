from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def format_price(value):
    """Polish price without needless decimals: "30 zł", "30,50 zł"."""
    if value == value.to_integral_value():
        return f'{value:.0f} zł'
    return f'{value:.2f} zł'.replace('.', ',')


class ServiceCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    # Position in the price list on the website (lower first)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name


class ServiceQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in minutes")
    # Inactive = no longer offered: hidden from the website, API and new bookings; past appointments keep it
    # (appointments PROTECT their service, so it can't be deleted once booked)
    is_active = models.BooleanField(default=True)

    objects = ServiceQuerySet.as_manager()

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    @property
    def price_label(self):
        """Price as shown on the website: "bezpłatnie", "30 zł" or "30,50 zł"."""
        if self.price == 0:
            return 'bezpłatnie'
        return format_price(self.price)


class EmployeeQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Employee(models.Model):
    # Public name shown to clients; may differ from the linked account's `User.first_name/last_name` on purpose
    # (e.g. "Ania" vs "Anna Kowalska"), so don't sync them. Account e-mail lives on `User.email`; this `email`
    # field is legacy and no longer edited in the panel.
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
    # Inactive = left the salon / long leave: hidden from booking and pickers, no panel login, history kept.
    # Lists shown to clients or used to pick someone must use `.active()` (also on `service.employees`).
    is_active = models.BooleanField(default=True)

    objects = EmployeeQuerySet.as_manager()

    def __str__(self):
        return f"{self.first_name}"


class Schedule(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    # Who/when last changed it from the panel (owner sees employees' changes); null = system or before tracking
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

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
    # Who/when last changed it from the panel (owner sees employees' changes); null = system or before tracking
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f"{self.employee} - {self.date} {self.start_time}-{self.end_time} (blocked)"
