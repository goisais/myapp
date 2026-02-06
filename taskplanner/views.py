from django.http import HttpResponse
from django.shortcuts import render


def base(request):
    return render(request, "base.html")


def home(request):
    return render(request, "home.html")