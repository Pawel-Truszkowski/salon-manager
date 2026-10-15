import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.services.models import TimeBlock
from tests.conftest import make_time_block

LIST_URL = reverse('panel:time_block_list')
CREATE_URL = reverse('panel:time_block_create')


def in_days(days):
    return timezone.localdate() + datetime.timedelta(days=days)


def block_data(date, start='10:00', end='12:00', **extra):
    data = {'date': date.isoformat(), 'start_time': start, 'end_time': end, 'reason': 'urlop'}
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


@pytest.mark.django_db
class TestTimeBlockList:
    def test_employee_sees_only_her_own_blocks(self, employee_client, employee, other_employee):
        make_time_block(employee, in_days(1), 10, 12, reason='moja przerwa')
        make_time_block(other_employee, in_days(1), 10, 12, reason='cudzy urlop')

        response = employee_client.get(LIST_URL)

        assert response.status_code == 200
        assert [block.reason for block in response.context['time_blocks']] == ['moja przerwa']

    def test_owner_sees_all_blocks(self, owner_client, employee, other_employee):
        make_time_block(employee, in_days(1), 10, 12)
        make_time_block(other_employee, in_days(2), 10, 12)

        response = owner_client.get(LIST_URL)

        assert len(response.context['time_blocks']) == 2

    def test_past_blocks_are_hidden(self, employee_client, employee):
        make_time_block(employee, in_days(-1), 10, 12, reason='wczoraj')
        make_time_block(employee, in_days(0), 10, 12, reason='dziś')

        response = employee_client.get(LIST_URL)

        assert [block.reason for block in response.context['time_blocks']] == ['dziś']


@pytest.mark.django_db
class TestTimeBlockCreate:
    def test_employee_block_is_always_assigned_to_her(self, employee_client, employee, other_employee):
        # A forged `employee` field must be ignored — the form doesn't even have it for employees
        response = employee_client.post(CREATE_URL, block_data(in_days(1), employee=other_employee.pk))

        assert response.status_code == 302
        assert TimeBlock.objects.get().employee == employee

    def test_employee_has_no_employee_field(self, employee_client):
        response = employee_client.get(CREATE_URL)

        assert response.status_code == 200
        assert 'employee' not in response.context['form'].fields

    def test_owner_creates_block_for_chosen_employee(self, owner_client, other_employee):
        response = owner_client.post(CREATE_URL, block_data(in_days(3), employee=other_employee.pk))

        assert response.status_code == 302
        assert response.url == LIST_URL
        block = TimeBlock.objects.get()
        assert (block.employee, block.date, block.start_time, block.end_time) == (
            other_employee,
            in_days(3),
            datetime.time(10),
            datetime.time(12),
        )

    @pytest.mark.parametrize(
        ('data', 'field'),
        [
            (block_data(in_days(1), start='12:00', end='10:00'), 'end_time'),
            (block_data(in_days(1), start='10:00', end='10:00'), 'end_time'),
            (block_data(in_days(-1)), 'date'),
        ],
        ids=['end-before-start', 'zero-length', 'past-date'],
    )
    def test_invalid_block_is_rejected(self, employee_client, data, field):
        response = employee_client.post(CREATE_URL, data)

        assert response.status_code == 200
        assert field in response.context['form'].errors
        assert not TimeBlock.objects.exists()


@pytest.mark.django_db
class TestTimeBlockDelete:
    def url(self, block):
        return reverse('panel:time_block_delete', args=[block.pk])

    def test_employee_deletes_her_own_block(self, employee_client, employee):
        block = make_time_block(employee, in_days(1), 10, 12)

        response = employee_client.post(self.url(block))

        assert response.status_code == 302
        assert response.url == LIST_URL
        assert not TimeBlock.objects.exists()

    def test_employee_cannot_delete_someone_elses_block(self, employee_client, other_employee):
        block = make_time_block(other_employee, in_days(1), 10, 12)

        response = employee_client.post(self.url(block))

        assert response.status_code == 404
        assert TimeBlock.objects.filter(pk=block.pk).exists()

    def test_owner_deletes_any_block(self, owner_client, other_employee):
        block = make_time_block(other_employee, in_days(1), 10, 12)

        assert owner_client.post(self.url(block)).status_code == 302
        assert not TimeBlock.objects.exists()

    def test_get_does_not_delete(self, employee_client, employee):
        block = make_time_block(employee, in_days(1), 10, 12)

        response = employee_client.get(self.url(block))

        assert response.status_code == 405
        assert TimeBlock.objects.filter(pk=block.pk).exists()


@pytest.mark.django_db
def test_user_without_role_gets_403(client, plain_user):
    client.force_login(plain_user)

    assert client.get(LIST_URL).status_code == 403
    assert client.get(CREATE_URL).status_code == 403
