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

### 3. Grafik tygodniowy ✅
- Szablon tygodnia per specjalistka (`WeeklyScheduleEntry`; np. pon–pt 9–17, możliwe kilka bloków dziennie, bloki nie mogą na siebie nachodzić), z którego `generate_schedules()` (`apps/services/scheduling.py`) tworzy wpisy `Schedule` na wybrany zakres dat (max 183 dni, nie w przeszłości). Dni, które już mają grafik, są pomijane — ręczne wyjątki nie są nadpisywane. Logika dostępności (`get_available_slots`) się nie zmienia.
- Strona „Grafik” (`/panel/schedule/`): szablon, najbliższe 4 tygodnie (praca + blokady), generowanie; edytor szablonu (formset).
- Zarządzanie `TimeBlock` (urlopy, przerwy): lista od dziś, dodawanie, usuwanie.
- `updated_by` / `updated_at` na `Schedule` / `TimeBlock`.
- Do rozważenia później: edycja pojedynczych dni grafiku (wyjątki) w panelu — dziś tylko przez `/admin/`.

### 4. Kalendarz (FullCalendar) ✅
- Darmowy FullCalendar (MIT) z CDN — **bez** płatnych widoków z kolumnami per osoba (`resourceTimeGrid` jest w licencji Premium, a salon to użytek komercyjny).
- Widok tygodnia/dnia (na telefonie lista). Właściciel wybiera specjalistkę albo „wszystkie” (kolor = status wizyty, imię specjalistki w tytule); specjalistka widzi tylko siebie. Grafik i blokady jako tło — tylko przy jednej wybranej osobie.
- Endpoint JSON `/panel/calendar/events/` z wizytami, grafikiem i blokadami w zakresie dat (przez `scope_to_employee()`).
- Kliknięcie wizyty → szczegóły; kliknięcie wolnego miejsca → nowa wizyta z wypełnioną datą/godziną/specjalistką.
- Przeciągnięcie wizyty = zmiana terminu przez tę samą walidację co w etapie 2 (`RescheduleForm` / `get_available_slots`) w `POST /panel/calendar/appointments/<pk>/move/` — bez `force` i bez zmiany specjalistki; przed wysłaniem potwierdzenie (klientka dostaje mail), przy błędzie wizyta wraca na miejsce. Rozciąganie wyłączone (czas trwania wynika z usługi).

### 5. Statystyki (tylko właściciel)
- Liczba wizyt, przychód (`Service.price` zrealizowanych wizyt), obłożenie specjalistek, odsetek anulacji — w wybranym okresie.

### Zarządzanie salonem (właściciel) — w toku, przed etapem 5
Kolejność zmieniona: bez tego panelu nie da się wdrożyć (konto specjalistki dało się podpiąć tylko w `/admin/`).
- ✅ Zespół: lista, dodawanie, edycja specjalistek (`/panel/employees/`; imię publiczne, opis, usługi).
- ✅ Dezaktywacja (`is_active`, `.active()`; blokowana przy przyszłych wizytach).
- ✅ Zaproszenia do panelu: konto bez hasła (login = e-mail, małymi literami) + link z tokenem resetu hasła (`apps/panel/invitations.py`, `/panel/invitation/<uidb64>/<token>/`), ponowne wysłanie dopóki hasło nie jest ustawione.
- ✅ Usługi (`/panel/services/`): lista wg kategorii, dodawanie, edycja, wyłączanie (`Service.is_active`, blokowane przy przyszłych wizytach); czas trwania 15–480 min, wielokrotność 15 (siatka terminów). Kategorie tylko do wyboru — zakładki na stronie są wpisane w `home.html`, więc nowa kategoria nie miałaby zakładki.
- **Przed etapem 5:** zapamiętywać `price` i `duration` w `Appointment` przy zapisie (snapshot) — dziś zmiana usługi zmienia wstecz długość zapisanych wizyt i historyczny przychód.
- `Employee.first_name/last_name` = nazwa publiczna, `User.*` = dane konta — mogą się różnić, nie synchronizujemy.
- E-mail konta tylko w `User.email`. `Employee.email` usuwamy etapami (expand/contract): ✅ panel i publiczne API już go nie pokazują → zaproszenia podpowiadają adres z `Employee.email` → usunąć z admina i fixtur → backup bazy + migracja `RemoveField`.
- Specjalistki: dodawanie, edycja, dezaktywacja, zakładanie konta i wysyłka zaproszenia. Uwaga: wbudowany reset hasła pomija konta bez ustawionego hasła (`has_usable_password`), więc zaproszenie potrzebuje własnego formularza/linku.
- Usługi i kategorie.
