# Panel salonu (`/panel/`) — plan

Własny panel do zarządzania salonem dla właściciela i specjalistek, zbudowany na Django templates + Bootstrap 5 + vanilla JS (jak reszta strony). Django admin (`/admin/`) zostaje wyłącznie jako dostęp techniczny dla developera.

## Role

| | Developer (superuser) | Właściciel | Specjalistka |
|---|---|---|---|
| `/admin/` Django | ✅ | ❌ | ❌ |
| Wizyty: potwierdź / anuluj / przenieś / dodaj | wszystkie | wszystkie | tylko swoje |
| Grafik i blokady | wszystkie | wszystkie | tylko swoje |
| Specjalistki, konta, usługi | ✅ | ✅ | ❌ |
| Kalendarz | ✅ | wszystkie specjalistki | tylko swój |
| Statystyki | ✅ | ✅ | ❌ |

- **Właściciel** = członek grupy Django `Właściciel` (superuser też jest traktowany jak właściciel). Nie dostaje `is_staff` / `is_superuser`.
- **Specjalistka** = konto powiązane z `Employee` przez `Employee.user`.
- Role się nie wykluczają: właściciel, który sam wykonuje zabiegi, ma powiązany `Employee` i widzi zarówno „swoje”, jak i cały salon.
- Każda operacja w panelu idzie przez logikę modeli (`confirm()`, `cancel()`, …), więc maile i sprawdzanie dostępności działają tak samo jak na stronie.
- Zmiany grafiku i wizyt zapisują, kto i kiedy je zrobił (`updated_by` / `updated_at`), żeby właściciel widział zmiany wprowadzane przez specjalistki.

## Etapy (każdy jako osobny PR na `dev`)

### 1. Fundamenty ✅
- Aplikacja `apps/panel/`, layout panelu, nawigacja zależna od roli.
- Logowanie / wylogowanie / reset hasła mailem (wbudowane widoki `django.contrib.auth`).
- `Employee.user` (`OneToOneField`, opcjonalne), grupa `Właściciel` tworzona migracją.
- Helpery ról (`apps/accounts/roles.py`) i mixiny dostępu (`PanelAccessMixin`, `OwnerRequiredMixin`) z filtrowaniem danych do „swoich” dla specjalistki.
- Dashboard: dzisiejsze i oczekujące wizyty.
- `/panel/` wykluczony w `robots.txt`.

### 2. Obsługa wizyt ✅
- Lista z filtrami (status, specjalistka, zakres dat, wyszukiwanie klienta).
- Akcje: potwierdź / zrealizuj / anuluj — przez istniejące metody modelu (maile wychodzą automatycznie).
- Zmiana terminu i ręczne dodanie wizyty (telefonicznej) — **zawsze walidowane przez `get_available_slots`** (`apps/bookings/utils.py`); baza nie blokuje nakładających się wizyt.
- `updated_by` / `updated_at` na `Appointment`.
- Zasady (ustalone): wizyta dodana w panelu jest od razu potwierdzona (mail „potwierdzona” do klienta, bez powiadomienia salonu); e-mail klienta opcjonalny w panelu, wymagany na stronie; tylko właściciel może pominąć grafik („force”); specjalistki nie dostają maili o zmianach.

### 3. Grafik tygodniowy
- Szablon tygodnia per specjalistka (np. pon–pt 9–17, możliwe kilka bloków dziennie), z którego generowane są wpisy `Schedule` na wybrany zakres dat. Logika dostępności (`get_available_slots`) się nie zmienia.
- Zarządzanie `TimeBlock` (urlopy, przerwy).
- `updated_by` / `updated_at` na `Schedule` / `TimeBlock`.

### 4. Kalendarz (FullCalendar)
- Widok dnia/tygodnia, kolumny per specjalistka (właściciel) lub tylko własny (specjalistka).
- Endpoint JSON z wizytami, grafikiem i blokadami w zakresie dat.
- Przeciągnięcie wizyty = zmiana terminu przez tę samą walidację co w etapie 2.

### 5. Statystyki (tylko właściciel)
- Liczba wizyt, przychód (`Service.price` zrealizowanych wizyt), obłożenie specjalistek, odsetek anulacji — w wybranym okresie.

### Zarządzanie salonem (właściciel, w ramach etapów 2–3)
- Specjalistki: dodawanie, edycja, dezaktywacja, zakładanie konta i wysyłka zaproszenia. Uwaga: wbudowany reset hasła pomija konta bez ustawionego hasła (`has_usable_password`), więc zaproszenie potrzebuje własnego formularza/linku.
- Usługi i kategorie.
