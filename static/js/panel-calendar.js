// Panel calendar (FullCalendar v6, standard bundle from the CDN — MIT, no premium plugins).
// Events (appointments + background working hours/blocks) come from /panel/calendar/events/,
// which FullCalendar calls itself with ?start=&end= for the visible range.
(function () {
  const el = document.getElementById('calendar');
  if (!el || !window.FullCalendar) return;

  const { eventsUrl, createUrl, employee, csrfToken } = el.dataset;
  const isNarrow = window.matchMedia('(max-width: 767.98px)').matches;

  const calendar = new FullCalendar.Calendar(el, {
    locale: 'pl',
    timeZone: 'local',
    initialView: isNarrow ? 'listWeek' : 'timeGridWeek',
    headerToolbar: isNarrow
      ? { left: 'prev,next', center: 'title', right: 'today' }
      : { left: 'prev,next today', center: 'title', right: 'timeGridWeek,timeGridDay,listWeek' },
    firstDay: 1,
    // The all-day row is the "Grafik" strip: who works when and blocked periods (chips from the server)
    allDaySlot: true,
    allDayText: 'Grafik',
    eventOrder: 'order,title',
    slotMinTime: '07:00:00',
    slotMaxTime: '21:00:00',
    slotDuration: '00:15:00',
    slotLabelInterval: '01:00',
    nowIndicator: true,
    height: 'auto',
    events: {
      url: eventsUrl,
      extraParams: employee ? { employee } : {},
      failure: () => flash('Nie udało się wczytać kalendarza. Odśwież stronę.'),
    },

    // Click on an empty slot -> "new appointment" with date/time (and the selected employee) filled in.
    // List view has no times (allDay), so only the date is passed there.
    dateClick(info) {
      const params = new URLSearchParams({ date: info.dateStr.slice(0, 10) });
      if (!info.allDay) params.set('time', info.dateStr.slice(11, 16));
      if (employee) params.set('employee', employee);
      window.location.href = `${createUrl}?${params}`;
    },

    // Drag & drop = change the time only. Which events can move is decided per event by the server
    // (`startEditable`); resizing would change the service duration, so it's off everywhere.
    eventDurationEditable: false,
    async eventDrop(info) {
      // A move e-mails the client, and drags happen by accident — so ask first
      const when = info.event.start.toLocaleString('pl-PL', { dateStyle: 'short', timeStyle: 'short' });
      if (!window.confirm(`Przenieść wizytę „${info.event.title}” na ${when}?\nKlientka dostanie e-mail o zmianie (jeśli podała adres).`)) {
        info.revert();
        return;
      }
      const { ok, message } = await postMove(info.event);
      if (!ok) info.revert(); // the server changed nothing, so the calendar must not pretend otherwise
      flash(message, ok ? 'success' : 'danger');
    },
  });

  // POST the new local date/time; resolves to {ok, message} — `message` is the server's text either way
  async function postMove(event) {
    const body = new URLSearchParams({ date: event.startStr.slice(0, 10), time: event.startStr.slice(11, 16) });
    try {
      const response = await fetch(event.extendedProps.moveUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body,
      });
      const data = await response.json();
      return { ok: response.ok, message: data.message || data.error };
    } catch {
      return { ok: false, message: 'Brak połączenia z serwerem — wizyta nie została przeniesiona.' };
    }
  }

  // Dismissible Bootstrap alert above the calendar; kind = 'danger' | 'success'
  function flash(text, kind = 'danger') {
    const box = document.createElement('div');
    box.className = `alert alert-${kind} alert-dismissible fade show`;
    box.textContent = text;
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'btn-close';
    close.dataset.bsDismiss = 'alert';
    close.ariaLabel = 'Zamknij';
    box.append(close);
    el.closest('.card').before(box);
  }

  calendar.render();
})();
