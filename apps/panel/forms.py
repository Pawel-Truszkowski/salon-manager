import datetime

from django import forms
from django.utils import timezone

from apps.bookings.models import Appointment
from apps.bookings.utils import find_available_specialist, get_available_slots
from apps.services.models import Employee, TimeBlock

FORCE_HELP = 'Pozwala zapisać wizytę poza grafikiem lub na zajęty termin. Używaj świadomie.'


def add_bootstrap_classes(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            css = 'form-check-input'
        elif isinstance(widget, forms.Select):
            css = 'form-select'
        else:
            css = 'form-control'
        widget.attrs['class'] = f"{widget.attrs.get('class', '')} {css}".strip()


class SlotFieldsMixin(forms.Form):
    """Date + time (+ owner-only "force") fields and the availability check shared by create/reschedule."""

    date = forms.DateField(label='Data', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    time = forms.TimeField(label='Godzina', widget=forms.TimeInput(attrs={'type': 'time', 'step': 900}, format='%H:%M'))
    force = forms.BooleanField(label='Pomiń grafik i dostępność', required=False, help_text=FORCE_HELP)

    def setup_slot_fields(self, is_owner):
        self.is_owner = is_owner
        if not is_owner:
            del self.fields['force']
        add_bootstrap_classes(self)

    def build_date_time(self, cleaned):
        date, time = cleaned.get('date'), cleaned.get('time')
        if not date or not time:
            return None
        date_time = timezone.make_aware(datetime.datetime.combine(date, time))
        if date_time < timezone.now():
            raise forms.ValidationError('Nie można zapisać wizyty w przeszłości.')
        return date_time

    def check_slot(self, employee, service, date_time, exclude_appointment=None):
        if not employee.services.filter(pk=service.pk).exists():
            raise forms.ValidationError(f'{employee} nie wykonuje usługi „{service}”.')
        if self.cleaned_data.get('force'):
            return
        slots = get_available_slots(employee, date_time.date(), service, exclude_appointment=exclude_appointment)
        if date_time not in slots:
            raise forms.ValidationError(
                f'Termin {date_time:%d.%m.%Y %H:%M} jest niedostępny dla: {employee} '
                '(poza grafikiem, zajęty albo zablokowany).'
            )


class AppointmentCreateForm(SlotFieldsMixin, forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['service', 'employee', 'client_name', 'client_phone', 'client_email', 'notes']
        labels = {
            'service': 'Usługa',
            'employee': 'Specjalistka',
            'client_name': 'Imię i nazwisko klienta',
            'client_phone': 'Telefon',
            'client_email': 'E-mail',
            'notes': 'Uwagi',
        }
        help_texts = {
            'client_email': 'Opcjonalnie — bez e-maila klient nie dostanie potwierdzenia.',
            'notes': 'Widoczne dla klienta w mailu z potwierdzeniem.',
        }
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}

    field_order = ['service', 'employee', 'date', 'time', 'force', 'client_name', 'client_phone', 'client_email']

    def __init__(self, *args, is_owner, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_slot_fields(is_owner)
        self.current_employee = employee
        if is_owner:
            self.fields['employee'].required = False
            self.fields['employee'].empty_label = 'Pierwsza wolna specjalistka'
        else:
            # Employees always book for themselves, only services they perform
            del self.fields['employee']
            self.fields['service'].queryset = employee.services.all()

    def clean(self):
        cleaned = super().clean()
        service = cleaned.get('service')
        date_time = self.build_date_time(cleaned)
        if not service or not date_time:
            return cleaned

        employee = cleaned.get('employee') if self.is_owner else self.current_employee
        if employee is None:
            if cleaned.get('force'):
                raise forms.ValidationError('Przy pomijaniu grafiku wybierz specjalistkę.')
            employee = find_available_specialist(service, date_time)
            if employee is None:
                raise forms.ValidationError(f'Żadna specjalistka nie ma wolnego terminu {date_time:%d.%m.%Y %H:%M}.')
        else:
            self.check_slot(employee, service, date_time)

        cleaned['employee'] = employee
        cleaned['date_time'] = date_time
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.employee = self.cleaned_data['employee']
        instance.date_time = self.cleaned_data['date_time']
        instance.status = Appointment.Status.CONFIRMED
        if commit:
            instance.save()
        return instance


class RescheduleForm(SlotFieldsMixin, forms.Form):
    employee = forms.ModelChoiceField(queryset=Employee.objects.none(), label='Specjalistka')

    field_order = ['employee', 'date', 'time', 'force']

    def __init__(self, *args, appointment, is_owner, **kwargs):
        local_dt = timezone.localtime(appointment.date_time)
        # FormView always passes `initial` (empty by default), so merge instead of setdefault
        kwargs['initial'] = {
            'employee': appointment.employee,
            'date': local_dt.date(),
            'time': local_dt.time(),
            **kwargs.get('initial', {}),
        }
        super().__init__(*args, **kwargs)
        self.setup_slot_fields(is_owner)
        self.appointment = appointment
        if is_owner:
            self.fields['employee'].queryset = appointment.service.employees.all()
        else:
            del self.fields['employee']

    def clean(self):
        cleaned = super().clean()
        date_time = self.build_date_time(cleaned)
        if not date_time:
            return cleaned
        employee = cleaned.get('employee', self.appointment.employee) if self.is_owner else self.appointment.employee
        if employee is None:
            return cleaned  # field error already reported
        self.check_slot(employee, self.appointment.service, date_time, exclude_appointment=self.appointment)
        cleaned['employee'] = employee
        cleaned['date_time'] = date_time
        return cleaned


class TimeBlockForm(forms.ModelForm):
    """Blocked period (holiday, break, doctor's visit). Owners pick the employee; employees always block their own time."""

    class Meta:
        model = TimeBlock
        fields = ['employee', 'date', 'start_time', 'end_time', 'reason']
        labels = {
            'employee': 'Specjalistka',
            'date': 'Data',
            'start_time': 'Od',
            'end_time': 'Do',
            'reason': 'Powód',
        }
        help_texts = {'reason': 'Np. urlop, przerwa, lekarz — widoczne tylko w panelu.'}
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'step': 900}, format='%H:%M'),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'step': 900}, format='%H:%M'),
        }

    def __init__(self, *args, is_owner, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_owner = is_owner
        self.current_employee = employee
        if not is_owner:
            del self.fields['employee']
        add_bootstrap_classes(self)

    def clean(self):
        cleaned = super().clean()
        date, start_time, end_time = cleaned.get('date'), cleaned.get('start_time'), cleaned.get('end_time')
        # Any of these may be missing if its own field validation already failed
        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', 'Godzina zakończenia musi być późniejsza niż rozpoczęcia.')
        if date:
            today = timezone.localdate()
            if date < today:
                self.add_error('date', 'Nie można zablokować dnia z przeszłości.')
            elif date == today and start_time and start_time < timezone.localtime().time():
                self.add_error('start_time', 'Ta godzina już minęła.')
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not self.is_owner:
            instance.employee = self.current_employee
        if commit:
            instance.save()
        return instance
