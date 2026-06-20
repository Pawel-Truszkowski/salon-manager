import datetime

from django import forms
from .models import Appointment


class BookingForm(forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label='Data')
    time = forms.ChoiceField(choices=[], label='Godzina')

    class Meta:
        model  = Appointment
        fields = ['service', 'employee', 'client_name', 'client_phone', 'client_email', 'date', 'time', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].required   = False
        self.fields['employee'].empty_label = 'Dowolna specjalistka'
        self.fields['client_email'].required = False

        # Jeśli formularz ma już dane (np. błąd walidacji) — zachowaj wybraną godzinę
        if self.data.get('time'):
            t = self.data['time']
            self.fields['time'].choices = [(t, t)]
        
    def clean(self):
        cleaned = super().clean()
        date = cleaned.get('date')
        time = cleaned.get('time')

        if date and time:
            try:
                # Złącz date + time w jedno datetime
                time_obj = datetime.datetime.strptime(time, '%H:%M').time()
                cleaned['date_time'] = datetime.datetime.combine(date, time_obj)
            except ValueError:
                raise forms.ValidationError('Nieprawidłowy format godziny.')

        if cleaned.get('date_time') and cleaned['date_time'] < datetime.datetime.now():
            raise forms.ValidationError('Nie można rezerwować w przeszłości.')

        return cleaned
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Przepisz złożone datetime do pola modelu
        instance.date_time = self.cleaned_data['date_time']
        if commit:
            instance.save()
        return instance