from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("base/", views.base, name="base"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.schedule_create, name="schedule_create"),
    path("list/", views.schedule_list_view, name="schedule_list"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("plan/generate/", views.plan_generate, name="plan_generate"),
    path("plan/apply/", views.plan_apply, name="plan_apply"),
    path("plan/task", views.plan_task_view, name="plan_task"),
    path("plan/ai/", views.plan_ai_view, name="plan_ai"),
    path("plan/task/<int:pk>/edit/", views.plan_task_edit, name="plan_task_edit"),
    path("plan/task/<int:pk>/delete/", views.plan_task_delete, name="plan_task_delete"),
    path("plan/suggestion/<int:pk>/edit/", views.plan_suggestion_edit, name="plan_suggestion_edit"),
    path("plan/suggestion/<int:pk>/delete/", views.plan_suggestion_delete, name="plan_suggestion_delete"),
    path("schedule/<int:pk>/edit/", views.schedule_edit, name="schedule_edit"),
    path("schedule/<int:pk>/delete/", views.schedule_delete, name="schedule_delete"),
    path("settings/", views.settings_view, name="settings"),
    path("settings/", views.settings_view, name="settings"),
    path("settings/username/", views.settings_username_view, name="settings_username"),
    path("settings/email/", views.settings_email_view, name="settings_email"),
    path(
        "settings/password/",
        auth_views.PasswordChangeView.as_view(
            form_class=views.PasswordChangeFormStyled,
            template_name="saving/password_change.html",
            success_url="/settings/",
        ),
        name="password_change",
    ),
]
