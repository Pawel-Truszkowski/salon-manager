import datetime
import pytest
from django.utils import timezone

from apps.services.models import ServiceCategory, Service, Employee, Schedule
from apps.bookings.models import Appointment


@pytest.fixture
def category(db):
    return ServiceCategory.objects.create(
        name='Zabiegi kosmetyczne', 
        slug='zabiegi-kosmetyczne'
    )


@pytest.fixture
def service(category):
    return Service.objects.create(
        name='Manicure',
        category=category,
        price='80.00',
        duration=60,
    )


@pytest.fixture
def service_short(category):
    return Service.objects.create(
        name='Konsultacja',
        category=category,
        price='30.00',
        duration=30,
    )


@pytest.fixture
def employee(service):
    emp = Employee.objects.create(
        first_name='Anna',
        last_name='Kowalska',
        email='anna@salon.pl',
        bio='Doświadczona stylistka.',
    )
    emp.services.add(service)
    return emp


@pytest.fixture
def schedule(employee):
    """Employee works 09:00–17:00 tomorrow."""
    tomorrow = (timezone.now() + datetime.timedelta(days=1)).date()
    return Schedule.objects.create(
        employee=employee,
        date=tomorrow,
        start_time=datetime.time(9, 0),
        end_time=datetime.time(17, 0),
    )


@pytest.fixture
def tomorrow(schedule):
    return schedule.date


def make_appointment(employee, service, date, hour, minute=0, status='confirmed'):
    dt = timezone.make_aware(datetime.datetime.combine(date, datetime.time(hour, minute)))
    return Appointment.objects.create(
        service=service,
        employee=employee,
        date_time=dt,
        status=status,
        client_name='Klient Testowy',
        client_email='klient@test.pl',
        client_phone='123456789',
    )
