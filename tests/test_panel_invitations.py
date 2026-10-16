import re

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.panel.forms import InviteEmployeeForm
from apps.panel.invitations import create_invited_account, invitation_url
from apps.services.models import Employee

User = get_user_model()
LIST_URL = reverse('panel:employee_list')


def invite_url(employee):
    return reverse('panel:employee_invite', args=[employee.pk])


def resend_url(employee):
    return reverse('panel:employee_invite_resend', args=[employee.pk])


def link_from(mail):
    """The /panel/invitation/... path from the plain-text body (SITE_URL is http://testserver in tests)."""
    return re.search(r'http://testserver(/panel/invitation/\S+/)', mail.body).group(1)


@pytest.fixture
def owner_client(client, owner_user):
    client.force_login(owner_user)
    return client


@pytest.fixture
def new_employee(service):
    """Active specialist without a panel account, with the legacy e-mail filled in."""
    employee = Employee.objects.create(first_name='Ola', last_name='Nowak', email='Ola@Salon.pl', bio='')
    employee.services.add(service)
    return employee


@pytest.mark.django_db
class TestInviteEmployeeForm:
    def test_normalizes_to_lowercase(self):
        form = InviteEmployeeForm(data={'email': 'Ola@Salon.PL'})

        assert form.is_valid()
        assert form.cleaned_data['email'] == 'ola@salon.pl'

    @pytest.mark.parametrize('field', ['email', 'username'])
    def test_rejects_address_already_used_by_an_account(self, owner_user, field):
        setattr(owner_user, field, 'zajety@salon.pl')
        owner_user.save()

        form = InviteEmployeeForm(data={'email': 'ZAJETY@salon.pl'})

        assert not form.is_valid()
        assert form.errors['email'] == ['Konto z tym adresem już istnieje.']


@pytest.mark.django_db
class TestInviteView:
    def test_prefills_the_legacy_employee_email(self, owner_client, new_employee):
        response = owner_client.get(invite_url(new_employee))

        assert response.status_code == 200
        assert response.context['form'].initial['email'] == 'Ola@Salon.pl'

    def test_creates_passwordless_account_and_sends_the_link(self, owner_client, new_employee, mailoutbox):
        response = owner_client.post(invite_url(new_employee), {'email': 'ola@salon.pl'}, follow=True)

        assert response.redirect_chain == [(LIST_URL, 302)]
        new_employee.refresh_from_db()
        user = new_employee.user
        assert (user.username, user.email, user.first_name, user.last_name) == (
            'ola@salon.pl',
            'ola@salon.pl',
            'Ola',
            'Nowak',
        )
        assert not user.has_usable_password()

        [mail] = mailoutbox
        assert mail.to == ['ola@salon.pl']
        assert '/panel/invitation/' in mail.body
        # no name: it can't be put in the Polish vocative automatically (Ewa -> Ewo)
        assert mail.body.startswith('Dzień dobry,\n')
        assert 'zaproszona' in response.content.decode()

    def test_mail_failure_keeps_the_account_and_says_so(self, owner_client, new_employee, monkeypatch):
        def broken(*args, **kwargs):
            raise ConnectionError('Resend is down')

        monkeypatch.setattr('apps.panel.views.send_invitation', broken)

        response = owner_client.post(invite_url(new_employee), {'email': 'ola@salon.pl'}, follow=True)

        new_employee.refresh_from_db()
        assert new_employee.user is not None
        assert 'nie udało się wysłać' in response.content.decode()

    def test_employee_with_an_account_cannot_be_invited_again(self, owner_client, employee, employee_user):
        response = owner_client.post(invite_url(employee), {'email': 'nowy@salon.pl'})

        assert response.status_code == 302
        assert not User.objects.filter(email='nowy@salon.pl').exists()

    def test_inactive_employee_cannot_be_invited(self, owner_client, new_employee):
        new_employee.is_active = False
        new_employee.save()

        owner_client.post(invite_url(new_employee), {'email': 'ola@salon.pl'})

        assert not User.objects.filter(email='ola@salon.pl').exists()

    def test_employee_cannot_invite(self, client, employee_user, new_employee):
        client.force_login(employee_user)

        assert client.get(invite_url(new_employee)).status_code == 403


@pytest.mark.django_db
class TestAcceptInvitation:
    def test_sets_password_once_then_logs_in(self, client, new_employee, mailoutbox):
        user = create_invited_account(new_employee, 'ola@salon.pl')
        path = invitation_url(user).removeprefix('http://testserver')

        # The view swaps the token for a session marker and redirects to a "set-password" URL
        response = client.get(path, follow=True)
        assert response.context['validlink']
        form_url = response.redirect_chain[-1][0]
        response = client.post(form_url, {'new_password1': 'Bardzo-Trudne-77', 'new_password2': 'Bardzo-Trudne-77'})
        assert response.status_code == 302

        user.refresh_from_db()
        assert user.check_password('Bardzo-Trudne-77')
        # The token hashed the old (unusable) password, so the same link is dead now
        client.logout()
        assert not client.get(path, follow=True).context['validlink']
        # ...and the new account opens her panel
        assert client.login(username='ola@salon.pl', password='Bardzo-Trudne-77')
        assert client.get(reverse('panel:dashboard')).status_code == 200

    def test_link_in_the_mail_works(self, owner_client, client, new_employee, mailoutbox):
        owner_client.post(invite_url(new_employee), {'email': 'ola@salon.pl'})
        owner_client.logout()

        assert client.get(link_from(mailoutbox[0]), follow=True).context['validlink']


@pytest.mark.django_db
class TestResendInvitation:
    def test_resends_while_password_not_set(self, owner_client, new_employee, mailoutbox):
        create_invited_account(new_employee, 'ola@salon.pl')

        owner_client.post(resend_url(new_employee))

        assert [mail.to for mail in mailoutbox] == [['ola@salon.pl']]

    def test_refuses_when_she_already_has_a_password(self, owner_client, employee, employee_user, mailoutbox):
        response = owner_client.post(resend_url(employee), follow=True)

        assert mailoutbox == []
        assert 'nie czeka na zaproszenie' in response.content.decode()

    def test_get_is_not_allowed(self, owner_client, new_employee):
        assert owner_client.get(resend_url(new_employee)).status_code == 405


@pytest.mark.django_db
def test_team_list_shows_invitation_state(owner_client, new_employee, employee, employee_user):
    content = owner_client.get(LIST_URL).content.decode()
    assert invite_url(new_employee) in content  # no account yet -> "Zaproś"
    assert invite_url(employee) not in content  # has an account

    create_invited_account(new_employee, 'ola@salon.pl')
    content = owner_client.get(LIST_URL).content.decode()
    assert 'zaproszona' in content
    assert resend_url(new_employee) in content
