import pytest

from apps.bookings.checks import check_site_url


@pytest.mark.parametrize(
    'site_url',
    ['https://royalbeauty-studiourody.pl', 'https://royalbeauty-studiourody.pl/', 'http://localhost:8000'],
)
def test_absolute_site_url_passes(settings, site_url):
    settings.SITE_URL = site_url

    assert check_site_url(None) == []


@pytest.mark.parametrize(
    'site_url',
    [
        'royalbeauty-studiourody.pl',  # the 21.10.2026 deploy
        'www.royalbeauty-studiourody.pl',
        '//royalbeauty-studiourody.pl',
        'https://',
        'ftp://royalbeauty-studiourody.pl',
        '',
    ],
)
def test_site_url_without_a_scheme_is_an_error(settings, site_url):
    settings.SITE_URL = site_url

    [error] = check_site_url(None)

    assert error.id == 'bookings.E001'
    assert error.is_serious()  # stops migrate, so a broken deploy can't go unnoticed
