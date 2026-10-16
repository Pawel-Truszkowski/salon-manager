import datetime

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings.forms import BookingForm
from apps.bookings.utils import get_available_slots
from apps.panel.forms import AppointmentCreateForm, ServiceForm
from apps.services.models import Service, ServiceCategory
from tests.conftest import make_appointment

LIST_URL = reverse('panel:service_list')
CREATE_URL = reverse('panel:service_create')


def in_days(days):
    return timezone.localdate() + datetime.timedelta(days=days)


def toggle_url(service):
    return reverse('panel:service_toggle_active', args=[service.pk])


def turn_off(service):
    service.is_active = False
    service.save(update_fields=['is_active'])


def service_data(category, **overrides):
    return {
        'category': category.pk,
        'name': 'Pedicure',
        'description': '',
        'price': '120.00',
        'duration': 60,
    } | overrides


@pytest.fixture
def other_category_service(db):
    category = ServiceCategory.objects.create(name='Depilacja woskiem', slug='depilacja-woskiem')
    return Service.objects.create(name='Depilacja nóg', category=category, price='90.00', duration=45)


@pytest.fixture
def owner_client(client, owner_user):
    client.force_login(owner_user)
    return client


@pytest.mark.django_db
class TestServiceForm:
    def test_valid_service(self, category):
        assert ServiceForm(data=service_data(category)).is_valid()

    @pytest.mark.parametrize(
        ('duration', 'message'),
        [(0, 'dłuższy niż 0'), (-15, 'dłuższy niż 0'), (8 * 60 + 15, 'najwyżej 8 godzin'), (50, 'wielokrotnością 15')],
    )
    def test_rejects_bad_duration(self, category, duration, message):
        form = ServiceForm(data=service_data(category, duration=duration))

        assert not form.is_valid()
        assert message in form.errors['duration'][0]

    @pytest.mark.parametrize('duration', [15, 45, 8 * 60])
    def test_accepts_durations_on_the_15_minute_grid(self, category, duration):
        assert ServiceForm(data=service_data(category, duration=duration)).is_valid()

    def test_rejects_negative_price(self, category):
        form = ServiceForm(data=service_data(category, price='-1'))

        assert not form.is_valid()
        assert 'price' in form.errors

    def test_category_is_required(self, category):
        data = service_data(category) | {'category': ''}

        assert not ServiceForm(data=data).is_valid()


@pytest.mark.django_db
class TestServiceViews:
    def test_owner_sees_services_grouped(self, owner_client, service, service_short):
        response = owner_client.get(LIST_URL)

        assert response.status_code == 200
        assert set(response.context['services']) == {service, service_short}

    def test_one_tab_per_category(self, owner_client, service, other_category_service):
        content = owner_client.get(LIST_URL).content.decode()

        for slug in (service.category.slug, other_category_service.category.slug):
            assert f'data-hash="{slug}"' in content
            assert f'id="pane-{slug}"' in content

    def test_long_description_is_shortened_with_full_text_on_hover(self, owner_client, service):
        service.description = 'Bardzo długi opis zabiegu. ' * 10
        service.save()

        content = owner_client.get(LIST_URL).content.decode()

        assert f'title="{service.description}"' in content
        assert f'>{service.description[:89]}…<' in content

    def test_toggle_returns_to_the_category_tab(self, owner_client, service):
        response = owner_client.post(toggle_url(service))

        assert response.url == f'{LIST_URL}#{service.category.slug}'

    def test_owner_adds_service(self, owner_client, category):
        response = owner_client.post(CREATE_URL, service_data(category), follow=True)

        # back on the new service's category tab
        assert response.redirect_chain == [(f'{LIST_URL}#{category.slug}', 302)]
        assert Service.objects.get(name='Pedicure').duration == 60
        assert 'Zespół' in response.content.decode()  # the hint to assign it to specialists

    def test_owner_edits_service(self, owner_client, service, category):
        owner_client.post(
            reverse('panel:service_update', args=[service.pk]), service_data(category, name='Manicure hybrydowy')
        )

        service.refresh_from_db()
        assert service.name == 'Manicure hybrydowy'

    @pytest.mark.parametrize('url_name', ['service_list', 'service_create'])
    def test_employee_has_no_access(self, client, employee_user, url_name):
        client.force_login(employee_user)

        assert client.get(reverse(f'panel:{url_name}')).status_code == 403


@pytest.mark.django_db
class TestServiceToggleActive:
    def test_turns_off_service_without_upcoming_appointments(self, owner_client, service):
        owner_client.post(toggle_url(service))

        service.refresh_from_db()
        assert not service.is_active

    def test_upcoming_appointment_blocks(self, owner_client, employee, service, settings):
        settings.TIME_ZONE = 'Europe/Warsaw'
        make_appointment(employee, service, in_days(2), 10)

        response = owner_client.post(toggle_url(service), follow=True)

        service.refresh_from_db()
        assert service.is_active
        assert f'najbliższa {in_days(2):%d.%m.%Y} 10:00' in response.content.decode()

    def test_turns_back_on(self, owner_client, service):
        turn_off(service)

        owner_client.post(toggle_url(service))

        service.refresh_from_db()
        assert service.is_active

    def test_get_is_not_allowed(self, owner_client, service):
        assert owner_client.get(toggle_url(service)).status_code == 405


@pytest.mark.django_db
class TestInactiveServiceEverywhere:
    def test_has_no_free_slots(self, employee, service, tomorrow):
        turn_off(service)

        assert get_available_slots(employee, tomorrow, service) == []

    def test_hidden_from_public_api_and_home_page(self, client, service, service_short):
        turn_off(service)

        assert [s['id'] for s in client.get(reverse('api-services')).json()] == [service_short.pk]
        assert list(client.get(reverse('home')).context['services']) == [service_short]

    def test_public_slots_api_rejects_it(self, client, employee, service, tomorrow):
        turn_off(service)
        params = {'date': tomorrow.isoformat(), 'service': service.pk}

        assert client.get(reverse('api-available-slots'), params).status_code == 400

    def test_booking_and_panel_forms_skip_it(self, employee, service, service_short):
        turn_off(service)

        assert list(BookingForm().fields['service'].queryset) == [service_short]
        assert list(AppointmentCreateForm(is_owner=True).fields['service'].queryset) == [service_short]
        # an employee only offers her own services, and only active ones
        employee.services.add(service_short)
        assert list(AppointmentCreateForm(is_owner=False, employee=employee).fields['service'].queryset) == [
            service_short
        ]
