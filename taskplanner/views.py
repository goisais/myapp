from .forms import ScheduleForm
from django.shortcuts import render, redirect


def schedule_priority_list(request):
    schedules = Schedule.objects.order_by("priority", "date")
    return render(request, "saving/schedule_priority.html", {
        "schedules": schedules
    })


def schedule_create(request):
    if request.method == "POST":
        form = ScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('schedule_create')
    else:
        form = ScheduleForm()

    return render(request, 'saving/schedule_form.html', {'form': form})


def base(request):
    return render(request, "saving/base.html")
