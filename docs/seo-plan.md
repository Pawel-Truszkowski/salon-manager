# SEO / GEO / AEO + redesign — plan

Na podstawie pełnego audytu produkcji (`royalbeauty-studiourody.pl`, 2026-10-16; raport: `~/Downloads/seo-audit-royalbeauty-studiourody-pl-2026-10-16.docx`) i propozycji redesignu (`docs/redesign/`).

**Oceny wyjściowe:** SEO 5/10 · GEO 4/10 · AEO 3/10 (12/30). Cel po etapach 1–6: ok. 7–8 w każdym wymiarze, a po etapach 7–8: 8–9.

**Główna diagnoza:** najcenniejsza treść, czyli usługi z opisami, cenami i czasem trwania, istnieje tylko po wykonaniu JS (`static/js/script.js` pobiera `/api/services/` i wypełnia pusty `#servicesGrid`). Boty AI zazwyczaj nie wykonują JS. Do tego strona podaje nieprawdziwe informacje: przykładowe opinie, trzy specjalistki, stałe godziny otwarcia.

## Ustalenia (2026-10-17)

- **Zespół:** pracuje tylko właścicielka, **Paulina, magister kosmetologii**. Aplikacja zostaje wieloosobowa, a strona dopasowuje się do liczby aktywnych `Employee`: przy jednej osobie pokazuje profil, przy dwóch i więcej listę zespołu i pole „Specjalistka” w formularzu. Nigdy nie wpisujemy „jedna” na sztywno.
- **Godziny:** brak stałych godzin. Wizyty **po wcześniejszym umówieniu, codziennie 9:00–21:00**, także w weekendy. Te same ramy w wizytówce Google i w schema. Na stronie zamiast tabeli godzin pokazujemy „Najbliższy wolny termin”, liczony z `Schedule`.
- **Laser:** wynajmowany na ok. 2 dni co ok. 6 tygodni, najbliżej **8–9 listopada 2026** (niedziela i poniedziałek). Model danych: wariant B, czyli urządzenie i terminy jego wynajmu (etap 5).
- **Opinie:** Google Places API albo link do wizytówki. Nie kopiujemy treści ręcznie. Przykładowe opinie znikną razem z publikacją nowej strony.
- **Regulamin i polityka prywatności:** na końcu (etap 8), ze wzoru, który przygotuje developer.
- **Publikacja:** nowa strona trafia na produkcję w całości po etapach 1–5 (etap 6). Do tego czasu PR-y idą na `dev` i są sprawdzane na stagingu.

## Do zebrania od Pauliny

- [ ] Model lasera i opis technologii, partie ciała, ceny, czas trwania, przeciwwskazania, zalecany odstęp między zabiegami. Część jest już w wizytówce Google.
- [ ] Zdjęcie portretowe 3:4 do profilu.
- [ ] Czy „ponad 10 lat doświadczenia” i „ponad 2000 klientek” to dane o niej (dziś są na stronie)?
- [ ] Nazwa marki: „Royal Beauty” czy „Royal Beauty Studio Urody”? Ma być identyczna w title, schema, stopce i wizytówce.
- [ ] Link do wizytówki Google (do `sameAs`, `hasMap` i przycisku „Opinie w Google”) oraz `place_id`, jeśli idziemy w Places API.

## Etapy (każdy jako osobny PR na `dev`, gałąź od `dev`)

### 0. Dane: bez kodu
Pole `Employee.is_active` istnieje dopiero na `dev` (panel), a na `main` (produkcja) go nie ma, więc na produkcji dezaktywacja jest możliwa dopiero po deployu w etapie 6. Na produkcji nikt nie ma grafiku, więc rezerwacji do nieaktywnych osób i tak nie da się zrobić. Stan 2026-10-17: na produkcji i na stagingu API wciąż zwraca trzy osoby.
- [ ] **Staging** (`dev.royalbeauty-studiourody.pl/admin/` → Employees): Marika i Wiola → `is_active = False`. Uwaga: to pole na `Employee`, a nie `User.is_active` konta. Sprawdzenie: `/api/employees/` zwraca tylko Paulinę.
- [ ] Bio Pauliny: poprawić literówkę „paznocki” → „paznokci” (staging, a po etapie 6 produkcja).

### 1. Fundamenty wyglądu + quick wins SEO
Według `docs/redesign/README.md` (tokeny, typografia) i prototypu.
- [x] Tokeny w `:root` (`--rb-gold-ink` do tekstu w złocie), Jost zamiast Raleway i Cormorant (PR #29). Ozdobniki w hero usunięte w 1.2; wersaliki nad nagłówkami, złota kursywa i kreski w pozostałych sekcjach znikną przy ich przebudowie (etapy 2–4).
- [x] **Czcionki hostowane lokalnie** w `static/fonts/` zamiast Google Fonts. Strona przestaje przekazywać IP odwiedzających do Google (RODO) i szybciej się ładuje.
- [x] Nagłówek i hero z prototypu: dokładnie jeden `<h1>`, `tel:` w linkach, nawigacja do kotwic.
  *Akceptacja:* test `assertContains(response, '<h1', count=1)`.
- [ ] **Title** ≤ 60 znaków. **Open Graph + Twitter Card** w `base.html` przez bloki (podstrony je nadpiszą), `og:image` 1200×630.
- [ ] **JSON-LD BeautySalon** (wzór w prototypie): `@id`, `geo`, `priceRange: "20–400 zł"`, `openingHoursSpecification` pn–nd 09:00–21:00, `description` z „wyłącznie po wcześniejszym umówieniu”, `founder` → `Person` (Paulina), `logo`, `email`.
- [x] Alty opisowe, `rel="noopener"` przy `target="_blank"`.
- [x] Polskie `404.html` / `500.html`.
  *Akceptacja:* test z `@override_settings(DEBUG=False)`.
- [x] **www → 301** na domenę główną (`nginx/prod.conf`; zadziała po deployu, patrz etap 6).

### 2. Cennik renderowany po stronie serwera ⭐
- [ ] Usługi pogrupowane w widoku `home` i wyrenderowane w Django jako wiersze `<details>`: nazwa (`<h3>`), czas, cena, opis (listy z „- ” jako `<ul>`). Spis kategorii z liczbą zabiegów i zakresem cen.
- [ ] JS nie pobiera już `/api/services/` dla cennika. Dropdown usług w formularzu też z Django.
- [ ] Cena 0 → „bezpłatnie”.
  *Akceptacja:* `curl … | grep "Mezoterapia mikroigłowa"` znajduje usługę; test widoku sprawdza nazwę i cenę przykładowej usługi; liczba zapytań do bazy stała (`django_assert_num_queries`).

> Uwaga: to zmienia kontrakt z `script.js`. Sprawdź, co jeszcze czyta `servicesData`, zanim go usuniesz.

### 3. Prawda o salonie: profil, godziny, opinie, obrazy
- [ ] **Profil / zespół** zależny od `employees|length`: przy jednej osobie profil (zdjęcie, imię, „Właścicielka, magister kosmetologii”, specjalizacje), przy dwóch i więcej lista. Pole „Specjalistka” w formularzu tylko przy 2+ aktywnych.
  *Akceptacja:* dwa testy, jeden aktywny `Employee` (brak pola `employee` w HTML) i dwa aktywne (pole jest).
- [ ] **Najbliższy wolny termin** w hero i w kontakcie: funkcja pomocnicza w `apps/bookings/utils.py`, np. `next_available_date(days_ahead=30)`. Korzysta z tej samej logiki co `/api/available-dates/` (`get_available_slots`), nie z osobnej kopii. Gdy brak terminów w 30 dniach: „Zadzwoń, znajdziemy termin”.
  *Akceptacja:* testy z `Schedule` jutro / bez grafiku; liczba zapytań rozsądna (to jest na stronie głównej).
- [ ] Kontakt: „Przyjmujemy po wcześniejszym umówieniu, codziennie 9:00–21:00” zamiast tabeli godzin. Usunąć „w centrum” / „w sercu miasta”.
- [ ] **Opinie:** sekcja bez karuzeli i bez treści na sztywno. Wariant minimum: przycisk „Opinie w Google”. Wariant z API: Google Places API (do 5 opinii) z wymaganym oznaczeniem źródła, cache krótkoterminowy zgodnie z warunkami Google i informacją „Opinie pochodzą z Google” (wymóg UOKiK o weryfikacji opinii). Bez schema `Review` / `AggregateRating` dla własnych opinii.
- [ ] Pole „Uwagi” w formularzu z podpowiedzią „Nie wpisuj tu informacji o zdrowiu, omówimy je na miejscu” (RODO art. 9).
- [ ] Obrazy: logo PNG 1,44 MB → WebP lub SVG (< 50 KB), `hero.jpg` i `contact.jpg` → WebP, `width`/`height`, `loading="lazy"` poniżej pierwszego ekranu, bez tła z Unsplash.
  *Akceptacja:* PageSpeed Insights (mobile) przed i po, z wynikiem w opisie PR.

### 4. FAQ (AEO)
- [ ] Sekcja `#faq` (wzór pytań w prototypie): ceny rzęs, konsultacja, kiedy można się umówić, kiedy laser, jak zarezerwować, jak odwołać, manicure hybrydowy. Pytanie jako `<h3>` w `<summary>`, odpowiedź 40–60 słów.
- [ ] Ceny i daty w odpowiedziach **z bazy**, nie wpisane na sztywno: np. zakres cen przedłużania rzęs z `Service`, najbliższy termin lasera z `EquipmentRental` (etap 5).
- [ ] `FAQPage` JSON-LD generowany z tych samych danych co HTML.

### 5. Laser: urządzenie i terminy wynajmu (wariant B)
Termin docelowy: przed 8 listopada. Jeśli nie zdążymy, laser na pierwszy termin rezerwujemy telefonicznie.
- [ ] Modele w `apps/services/models.py`:
  - `Equipment(name, description, is_active)`;
  - `EquipmentRental(equipment FK, date_from, date_to)` z walidacją `date_from <= date_to`;
  - `Service.required_equipment` (FK do `Equipment`, `null=True`, `on_delete=PROTECT`).
- [ ] Jedna funkcja pomocnicza, np. `is_service_available_on(service, date)`: `True`, gdy usługa nie wymaga urządzenia albo data mieści się w którymś wynajmie. Wywołana **zarówno** w `get_available_slots`, jak i w `find_available_specialist` (zasada z CLAUDE.md: obie ścieżki muszą być spójne).
  *Akceptacja:* testy obu ścieżek (z wybraną specjalistką i bez) dla dnia z wynajmem i bez; `/api/available-dates/` dla usługi laserowej zwraca tylko dni z wynajmu.
- [ ] Panel (właściciel): lista urządzeń i dodawanie terminów wynajmu; przy usłudze wybór wymaganego urządzenia.
- [ ] Strona: kategoria „Depilacja laserowa” z blokiem „Laser w salonie: 8–9 listopada” i opisem urządzenia (`Equipment.description`). Przy braku przyszłych terminów: „Kolejny termin wkrótce, zadzwoń, zapiszemy Cię jako pierwszą”.
- [ ] Schema: `Offer` z `availabilityStarts` / `availabilityEnds` z najbliższego wynajmu.
- [ ] Na później (gdy będą pracownice): sprawdzanie, czy urządzenie nie jest zajęte przez inną wizytę w tym samym czasie.

### 6. Publikacja na produkcji
- [ ] Merge `dev` → `main`, ręczny deploy na Droplet (jak dotąd), sprawdzenie na stagingu przed deployem.
- [ ] Po deployu przeładować nginx (`docker compose -f docker-compose.prod.yml exec nginx nginx -s reload`): `prod.conf` jest montowany jako plik, więc `up -d --build` go nie podchwyci. Sprawdzenie: `curl -sI https://www.royalbeauty-studiourody.pl/` → `301` na domenę bez www.
- [ ] Zaraz po deployu na produkcji: etap 0 (Marika, Wiola → `is_active = False`, bio Pauliny).
- [ ] Paulina ustawia w panelu szablon tygodnia i generuje grafik (dziś na produkcji nikt nie ma grafiku, więc formularz nie pokazuje żadnych terminów, a „najbliższy wolny termin” pokazałby „zadzwoń”). Do tego wynajem lasera 8–9.11, jeśli etap 5 jest gotowy.
- [ ] `robots.txt` z `Disallow: /panel/` trafi na produkcję razem z panelem.
- [ ] Wizytówka Google: godziny pn–nd 9–21 i opis „wyłącznie po wcześniejszym umówieniu”, link do strony, link do rezerwacji.
- [ ] Google Search Console: zgłoszenie sitemapy, sprawdzenie, czy strona główna jest zaindeksowana na nowo.

### 7. Podstrony kategorii (SEO long-tail)
- [ ] `/uslugi/<slug>/` dla każdej kategorii, zaczynając od **depilacji laserowej** (najmocniejsza fraza): własny `title`, H1 „Depilacja laserowa we Wrocławiu”, opis urządzenia, terminy, tabela cen, FAQ kategorii, CTA.
- [ ] JSON-LD `OfferCatalog` + `BreadcrumbList`, `provider` → `@id` salonu.
- [ ] `CategorySitemap` w `config/sitemaps.py` z `lastmod`.

### 8. Na koniec
- [ ] Polityka prywatności i regulamin rezerwacji jako strony (`TemplateView`) + linki w stopce i przy formularzu.
- [ ] Cloudflare: wyłączone „Block AI bots”, jeśli zależy nam na GEO.
- [ ] Opcjonalnie `llms.txt`.
- [ ] Ponowny audyt SEO/GEO/AEO.
