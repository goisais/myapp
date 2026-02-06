from django.contrib import admin
from django.urls import include, path
from taskplanner import views

urlpatterns = [
    path("base/", views.base, name="base"),
    path('', views.schedule_create, name='schedule_create'),
]
