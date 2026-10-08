from django.utils import timezone
from django.views.generic import TemplateView

from apps.bookings.models import Appointment

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
