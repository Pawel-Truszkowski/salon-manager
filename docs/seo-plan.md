# SEO / GEO / AEO + redesign — plan

Na podstawie pełnego audytu produkcji (`royalbeauty-studiourody.pl`, 2026-10-16; raport: `~/Downloads/seo-audit-royalbeauty-studiourody-pl-2026-10-16.docx`) i propozycji redesignu (`docs/redesign/`).

**Oceny wyjściowe:** SEO 5/10 · GEO 4/10 · AEO 3/10 (12/30). Cel po etapach 1–6: ok. 7–8 w każdym wymiarze (osiągnięte: 7/7/7 w audycie z 21.10.2026), a po etapach 7–12: 8–9.

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
- [x] Zdjęcie portretowe 3:4 do profilu (`static/img/profilowe.jpg`, 2026-10-20).
- [x] **Doświadczenie:** około 10 lat w zawodzie, salon prowadzi od 3 lat (od 2023). Wcześniej pracowała w innym salonie i przyjmowała klientki w domu. **„2000+ klientek” jest zmyślone i znika** (etap 3), razem z „3 ekspertów” i „20+ usług premium”. Na stronie: „ponad 10 lat doświadczenia, własny salon od 2023 roku”. Paulina potwierdza dokładny rok.
- [x] **Nazwa:** pełna to „Royal Beauty Studio Urody” (schema `name`, nagłówek strony od etapu 2, stopka, wizytówka Google), skrócona to „Royal Beauty” (title, `alternateName`).
- [x] **Link do wystawienia opinii:** https://g.page/r/CWOM8YrRCi7eEBM/review, do przycisku „Wystaw opinię” w etapie 3.
  - [ ] Jeszcze brakuje: link do wizytówki w Mapach (`hasMap`, `sameAs`, „Zobacz opinie w Google”), a przy Places API też `place_id`. Link do opinii otwiera tylko formularz wystawiania.

- [ ] **Po audycie 21.10 (etapy 7–12):**
  - [x] Link do profilu salonu na Booksy (`sameAs`).
  - [ ] Aktualizacja Booksy: tylko Paulina, codziennie 9–21.
  - [x] Zgoda na pełne imię i nazwisko w danych strukturalnych (`founder`).
  - [ ] Odpowiedzi do FAQ: przeciwwskazania, liczba i odstęp zabiegów laserem, czy laser boli, trwałość hybrydy i rzęs, parking i dojazd, płatność kartą / BLIK.
  - [ ] Opinie: którą opcję wybiera (etap 10) i ewentualnie 3–6 ulubionych opinii.
  - [ ] Tekst o depilacji laserowej na pierwszą podstronę (efekty, przebieg, przygotowanie, przeciwwskazania) + 1–2 zdjęcia z zabiegu.

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
Produkcja (`main` = 50421fc) przeskakuje naraz o ~40 commitów i 15 migracji, w tym trzy migracje danych (`accounts.0002` grupa, `bookings.0005` import klientek, `services.0013` cennik). Migracje danych nie mają cofania, więc **jedynym rollbackiem jest kopia bazy**.

**6a. Ostatni PR na `dev` (przed deployem)** ✅
- [x] Zdjęcie Pauliny (`static/img/paulina.webp`, 480×640) w profilu, gdy jest jedna aktywna osoba; przy kilku zostają inicjały. Docelowo `Employee.photo` wgrywane w panelu, gdy salon kogoś zatrudni.
- [x] Data „Obowiązuje od” w `templates/legal/_page.html` = 21 października 2026 (dzień deployu).
- [x] Paulina przeczytała politykę prywatności i regulamin (2026-10-21).
- [ ] **Przypomnienie o wizycie** (mail ok. 24 h przed): komenda `send_reminders` (`apps/bookings/reminders.py`) co godzinę z crona. Reguły: tylko wizyty potwierdzone, z e-mailem, w ciągu najbliższych 24 h, zarezerwowane co najmniej 24 h przed terminem; raz na wizytę (`Appointment.reminder_sent_at`, zerowane przy zmianie terminu); nieudana wysyłka = ponowna próba za godzinę. Paulina musi potwierdzać wizyty ze strony na czas, bo oczekujące nie dostają przypomnienia.
- [ ] Na stagingu pełna ścieżka: rezerwacja ze strony → mail → link „odwołaj” → mail; panel: potwierdzenie, przeniesienie w kalendarzu, laser tylko w dni wynajmu.

**6b. Próba generalna migracji (lokalnie, na kopii produkcji)** ✅ 2026-10-21, kopia `salon_prod_20261021_082201`
- [x] Wszystkie 16 migracji OK. Cennik: 64 → 73 usługi (12 laserowych, 3 usunięte), wszystkie z opisami, 5 kategorii w kolejności; grupa „Właściciel” jest; `send_reminders` → 0.
- [x] Na produkcji są 3 wizyty testowe z 9.07.2026 (Paulina, manicure męski, 2 potwierdzone + 1 oczekująca, wszystkie w przeszłości) → 1 karta klientki. Nic nie blokują.
- [x] **Wykryte:** 14 zabiegów na twarz (cała kategoria „Zabiegi kosmetyczne”, w tym bezpłatna konsultacja) ma przypisaną tylko Marikę → patrz 6d.
- [x] **Wykryte:** konto `paula` (Paulina) już istnieje: `is_staff` + 44 uprawnienia do `/admin/`, bez grupy, niepowiązane z `Employee` → patrz 6d.

**6c. Deploy** ✅ 2026-10-21 (PR #40)
- [x] Na Droplecie (`~/salon-manager`): `.env.prod` miał `SITE_URL` **bez `https://`** (zepsute canonical i linki w mailach) — poprawione 21.10 po deployu, `up -d --force-recreate web`. Sprawdzić też i czy w katalogu projektu **nie ma** `.env` z `NGINX_CONF` (na produkcji ma być domyślny `prod.conf`).
- [x] Świeża kopia bazy tuż przed deployem (`backup_db.sh --env prod`) + kopia poza serwerem.
- [x] PR `dev` → `main` (CI: ruff + testy), merge.
- [x] SSH: `git pull origin main`, `docker compose -f docker-compose.prod.yml up -d --build`, `docker compose … logs web | head -80` (migracje OK, gunicorn wstał). Wszystkie kontenery zostaną odtworzone (nowe `logging:`), więc nginx też wczyta nowy `prod.conf`; gdyby nie: `exec nginx nginx -s reload`.
- [x] Smoke test: `curl -sI https://www.royalbeauty-studiourody.pl/` i `http://…` → `301` na `https://royalbeauty-studiourody.pl/`; `/robots.txt` ma `Disallow: /panel/`; `/sitemap.xml` ma strony prawne; `/polityka-prywatnosci/`, `/regulamin/`, `/panel/login/` → 200.
- [x] **Rollback**, jeśli strona nie wstaje albo migracja się wywali: `git checkout 50421fc`, odtworzenie bazy z kopii z tego dnia, `up -d --build`.

**6d. Dane zaraz po deployu (zanim ktoś zarezerwuje)** ✅ 2026-10-21
- [x] **Najpierw** Panel → Zespół → Paulina → Usługi: dodać 14 zabiegów na twarz, które dziś ma tylko Marika (inaczej po jej wyłączeniu zniknie z formularza cała kategoria, łącznie z bezpłatną konsultacją). Sprawdzenie: w formularzu rezerwacji „Bezpłatna konsultacja” pokazuje terminy.
- [x] Panel → Zespół: Marika i Wiola → nieaktywne (`0013_catalog` przypisało im zabiegi laserowe, po wyłączeniu nie da się ich zarezerwować). Sprawdzenie: `/api/employees/` zwraca tylko Paulinę.
- [ ] Bio Pauliny: „paznocki” → „paznokci”.
- [x] Konto Pauliny: istniejące `paula` zamiast zaproszenia. W `/admin/`: `Employee` Paulina → `user = paula`; `paula` → grupa „Właściciel”, odznaczyć `is_staff`, usunąć 44 uprawnienia (właścicielka pracuje w `/panel/`, nie w `/admin/`). Sprawdzenie: Paulina loguje się na `/panel/login/` i widzi „Zespół”, „Usługi”, kalendarz.
- [x] Paulina: szablon tygodnia + generowanie grafiku (bez tego formularz nie pokazuje terminów), terminy lasera w „Urządzenia”: 8–9.11 i 14–15.12.
- [x] Rezerwacja testowa na produkcji na własny e-mail → odwołanie linkiem z maila (sprawdza Resend, `SITE_URL`, `SALON_EMAIL`).
- [x] Cron z `backup_db.sh` na Droplecie dalej działa (`crontab -l`, data najnowszego pliku w `backups/`).
- [x] Cron z przypomnieniami na Droplecie (`crontab -e`), potem po godzinie sprawdzić `logs/reminders.log`:
  `0 * * * * cd ~/salon-manager && docker compose -f docker-compose.prod.yml exec -T web uv run python manage.py send_reminders >> logs/reminders.log 2>&1`
  Na stagingu cronu nie zakładamy (tam ręcznie: `… exec web uv run python manage.py send_reminders`).

**6e. Po publikacji**
- [ ] Wizytówka Google: godziny pn–nd 9–21 i opis „wyłącznie po wcześniejszym umówieniu”, link do strony, link do rezerwacji.
- [ ] Google Search Console: zgłoszenie sitemapy, „Sprawdź URL” strony głównej → prośba o zaindeksowanie.
- [ ] Rich Results Test: `BeautySalon` + `FAQPage` bez błędów.

**6f. Wnioski z deployu (małe PR-y)**
- [ ] System check Django: `SITE_URL` musi zaczynać się od `http://` lub `https://`, inaczej start aplikacji się wywala (21.10 brak schematu po cichu zepsuł canonical i linki w mailach).
- [ ] `.dockerignore`: `.git`, `.venv`, `.env*`, `backups/`, `certs/`, `logs/` — dziś `COPY . .` wkłada do obrazu sekrety i kopie bazy z danymi klientek.
- [ ] Po deployu purge cache w Cloudflare (pliki bez hasha, np. `robots.txt`, są trzymane 4 h) — dopisać do checklisty deployu.
- [ ] Później: `Employee.photo` (ImageField w panelu) zamiast `paulina.webp`, gdy salon kogoś zatrudni.

## Po audycie z 21.10.2026 (7/10 w każdym wymiarze, łącznie 21/30)

Raport: `docs/seo-audit-royalbeauty-studiourody-pl-2026-10-21.pdf`. Trzy krytyczne problemy z poprzedniego audytu są rozwiązane, nowych krytycznych nie ma. **Główna luka:** cała oferta jest pod jednym adresem (jedna szansa na ranking dla ok. 80 usług). **Druga:** na stronie nie ma ani jednej treści opinii. Cel: 8–9/10.

Sprawdzone w kodzie, **nie wymaga zmian** (audyt się myli):
- Data lasera w FAQ i w cenniku nie jest wpisana na sztywno: `apps/services/faq.py` i `next_rentals()` biorą ją z `EquipmentRental`. Audyt widział termin 8–9.11 wpisany w panelu.
- Kroki rezerwacji są już w `<ol class="rb-steps">`.
- Nie robimy: `HowTo` i `Speakable` (niski priorytet; `Speakable` działa tylko dla wydawców wiadomości), `<table>` cennika na stronie głównej (tabele dopiero na podstronach kategorii).

### 7. Quick wins (jeden PR)
- [ ] **Meta description** w `templates/base.html` (max ok. 155 znaków), z depilacją laserową i „codziennie 9–21”, np. „Rzęsy, paznokcie, depilacja laserowa i zabiegi na twarz na Fabrycznej. Codziennie 9–21, bezpłatna konsultacja. Zarezerwuj online!”. *Akceptacja:* test na treść i długość.
- [x] **`sameAs` + Booksy**: `https://royalbeauty-studiourody.booksy.com/` (uwaga: Booksy zwraca 200 dla każdej subdomeny, także z literówką — sprawdzać `<title>`), link do profilu Booksy w JSON-LD `BeautySalon` (profil ma 90 opinii, silna encja dla AI). Potrzebny dokładny URL od Pauliny.
- [ ] **`<lastmod>` w sitemapie**: strony prawne = data „Obowiązuje od”, strona główna = ostatnia zmiana cennika. `Service` nie ma `updated_at`, więc albo dodać to pole (migracja), albo przyjąć datę deployu. Do decyzji przy realizacji.
- [ ] **`hasOfferCatalog`** w `BeautySalon`: `OfferCatalog` per kategoria → `Offer` z `price` + `priceCurrency: PLN` → `itemOffered: Service`, generowane z aktywnych `Service` (te same dane co cennik, jedno zapytanie). **Bez `aggregateRating`**: Google nie pozwala na oceny wystawiane samej sobie w `LocalBusiness`.
- [ ] **`llms.txt`** (`/llms.txt`, jak `robots.txt` przez szablon): krótki opis salonu, adres, godziny, linki do cennika, FAQ, regulaminu.
- [x] **Pełne imię i nazwisko** w `founder`: Paulina Truszkowska.

### 8. Spójność poza stroną (bez kodu, Paulina)
- [ ] **Booksy**: zespół = tylko Paulina (dziś są tam 4 osoby: Paulina, Wiola, Marika, Magdalena), godziny codziennie 9–21. Rozbieżne dane między stroną, Booksy i Google osłabiają zaufanie do encji (GEO i SEO lokalne).
- [ ] **Wizytówka Google**: te same godziny i opis (patrz 6e).
- [ ] **Cloudflare**: sprawdzić, czy „Block AI Scrapers / AI bots” jest wyłączone (inaczej GEO nie ma sensu).
- [ ] Search Console: „Ulepszenia → Często zadawane pytania” i raport Core Web Vitals (po kilku tygodniach ruchu).

### 9. Rozszerzenie FAQ (treść od Pauliny)
Odpowiedzi w tym samym formacie co dziś: 25–55 słów, zaczynające od konkretu. Te same dane w HTML i w `FAQPage` (`apps/services/faq.py`).
- [ ] Przeciwwskazania (ogólnie + laser; wciąż brakuje ich w „Do zebrania od Pauliny”).
- [ ] Ile zabiegów laserem potrzeba i co ile (brakuje „zalecanego odstępu”).
- [ ] Czy depilacja laserowa boli.
- [ ] Ile trzyma hybryda, a ile przedłużane rzęsy.
- [ ] Parking i dojazd (przystanek, tramwaj).
- [ ] Płatność kartą / BLIK.
- Przy podstronach (etap 11) pytania przechodzą do FAQ swojej kategorii, a na stronie głównej zostają ogólne.

### 10. Prawdziwe opinie na stronie
Rekomendacja audytu: 3–6 cytatów z imieniem, datą i źródłem + „4,9/5 · 90 opinii na Booksy”, przy sekcji `#opinie`.
- [ ] **Decyzja:** ustaliliśmy wcześniej „Places API albo link, bez ręcznego kopiowania”. Opcje: (a) Google Places API (automatycznie, ale klucz API, limit 5 opinii, opinie Google, nie Booksy, warunki wyświetlania); (b) ręcznie wybrane cytaty w bazie (np. model `Review` edytowany w panelu: treść, imię, data, źródło, link), za zgodą autorek albo tylko z imieniem i inicjałem; (c) zostaje link.
- [ ] Bez `Review`/`aggregateRating` w schema (zasada Google jak wyżej). Cytaty muszą być prawdziwe i datowane.

### 11. Podstrony kategorii (SEO long-tail, największy wpływ)
Pięć stron, każda z własnym `title` i H1, min. 500 słów, cennikiem kategorii w `<table>`, FAQ kategorii, zdjęciami, CTA do rezerwacji z wybraną kategorią i linkiem ze strony głównej (nagłówek kategorii w cenniku → podstrona). **Zaczynamy od depilacji laserowej** (najwyższe ceny, mała konkurencja lokalna, konkretne urządzenie).
- [ ] **Decyzja: adresy.** Audyt proponuje `/depilacja-laserowa-wroclaw/`, plan miał `/uslugi/<slug>/`. Rekomendacja: `/uslugi/depilacja-laserowa/` (czysta hierarchia pod `BreadcrumbList`, slug już istnieje, miasto i tak jest w `title` i H1; słowo w URL to dziś słaby sygnał).
- [ ] Model: `ServiceCategory` + `seo_title`, `meta_description`, `intro` (TextField). FAQ kategorii: osobny model (`FaqItem`, FK do kategorii, kolejność) edytowany w panelu albo w kodzie jak dziś (`faq.py`). Do decyzji przy realizacji.
- [ ] Widok `DetailView` po slugu (tylko kategorie z aktywnymi usługami), szablon z `base.html`, bloki `meta_description` i JSON-LD.
- [ ] JSON-LD per podstrona: `Service`/`OfferCatalog` z `provider` → `@id` salonu, `BreadcrumbList`, `FAQPage` z tych samych danych co HTML.
- [ ] `CategorySitemap` w `config/sitemaps.py` z `lastmod`.
- [ ] Treść: Paulina (opis zabiegów, efekty, przeciwwskazania, przygotowanie). Developer składa, Paulina zatwierdza, bo to treści o zdrowiu.
- Kolejność: depilacja laserowa → rzęsy i brwi → dłonie i stopy → zabiegi kosmetyczne → depilacja woskiem.

### 12. Poradniki (GEO)
2–4 artykuły, które najczęściej trafiają do cytowań AI: „Pielęgnacja rzęs po przedłużaniu”, „Laser diodowy czy wosk?”, „Jak przygotować się do mezoterapii mikroigłowej”.
- [ ] **Decyzja:** blog w bazie (model `Article` + panel) czy kilka stron w szablonach. Przy 2–4 tekstach wystarczą szablony; model, jeśli Paulina chce pisać sama.
- [ ] Każdy z autorką (`Article` + `author` → Paulina, `datePublished`), linkiem do podstrony kategorii i w sitemapie.

### 13. Na koniec
- [ ] RODO w panelu: „Usuń klientkę” (z anonimizacją jej wizyt) oraz komenda czyszcząca karty i wizyty starsze niż 3 lata od ostatniej wizyty (tak obiecuje polityka prywatności; pierwsze dane się „przedawnią” jesienią 2029, ale lepiej zrobić to wcześniej).
- [ ] Ponowny audyt SEO/GEO/AEO po etapach 7–11.
