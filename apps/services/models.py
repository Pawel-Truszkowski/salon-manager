from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def format_price(value):
    """Polish price without needless decimals: "30 zł", "30,50 zł"."""
    if value == value.to_integral_value():
        return f'{value:.0f} zł'
    return f'{value:.2f} zł'.replace('.', ',')


MONTHS_GENITIVE = [
    'stycznia', 'lutego', 'marca', 'kwietnia', 'maja', 'czerwca',
    'lipca', 'sierpnia', 'września', 'października', 'listopada', 'grudnia',
]  # fmt: skip


def format_date_range(date_from, date_to):
    """Polish day range as people write it: "8 listopada", "8–9 listopada", "30 listopada – 1 grudnia"."""

    def day_month(d):
        return f'{d.day} {MONTHS_GENITIVE[d.month - 1]}'

    if date_from == date_to:
        return day_month(date_from)
    if (date_from.year, date_from.month) == (date_to.year, date_to.month):
        return f'{date_from.day}–{day_month(date_to)}'
    return f'{day_month(date_from)} – {day_month(date_to)}'


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


class Equipment(models.Model):
    """A device that isn't in the salon all the time, e.g. the rented laser.

    Services that need it (`Service.required_equipment`) can be booked only on the days of an `EquipmentRental`.
    """

    name = models.CharField(max_length=100, unique=True)
    # Shown on the website next to the services that need it
    description = models.TextField(blank=True)
    # Inactive = no longer used: its services can't be booked on any day
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Equipment'

    def __str__(self):
        return self.name


class EquipmentRentalQuerySet(models.QuerySet):
    def upcoming(self):
        """Rentals that haven't ended yet (today's included), soonest first."""
        return self.filter(date_to__gte=timezone.localdate()).order_by('date_from')

    def covering(self, date):
        return self.filter(date_from__lte=date, date_to__gte=date)


class EquipmentRental(models.Model):
    """The days a piece of equipment is in the salon, both ends inclusive (e.g. the laser on 8–9 November)."""

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='rentals')
    date_from = models.DateField()
    date_to = models.DateField()

    objects = EquipmentRentalQuerySet.as_manager()

    class Meta:
        ordering = ['date_from']

    def __str__(self):
        return f'{self.equipment}: {self.date_from:%d.%m.%Y}–{self.date_to:%d.%m.%Y}'

    @property
    def label(self):
        """For the website: "8–9 listopada"."""
        return format_date_range(self.date_from, self.date_to)

    def clean(self):
        # Either date may be None here if its own field validation already failed
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError({'date_to': 'Data końca nie może być wcześniejsza niż data początku.'})


class ServiceQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Service(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # The price is a minimum ("od 170 zł"): the final one depends on the area, agreed at the visit
    price_is_from = models.BooleanField(default=False)
    duration = models.IntegerField(help_text="Duration in minutes")
    # Inactive = no longer offered: hidden from the website, API and new bookings; past appointments keep it
    # (appointments PROTECT their service, so it can't be deleted once booked)
    is_active = models.BooleanField(default=True)
    # Set = bookable only on the days this equipment is rented (`is_service_available_on`)
    required_equipment = models.ForeignKey(
        Equipment, on_delete=models.PROTECT, null=True, blank=True, related_name='services'
    )
    # Latest change to any service (incl. turning one off) = the price list's <lastmod> in the sitemap
    updated_at = models.DateTimeField(auto_now=True)

    objects = ServiceQuerySet.as_manager()

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return self.name

    @property
    def price_label(self):
        """Price as shown on the website: "bezpłatnie", "30 zł", "30,50 zł" or "od 170 zł"."""
        if self.price == 0:
            return 'bezpłatnie'
        if self.price_is_from:
            return f'od {format_price(self.price)}'
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


class BooksyRating(models.Model):
    """The salon's rating on Booksy as the owner read it on one day; the home page shows the latest one.

    Booksy has no public API, so the owner copies the two numbers from her profile. Each update is a new
    row (a short history instead of overwriting), and `as_of` explains why the page may lag behind Booksy.
    Shown as text only: no aggregateRating in JSON-LD (self-serving ratings are forbidden for a LocalBusiness).
    """

    rating = models.DecimalField(
        max_digits=2, decimal_places=1, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    count = models.PositiveIntegerField()
    as_of = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        ordering = ['-as_of', '-pk']  # newest first: .first() is what the page shows

    def __str__(self):
        return f'{self.rating}/5, {self.count} opinii (stan na {self.as_of:%d.%m.%Y})'
