// Panel calendar (FullCalendar v6, standard bundle from the CDN — MIT, no premium plugins).
// Events (appointments + background working hours/blocks) come from /panel/calendar/events/,
// which FullCalendar calls itself with ?start=&end= for the visible range.
(function () {
  const el = document.getElementById('calendar');
  if (!el || !window.FullCalendar) return;

  const { eventsUrl, createUrl, employee } = el.dataset;
  const isNarrow = window.matchMedia('(max-width: 767.98px)').matches;

  const calendar = new FullCalendar.Calendar(el, {
    locale: 'pl',
    timeZone: 'local',
    initialView: isNarrow ? 'listWeek' : 'timeGridWeek',
    headerToolbar: isNarrow
      ? { left: 'prev,next', center: 'title', right: 'today' }
      : { left: 'prev,next today', center: 'title', right: 'timeGridWeek,timeGridDay,listWeek' },
    firstDay: 1,
    allDaySlot: false,
    slotMinTime: '07:00:00',
    slotMaxTime: '21:00:00',
    slotDuration: '00:15:00',
    slotLabelInterval: '01:00',
    nowIndicator: true,
    height: 'auto',
    events: {
      url: eventsUrl,
      extraParams: employee ? { employee } : {},
      failure: () => alertBox('Nie udało się wczytać kalendarza. Odśwież stronę.'),
    },

    // Click on an empty slot -> "new appointment" with date/time (and the selected employee) filled in.
    // List view has no times (allDay), so only the date is passed there.
    dateClick(info) {
      const params = new URLSearchParams({ date: info.dateStr.slice(0, 10) });
      if (!info.allDay) params.set('time', info.dateStr.slice(11, 16));
      if (employee) params.set('employee', employee);
      window.location.href = `${createUrl}?${params}`;
    },
  });

  function alertBox(text) {
    const box = document.createElement('div');
    box.className = 'alert alert-danger';
    box.textContent = text;
    el.before(box);
  }

  calendar.render();
})();
