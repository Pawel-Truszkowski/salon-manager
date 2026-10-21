import json
import re
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.services.faq import build_faq, faq_jsonld
from apps.services.models import Service, format_price


def svc(name, price, duration=60):
    # build_faq only reads name/price/duration, so unsaved instances are enough
    return Service(name=name, price=Decimal(price), duration=duration)


def answers(services):
    return {item['question']: item['answer'] for item in build_faq(services)}


LASHES = 'Ile kosztuje przedłużanie rzęs?'
CONSULTATION = 'Czy mogę najpierw przyjść na konsultację?'
MANICURE = 'Ile trwa manicure hybrydowy i ile kosztuje?'


class TestFormatPrice:
    @pytest.mark.parametrize(('value', 'label'), [('150.00', '150 zł'), ('30.50', '30,50 zł'), ('0.00', '0 zł')])
    def test_format(self, value, label):
        assert format_price(Decimal(value)) == label


class TestBuildFaq:
    def test_lash_answer_uses_prices_and_durations_from_services(self):
        faq = answers(
            [
                svc('Przedłużanie rzęs 5/6:1', '210', 135),
                svc('Przedłużanie rzęs 1:1', '150', 105),
                svc('Uzupełnianie rzęs 1:1', '130'),
                svc('Uzupełnianie rzęs 5/6:1', '190'),
            ]
        )
        assert faq[LASHES].startswith(
            'Przedłużanie rzęs kosztuje od 150 do 210 zł (od metody 1:1 do 5/6:1) i trwa od 105 do 135 minut.'
        )
        assert 'Uzupełnianie kosztuje od 130 do 190 zł.' in faq[LASHES]

    def test_single_price_is_not_a_range(self):
        faq = answers([svc('Przedłużanie rzęs 1:1', '150', 105)])
        assert faq[LASHES].startswith('Przedłużanie rzęs kosztuje 150 zł i trwa 105 minut.')
        assert 'Uzupełnianie' not in faq[LASHES]

    def test_consultation_only_when_a_free_one_exists(self):
        assert 'trwa około 30 minut' in answers([svc('Bezpłatna konsultacja z kosmetologiem', '0', 30)])[CONSULTATION]
        assert CONSULTATION not in answers([svc('Konsultacja', '50', 30)])

    def test_hybrid_manicure_with_variants_and_removal(self):
        faq = answers(
            [
                svc('Manicure hybrydowy', '120', 75),
                svc('Manicure hybrydowy french', '130', 75),
                svc('Usunięcie hybrydy', '40'),
            ]
        )
        assert faq[MANICURE] == (
            'Manicure hybrydowy trwa około 75 minut i kosztuje 120 zł. Wersja french kosztuje 130 zł. '
            'Jeśli masz starą hybrydę: usunięcie hybrydy 40 zł.'
        )

    def test_questions_without_their_services_are_left_out(self):
        faq = answers([])
        assert LASHES not in faq and CONSULTATION not in faq and MANICURE not in faq
        # the rest doesn't depend on the price list
        assert 'Kiedy mogę się umówić?' in faq
        assert 'Jak odwołać lub przełożyć wizytę?' in faq

    def test_jsonld_matches_the_questions_and_cannot_close_the_script_tag(self):
        faq = [{'question': 'Czy </script> działa?', 'answer': 'A & B'}]
        text = faq_jsonld(faq)
        assert '</script>' not in text
        data = json.loads(text)
        assert data['@type'] == 'FAQPage'
        assert data['mainEntity'][0]['name'] == 'Czy </script> działa?'
        assert data['mainEntity'][0]['acceptedAnswer']['text'] == 'A & B'


@pytest.mark.django_db
class TestFaqOnHomePage:
    def test_section_and_jsonld_show_the_same_questions(self, client, category):
        Service.objects.create(name='Przedłużanie rzęs 1:1', category=category, price='150', duration=105)
        html = client.get(reverse('home')).content.decode()
        visible = re.findall(r'<h3 class="rb-faq-question">(.*?)</h3>', html)
        assert 'Ile kosztuje przedłużanie rzęs?' in visible
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        faq_ld = next(json.loads(b) for b in blocks if '"FAQPage"' in b)
        assert [q['name'] for q in faq_ld['mainEntity']] == visible

    def test_inactive_service_price_is_not_quoted(self, client, category):
        Service.objects.create(
            name='Przedłużanie rzęs 1:1', category=category, price='999', duration=105, is_active=False
        )
        html = client.get(reverse('home')).content.decode()
        assert 'Ile kosztuje przedłużanie rzęs?' not in html
        assert '999' not in html

    def test_navigation_links_to_faq(self, client):
        html = client.get(reverse('home')).content.decode()
        assert 'href="/#faq"' in html
        assert 'id="faq"' in html
