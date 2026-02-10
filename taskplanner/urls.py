from django.contrib import admin
from django.urls import  path
from taskplanner import views
from . import views

urlpatterns = [
    path("base/", views.base, name="base"),
    path("", views.schedule_create, name="schedule_create"),
    path("schedule/priority/", views.schedule_priority_list, name="schedule_priority"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("plan/generate/", views.plan_generate, name="plan_generate"),
    path("plan/apply/", views.plan_apply, name="plan_apply"),
    path("plan/task", views.plan_task_view, name="plan_task"),
    path("plan/ai/", views.plan_ai_view, name="plan_ai"),
    path("plan/task/<int:pk>/edit/", views.plan_task_edit, name="plan_task_edit"),
    path("plan/task/<int:pk>/delete/", views.plan_task_delete, name="plan_task_delete"),
    path("plan/suggestion/<int:pk>/edit/", views.plan_suggestion_edit, name="plan_suggestion_edit"),
    path("plan/suggestion/<int:pk>/delete/", views.plan_suggestion_delete, name="plan_suggestion_delete"),
]