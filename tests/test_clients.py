"""Client file: one card per phone number, filled by every booking path, managed by the owner in the panel."""

import importlib
import json

import pytest
from django.apps import apps as django_apps
from django.urls import reverse

from apps.bookings.models import Appointment, Client, normalize_phone
from tests.conftest import make_appointment
from tests.test_panel_appointments import create_data
from tests.test_views import post_booking

import_migration = importlib.import_module('apps.bookings.migrations.0005_import_clients')


@pytest.fixture
def owner_client(client, owner_user):
    client.force_login(owner_user)
    return client


@pytest.fixture
def anna(db):
    return Client.objects.create(
        name='Anna Nowak', phone='+48 600 100 200', email='anna@test.pl', notes='Alergia na lateks'
    )


class TestNormalizePhone:
    @pytest.mark.parametrize(
        ('typed', 'stored'),
        [
            ('600100200', '600100200'),
            ('600 100 200', '600100200'),
            ('600-100-200', '600100200'),
            ('+48 600 100 200', '600100200'),
            ('0048600100200', '600100200'),
            ('+44 20 7946 0958', '442079460958'),  # foreign number: digits only, prefix kept
            ('', ''),
        ],
    )
    def test_formats(self, typed, stored):
        assert normalize_phone(typed) == stored


@pytest.mark.django_db
class TestClientModel:
    def test_phone_is_stored_normalized_and_displayed_in_groups(self, anna):
        assert anna.phone == '600100200'
        assert anna.phone_display == '600 100 200'

    def test_first_booking_creates_the_client(self, employee, service, tomorrow):
        appointment = make_appointment(employee, service, tomorrow, 10)
        client = appointment.client
        assert (client.name, client.phone, client.email) == ('Klient Testowy', '123456789', 'klient@test.pl')

    def test_same_phone_typed_differently_is_the_same_client(self, anna, employee, service, tomorrow):
        appointment = make_appointment(employee, service, tomorrow, 10)
        appointment.client = None
        appointment.client_phone = '+48 600-100-200'
        appointment.save()
        assert appointment.client == anna
        assert Client.objects.count() == 2  # the one from make_appointment + Anna, no duplicate

    def test_booking_does_not_overwrite_the_card_but_fills_a_missing_email(self, db):
        client = Client.for_booking('Anna', '600100200', '')
        same = Client.for_booking('Ania z literówką', '600100200', 'anna@test.pl')
        assert same == client
        client.refresh_from_db()
        assert client.name == 'Anna'
        assert client.email == 'anna@test.pl'
        Client.for_booking('Anna', '600100200', 'inny@test.pl')
        client.refresh_from_db()
        assert client.email == 'anna@test.pl'

    def test_appointment_keeps_its_own_copy_of_the_details(self, anna, employee, service, tomorrow):
        appointment = make_appointment(employee, service, tomorrow, 10)
        anna.name = 'Anna Kowalska'
        anna.save()
        appointment.refresh_from_db()
        assert appointment.client_name == 'Klient Testowy'


@pytest.mark.django_db
class TestBookingPathsFillTheFile:
    def test_website_booking(self, client, employee, service, schedule, tomorrow):
        post_booking(client, service, employee, time='09:00', date=tomorrow)
        assert Appointment.objects.get().client.phone == '123456789'

    def test_panel_booking(self, owner_client, employee, service, tomorrow, anna):
        owner_client.post(
            reverse('panel:appointment_create'),
            create_data(service, tomorrow, 10, employee=employee.pk, client_phone='600 100 200'),
        )
        assert Appointment.objects.get().client == anna


@pytest.mark.django_db
class TestImportMigration:
    def test_one_client_per_phone_newest_name_wins(self, employee, service, tomorrow):
        older = make_appointment(employee, service, tomorrow, 10)
        newer = make_appointment(employee, service, tomorrow, 12)
        Appointment.objects.filter(pk=older.pk).update(client=None, client_name='Ania', client_phone='+48123456789')
        Appointment.objects.filter(pk=newer.pk).update(client=None, client_name='Anna Nowak', client_email='')
        Client.objects.all().delete()

        import_migration.import_clients(django_apps, None)

        client = Client.objects.get()
        assert client.name == 'Anna Nowak'
        assert client.email == 'klient@test.pl'  # the older appointment had one
        assert set(client.appointments.all()) == {older, newer}
        assert client.created_at == min(older.created_at, newer.created_at)


@pytest.mark.django_db
class TestPanelClients:
    def test_list_search_by_name_and_phone_in_any_format(self, owner_client, anna):
        Client.objects.create(name='Ewa Lis', phone='700800900')
        url = reverse('panel:client_list')
        for q in ('nowak', '600 100', '+48600100200', 'anna@'):
            html = owner_client.get(url, {'q': q}).content.decode()
            assert 'Anna Nowak' in html and 'Ewa Lis' not in html, q

    def test_card_shows_upcoming_and_past_visits(self, owner_client, anna, employee, service, tomorrow):
        visit = make_appointment(employee, service, tomorrow, 10)
        Appointment.objects.filter(pk=visit.pk).update(client=anna)
        html = owner_client.get(reverse('panel:client_detail', args=[anna.pk])).content.decode()
        assert 'Alergia na lateks' in html
        assert f'{tomorrow:%d.%m.%Y}, 10:00: {service}' in html
        assert 'Jeszcze nie było wizyt.' in html

    def test_add_client(self, owner_client):
        response = owner_client.post(
            reverse('panel:client_create'), {'name': 'Ewa Lis', 'phone': '+48 700 800 900', 'email': '', 'notes': ''}
        )
        client = Client.objects.get()
        assert response.status_code == 302
        assert client.phone == '700800900'

    @pytest.mark.parametrize(
        ('phone', 'error'), [('600-100-200', 'Ten numer ma już klientka Anna Nowak.'), ('123', 'Podaj pełny numer')]
    )
    def test_duplicate_or_short_phone_is_refused(self, owner_client, anna, phone, error):
        response = owner_client.post(
            reverse('panel:client_create'), {'name': 'Ktoś', 'phone': phone, 'email': '', 'notes': ''}
        )
        assert error in response.content.decode()
        assert Client.objects.count() == 1

    def test_editing_keeps_own_phone(self, owner_client, anna):
        owner_client.post(
            reverse('panel:client_update', args=[anna.pk]),
            {'name': 'Anna Nowak', 'phone': '600100200', 'email': '', 'notes': 'Woli rano'},
        )
        anna.refresh_from_db()
        assert anna.notes == 'Woli rano'

    def test_search_suggestions(self, owner_client, anna):
        response = owner_client.get(reverse('panel:client_search'), {'q': '600'})
        assert json.loads(response.content) == {
            'clients': [
                {'name': 'Anna Nowak', 'phone': '600100200', 'phone_display': '600 100 200', 'email': 'anna@test.pl'}
            ]
        }
        assert json.loads(owner_client.get(reverse('panel:client_search'), {'q': 'a'}).content) == {'clients': []}

    def test_new_appointment_from_the_card_is_prefilled(self, owner_client, anna):
        form = owner_client.get(reverse('panel:appointment_create'), {'client': anna.pk}).context['form']
        assert form.initial['client_name'] == 'Anna Nowak'
        assert form.initial['client_phone'] == '600100200'

    def test_employee_has_no_access(self, client, employee_user, anna):
        client.force_login(employee_user)
        for url in (
            reverse('panel:client_list'),
            reverse('panel:client_detail', args=[anna.pk]),
            reverse('panel:client_search') + '?q=anna',
        ):
            assert client.get(url).status_code == 403
        form = client.get(reverse('panel:appointment_create'), {'client': anna.pk}).context['form']
        assert 'client_name' not in form.initial
