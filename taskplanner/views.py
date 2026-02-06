from .forms import ScheduleForm
from django.shortcuts import render, redirect

from .models import Schedule

import calendar
from datetime import date, datetime, timedelta


def schedule_priority_list(request):
    schedules = Schedule.objects.order_by("priority", "date")
    return render(request, "saving/schedule_priority.html", {"schedules": schedules})


def schedule_create(request):
    if request.method == "POST":
        form = ScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)

            # 開始時間
            schedule.start_time = schedule.date

            # POSTから取得
            minutes = request.POST.get("duration_choice")

            if not minutes:
                minutes = request.POST.get("duration", 0)

            minutes = int(minutes)

            # 終了時間
            schedule.end_time = schedule.start_time + timedelta(minutes=minutes)

            schedule.save()
            return redirect("schedule_create")
    else:
        form = ScheduleForm()

    return render(request, "saving/schedule_form.html", {"form": form})
# def schedule_create(request):
#     if request.method == "POST":
#         form = ScheduleForm(request.POST)
#         if form.is_valid():
#             schedule = form.save(commit=False)
#             schedule.start_time = schedule.date
#             schedule.save()
#             return redirect("schedule_create")
#     else:
#         form = ScheduleForm()

#     return render(request, "saving/schedule_form.html", {"form": form})


def base(request):
    return render(request, "saving/base.html")


# カレンダー画面ビュー
def calendar_view(request):
    today = date.today()
    year = request.GET.get("year", today.year)
    month = request.GET.get("month", today.month)
    try:
        year = int(year)
        month = int(month)
    except ValueError:
        year = today.year
        month = today.month

    cal = calendar.Calendar()
    month_days = list(cal.itermonthdays(year, month))
    month_days = month_days[:35]  # 5週分だけ使う場合
    weeks = [month_days[i : i + 7] for i in range(0, len(month_days), 7)]

    # 選択日
    selected_day = request.GET.get("day", today.day)
    try:
        selected_day = int(selected_day)
    except ValueError:
        selected_day = today.day

    # 選択日の予定（DateTimeField対応）
    try:
        selected_date = datetime(year, month, selected_day).date()
        schedules = Schedule.objects.filter(date__date=selected_date)
    except Exception:
        schedules = Schedule.objects.none()

    context = {
        "year": year,
        "month": month,
        "weeks": weeks,
        "selected_day": selected_day,
        "schedules": schedules,
        "today": today,
    }
    return render(request, "saving/calendar.html", context)
