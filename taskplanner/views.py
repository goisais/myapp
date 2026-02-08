from .forms import ScheduleForm, PlanTaskForm
from django.shortcuts import render, redirect
from .models import Schedule, PlanTask
from datetime import date, datetime, timedelta
from django.utils import timezone
import calendar


def plan_design_view(request):
    if request.method == "POST":
        form = PlanTaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("plan_design")
    else:
        form = PlanTaskForm()

    tasks = PlanTask.objects.order_by("-created_at")

    return render(
        request,
        "saving/plan_design.html",
        {
            "form": form,
            "tasks": tasks,
        },
    )


def calendar_view(request):
    today = date.today()

    # GET取得（不正値対策）
    try:
        year = int(request.GET.get("year", today.year))
    except (TypeError, ValueError):
        year = today.year

    try:
        month = int(request.GET.get("month", today.month))
    except (TypeError, ValueError):
        month = today.month

    try:
        selected_day = int(request.GET.get("day", today.day))
    except (TypeError, ValueError):
        selected_day = today.day

    # month を 1..12 に補正（13や0を吸収）
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1

    # 選択日をその月の最大日に丸める（例: 2/31 対策）
    last_day = calendar.monthrange(year, month)[1]
    if selected_day < 1:
        selected_day = 1
    elif selected_day > last_day:
        selected_day = last_day

    cal = calendar.Calendar(firstweekday=6)
    weeks = cal.monthdayscalendar(year, month)

    # 前月/次月（テンプレ用）
    prev_year, prev_month = year, month - 1
    next_year, next_month = year, month + 1
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    if next_month == 13:
        next_month = 1
        next_year += 1

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
        "prev_year": prev_year,
        "prev_month": prev_month,
        "next_year": next_year,
        "next_month": next_month,
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
