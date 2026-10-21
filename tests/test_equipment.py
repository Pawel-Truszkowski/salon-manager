"""Rented equipment (the laser): its services are bookable only on rental days, on every booking path."""

import datetime
import json

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Appointment
from apps.bookings.utils import (
    find_available_specialist,
    get_available_slots,
    is_service_available_on,
    next_available_date,
)
from apps.services.models import Equipment, EquipmentRental, Service, ServiceCategory, format_date_range
from tests.conftest import make_appointment
from tests.test_views import home_html, post_booking


def in_days(days):
    return timezone.localdate() + datetime.timedelta(days=days)


def at(date, hour):
    return timezone.make_aware(datetime.datetime.combine(date, datetime.time(hour, 0)))


@pytest.fixture
def laser(db):
    # Created by migration 0011 (also in the test database)
    return Equipment.objects.get(name='LightSheer DUET')


@pytest.fixture
def laser_service(laser, employee):
    category = ServiceCategory.objects.get(slug='depilacja-laserowa')
    service = Service.objects.create(
        name='Laser pachy', category=category, price='150', duration=30, required_equipment=laser
    )
    employee.services.add(service)
    return service


def rent(equipment, date_from, date_to=None):
    return EquipmentRental.objects.create(equipment=equipment, date_from=date_from, date_to=date_to or date_from)


class TestFormatDateRange:
    @pytest.mark.parametrize(
        ('date_from', 'date_to', 'label'),
        [
            (datetime.date(2026, 11, 8), datetime.date(2026, 11, 8), '8 listopada'),
            (datetime.date(2026, 11, 8), datetime.date(2026, 11, 9), '8–9 listopada'),
            (datetime.date(2026, 11, 30), datetime.date(2026, 12, 1), '30 listopada – 1 grudnia'),
        ],
    )
    def test_polish_label(self, date_from, date_to, label):
        assert format_date_range(date_from, date_to) == label


@pytest.mark.django_db
class TestAvailabilityRule:
    def test_service_without_equipment_is_always_available(self, service, tomorrow):
        assert is_service_available_on(service, tomorrow)

    def test_only_on_rental_days_both_ends_inclusive(self, laser, laser_service):
        rent(laser, in_days(3), in_days(4))
        assert not is_service_available_on(laser_service, in_days(2))
        assert is_service_available_on(laser_service, in_days(3))
        assert is_service_available_on(laser_service, in_days(4))
        assert not is_service_available_on(laser_service, in_days(5))

    def test_inactive_equipment_is_never_available(self, laser, laser_service, tomorrow):
        rent(laser, tomorrow)
        laser.is_active = False
        laser.save()
        assert not is_service_available_on(laser_service, tomorrow)

    def test_slots_follow_the_rule(self, laser, employee, laser_service, tomorrow):
        assert get_available_slots(employee, tomorrow, laser_service) == []
        rent(laser, tomorrow)
        assert get_available_slots(employee, tomorrow, laser_service)

    def test_specialist_is_found_only_on_rental_day(self, laser, employee, laser_service, tomorrow):
        assert find_available_specialist(laser_service, at(tomorrow, 10)) is None
        rent(laser, tomorrow)
        assert find_available_specialist(laser_service, at(tomorrow, 10)) == employee


@pytest.mark.django_db
class TestBookingPaths:
    """Both paths from CLAUDE.md: with a chosen specialist (get_available_slots) and without (find_available_specialist)."""

    @pytest.mark.parametrize('choose_employee', [True, False])
    def test_rejected_without_rental(self, client, employee, laser_service, tomorrow, choose_employee):
        response = post_booking(client, laser_service, employee if choose_employee else None, date=tomorrow)
        assert response.status_code == (409 if choose_employee else 400)  # existing codes of the two paths
        assert json.loads(response.content)['ok'] is False
        assert Appointment.objects.count() == 0

    @pytest.mark.parametrize('choose_employee', [True, False])
    def test_accepted_on_rental_day(self, client, laser, employee, laser_service, tomorrow, choose_employee):
        rent(laser, tomorrow)
        response = post_booking(client, laser_service, employee if choose_employee else None, date=tomorrow)
        assert response.status_code == 200
        assert Appointment.objects.get().employee == employee

    def test_available_dates_api_returns_only_rental_days(self, client, laser, employee, laser_service, schedule):
        day_after = schedule.date + datetime.timedelta(days=1)
        schedule.pk = None
        schedule.date = day_after
        schedule.save()  # works two days in a row, the laser is there only on the second
        rent(laser, day_after)
        month = day_after.strftime('%Y-%m')
        response = client.get(reverse('api-available-dates'), {'service': laser_service.pk, 'month': month})
        assert json.loads(response.content)['dates'] == [day_after.isoformat()]


@pytest.mark.django_db
class TestNextAvailableDate:
    def test_laser_only_employee_waits_for_the_rental(self, laser, employee, service, laser_service, tomorrow):
        employee.services.remove(service)
        assert next_available_date() is None
        rent(laser, tomorrow)
        assert next_available_date() == tomorrow

    def test_shorter_laser_service_does_not_hide_a_free_day(self, employee, service, laser_service, tomorrow):
        # The laser service (30 min) is the shortest, but on a day without the laser the 60-min one still counts
        assert next_available_date() == tomorrow


@pytest.fixture
def owner_client(client, owner_user):
    client.force_login(owner_user)
    return client


def rental_url(equipment):
    return reverse('panel:equipment_rental_create', args=[equipment.pk])


@pytest.mark.django_db
class TestPanelRentals:
    def test_owner_adds_a_rental(self, owner_client, laser):
        response = owner_client.post(
            rental_url(laser), {'date_from': in_days(20).isoformat(), 'date_to': in_days(21).isoformat()}
        )
        assert response.status_code == 302
        assert EquipmentRental.objects.get(equipment=laser).date_to == in_days(21)

    @pytest.mark.parametrize(
        ('date_from', 'date_to', 'error'),
        [
            (5, 4, 'Data końca nie może być wcześniejsza'),
            (-3, -2, 'Ten termin już minął.'),
            (11, 12, 'nachodzi na już zapisany'),
        ],
    )
    def test_invalid_rentals_are_refused(self, owner_client, laser, date_from, date_to, error):
        rent(laser, in_days(10), in_days(11))
        response = owner_client.post(
            rental_url(laser), {'date_from': in_days(date_from).isoformat(), 'date_to': in_days(date_to).isoformat()}
        )
        assert response.status_code == 200
        assert error in response.content.decode()
        assert EquipmentRental.objects.count() == 1

    def test_delete_refused_while_clients_are_booked(self, owner_client, laser, employee, laser_service, tomorrow):
        rental = rent(laser, tomorrow)
        make_appointment(employee, laser_service, tomorrow, hour=10)
        owner_client.post(reverse('panel:equipment_rental_delete', args=[rental.pk]))
        assert EquipmentRental.objects.filter(pk=rental.pk).exists()

    def test_delete_without_bookings(self, owner_client, laser):
        rental = rent(laser, in_days(5))
        owner_client.post(reverse('panel:equipment_rental_delete', args=[rental.pk]))
        assert not EquipmentRental.objects.exists()

    def test_list_shows_upcoming_rentals_and_services(self, owner_client, laser, laser_service):
        past = rent(laser, in_days(-10))
        rent(laser, datetime.date(2099, 11, 8), datetime.date(2099, 11, 9))
        html = owner_client.get(reverse('panel:equipment_list')).content.decode()
        assert 'Laser pachy' in html
        assert '08.11.2099' in html
        assert f'{past.date_from:%d.%m.%Y}' not in html

    def test_employee_has_no_access(self, client, employee_user, laser):
        client.force_login(employee_user)
        assert client.get(reverse('panel:equipment_list')).status_code == 403
        assert client.post(rental_url(laser), {}).status_code == 403

    def test_service_form_sets_required_equipment(self, owner_client, laser, service):
        data = {
            'category': service.category.pk,
            'name': service.name,
            'description': '',
            'price': '80',
            'duration': '60',
            'required_equipment': laser.pk,
        }
        owner_client.post(reverse('panel:service_update', args=[service.pk]), data)
        service.refresh_from_db()
        assert service.required_equipment == laser


@pytest.mark.django_db
class TestWebsite:
    def test_price_list_shows_the_next_laser_days(self, client, laser, laser_service):
        rent(laser, datetime.date(2099, 11, 8), datetime.date(2099, 11, 9))
        html = home_html(client)
        assert 'Najbliżej: <strong>8–9 listopada</strong>' in html
        assert 'Laser diodowy LightSheer DUET' in html  # equipment description
        assert 'najbliżej 8–9 listopada' in html  # FAQ answer

    def test_without_rental_the_client_is_asked_to_call(self, client, laser_service):
        html = home_html(client)
        assert 'Kolejny termin wkrótce' in html
        assert 'O najbliższy termin zapytaj telefonicznie' in html

    def test_inactive_equipment_rental_is_not_announced(self, client, laser, laser_service):
        rent(laser, datetime.date(2099, 11, 8))
        laser.is_active = False
        laser.save()
        assert '8 listopada' not in home_html(client)
