from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from apps.accounts.roles import get_employee, is_owner


class PanelAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Owner or employee with a linked account. Logged-in users without a role get 403."""

    def dispatch(self, request, *args, **kwargs):
        self.is_owner = is_owner(request.user)
        self.employee = get_employee(request.user)
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        return self.is_owner or self.employee is not None

    def scope_to_employee(self, queryset, field='employee'):
        """Owners see everything; employees only rows where `field` points at themselves."""
        if self.is_owner:
            return queryset
        return queryset.filter(**{field: self.employee})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_owner'] = self.is_owner
        context['current_employee'] = self.employee
        return context


class OwnerRequiredMixin(PanelAccessMixin):
    def test_func(self):
        return self.is_owner
