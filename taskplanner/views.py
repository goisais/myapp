from .forms import ScheduleForm, PlanTaskForm
from django.shortcuts import render, redirect
from .models import Schedule, PlanTask, PlanSuggestion
from datetime import date, datetime, timedelta, timezone as dt_timezone
from django.utils import timezone
from .ai_service import ai_plan_tasks
from django.contrib import messages
import json
import calendar


def plan_task_view(request):
    if request.method == "POST":
        form = PlanTaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("plan_task")
    else:
        form = PlanTaskForm()

    tasks = PlanTask.objects.order_by("-created_at")
    return render(request, "saving/plan_task.html", {"form": form, "tasks": tasks})


def plan_ai_view(request):
    tasks = PlanTask.objects.order_by("-created_at")
    suggestions = PlanSuggestion.objects.select_related("task").order_by("order")
    return render(
        request,
        "saving/plan_ai.html",
        {"tasks": tasks, "suggestions": suggestions},
    )


def plan_apply(request):
    if request.method != "POST":
        return redirect("plan_task")

    suggestions = PlanSuggestion.objects.select_related("task")

    for s in suggestions:
        Schedule.objects.create(
            title=s.task.title,
            memo=s.task.memo,
            date=s.suggested_start,
            start_time=s.suggested_start.time(),
            end_time=s.suggested_end.time(),
            priority=s.task.priority,
            duration=str(s.task.estimated_minutes or 60),
        )

    return redirect("calendar")


def plan_generate(request):
    if request.method != "POST":
        return redirect("plan_ai")

    # 既存の提案を削除
    PlanSuggestion.objects.all().delete()

    tasks = PlanTask.objects.all()

    payload = [
        {
            "id": t.id,
            "title": t.title,
            "memo": t.memo,
            "priority": t.priority,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "estimated_minutes": t.estimated_minutes,
        }
        for t in tasks
    ]

    result = None

    # ===== Gemini呼び出し（失敗したら疑似AIへ）=====
    try:
        result = ai_plan_tasks(payload)
        if not isinstance(result, list):
            raise ValueError(f"AI結果がlistではありません: {type(result)}")
    except Exception as e:
        # ここでだけ e / msg を使う（外に出さない）
        msg = str(e)

        if ("503" in msg) or ("UNAVAILABLE" in msg) or ("high demand" in msg):
            messages.error(
                request,
                "AIが混雑しています（503）。仮のルールでプランを作りました。"
            )
        else:
            messages.error(
                request,
                f"AIエラーが発生しました。仮のルールでプランを作りました。（詳細: {msg}）"
            )

    # ===== フォールバック（疑似AI）=====
    if result is None:
        tasks_sorted = sorted(
            tasks,
            key=lambda t: (
                t.priority,
                t.deadline or datetime.max.replace(tzinfo=dt_timezone.utc),
                t.estimated_minutes or 9999,
            ),
        )

        result = []
        order = 1
        for t in tasks_sorted:
            result.append(
                {
                    "id": t.id,
                    "estimated_minutes": t.estimated_minutes or 60,
                    "order": order,
                }
            )
            order += 1

    # ===== PlanSuggestion 作成（result を信頼しすぎない）=====
    base = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)

    for r in sorted(result, key=lambda x: int(x.get("order", 999999))):
        task_id = r.get("id")
        if task_id is None:
            continue

        task = PlanTask.objects.filter(id=task_id).first()
        if not task:
            continue

        est = r.get("estimated_minutes")
        try:
            minutes = int(est) if est is not None else (task.estimated_minutes or 60)
        except (TypeError, ValueError):
            minutes = task.estimated_minutes or 60

        if minutes <= 0:
            minutes = 60

        start = base
        end = start + timedelta(minutes=minutes)

        PlanSuggestion.objects.create(
            task=task,
            suggested_start=start,
            suggested_end=end,
            order=int(r.get("order", 999999)),
        )

        base = end + timedelta(minutes=30)
        
    messages.success(request, f"AIプランを {len(result)} 件生成しました。")
    return redirect("plan_ai")


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

    schedules = Schedule.objects.filter(date__gte=start, date__lt=end).order_by("date")

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

            minutes = int(form.cleaned_data.get("duration") or 0)

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
