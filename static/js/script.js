// Same-page links (logo, menu, "#rezerwacja" buttons): smooth scroll, close the mobile menu.
// Header offset comes from `scroll-padding-top` in CSS. Links to other pages (e.g. the menu on
// the cancel-booking page pointing at "/#cennik") just navigate.
var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

// Price list tabs: one category at a time instead of the whole list to scroll through.
// Without JS all categories stay visible, one under another, with the index as anchor links;
// the hidden ones stay in the HTML, so search engines still read the whole price list.
(function () {
  var menu = document.getElementById("cennik");
  var tabs = menu ? Array.prototype.slice.call(menu.querySelectorAll(".rb-menu-index a")) : [];
  if (!tabs.length) return;
  var list = tabs[0].closest("ol");
  var panels = tabs.map(function (tab) {
    return document.getElementById(tab.hash.slice(1));
  });

  menu.classList.add("rb-menu-tabbed");
  list.setAttribute("role", "tablist");
  list.setAttribute("aria-label", "Kategorie cennika");
  tabs.forEach(function (tab, i) {
    tab.parentElement.setAttribute("role", "presentation");
    tab.setAttribute("role", "tab");
    tab.setAttribute("aria-controls", panels[i].id);
    tab.id = panels[i].id + "-tab";
    panels[i].setAttribute("role", "tabpanel");
    panels[i].setAttribute("aria-labelledby", tab.id);
  });

  // `byUser`: a click or a key; on page load nothing may scroll
  function select(index, byUser) {
    tabs.forEach(function (tab, i) {
      var active = i === index;
      tab.setAttribute("aria-selected", active ? "true" : "false");
      tab.tabIndex = active ? 0 : -1;
      panels[i].hidden = !active;
    });
    // Phones: the categories are a sideways-scrolling strip; bring the chosen one into it (sideways only)
    var tab = tabs[index];
    if (tab.offsetLeft < list.scrollLeft || tab.offsetLeft + tab.offsetWidth > list.scrollLeft + list.clientWidth) {
      list.scrollLeft = tab.offsetLeft - 16;
    }
    if (!byUser) return;
    // Switching from deep inside a long category: back up to the strip so the new one starts in view
    if (list.getBoundingClientRect().top < 0) list.scrollIntoView({ block: "start" });
  }

  tabs.forEach(function (tab, i) {
    tab.addEventListener("click", function (e) {
      e.preventDefault();
      select(i, true);
      history.replaceState(null, "", tab.hash);
    });
    tab.addEventListener("keydown", function (e) {
      var keys = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1, Home: 0, End: tabs.length - 1 };
      if (!(e.key in keys)) return;
      e.preventDefault();
      var next = (keys[e.key] + tabs.length) % tabs.length;
      select(next, true);
      tabs[next].focus({ preventScroll: true }); // a click focuses the link by itself
    });
  });

  // A link straight to a category ("/#depilacja-laserowa") opens its tab
  function fromHash() {
    return panels.findIndex(function (panel) {
      return "#" + panel.id === location.hash;
    });
  }
  select(Math.max(fromHash(), 0), false);
  window.addEventListener("hashchange", function () {
    if (fromHash() >= 0) select(fromHash(), false);
  });
})();

document.querySelectorAll("a[href]").forEach(function (a) {
  if (a.origin !== location.origin || a.pathname !== location.pathname) return;
  if (a.getAttribute("role") === "tab") return; // price list tabs switch, they don't scroll
  a.addEventListener("click", function (e) {
    var target = a.hash ? document.querySelector(a.hash) : document.body;
    if (!target) return;
    e.preventDefault();
    target.scrollIntoView({ behavior: reduceMotion.matches ? "auto" : "smooth" });
    var m = document.getElementById("navMenu");
    if (m && m.classList.contains("show")) bootstrap.Collapse.getInstance(m).hide();
  });
});

// "Zarezerwuj ten zabieg" in the price list: preselect the service in the booking form.
// The link itself is href="#rezerwacja", so scrolling is handled by the same-page link handler above.
document.addEventListener("click", function (e) {
  var link = e.target.closest("[data-book-service]");
  if (!link) return;
  var select = document.getElementById("bookingService");
  select.value = link.dataset.bookService;
  select.dispatchEvent(new Event("change"));
});

function openLightbox(el) {
  var thumb = el.querySelector("img");
  var big = document.getElementById("lightboxImg");
  big.src = thumb.src;
  big.alt = thumb.alt;
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
    else resetTimeSlots("Najpierw wybierz zabieg i dzień");
  },
});

// The specialist picker is rendered only when 2+ employees are active; without it the server picks one
var employeeSelect = document.getElementById("bookingEmployee");

function selectedEmployee() {
  return employeeSelect ? employeeSelect.value : "";
}

function loadAvailableDates(serviceId, year, month) {
  var employeeId = selectedEmployee();
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
    '<option value="" disabled selected>' + (msg || "Najpierw wybierz zabieg i dzień") + "</option>";
}

function fetchEmployees(serviceId) {
  var empSelect = employeeSelect;
  resetTimeSlots();
  if (!empSelect) return;
  empSelect.innerHTML = '<option value="">Dowolna specjalistka</option>';
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
  var employeeId = selectedEmployee();
  var timeSelect = document.getElementById("bookingTime");

  if (!serviceId || !date) {
    resetTimeSlots("Najpierw wybierz zabieg i dzień");
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

// Only the home page has the booking form; on subpages (legal pages, cancel link, 404) there is nothing to bind
var serviceSelect = document.getElementById("bookingService");
if (serviceSelect) serviceSelect.addEventListener("change", function () {
  var serviceId = this.value;
  fetchEmployees(serviceId);
  bookingPicker.clear();
  bookingPicker.set("enable", []);
  resetTimeSlots("Najpierw wybierz zabieg i dzień");
  if (serviceId) {
    loadAvailableDates(serviceId, bookingPicker.currentYear, bookingPicker.currentMonth + 1);
  }
});

if (employeeSelect) employeeSelect.addEventListener("change", function () {
  var serviceId = document.getElementById("bookingService").value;
  bookingPicker.clear();
  resetTimeSlots("Najpierw wybierz zabieg i dzień");
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
    setFieldError(service, "Wybierz zabieg.");
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
  var field = document.getElementById(id);
  if (field) field.addEventListener("input", function () { clearFieldError(this); });
});
["bookingService", "bookingDate", "bookingTime"].forEach(function (id) {
  var field = document.getElementById(id);
  if (field) field.addEventListener("change", function () { clearFieldError(this); });
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
    employee: selectedEmployee(),
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
  if (employeeSelect) employeeSelect.innerHTML = '<option value="">Dowolna specjalistka</option>';
  resetTimeSlots("Najpierw wybierz zabieg i dzień");
  form.classList.remove("d-none");
  document.getElementById("bookingSuccess").classList.add("d-none");
}
