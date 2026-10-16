from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('appointments/', views.AppointmentListView.as_view(), name='appointment_list'),
    path('appointments/new/', views.AppointmentCreateView.as_view(), name='appointment_create'),
    path('appointments/<int:pk>/', views.AppointmentDetailView.as_view(), name='appointment_detail'),
    path('appointments/<int:pk>/reschedule/', views.AppointmentRescheduleView.as_view(), name='appointment_reschedule'),
    path('appointments/<int:pk>/<str:action>/', views.AppointmentActionView.as_view(), name='appointment_action'),
    path('slots/', views.SlotsView.as_view(), name='slots'),
    path('time-blocks/', views.TimeBlockListView.as_view(), name='time_block_list'),
    path('time-blocks/new/', views.TimeBlockCreateView.as_view(), name='time_block_create'),
    path('time-blocks/<int:pk>/delete/', views.TimeBlockDeleteView.as_view(), name='time_block_delete'),
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('calendar/events/', views.CalendarEventsView.as_view(), name='calendar_events'),
    path('calendar/appointments/<int:pk>/move/', views.CalendarMoveView.as_view(), name='calendar_move'),
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/new/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_update'),
    path('employees/<int:pk>/toggle-active/', views.EmployeeToggleActiveView.as_view(), name='employee_toggle_active'),
    path('schedule/', views.ScheduleView.as_view(), name='schedule'),
    path('schedule/<int:employee_pk>/weekly/', views.WeeklyScheduleEditView.as_view(), name='weekly_schedule'),
    path('schedule/<int:employee_pk>/generate/', views.ScheduleGenerateView.as_view(), name='schedule_generate'),
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
