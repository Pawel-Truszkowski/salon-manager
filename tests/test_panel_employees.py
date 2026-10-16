import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings.forms import BookingForm
from apps.bookings.models import Appointment
from apps.bookings.utils import find_available_specialist, get_available_slots
from apps.panel.forms import AppointmentCreateForm, EmployeeForm, TimeBlockForm
from apps.services.models import Employee
from tests.conftest import make_appointment

LIST_URL = reverse('panel:employee_list')
CREATE_URL = reverse('panel:employee_create')


def in_days(days):
    return timezone.localdate() + datetime.timedelta(days=days)


def update_url(employee):
    return reverse('panel:employee_update', args=[employee.pk])


@pytest.fixture
def owner_client(client, owner_user):
    client.force_login(owner_user)
    return client


@pytest.fixture
def employee_client(client, employee_user):
    client.force_login(employee_user)
    return client


@pytest.mark.django_db
class TestEmployeeForm:
    def test_bio_is_optional(self, service):
        form = EmployeeForm(data={'first_name': 'Ola', 'services': [service.pk]})

        assert form.is_valid(), form.errors

    def test_at_least_one_service_is_required(self):
        form = EmployeeForm(data={'first_name': 'Ola'})

        assert not form.is_valid()
        assert 'services' in form.errors

    def test_service_checkboxes_get_bootstrap_check_class(self):
        assert 'form-check-input' in EmployeeForm().fields['services'].widget.attrs['class']

    def test_editing_keeps_the_legacy_email(self, employee, service):
        # `email` is not on the form; it must not be wiped (it seeds the panel invitations later)
        form = EmployeeForm(instance=employee, data={'first_name': 'Anna', 'services': [service.pk]})
        form.save()

        employee.refresh_from_db()
        assert employee.email == 'anna@salon.pl'


@pytest.mark.django_db
class TestEmployeeViews:
    def test_owner_sees_the_team(self, owner_client, employee, other_employee):
        response = owner_client.get(LIST_URL)

        assert response.status_code == 200
        assert list(response.context['employees']) == [employee, other_employee]

    def test_owner_adds_employee_with_services(self, owner_client, service, service_short):
        response = owner_client.post(
            CREATE_URL,
            {'first_name': 'Ola', 'last_name': 'Nowak', 'bio': '', 'services': [service.pk, service_short.pk]},
            follow=True,
        )

        assert response.redirect_chain == [(LIST_URL, 302)]
        ola = Employee.objects.get(first_name='Ola')
        assert set(ola.services.all()) == {service, service_short}
        assert 'Dodano specjalistkę' in response.content.decode()

    def test_owner_edits_employee_services(self, owner_client, employee, service, service_short):
        owner_client.post(update_url(employee), {'first_name': 'Ania', 'services': [service_short.pk]})

        employee.refresh_from_db()
        assert employee.first_name == 'Ania'
        assert list(employee.services.all()) == [service_short]

    def test_invalid_form_is_shown_again(self, owner_client):
        response = owner_client.post(CREATE_URL, {'first_name': ''})

        assert response.status_code == 200
        assert not Employee.objects.exists()

    @pytest.mark.parametrize('url_name', ['employee_list', 'employee_create'])
    def test_employee_cannot_manage_the_team(self, employee_client, url_name):
        assert employee_client.get(reverse(f'panel:{url_name}')).status_code == 403

    def test_employee_cannot_edit_herself(self, employee_client, employee):
        assert employee_client.post(update_url(employee), {'first_name': 'X'}).status_code == 403

    def test_team_link_shown_for_owner(self, owner_client):
        content = owner_client.get(reverse('panel:dashboard')).content.decode()

        assert LIST_URL in content
        assert 'Właścicielka</span>' in content

    def test_team_link_hidden_for_employee(self, employee_client):
        assert LIST_URL not in employee_client.get(reverse('panel:dashboard')).content.decode()


def toggle_url(employee):
    return reverse('panel:employee_toggle_active', args=[employee.pk])


def deactivate(employee):
    employee.is_active = False
    employee.save(update_fields=['is_active'])


@pytest.mark.django_db
class TestEmployeeToggleActive:
    def test_deactivates_employee_without_upcoming_appointments(self, owner_client, employee):
        response = owner_client.post(toggle_url(employee), follow=True)

        assert response.redirect_chain == [(LIST_URL, 302)]
        employee.refresh_from_db()
        assert not employee.is_active
        assert 'nieaktywna' in response.content.decode()

    def test_upcoming_appointment_blocks_and_shows_local_time(self, owner_client, employee, service, settings):
        settings.TIME_ZONE = 'Europe/Warsaw'  # tests run in UTC, which would hide a missing localtime()
        make_appointment(employee, service, in_days(3), 10)
        make_appointment(employee, service, in_days(5), 12)

        response = owner_client.post(toggle_url(employee), follow=True)

        employee.refresh_from_db()
        assert employee.is_active
        content = response.content.decode()
        assert f'(2), najbliższa {in_days(3):%d.%m.%Y} 10:00' in content

    @pytest.mark.parametrize('status', [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED])
    def test_closed_appointments_do_not_block(self, owner_client, employee, service, status):
        make_appointment(employee, service, in_days(3), 10, status=status)

        owner_client.post(toggle_url(employee))

        employee.refresh_from_db()
        assert not employee.is_active

    def test_past_appointments_do_not_block(self, owner_client, employee, service):
        make_appointment(employee, service, in_days(-3), 10)

        owner_client.post(toggle_url(employee))

        employee.refresh_from_db()
        assert not employee.is_active

    def test_reactivates(self, owner_client, employee):
        deactivate(employee)

        owner_client.post(toggle_url(employee))

        employee.refresh_from_db()
        assert employee.is_active

    def test_employee_cannot_toggle(self, employee_client, other_employee):
        assert employee_client.post(toggle_url(other_employee)).status_code == 403

    def test_get_is_not_allowed(self, owner_client, employee):
        assert owner_client.get(toggle_url(employee)).status_code == 405

    def test_inactive_are_listed_last(self, owner_client, employee, other_employee):
        deactivate(employee)  # "Anna" would sort first by name

        assert list(owner_client.get(LIST_URL).context['employees']) == [other_employee, employee]


@pytest.mark.django_db
class TestInactiveEmployeeEverywhere:
    """A deactivated employee disappears from booking and pickers but keeps her history."""

    def test_has_no_free_slots(self, employee, service, tomorrow):
        assert get_available_slots(employee, tomorrow, service)
        deactivate(employee)

        assert get_available_slots(employee, tomorrow, service) == []

    def test_is_not_auto_assigned(self, employee, service, tomorrow):
        deactivate(employee)
        date_time = timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(10)))

        assert find_available_specialist(service, date_time) is None

    def test_is_hidden_from_public_api_and_home_page(self, client, employee, other_employee):
        deactivate(employee)

        assert [e['id'] for e in client.get(reverse('api-employees')).json()] == [other_employee.pk]
        assert list(client.get(reverse('home')).context['employees']) == [other_employee]

    def test_public_slots_api_treats_her_as_unknown(self, client, employee, service, tomorrow):
        deactivate(employee)
        params = {'date': tomorrow.isoformat(), 'service': service.pk, 'employee': employee.pk}

        assert client.get(reverse('api-available-slots'), params).status_code == 404

    def test_website_booking_form_rejects_her(self, employee, service, tomorrow):
        deactivate(employee)
        data = {
            'service': service.pk,
            'employee': employee.pk,
            'client_name': 'Jan',
            'client_phone': '123456789',
            'client_email': 'jan@test.pl',
            'date': tomorrow.isoformat(),
            'time': '10:00',
        }

        form = BookingForm(data=data)

        assert not form.is_valid()
        assert 'employee' in form.errors

    def test_panel_pickers_skip_her(self, employee, other_employee):
        deactivate(employee)

        assert list(TimeBlockForm(is_owner=True).fields['employee'].queryset) == [other_employee]
        assert list(AppointmentCreateForm(is_owner=True).fields['employee'].queryset) == [other_employee]

    def test_loses_panel_access(self, employee_client, employee):
        deactivate(employee)

        assert employee_client.get(reverse('panel:dashboard')).status_code == 403

    def test_her_appointments_stay_in_the_history(self, owner_client, employee, service):
        appointment = make_appointment(employee, service, in_days(-3), 10, status=Appointment.Status.COMPLETED)
        deactivate(employee)

        response = owner_client.get(reverse('panel:appointment_detail', args=[appointment.pk]))

        assert response.status_code == 200
        assert employee in owner_client.get(reverse('panel:appointment_list')).context['employees']
