from django.contrib import admin
from django.urls import  path
from taskplanner import views

urlpatterns = [
    path("base/", views.base, name="base"),
    path("", views.schedule_create, name="schedule_create"),
    path("schedule/priority/", views.schedule_priority_list, name="schedule_priority"),
    path("calendar/", views.calendar_view, name="calendar"),
    path("plan/generate/", views.plan_generate, name="plan_generate"),
    path("plan/apply/", views.plan_apply, name="plan_apply"),
    path("plan/", views.plan_task_view, name="plan_task"),
    path("plan/ai/", views.plan_ai_view, name="plan_ai"),
]