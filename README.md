# Salon Manager

Aplikacja webowa do zarządzania rezerwacjami w salonie kosmetycznym — strona wizytówkowa z katalogiem usług, wyborem specjalistki i terminu oraz automatycznymi powiadomieniami mailowymi o rezerwacji.

🌐 **Aplikacja działa na produkcji:** [royalbeauty-studiourody.pl](https://royalbeauty-studiourody.pl)

> **Status projektu:** aktywnie rozwijany. Część funkcji i usprawnień (m.in. panel klienta, rozbudowa API, dalsze pokrycie testami) jest jeszcze w planach — patrz sekcja [Roadmapa](#roadmapa).

## Spis treści

- [Funkcje](#funkcje)
- [Stack technologiczny](#stack-technologiczny)
- [Architektura](#architektura)
- [Wymagania](#wymagania)
- [Uruchomienie lokalne](#uruchomienie-lokalne)
- [Uruchomienie przez Docker](#uruchomienie-przez-docker)
- [Zmienne środowiskowe](#zmienne-środowiskowe)
- [Testy](#testy)
- [Deployment](#deployment)
- [Backupy bazy danych](#backupy-bazy-danych)
- [Struktura projektu](#struktura-projektu)
- [Roadmapa](#roadmapa)

## Funkcje

- Strona główna z kategoriami usług, galerią i formularzem rezerwacji
- REST API do pobierania usług, specjalistek oraz dostępnych terminów/godzin
- Automatyczne wyszukiwanie wolnej specjalistki dla wybranej usługi i terminu
- Statusy rezerwacji (oczekująca / potwierdzona / zrealizowana / anulowana) z akcjami w panelu admina
- E-mail z potwierdzeniem rezerwacji do klienta oraz powiadomieniem dla salonu
- Panel administracyjny Django do zarządzania usługami, specjalistkami, grafikami i rezerwacjami
- Mapa strony (`sitemap.xml`) i `robots.txt` pod SEO

## Stack technologiczny

- **Backend:** Django 6, Django REST Framework
- **Baza danych:** PostgreSQL (Docker/produkcja), SQLite (opcjonalnie lokalnie)
- **E-mail:** django-anymail (Resend)
- **Frontend:** Django Templates, Bootstrap 5, vanilla JS
- **Zależności:** zarządzane przez [uv](https://docs.astral.sh/uv/)
- **Serwer aplikacji:** Gunicorn + Nginx (produkcja)
- **Testy:** pytest / pytest-django
- **CI/CD:** GitHub Actions (testy + automatyczny deployment środowiska deweloperskiego po SSH)
- **Hosting:** Digital Ocean Droplet (produkcja), VPS Mikrus (środowisko deweloperskie/staging)

## Architektura

Projekt jest podzielony na niezależne aplikacje Django w katalogu `apps/`:

| Aplikacja  | Odpowiedzialność                                                             |
| ---------- | ----------------------------------------------------------------------------- |
| `accounts` | Własny model użytkownika (`AbstractUser` + numer telefonu)                    |
| `services` | Kategorie usług, usługi, specjalistki (`Employee`), grafiki i bloki czasowe   |
| `bookings` | Model `Appointment`, formularz i widok rezerwacji, e-maile, logika dostępności |
| `api`      | Endpointy DRF (usługi, specjalistki, dostępne terminy/godziny)               |

Kluczowe relacje danych:

- `Employee` ↔ `Service` — relacja M2M (specjalistka może wykonywać wiele usług)
- `Schedule` / `TimeBlock` → `Employee` — godziny pracy i blokady terminów
- `Appointment` → `Service` + `Employee` + dane klienta + status

Konfiguracja Django (`config/`) rozdziela ustawienia na `base.py`, `development.py`, `production.py` i `test.py`.

## Wymagania

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- PostgreSQL (lub SQLite do szybkich testów lokalnych)
- Docker + Docker Compose (opcjonalnie, do uruchomienia w kontenerach)

## Uruchomienie lokalne

```bash
# Instalacja zależności z lockfile'a
uv sync

# Skopiuj przykładowy plik i uzupełnij realnymi wartościami
cp .env.example .env.dev

# Migracje bazy danych
uv run python manage.py migrate

# Utworzenie konta administratora
uv run python manage.py createsuperuser

# Uruchomienie serwera deweloperskiego
uv run python manage.py runserver
```

Aplikacja będzie dostępna pod `http://localhost:8000`, panel admina pod `http://localhost:8000/admin/`.

## Uruchomienie przez Docker

**Development** (hot-reload, wolumen z kodem):

```bash
docker compose -f docker-compose.dev.yml up --build
```

**Produkcja** (Gunicorn + Nginx, statyki i media w wolumenach):

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## Zmienne środowiskowe

Konfiguracja wczytywana jest z plików `.env.dev` / `.env.prod` (django-environ). Wzór ze wszystkimi zmiennymi znajduje się w [.env.example](.env.example) — skopiuj go jako `.env.dev` lub `.env.prod` i uzupełnij realnymi wartościami (nigdy nie commituj tych plików). Wymagane zmienne:

| Zmienna                | Opis                                                    |
| ----------------------- | -------------------------------------------------------- |
| `DJANGO_SETTINGS_MODULE`| Moduł ustawień (`config.settings.development`/`production`) |
| `SECRET_KEY`            | Klucz Django                                            |
| `ALLOWED_HOSTS`         | Lista dozwolonych hostów                                |
| `DATABASE_URL`          | Connection string do bazy danych                        |
| `POSTGRES_DB/USER/PASSWORD` | Dane bazy PostgreSQL (Docker)                       |
| `DB_HOST` / `DB_PORT`   | Host i port bazy danych                                 |
| `RESEND_API_KEY`        | Klucz API Resend do wysyłki e-maili                     |
| `DEFAULT_FROM_EMAIL`    | Adres nadawcy e-maili                                   |
| `SALON_EMAIL`           | Adres, na który przychodzą powiadomienia o rezerwacjach |

## Testy

```bash
uv run pytest
```

Konfiguracja testów znajduje się w [pytest.ini](pytest.ini) i korzysta z `config.settings.test`. Testy skupiają się na głównej logice biznesowej aplikacji — modelach, formularzach, widokach, panelu admina i funkcjach pomocnicznych (`tests/`). Nie jest to pełne pokrycie kodu — priorytetem było zabezpieczenie kluczowych ścieżek (rezerwacje, dostępność terminów), a nie 100% coverage.

## Deployment

Projekt działa równolegle w dwóch środowiskach, każde na osobnym VPS-ie:

| Środowisko | Hosting | Branch | Adres | Sposób wdrożenia |
| ---------- | ------- | ------ | ----- | ------------------ |
| **Produkcja** | Digital Ocean Droplet | `main` | [royalbeauty-studiourody.pl](https://royalbeauty-studiourody.pl) | Ręcznie — po zmergowaniu do `main` deploy wykonywany jest po SSH na Droplecie (`git pull`, restart kontenerów) |
| **Development / staging** | VPS [Mikrus](https://mikr.us/) | `dev` | wewnętrzny/testowy | Automatycznie przez GitHub Actions przy każdym pushu na `dev` |

Oba środowiska uruchamiają aplikację w całości przez Docker Compose (Gunicorn + Nginx, patrz [docker-compose.prod.yml](docker-compose.prod.yml)).

Automatyczny deployment środowiska deweloperskiego skonfigurowany jest w [.github/workflows/deploy.yml](.github/workflows/deploy.yml):

1. Push/PR uruchamia testy (`uv run pytest`).
2. Po pushu na `dev` workflow łączy się po SSH z serwerem Mikrus, pobiera zmiany (`git pull origin dev`) i restartuje kontenery (`docker-compose.prod.yml`).

Wdrożenie na produkcję (Digital Ocean) nie jest jeszcze zautomatyzowane w CI — wykonywane jest świadomie ręcznie, po zweryfikowaniu zmian na środowisku deweloperskim.

## Backupy bazy danych

Skrypt [scripts/backup_db.sh](scripts/backup_db.sh) tworzy skompresowany zrzut bazy (`.sql.gz`). Na produkcji uruchamiany jest automatycznie przez cron na serwerze (`--env prod`), niezależnie od procesu deployu.

## Struktura projektu

```
apps/
  accounts/     # Model użytkownika
  api/          # Endpointy REST (DRF)
  bookings/     # Rezerwacje: model, formularz, widok, e-maile
  services/     # Usługi, specjalistki, grafiki
config/
  settings/     # base / development / production / test
  urls.py, sitemaps.py, asgi.py, wsgi.py
templates/      # Szablony HTML (w tym e-maile)
static/         # CSS, JS, obrazy
tests/          # Testy pytest
scripts/        # Skrypty pomocnicze (backup bazy)
nginx/          # Konfiguracja Nginx (produkcja)
.env.example    # Wzór zmiennych środowiskowych
```

## Roadmapa

Projekt jest w aktywnym rozwoju. Planowane / rozważane usprawnienia:

- Panel klienta z historią i zarządzaniem własnymi rezerwacjami
- Rozszerzenie testów o dodatkowe scenariusze brzegowe i wyższe pokrycie kodu
- Powiadomienia SMS / przypomnienia o wizytach
- Kalendarz specjalistki w panelu admina (widok graficzny zamiast listy)

Zgłoszenia i propozycje mile widziane w Issues.
