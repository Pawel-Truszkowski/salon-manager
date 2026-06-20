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

var servicesData = {};
var activeCategory = "twarz";

function renderServices(category) {
  var grid = document.getElementById("servicesGrid");
  var items = servicesData[category];
  if (!items || items.length === 0) {
    grid.innerHTML = '<div class="col-12 text-center py-5"><p class="rb-body-text">Brak usług w tej kategorii.</p></div>';
    return;
  }
  grid.innerHTML = items
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
  activeCategory = b.dataset.category;
  renderServices(activeCategory);
});

fetch("/api/services/")
  .then(function (r) { return r.json(); })
  .then(function (data) {
    data.forEach(function (s) {
      var cat = s.category.slug;
      if (!servicesData[cat]) servicesData[cat] = [];
      servicesData[cat].push({
        name: s.name,
        desc: s.description || "",
        price: parseFloat(s.price).toFixed(0) + " zł",
        duration: s.duration + " min",
      });
    });
    renderServices(activeCategory);
  })
  .catch(function () {
    renderServices(activeCategory);
  });
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
