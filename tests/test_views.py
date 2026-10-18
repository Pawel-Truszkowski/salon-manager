import datetime
import json
import re
from decimal import Decimal

import pytest
from django.conf import settings
from django.db import connection
from django.test import Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Appointment
from apps.services.models import Employee, Service, ServiceCategory
from tests.conftest import make_appointment, make_time_block


def future_date():
    return (timezone.now() + datetime.timedelta(days=1)).date()


def post_booking(client, service, employee=None, time='10:00', date=None):
    date = date or future_date()
    data = {
        'service': service.pk,
        'employee': employee.pk if employee else '',
        'client_name': 'Jan Kowalski',
        'client_phone': '123456789',
        'client_email': 'jan@test.pl',
        'date': date.isoformat(),
        'time': time,
        'notes': '',
    }
    return client.post(reverse('submit_booking'), data)


@pytest.mark.django_db
class TestSubmitBookingView:
    def setup_method(self):
        self.client = Client()

    def test_booking_created_successfully(self, employee, service, schedule, tomorrow):
        response = post_booking(self.client, service, employee, time='09:00', date=tomorrow)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['ok'] is True
        assert Appointment.objects.count() == 1

    def test_auto_assigns_specialist_when_none_selected(self, employee, service, schedule, tomorrow):
        response = post_booking(self.client, service, employee=None, time='09:00', date=tomorrow)
        assert response.status_code == 200
        appt = Appointment.objects.get()
        assert appt.employee == employee

    def test_returns_409_on_collision(self, employee, service, schedule, tomorrow):
        make_appointment(employee, service, tomorrow, hour=9, minute=0)
        response = post_booking(self.client, service, employee, time='09:00', date=tomorrow)
        assert response.status_code == 409
        data = json.loads(response.content)
        assert data['ok'] is False

    def test_returns_409_when_time_is_blocked_by_owner(self, employee, service, schedule, tomorrow):
        make_time_block(employee, tomorrow, start_hour=12, end_hour=14)
        response = post_booking(self.client, service, employee, time='12:00', date=tomorrow)
        assert response.status_code == 409
        data = json.loads(response.content)
        assert data['ok'] is False
        assert Appointment.objects.count() == 0

    def test_allows_booking_outside_blocked_range(self, employee, service, schedule, tomorrow):
        make_time_block(employee, tomorrow, start_hour=12, end_hour=14)
        response = post_booking(self.client, service, employee, time='14:00', date=tomorrow)
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['ok'] is True

    def test_returns_400_when_no_specialist_available(self, employee, service, schedule, tomorrow):
        # Fill the only available specialist
        make_appointment(employee, service, tomorrow, hour=9, minute=0)
        # Try to book without selecting specialist (auto-assign should fail)
        response = post_booking(self.client, service, employee=None, time='09:00', date=tomorrow)
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['ok'] is False

    def test_get_method_not_allowed(self, service):
        response = self.client.get(reverse('submit_booking'))
        assert response.status_code == 405

    def test_invalid_form_returns_400(self, service):
        response = self.client.post(reverse('submit_booking'), {})
        assert response.status_code == 400
        data = json.loads(response.content)
        assert data['ok'] is False
        assert 'errors' in data


@pytest.mark.django_db
class TestEmployeesAPI:
    def test_does_not_expose_contact_data(self, client, employee):
        [data] = client.get(reverse('api-employees')).json()

        assert data['first_name'] == employee.first_name
        assert 'email' not in data


@pytest.mark.django_db
class TestAvailableSlotsAPI:
    def setup_method(self):
        self.client = Client()

    def test_returns_slots_for_valid_params(self, employee, service, schedule, tomorrow):
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': tomorrow.isoformat(),
                'service': service.pk,
                'employee': employee.pk,
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['slots']) > 0

    def test_returns_400_without_required_params(self, service):
        response = self.client.get(reverse('api-available-slots'))
        assert response.status_code == 400

    def test_returns_400_for_past_date(self, service):
        past = (timezone.now() - datetime.timedelta(days=1)).date()
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': past.isoformat(),
                'service': service.pk,
            },
        )
        assert response.status_code == 400

    def test_returns_empty_when_no_schedule(self, employee, service):
        # Deliberately no schedule fixture — employee has no working hours on this date
        date_without_schedule = (timezone.now() + datetime.timedelta(days=30)).date()
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': date_without_schedule.isoformat(),
                'service': service.pk,
                'employee': employee.pk,
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data['slots'] == []

    def test_aggregates_slots_from_all_employees_when_no_employee_param(self, employee, service, schedule, tomorrow):
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': tomorrow.isoformat(),
                'service': service.pk,
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['slots']) > 0

    def test_excludes_slots_blocked_by_owner(self, employee, service, schedule, tomorrow):
        make_time_block(employee, tomorrow, start_hour=12, end_hour=14)
        response = self.client.get(
            reverse('api-available-slots'),
            {
                'date': tomorrow.isoformat(),
                'service': service.pk,
                'employee': employee.pk,
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert '12:00' not in data['slots']
        assert '13:00' not in data['slots']
        assert '14:00' in data['slots']


@pytest.mark.django_db
class TestAvailableDatesAPI:
    def setup_method(self):
        self.client = Client()

    def test_returns_date_with_open_schedule(self, employee, service, schedule, tomorrow):
        response = self.client.get(
            reverse('api-available-dates'),
            {
                'service': service.pk,
                'employee': employee.pk,
                'month': f'{tomorrow.year}-{tomorrow.month:02d}',
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert tomorrow.isoformat() in data['dates']

    def test_excludes_date_fully_blocked_by_owner(self, employee, service, schedule, tomorrow):
        # Block the entire working day (09:00-17:00 per the `schedule` fixture)
        make_time_block(employee, tomorrow, start_hour=9, end_hour=17)
        response = self.client.get(
            reverse('api-available-dates'),
            {
                'service': service.pk,
                'employee': employee.pk,
                'month': f'{tomorrow.year}-{tomorrow.month:02d}',
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert tomorrow.isoformat() not in data['dates']

    def test_keeps_date_when_only_partially_blocked(self, employee, service, schedule, tomorrow):
        make_time_block(employee, tomorrow, start_hour=12, end_hour=14)
        response = self.client.get(
            reverse('api-available-dates'),
            {
                'service': service.pk,
                'employee': employee.pk,
                'month': f'{tomorrow.year}-{tomorrow.month:02d}',
            },
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert tomorrow.isoformat() in data['dates']


@pytest.mark.django_db
class TestCancelBookingView:
    def setup_method(self):
        self.client = Client()

    def test_get_shows_confirmation_page_for_cancellable_appointment(self, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CONFIRMED)
        response = self.client.get(reverse('cancel_booking', args=[appt.cancellation_token]))
        assert response.status_code == 200
        assert Appointment.objects.get(pk=appt.pk).status == Appointment.Status.CONFIRMED

    def test_post_cancels_the_appointment(self, employee, service, tomorrow, mailoutbox):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CONFIRMED)
        mailoutbox.clear()
        response = self.client.post(reverse('cancel_booking', args=[appt.cancellation_token]))
        assert response.status_code == 200
        appt.refresh_from_db()
        assert appt.status == Appointment.Status.CANCELLED
        assert len(mailoutbox) == 2

    def test_unknown_token_returns_404(self):
        response = self.client.get(reverse('cancel_booking', args=['00000000-0000-0000-0000-000000000000']))
        assert response.status_code == 404

    def test_post_on_already_cancelled_appointment_does_not_resend_emails(
        self, employee, service, tomorrow, mailoutbox
    ):
        appt = make_appointment(employee, service, tomorrow, hour=10, status=Appointment.Status.CANCELLED)
        mailoutbox.clear()
        response = self.client.post(reverse('cancel_booking', args=[appt.cancellation_token]))
        assert response.status_code == 200
        assert len(mailoutbox) == 0


class TestSelfHostedFonts:
    """Fonts are served from static/ so no visitor IP reaches Google Fonts (GDPR)."""

    @pytest.mark.parametrize('url_name', ['home', 'panel:login'])
    def test_page_uses_local_fonts_only(self, client, db, url_name):
        response = client.get(reverse(url_name))
        assert response.status_code == 200
        assert 'css/fonts.css' in response.content.decode()
        assert 'fonts.googleapis.com' not in response.content.decode()
        assert 'fonts.gstatic.com' not in response.content.decode()

    def test_every_font_face_points_to_an_existing_file(self):
        static_dir = settings.STATICFILES_DIRS[0]
        css = (static_dir / 'css' / 'fonts.css').read_text()
        urls = re.findall(r'url\("\.\./(fonts/[^"]+)"\)', css)
        assert urls
        missing = [u for u in urls if not (static_dir / u).is_file()]
        assert missing == []


class TestMobilePerformance:
    """The public site loads everything from our own domain: no CDN handshake delays the first paint on a phone."""

    def test_home_loads_no_third_party_css_or_js(self, client, db):
        html = home_html(client)
        assert re.findall(r'<link rel="(?:stylesheet|preload)"[^>]+href="https?://', html) == []
        assert re.findall(r'<script[^>]+src="https?://', html) == []
        assert 'bootstrap-icons' not in html  # inline SVG instead of a 128 KB icon font

    def test_scripts_do_not_block_parsing(self, client, db):
        scripts = re.findall(r'<script src="[^"]+"[^>]*>', home_html(client))
        assert scripts
        assert all(' defer' in tag for tag in scripts)

    def test_content_is_in_a_main_landmark(self, client, db):
        html = home_html(client)
        assert html.count('<main') == 1
        assert html.index('<main') < html.index('<h1') < html.index('</main>')

    def test_every_static_file_referenced_by_the_page_exists(self, client, db):
        static_dir = settings.STATICFILES_DIRS[0]
        paths = re.findall(r'(?:href|src)="/static/([^"]+)"', home_html(client))
        assert paths
        assert [p for p in paths if not (static_dir / p).is_file()] == []


class TestHeaderAndHero:
    def test_home_has_exactly_one_h1_with_the_main_phrase(self, client, db):
        html = client.get(reverse('home')).content.decode()
        assert html.count('<h1') == 1
        assert 'Salon kosmetyczny we Wrocławiu' in html

    def test_phone_numbers_are_tel_links(self, client, db):
        html = client.get(reverse('home')).content.decode()
        assert 'href="tel:+48793355756"' in html
        assert 'href="tel:+48792646256"' in html

    def test_hero_does_not_claim_fixed_opening_hours(self, client, db):
        html = client.get(reverse('home')).content.decode()
        assert 'po umówieniu' in html
        assert 'w sercu miasta' not in html

    def test_menu_on_other_pages_links_back_to_home_sections(self, client, employee, service, tomorrow):
        appt = make_appointment(employee, service, tomorrow, hour=10)
        html = client.get(reverse('cancel_booking', args=[appt.cancellation_token])).content.decode()
        assert f'href="{reverse("home")}#cennik"' in html
        assert 'href="#cennik"' not in html


def json_ld_blocks(html):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


class TestSeoMeta:
    def test_title_fits_in_search_results(self, client, db):
        html = client.get(reverse('home')).content.decode()
        title = re.search(r'<title>(.*?)</title>', html, re.S).group(1)
        assert len(title) <= 60

    def test_open_graph_uses_absolute_urls_from_site_url(self, client, db, settings):
        settings.SITE_URL = 'https://example.test/'
        html = client.get(reverse('home')).content.decode()
        assert '<meta property="og:url" content="https://example.test/"' in html
        assert re.search(
            r'<meta property="og:image" content="https://example\.test/static/img/og-salon[^"]*\.jpg"', html
        )
        assert '<link rel="canonical" href="https://example.test/"' in html
        assert 'name="twitter:card" content="summary_large_image"' in html

    def test_salon_json_ld(self, client, db):
        html = client.get(reverse('home')).content.decode()
        (salon,) = [b for b in json_ld_blocks(html) if b['@type'] == 'BeautySalon']
        assert salon['@id'] == 'http://testserver/#salon'
        assert (salon['name'], salon['alternateName']) == ('Royal Beauty Studio Urody', 'Royal Beauty')
        assert salon['foundingDate'] == '2023'
        assert salon['hasMap'] in salon['sameAs']
        assert 'Sunday' in salon['openingHoursSpecification'][0]['dayOfWeek']
        assert 'po wcześniejszym umówieniu' in salon['description']
        assert salon['founder']['name'] == 'Paulina'
        assert salon['priceRange'] != 'PLN'
        assert salon['geo']['latitude']

    def test_robots_txt_points_to_sitemap_on_this_site(self, client, db):
        body = client.get('/robots.txt').content.decode()
        assert 'Sitemap: http://testserver/sitemap.xml' in body
        assert 'Disallow: /panel/' in body


class TestErrorPages:
    def test_404_is_polish_and_links_to_booking(self, client, db, settings):
        settings.DEBUG = False
        response = client.get('/nie-ma-takiej-strony/')
        assert response.status_code == 404
        html = response.content.decode()
        assert 'Nie ma takiej strony' in html
        assert f'href="{reverse("home")}#rezerwacja"' in html

    def test_500_renders_without_request_context(self, rf):
        from django.views.defaults import server_error

        response = server_error(rf.get('/'))
        assert response.status_code == 500
        html = response.content.decode()
        assert 'Coś poszło nie tak' in html
        assert 'href="tel:+48793355756"' in html


class TestImagesAndLinks:
    def test_gallery_images_have_descriptive_alt_text(self, client, db):
        html = client.get(reverse('home')).content.decode()
        alts = re.findall(r'<img [^>]*alt="([^"]*)"', html)
        assert 'Sprzęt' not in alts
        assert 'Kosmetyki' not in alts
        # Only decorative images: the navbar logo (the link next to it has the name as text) and the lightbox
        # placeholder (JS copies the alt in when it opens)
        assert alts.count('') == 2

    def test_navbar_shows_the_full_business_name(self, client, db):
        html = client.get(reverse('home')).content.decode()
        assert '<span class="rb-brand-name">Royal Beauty<span>Studio Urody</span></span>' in html

    def test_external_links_in_new_tab_use_noopener(self, client, db):
        html = client.get(reverse('home')).content.decode()
        for tag in re.findall(r'<a [^>]*target="_blank"[^>]*>', html):
            assert 'noopener' in tag, tag


class TestPriceList:
    """The price list is rendered by Django, so it is in the HTML without JavaScript (search engines, AI crawlers)."""

    def test_services_are_in_the_html(self, client, service):
        service.description = 'Opracowanie skórek.\r\n- malowanie lakierem'
        service.save()
        html = client.get(reverse('home')).content.decode()
        assert '<h4 class="rb-treat-name">Manicure</h4>' in html
        assert '80 zł' in html
        assert '60 min' in html
        assert '<p>Opracowanie skórek.</p><ul><li>malowanie lakierem</li></ul>' in html
        assert f'data-book-service="{service.pk}"' in html

    def test_inactive_services_are_hidden(self, client, service):
        Service.objects.create(name='Stary zabieg', category=service.category, price='50', duration=30, is_active=False)
        html = client.get(reverse('home')).content.decode()
        assert 'Stary zabieg' not in html

    def test_categories_follow_their_order_field(self, client, db):
        later = ServiceCategory.objects.create(name='Depilacja woskiem', slug='depilacja-woskiem', order=20)
        first = ServiceCategory.objects.create(name='Rzęsy i brwi', slug='rzesy-i-brwi', order=10)
        Service.objects.create(name='Pachy', category=later, price='40', duration=20)
        Service.objects.create(name='Henna brwi', category=first, price='30', duration=20)
        price_list = client.get(reverse('home')).context['price_list']
        assert [group['category'] for group in price_list] == [first, later]

    def test_price_range_ignores_free_services(self, client, service, service_short):
        Service.objects.create(name='Bezpłatna konsultacja', category=service.category, price='0', duration=30)
        (group,) = client.get(reverse('home')).context['price_list']
        assert (group['min_price'], group['max_price']) == (Decimal('30'), Decimal('80'))
        assert len(group['services']) == 3

    def test_free_service_is_labelled_free(self, client, category):
        Service.objects.create(name='Bezpłatna konsultacja', category=category, price='0', duration=30)
        html = client.get(reverse('home')).content.decode()
        assert '<span class="rb-treat-price">bezpłatnie</span>' in html
        assert '<span class="rb-treat-price">0 zł</span>' not in html

    def test_booking_select_lists_services_grouped_by_category(self, client, service):
        html = client.get(reverse('home')).content.decode()
        assert f'<optgroup label="{service.category.name}">' in html
        assert f'<option value="{service.pk}">Manicure — 80 zł</option>' in html

    def test_query_count_does_not_grow_with_services(self, client, category):
        def count_queries():
            with CaptureQueriesContext(connection) as ctx:
                client.get(reverse('home'))
            return len(ctx)

        Service.objects.create(name='Jeden', category=category, price='10', duration=10)
        few = count_queries()
        other = ServiceCategory.objects.create(name='Inna', slug='inna', order=5)
        for i in range(10):
            Service.objects.create(name=f'Zabieg {i}', category=other, price='10', duration=10)
        assert count_queries() == few


def home_html(client):
    return client.get(reverse('home')).content.decode()


class TestSalonTruth:
    """The home page shows only what is true today: who works, when the next free slot is, real reviews."""

    def test_one_employee_profile_without_specialist_picker(self, client, employee):
        html = home_html(client)
        assert 'Kto Cię przyjmie' in html
        assert '<h4 class="rb-person-name">Anna</h4>' in html
        assert 'Doświadczona stylistka.' in html
        assert '<p class="rb-person-skills">Zabiegi kosmetyczne</p>' in html  # from the employee's services
        assert 'id="bookingEmployee"' not in html

    def test_two_employees_team_with_specialist_picker(self, client, employee, other_employee):
        html = home_html(client)
        assert 'Nasz zespół' in html
        assert html.count('class="rb-person"') == 2
        assert 'id="bookingEmployee"' in html

    def test_inactive_employee_is_not_shown(self, client, employee, other_employee):
        other_employee.is_active = False
        other_employee.save()
        html = home_html(client)
        assert 'Ewa' not in html
        assert 'id="bookingEmployee"' not in html

    def test_no_made_up_numbers_or_staff(self, client, employee):
        html = home_html(client)
        for text in [
            '2000+',
            'Ekspertów urody',
            'Usług premium',
            'Marika',
            'Wiola',
            'w sercu',
            'w centrum',
            'unsplash',
        ]:
            assert text not in html, text

    @override_settings(LANGUAGE_CODE='pl')
    def test_next_free_date(self, client, employee, tomorrow):
        html = home_html(client)
        assert html.count('<a href="#rezerwacja">jutro</a>') == 2  # hero and contact

    def test_no_free_date_asks_to_call(self, client, employee):
        assert home_html(client).count('zadzwoń, znajdziemy termin') == 2

    def test_reviews_link_to_google(self, client, db):
        html = home_html(client)
        assert 'href="https://maps.google.com/?cid=16009745620444220515"' in html
        assert 'href="https://g.page/r/CWOM8YrRCi7eEBM/review"' in html
        assert 'testimonial' not in html

    def test_notes_field_warns_about_health_data(self, client, db):
        html = home_html(client)
        assert 'aria-describedby="bookingNotesHint"' in html
        assert 'Nie wpisuj tu informacji o zdrowiu' in html

    def test_query_count_does_not_grow_with_employees(self, client, employee, tomorrow):
        def count_queries():
            with CaptureQueriesContext(connection) as ctx:
                client.get(reverse('home'))
            return len(ctx)

        few = count_queries()
        for i in range(5):
            Employee.objects.create(first_name=f'Osoba {i}', bio='').services.add(*employee.services.all())
        assert count_queries() == few
