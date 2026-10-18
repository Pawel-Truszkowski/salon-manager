import datetime
import secrets

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from apps.accounts.roles import OWNER_GROUP
from apps.bookings.models import Appointment
from apps.services.models import Employee, Schedule, Service, ServiceCategory, TimeBlock

# Random per test run instead of a literal: there's nothing for secret scanners (GitGuardian) to flag
TEST_PASSWORD = secrets.token_urlsafe(16)


@pytest.fixture
def category(db):
    return ServiceCategory.objects.create(name='Zabiegi kosmetyczne', slug='zabiegi-kosmetyczne')


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


def make_appointment(employee, service, date, hour, minute=0, status=Appointment.Status.CONFIRMED):
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


def make_time_block(employee, date, start_hour, end_hour, reason=''):
    return TimeBlock.objects.create(
        employee=employee,
        date=date,
        start_time=datetime.time(start_hour, 0),
        end_time=datetime.time(end_hour, 0),
        reason=reason,
    )


# --- Panel roles ---

User = get_user_model()


@pytest.fixture
def owner_user(db):
    user = User.objects.create_user(username='wlascicielka', password=TEST_PASSWORD, email='owner@salon.pl')
    user.groups.add(Group.objects.get(name=OWNER_GROUP))
    return user


@pytest.fixture
def employee_user(employee):
    user = User.objects.create_user(username='anna', password=TEST_PASSWORD, email='anna@salon.pl')
    employee.user = user
    employee.save()
    return user


@pytest.fixture
def other_employee(service):
    emp = Employee.objects.create(first_name='Ewa', email='ewa@salon.pl', bio='')
    emp.services.add(service)
    return emp


@pytest.fixture
def plain_user(db):
    return User.objects.create_user(username='klient', password=TEST_PASSWORD)
