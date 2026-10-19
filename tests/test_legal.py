"""Privacy policy and booking terms: reachable, linked from the footer and the booking form, in the sitemap."""

import pytest
from django.urls import reverse

from tests.test_views import home_html


@pytest.mark.django_db
class TestLegalPages:
    @pytest.mark.parametrize(
        ('name', 'heading'), [('privacy', 'Polityka prywatności'), ('terms', 'Regulamin rezerwacji')]
    )
    def test_page_names_the_salon_owner(self, client, name, heading):
        html = client.get(reverse(name)).content.decode()
        assert f'<h1>{heading}</h1>' in html
        assert 'NIP 6131586038' in html

    def test_terms_rules_agreed_with_the_salon(self, client):
        html = client.get(reverse('terms')).content.decode()
        assert '24 godziny przed wizytą' in html
        assert 'spóźnieniu powyżej 15 minut' in html
        assert 'nie pobiera zadatków' in html
        assert 'gotówką lub BLIK-iem' in html
        assert 'Cena zabiegu się nie zmienia.' in html

    def test_footer_and_booking_form_link_both_pages(self, client):
        html = home_html(client)
        for name in ('privacy', 'terms'):
            assert html.count(f'href="{reverse(name)}"') == 2  # footer + note above the booking button

    def test_sitemap_lists_them(self, client):
        xml = client.get('/sitemap.xml').content.decode()
        assert 'http://testserver/polityka-prywatnosci/' in xml
        assert 'http://testserver/regulamin/' in xml
