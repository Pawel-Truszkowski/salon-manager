from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='panel/auth/login.html', redirect_authenticated_user=True),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='panel/auth/password_reset_form.html',
            email_template_name='panel/auth/password_reset_email.txt',
            html_email_template_name='panel/auth/password_reset_email.html',
            subject_template_name='panel/auth/password_reset_subject.txt',
            success_url=reverse_lazy('panel:password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/sent/',
        auth_views.PasswordResetDoneView.as_view(template_name='panel/auth/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='panel/auth/password_reset_confirm.html',
            success_url=reverse_lazy('panel:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name='panel/auth/password_reset_complete.html'),
        name='password_reset_complete',
    ),
]
