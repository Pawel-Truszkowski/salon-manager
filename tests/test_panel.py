import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from apps.accounts.roles import OWNER_GROUP, get_employee, has_panel_access, is_owner
from apps.bookings.models import Appointment
from apps.services.models import Employee

User = get_user_model()


@pytest.fixture
def owner_user(db):
    user = User.objects.create_user(username='wlascicielka', password='haslo-123!', email='owner@salon.pl')
    user.groups.add(Group.objects.get(name=OWNER_GROUP))
    return user


@pytest.fixture
def employee_user(employee):
    user = User.objects.create_user(username='anna', password='haslo-123!', email='anna@salon.pl')
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
    return User.objects.create_user(username='klient', password='haslo-123!')


def make_today_appointment(employee, service, hour, client_name, status=Appointment.Status.CONFIRMED):
    dt = timezone.make_aware(datetime.datetime.combine(timezone.localdate(), datetime.time(hour, 0)))
    return Appointment.objects.create(
        service=service,
        employee=employee,
        date_time=dt,
        status=status,
        client_name=client_name,
        client_email='klient@test.pl',
        client_phone='123456789',
    )


class TestRoles:
    def test_owner_group_is_created_by_migration(self, db):
        assert Group.objects.filter(name=OWNER_GROUP).exists()

    def test_owner(self, owner_user):
        assert is_owner(owner_user)
        assert get_employee(owner_user) is None
        assert has_panel_access(owner_user)

    def test_superuser_counts_as_owner(self, db):
        admin = User.objects.create_superuser(username='dev', password='x', email='dev@x.pl')
        assert is_owner(admin)

    def test_employee(self, employee_user, employee):
        assert not is_owner(employee_user)
        assert get_employee(employee_user) == employee
        assert has_panel_access(employee_user)

    def test_owner_can_also_be_employee(self, owner_user, employee):
        employee.user = owner_user
        employee.save()
        assert is_owner(owner_user)
        assert get_employee(owner_user) == employee

    def test_user_without_role(self, plain_user):
        assert not has_panel_access(plain_user)

    def test_anonymous(self):
        from django.contrib.auth.models import AnonymousUser

        assert not has_panel_access(AnonymousUser())


class TestPanelAccess:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse('panel:dashboard'))
        assert response.status_code == 302
        assert response.url.startswith(reverse('panel:login'))

    def test_user_without_role_gets_403(self, client, plain_user):
        client.force_login(plain_user)
        assert client.get(reverse('panel:dashboard')).status_code == 403

    def test_owner_can_open_dashboard(self, client, owner_user):
        client.force_login(owner_user)
        assert client.get(reverse('panel:dashboard')).status_code == 200

    def test_employee_can_open_dashboard(self, client, employee_user):
        client.force_login(employee_user)
        assert client.get(reverse('panel:dashboard')).status_code == 200


class TestDashboardScoping:
    def test_employee_sees_only_own_appointments(self, client, employee_user, employee, other_employee, service):
        own = make_today_appointment(employee, service, 10, 'Moja Klientka')
        make_today_appointment(other_employee, service, 11, 'Cudza Klientka')

        client.force_login(employee_user)
        response = client.get(reverse('panel:dashboard'))

        assert list(response.context['today_appointments']) == [own]
        assert 'Cudza Klientka' not in response.content.decode()

    def test_owner_sees_all_appointments(self, client, owner_user, employee, other_employee, service):
        make_today_appointment(employee, service, 10, 'Moja Klientka')
        make_today_appointment(other_employee, service, 11, 'Cudza Klientka')

        client.force_login(owner_user)
        response = client.get(reverse('panel:dashboard'))

        assert len(response.context['today_appointments']) == 2

    def test_cancelled_appointments_hidden_from_today(self, client, owner_user, employee, service):
        make_today_appointment(employee, service, 10, 'Anulowana', status=Appointment.Status.CANCELLED)

        client.force_login(owner_user)
        response = client.get(reverse('panel:dashboard'))

        assert len(response.context['today_appointments']) == 0


class TestAuthViews:
    @pytest.mark.parametrize('url_name', ['panel:login', 'panel:password_reset', 'panel:password_reset_done'])
    def test_auth_pages_render(self, client, db, url_name):
        assert client.get(reverse(url_name)).status_code == 200

    def test_login_redirects_to_dashboard(self, client, owner_user):
        response = client.post(reverse('panel:login'), {'username': 'wlascicielka', 'password': 'haslo-123!'})
        assert response.status_code == 302
        assert response.url == reverse('panel:dashboard')

    def test_logout_requires_post_and_redirects_to_login(self, client, owner_user):
        client.force_login(owner_user)
        response = client.post(reverse('panel:logout'))
        assert response.status_code == 302
        assert response.url == reverse('panel:login')

    def test_password_reset_sends_email_with_panel_link(self, client, owner_user, mailoutbox):
        response = client.post(reverse('panel:password_reset'), {'email': 'owner@salon.pl'})

        assert response.status_code == 302
        assert len(mailoutbox) == 1
        assert '/panel/password-reset/' in mailoutbox[0].body
