import datetime
import pytest
from unittest.mock import Mock

from django.contrib import admin
from django.urls import reverse
from django.utils import timezone

from apps.bookings.admin import AppointmentAdmin
from apps.bookings.models import Appointment
from tests.conftest import make_appointment


@pytest.mark.django_db
class TestConfirmAppointmentsAction:

    def test_confirms_pending_appointments_and_sends_emails(
        self, admin_client, employee, service, tomorrow, mailoutbox
    ):
        pending_1 = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.PENDING)
        pending_2 = make_appointment(employee, service, tomorrow, hour=11, status=Appointment.Status.PENDING)
        mailoutbox.clear()

        response = admin_client.post(
            reverse('admin:bookings_appointment_changelist'),
            {'action': 'confirm_appointments', '_selected_action': [pending_1.pk, pending_2.pk]},
            follow=True,
        )

        assert response.status_code == 200
        pending_1.refresh_from_db()
        pending_2.refresh_from_db()
        assert pending_1.status == Appointment.Status.CONFIRMED
        assert pending_2.status == Appointment.Status.CONFIRMED
        assert len(mailoutbox) == 2

    def test_skips_already_confirmed_appointments(
        self, admin_client, employee, service, tomorrow, mailoutbox
    ):
        already_confirmed = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CONFIRMED)
        mailoutbox.clear()

        response = admin_client.post(
            reverse('admin:bookings_appointment_changelist'),
            {'action': 'confirm_appointments', '_selected_action': [already_confirmed.pk]},
            follow=True,
        )

        assert response.status_code == 200
        assert len(mailoutbox) == 0


@pytest.mark.django_db
class TestAppointmentAdminSaveModel:

    def test_manually_confirming_via_change_form_sends_email(
        self, employee, service, tomorrow, mailoutbox, rf
    ):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.PENDING)
        appt.status = Appointment.Status.CONFIRMED
        mailoutbox.clear()

        model_admin = AppointmentAdmin(Appointment, admin.site)
        request = rf.post(f'/admin/bookings/appointment/{appt.pk}/change/')
        form = Mock(changed_data=['status'])

        model_admin.save_model(request, appt, form, change=True)

        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [appt.client_email]

    def test_creating_appointment_as_confirmed_does_not_send_extra_email(
        self, employee, service, tomorrow, mailoutbox, rf
    ):
        appt = Appointment(
            service=service,
            employee=employee,
            date_time=timezone.make_aware(datetime.datetime.combine(tomorrow, datetime.time(12, 0))),
            status=Appointment.Status.CONFIRMED,
            client_name='Nowy Klient',
            client_email='nowy@test.pl',
            client_phone='987654321',
        )

        model_admin = AppointmentAdmin(Appointment, admin.site)
        request = rf.post('/admin/bookings/appointment/add/')
        form = Mock(changed_data=['service', 'employee', 'date_time', 'status', 'client_name', 'client_email', 'client_phone'])

        model_admin.save_model(request, appt, form, change=False)

        # Creating an appointment still triggers the "new booking" emails via
        # the post_save signal — only the admin's own "wizyta potwierdzona"
        # email (which only fires on an update) must be absent here.
        subjects = [m.subject.lower() for m in mailoutbox]
        assert not any('potwierdzona' in subject for subject in subjects)

    def test_editing_without_changing_status_does_not_send_email(
        self, employee, service, tomorrow, mailoutbox, rf
    ):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CONFIRMED)
        appt.notes = 'Zaktualizowana notatka'
        mailoutbox.clear()

        model_admin = AppointmentAdmin(Appointment, admin.site)
        request = rf.post(f'/admin/bookings/appointment/{appt.pk}/change/')
        form = Mock(changed_data=['notes'])

        model_admin.save_model(request, appt, form, change=True)

        assert len(mailoutbox) == 0
