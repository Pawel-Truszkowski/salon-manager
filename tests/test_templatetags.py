import pytest

from apps.services.templatetags.services_extras import description_html, without_category


class TestDescriptionHtml:
    @pytest.mark.parametrize(
        ('text', 'expected'),
        [
            ('', ''),
            (None, ''),
            ('Jeden akapit.', '<p>Jeden akapit.</p>'),
            (
                'Henna brwi.\r\nZabieg obejmuje:\r\n- regulację brwi\r\n- hennę rzęs',
                '<p>Henna brwi.</p><p>Zabieg obejmuje:</p><ul><li>regulację brwi</li><li>hennę rzęs</li></ul>',
            ),
            ('- a\n\n- b', '<ul><li>a</li></ul><ul><li>b</li></ul>'),
            ('- a\nKoniec.', '<ul><li>a</li></ul><p>Koniec.</p>'),
            ('Cena -10% w środy', '<p>Cena -10% w środy</p>'),
        ],
    )
    def test_formats_paragraphs_and_lists(self, text, expected):
        assert description_html(text) == expected

    def test_escapes_html(self):
        assert description_html('<b>x</b>\n- <script>') == '<p>&lt;b&gt;x&lt;/b&gt;</p><ul><li>&lt;script&gt;</li></ul>'


class TestWithoutCategory:
    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('Depilacja laserowa – pachy', 'Pachy'),
            ('Depilacja laserowa – wąsik + broda', 'Wąsik + broda'),
            ('depilacja laserowa – bikini', 'Bikini'),
            ('Depilacja laserowa – ', 'Depilacja laserowa – '),  # nothing left: keep the full name
            ('Henna brwi', 'Henna brwi'),
        ],
    )
    def test_strips_only_the_repeated_category(self, name, expected):
        assert without_category(name, 'Depilacja laserowa') == expected
