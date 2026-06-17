window.addEventListener(
  "scroll",
  function () {
    document
      .getElementById("navbar")
      .classList.toggle("scrolled", window.scrollY > 60);
  },
  { passive: true },
);
function scrollToTop(e) {
  e.preventDefault();
  window.scrollTo({ top: 0, behavior: "smooth" });
}
document.querySelectorAll('a[href^="#"]').forEach(function (a) {
  a.addEventListener("click", function (e) {
    var t = document.querySelector(this.getAttribute("href"));
    if (!t) return;
    e.preventDefault();
    window.scrollTo({
      top: t.getBoundingClientRect().top + window.scrollY - 80,
      behavior: "smooth",
    });
    var m = document.getElementById("navMenu");
    if (m && m.classList.contains("show"))
      bootstrap.Collapse.getInstance(m).hide();
  });
});
var servicesData = {
  twarz: [
    {
      name: "Zabieg limfatyczny",
      desc: "Intensywne ujędrnienie i odmłodzenie skóry",
      price: "350 zł",
      duration: "90 min",
    },
    {
      name: "Mezoterapia igłowa",
      desc: "Odżywienie skóry koktajlami witaminowymi",
      price: "280 zł",
      duration: "60 min",
    },
    {
      name: "Peeling chemiczny",
      desc: "Głęboka regeneracja i wyrównanie kolorytu",
      price: "220 zł",
      duration: "60 min",
    },
    {
      name: "Makijaż wieczorowy",
      desc: "Glamour look na wyjątkowe okazje",
      price: "180 zł",
      duration: "75 min",
    },
  ],
  rzesy: [
    {
      name: "Przedłużanie rzęs 1:1",
      desc: "Klasyczna metoda dla naturalnego efektu",
      price: "180 zł",
      duration: "120 min",
    },
    {
      name: "Objętość 2D–6D",
      desc: "Intensywny, teatralny wygląd",
      price: "250 zł",
      duration: "150 min",
    },
    {
      name: "Lifting rzęs",
      desc: "Podkręcenie i laminowanie",
      price: "130 zł",
      duration: "60 min",
    },
    {
      name: "Regulacja i henna brwi",
      desc: "Modelowanie idealnego łuku",
      price: "90 zł",
      duration: "45 min",
    },
  ],
  dlonie: [
    {
      name: "Manicure hybrydowy",
      desc: "Trwały kolor do 4 tygodni",
      price: "110 zł",
      duration: "60 min",
    },
    {
      name: "Pedicure spa",
      desc: "Relaksująca pielęgnacja stóp",
      price: "150 zł",
      duration: "75 min",
    },
    {
      name: "Przedłużanie paznokci",
      desc: "Żel lub akryl, dowolny kształt",
      price: "180 zł",
      duration: "120 min",
    },
    {
      name: "Nail art premium",
      desc: "Unikalne wzory i zdobienia",
      price: "150 zł+",
      duration: "90 min",
    },
  ],
  cialo: [
    {
      name: "Masaż relaksacyjny",
      desc: "Uwolnienie napięcia i głęboki relaks",
      price: "200 zł",
      duration: "60 min",
    },
    {
      name: "Peeling ciała",
      desc: "Wygładzenie i rozświetlenie skóry",
      price: "160 zł",
      duration: "60 min",
    },
    {
      name: "Depilacja woskiem",
      desc: "Gładka skóra na długo",
      price: "80–200 zł",
      duration: "30–60 min",
    },
    {
      name: "Owijanie algowe",
      desc: "Detoks i intensywne nawilżenie",
      price: "220 zł",
      duration: "90 min",
    },
  ],
  pielegnacja: [
    {
      name: "Mikrodermabrazja",
      desc: "Mechaniczne złuszczanie i wygładzenie",
      price: "200 zł",
      duration: "60 min",
    },
    {
      name: "Oczyszczanie ultradźwiękowe",
      desc: "Głębokie oczyszczenie porów",
      price: "170 zł",
      duration: "45 min",
    },
    {
      name: "Maska algowa",
      desc: "Intensywne nawilżenie i kojenie",
      price: "140 zł",
      duration: "45 min",
    },
    {
      name: "Zabieg anti-aging",
      desc: "Redukcja zmarszczek i poprawa napięcia",
      price: "310 zł",
      duration: "75 min",
    },
  ],
  solarium: [
    {
      name: "Opalenizna natryskowa",
      desc: "Naturalny złocisty efekt bez słońca",
      price: "120 zł",
      duration: "30 min",
    },
    {
      name: "Solarium premium",
      desc: "Kolagenolampy dla skóry i urody",
      price: "60 zł",
      duration: "15 min",
    },
    {
      name: "Pielęgnacja po opalaniu",
      desc: "Intensywne nawilżenie i utrwalenie koloru",
      price: "90 zł",
      duration: "30 min",
    },
    {
      name: "Pakiet opalenizna + ciało",
      desc: "Kompletny rytuał złotej skóry",
      price: "280 zł",
      duration: "90 min",
    },
  ],
};
function renderServices(c) {
  document.getElementById("servicesGrid").innerHTML = servicesData[c]
    .map(function (s) {
      return (
        '<div class="col-sm-6 col-lg-3"><div class="rb-service-card h-100 d-flex flex-column"><h3 class="rb-service-name">' +
        s.name +
        '</h3><p class="rb-service-desc mb-4">' +
        s.desc +
        '</p><div class="d-flex justify-content-between align-items-end mt-auto"><span class="rb-service-price">' +
        s.price +
        '</span><span class="rb-service-duration">' +
        s.duration +
        "</span></div></div></div>"
      );
    })
    .join("");
}
document.getElementById("serviceTabs").addEventListener("click", function (e) {
  var b = e.target.closest(".rb-tab-btn");
  if (!b) return;
  document.querySelectorAll(".rb-tab-btn").forEach(function (x) {
    x.classList.remove("active");
  });
  b.classList.add("active");
  renderServices(b.dataset.category);
});
renderServices("twarz");
function openLightbox(el) {
  document.getElementById("lightboxImg").src = el.querySelector("img").src;
  document.getElementById("lightbox").classList.add("open");
  document.body.style.overflow = "hidden";
}
function closeLightbox() {
  document.getElementById("lightbox").classList.remove("open");
  document.body.style.overflow = "";
}
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") closeLightbox();
});
var testimonials = [
    {
      text: "Royal Beauty to miejsce, do którego wracam co miesiąc. Profesjonalizm, luksusowe produkty i atmosfera sprawiają, że czuję się wyjątkowo.",
      name: "Aleksandra Wiśniewska",
      role: "Stała klientka od 3 lat",
      initials: "AW",
    },
    {
      text: "Przedłużanie rzęs wykonane perfekcyjnie. Efekt naturalny i trwały. Polecam wszystkim szukającym jakości premium.",
      name: "Katarzyna Nowak",
      role: "Klientka",
      initials: "KN",
    },
    {
      text: "Zabieg liftingujący twarzy przyniósł spektakularne efekty. Skóra wygląda promiennie i młodziej.",
      name: "Monika Kowalczyk",
      role: "Klientka",
      initials: "MK",
    },
    {
      text: "Mezoterapia igłowa to mój ulubiony zabieg. Efekty są spektakularne, a rytuał przeprowadzony z niezwykłą delikatnością.",
      name: "Joanna Malinowska",
      role: "Klientka od roku",
      initials: "JM",
    },
    {
      text: "Manicure hybrydowy trwa u mnie ponad 4 tygodnie. Wyjątkowe miejsce z wyjątkowym podejściem.",
      name: "Ewa Zielińska",
      role: "Klientka",
      initials: "EZ",
    },
  ],
  tIdx = 0;
function renderTestimonial(i) {
  var t = testimonials[i];
  document.getElementById("testimonialText").textContent = "„" + t.text + '"';
  document.getElementById("testimonialName").textContent = t.name;
  document.getElementById("testimonialRole").textContent = t.role;
  document.getElementById("testimonialAvatar").textContent = t.initials;
  document.querySelectorAll(".rb-dot").forEach(function (d, j) {
    d.classList.toggle("active", j === i);
    d.style.width = j === i ? "2rem" : "1rem";
  });
}
function buildDots() {
  document.getElementById("testimonialDots").innerHTML = testimonials
    .map(function (_, i) {
      return (
        '<button class="rb-dot' +
        (i === 0 ? " active" : "") +
        '" style="width:' +
        (i === 0 ? "2rem" : "1rem") +
        '" onclick="goTestimonial(' +
        i +
        ')"></button>'
      );
    })
    .join("");
}
function goTestimonial(i) {
  tIdx = i;
  renderTestimonial(i);
}
function prevTestimonial() {
  tIdx = (tIdx - 1 + testimonials.length) % testimonials.length;
  renderTestimonial(tIdx);
}
function nextTestimonial() {
  tIdx = (tIdx + 1) % testimonials.length;
  renderTestimonial(tIdx);
}
buildDots();
renderTestimonial(0);
setInterval(nextTestimonial, 6000);
(function () {
  var d = document.getElementById("bookingDate");
  if (d) d.min = new Date().toISOString().split("T")[0];
})();
function submitBooking(e) {
  e.preventDefault();
  document.getElementById("bookingForm").classList.add("d-none");
  document.getElementById("bookingSuccess").classList.remove("d-none");
}
function resetBookingForm() {
  document.getElementById("bookingForm").reset();
  document.getElementById("bookingForm").classList.remove("d-none");
  document.getElementById("bookingSuccess").classList.add("d-none");
}
(function () {
  var el = document.getElementById("footerYear");
  if (el)
    el.textContent =
      "© " +
      new Date().getFullYear() +
      " Royal Beauty Studio Urody. Wszelkie prawa zastrzeżone.";
})();
