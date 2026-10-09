import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Appointment
from apps.services.models import Schedule
from tests.conftest import make_appointment, make_time_block


def at(date, hour, minute=0):
    return timezone.make_aware(datetime.datetime.combine(date, datetime.time(hour, minute)))


def give_schedule(employee, date, start=9, end=17):
    Schedule.objects.create(employee=employee, date=date, start_time=datetime.time(start), end_time=datetime.time(end))


def create_data(service, date, hour, **extra):
    data = {
        'service': service.pk,
        'date': date.isoformat(),
        'time': f'{hour:02d}:00',
        'client_name': 'Jan Telefon',
        'client_phone': '600100200',
        'client_email': 'jan@test.pl',
        'notes': '',
    }
    data.update(extra)
    return data


@pytest.fixture
def owner_client(client, owner_user):
    client.force_login(owner_user)
    return client


@pytest.fixture
def employee_client(client, employee_user):
    client.force_login(employee_user)
    return client


class TestAppointmentList:
    def test_employee_sees_only_own(self, employee_client, employee, other_employee, service, tomorrow):
        give_schedule(other_employee, tomorrow)
        own = make_appointment(employee, service, tomorrow, 10)
        make_appointment(other_employee, service, tomorrow, 11)

        response = employee_client.get(reverse('panel:appointment_list'))

        assert list(response.context['appointments']) == [own]

    def test_owner_filters(self, owner_client, employee, other_employee, service, tomorrow):
        give_schedule(other_employee, tomorrow)
        pending = make_appointment(employee, service, tomorrow, 10, status=Appointment.Status.PENDING)
        make_appointment(employee, service, tomorrow, 12)
        make_appointment(other_employee, service, tomorrow, 11, status=Appointment.Status.PENDING)

        response = owner_client.get(reverse('panel:appointment_list'), {'status': 'pending', 'employee': employee.pk})

        assert list(response.context['appointments']) == [pending]

    def test_search_by_phone(self, owner_client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 10)
        appt.client_phone = '511222333'
        appt.save()
        make_appointment(employee, service, tomorrow, 12)

        response = owner_client.get(reverse('panel:appointment_list'), {'q': '222'})

        assert list(response.context['appointments']) == [appt]

    def test_past_hidden_by_default(self, owner_client, employee, service):
        yesterday = timezone.localdate() - datetime.timedelta(days=1)
        make_appointment(employee, service, yesterday, 10)

        response = owner_client.get(reverse('panel:appointment_list'))

        assert list(response.context['appointments']) == []


class TestAppointmentDetailAccess:
    def test_employee_gets_404_for_someone_elses(self, employee_client, other_employee, service, tomorrow):
        other_employee.services.add(service)
        appt = make_appointment(other_employee, service, tomorrow, 10)

        assert employee_client.get(reverse('panel:appointment_detail', args=[appt.pk])).status_code == 404

    def test_employee_cannot_act_on_someone_elses(self, employee_client, other_employee, service, tomorrow):
        appt = make_appointment(other_employee, service, tomorrow, 10)

        response = employee_client.post(reverse('panel:appointment_action', args=[appt.pk, 'cancel']))

        assert response.status_code == 404
        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CONFIRMED


class TestAppointmentCreate:
    def test_owner_creates_confirmed_appointment(
        self, owner_client, owner_user, employee, service, tomorrow, mailoutbox
    ):
        response = owner_client.post(
            reverse('panel:appointment_create'), create_data(service, tomorrow, 10, employee=employee.pk)
        )

        appt = Appointment.objects.get()
        assert response.status_code == 302
        assert appt.status == Appointment.Status.CONFIRMED
        assert appt.employee == employee
        assert appt.date_time == at(tomorrow, 10)
        assert appt.updated_by == owner_user
        # Only the "confirmed" e-mail to the client; no "booking received", no salon notification
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ['jan@test.pl']
        assert 'potwierdzona' in mailoutbox[0].subject

    def test_without_email_sends_nothing(self, owner_client, employee, service, tomorrow, mailoutbox):
        owner_client.post(
            reverse('panel:appointment_create'),
            create_data(service, tomorrow, 10, employee=employee.pk, client_email=''),
        )

        assert Appointment.objects.get().client_email == ''
        assert mailoutbox == []

    def test_auto_assigns_free_specialist(self, owner_client, employee, service, tomorrow):
        owner_client.post(reverse('panel:appointment_create'), create_data(service, tomorrow, 10))

        assert Appointment.objects.get().employee == employee

    def test_taken_slot_is_rejected(self, owner_client, employee, service, tomorrow):
        make_appointment(employee, service, tomorrow, 10)

        response = owner_client.post(
            reverse('panel:appointment_create'), create_data(service, tomorrow, 10, employee=employee.pk)
        )

        assert response.status_code == 200
        assert response.context['form'].non_field_errors()
        assert Appointment.objects.count() == 1

    def test_outside_schedule_rejected_without_force(self, owner_client, employee, service, tomorrow):
        response = owner_client.post(
            reverse('panel:appointment_create'), create_data(service, tomorrow, 19, employee=employee.pk)
        )

        assert response.status_code == 200
        assert not Appointment.objects.exists()

    def test_owner_can_force_outside_schedule(self, owner_client, employee, service, tomorrow):
        response = owner_client.post(
            reverse('panel:appointment_create'), create_data(service, tomorrow, 19, employee=employee.pk, force='on')
        )

        assert response.status_code == 302
        assert Appointment.objects.get().date_time == at(tomorrow, 19)

    def test_force_requires_specialist(self, owner_client, employee, service, tomorrow):
        response = owner_client.post(
            reverse('panel:appointment_create'), create_data(service, tomorrow, 19, force='on')
        )

        assert response.status_code == 200
        assert not Appointment.objects.exists()

    def test_employee_books_for_herself_and_cannot_force(
        self, employee_client, employee, other_employee, service, tomorrow
    ):
        give_schedule(other_employee, tomorrow)
        # Tries to book for someone else and to bypass the schedule — both ignored
        response = employee_client.post(
            reverse('panel:appointment_create'),
            create_data(service, tomorrow, 19, employee=other_employee.pk, force='on'),
        )
        assert response.status_code == 200
        assert not Appointment.objects.exists()

        employee_client.post(
            reverse('panel:appointment_create'), create_data(service, tomorrow, 10, employee=other_employee.pk)
        )
        assert Appointment.objects.get().employee == employee

    def test_specialist_must_perform_service(self, owner_client, other_employee, service_short, tomorrow):
        give_schedule(other_employee, tomorrow)

        response = owner_client.post(
            reverse('panel:appointment_create'), create_data(service_short, tomorrow, 10, employee=other_employee.pk)
        )

        assert response.status_code == 200
        assert not Appointment.objects.exists()

    def test_past_rejected(self, owner_client, employee, service):
        yesterday = timezone.localdate() - datetime.timedelta(days=1)

        response = owner_client.post(
            reverse('panel:appointment_create'), create_data(service, yesterday, 10, employee=employee.pk, force='on')
        )

        assert response.status_code == 200
        assert not Appointment.objects.exists()


class TestAppointmentReschedule:
    def test_form_prefilled_with_current_slot(self, owner_client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 10, minute=30)

        html = owner_client.get(reverse('panel:appointment_reschedule', args=[appt.pk])).content.decode()

        assert f'value="{tomorrow.isoformat()}"' in html
        assert 'value="10:30"' in html

    def test_can_move_within_its_own_slot(self, owner_client, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, 10)
        mailoutbox.clear()  # drop the website-booking e-mails sent on creation

        # 10:00-11:00 -> 10:15-11:15 overlaps the appointment's own current slot
        response = owner_client.post(
            reverse('panel:appointment_reschedule', args=[appt.pk]),
            {'employee': employee.pk, 'date': tomorrow.isoformat(), 'time': '10:15'},
        )

        assert response.status_code == 302
        appt.refresh_from_db()
        assert appt.date_time == at(tomorrow, 10, 15)
        assert len(mailoutbox) == 1
        assert 'Zmiana terminu' in mailoutbox[0].subject

    def test_cannot_move_onto_another_appointment(self, owner_client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 10)
        make_appointment(employee, service, tomorrow, 13)

        response = owner_client.post(
            reverse('panel:appointment_reschedule', args=[appt.pk]),
            {'employee': employee.pk, 'date': tomorrow.isoformat(), 'time': '13:00'},
        )

        assert response.status_code == 200
        appt.refresh_from_db()
        assert appt.date_time == at(tomorrow, 10)

    def test_owner_can_move_to_another_specialist(self, owner_client, employee, other_employee, service, tomorrow):
        give_schedule(other_employee, tomorrow)
        appt = make_appointment(employee, service, tomorrow, 10)

        owner_client.post(
            reverse('panel:appointment_reschedule', args=[appt.pk]),
            {'employee': other_employee.pk, 'date': tomorrow.isoformat(), 'time': '10:00'},
        )

        appt.refresh_from_db()
        assert appt.employee == other_employee

    def test_employee_reschedules_own(self, employee_client, employee_user, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 10)

        employee_client.post(
            reverse('panel:appointment_reschedule', args=[appt.pk]), {'date': tomorrow.isoformat(), 'time': '14:00'}
        )

        appt.refresh_from_db()
        assert appt.date_time == at(tomorrow, 14)
        assert appt.updated_by == employee_user

    def test_cancelled_cannot_be_rescheduled(self, owner_client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 10, status=Appointment.Status.CANCELLED)

        response = owner_client.get(reverse('panel:appointment_reschedule', args=[appt.pk]))

        assert response.status_code == 302


class TestAppointmentActions:
    def test_confirm_pending(self, employee_client, employee_user, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, 10, status=Appointment.Status.PENDING)
        mailoutbox.clear()  # drop the website-booking e-mails sent on creation

        employee_client.post(reverse('panel:appointment_action', args=[appt.pk, 'confirm']))

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CONFIRMED
        assert appt.updated_by == employee_user
        assert len(mailoutbox) == 1

    def test_cancel_by_salon_sends_salon_wording_and_no_salon_notification(
        self, owner_client, employee, service, tomorrow, mailoutbox
    ):
        appt = make_appointment(employee, service, tomorrow, 10)
        mailoutbox.clear()  # drop the website-booking e-mails sent on creation

        owner_client.post(reverse('panel:appointment_action', args=[appt.pk, 'cancel']))

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CANCELLED
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ['klient@test.pl']
        assert 'przez salon' in mailoutbox[0].subject

    def test_cannot_confirm_cancelled(self, owner_client, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, 10, status=Appointment.Status.CANCELLED)
        mailoutbox.clear()  # drop the website-booking e-mails sent on creation

        owner_client.post(reverse('panel:appointment_action', args=[appt.pk, 'confirm']))

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CANCELLED
        assert mailoutbox == []

    def test_complete_confirmed(self, owner_client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 10)

        owner_client.post(reverse('panel:appointment_action', args=[appt.pk, 'complete']))

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.COMPLETED

    def test_unknown_action_changes_nothing(self, owner_client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 10)

        owner_client.post(reverse('panel:appointment_action', args=[appt.pk, 'delete']))

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CONFIRMED

    def test_redirects_to_safe_next_only(self, owner_client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 10, status=Appointment.Status.PENDING)
        url = reverse('panel:appointment_action', args=[appt.pk, 'confirm'])

        assert owner_client.post(url, {'next': '/panel/'}).url == '/panel/'
        appt.status = Appointment.Status.PENDING
        appt.save()
        assert owner_client.post(url, {'next': 'https://evil.example/'}).url == reverse(
            'panel:appointment_detail', args=[appt.pk]
        )


class TestSlotsView:
    def test_returns_free_slots(self, owner_client, employee, service, tomorrow):
        make_appointment(employee, service, tomorrow, 9)
        make_time_block(employee, tomorrow, 12, 13)

        response = owner_client.get(
            reverse('panel:slots'), {'service': service.pk, 'date': tomorrow.isoformat(), 'employee': employee.pk}
        )

        slots = response.json()['slots']
        assert '09:00' not in slots
        assert '10:00' in slots
        assert '12:00' not in slots

    def test_exclude_frees_the_appointments_own_slot(self, owner_client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 9)

        response = owner_client.get(
            reverse('panel:slots'),
            {'service': service.pk, 'date': tomorrow.isoformat(), 'employee': employee.pk, 'exclude': appt.pk},
        )

        assert '09:00' in response.json()['slots']

    def test_employee_only_gets_own_slots(self, employee_client, other_employee, service, tomorrow):
        # Other specialist works 18-20; the employee (09-17) asks for her slots -> must not see 18:00
        give_schedule(other_employee, tomorrow, 18, 20)

        response = employee_client.get(
            reverse('panel:slots'), {'service': service.pk, 'date': tomorrow.isoformat(), 'employee': other_employee.pk}
        )

        assert '18:00' not in response.json()['slots']
        assert '09:00' in response.json()['slots']

    def test_bad_params(self, owner_client):
        assert owner_client.get(reverse('panel:slots'), {'service': 'x', 'date': 'y'}).status_code == 400


class TestWebsiteBookingStillRequiresEmail:
    def test_booking_form_requires_email(self, employee, service, tomorrow):
        from apps.bookings.forms import BookingForm

        form = BookingForm(
            data={
                'service': service.pk,
                'employee': employee.pk,
                'client_name': 'X',
                'client_phone': '1',
                'client_email': '',
                'date': tomorrow.isoformat(),
                'time': '10:00',
            }
        )

        assert not form.is_valid()
        assert 'client_email' in form.errors

    def test_client_self_cancel_clears_updated_by(self, client, owner_user, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, 10)
        appt.updated_by = owner_user
        appt.save()

        client.post(reverse('cancel_booking', args=[appt.cancellation_token]))

        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CANCELLED
        assert appt.updated_by is None
