"""Price list migration (0013), "od" prices, price list tabs markup and the floor/elevator info."""

import importlib
from decimal import Decimal

import pytest
from django.apps import apps as django_apps

from apps.bookings.models import Appointment
from apps.services.models import Employee, Service, ServiceCategory
from tests.conftest import make_appointment
from tests.test_views import home_html

catalog_migration = importlib.import_module('apps.services.migrations.0013_catalog')


def apply_catalog():
    # The models of the migration's state are the current ones, so the live registry stands in for it
    catalog_migration.apply_catalog(django_apps, None)


@pytest.fixture
def lashes(db):
    return ServiceCategory.objects.create(name='Rzęsy i brwi', slug='rzesy-i-brwi')


@pytest.fixture
def paulina(db):
    return Employee.objects.create(first_name='Paulina', email='paulina@salon.pl')


@pytest.mark.django_db
class TestCatalogMigration:
    def test_fresh_database_stays_empty(self):
        apply_catalog()
        assert not Service.objects.exists()

    def test_lamination_is_removed_and_the_rest_is_kept(self, lashes, paulina):
        old = Service.objects.create(name='Laminacja rzęs', category=lashes, price='100', duration=60)
        henna = Service.objects.create(name='Henna rzęs', category=lashes, price='25', duration=30)
        paulina.services.add(old, henna)
        apply_catalog()
        assert not Service.objects.filter(name__startswith='Laminacja').exists()
        henna.refresh_from_db()
        assert henna.price == Decimal('30.00')  # production price
        assert henna.description.startswith('Henna rzęs')

    def test_booked_lamination_is_only_hidden(self, lashes, paulina, tomorrow):
        old = Service.objects.create(name='Laminacja rzęs', category=lashes, price='100', duration=60)
        make_appointment(paulina, old, tomorrow, hour=10)
        apply_catalog()
        old.refresh_from_db()
        assert old.is_active is False
        assert Appointment.objects.get().service == old

    def test_old_names_are_renamed_not_duplicated(self, lashes):
        wax = ServiceCategory.objects.create(name='Depilacja woskiem', slug='depilacja-woskiem')
        tora = Service.objects.create(name='Tora', category=wax, price='80', duration=30)
        apply_catalog()
        tora.refresh_from_db()
        assert tora.name == 'Tors'
        assert not Service.objects.filter(name='Tora').exists()
        assert Service.objects.filter(name__startswith='Mezoterapia mikroigłowa (twarz)').exists()

    def test_laser_services_need_the_laser_and_go_to_active_staff(self, lashes, paulina):
        Service.objects.create(name='Henna rzęs', category=lashes, price='30', duration=30)
        retired = Employee.objects.create(first_name='Wiola', email='wiola@salon.pl', is_active=False)
        apply_catalog()
        laser = Service.objects.filter(category__slug='depilacja-laserowa')
        assert laser.count() == 12
        assert all(s.required_equipment.name == 'LightSheer DUET' for s in laser)
        bikini = laser.get(name='Depilacja laserowa – bikini')
        assert bikini.price_label == 'od 170 zł'
        assert list(bikini.employees.all()) == [paulina]
        assert not retired.services.exists()

    def test_running_twice_changes_nothing(self, lashes, paulina):
        Service.objects.create(name='Henna rzęs', category=lashes, price='30', duration=30)
        apply_catalog()
        before = list(Service.objects.values_list('pk', 'name', 'price', 'description').order_by('pk'))
        apply_catalog()
        assert list(Service.objects.values_list('pk', 'name', 'price', 'description').order_by('pk')) == before


class TestPriceLabel:
    @pytest.mark.parametrize(
        ('price', 'is_from', 'label'),
        [('170', True, 'od 170 zł'), ('170', False, '170 zł'), ('0', True, 'bezpłatnie')],
    )
    def test_label(self, price, is_from, label):
        assert Service(price=Decimal(price), price_is_from=is_from).price_label == label


@pytest.mark.django_db
class TestWebsite:
    def test_price_list_categories_are_tab_targets(self, client, service):
        html = home_html(client)
        # script.js turns the index links into tabs over the sections with these ids
        assert f'href="#{service.category.slug}"' in html
        assert f'id="{service.category.slug}"' in html

    def test_lamination_is_not_advertised(self, client):
        assert 'laminuj' not in home_html(client)

    def test_floor_and_elevator(self, client):
        html = home_html(client)
        assert 'Salon jest na 1. piętrze. W budynku jest winda.' in html
        assert 'Gdzie dokładnie jest salon?' in html  # FAQ

    def test_confirmation_email_tells_the_floor(self, employee, service, tomorrow, mailoutbox):
        make_appointment(employee, service, tomorrow, hour=10)
        client_mail = next(m for m in mailoutbox if m.to == ['klient@test.pl'])
        assert '1. piętro, w budynku jest winda' in client_mail.alternatives[0][0]
