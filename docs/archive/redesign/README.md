# Redesign strony głównej — propozycja

Prototyp: `docs/redesign/prototype.html`, statyczny plik z prawdziwymi danymi (64 usługi z `/api/services/`, stan na 2026-10-16) i miejscami do uzupełnienia oznaczonymi przerywaną ramką. Podgląd z katalogu repo:

```bash
python3 -m http.server 8765   # potem http://127.0.0.1:8765/docs/redesign/prototype.html
```

Prototyp jest generowany: `template.html` (HTML + CSS) + `gen.py` (cennik, FAQ, JSON-LD) + `services-snapshot.json` (dane). Po zmianie:

```bash
python3 docs/redesign/gen.py docs/redesign/services-snapshot.json docs/redesign/prototype.html docs/redesign/template.html
```

Ustalenia biznesowe (jedna stylistka, godziny po umówieniu, laser) są opisane w `docs/seo-plan.md`, w sekcji „Ustalenia”.

Prototyp to **referencja wizualna**, nie kod do skopiowania. Docelowo trafia do `templates/home.html` + `static/css/style.css`, a dane pochodzą z kontekstu widoku `home`.

## Pomysł w jednym zdaniu

Strona jest zbudowana wokół **cennika jako karty zabiegów**: nazwa, kropkowana linia, czas i cena, jak w drukowanym cenniku salonu. Ten jeden element jest odważny, reszta jest spokojna. To też najważniejsza poprawka z audytu: cała oferta w HTML, bez JS.

## Co zostaje, co się zmienia

| Zostaje | Zmienia się |
|---|---|
| Kolory: `#f5efe6`, `#ede5d8`, `#fdf9f4`, `#2c2418`, `#3d2e1e`, `#b8935a` | Złoto `#b8935a` tylko na linie i obramowania. Tekst w złocie ma `#7d5f2e`, bo `#b8935a` na kremowym tle nie spełnia kontrastu WCAG AA |
| Playfair Display w nagłówkach | 3 kroje → 2: Raleway + Cormorant zastępuje **Jost**, który ma czytelne cyfry w cenach (lining figures) i pełne polskie znaki |
| Logo, zdjęcia, dane, adres, telefony | Hero: zamiast logo na rozmytym zdjęciu jest H1 z frazą, zdanie o ofercie, CTA i NAP, a obok zdjęcie w łuku |
| Ciemne espresso w stopce | Espresso także jako tło sekcji rezerwacji, żeby był wyraźny moment „teraz działaj” |
| | Godziny otwarcia → „po wcześniejszym umówieniu, codziennie 9–21” + najbliższy wolny termin |
| | Trzy specjalistki → profil Pauliny (wariant dla jednej aktywnej osoby) |

**Usunięte ozdobniki** (wyglądały na szablon i nic nie niosły): napisy WERSALIKAMI nad każdym nagłówkiem, złota kursywa na jednym słowie w nagłówku, „Elegancja · Luksus · Piękno”, złote kreski pod nagłówkami, podwójna ramka w hero, karuzela opinii, tło ze Unsplash.

## System

- **Łuk** (`border-radius: 999px 999px 0 0`) to motyw lustra salonowego. Pojawia się tylko na zdjęciach i portretach. Przyciski i pola mają 2 px, karty nie mają cieni.
- **Wyrównanie do lewej** wszędzie poza drobnymi elementami. Sekcje mają układ „nagłówek po lewej, treść po prawej”, który na telefonie składa się w jedną kolumnę.
- **Jeden ruch bez interakcji:** zdjęcie w hero odsłania się od dołu przy załadowaniu. Poza tym animują się tylko rzeczy, które otwiera użytkownik (opis zabiegu, FAQ). `prefers-reduced-motion` wyłącza animacje.
- **Bez JS działa wszystko:** cennik (`<details>`), FAQ, menu kategorii (kotwice), formularz. „Najbliższy wolny termin” liczy Django, nie przeglądarka.
- **Kameralność jako zaleta, nie brak:** teksty mówią „po umówieniu, termin dopasowujemy do Ciebie, na wizycie jesteś tylko Ty”, zamiast udawać duży salon. Liczba mnoga („przyjmujemy”), żeby teksty przetrwały zatrudnienie pracownicy.

## Kolejność sekcji (i który punkt audytu realizuje)

1. **Nagłówek:** logo, Cennik / O salonie / Opinie / Pytania / Kontakt, telefon jako `tel:`, „Zarezerwuj wizytę”.
2. **Hero:** `<h1>` „Salon kosmetyczny we Wrocławiu”, zdanie definiujące ofertę (GEO), adres, **najbliższy wolny termin** i telefon nad zgięciem (lokalne SEO). *seo-plan etapy 1 i 3*
3. **O salonie:** kameralne studio, wizyty po umówieniu 9–21 także w weekendy; obok **profil Pauliny** (przy 2+ aktywnych `Employee` lista zespołu). *etap 3*
4. **Cennik:** sticky indeks kategorii, na początku **Depilacja laserowa** z blokiem „Laser w salonie: 8–9 listopada”, opisem urządzenia i rytmem co ok. 6 tygodni; potem pozostałe kategorie, wiersze `<details>`, „Zarezerwuj ten zabieg”. *etapy 2 i 5*
5. **Galeria:** mozaika, opisowe alty, `loading="lazy"`.
6. **Opinie:** 2–3 prawdziwe cytaty bez karuzeli + link do Google. W prototypie jest wyraźnie oznaczone miejsce. *etap 3, decyzja właścicielki*
7. **Częste pytania:** 7 pytań z odpowiedziami zbudowanymi z danych (ceny, czasy, kiedy można się umówić, kiedy laser, odwoływanie) + `FAQPage` JSON-LD. *etap 4*
8. **Rezerwacja:** 3 kroki obok formularza, bez pola „Specjalistka” (tylko przy 2+ osobach), podpowiedź „nie wpisuj informacji o zdrowiu”, informacja RODO z linkiem do polityki. *etap 3*
9. **Kontakt:** adres w `<address>`, „Przyjmujemy po wcześniejszym umówieniu, codziennie 9:00–21:00”, najbliższy wolny termin, „Wyznacz trasę”.
10. **Stopka:** prawdziwe linki do polityki prywatności i regulaminu.

## Do wyjaśnienia przed wdrożeniem

- **Zdjęcie Pauliny:** w prototypie jest pusty łuk z inicjałem. Potrzebny portret w pionie 3:4.
- **Laser:** model, opis, partie ciała, ceny i czasy (z wizytówki Google). W prototypie są puste wiersze „— zł”.
- **Najbliższy wolny termin** w prototypie jest wpisany na sztywno („wtorek, 20 października”); docelowo liczy go Django.
- **Długi cennik:** 64 wiersze na desktopie to ok. 3000 px przewijania. Sticky indeks pomaga, ale alternatywą są zakładki, które pokazują jedną kategorię naraz, z pozostałymi kategoriami w HTML ukrytymi przez `hidden`. Do decyzji po obejrzeniu prototypu.
- **og:image:** prototyp odwołuje się do `og-salon.jpg` (1200×630), którego jeszcze nie ma.

## Jak to wdrożyć

Wdrożenie idzie razem z etapami z `docs/seo-plan.md`, a nie jako osobny „wielki PR”:

1. **Tokeny i typografia:** zmienne w `:root`, Jost zamiast Raleway i Cormorant, `--gold-ink`, usunięcie klas ozdobników. Mały PR, cała strona od razu wygląda nowocześniej.
2. **Hero + nagłówek:** razem z etapem 1 SEO (H1, `tel:`, OG).
3. **Cennik:** to jest etap 2 SEO (renderowanie po stronie serwera). Nowy wygląd wchodzi od razu w nowym HTML.
4. **Profil, opinie, rezerwacja, kontakt:** etap 3.
5. **FAQ:** etap 4.
6. **Laser:** etap 5. Potem publikacja całości na produkcji (etap 6).
