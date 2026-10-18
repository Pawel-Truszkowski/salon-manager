import datetime
import itertools
from collections import defaultdict

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.bookings.models import Appointment
from apps.bookings.utils import find_available_specialist, get_available_slots
from apps.services.models import Employee, Equipment, EquipmentRental, Service, TimeBlock, WeeklyScheduleEntry

FORCE_HELP = 'Pozwala zapisać wizytę poza grafikiem lub na zajęty termin. Używaj świadomie.'


def add_bootstrap_classes(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
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
        self.fields['service'].queryset = Service.objects.active()
        if is_owner:
            self.fields['employee'].queryset = Employee.objects.active()
            self.fields['employee'].required = False
            self.fields['employee'].empty_label = 'Pierwsza wolna specjalistka'
        else:
            # Employees always book for themselves, only services they perform
            del self.fields['employee']
            self.fields['service'].queryset = employee.services.active()

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
            self.fields['employee'].queryset = appointment.service.employees.active()
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
        if is_owner:
            self.fields['employee'].queryset = Employee.objects.active()
        else:
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


class WeeklyScheduleEntryForm(forms.ModelForm):
    """One row of the weekly template editor; start < end is checked by `WeeklyScheduleEntry.clean()`."""

    class Meta:
        model = WeeklyScheduleEntry
        fields = ['weekday', 'start_time', 'end_time']
        labels = {'weekday': 'Dzień', 'start_time': 'Od', 'end_time': 'Do'}
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time', 'step': 900}, format='%H:%M'),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'step': 900}, format='%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class BaseWeeklyScheduleFormSet(forms.BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        # DELETE is added by the formset after the form's __init__, so style it here
        if 'DELETE' in form.fields:
            form.fields['DELETE'].label = 'Usuń'
            form.fields['DELETE'].widget.attrs['class'] = 'form-check-input'

    def clean(self):
        super().clean()
        blocks_by_day = defaultdict(list)
        for form in self.forms:
            # Invalid rows already show their own errors (and may lack fields); empty extra rows and deleted ones don't count
            if not form.is_valid() or not form.has_changed() or form in self.deleted_forms:
                continue
            data = form.cleaned_data
            blocks_by_day[data['weekday']].append((data['start_time'], data['end_time']))

        # Touching blocks (9-13 + 13-17) are fine; only a real overlap is an error
        errors = []
        for weekday, blocks in sorted(blocks_by_day.items()):
            blocks.sort()
            for (prev_start, prev_end), (next_start, next_end) in itertools.pairwise(blocks):
                if prev_end > next_start:
                    errors.append(
                        f'Bloki w dniu {WeeklyScheduleEntry.WeekDay(weekday).label} nachodzą na siebie: '
                        f'{prev_start:%H:%M}–{prev_end:%H:%M} i {next_start:%H:%M}–{next_end:%H:%M}.'
                    )
        if errors:
            raise forms.ValidationError(errors)


WeeklyScheduleFormSet = forms.inlineformset_factory(
    Employee,
    WeeklyScheduleEntry,
    form=WeeklyScheduleEntryForm,
    formset=BaseWeeklyScheduleFormSet,
    extra=1,
    can_delete=True,
)


class GenerateScheduleForm(forms.Form):
    """Date range for `generate_schedules()`."""

    MAX_DAYS = 183  # ~6 months: the template may change, so don't materialize too far ahead

    date_from = forms.DateField(label='Od', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    date_to = forms.DateField(label='Do', widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

    def clean(self):
        cleaned = super().clean()
        date_from, date_to = cleaned.get('date_from'), cleaned.get('date_to')
        if date_from is None or date_to is None:
            return cleaned  # field errors already reported

        if date_from < timezone.localdate():
            self.add_error('date_from', 'Nie można generować grafiku w przeszłości.')
        if date_from > date_to:
            self.add_error('date_to', 'Data końcowa nie może być wcześniejsza niż początkowa.')
        elif (date_to - date_from).days + 1 > self.MAX_DAYS:  # both ends inclusive
            self.add_error('date_to', f'Grafik można wygenerować najwyżej na {self.MAX_DAYS} dni naraz.')
        return cleaned


class EmployeeForm(forms.ModelForm):
    """Owner adds/edits a specialist: public name, bio and which services she performs."""

    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'bio', 'services']
        labels = {
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
            'bio': 'O specjalistce',
            'services': 'Usługi',
        }
        help_texts = {
            'bio': 'Opcjonalnie — krótki opis specjalistki.',
            'services': 'Wybierz wszystkie usługi, które wykonuje specjalistka.',
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
            'services': forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bio'].required = False
        add_bootstrap_classes(self)


class InviteEmployeeForm(forms.Form):
    """E-mail for the specialist's new panel account; it also becomes her login."""

    email = forms.EmailField(
        label='E-mail',
        help_text='Na ten adres wyślemy link do ustawienia hasła. Będzie też loginem do panelu.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)

    def clean_email(self):
        # It becomes the login too, so store one canonical form: people don't think of e-mails as case-sensitive
        email = self.cleaned_data['email'].lower()
        User = get_user_model()
        # `User.email` isn't unique in Django and `username` is (and equals the e-mail for invited accounts): check both
        if User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            # Don't say whose account it is (owner, another specialist, later maybe a client)
            raise forms.ValidationError('Konto z tym adresem już istnieje.')
        return email


class ServiceForm(forms.ModelForm):
    """Owner adds/edits a service offered on the website."""

    class Meta:
        model = Service
        fields = ['category', 'name', 'description', 'price', 'duration', 'required_equipment']
        labels = {
            'category': 'Kategoria',
            'name': 'Nazwa',
            'description': 'Opis',
            'price': 'Cena (zł)',
            'duration': 'Czas trwania (min)',
            'required_equipment': 'Wymaga urządzenia',
        }
        help_texts = {
            'required_equipment': 'Wtedy usługę można zarezerwować tylko w dni, w które urządzenie jest w salonie '
            '(Urządzenia → terminy).',
            'description': 'Widoczny na stronie w zakładce usług.',
            'price': 'Zmiana dotyczy też już zapisanych wizyt (szczegóły wizyty pokazują aktualną cenę).',
            'duration': 'Zmiana dotyczy też już zapisanych wizyt: zmieni się ich długość w kalendarzu i dostępność.',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'price': forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'duration': forms.NumberInput(attrs={'min': 15, 'step': 15}),
        }

    MAX_DURATION = 8 * 60  # longer than a working day makes no sense

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].empty_label = None  # every service belongs to a category tab on the website
        self.fields['required_equipment'].empty_label = 'Nie, zawsze dostępna'
        add_bootstrap_classes(self)

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError('Cena nie może być ujemna.')
        return price

    def clean_duration(self):
        duration = self.cleaned_data['duration']
        if duration <= 0:
            raise forms.ValidationError('Czas trwania musi być dłuższy niż 0 minut.')
        if duration > self.MAX_DURATION:
            raise forms.ValidationError(f'Czas trwania może wynosić najwyżej {self.MAX_DURATION // 60} godzin.')
        # Bookings start every 15 min (`get_available_slots`); other lengths leave unbookable gaps, e.g. 50 min
        # ends at :50 and the next free start is :00 -> 10 min lost after every such appointment
        if duration % 15:
            raise forms.ValidationError('Czas trwania musi być wielokrotnością 15 minut (np. 45, 60, 90).')
        return duration


class EquipmentForm(forms.ModelForm):
    """Owner adds/edits a device that comes and goes, e.g. the rented laser."""

    class Meta:
        model = Equipment
        fields = ['name', 'description', 'is_active']
        labels = {'name': 'Nazwa', 'description': 'Opis', 'is_active': 'W użyciu'}
        help_texts = {
            'description': 'Widoczny na stronie przy usługach, które wymagają tego urządzenia.',
            'is_active': 'Odznacz, gdy salon przestaje z niego korzystać: jego usług nie da się wtedy zarezerwować.',
        }
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_bootstrap_classes(self)


class EquipmentRentalForm(forms.ModelForm):
    """The days a device is in the salon. Both ends inclusive; one-day rental = the same date twice."""

    class Meta:
        model = EquipmentRental
        fields = ['date_from', 'date_to']
        labels = {'date_from': 'Od', 'date_to': 'Do (włącznie)'}
        widgets = {
            'date_from': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'date_to': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, equipment, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.equipment = equipment
        add_bootstrap_classes(self)

    def clean(self):
        cleaned = super().clean()  # also runs EquipmentRental.clean(): date_from <= date_to
        date_from, date_to = cleaned.get('date_from'), cleaned.get('date_to')
        if not (date_from and date_to):
            return cleaned
        if date_to < timezone.localdate():
            self.add_error('date_to', 'Ten termin już minął.')
        overlapping = (
            EquipmentRental.objects.filter(equipment=self.instance.equipment)
            .filter(date_from__lte=date_to, date_to__gte=date_from)
            .exclude(pk=self.instance.pk)
            .first()
        )
        if overlapping:
            raise forms.ValidationError(
                f'Ten termin nachodzi na już zapisany: {overlapping.date_from:%d.%m}–{overlapping.date_to:%d.%m.%Y}.'
            )
        return cleaned
