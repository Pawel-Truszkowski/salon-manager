import contextlib
import datetime
import logging
from collections import defaultdict

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView

from apps.bookings.emails import send_confirmation_email
from apps.bookings.models import Appointment
from apps.bookings.utils import get_available_slots
from apps.services.models import Employee, Equipment, EquipmentRental, Schedule, Service, TimeBlock, WeeklyScheduleEntry
from apps.services.scheduling import generate_schedules

from .forms import (
    AppointmentCreateForm,
    EmployeeForm,
    EquipmentForm,
    EquipmentRentalForm,
    GenerateScheduleForm,
    InviteEmployeeForm,
    RescheduleForm,
    ServiceForm,
    TimeBlockForm,
    WeeklyScheduleFormSet,
)
from .invitations import create_invited_account, is_pending_invitation, send_invitation
from .mixins import OwnerRequiredMixin, PanelAccessMixin

logger = logging.getLogger(__name__)


class DashboardView(PanelAccessMixin, TemplateView):
    template_name = 'panel/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = self.scope_to_employee(Appointment.objects.select_related('service', 'employee'))
        now = timezone.now()

        context['today_appointments'] = (
            appointments.filter(date_time__date=timezone.localdate())
            .exclude(status=Appointment.Status.CANCELLED)
            .order_by('date_time')
        )
        context['pending_appointments'] = appointments.filter(
            status=Appointment.Status.PENDING, date_time__gte=now
        ).order_by('date_time')
        return context


class AppointmentScopeMixin(PanelAccessMixin):
    """Appointments visible to the current user; someone else's appointment is a 404 for an employee."""

    def get_appointments(self):
        return self.scope_to_employee(Appointment.objects.select_related('service', 'employee', 'updated_by'))

    def get_appointment(self):
        return get_object_or_404(self.get_appointments(), pk=self.kwargs['pk'])


class AppointmentListView(AppointmentScopeMixin, ListView):
    template_name = 'panel/appointments/list.html'
    context_object_name = 'appointments'
    paginate_by = 25

    def get_filters(self):
        params = self.request.GET
        filters = {
            'status': params.get('status', ''),
            'employee': params.get('employee', '') if self.is_owner else '',
            'date_from': params.get('date_from', timezone.localdate().isoformat()),
            'date_to': params.get('date_to', ''),
            'q': params.get('q', '').strip(),
        }
        return filters

    def get_queryset(self):
        self.filters = self.get_filters()
        queryset = self.get_appointments().order_by('date_time')
        f = self.filters
        if f['status'] in Appointment.Status.values:
            queryset = queryset.filter(status=f['status'])
        if f['employee'].isdigit():
            queryset = queryset.filter(employee_id=f['employee'])
        for key, lookup in (('date_from', 'date_time__date__gte'), ('date_to', 'date_time__date__lte')):
            with contextlib.suppress(ValueError):  # empty or malformed date -> no filter
                queryset = queryset.filter(**{lookup: datetime.date.fromisoformat(f[key])})
        if f['q']:
            queryset = queryset.filter(
                Q(client_name__icontains=f['q']) | Q(client_phone__icontains=f['q']) | Q(client_email__icontains=f['q'])
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filters'] = self.filters
        context['statuses'] = Appointment.Status.choices
        context['employees'] = Employee.objects.order_by('first_name') if self.is_owner else []
        params = self.request.GET.copy()
        params.pop('page', None)
        context['filter_querystring'] = params.urlencode()
        return context


class AppointmentDetailView(AppointmentScopeMixin, DetailView):
    template_name = 'panel/appointments/detail.html'
    context_object_name = 'appointment'

    def get_object(self, queryset=None):
        return self.get_appointment()


class AppointmentCreateView(PanelAccessMixin, CreateView):
    template_name = 'panel/appointments/form.html'
    form_class = AppointmentCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(is_owner=self.is_owner, employee=self.employee)
        return kwargs

    def get_initial(self):
        # Prefill from the calendar's "click an empty slot"; the form still validates everything
        initial = super().get_initial()
        params = self.request.GET
        for name in ('date', 'time'):
            if value := params.get(name):
                initial[name] = value
        if params.get('employee', '').isdigit():
            initial['employee'] = params['employee']  # ignored for employees: their form has no such field
        return initial

    def form_valid(self, form):
        appointment = form.save(commit=False)
        appointment.updated_by = self.request.user
        # Created by the salon: skip "booking received" + salon notification, send "confirmed" instead
        appointment._skip_booking_emails = True
        appointment.save()
        send_confirmation_email(appointment)
        messages.success(self.request, f'Dodano wizytę: {appointment}.')
        return redirect('panel:appointment_detail', pk=appointment.pk)


class AppointmentRescheduleView(AppointmentScopeMixin, FormView):
    template_name = 'panel/appointments/reschedule.html'
    form_class = RescheduleForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(appointment=self.appointment, is_owner=self.is_owner)
        return kwargs

    def get(self, request, *args, **kwargs):
        return self._guard() or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._guard() or super().post(request, *args, **kwargs)

    def _guard(self):
        self.appointment = self.get_appointment()
        if not self.appointment.can_be_rescheduled:
            messages.error(self.request, 'Tej wizyty nie można już przenieść.')
            return redirect('panel:appointment_detail', pk=self.appointment.pk)
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['appointment'] = self.appointment
        return context

    def form_valid(self, form):
        self.appointment.updated_by = self.request.user
        self.appointment.reschedule(form.cleaned_data['date_time'], employee=form.cleaned_data['employee'])
        messages.success(self.request, f'Przeniesiono wizytę na {self.appointment.date_time:%d.%m.%Y %H:%M}.')
        return redirect('panel:appointment_detail', pk=self.appointment.pk)


class AppointmentActionView(AppointmentScopeMixin, View):
    http_method_names = ['post']

    def post(self, request, pk, action):
        appointment = self.get_appointment()
        appointment.updated_by = request.user

        if action == 'confirm' and appointment.status == Appointment.Status.PENDING:
            appointment.confirm()
            messages.success(request, 'Wizyta potwierdzona.')
        elif action == 'complete' and appointment.status == Appointment.Status.CONFIRMED:
            appointment.complete()
            messages.success(request, 'Wizyta oznaczona jako zrealizowana.')
        elif action == 'cancel' and appointment.can_be_cancelled:
            appointment.cancel(by_salon=True)
            messages.success(request, 'Wizyta odwołana.')
        else:
            messages.error(request, 'Tej akcji nie można wykonać dla tej wizyty.')

        next_url = request.POST.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
            return HttpResponseRedirect(next_url)
        return redirect('panel:appointment_detail', pk=appointment.pk)


class SlotsView(PanelAccessMixin, View):
    """Free start times (HH:MM) for the time pickers in the appointment forms."""

    def get(self, request):
        params = request.GET
        try:
            service = Service.objects.get(pk=params.get('service'))
            date = datetime.date.fromisoformat(params.get('date', ''))
        except Service.DoesNotExist, ValueError:
            return JsonResponse({'slots': []}, status=400)

        exclude = None
        if params.get('exclude'):
            exclude = get_object_or_404(self.scope_to_employee(Appointment.objects.all()), pk=params['exclude'])

        if self.is_owner:
            employee_id = params.get('employee')
            employees = service.employees.active()
            employees = employees.filter(pk=employee_id) if employee_id else employees
        else:
            employees = service.employees.filter(pk=self.employee.pk)

        slots = set()
        for employee in employees:
            slots.update(get_available_slots(employee, date, service, exclude_appointment=exclude))
        return JsonResponse({'slots': [timezone.localtime(s).strftime('%H:%M') for s in sorted(slots)]})


class TimeBlockListView(PanelAccessMixin, ListView):
    """Upcoming blocked periods (today onwards); an employee sees only her own."""

    template_name = 'panel/timeblocks/list.html'
    context_object_name = 'time_blocks'
    paginate_by = 25

    def get_queryset(self):
        return self.scope_to_employee(
            TimeBlock.objects.select_related('employee', 'updated_by')
            .filter(date__gte=timezone.localdate())
            .order_by('date', 'start_time')
        )


class TimeBlockCreateView(PanelAccessMixin, CreateView):
    """Add a blocked period; an employee always blocks her own time."""

    template_name = 'panel/timeblocks/form.html'
    form_class = TimeBlockForm
    success_url = reverse_lazy('panel:time_block_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(is_owner=self.is_owner, employee=self.employee)
        return kwargs

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)  # saves -> self.object
        messages.success(
            self.request,
            f'Dodano blokadę: {self.object.date:%d.%m.%Y} {self.object.start_time:%H:%M}–{self.object.end_time:%H:%M}.',
        )
        return response


class TimeBlockDeleteView(PanelAccessMixin, View):
    """POST-only delete; someone else's block is a 404 for an employee."""

    http_method_names = ['post']

    def post(self, request, pk):
        time_block = get_object_or_404(self.scope_to_employee(TimeBlock.objects), pk=pk)
        time_block.delete()
        messages.success(request, 'Blokada usunięta.')
        return redirect('panel:time_block_list')


class TargetEmployeeMixin(PanelAccessMixin):
    """Pages about one employee's schedule: owners may open anyone's, employees only their own (others = 404)."""

    def get_target_employee(self, pk):
        # scope_to_employee() filters rows that *belong to* an employee; here the row *is* the employee
        employees = Employee.objects.all() if self.is_owner else Employee.objects.filter(pk=self.employee.pk)
        return get_object_or_404(employees, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_employee'] = self.target
        context['employees'] = Employee.objects.active().order_by('first_name') if self.is_owner else []
        return context


class WeeklyScheduleEditView(TargetEmployeeMixin, TemplateView):
    """Edit one employee's weekly template (several blocks per day allowed)."""

    template_name = 'panel/schedule/weekly.html'

    def get(self, request, *args, **kwargs):
        self.target = self.get_target_employee(self.kwargs['employee_pk'])
        formset = WeeklyScheduleFormSet(instance=self.target)
        return self.render_to_response(self.get_context_data(formset=formset))

    def post(self, request, *args, **kwargs):
        self.target = self.get_target_employee(self.kwargs['employee_pk'])
        formset = WeeklyScheduleFormSet(request.POST, instance=self.target)
        if formset.is_valid():
            formset.save()
            messages.success(request, f'Zapisano szablon tygodnia: {self.target}.')
            return redirect('panel:weekly_schedule', employee_pk=self.target.pk)
        return self.render_to_response(self.get_context_data(formset=formset))


def schedule_url(employee):
    return f"{reverse('panel:schedule')}?employee={employee.pk}"


class ScheduleView(TargetEmployeeMixin, TemplateView):
    """Weekly template summary, the next weeks day by day (working hours + blocks) and the generate form."""

    template_name = 'panel/schedule/overview.html'
    days_ahead = 28

    def get(self, request, *args, **kwargs):
        employee_pk = request.GET.get('employee', '')
        if employee_pk.isdigit():
            self.target = self.get_target_employee(employee_pk)
        else:
            # Own schedule first (also for an owner who works as a specialist), otherwise the first one
            self.target = self.employee or Employee.objects.active().order_by('first_name').first()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.target is None:  # owner, no employees yet
            return context

        today = timezone.localdate()
        last_day = today + datetime.timedelta(days=self.days_ahead - 1)
        schedules, blocks = defaultdict(list), defaultdict(list)
        for schedule in self.target.schedules.filter(date__range=(today, last_day)).order_by('start_time'):
            schedules[schedule.date].append(schedule)
        for block in self.target.time_blocks.filter(date__range=(today, last_day)):
            blocks[block.date].append(block)
        context['days'] = [
            {'date': day, 'schedules': schedules[day], 'blocks': blocks[day]}
            for day in (today + datetime.timedelta(days=offset) for offset in range(self.days_ahead))
        ]

        entries = defaultdict(list)
        for entry in self.target.weekly_schedule.all():
            entries[entry.weekday].append(entry)
        context['template_days'] = [
            (label, entries.get(value, [])) for value, label in WeeklyScheduleEntry.WeekDay.choices
        ]
        context['has_template'] = bool(entries)
        context['generate_form'] = GenerateScheduleForm(initial={'date_from': today, 'date_to': last_day})
        return context


class ScheduleGenerateView(TargetEmployeeMixin, View):
    """POST-only: materialize `Schedule` rows from the employee's weekly template."""

    http_method_names = ['post']

    def post(self, request, employee_pk):
        employee = self.get_target_employee(employee_pk)
        form = GenerateScheduleForm(request.POST)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect(schedule_url(employee))

        date_from, date_to = form.cleaned_data['date_from'], form.cleaned_data['date_to']
        created = generate_schedules(employee, date_from, date_to, updated_by=request.user)
        period = f'{date_from:%d.%m.%Y}–{date_to:%d.%m.%Y}'
        if created:
            messages.success(request, f'Wygenerowano grafik ({period}): {created} bloków pracy.')
        else:
            messages.info(
                request, f'Nic nie dodano ({period}) — te dni mają już grafik albo szablon nie ma w nich godzin pracy.'
            )
        return redirect(schedule_url(employee))


def hours_label(start, end):
    """Short "from–to" label for the calendar's Grafik row, e.g. `9–17`, `9:30–17`, `12:15–13`."""

    def short(t):  # full hours without ":00" and no leading zero: the day column is narrow
        return f'{t.hour}:{t.minute:02}' if t.minute else str(t.hour)

    # Midnight as an end isn't handled: the panel forms require end > start on the same day, so it can't occur
    return f'{short(start)}–{short(end)}'


class CalendarEventsView(PanelAccessMixin, View):
    """JSON feed for FullCalendar: `GET ?start=<ISO>&end=<ISO>[&employee=<pk>]` -> list of event dicts.

    FullCalendar sends `start`/`end` as ISO datetimes with an offset (e.g. `2026-10-12T00:00:00+02:00`) and
    expects a JSON array of `{"id", "title", "start", "end", "url", "color", ...}` (ISO strings for times).
    """

    STATUS_COLORS = {
        Appointment.Status.PENDING: '#e0a100',
        Appointment.Status.CONFIRMED: '#b07d62',
        Appointment.Status.COMPLETED: '#8a9a8b',
    }
    WORKING_HOURS_COLOR = '#d1e7dd'
    TIME_BLOCK_COLOR = '#adb5bd'
    # "Grafik" row above the time grid (all-day events): who works when, who's off, blocked periods
    CHIP_WORKING = {'color': '#d1e7dd', 'textColor': '#0f5132'}
    CHIP_OFF = {'color': '#f1f3f5', 'textColor': '#6c757d'}
    CHIP_BLOCK = {'color': '#adb5bd', 'textColor': '#212529'}

    def get(self, request):
        try:
            start = self.parse_datetime(request.GET['start'])
            end = self.parse_datetime(request.GET['end'])
        except KeyError, ValueError:
            return JsonResponse({'error': 'Podaj poprawne parametry start i end (ISO 8601).'}, status=400)

        appointments = self.scope_to_employee(Appointment.objects.select_related('service', 'employee'))
        employee_id = request.GET.get('employee', '')
        if self.is_owner and employee_id.isdigit():
            appointments = appointments.filter(employee_id=employee_id)

        appointments = appointments.filter(date_time__gte=start, date_time__lt=end).exclude(
            status=Appointment.Status.CANCELLED
        )
        events = [self.appointment_event(appointment) for appointment in appointments.order_by('date_time')]

        if not self.is_owner:
            employees = [self.employee]
        elif employee_id.isdigit():
            employees = list(Employee.objects.filter(pk=employee_id))
        else:
            employees = list(Employee.objects.active().order_by('first_name', 'last_name'))

        # Shaded working hours / blocks behind the grid only for one person (for everyone they'd overlap);
        # the "Grafik" row works for any number of people
        if len(employees) == 1 and (not self.is_owner or employee_id.isdigit()):
            events += self.background_events(employees[0], start, end)
        events += self.schedule_chips(employees, start, end)
        return JsonResponse(events, safe=False)

    def schedule_chips(self, employees, start, end):
        """All-day events for the "Grafik" row: per day, each employee's hours (or "wolne"), then blocked periods.

        Days on which none of `employees` works (salon closed, weekend) get no chips at all, so the row stays empty.
        """
        first_day, last_day = timezone.localtime(start).date(), timezone.localtime(end).date()
        in_range = {'employee__in': employees, 'date__gte': first_day, 'date__lt': last_day}

        shifts = defaultdict(list)  # (date, employee_id) -> that day's Schedule rows, earliest first
        for schedule in Schedule.objects.filter(**in_range).order_by('start_time'):
            shifts[schedule.date, schedule.employee_id].append(schedule)
        blocks = defaultdict(list)  # date -> TimeBlocks
        for block in TimeBlock.objects.filter(**in_range).select_related('employee').order_by('start_time'):
            blocks[block.date].append(block)
        working_days = {date for date, _ in shifts}

        def chip(date, title, style, order):
            return {
                'title': title,
                'start': date.isoformat(),
                'allDay': True,
                'editable': False,
                'classNames': ['calendar-chip'],
                'extendedProps': {'order': order},
                **style,
            }

        events = []
        for date in sorted(working_days):
            for order, employee in enumerate(employees):
                day_shifts = shifts.get((date, employee.pk))
                if day_shifts:
                    hours = ', '.join(hours_label(s.start_time, s.end_time) for s in day_shifts)
                    events.append(chip(date, f'{employee} {hours}', self.CHIP_WORKING, order))
                else:
                    events.append(chip(date, f'{employee} — wolne', self.CHIP_OFF, order))
        for date, day_blocks in blocks.items():
            for block in day_blocks:
                title = f'⊘ {block.employee} {hours_label(block.start_time, block.end_time)}'
                if block.reason:
                    title = f'{title} {block.reason}'
                events.append(chip(date, title, self.CHIP_BLOCK, len(employees)))  # after everyone's hours
        return events

    def background_events(self, employee, start, end):
        """`Schedule` rows (working hours) and `TimeBlock`s of `employee` in [start, end) as background events.

        FullCalendar draws `{'start', 'end', 'display': 'background', 'color', 'title'?}` behind the appointments.
        """
        first_day, last_day = timezone.localtime(start).date(), timezone.localtime(end).date()

        def at(date, time):
            return timezone.make_aware(datetime.datetime.combine(date, time)).isoformat()

        events = [
            {
                'start': at(schedule.date, schedule.start_time),
                'end': at(schedule.date, schedule.end_time),
                'display': 'background',
                'color': self.WORKING_HOURS_COLOR,
            }
            for schedule in employee.schedules.filter(date__gte=first_day, date__lt=last_day)
        ]
        events += [
            {
                'title': block.reason or 'Blokada',
                'start': at(block.date, block.start_time),
                'end': at(block.date, block.end_time),
                'display': 'background',
                'color': self.TIME_BLOCK_COLOR,
            }
            for block in employee.time_blocks.filter(date__gte=first_day, date__lt=last_day)
        ]
        return events

    def appointment_event(self, appointment):
        begins = timezone.localtime(appointment.date_time)
        title = f'{appointment.client_name} — {appointment.service}'
        if self.is_owner and appointment.employee:
            # Owners may look at all employees at once, so say whose appointment it is
            title = f'{title} ({appointment.employee})'
        return {
            'id': appointment.pk,
            'title': title,
            'start': begins.isoformat(),
            'end': (begins + datetime.timedelta(minutes=appointment.service.duration)).isoformat(),
            'url': reverse('panel:appointment_detail', args=[appointment.pk]),
            'color': self.STATUS_COLORS.get(appointment.status, '#6c757d'),
            # Drag & drop only where the "Przenieś" page would allow it; the server re-checks anyway
            'startEditable': appointment.can_be_rescheduled and appointment.date_time > timezone.now(),
            'extendedProps': {'moveUrl': reverse('panel:calendar_move', args=[appointment.pk])},
        }

    @staticmethod
    def parse_datetime(value):
        """ISO string from FullCalendar -> aware datetime (a bare date like `2026-10-12` is local midnight)."""
        parsed = datetime.datetime.fromisoformat(value)
        return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed


class CalendarMoveView(AppointmentScopeMixin, View):
    """Drag & drop in the calendar: `POST date=YYYY-MM-DD&time=HH:MM` -> JSON.

    Same rules as the "Przenieś" page via `RescheduleForm`, but never `force` and never a different employee
    (the free FullCalendar has no per-employee columns to drop onto). 400 + `{"error"}` -> the JS reverts the drop.
    """

    http_method_names = ['post']

    def post(self, request, pk):
        appointment = self.get_appointment()
        if not appointment.can_be_rescheduled:
            return JsonResponse({'error': 'Tej wizyty nie można już przenieść.'}, status=400)

        data = {'date': request.POST.get('date'), 'time': request.POST.get('time'), 'employee': appointment.employee_id}
        form = RescheduleForm(data=data, appointment=appointment, is_owner=self.is_owner)
        if not form.is_valid():
            errors = [error for field_errors in form.errors.values() for error in field_errors]
            return JsonResponse({'error': ' '.join(errors)}, status=400)

        appointment.updated_by = request.user
        appointment.reschedule(form.cleaned_data['date_time'])
        moved_to = timezone.localtime(appointment.date_time)
        return JsonResponse({'message': f'Przeniesiono wizytę na {moved_to:%d.%m.%Y %H:%M}.'})


class CalendarView(PanelAccessMixin, TemplateView):
    """FullCalendar page; events come from `CalendarEventsView`. Owners pick one employee or see everyone."""

    template_name = 'panel/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee_id = self.request.GET.get('employee', '')
        context['selected_employee'] = employee_id if self.is_owner and employee_id.isdigit() else ''
        context['employees'] = Employee.objects.active().order_by('first_name') if self.is_owner else []
        return context


class EmployeeListView(OwnerRequiredMixin, ListView):
    """The salon's specialists with their services and whether they can sign in to the panel."""

    template_name = 'panel/employees/list.html'
    context_object_name = 'employees'

    def get_queryset(self):
        return (
            Employee.objects.select_related('user')
            .prefetch_related('services')
            .order_by('-is_active', 'first_name', 'last_name')  # active first, the former team below
        )


class EmployeeFormViewMixin(OwnerRequiredMixin):
    """Shared by add/edit: same form, same template, back to the list with a message."""

    template_name = 'panel/employees/form.html'
    form_class = EmployeeForm
    model = Employee
    success_url = reverse_lazy('panel:employee_list')
    success_message = ''

    def form_valid(self, form):
        response = super().form_valid(form)  # saves -> self.object (incl. the M2M services)
        messages.success(self.request, self.success_message.format(employee=self.object))
        return response


class EmployeeCreateView(EmployeeFormViewMixin, CreateView):
    success_message = 'Dodano specjalistkę: {employee}.'


class EmployeeUpdateView(EmployeeFormViewMixin, UpdateView):
    success_message = 'Zapisano zmiany: {employee}.'


def upcoming_appointments(**filters):
    """Future appointments that still need someone to show up (pending/confirmed), soonest first."""
    return Appointment.objects.filter(
        date_time__gte=timezone.now(),
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
        **filters,
    ).order_by('date_time')


class EmployeeToggleActiveView(OwnerRequiredMixin, View):
    """POST: deactivate an active employee (hidden from booking, no panel login, history kept) or reactivate."""

    http_method_names = ['post']

    def post(self, request, pk):
        employee = get_object_or_404(Employee, pk=pk)

        if not employee.is_active:
            employee.is_active = True
            employee.save(update_fields=['is_active'])
            messages.success(request, f'{employee} jest znów aktywna — klienci mogą się do niej zapisywać.')
            return redirect('panel:employee_list')

        upcoming = upcoming_appointments(employee=employee)

        next_appointment = upcoming.first()  # one query instead of exists() + first()
        if next_appointment:
            # From the DB the datetime is UTC; f-string formatting doesn't convert, so go local first
            when = timezone.localtime(next_appointment.date_time)
            messages.error(
                request,
                f'{employee} ma zaplanowane wizyty ({upcoming.count()}), najbliższa {when:%d.%m.%Y %H:%M}. '
                'Odwołaj je lub przenieś na inną specjalistkę przed dezaktywacją.',
            )
            return redirect('panel:employee_list')

        employee.is_active = False
        employee.save(update_fields=['is_active'])
        messages.success(
            request,
            f'{employee} jest teraz nieaktywna — zniknęła z rezerwacji i nie zaloguje się do panelu. '
            'Historia wizyt zostaje.',
        )
        return redirect('panel:employee_list')


class EmployeeInviteView(OwnerRequiredMixin, FormView):
    """Create a panel account for an active specialist who has none, and e-mail her the invitation."""

    template_name = 'panel/employees/invite.html'
    form_class = InviteEmployeeForm

    def dispatch(self, request, *args, **kwargs):
        self.target = get_object_or_404(Employee, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self._guard() or super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self._guard() or super().post(request, *args, **kwargs)

    def _guard(self):
        if self.target.user_id or not self.target.is_active:
            messages.error(self.request, f'{self.target} ma już konto albo jest nieaktywna — nie można jej zaprosić.')
            return redirect('panel:employee_list')
        return None

    def get_initial(self):
        # Legacy `Employee.email` (set in /admin/ before the panel) is the best guess; the owner can change it
        return {'email': self.target.email}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = self.target
        return context

    def form_valid(self, form):
        email = form.cleaned_data['email']
        user = create_invited_account(self.target, email)
        try:
            send_invitation(user)
        except Exception:  # account stays; the owner can resend from the team list
            logger.exception(f'Panel invitation for employee({self.target.pk}) failed')
            messages.error(
                self.request,
                f'Konto dla {self.target} zostało utworzone, ale maila nie udało się wysłać. '
                'Spróbuj „Wyślij zaproszenie ponownie” za chwilę.',
            )
        else:
            messages.success(self.request, f'Wysłano zaproszenie do {email}.')
        return redirect('panel:employee_list')


class EmployeeResendInviteView(OwnerRequiredMixin, View):
    """POST: send the invitation again (lost e-mail, expired link) while she hasn't set a password yet."""

    http_method_names = ['post']

    def post(self, request, pk):
        employee = get_object_or_404(Employee.objects.select_related('user'), pk=pk)
        if not employee.is_active or not is_pending_invitation(employee.user):
            messages.error(request, f'{employee} nie czeka na zaproszenie.')
            return redirect('panel:employee_list')
        try:
            send_invitation(employee.user)
        except Exception:
            logger.exception(f'Resending panel invitation for employee({employee.pk}) failed')
            messages.error(request, 'Nie udało się wysłać maila. Spróbuj ponownie za chwilę.')
        else:
            messages.success(request, f'Wysłano ponownie zaproszenie do {employee.user.email}.')
        return redirect('panel:employee_list')


class ServiceListView(OwnerRequiredMixin, ListView):
    """All services grouped by category (the website's tabs); inactive ones at the end of each group."""

    template_name = 'panel/services/list.html'
    context_object_name = 'services'

    def get_queryset(self):
        return Service.objects.select_related('category').order_by('category__name', '-is_active', 'name')


def service_list_url(service):
    """The services list opened on the service's category tab (see `static/js/panel-tabs.js`)."""
    return f"{reverse('panel:service_list')}#{service.category.slug}"


class ServiceFormViewMixin(OwnerRequiredMixin):
    template_name = 'panel/services/form.html'
    form_class = ServiceForm
    model = Service
    success_message = ''

    def get_success_url(self):
        return service_list_url(self.object)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message.format(service=self.object))
        return response


class ServiceCreateView(ServiceFormViewMixin, CreateView):
    success_message = 'Dodano usługę: {service}. Zaznacz ją w zespole u specjalistek, które ją wykonują.'


class ServiceUpdateView(ServiceFormViewMixin, UpdateView):
    success_message = 'Zapisano zmiany: {service}.'


class ServiceToggleActiveView(OwnerRequiredMixin, View):
    """POST: stop offering a service (refused while it has upcoming appointments) or offer it again."""

    http_method_names = ['post']

    def post(self, request, pk):
        service = get_object_or_404(Service.objects.select_related('category'), pk=pk)

        if not service.is_active:
            service.is_active = True
            service.save(update_fields=['is_active'])
            messages.success(request, f'Usługa „{service}” jest znów dostępna do rezerwacji.')
            return redirect(service_list_url(service))

        upcoming = upcoming_appointments(service=service)
        next_appointment = upcoming.first()
        if next_appointment:
            when = timezone.localtime(next_appointment.date_time)
            messages.error(
                request,
                f'Usługa „{service}” ma zaplanowane wizyty ({upcoming.count()}), najbliższa {when:%d.%m.%Y %H:%M}. '
                'Wyłącz ją, gdy się odbędą albo zostaną odwołane.',
            )
            return redirect(service_list_url(service))

        service.is_active = False
        service.save(update_fields=['is_active'])
        messages.success(request, f'Usługa „{service}” zniknęła ze strony i z rezerwacji. Historia wizyt zostaje.')
        return redirect(service_list_url(service))


class EquipmentListView(OwnerRequiredMixin, ListView):
    """Devices that come and go (the laser): upcoming rental days and the services that need them."""

    template_name = 'panel/equipment/list.html'
    context_object_name = 'equipment_list'

    def get_queryset(self):
        return Equipment.objects.prefetch_related(
            Prefetch('rentals', queryset=EquipmentRental.objects.upcoming(), to_attr='upcoming_rentals'),
            Prefetch('services', queryset=Service.objects.active().order_by('name'), to_attr='active_services'),
        )


class EquipmentFormViewMixin(OwnerRequiredMixin):
    template_name = 'panel/equipment/form.html'
    form_class = EquipmentForm
    model = Equipment
    success_url = reverse_lazy('panel:equipment_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Zapisano: {self.object}.')
        return response


class EquipmentCreateView(EquipmentFormViewMixin, CreateView):
    pass


class EquipmentUpdateView(EquipmentFormViewMixin, UpdateView):
    pass


class EquipmentRentalCreateView(OwnerRequiredMixin, CreateView):
    template_name = 'panel/equipment/rental_form.html'
    form_class = EquipmentRentalForm
    success_url = reverse_lazy('panel:equipment_list')

    def dispatch(self, request, *args, **kwargs):
        self.equipment = get_object_or_404(Equipment, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'equipment': self.equipment}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), 'equipment': self.equipment}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Dodano termin: {self.object}. Usługi z tym urządzeniem można zarezerwować w te dni '
            '(o ile w grafiku są godziny pracy).',
        )
        return response


class EquipmentRentalDeleteView(OwnerRequiredMixin, View):
    """POST-only; refused while clients are booked on those days for services that need the device."""

    http_method_names = ['post']

    def post(self, request, pk):
        rental = get_object_or_404(EquipmentRental.objects.select_related('equipment'), pk=pk)
        booked = upcoming_appointments(
            service__required_equipment=rental.equipment,
            date_time__date__gte=rental.date_from,
            date_time__date__lte=rental.date_to,
        )
        if booked.exists():
            messages.error(
                request,
                f'Na termin {rental.date_from:%d.%m}–{rental.date_to:%d.%m.%Y} są zapisane wizyty ({booked.count()}). '
                'Najpierw je przenieś albo odwołaj.',
            )
            return redirect('panel:equipment_list')
        rental.delete()
        messages.success(request, 'Termin usunięty.')
        return redirect('panel:equipment_list')
