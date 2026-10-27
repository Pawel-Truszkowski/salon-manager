"""Frequently asked questions on the home page and on the category pages (`category_pages.py`).

The same list feeds the visible `#faq` section and the `FAQPage` JSON-LD, so search engines and AI answer engines
read exactly what clients see. Prices and durations come from `Service`, never typed into the text: a price change
in the panel updates the answers. A question whose services are missing (renamed or deactivated) is left out
instead of showing a wrong number.
"""

from apps.services.models import format_price
from apps.services.schema import jsonld

PHONES = '+48 793 355 756 lub +48 792 646 256'


def _range(values, number, unit):
    """ "150 zł" or "od 150 do 210 zł": the unit only once, as people say it."""
    low, high = min(values), max(values)
    if low == high:
        return f'{number(low)} {unit}'
    return f'od {number(low)} do {number(high)} {unit}'


def _prices(values):
    return _range(values, lambda v: format_price(v).removesuffix(' zł'), 'zł')


def _minutes(values):
    return _range(values, str, 'minut')


def _named(services, prefix):
    """Active services whose name starts with `prefix` (case-insensitive), cheapest first."""
    found = [s for s in services if s.name.lower().startswith(prefix.lower())]
    return sorted(found, key=lambda s: (s.price, s.name))


def _variant(service, prefix):
    """The part of the name after the prefix, e.g. "1:1" for "Przedłużanie rzęs 1:1"."""
    return service.name[len(prefix) :].strip()


def _lashes(services):
    prefix = 'Przedłużanie rzęs'
    extensions = _named(services, prefix)
    if not extensions:
        return None
    cheapest, dearest = extensions[0], extensions[-1]
    answer = f'Przedłużanie rzęs kosztuje {_prices([s.price for s in extensions])}'
    if len(extensions) > 1 and _variant(cheapest, prefix) and _variant(dearest, prefix):
        answer += f' (od metody {_variant(cheapest, prefix)} do {_variant(dearest, prefix)})'
    answer += f' i trwa {_minutes([s.duration for s in extensions])}.'
    refills = _named(services, 'Uzupełnianie rzęs')
    if refills:
        answer += f' Uzupełnianie kosztuje {_prices([s.price for s in refills])}.'
    answer += ' Ceny wszystkich metod znajdziesz w cenniku, w kategorii rzęsy i brwi.'
    return 'Ile kosztuje przedłużanie rzęs?', answer


def _consultation(services):
    free = [s for s in services if s.price == 0 and 'konsultacja' in s.name.lower()]
    if not free:
        return None
    return (
        'Czy mogę najpierw przyjść na konsultację?',
        f'Tak, konsultacja z kosmetologiem jest bezpłatna i trwa około {free[0].duration} minut. '
        'Kosmetolog oceni stan skóry i doradzi, który zabieg będzie dla Ciebie najlepszy. '
        'Konsultację rezerwujesz tak samo jak każdy zabieg: w formularzu na stronie albo telefonicznie.',
    )


def _hybrid_manicure(services):
    prefix = 'Manicure hybrydowy'
    manicures = _named(services, prefix)
    basic = next((s for s in manicures if s.name.lower() == prefix.lower()), None)
    if basic is None:
        return None
    answer = f'Manicure hybrydowy trwa około {basic.duration} minut i kosztuje {format_price(basic.price)}.'
    for variant in manicures:
        if variant is not basic:
            answer += f' Wersja {_variant(variant, prefix)} kosztuje {format_price(variant.price)}.'
    removals = _named(services, 'Usunięcie hybrydy')
    if removals:
        listed = ', '.join(f'{s.name[0].lower()}{s.name[1:]} {format_price(s.price)}' for s in removals)
        answer += f' Jeśli masz starą hybrydę: {listed}.'
    return 'Ile trwa manicure hybrydowy i ile kosztuje?', answer


def _laser_services(services):
    """Services done with rented laser equipment (laser hair removal)."""
    return [s for s in services if s.required_equipment_id and 'laser' in s.category.name.lower()]


def _laser(services, rentals):
    """Next laser days from the rentals of the equipment that laser services need; phone when none is planned."""
    laser_equipment = {s.required_equipment_id for s in _laser_services(services)}
    if not laser_equipment:
        return None
    upcoming = sorted((rentals[pk] for pk in laser_equipment if pk in rentals), key=lambda r: r.date_from)
    answer = (
        'Depilację wykonujemy laserem diodowym LightSheer DUET firmy Lumenis. '
        'Laser jest w salonie przez dwa dni mniej więcej co 6 tygodni'
    )
    if upcoming:
        answer += (
            f', najbliżej {upcoming[0].label}. Zabiegi robi się w serii co kilka tygodni, więc kolejny termin '
            'umówisz od razu po wizycie. W formularzu zabiegi laserowe zarezerwujesz tylko na dni z laserem.'
        )
    else:
        answer += (
            '. Zabiegi robi się w serii co kilka tygodni, więc kolejny termin umówisz od razu po wizycie. '
            f'O najbliższy termin zapytaj telefonicznie: {PHONES}.'
        )
    return 'Kiedy mogę zrobić depilację laserową?', answer


def _laser_sessions(services):
    if not _laser_services(services):
        return None
    return (
        'Ile zabiegów depilacji laserowej potrzeba?',
        'Depilacja laserowa to seria zabiegów: na jedną partię ciała zwykle 6–8, w odstępach około 6 tygodni. '
        'Laser działa tylko na włosy w fazie wzrostu, a rosną one cyklicznie. Liczba zabiegów zależy od koloru '
        'i grubości włosów, gęstości owłosienia i partii ciała. Ile potrzebujesz Ty, ocenimy na pierwszej wizycie.',
    )


def _laser_pain(services):
    if not _laser_services(services):
        return None
    return (
        'Czy depilacja laserowa boli?',
        'To kwestia indywidualna. Najczęściej czuć ciepło i krótkie ukłucie, podobne do pstryknięcia gumką. '
        'Laser LightSheer DUET ma głowicę z podciśnieniem lub chłodzeniem, które zmniejsza dyskomfort. '
        'Najbardziej wrażliwe bywają bikini i pachy. Jeśli coś będzie nieprzyjemne, powiedz od razu, '
        'a dopasujemy ustawienia.',
    )


def _laser_contraindications(services):
    if not _laser_services(services):
        return None
    return (
        'Kto nie może zrobić depilacji laserowej?',
        'Przeciwwskazania to m.in. ciąża i karmienie piersią, świeża opalenizna lub samoopalacz, leki '
        'światłouczulające (np. izotretynoina), stany zapalne, rany lub opryszczka w miejscu zabiegu, choroba '
        'nowotworowa, padaczka i skłonność do bliznowców. Laser nie usuwa jasnych, siwych ani rudych włosów. '
        'Przed pierwszym zabiegiem porozmawiamy i poprosimy o wypełnienie ankiety.',
    )


def _lash_refills(services):
    if not _named(services, 'Przedłużanie rzęs'):
        return None
    answer = (
        'Rzęsy naturalnie wypadają i odrastają, więc przedłużone najlepiej uzupełniać mniej więcej co 2–3 tygodnie. '
        'Po dłuższej przerwie zostaje zbyt mało rzęs do uzupełnienia i trzeba założyć je od nowa.'
    )
    refills = _named(services, 'Uzupełnianie rzęs')
    if refills:
        answer += f' Uzupełnianie kosztuje {_prices([s.price for s in refills])}.'
    return 'Jak często trzeba uzupełniać przedłużone rzęsy?', answer


def _hybrid_lasts(services):
    if not _named(services, 'Manicure hybrydowy'):
        return None
    return (
        'Jak długo utrzymuje się manicure hybrydowy?',
        'Hybryda utrzymuje się zwykle 3–4 tygodnie, zależnie od tempa wzrostu paznokci i tego, jak dbasz o dłonie. '
        'Potem paznokieć odrasta przy skórkach i warto umówić kolejną wizytę. Hybrydy nie zrywaj samodzielnie, '
        'bo osłabia to płytkę paznokcia.',
    )


def build_faq(services, rentals=None):
    """[{'question', 'answer'}, ...] for the home page.

    `services` are the active services already loaded (with `category`), `rentals` the next rental per
    equipment id (`apps.services.views.next_rentals`).
    """
    services = list(services)
    items = [
        # Detailed questions of a category are on its page (`*_page_faq` below): Google wants a question marked
        # up as FAQPage on one page only. The home page keeps one question per category
        _lashes(services),
        _consultation(services),
        (
            'Kiedy mogę się umówić?',
            'Przyjmujemy po wcześniejszym umówieniu, codziennie od 9:00 do 21:00, także w soboty i niedziele. '
            'Termin dopasowujemy do Ciebie, więc łatwo umówić się po pracy albo w weekend. '
            'Wolne godziny widzisz w formularzu rezerwacji. Jeśli żadna nie pasuje, zadzwoń.',
        ),
        _laser(services, rentals or {}),
        (
            'Jak zarezerwować wizytę?',
            'Wybierz zabieg, dzień i godzinę w formularzu rezerwacji. Pokazujemy tylko wolne terminy. '
            'Potwierdzimy wizytę e-mailem w ciągu 24 godzin. '
            f'Możesz też zadzwonić: {PHONES}.',
        ),
        (
            'Gdzie dokładnie jest salon?',
            'Przy ul. Małopanewskiej 24B/5 we Wrocławiu (54-212, Fabryczna). '
            'Salon jest na 1. piętrze, w budynku jest winda.',
        ),
        (
            'Jak dojechać do salonu i gdzie zaparkować?',
            'Samochodem: na osiedlu pod blokiem jest bezpłatny parking. Tramwajem lub autobusem: najbliższy '
            'przystanek to Małopanewska, a kilka minut dalej jest przystanek Niedźwiedzia przy Magnolia Park. '
            'Trasę z Twojego miejsca pokaże link do mapy w sekcji Kontakt.',
        ),
        (
            'Jak mogę zapłacić za zabieg?',
            'Za zabieg płacisz w salonie po jego wykonaniu, gotówką lub BLIK-iem. Rezerwacja jest bezpłatna, '
            'nie pobieramy zadatków. Cenę każdego zabiegu znajdziesz w cenniku, a przy zabiegach z ceną „od” '
            'ostateczną kwotę ustalimy przed rozpoczęciem.',
        ),
        (
            'Jak odwołać lub przełożyć wizytę?',
            'W e-mailu z potwierdzeniem rezerwacji jest link do odwołania wizyty. Wystarczy go kliknąć '
            'i potwierdzić. Jeśli chcesz przełożyć termin, zadzwoń do salonu, a razem znajdziemy nowy. '
            'Prosimy o odwołanie najpóźniej 24 godziny przed wizytą.',
        ),
        _hybrid_manicure(services),
    ]
    return [{'question': q, 'answer': a} for q, a in filter(None, items)]


def _laser_price(services):
    laser = _laser_services(services)
    if not laser:
        return None
    return (
        'Ile kosztuje depilacja laserowa?',
        f'Cena zależy od partii ciała: {_prices([s.price for s in laser])} za jeden zabieg. '
        'Pełny cennik partii jest wyżej na tej stronie. Płacisz po zabiegu, gotówką lub BLIK-iem, '
        'bez zadatków i bez kupowania pakietu z góry.',
    )


def _laser_preparation(services):
    if not _laser_services(services):
        return None
    return (
        'Jak przygotować się do depilacji laserowej?',
        'Na dzień lub dwa przed zabiegiem ogól miejsce zabiegu maszynką. Na 4 tygodnie przed nie depiluj go '
        'woskiem, pastą ani depilatorem, bo laser potrzebuje cebulki włosa. Przez 2–4 tygodnie unikaj słońca, '
        'solarium i samoopalacza. W dniu zabiegu nie nakładaj na to miejsce kremów ani dezodorantu.',
    )


def _laser_aftercare(services):
    if not _laser_services(services):
        return None
    return (
        'Co robić po depilacji laserowej?',
        'Zaczerwienienie po zabiegu zwykle mija w ciągu kilku godzin. Przez 2 dni unikaj sauny, basenu i gorących '
        'kąpieli, a przez 2 tygodnie słońca: na odsłonięte miejsca nakładaj krem z filtrem SPF 50. Nie rób '
        'peelingu przez kilka dni. Włosy wypadają same w ciągu 1–3 tygodni, nie wyrywaj ich.',
    )


def laser_page_faq(services, rentals=None):
    """FAQ of /uslugi/depilacja-laserowa/: the laser questions that aren't on the home page."""
    services = list(services)
    items = [
        _laser_price(services),
        _laser_sessions(services),
        _laser_pain(services),
        _laser_preparation(services),
        _laser_aftercare(services),
        _laser_contraindications(services),
    ]
    return [{'question': q, 'answer': a} for q, a in filter(None, items)]


def _lash_methods(services):
    prefix = 'Przedłużanie rzęs'
    extensions = _named(services, prefix)
    if len(extensions) < 2:
        return None
    return (
        'Jaką metodę przedłużania rzęs wybrać?',
        'Metoda 1:1 (jedna sztuczna rzęsa na jedną naturalną) daje naturalny efekt, jak po dobrym tuszu. '
        'Metody objętościowe, od 2:1 do 5/6:1, to kępki z kilku cienkich rzęs: im więcej rzęs w kępce, tym '
        'gęstsza linia. Długość i skręt dobieramy do oka i kondycji Twoich rzęs, a metodę doradzimy na wizycie.',
    )


def _lash_aftercare(services):
    if not _named(services, 'Przedłużanie rzęs'):
        return None
    return (
        'Jak dbać o przedłużone rzęsy?',
        'Przez pierwszą dobę nie mocz rzęs i unikaj pary, sauny i basenu. Do demakijażu używaj płynów bez olejów, '
        'bo olej rozpuszcza klej. Czesz rzęsy codziennie czystą szczoteczką, nie trzyj oczu, nie używaj zalotki '
        'ani wodoodpornego tuszu. Śpij na plecach lub na boku, nie twarzą w poduszce.',
    )


def _henna(services):
    hennas = _named(services, 'Henna')
    if not hennas:
        return None
    return (
        'Jak długo utrzymuje się henna brwi i rzęs?',
        'Henna na włoskach brwi trzyma się zwykle 2–4 tygodnie, a na skórze kilka dni. Na rzęsach kolor utrzymuje '
        'się dłużej, aż rzęsy się wymienią. Henna kosztuje '
        f'{_prices([s.price for s in hennas])}, zależnie od tego, czy łączysz ją z regulacją brwi.',
    )


def lash_brow_page_faq(services, rentals=None):
    """FAQ of /uslugi/rzesy-i-brwi/."""
    services = list(services)
    items = [_lash_methods(services), _lash_refills(services), _lash_aftercare(services), _henna(services)]
    return [{'question': q, 'answer': a} for q, a in filter(None, items)]


def _gel_or_hybrid(services):
    gels = _named(services, 'Żel')
    if not gels or not _named(services, 'Manicure hybrydowy'):
        return None
    return (
        'Czym różni się manicure hybrydowy od paznokci żelowych?',
        'Hybryda to kolor na naturalnej płytce, który utrzymuje się 3–4 tygodnie. Żel dodatkowo wzmacnia '
        'paznokcie i pozwala je przedłużyć, więc sprawdzi się przy miękkich i łamliwych płytkach. '
        f'Paznokcie żelowe kosztują {_prices([s.price for s in gels])}, a co kilka tygodni potrzebne jest '
        'uzupełnienie.',
    )


def _acid_pedicure(services):
    with_acids = [s for s in _named(services, 'Pedicure') if 'kwas' in s.name.lower()]
    if not with_acids:
        return None
    return (
        'Co to jest pedicure z kwasami?',
        'To pedicure, w którym zrogowaciały naskórek na stopach zmiękczamy preparatem z kwasami (callus). '
        'Dzięki temu usuwamy go dokładniej i delikatniej niż samym pilnikiem, a stopy są gładkie na dłużej. '
        f'Polecamy go przy twardej skórze i pękających piętach. Kosztuje {_prices([s.price for s in with_acids])}.',
    )


def _after_hybrid(services):
    biological = _named(services, 'Manicure biologiczny')
    if not biological:
        return None
    return (
        'Co zrobić, gdy paznokcie są osłabione po hybrydzie?',
        'Nie zrywaj hybrydy sama, bo razem z nią schodzą wierzchnie warstwy płytki. Przy osłabionych paznokciach '
        f'polecamy {biological[0].name[0].lower()}{biological[0].name[1:]}: odżywia płytkę i jest przeznaczony '
        'właśnie na czas po stylizacji hybrydowej lub żelowej. Możesz też dać paznokciom odpocząć '
        'z klasycznym lakierem.',
    )


def nails_page_faq(services, rentals=None):
    """FAQ of /uslugi/dlonie-i-stopy/."""
    services = list(services)
    items = [_hybrid_lasts(services), _gel_or_hybrid(services), _acid_pedicure(services), _after_hybrid(services)]
    return [{'question': q, 'answer': a} for q, a in filter(None, items)]


def _microneedling(services):
    sessions = _named(services, 'Mezoterapia mikroigłowa')
    if not sessions:
        return None
    return (
        'Ile kosztuje mezoterapia mikroigłowa i ile zabiegów potrzeba?',
        f'Mezoterapia mikroigłowa kosztuje {_prices([s.price for s in sessions])}, zależnie od tego, czy obejmuje '
        'samą twarz, czy także szyję i dekolt. Najlepsze efekty daje seria, zwykle 3–6 zabiegów co 2–4 tygodnie. '
        'Ile potrzebujesz Ty, ocenimy na konsultacji.',
    )


def _microneedling_aftercare(services):
    if not _named(services, 'Mezoterapia mikroigłowa'):
        return None
    return (
        'Co robić po mezoterapii mikroigłowej?',
        'Zaczerwienienie po zabiegu zwykle mija w ciągu doby. Przez 24 godziny nie nakładaj makijażu, nie '
        'chodź na basen ani do sauny. Przez 2 tygodnie unikaj słońca i codziennie używaj kremu z filtrem SPF 50. '
        'Retinoidy i kwasy odstaw na tydzień przed zabiegiem i po nim.',
    )


def _exfoliation(services):
    if not _named(services, 'Mikrodermabrazja') or not _named(services, 'Peeling kawitacyjny'):
        return None
    return (
        'Czym różni się mikrodermabrazja od peelingu kawitacyjnego?',
        'Oba zabiegi złuszczają martwy naskórek. Peeling kawitacyjny robi to ultradźwiękami: jest krótki '
        'i łagodny, dobry na odświeżenie skóry. Mikrodermabrazja diamentowa złuszcza mechanicznie, głowicą '
        'z diamentową końcówką, więc działa mocniej: wygładza, wyrównuje koloryt i rozjaśnia skórę.',
    )


def _cleansing(services):
    if not _named(services, 'Manualne oczyszczanie') or not _named(services, 'Oczyszczanie wodorowe'):
        return None
    return (
        'Oczyszczanie manualne czy wodorowe?',
        'Manualne oczyszczanie usuwa zaskórniki ręcznie, więc polecamy je przy cerze tłustej, mieszanej '
        'i trądzikowej. Oczyszczanie wodorowe jest delikatniejsze: wypłukuje pory i od razu nawilża skórę, '
        'więc sprawdzi się też przy cerze wrażliwej i odwodnionej. Jeśli nie wiesz, który wybrać, przyjdź '
        'na bezpłatną konsultację.',
    )


def face_page_faq(services, rentals=None):
    """FAQ of /uslugi/zabiegi-kosmetyczne/. The free consultation question stays on the home page."""
    services = list(services)
    items = [
        _microneedling(services),
        _microneedling_aftercare(services),
        _cleansing(services),
        _exfoliation(services),
    ]
    return [{'question': q, 'answer': a} for q, a in filter(None, items)]


def _wax_price(services):
    if not services:
        return None
    return (
        'Ile kosztuje depilacja woskiem?',
        f'Cena zależy od partii ciała: {_prices([s.price for s in services])} za zabieg, od wąsika po całe nogi. '
        'Partie możesz łączyć w jednej wizycie, a pełny cennik jest wyżej na tej stronie. Płacisz po zabiegu, '
        'gotówką lub BLIK-iem.',
    )


def _wax_hair_length(services):
    if not services:
        return None
    return (
        'Jak długie muszą być włosy do depilacji woskiem?',
        'Około 5 mm, czyli mniej więcej 2–3 tygodnie od ostatniego golenia. Krótszych wosk nie chwyci, a zbyt '
        'długie można przed zabiegiem przyciąć. Na dzień przed wizytą zrób delikatny peeling, a w dniu '
        'zabiegu nie nakładaj balsamu ani olejku.',
    )


def _wax_lasts(services):
    if not services:
        return None
    return (
        'Jak długo utrzymuje się efekt depilacji woskiem?',
        'Zwykle 3–4 tygodnie, bo wosk usuwa włoski razem z cebulkami. Odrastają cieńsze i miękkie, a nie kłujące '
        'jak po goleniu. Przy regularnych zabiegach rosną z czasem rzadsze. Jeśli chcesz pozbyć się włosów '
        'na dłużej, rozważ depilację laserową.',
    )


def _wax_aftercare(services):
    if not services:
        return None
    return (
        'Co robić po depilacji woskiem?',
        'Przez dobę unikaj sauny, basenu, solarium i opalania, a także perfumowanych kosmetyków i ciasnych '
        'ubrań na depilowanym miejscu. Lekkie zaczerwienienie mija zwykle po kilku godzinach. Po 2–3 dniach '
        'zacznij regularnie robić peeling i nawilżać skórę, żeby włoski nie wrastały.',
    )


def wax_page_faq(services, rentals=None):
    """FAQ of /uslugi/depilacja-woskiem/. `services` are the waxing ones only (named by body part, "Pachy")."""
    services = list(services)
    items = [_wax_price(services), _wax_hair_length(services), _wax_lasts(services), _wax_aftercare(services)]
    return [{'question': q, 'answer': a} for q, a in filter(None, items)]


def faq_jsonld(faq):
    """`FAQPage` JSON-LD for a <script type="application/ld+json"> tag, safe to output unescaped."""
    data = {
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        'mainEntity': [
            {
                '@type': 'Question',
                'name': item['question'],
                'acceptedAnswer': {'@type': 'Answer', 'text': item['answer']},
            }
            for item in faq
        ],
    }
    return jsonld(data)
