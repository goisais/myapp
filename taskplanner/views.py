from .forms import ScheduleForm
from django.shortcuts import render, redirect
from .models import Schedule
from datetime import date, datetime, timedelta
from django.utils import timezone
import calendar


def calendar_view(request):
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))
    selected_day = int(request.GET.get("day", today.day))

    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month)

    # JSTで1日の開始を作る
    jst = timezone.get_current_timezone()
    start = timezone.make_aware(datetime(year, month, selected_day, 0, 0, 0), jst)
    end = start + timedelta(days=1)

    schedules = Schedule.objects.filter(
        date__gte=start,
        date__lt=end
    ).order_by("date")

    context = {
        "year": year,
        "month": month,
        "weeks": weeks,
        "selected_day": selected_day,
        "schedules": schedules,
        "today": today,
    }
    return render(request, "saving/calendar.html", context)


def schedule_priority_list(request):
    schedules = Schedule.objects.order_by("priority", "date")
    return render(request, "saving/schedule_priority.html", {"schedules": schedules})


def schedule_create(request):
    if request.method == "POST":
        form = ScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)

            minutes = int(form.cleaned_data["duration"] or 0)

            schedule.start_time = schedule.date.time()

            end_datetime = schedule.date + timedelta(minutes=minutes)
            schedule.end_time = end_datetime.time()

            schedule.save()

            return redirect(
                f"/calendar/?year={schedule.date.year}&month={schedule.date.month}&day={schedule.date.day}"
            )
    else:
        form = ScheduleForm()

    return render(request, "saving/schedule_form.html", {"form": form})


def base(request):
    return render(request, "saving/base.html")
