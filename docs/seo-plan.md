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

- [x] **Laser:** LightSheer DUET (Lumenis), https://lumenis.com/aesthetics/products/lightsheer-duet/. Partie ciała, ceny i czas: z wizytówki Google (etap 5).
  - [ ] Jeszcze brakuje: przeciwwskazań i zalecanego odstępu między zabiegami.
- [ ] Zdjęcie portretowe 3:4 do profilu.
- [x] **Doświadczenie:** około 10 lat w zawodzie, salon prowadzi od 3 lat (od 2023). Wcześniej pracowała w innym salonie i przyjmowała klientki w domu. **„2000+ klientek” jest zmyślone i znika** (etap 3), razem z „3 ekspertów” i „20+ usług premium”. Na stronie: „ponad 10 lat doświadczenia, własny salon od 2023 roku”. Paulina potwierdza dokładny rok.
- [x] **Nazwa:** pełna to „Royal Beauty Studio Urody” (schema `name`, nagłówek strony od etapu 2, stopka, wizytówka Google), skrócona to „Royal Beauty” (title, `alternateName`).
- [x] **Link do wystawienia opinii:** https://g.page/r/CWOM8YrRCi7eEBM/review, do przycisku „Wystaw opinię” w etapie 3.
  - [ ] Jeszcze brakuje: link do wizytówki w Mapach (`hasMap`, `sameAs`, „Zobacz opinie w Google”), a przy Places API też `place_id`. Link do opinii otwiera tylko formularz wystawiania.

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
- [x] **Title** ≤ 60 znaków. **Open Graph + Twitter Card** w `base.html` przez bloki (podstrony je nadpiszą), `og:image` 1200×630.
- [x] **JSON-LD BeautySalon** (wzór w prototypie): `@id`, `geo`, `priceRange: "20–400 zł"`, `openingHoursSpecification` pn–nd 09:00–21:00, `description` z „wyłącznie po wcześniejszym umówieniu”, `founder` → `Person` (Paulina), `logo`, `email`.
- [x] Alty opisowe, `rel="noopener"` przy `target="_blank"`.
- [x] Polskie `404.html` / `500.html`.
  *Akceptacja:* test z `@override_settings(DEBUG=False)`.
- [x] **www → 301** na domenę główną (`nginx/prod.conf`; zadziała po deployu, patrz etap 6).

### 2. Cennik renderowany po stronie serwera ⭐
- [x] Usługi pogrupowane w widoku `home` (`build_price_list`) i wyrenderowane w Django jako wiersze `<details>`: nazwa (`<h4>` pod `<h2>` „Cennik” i `<h3>` kategorii), czas, cena, opis (filtr `description_html`: linie z „- ” jako `<ul>`). Spis kategorii z liczbą zabiegów i zakresem cen.
- [x] Kolejność kategorii z pola `ServiceCategory.order` (edytowalne w adminie). Migracja `0009` ustawia kolejność z prototypu: rzęsy, dłonie, zabiegi, depilacja.
- [x] JS nie pobiera już `/api/services/` dla cennika. Dropdown usług w formularzu też z Django (`<optgroup>`).
- [x] Cena 0 → „bezpłatnie” (`Service.price_label`).
- [x] Przy okazji: kontener 72rem jak w prototypie, pełna nazwa „Royal Beauty Studio Urody” w nagłówku, poprawka rozciągniętego zdjęcia w „O nas”.
- [ ] Dane dla Pauliny (panel): nazwa kategorii „Zabiegi kosmetyczne” → „Zabiegi na twarz i ciało”, spacje w nawiasach w nazwach („Mezoterapia mikroigłowa ( twarz)”).
  *Akceptacja:* `curl … | grep "Mezoterapia mikroigłowa"` znajduje usługę; test widoku sprawdza nazwę i cenę przykładowej usługi; liczba zapytań do bazy stała (`CaptureQueriesContext`).

> Uwaga: to zmienia kontrakt z `script.js`. Sprawdź, co jeszcze czyta `servicesData`, zanim go usuniesz.

### 3. Prawda o salonie: profil, godziny, opinie, obrazy
- [x] **Profil / zespół** zależny od `employees|length`: przy jednej osobie „Kto Cię przyjmie” (inicjał w łuku, imię, `bio`, specjalizacje z kategorii jej usług), przy dwóch i więcej „Nasz zespół”. Pole „Specjalistka” w formularzu tylko przy 2+ aktywnych; JS działa bez niego (serwer wybiera osobę przez `find_available_specialist`).
- [ ] **Portret Pauliny 3:4** (czeka na zdjęcie). Wtedy: pole `Employee.photo` albo plik w `static/img/`, decyzja przy wgrywaniu.
- [x] **Najbliższy wolny termin** w hero i w kontakcie: `next_available_date(days_ahead=30)` w `apps/bookings/utils.py`, przez `get_available_slots` (najkrótsza aktywna usługa osoby). „dzisiaj” / „jutro” / „wtorek, 20 października” (`naturalday`), bez terminu: „zadzwoń, znajdziemy termin”.
  - [ ] Etap 5: gdy dojdzie laser, najkrótsza usługa może wymagać urządzenia; sprawdzać usługi po kolei, nie tylko najkrótszą.
- [x] Kontakt: „Przyjmujemy po wcześniejszym umówieniu, codziennie 9:00–21:00” zamiast tabeli godzin, NAP w `<address>`, „Wyznacz trasę”. Bez „w centrum” / „w sercu miasta” (także w stopce).
- [x] „O salonie”: bez „2000+”, „3 ekspertów”, „20+ usług premium”. „Salon prowadzi od 2023 roku Paulina, magister kosmetologii z ponad 10-letnim doświadczeniem”. JSON-LD: `foundingDate`, `hasMap`, wizytówka w `sameAs`.
- [x] **Opinie (wariant minimum):** bez karuzeli i bez treści na sztywno; „Zobacz opinie w Google” (`maps.google.com/?cid=…`) i „Wystaw opinię” (`g.page/r/…/review`). Linki w `config/context_processors.py`.
  - [ ] Wariant z Places API (do 5 opinii, oznaczenie źródła): osobna decyzja, wymaga klucza API i konta rozliczeniowego Google Cloud.
- [x] Pole „Uwagi” z podpowiedzią „Nie wpisuj tu informacji o zdrowiu, omówimy je na miejscu” (`aria-describedby`). Etykiety formularza powiązane z polami (`for`), `autocomplete`.
- [x] Obrazy: WebP zamiast JPG/PNG (logo 1,44 MB → 12 KB, łącznie ~3,5 MB → ~0,7 MB), `width`/`height`, `loading="lazy"` poniżej pierwszego ekranu, bez tła z Unsplash. `logo.png` 512 px tylko dla schema.
  - [ ] PageSpeed Insights (mobile) na stagingu po deployu; API bez klucza miało wyczerpany limit, więc pomiar „przed” się nie udał. Wynik „po” do opisu PR.

### 4. FAQ (AEO)
- [x] Sekcja `#faq` „Częste pytania” (przed rezerwacją, link „Pytania” w menu i w stopce): ceny rzęs, konsultacja, kiedy można się umówić, laser, jak zarezerwować, jak odwołać, manicure hybrydowy. Pytanie jako `<h3>` w `<summary>`, odpowiedzi ok. 25–50 słów.
- [x] Ceny i czasy **z bazy** (`apps/services/faq.py`, `build_faq`): usługi szukane po początku nazwy („Przedłużanie rzęs”, „Uzupełnianie rzęs”, „Manicure hybrydowy”, „Usunięcie hybrydy”, bezpłatna „konsultacja”). Gdy usługi nie ma (zmiana nazwy, dezaktywacja), pytanie znika zamiast pokazać złą cenę.
  - [ ] Etap 5: w odpowiedzi o laser najbliższy termin z `EquipmentRental` (dziś: „zapytaj telefonicznie”).
- [x] `FAQPage` JSON-LD z tej samej listy co HTML (`faq_jsonld`, test porównuje pytania).
- [ ] Dane dla Pauliny (panel): „Manicure hybrydowy french/ babyboomer” → np. „Manicure hybrydowy french / baby boomer” (nazwa trafia do odpowiedzi w FAQ).
- [x] Przy okazji (PageSpeed mobile 87): Bootstrap i flatpickr z własnej domeny zamiast jsdelivr, 6 ikon jako inline SVG zamiast fontu 128 KB, `defer`, `<main>`, mniejsze logo w nagłówku, kontrast stopki, większe pola dotyku telefonów. Cloudflare: wyłączone Email Address Obfuscation (adres i tak jest w JSON-LD, a crawlery bez JS widziały zakodowany ciąg).
  - [ ] Ponowny pomiar PSI mobile na stagingu po deployu.

### 5. Laser: urządzenie i terminy wynajmu (wariant B)
Termin docelowy: przed 8 listopada. Jeśli nie zdążymy, laser na pierwszy termin rezerwujemy telefonicznie.
- [x] Modele: `Equipment(name, description, is_active)`, `EquipmentRental(equipment, date_from, date_to)` (oba końce włącznie, walidacja kolejności dat), `Service.required_equipment` (`PROTECT`). Migracja `0011` dodaje urządzenie „LightSheer DUET” i pustą kategorię „Depilacja laserowa” (cennik ukrywa ją, dopóki nie ma usług).
- [x] `is_service_available_on(service, date)` w `apps/bookings/utils.py`, wywoływana w `get_available_slots`. `find_available_specialist`, API slotów i dat, panel i `next_available_date` przechodzą przez `get_available_slots`, więc reguła obowiązuje wszędzie. Testy obu ścieżek rezerwacji (z wybraną osobą i bez) oraz `/api/available-dates/`.
- [x] `next_available_date`: dla każdego dnia najkrótsza usługa **możliwa tego dnia** (laser poza dniami wynajmu nie zasłania wolnego dnia).
- [x] Panel (właścicielka): „Urządzenia” — terminy wynajmu (dodawanie z walidacją: przeszłość, nakładanie się; usuwanie zablokowane, gdy są zapisane wizyty), edycja urządzenia; przy usłudze pole „Wymaga urządzenia”.
- [x] Strona: w kategorii z urządzeniem „Zabiegi wykonujemy w wybrane dni. Najbliżej: 8–9 listopada” + opis urządzenia; bez terminu: „Kolejny termin wkrótce. Zadzwoń, zapiszemy Cię jako pierwszą”. FAQ o laserze z datą najbliższego wynajmu.
- [ ] **Dane (Paulina / panel):** usługi laserowe w kategorii „Depilacja laserowa” z „Wymaga urządzenia: LightSheer DUET” (partie ciała, ceny, czas z wizytówki Google), termin wynajmu 8–9.11, grafik na te dni.
- [ ] Schema `Offer` z `availabilityStarts` / `availabilityEnds`: przeniesione do etapu 7 (podstrona depilacji laserowej z `OfferCatalog`).
- [ ] Na później (gdy będą pracownice): sprawdzanie, czy urządzenie nie jest zajęte przez inną wizytę w tym samym czasie.

### Przed etapem 6 (zrobione, gałąź `feature/catalog-pricelist`)
- [x] Cennik migracją `services.0013_catalog`: opisy z produkcji, czasy z Booksy, bez laminacji, 12 zabiegów laserowych (bikini „od 170 zł”, `Service.price_is_from`). Bez podmiany bazy produkcji.
- [x] Cennik w zakładkach (jedna kategoria naraz, cała treść w HTML).
- [x] 1. piętro i winda: kontakt, FAQ, maile do klientki.
- [x] Baza klientek w panelu (`Client`, „Klientki”, podpowiedzi w „Nowa wizyta”, import z dotychczasowych wizyt).
- [x] Polityka prywatności (`/polityka-prywatnosci/`) i regulamin rezerwacji (`/regulamin/`): linki w stopce i nad przyciskiem rezerwacji, w sitemapie. Logi kontenerów produkcji rotowane (`x-logging` w `docker-compose.prod.yml`), bo polityka mówi, że nie są trzymane w nieskończoność.
- [ ] Paulina (najlepiej z księgową) czyta obie strony; datę „Obowiązuje od” w `templates/legal/_page.html` ustawić na dzień deployu produkcji.
- [ ] Umowa powierzenia przetwarzania danych między Pauliną a osobą utrzymującą stronę (dostęp do bazy przez `/admin/` i serwer).

### 6. Publikacja na produkcji
- [ ] Merge `dev` → `main`, ręczny deploy na Droplet (jak dotąd), sprawdzenie na stagingu przed deployem.
- [ ] Po deployu przeładować nginx (`docker compose -f docker-compose.prod.yml exec nginx nginx -s reload`): `prod.conf` jest montowany jako plik, więc `up -d --build` go nie podchwyci. Sprawdzenie: `curl -sI https://www.royalbeauty-studiourody.pl/` → `301` na domenę bez www.
- [ ] Zaraz po deployu na produkcji: etap 0 (Marika, Wiola → `is_active = False`, bio Pauliny). Produkcja przeskoczy z migracji 0003 na 0013 naraz; `0013_catalog` przypisze zabiegi laserowe wszystkim aktywnym, czyli też Marice i Wioli, ale po wyłączeniu nie są one do zarezerwowania.
- [ ] Konto właścicielki dla Pauliny (grupa „Właściciel”), jeśli jeszcze go nie ma.
- [ ] Paulina ustawia w panelu szablon tygodnia i generuje grafik (dziś na produkcji nikt nie ma grafiku, więc formularz nie pokazuje żadnych terminów, a „najbliższy wolny termin” pokazałby „zadzwoń”). Do tego terminy lasera w „Urządzenia”: 8–9.11 i 14–15.12 (jak na Booksy).
- [ ] `robots.txt` z `Disallow: /panel/` trafi na produkcję razem z panelem.
- [ ] Wizytówka Google: godziny pn–nd 9–21 i opis „wyłącznie po wcześniejszym umówieniu”, link do strony, link do rezerwacji.
- [ ] Google Search Console: zgłoszenie sitemapy, sprawdzenie, czy strona główna jest zaindeksowana na nowo.

### 7. Podstrony kategorii (SEO long-tail)
- [ ] `/uslugi/<slug>/` dla każdej kategorii, zaczynając od **depilacji laserowej** (najmocniejsza fraza): własny `title`, H1 „Depilacja laserowa we Wrocławiu”, opis urządzenia, terminy, tabela cen, FAQ kategorii, CTA.
- [ ] JSON-LD `OfferCatalog` + `BreadcrumbList`, `provider` → `@id` salonu.
- [ ] `CategorySitemap` w `config/sitemaps.py` z `lastmod`.

### 8. Na koniec
- [ ] RODO w panelu: „Usuń klientkę” (z anonimizacją jej wizyt) oraz komenda czyszcząca karty i wizyty starsze niż 3 lata od ostatniej wizyty (tak obiecuje polityka prywatności; pierwsze dane się „przedawnią” jesienią 2029, ale lepiej zrobić to wcześniej).
- [ ] Cloudflare: wyłączone „Block AI bots”, jeśli zależy nam na GEO.
- [ ] Opcjonalnie `llms.txt`.
- [ ] Ponowny audyt SEO/GEO/AEO.
