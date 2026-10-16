# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All Django commands are run from the project root (there is no `src/` directory — `manage.py` lives at the repo root), always through `uv run` so they use the project venv (Python 3.14).

```bash
uv run python manage.py runserver
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run pytest
```

### Lint & format

Ruff (config in `pyproject.toml`; migrations excluded, `E501` off because `ruff format` owns line length, quote style preserved). CI fails on either check.

```bash
uv run ruff check --fix   # lint + autofix (incl. import sorting)
uv run ruff format        # format
```

Dependencies are managed with `uv` (not pip directly):

```bash
uv add <package>        # Add dependency
uv sync                 # Install from lockfile
uv run <command>         # Run a command inside the project's venv (e.g. uv run pytest)
```

### Docker

```bash
docker compose -f docker-compose.dev.yml up --build    # development (hot-reload)
docker compose -f docker-compose.prod.yml up -d --build # production (gunicorn + nginx)
```

### Tests

Test suite lives in `./tests/` (pytest + pytest-django, config in `pytest.ini`, settings module `config.settings.test`). Covers models, forms, views, admin, and utils.

```bash
uv run pytest
uv run pytest tests/test_views.py::TestCancelBookingView                       # one class
uv run pytest tests/test_views.py::TestCancelBookingView::test_post_cancels_the_appointment  # one test
uv run pytest -k cancel                                                        # by name pattern
```

`config.settings.test` is standalone (does **not** import `base.py`) — new apps or settings must be added there too. It uses SQLite and the `locmem` e-mail backend (sent mail lands in `mailoutbox` / `django.core.mail.outbox`), so tests need neither Postgres nor Resend. `SITE_URL` is `http://testserver` there.

## Architecture

**Stack:** Django 6 + Django REST Framework + PostgreSQL (Docker/prod; env-driven via `django-environ`). No separate frontend build step — all HTML is server-rendered Django templates with Bootstrap 5 and vanilla JS. E-mail sending goes through `django-anymail` (Resend backend).

**Project layout:**
- `./config/` — Django settings package (`settings/base.py`, `development.py`, `production.py`, `test.py`), root URL conf, `sitemaps.py`, `asgi.py`/`wsgi.py`
- `./apps/accounts/` — Custom `User` model (`AbstractUser` + `phone_number`), set as `AUTH_USER_MODEL`
- `./apps/services/` — `ServiceCategory`, `Service`, `Employee`, `Schedule`, `TimeBlock`, `WeeklyScheduleEntry` models; `scheduling.py` (`generate_schedules()`: weekly template → `Schedule` rows)
- `./apps/bookings/` — `Appointment` model, booking form/view, availability logic (`utils.py`), confirmation e-mails (`emails.py`), post-save signal that triggers booking e-mails (`signals.py`)
- `./apps/panel/` — staff panel at `/panel/` (own views + `templates/panel/`, not Django admin): login/logout/password reset, dashboard, appointments, time blocks, schedule (weekly template editor + generation), calendar (FullCalendar v6 free bundle from CDN, `static/js/panel-calendar.js`; JSON feed + drag & drop move endpoint that reuses `RescheduleForm`). Access via `PanelAccessMixin` / `OwnerRequiredMixin` (`apps/panel/mixins.py`); querysets for employees must go through `scope_to_employee()`. Roadmap in `docs/panel-plan.md`
- `./apps/api/` — DRF app: serializers + views for services, employees, available slots/dates (implemented, not a stub)
- `./templates/` — Django HTML templates (`base.html`, `home.html`, `bookings/cancel_appointment.html`, `emails/*.html` incl. cancellation e-mails, `robots.txt`)
- `./static/` — CSS (`style.css`), JS (`script.js`), images
- `./nginx/` — Nginx configs for the Docker prod stack: `prod.conf` (royalbeauty-studiourody.pl) and `dev.conf` (dev.royalbeauty-studiourody.pl). `docker-compose.prod.yml` mounts `./nginx/${NGINX_CONF:-prod.conf}`, so the staging server must set `NGINX_CONF=dev.conf` in its shell or a project-root `.env` — compose interpolation does not read the services' `env_file`
- `./scripts/backup_db.sh` — gzipped `pg_dump` of the Dockerized DB (`--env dev|prod` picks `.env.<env>`, `--keep N` rotation, default 10); on production it runs from cron on the server, not as part of deploy
- `./tests/` — pytest test suite

**Roles** (`apps/accounts/roles.py`): *owner* = member of the `Właściciel` group (created by a data migration; superusers count as owners) — full business control in `/panel/`, no `/admin/` access. *Employee* = `User` linked via `Employee.user` — sees/manages only own data. Roles can overlap (an owner who also works as a specialist). `/admin/` is for the developer only.

**Data model relationships:**
- `Employee` M2M `Service` (an employee can perform multiple services); optional `Employee.user` (OneToOne) is the panel login
- `Schedule` belongs to `Employee` (working hours per day; supports multiple blocks/day e.g. split shifts)
- `TimeBlock` belongs to `Employee` (ad-hoc blocked periods: breaks, days off)
- `WeeklyScheduleEntry` belongs to `Employee` (weekly template: weekday + hours, several per day allowed). It is **not** read by availability logic — `generate_schedules()` materializes it into `Schedule` rows, skipping days that already have any (manual exceptions win)
- `Appointment` → `Service` + `Employee` (optional — auto-assigned if omitted) + datetime + client info + `status` (`pending`/`confirmed`/`completed`/`cancelled`) + `cancellation_token` (unique UUID used in the client's cancel link). State transitions live on the model: `confirm()`, `complete()`, `cancel()` (allowed only while `can_be_cancelled` — status `pending`/`confirmed` and `date_time` in the future)

**Booking flow:**
- `POST /bookings/` (`apps.bookings.views.submit_booking`) validates `BookingForm`, then saves the `Appointment`. Availability is checked differently per path: if the client chose an employee, the time must be in `get_available_slots(employee, date, service)`; if not, `find_available_specialist(service, date_time)` picks one and is the only check. Changes to availability rules must keep both functions (`apps/bookings/utils.py`) consistent.
- Saving a new `Appointment` fires a `post_save` signal that sends a confirmation e-mail to the client and a notification e-mail to the salon (`SALON_EMAIL`).
- Admin actions in `apps.bookings.admin` (or calling `Appointment.confirm()`) send a further "confirmed" e-mail to the client; `Appointment.complete()` marks a confirmed appointment as completed.
- Client self-cancellation: the confirmation e-mails include `cancel_url` from `Appointment.get_cancel_url()` (built from `settings.SITE_URL`). `GET /bookings/cancel/<uuid:token>/` (`apps.bookings.views.cancel_booking`, routed in `config/urls.py`) shows a confirmation page; `POST` calls `Appointment.cancel()`, which e-mails the client and the salon. Re-posting on an already cancelled appointment sends nothing.
- E-mail sending is split: creation e-mails come from the `post_save` signal; confirm/cancel/reschedule e-mails are sent directly from the model methods (all helpers in `apps/bookings/emails.py`; client e-mails are silently skipped when `client_email` is empty).
- Panel (`/panel/appointments/`): appointments created there set `instance._skip_booking_emails = True` before `save()` (signal skips "booking received" + salon notification) and are saved as `confirmed` with a "confirmed" e-mail instead. Panel cancels use `cancel(by_salon=True)` (different client e-mail, no salon notification); moves use `reschedule()`. Panel views set `updated_by` before calling model methods. Availability in panel forms (`apps/panel/forms.py`) goes through `get_available_slots(..., exclude_appointment=...)`; only owners may bypass it (`force`).
- `client_email` is `blank=True` on the model (phone bookings in the panel); `BookingForm` re-requires it for the website.

**API endpoints** (`apps/api/urls.py`, mounted at `/api/`):
- `GET /api/services/` — list services
- `GET /api/employees/?service=<id>` — list employees, optionally filtered by service
- `GET /api/available-slots/?date=&service=&employee=` — available time slots for a date/service(/employee)
- `GET /api/available-dates/?month=YYYY-MM&service=&employee=` — which days in a month have availability

**Current state:** The frontend (home page) is fully built with service category tabs, gallery lightbox, and a working reservation form backed by the `bookings` app and `api` app. Sitemap (`/sitemap.xml`) and `robots.txt` are wired up for SEO. The site content is in Polish.

## CI/CD

Branch flow: work on `dev` → PR to `main`.

`.github/workflows/deploy.yml` runs `ruff check`, `ruff format --check` and tests (`uv sync --frozen` + `uv run pytest`, Python 3.14) on push to `dev` and on PRs to `main` (changes only to `*.md`/`docs/` are skipped). On push to `dev` it then SSHes into the dev/staging VPS (Mikrus, dev.royalbeauty-studiourody.pl), does `git pull origin dev` and runs `docker compose -f docker-compose.prod.yml up -d --build` — which also starts the stack if it was stopped there.

Production (`main`, DigitalOcean Droplet, royalbeauty-studiourody.pl) is **not** deployed by CI — it's done manually over SSH after verifying on staging. Both servers run the same `docker-compose.prod.yml` stack (Postgres + gunicorn + nginx).

## Environment variables

`.env.example` is the template for `.env.dev` / `.env.prod` (never commit real values). How they reach Django differs:
- `config/settings/base.py` calls `environ.Env.read_env(BASE_DIR / ".env.dev")` — only `.env.dev` is ever read from disk by Django.
- `.env.prod` reaches the app only via `env_file` in `docker-compose.prod.yml`. Running production settings outside Docker would silently pick up `.env.dev` values.

Key variables: `DJANGO_SETTINGS_MODULE`, `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL` (+ `POSTGRES_DB/USER/PASSWORD`, `DB_HOST`, `DB_PORT`), `RESEND_API_KEY`, `DEFAULT_FROM_EMAIL`, `SALON_EMAIL`, `SITE_URL` (base URL for links in e-mails, e.g. the cancel link). E-mail always goes through Resend (`anymail` backend); there is no SMTP fallback. `SECURE_PROXY_SSL_HEADER` is hard-coded in `config/settings/production.py`, not read from env.
