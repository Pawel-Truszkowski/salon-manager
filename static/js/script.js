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
var defaultTab = document.querySelector(".rb-tab-btn.active");
var activeCategory = defaultTab ? defaultTab.dataset.category : "";

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
    var serviceSelect = document.getElementById("bookingService");
    serviceSelect.innerHTML = '<option value="" disabled selected>Wybierz usługę...</option>';
    data.forEach(function (s) {
      var cat = s.category.slug;
      if (!servicesData[cat]) servicesData[cat] = [];
      servicesData[cat].push({
        name: s.name,
        desc: s.description || "",
        price: parseFloat(s.price).toFixed(0) + " zł",
        duration: s.duration + " min",
      });
      var opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name + " — " + parseFloat(s.price).toFixed(0) + " zł";
      serviceSelect.appendChild(opt);
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

// ── Booking ───────────────────────────────────────────────────────────────────

var bookingPicker = flatpickr("#bookingDate", {
  minDate: "today",
  dateFormat: "Y-m-d",
  locale: "pl",
  enable: [],
  onMonthChange: function (selectedDates, dateStr, instance) {
    var serviceId = document.getElementById("bookingService").value;
    if (serviceId) {
      loadAvailableDates(serviceId, instance.currentYear, instance.currentMonth + 1);
    }
  },
  onChange: function (selectedDates, dateStr) {
    if (dateStr) fetchSlots();
    else resetTimeSlots("Najpierw wybierz usługę i datę");
  },
});

function loadAvailableDates(serviceId, year, month) {
  var employeeId = document.getElementById("bookingEmployee").value;
  var monthStr = year + "-" + String(month).padStart(2, "0");
  var url = "/api/available-dates/?service=" + serviceId + "&month=" + monthStr;
  if (employeeId) url += "&employee=" + employeeId;

  fetch(url)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      bookingPicker.set("enable", data.dates || []);
    })
    .catch(function () {
      bookingPicker.set("enable", []);
    });
}

function resetTimeSlots(msg) {
  document.getElementById("bookingTime").innerHTML =
    '<option value="" disabled selected>' + (msg || "Wybierz datę i usługę") + "</option>";
}

function fetchEmployees(serviceId) {
  var empSelect = document.getElementById("bookingEmployee");
  empSelect.innerHTML = '<option value="">Dowolna specjalistka</option>';
  resetTimeSlots();
  if (!serviceId) return;
  fetch("/api/employees/?service=" + serviceId)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      data.forEach(function (emp) {
        var opt = document.createElement("option");
        opt.value = emp.id;
        opt.textContent = emp.first_name;
        empSelect.appendChild(opt);
      });
    });
}

function fetchSlots() {
  var serviceId = document.getElementById("bookingService").value;
  var date = document.getElementById("bookingDate").value;
  var employeeId = document.getElementById("bookingEmployee").value;
  var timeSelect = document.getElementById("bookingTime");

  if (!serviceId || !date) {
    resetTimeSlots("Najpierw wybierz usługę i datę");
    return;
  }

  timeSelect.innerHTML = '<option value="" disabled selected>Ładowanie terminów...</option>';

  var url = "/api/available-slots/?service=" + serviceId + "&date=" + date;
  if (employeeId) url += "&employee=" + employeeId;

  fetch(url)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (!data.slots || data.slots.length === 0) {
        resetTimeSlots("Brak wolnych terminów w tym dniu");
        return;
      }
      timeSelect.innerHTML = '<option value="" disabled selected>Wybierz godzinę...</option>';
      data.slots.forEach(function (slot) {
        var opt = document.createElement("option");
        opt.value = slot;
        opt.textContent = slot;
        timeSelect.appendChild(opt);
      });
    })
    .catch(function () {
      resetTimeSlots("Błąd ładowania terminów");
    });
}

document.getElementById("bookingService").addEventListener("change", function () {
  var serviceId = this.value;
  fetchEmployees(serviceId);
  bookingPicker.clear();
  bookingPicker.set("enable", []);
  resetTimeSlots("Najpierw wybierz usługę i datę");
  if (serviceId) {
    loadAvailableDates(serviceId, bookingPicker.currentYear, bookingPicker.currentMonth + 1);
  }
});

document.getElementById("bookingEmployee").addEventListener("change", function () {
  var serviceId = document.getElementById("bookingService").value;
  bookingPicker.clear();
  resetTimeSlots("Najpierw wybierz usługę i datę");
  if (serviceId) {
    loadAvailableDates(serviceId, bookingPicker.currentYear, bookingPicker.currentMonth + 1);
  }
});

function setFieldError(el, msg) {
  el.classList.add("is-invalid");
  var fb = el.parentElement.querySelector(".invalid-feedback");
  if (!fb) {
    fb = document.createElement("div");
    fb.className = "invalid-feedback";
    el.parentElement.appendChild(fb);
  }
  fb.textContent = msg;
}

function clearFieldError(el) {
  el.classList.remove("is-invalid");
  var fb = el.parentElement.querySelector(".invalid-feedback");
  if (fb) fb.remove();
}

function clearAllErrors(form) {
  form.querySelectorAll(".is-invalid").forEach(function (el) { el.classList.remove("is-invalid"); });
  form.querySelectorAll(".invalid-feedback").forEach(function (el) { el.remove(); });
}

function validateBookingForm() {
  var form = document.getElementById("bookingForm");
  clearAllErrors(form);
  var valid = true;

  var name = document.getElementById("clientName");
  if (!name.value.trim()) {
    setFieldError(name, "Imię i nazwisko jest wymagane.");
    valid = false;
  }

  var phone = document.getElementById("clientPhone");
  if (!phone.value.trim()) {
    setFieldError(phone, "Numer telefonu jest wymagany.");
    valid = false;
  } else if (!/^\+?[\d\s\-]{7,15}$/.test(phone.value.trim())) {
    setFieldError(phone, "Podaj prawidłowy numer telefonu.");
    valid = false;
  }

  var email = document.getElementById("clientEmail");
  if (!email.value.trim()) {
    setFieldError(email, "Adres e-mail jest wymagany.");
    valid = false;
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) {
    setFieldError(email, "Podaj prawidłowy adres e-mail.");
    valid = false;
  }

  var service = document.getElementById("bookingService");
  if (!service.value) {
    setFieldError(service, "Wybierz usługę.");
    valid = false;
  }

  var date = document.getElementById("bookingDate");
  if (!date.value) {
    setFieldError(date, "Wybierz datę.");
    valid = false;
  }

  var time = document.getElementById("bookingTime");
  if (!time.value) {
    setFieldError(time, "Wybierz godzinę.");
    valid = false;
  }

  return valid;
}

["clientName", "clientPhone", "clientEmail"].forEach(function (id) {
  document.getElementById(id).addEventListener("input", function () { clearFieldError(this); });
});
["bookingService", "bookingDate", "bookingTime"].forEach(function (id) {
  document.getElementById(id).addEventListener("change", function () { clearFieldError(this); });
});

function submitBooking(e) {
  e.preventDefault();
  if (!validateBookingForm()) return;
  var form = document.getElementById("bookingForm");
  var btn = form.querySelector('button[type="submit"]');
  btn.disabled = true;
  btn.textContent = "Wysyłanie...";

  var csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
  var body = new URLSearchParams({
    csrfmiddlewaretoken: csrf,
    client_name: document.getElementById("clientName").value,
    client_phone: document.getElementById("clientPhone").value,
    client_email: document.getElementById("clientEmail").value,
    service: document.getElementById("bookingService").value,
    employee: document.getElementById("bookingEmployee").value,
    date: document.getElementById("bookingDate").value,
    time: document.getElementById("bookingTime").value,
    notes: document.getElementById("bookingNotes").value,
  });

  fetch("/bookings/", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.ok) {
        form.classList.add("d-none");
        document.getElementById("bookingSuccess").classList.remove("d-none");
      } else {
        alert(data.error || "Wystąpił błąd. Spróbuj ponownie.");
      }
    })
    .catch(function () {
      alert("Błąd połączenia. Spróbuj ponownie.");
    })
    .finally(function () {
      btn.disabled = false;
      btn.textContent = "Wyślij prośbę o rezerwację";
    });
}

function resetBookingForm() {
  var form = document.getElementById("bookingForm");
  form.reset();
  clearAllErrors(form);
  bookingPicker.clear();
  bookingPicker.set("enable", []);
  document.getElementById("bookingEmployee").innerHTML = '<option value="">Dowolna specjalistka</option>';
  resetTimeSlots("Najpierw wybierz usługę i datę");
  form.classList.remove("d-none");
  document.getElementById("bookingSuccess").classList.add("d-none");
}

// ── Footer ────────────────────────────────────────────────────────────────────

(function () {
  var el = document.getElementById("footerYear");
  if (el)
    el.textContent =
      "© " +
      new Date().getFullYear() +
      " Royal Beauty Studio Urody. Wszelkie prawa zastrzeżone.";
})();


