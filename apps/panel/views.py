import contextlib
import datetime
from collections import defaultdict

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView

from apps.bookings.emails import send_confirmation_email
from apps.bookings.models import Appointment
from apps.bookings.utils import get_available_slots
from apps.services.models import Employee, Service, TimeBlock, WeeklyScheduleEntry
from apps.services.scheduling import generate_schedules

from .forms import (
    AppointmentCreateForm,
    GenerateScheduleForm,
    RescheduleForm,
    TimeBlockForm,
    WeeklyScheduleFormSet,
)
from .mixins import PanelAccessMixin


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
        initial = super().get_initial()
        if date := self.request.GET.get('date'):
            initial['date'] = date
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
            employees = service.employees.filter(pk=employee_id) if employee_id else service.employees.all()
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
        context['employees'] = Employee.objects.order_by('first_name') if self.is_owner else []
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
            self.target = self.employee or Employee.objects.order_by('first_name').first()
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

        # Working hours / blocks only make sense for one person (an "all employees" view would be a mess)
        if not self.is_owner:
            events += self.background_events(self.employee, start, end)
        elif employee_id.isdigit():
            employee = Employee.objects.filter(pk=employee_id).first()
            if employee:
                events += self.background_events(employee, start, end)
        return JsonResponse(events, safe=False)

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
        }

    @staticmethod
    def parse_datetime(value):
        """ISO string from FullCalendar -> aware datetime (a bare date like `2026-10-12` is local midnight)."""
        parsed = datetime.datetime.fromisoformat(value)
        return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
