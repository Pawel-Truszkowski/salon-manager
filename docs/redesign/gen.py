"""Generates docs/redesign/prototype.html from a snapshot of /api/services/ (static, JS-free content)."""

import html
import json
import sys
from collections import defaultdict
from pathlib import Path

services = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
out_path = sys.argv[2]
IMG = "../../static/img/"

LASER = {
    "slug": "depilacja-laserowa",
    "name": "Depilacja laserowa",
    "dates": "8–9 listopada (niedziela i poniedziałek)",
    "start": "2026-11-08",
    "end": "2026-11-09",
    "rows": ["Pachy", "Bikini", "Łydki", "Całe nogi", "Wąsik"],
}
ORDER = [
    ("rzesy-i-brwi", "Rzęsy i brwi"),
    ("dlonie-i-stopy", "Dłonie i stopy"),
    ("zabiegi-kosmetyczne", "Zabiegi na twarz i ciało"),
    ("depilacja-woskiem", "Depilacja woskiem"),
]
by_cat = defaultdict(list)
for s in services:
    by_cat[s["category"]["slug"]].append(s)

e = html.escape


def price(s):
    p = int(float(s["price"]))
    return "bezpłatnie" if p == 0 else f"{p} zł"


def desc(text):
    lines = [ln.strip() for ln in (text or "").replace("\r", "").split("\n") if ln.strip()]
    paras, items = [], []
    for ln in lines:
        (items if ln.startswith("- ") else paras).append(ln.lstrip("- "))
    out = "".join(f"<p>{e(p)}</p>" for p in paras)
    if items:
        out += "<ul>" + "".join(f"<li>{e(i)}</li>" for i in items) + "</ul>"
    return out


def laser_group():
    rows = "".join(
        f"""<details class="treat">
  <summary><h3 class="treat-name">{e(n)}</h3><span class="leader" aria-hidden="true"></span><span class="treat-time">— min</span><span class="treat-price">— zł</span></summary>
  <div class="treat-body"><p>Opis, cena i czas z wizytówki Google.</p><a class="text-link" href="#rezerwacja">Zarezerwuj ten zabieg</a></div>
</details>"""
        for n in LASER["rows"]
    )
    return f"""<section class="menu-group" id="{LASER["slug"]}" aria-labelledby="{LASER["slug"]}-h">
<h3 class="menu-group-title" id="{LASER["slug"]}-h">{LASER["name"]}</h3>
<div class="laser-note">
  <p class="laser-when"><strong>Laser w salonie: {LASER["dates"]}</strong></p>
  <p>Laser [model] jest u nas mniej więcej co 6 tygodni. To rytm, w jakim wykonuje się kolejne zabiegi z serii, więc następną wizytę umówisz od razu po pierwszej. Zabiegi laserowe rezerwujesz tylko na te dni.</p>
  <span class="todo">Model lasera, opis technologii, ceny i partie ciała: z wizytówki Google</span>
</div>
{rows}</section>"""


def menu():
    index = [
        f'<li><a href="#{LASER["slug"]}"><span class="idx-name">{LASER["name"]}</span><span class="idx-meta">tylko 8–9 listopada</span></a></li>'
    ]
    groups = [laser_group()]
    for slug, name in ORDER:
        items = by_cat[slug]
        lo = min(int(float(s["price"])) for s in items if float(s["price"]) > 0)
        hi = max(int(float(s["price"])) for s in items)
        index.append(
            f'<li><a href="#{slug}"><span class="idx-name">{e(name)}</span><span class="idx-meta">{len(items)} zabiegów, {lo}–{hi} zł</span></a></li>'
        )
        rows = "".join(
            f"""<details class="treat">
  <summary><h3 class="treat-name">{e(s["name"])}</h3><span class="leader" aria-hidden="true"></span><span class="treat-time">{s["duration"]} min</span><span class="treat-price">{price(s)}</span></summary>
  <div class="treat-body">{desc(s["description"])}<a class="text-link" href="#rezerwacja" data-service="{s["id"]}">Zarezerwuj ten zabieg</a></div>
</details>"""
            for s in items
        )
        groups.append(
            f'<section class="menu-group" id="{slug}" aria-labelledby="{slug}-h"><h3 class="menu-group-title" id="{slug}-h">{e(name)}</h3>{rows}</section>'
        )
    return "".join(index), "".join(groups)


index_html, groups_html = menu()
options = "".join(f'<option>{e(n)} (depilacja laserowa, 8–9 listopada)</option>' for n in LASER["rows"]) + "".join(
    f'<option value="{s["id"]}">{e(s["name"])} ({price(s)})</option>' for slug, _ in ORDER for s in by_cat[slug]
)

lash = [s for s in by_cat["rzesy-i-brwi"] if s["name"].startswith("Przedłużanie")]
lash_lo, lash_hi = min(int(float(s["price"])) for s in lash), max(int(float(s["price"])) for s in lash)

FAQ = [
    (
        "Ile kosztuje przedłużanie rzęs?",
        f"Przedłużanie rzęs kosztuje od {lash_lo} zł (metoda 1:1) do {lash_hi} zł (objętość 5/6:1) i trwa od 105 do 135 minut. Uzupełnienie kosztuje od 130 do 190 zł. Pełny cennik rzęs i brwi znajdziesz wyżej, w sekcji Rzęsy i brwi.",
    ),
    (
        "Czy mogę najpierw przyjść na konsultację?",
        "Tak. Bezpłatna konsultacja z kosmetologiem trwa około 30 minut. Kosmetolog oceni stan skóry i doradzi, który zabieg będzie dla Ciebie najlepszy. Konsultację rezerwujesz tak samo jak każdy zabieg.",
    ),
    (
        "Kiedy mogę się umówić?",
        "Przyjmujemy po wcześniejszym umówieniu, codziennie od 9:00 do 21:00, także w soboty i niedziele. Termin dopasowujemy do Ciebie, więc łatwo umówić się po pracy albo w weekend. Wolne godziny widzisz w formularzu rezerwacji. Jeśli żadna nie pasuje, zadzwoń.",
    ),
    (
        "Kiedy mogę zrobić depilację laserową?",
        "Laser jest w salonie mniej więcej co 6 tygodni, najbliżej 8 i 9 listopada. Depilację laserową wykonuje się w serii zabiegów co kilka tygodni, więc kolejny termin umówisz od razu po wizycie. W formularzu zabiegi laserowe można zarezerwować tylko na dni, w które laser jest w salonie.",
    ),
    (
        "Jak zarezerwować wizytę?",
        "Wybierz zabieg, dzień i godzinę w formularzu rezerwacji. Pokazujemy tylko wolne terminy. Potwierdzimy wizytę e-mailem w ciągu 24 godzin. Możesz też zadzwonić: +48 793 355 756 lub +48 792 646 256.",
    ),
    (
        "Jak odwołać lub przełożyć wizytę?",
        "W e-mailu z potwierdzeniem rezerwacji jest link do odwołania wizyty. Wystarczy go kliknąć i potwierdzić. Jeśli chcesz przełożyć termin, zadzwoń do salonu, a znajdziemy nowy.",
    ),
    (
        "Ile trwa manicure hybrydowy i ile kosztuje?",
        "Manicure hybrydowy trwa około 75 minut i kosztuje 120 zł, a w wersji french lub baby boomer 130 zł. Usunięcie starej hybrydy kosztuje 40 zł, a z zabezpieczeniem płytki 90 zł.",
    ),
]
faq_html = "".join(f'<details class="faq"><summary><h3>{e(q)}</h3></summary><p>{e(a)}</p></details>' for q, a in FAQ)
salon_ld = json.dumps(
    {
        "@context": "https://schema.org",
        "@type": "BeautySalon",
        "@id": "https://royalbeauty-studiourody.pl/#salon",
        "name": "Royal Beauty Studio Urody",
        "url": "https://royalbeauty-studiourody.pl/",
        "telephone": ["+48793355756", "+48792646256"],
        "priceRange": "20–400 zł",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "ul. Małopanewska 24B/5",
            "addressLocality": "Wrocław",
            "postalCode": "54-212",
            "addressCountry": "PL",
        },
        "geo": {"@type": "GeoCoordinates", "latitude": 51.1206602, "longitude": 16.9835035},
        "description": "Studio urody we Wrocławiu. Wizyty wyłącznie po wcześniejszym umówieniu.",
        "openingHoursSpecification": [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                "opens": "09:00",
                "closes": "21:00",
            }
        ],
        "founder": {
            "@type": "Person",
            "name": "Paulina",
            "jobTitle": "Kosmetolog",
            "hasCredential": "Magister kosmetologii",
        },
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": "Depilacja laserowa",
            "itemListElement": [
                {
                    "@type": "Offer",
                    "itemOffered": {"@type": "Service", "name": "Depilacja laserowa — pachy"},
                    "availabilityStarts": LASER["start"],
                    "availabilityEnds": LASER["end"],
                    "priceCurrency": "PLN",
                }
            ],
        },
        "sameAs": [
            "https://www.instagram.com/royalbeauty_studiourody_/",
            "https://www.facebook.com/p/Royal-Beauty-100063223181002/",
        ],
    },
    ensure_ascii=False,
    indent=2,
)
faq_ld = json.dumps(
    {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ
        ],
    },
    ensure_ascii=False,
    indent=2,
)

# One active employee today -> owner profile. With 2+ active employees the template switches back to a team list.
TEAM = [
    ("Paulina", "Właścicielka, magister kosmetologii", "Zabiegi na twarz, rzęsy i brwi, manicure i pedicure, depilacja")
]
team_html = "".join(
    f'<li class="person"><div class="arch portrait" aria-hidden="true"><span>{n[0]}</span></div><div><h3>{n}</h3><p class="person-role">{e(r)}</p><p class="person-skills">{e(k)}</p></div></li>'
    for n, r, k in TEAM
)

template = Path(sys.argv[3]).read_text(encoding="utf-8")
page = (
    template.replace("{{IMG}}", IMG)
    .replace("{{MENU_INDEX}}", index_html)
    .replace("{{MENU_GROUPS}}", groups_html)
    .replace("{{OPTIONS}}", options)
    .replace("{{FAQ}}", faq_html)
    .replace("{{FAQ_LD}}", faq_ld)
    .replace("{{SALON_LD}}", salon_ld)
    .replace("{{TEAM}}", team_html)
    .replace("{{COUNT}}", str(len(services) + len(LASER["rows"])))
)
Path(out_path).write_text(page, encoding="utf-8")
print("written", out_path, len(page), "bytes")
