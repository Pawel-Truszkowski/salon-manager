# Roadmapa

Tylko to, co przed nami. Zrobione etapy i decyzje, które do nich doprowadziły, są w [archive/](archive/): `seo-plan.md` (SEO/GEO/AEO, redesign, deploy produkcji, etapy 0–13) i `panel-plan.md` (panel, etapy 1–4). Architektura i zasady działania kodu: [CLAUDE.md](../CLAUDE.md).

Stan: produkcja = `main` = `dev` od 28.10.2026 (etapy SEO 7–12). Każde zadanie to osobny PR na `dev`, gałąź od `dev`.

## Następne (w tej kolejności)

### 1. RODO w panelu
- [ ] „Usuń klientkę” (właścicielka): karta znika, jej wizyty zostają zanonimizowane (statystyki dalej się zgadzają).
- [ ] Komenda czyszcząca karty i wizyty starsze niż 3 lata od ostatniej wizyty — tak obiecuje polityka prywatności. Pierwsze dane „przedawnią się” jesienią 2029, ale lepiej mieć to wcześniej. Uruchamiana z crona hosta, jak `send_reminders`.

### 2. Cena i czas trwania zapisane w wizycie (snapshot)
- [ ] `Appointment` zapamiętuje `price` i `duration` przy zapisie. Dziś zmiana usługi zmienia wstecz długość zapisanych wizyt i historyczny przychód.
- [ ] Migracja danych wypełnia istniejące wizyty bieżącymi wartościami usług.
- Warunek dla etapu 3.

### 3. Statystyki (tylko właścicielka)
- [ ] Liczba wizyt, przychód (z ceny zapisanej w wizycie), obłożenie specjalistek, odsetek anulacji — w wybranym okresie.

### 4. Ponowny audyt SEO/GEO/AEO
- [ ] Po etapach 7–12 (ostatni: 21.10 → 7/7/7, cel 8–9). Porównać z raportem z 28.10.

## Drobne, niezależne

- [ ] **Kontener `web`:** `command` w `docker-compose.prod.yml` używa `uv run`, które przy każdym starcie doinstalowuje zależności deweloperskie (ruff, pytest), choć obraz jest budowany z `--no-dev`. Do poprawy: `uv run --no-sync` albo wywołanie binarek z `.venv`.
- [ ] **`Employee.email` — dokończyć usuwanie** (expand/contract): ✅ panel i API go nie pokazują → zaproszenia podpowiadają adres z `Employee.email` → usunąć z admina i fixtur → backup bazy + migracja `RemoveField`.
- [ ] **`Employee.photo`** (ImageField wgrywany w panelu) zamiast stałego `paulina.webp` — gdy salon kogoś zatrudni.
- [ ] **Zdjęcia prac na podstronach kategorii** — gdy Paulina je dostarczy.
- [ ] **Grafik:** edycja pojedynczych dni (wyjątki) w panelu — dziś tylko przez `/admin/`.
- [ ] **Laser w schema:** `Offer` z `availabilityStarts` / `availabilityEnds` z `EquipmentRental` na podstronie depilacji laserowej (niski priorytet).
- [ ] **Sprzęt przy kilku osobach:** sprawdzanie, czy urządzenie nie jest zajęte przez inną wizytę w tym samym czasie — dopiero gdy będą pracownice.

## Do sprawdzenia (poza kodem)

Punkty, które w starych planach zostały nieodhaczone, a ich stanu nie widać w repo. Odhaczyć albo usunąć po sprawdzeniu.

- [ ] Search Console: sitemapa zgłoszona, strona główna zaindeksowana; „Ulepszenia” i Rich Results Test (`BeautySalon`, `FAQPage`, `BlogPosting`) bez błędów.
- [ ] Wizytówka Google: godziny pn–nd 9–21, „wyłącznie po wcześniejszym umówieniu”, link do strony i do rezerwacji.
- [ ] Paulina wpisała pierwszą ocenę z Booksy w `/panel/reviews/`; sekcja opinii obejrzana na telefonie (karty Google widać tylko na produkcji).
- [ ] PageSpeed Insights (mobile) na produkcji.
- [ ] Dane w panelu (Paulina): literówka „paznocki” w bio, nazwy usług ze spacjami w nawiasach („Mezoterapia mikroigłowa ( twarz)”), „Manicure hybrydowy french/ babyboomer”.
- [ ] Laser: przeciwwskazania i odstęp między zabiegami od Pauliny (dziś z ogólnej wiedzy, zatwierdzone przez nią).
- [ ] Umowa powierzenia przetwarzania danych między Pauliną a osobą utrzymującą stronę.

## Zasady, które obowiązują dalej

**Role w panelu**

| | Developer (superuser) | Właścicielka | Specjalistka |
|---|---|---|---|
| `/admin/` Django | ✅ | ❌ | ❌ |
| Wizyty: potwierdź / anuluj / przenieś / dodaj | wszystkie | wszystkie | tylko swoje |
| Grafik i blokady | wszystkie | wszystkie | tylko swoje |
| Specjalistki, konta, usługi, klientki, sprzęt, opinie | ✅ | ✅ | ❌ |
| Kalendarz | ✅ | wszystkie specjalistki | tylko swój |
| Statystyki | ✅ | ✅ | ❌ |

**Treść i SEO**
- Treści o zdrowiu (zabiegi, przeciwwskazania, pielęgnacja) pisze developer, zatwierdza Paulina przed produkcją.
- Strona dopasowuje się do liczby aktywnych `Employee` — nigdy nie wpisujemy „jedna specjalistka” na sztywno.
- Bez `aggregateRating` / `Review` w schema (Google nie pozwala na oceny wystawiane samemu sobie w `LocalBusiness`).
- Opinii z Google nie zapisujemy w bazie ani w fixturach — tylko cache (warunki Google).
- Jedno pytanie FAQ tylko na jednej stronie (pilnuje tego test).
- `Guide.modified` i `LEGAL_EFFECTIVE_DATE` zmieniamy, gdy treść zmienia się merytorycznie (to `<lastmod>` w sitemapie).

**Deploy**
- Produkcja ręcznie, po sprawdzeniu na stagingu, zawsze z kopią bazy przed (`./scripts/backup_db.sh --env prod`). Nigdy nie otwieramy PR `main` → `dev`.
