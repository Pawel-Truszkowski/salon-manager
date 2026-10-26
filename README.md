# Salon Manager

Aplikacja webowa salonu kosmetycznego Royal Beauty Studio Urody we Wrocławiu: strona wizytówkowa z cennikiem, rezerwacją online i przypomnieniami e-mail oraz własny panel do prowadzenia salonu (wizyty, grafik, kalendarz, zespół, usługi, klientki).

🌐 **Produkcja:** [royalbeauty-studiourody.pl](https://royalbeauty-studiourody.pl) · **Staging:** [dev.royalbeauty-studiourody.pl](https://dev.royalbeauty-studiourody.pl)

> **Status projektu:** działa na produkcji od 21.10.2026 (nowa strona + panel). Dalszy rozwój (SEO, podstrony usług, opinie) — patrz [Roadmapa](#roadmapa).

## Spis treści

- [Funkcje](#funkcje)
- [Stack technologiczny](#stack-technologiczny)
- [Architektura](#architektura)
- [Wymagania](#wymagania)
- [Uruchomienie lokalne](#uruchomienie-lokalne)
- [Uruchomienie przez Docker](#uruchomienie-przez-docker)
- [Zmienne środowiskowe](#zmienne-środowiskowe)
- [Lint i testy](#lint-i-testy)
- [Deployment](#deployment)
- [Zadania cykliczne (cron)](#zadania-cykliczne-cron)
- [Struktura projektu](#struktura-projektu)
- [Roadmapa](#roadmapa)

## Funkcje

**Strona dla klientek**
- Cennik renderowany po stronie serwera (zakładki kategorii, opisy, ceny, czas trwania) — widoczny dla Google i botów AI bez JavaScriptu
- Rezerwacja online: wybór zabiegu, dnia i wolnej godziny; specjalistka do wyboru tylko, gdy w salonie pracuje więcej niż jedna osoba
- „Najbliższy wolny termin” liczony z grafiku; zabiegi wymagające wynajmowanego sprzętu (laser) tylko w dni wynajmu
- E-maile: potwierdzenie rezerwacji, potwierdzenie przez salon, zmiana terminu, odwołanie, **przypomnienie ok. 24 h przed wizytą**
- Samodzielne odwołanie wizyty linkiem z maila
- Profil salonu i właścicielki, FAQ, dojazd, polityka prywatności i regulamin rezerwacji
- SEO: jeden H1, Open Graph, JSON-LD (`BeautySalon`, `FAQPage`), `sitemap.xml`, `robots.txt`, obrazy WebP, fonty hostowane lokalnie, polskie strony 404/500

**Panel salonu (`/panel/`)**
- Logowanie, reset hasła, zaproszenia do panelu dla nowych specjalistek
- Wizyty: lista z filtrami, potwierdzanie, realizacja, odwołanie, zmiana terminu, dodawanie wizyt telefonicznych (z podpowiedziami z kartoteki klientek)
- Kalendarz (FullCalendar) z przeciąganiem wizyt i grafikiem w tle
- Grafik: szablon tygodnia → generowanie grafiku na wybrany okres, blokady (urlopy, przerwy)
- Zespół, usługi, klientki, wynajem urządzeń — tylko dla właścicielki
- Specjalistka widzi i zmienia wyłącznie swoje dane

## Stack technologiczny

- **Backend:** Django 6, Django REST Framework, Python 3.14
- **Baza danych:** PostgreSQL 16 (Docker), SQLite w testach
- **E-mail:** django-anymail (Resend)
- **Frontend:** Django Templates, Bootstrap 5, vanilla JS, FullCalendar v6 (panel) — bez osobnego builda
- **Zależności:** [uv](https://docs.astral.sh/uv/)
- **Lint/format:** Ruff
- **Testy:** pytest / pytest-django
- **Serwer:** Gunicorn + Nginx w Docker Compose, Cloudflare przed produkcją
- **CI/CD:** GitHub Actions (lint + testy, automatyczny deploy stagingu)
- **Hosting:** DigitalOcean Droplet (produkcja), VPS Mikrus (staging)

## Architektura

Aplikacje Django w katalogu `apps/`:

| Aplikacja  | Odpowiedzialność |
| ---------- | ---------------- |
| `accounts` | Własny model `User` (`AbstractUser` + telefon), role (`roles.py`) |
| `services` | Kategorie, usługi, specjalistki (`Employee`), grafik (`Schedule`, `WeeklyScheduleEntry`, `TimeBlock`), sprzęt i jego wynajem, FAQ, generowanie grafiku |
| `bookings` | `Appointment`, `Client`, formularz i widok rezerwacji, logika dostępności (`utils.py`), e-maile, przypomnienia (`reminders.py` + komenda `send_reminders`) |
| `panel`    | Panel salonu: widoki, formularze, mixiny dostępu, zaproszenia |
| `api`      | Endpointy DRF: usługi, specjalistki, wolne godziny i dni |

**Role:** *właścicielka* (grupa `Właściciel`) zarządza całym salonem w `/panel/`; *specjalistka* (`User` powiązany z `Employee`) widzi tylko swoje wizyty i grafik. `/admin/` służy wyłącznie developerowi.

**Kluczowe relacje danych:**
- `Employee` ↔ `Service` — M2M; `Employee.user` — opcjonalne konto w panelu
- `Schedule` / `TimeBlock` → `Employee` — godziny pracy i blokady; `WeeklyScheduleEntry` to szablon, z którego powstają wpisy `Schedule`
- `Service.required_equipment` → `Equipment` + `EquipmentRental` — usługa dostępna tylko w dni wynajmu sprzętu
- `Appointment` → `Service` + `Employee` + `Client` (jedna karta na numer telefonu) + status (`pending` / `confirmed` / `completed` / `cancelled`)

Ustawienia (`config/settings/`) są rozdzielone na `base.py`, `development.py`, `production.py` i samodzielny `test.py` (SQLite, e-maile w pamięci). Szczegóły architektury i przepływu rezerwacji: [CLAUDE.md](CLAUDE.md).

## Wymagania

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- PostgreSQL (lokalnie albo z `docker-compose.dev.yml`)
- Docker + Docker Compose (opcjonalnie lokalnie, wymagane na serwerach)

## Uruchomienie lokalne

```bash
uv sync                                   # zależności z lockfile'a
cp .env.example .env.dev                  # i uzupełnij wartości
uv run python manage.py migrate
uv run python manage.py createsuperuser   # konto developera (/admin/ i /panel/)
uv run python manage.py runserver
```

Strona: `http://localhost:8000`, panel: `http://localhost:8000/panel/`, admin: `http://localhost:8000/admin/`.

## Uruchomienie przez Docker

```bash
docker compose -f docker-compose.dev.yml up --build      # development (hot-reload)
docker compose -f docker-compose.prod.yml up -d --build  # produkcja / staging (Gunicorn + Nginx)
```

Kontener `web` w obu wariantach uruchamia `migrate` przy starcie.

## Zmienne środowiskowe

Wzór: [.env.example](.env.example) — skopiuj jako `.env.dev` (lokalnie) lub `.env.prod` (serwery). Nigdy nie commituj tych plików. Django czyta z dysku tylko `.env.dev`; `.env.prod` trafia do kontenerów przez `env_file` w `docker-compose.prod.yml`.

| Zmienna | Opis |
| ------- | ---- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` / `config.settings.production` |
| `SECRET_KEY` | Klucz Django |
| `ALLOWED_HOSTS` | Dozwolone hosty |
| `DATABASE_URL` | Connection string do bazy |
| `POSTGRES_DB/USER/PASSWORD` | Dane bazy PostgreSQL (Docker) |
| `DB_HOST` / `DB_PORT` | Host i port bazy |
| `RESEND_API_KEY` | Klucz API Resend |
| `DEFAULT_FROM_EMAIL` | Nadawca e-maili |
| `SALON_EMAIL` | Adres salonu na powiadomienia o rezerwacjach i odwołaniach |
| `SITE_URL` | Bazowy adres **ze schematem** (`https://…`): linki w mailach, canonical, Open Graph, JSON-LD |
| `NGINX_CONF` | Tylko staging: `dev.conf` w pliku `.env` w katalogu projektu (nie w `.env.prod`) — compose czyta go przy interpolacji |

## Lint i testy

```bash
uv run ruff check --fix   # lint + sortowanie importów
uv run ruff format        # formatowanie
uv run pytest             # ok. 425 testów
```

Testy (`tests/`, konfiguracja w [pytest.ini](pytest.ini)) pokrywają modele, formularze, widoki, panel, API, e-maile, przypomnienia, logikę dostępności i migracje danych. CI odrzuca zmiany, które nie przechodzą lintu, formatowania lub testów.

## Deployment

| Środowisko | Hosting | Branch | Adres | Wdrożenie |
| ---------- | ------- | ------ | ----- | --------- |
| **Produkcja** | DigitalOcean Droplet (`~/salon-manager`) | `main` | [royalbeauty-studiourody.pl](https://royalbeauty-studiourody.pl) | Ręcznie po SSH, po sprawdzeniu na stagingu |
| **Staging** | VPS [Mikrus](https://mikr.us/) (`~/projects/salon-manager`) | `dev` | [dev.royalbeauty-studiourody.pl](https://dev.royalbeauty-studiourody.pl) | Automatycznie przez GitHub Actions po pushu na `dev` |

Przepływ: gałąź od `dev` → PR do `dev` → (CI + staging) → PR `dev` → `main` (merge commit) → ręczny deploy produkcji.

[.github/workflows/deploy.yml](.github/workflows/deploy.yml): na pushu na `dev` i PR-ach do `main` uruchamia Ruff i testy; po pushu na `dev` łączy się po SSH ze stagingiem (`git pull origin dev` + `docker compose -f docker-compose.prod.yml up -d --build`). Zmiany tylko w `*.md` i `docs/` nie uruchamiają CI.

**Deploy produkcji (skrót):**
1. Kopia bazy: `./scripts/backup_db.sh --env prod` (jedyny rollback — migracje danych nie mają cofania).
2. Merge PR `dev` → `main`, na Droplecie `git pull origin main` i `docker compose -f docker-compose.prod.yml up -d --build`.
3. `docker compose -f docker-compose.prod.yml logs web` — migracje `OK`, Gunicorn uruchomiony. Błąd `bookings.E001` = `SITE_URL` w `.env.prod` bez `https://` (kontener celowo nie startuje).
4. Cloudflare → Purge cache (pliki bez hasha w nazwie, np. `robots.txt`, są w cache do 4 h).
5. Smoke test: przekierowania www/http → `https://royalbeauty-studiourody.pl/`, strona, panel, `robots.txt`, `sitemap.xml`.

Pełna checklista z pierwszego wdrożenia: [docs/seo-plan.md](docs/seo-plan.md), etap 6.

## Zadania cykliczne (cron)

Na serwerze produkcyjnym (crontab hosta, poza procesem deployu):

| Zadanie | Kiedy | Polecenie |
| ------- | ----- | --------- |
| Przypomnienia o wizytach | co godzinę | `docker compose -f docker-compose.prod.yml exec -T web uv run python manage.py send_reminders` |
| Backup bazy | wg crontaba serwera | `./scripts/backup_db.sh --env prod` (`--keep N`, domyślnie 10 kopii) |

Przypomnienie dostają potwierdzone wizyty z e-mailem, zaczynające się w ciągu 24 h i zarezerwowane co najmniej 24 h wcześniej — raz na wizytę (ponownie po zmianie terminu).

## Struktura projektu

```
apps/
  accounts/     # Model użytkownika, role
  api/          # Endpointy REST (DRF)
  bookings/     # Rezerwacje, klientki, e-maile, przypomnienia, logika dostępności
  panel/        # Panel salonu (/panel/)
  services/     # Usługi, specjalistki, grafik, sprzęt, FAQ
config/
  settings/     # base / development / production / test
  urls.py, sitemaps.py, context_processors.py, asgi.py, wsgi.py
templates/      # Szablony HTML (strona, panel, e-maile, strony prawne)
static/         # CSS, JS, fonty, obrazy
tests/          # Testy pytest
scripts/        # backup_db.sh
nginx/          # prod.conf (produkcja), dev.conf (staging)
docs/           # Plany: panel-plan.md, seo-plan.md, redesign/
.env.example    # Wzór zmiennych środowiskowych
```

## Roadmapa

Szczegóły: [docs/seo-plan.md](docs/seo-plan.md) (etapy 7–13) i [docs/panel-plan.md](docs/panel-plan.md).

- SEO quick wins: meta description, `hasOfferCatalog` z cennika, `<lastmod>` w sitemapie, `llms.txt`
- Rozszerzone FAQ (przeciwwskazania, laser, trwałość zabiegów, dojazd, płatności)
- Prawdziwe opinie klientek na stronie
- Podstrony kategorii usług (zaczynając od depilacji laserowej) i poradniki
- Statystyki dla właścicielki (wizyty, przychód, obłożenie, anulacje)
- RODO w panelu: usuwanie klientki, automatyczne czyszczenie starych danych
- Zdjęcia specjalistek wgrywane w panelu
