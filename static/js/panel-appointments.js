// Free-slot picker for the panel's appointment forms (create / reschedule).
// Reads service/employee/date from the form (or its data-* attributes) and lists free start times
// from /panel/slots/; clicking one fills the time input.
(function () {
  const form = document.querySelector('form[data-slots-url]');
  if (!form) return;

  const list = form.querySelector('[data-slot-list]');
  const timeInput = form.querySelector('input[name="time"]');
  const field = (name) => form.querySelector(`[name="${name}"]`);

  function value(name) {
    const input = field(name);
    if (input) return input.value;
    return form.dataset[name] || '';
  }

  function message(text) {
    list.replaceChildren();
    const span = document.createElement('span');
    span.className = 'small text-muted';
    span.textContent = text;
    list.appendChild(span);
  }

  function render(slots) {
    if (!slots.length) {
      message('Brak wolnych godzin tego dnia.');
      return;
    }
    list.replaceChildren();
    slots.forEach((slot) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-sm btn-outline-secondary panel-slot';
      button.textContent = slot;
      if (timeInput.value === slot) button.classList.add('active');
      button.addEventListener('click', () => {
        timeInput.value = slot;
        list.querySelectorAll('.panel-slot').forEach((b) => b.classList.toggle('active', b === button));
      });
      list.appendChild(button);
    });
  }

  let requestId = 0;
  async function load() {
    const service = value('service');
    const date = value('date');
    if (!service || !date) {
      message('Wybierz usługę i datę, aby zobaczyć wolne godziny.');
      return;
    }
    const params = new URLSearchParams({ service, date });
    const employee = value('employee');
    if (employee) params.set('employee', employee);
    if (form.dataset.exclude) params.set('exclude', form.dataset.exclude);

    const current = ++requestId;
    message('Ładowanie…');
    try {
      const response = await fetch(`${form.dataset.slotsUrl}?${params}`, { headers: { Accept: 'application/json' } });
      if (current !== requestId) return; // a newer request superseded this one
      if (!response.ok) throw new Error(response.status);
      render((await response.json()).slots);
    } catch (error) {
      if (current === requestId) message('Nie udało się pobrać wolnych godzin.');
    }
  }

  ['service', 'employee', 'date'].forEach((name) => {
    const input = field(name);
    if (input) input.addEventListener('change', load);
  });
  timeInput.addEventListener('input', () => {
    list.querySelectorAll('.panel-slot').forEach((b) => b.classList.toggle('active', b.textContent === timeInput.value));
  });
  load();
})();
