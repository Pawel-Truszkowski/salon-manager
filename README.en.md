# Salon Manager

[🇵🇱 Polski](README.md) · 🇬🇧 English

Web application for Royal Beauty Studio Urody, a beauty salon in Wrocław, Poland: a business website with a price list, online booking and e-mail reminders, plus a custom staff panel for running the salon (appointments, schedule, calendar, team, services, clients, reviews).

🌐 **Production:** [royalbeauty-studiourody.pl](https://royalbeauty-studiourody.pl) · **Staging:** [dev.royalbeauty-studiourody.pl](https://dev.royalbeauty-studiourody.pl)

> **Project status:** live in production since 21 Oct 2026 (new website + panel). SEO stages 7–12 shipped on 28 Oct 2026: category pages, guides, Google and Booksy reviews, `llms.txt`. Next steps: see [Roadmap](#roadmap).
>
> The site content, the panel and the code comments are in Polish; this document is a translation of the Polish README.

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Running locally](#running-locally)
- [Running with Docker](#running-with-docker)
- [Environment variables](#environment-variables)
- [Lint and tests](#lint-and-tests)
- [Deployment](#deployment)
- [Scheduled jobs (cron)](#scheduled-jobs-cron)
- [Project structure](#project-structure)
- [Roadmap](#roadmap)

## Features

**Public website**
- Server-rendered price list (category tabs, descriptions, prices, durations) — visible to Google and AI bots without JavaScript
- Online booking: choose a treatment, a day and a free time slot; the specialist picker appears only when more than one person works at the salon
- "Next available date" computed from the schedule; treatments that need rented equipment (the laser) are bookable only on rental days
- E-mails: booking received, confirmed by the salon, rescheduled, cancelled, **reminder about 24 h before the appointment**
- Self-service cancellation via a link in the e-mail
- Salon and owner profile, FAQ, directions, privacy policy and booking terms
- **Category pages** (`/uslugi/<slug>/`, five categories): treatment descriptions, the category's price list as a table, a dedicated FAQ
- **Guides** (`/poradniki/`): articles by the cosmetologist, cross-linked with the category pages
- **Reviews:** rating and up to 5 reviews from Google (Places API, cache only — Google's terms forbid storing them) and the Booksy rating entered in the panel
- SEO/GEO: a single H1, meta description, Open Graph, JSON-LD generated from the database (`BeautySalon`, `hasOfferCatalog` from the price list, `FAQPage`, `BreadcrumbList`, `BlogPosting`), `sitemap.xml` with `<lastmod>`, `robots.txt`, `llms.txt`, WebP images, self-hosted fonts, Polish 404/500 pages

**Salon panel (`/panel/`)**
- Login, password reset, panel invitations for new specialists
- Appointments: filtered list, confirm, complete, cancel, reschedule, add phone bookings (with suggestions from the client records)
- Calendar (FullCalendar) with drag & drop and working hours in the background
- Schedule: weekly template → generate the schedule for a chosen period, time blocks (holidays, breaks)
- Team, services, clients, equipment rentals, Booksy rating (`/panel/reviews/`) — owner only
- A specialist sees and edits only their own data

## Tech stack

- **Backend:** Django 6, Django REST Framework, Python 3.14
- **Database:** PostgreSQL 16 (Docker), SQLite in tests
- **E-mail:** django-anymail (Resend)
- **Frontend:** Django templates, Bootstrap 5, vanilla JS, FullCalendar v6 (panel) — no separate build step
- **Dependencies:** [uv](https://docs.astral.sh/uv/)
- **Lint/format:** Ruff
- **Tests:** pytest / pytest-django
- **Server:** Gunicorn + Nginx in Docker Compose, Cloudflare in front of production
- **CI/CD:** GitHub Actions (lint + tests, automatic staging deploy)
- **Hosting:** DigitalOcean Droplet (production), Mikrus VPS (staging)

## Architecture

Django apps in `apps/`:

| App        | Responsibility |
| ---------- | -------------- |
| `accounts` | Custom `User` model (`AbstractUser` + phone number), roles (`roles.py`) |
| `services` | Categories, services, specialists (`Employee`), schedule (`Schedule`, `WeeklyScheduleEntry`, `TimeBlock`), equipment and its rentals, schedule generation, FAQ, category pages (`category_pages.py`), guides (`guides.py`), JSON-LD (`schema.py`), Google reviews (`google_reviews.py`) and `BooksyRating` |
| `bookings` | `Appointment`, `Client`, booking form and view, availability logic (`utils.py`), e-mails, reminders (`reminders.py` + the `send_reminders` command) |
| `panel`    | Salon panel: views, forms, access mixins, invitations |
| `api`      | DRF endpoints: services, specialists, free time slots and dates |

**Roles:** the *owner* (`Właściciel` group) manages the whole salon in `/panel/`; a *specialist* (a `User` linked to an `Employee`) sees only their own appointments and schedule. `/admin/` is for the developer only.

**Key data relationships:**
- `Employee` ↔ `Service` — M2M; `Employee.user` — optional panel account
- `Schedule` / `TimeBlock` → `Employee` — working hours and blocked periods; `WeeklyScheduleEntry` is the template that `Schedule` rows are generated from
- `Service.required_equipment` → `Equipment` + `EquipmentRental` — the service is available only on equipment rental days
- `Appointment` → `Service` + `Employee` + `Client` (one record per phone number) + status (`pending` / `confirmed` / `completed` / `cancelled`)

Settings (`config/settings/`) are split into `base.py`, `development.py`, `production.py` and a standalone `test.py` (SQLite, in-memory e-mail). Architecture and booking flow details: [CLAUDE.md](CLAUDE.md).

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- PostgreSQL (local or from `docker-compose.dev.yml`)
- Docker + Docker Compose (optional locally, required on the servers)

## Running locally

```bash
uv sync                                   # dependencies from the lockfile
cp .env.example .env.dev                  # then fill in the values
uv run python manage.py migrate
uv run python manage.py createsuperuser   # developer account (/admin/ and /panel/)
uv run python manage.py runserver
```

Website: `http://localhost:8000`, panel: `http://localhost:8000/panel/`, admin: `http://localhost:8000/admin/`.

## Running with Docker

```bash
docker compose -f docker-compose.dev.yml up --build      # development (hot reload)
docker compose -f docker-compose.prod.yml up -d --build  # production / staging (Gunicorn + Nginx)
```

In both variants the `web` container runs `migrate` on start.

## Environment variables

Template: [.env.example](.env.example) — copy it to `.env.dev` (local) or `.env.prod` (servers). Never commit these files. Django reads only `.env.dev` from disk; `.env.prod` reaches the containers via `env_file` in `docker-compose.prod.yml`.

| Variable | Description |
| -------- | ----------- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` / `config.settings.production` |
| `SECRET_KEY` | Django secret key |
| `ALLOWED_HOSTS` | Allowed hosts |
| `DATABASE_URL` | Database connection string |
| `POSTGRES_DB/USER/PASSWORD` | PostgreSQL credentials (Docker) |
| `DB_HOST` / `DB_PORT` | Database host and port |
| `RESEND_API_KEY` | Resend API key |
| `DEFAULT_FROM_EMAIL` | Sender address |
| `SALON_EMAIL` | Salon address for booking and cancellation notifications |
| `SITE_URL` | Base URL **with the scheme** (`https://…`): e-mail links, canonical, Open Graph, JSON-LD. Without the scheme the container refuses to start (system check `bookings.E001`) |
| `GOOGLE_PLACES_API_KEY` / `GOOGLE_PLACE_ID` | Google reviews on the home page. The key is restricted to the Droplet's IP, so locally and on staging you only see the links fallback |
| `NGINX_CONF` | Staging only: `dev.conf` in a `.env` file in the project root (not in `.env.prod`) — compose reads it for interpolation |

## Lint and tests

```bash
uv run ruff check --fix   # lint + import sorting
uv run ruff format        # formatting
uv run pytest             # about 550 tests
```

The tests (`tests/`, configured in [pytest.ini](pytest.ini)) cover models, forms, views, the panel, the API, e-mails, reminders, availability logic, data migrations, JSON-LD, the sitemap, category pages, guides and reviews. They need neither Postgres, Resend nor a Google key. CI rejects changes that fail lint, formatting or tests.

## Deployment

| Environment | Hosting | Branch | URL | Deploy |
| ----------- | ------- | ------ | --- | ------ |
| **Production** | DigitalOcean Droplet (`~/salon-manager`) | `main` | [royalbeauty-studiourody.pl](https://royalbeauty-studiourody.pl) | Manually over SSH, after checking on staging |
| **Staging** | [Mikrus](https://mikr.us/) VPS (`~/projects/salon-manager`) | `dev` | [dev.royalbeauty-studiourody.pl](https://dev.royalbeauty-studiourody.pl) | Automatically by GitHub Actions after a push to `dev` |

Flow: branch off `dev` → PR to `dev` → (CI + staging) → PR `dev` → `main` (merge commit) → manual production deploy.

[.github/workflows/deploy.yml](.github/workflows/deploy.yml) runs Ruff and the tests on pushes to `dev` and on PRs to `main`; after a push to `dev` it SSHes into staging (`git pull origin dev` + `docker compose -f docker-compose.prod.yml up -d --build`). Changes only to `*.md` and `docs/` don't trigger CI.

**Production deploy (summary):**
1. Database backup: `./scripts/backup_db.sh --env prod` (the only rollback — data migrations can't be reversed).
2. Merge the `dev` → `main` PR; on the Droplet run `git pull origin main` and `docker compose -f docker-compose.prod.yml up -d --build`.
3. `docker compose -f docker-compose.prod.yml logs web` — migrations `OK`, Gunicorn started. Error `bookings.E001` = `SITE_URL` in `.env.prod` without `https://` (the container deliberately doesn't start).
4. Cloudflare → Purge cache (files without a hash in the name, e.g. `robots.txt`, stay cached for up to 4 h).
5. Smoke test: www/http redirects → `https://royalbeauty-studiourody.pl/`, website, panel, `robots.txt`, `sitemap.xml`.

Full checklist from the first deploy: [docs/archive/seo-plan.md](docs/archive/seo-plan.md), stage 6.

## Scheduled jobs (cron)

On the production server (host crontab, outside the deploy process):

| Job | When | Command |
| --- | ---- | ------- |
| Appointment reminders | hourly | `docker compose -f docker-compose.prod.yml exec -T web uv run python manage.py send_reminders` |
| Database backup | per the server's crontab | `./scripts/backup_db.sh --env prod` (`--keep N`, 10 copies by default) |

A reminder goes to confirmed appointments with an e-mail address that start within 24 h and were booked at least 24 h in advance — once per appointment (again after a reschedule).

## Project structure

```
apps/
  accounts/     # User model, roles
  api/          # REST endpoints (DRF)
  bookings/     # Bookings, clients, e-mails, reminders, availability logic
  panel/        # Salon panel (/panel/)
  services/     # Services, specialists, schedule, equipment, FAQ, category pages, guides, reviews
config/
  settings/     # base / development / production / test
  urls.py, sitemaps.py, context_processors.py, asgi.py, wsgi.py
templates/      # HTML templates (website, category pages, guides, panel, e-mails, legal pages, llms.txt)
static/         # CSS, JS, fonts, images
tests/          # pytest tests
scripts/        # backup_db.sh
nginx/          # prod.conf (production), dev.conf (staging)
docs/           # roadmap.md (open work), archive/ (finished plans, redesign prototype) — in Polish
.env.example    # Environment variable template
```

## Roadmap

Details and the full task list (in Polish): [docs/roadmap.md](docs/roadmap.md). History of finished stages: [docs/archive/](docs/archive/).

Done (in production since 28 Oct 2026): SEO quick wins, extended FAQ, Google and Booksy reviews, category pages, guides.

Next:
- GDPR in the panel: deleting a client (with their appointments anonymised), automatic cleanup of data older than 3 years
- A new SEO/GEO/AEO audit
- Photos of work on the category pages
- Storing price and duration on the appointment (snapshot), then statistics for the owner (appointments, revenue, utilisation, cancellations)
- Specialist photos uploaded in the panel
