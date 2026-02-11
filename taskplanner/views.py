from .forms import ScheduleForm, PlanTaskForm, PlanSuggestionForm
from django.shortcuts import render, redirect, get_object_or_404
from .models import Schedule, PlanTask, PlanSuggestion
from datetime import date, datetime, timedelta, timezone as dt_timezone
from django.utils import timezone
from .ai_service import ai_plan_tasks
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from django.urls import reverse
import calendar


def schedule_edit(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)

    if request.method == "POST":
        form = ScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            return redirect("schedule_list")
    else:
        form = ScheduleForm(instance=schedule)

    return render(request, "saving/schedule_edit.html", {"form": form, "schedule": schedule})


def schedule_list_view(request):
    qs = Schedule.objects.all().order_by("-date")

    # --- GETパラメータ取得 ---
    q = request.GET.get("q", "").strip()               # タイトル検索
    priority = request.GET.get("priority", "").strip() # 優先度
    date_from = request.GET.get("from", "").strip()    # 開始日
    date_to = request.GET.get("to", "").strip()        # 終了日

    # --- 絞り込み ---
    if q:
        qs = qs.filter(title__icontains=q)

    if priority:
        # priorityはIntegerField想定（"1","2","3"が来る）
        try:
            qs = qs.filter(priority=int(priority))
        except ValueError:
            pass

    if date_from:
        # "YYYY-MM-DD" を DateTimeField に当てるなら __date が簡単
        qs = qs.filter(date__date__gte=date_from)

    if date_to:
        qs = qs.filter(date__date__lte=date_to)

    context = {
        "schedules": qs,
        "q": q,
        "priority": priority,
        "date_from": date_from,
        "date_to": date_to,
    }
    return render(request, "saving/schedule_list.html", context)


def plan_suggestion_edit(request, pk):
    suggestion = get_object_or_404(PlanSuggestion, pk=pk)

    if request.method == "POST":
        form = PlanSuggestionForm(request.POST, instance=suggestion)
        if form.is_valid():
            form.save()
            return redirect("plan_ai")
    else:
        form = PlanSuggestionForm(instance=suggestion)

    return render(
        request,
        "saving/plan_suggestion_edit.html",
        {"form": form, "suggestion": suggestion},
    )


@require_POST
def plan_suggestion_delete(request, pk):
    suggestion = get_object_or_404(PlanSuggestion, pk=pk)
    suggestion.delete()
    return redirect("plan_ai")


def plan_task_edit(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)

    if request.method == "POST":
        form = PlanTaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('plan_ai')}?open={task.id}")
    else:
        form = PlanTaskForm(instance=task)

    return render(request, "saving/plan_task_edit.html", {"form": form, "task": task})


@require_POST
def plan_task_delete(request, pk):
    task = get_object_or_404(PlanTask, pk=pk)
    task.delete()
    return redirect(f"{reverse('plan_ai')}?open=1")


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

    open_id = request.GET.get("open")

    return render(
        request,
        "saving/plan_ai.html",
        {
            "tasks": tasks,
            "suggestions": suggestions,
            "open_id": open_id,
        },
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
    if not tasks.exists():
        messages.info(request, "タスクが無いのでプランを作れませんでした。")
        return redirect("plan_ai")

    payload = [
        {
            "id": t.id,
            "title": t.title,
            "memo": t.memo,

            "priority": t.priority,
            "priority_locked": True,  

            "deadline": t.deadline.isoformat() if t.deadline else None,

            "desired_at": t.desired_at.isoformat() if t.desired_at else None,
            "desired_at_locked": bool(t.desired_at), 

            "estimated_minutes": t.estimated_minutes,
            "estimated_minutes_locked": bool(t.estimated_minutes), 
        }
        for t in tasks
    ]

    # ===== AIに渡す「既存予定」「期間」「作業可能時間」 =====
    jst = timezone.get_current_timezone()
    window_start_dt = timezone.now().astimezone(jst).replace(hour=9, minute=0, second=0, microsecond=0)
    window_end_dt = window_start_dt + timedelta(days=14)

    schedules = Schedule.objects.filter(date__gte=window_start_dt, date__lt=window_end_dt).order_by("date")

    existing_events = []
    for s in schedules:
        start_dt = s.date.astimezone(jst)

        if s.end_time:
            end_dt = timezone.make_aware(datetime.combine(start_dt.date(), s.end_time), jst)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
        else:
            try:
                m = int(s.duration) if s.duration else 60
            except ValueError:
                m = 60
            end_dt = start_dt + timedelta(minutes=m)

        existing_events.append(
            {"title": s.title, "start": start_dt.isoformat(), "end": end_dt.isoformat()}
        )

    availability = {
        "timezone": "Asia/Tokyo",
        "weekday": [{"start": "18:00", "end": "23:00"}],
        "weekend": [{"start": "10:00", "end": "22:00"}],
        "slot_minutes": 15,
    }

    window_start = window_start_dt.isoformat()
    window_end = window_end_dt.isoformat()
    # ===== ここまで =====

    result = None
    used_fallback = False

    # ===== Gemini呼び出し =====
    try:
        result = ai_plan_tasks(payload, existing_events, availability, window_start, window_end)
        if not isinstance(result, list):
            raise ValueError(f"AI結果がlistではありません: {type(result)}")
    except Exception as e:
        used_fallback = True
        msg = str(e)

        # メッセージはここで出す（成功時には出さない）
        if ("503" in msg) or ("UNAVAILABLE" in msg) or ("high demand" in msg):
            messages.error(request, "AIが混雑しています（503）。仮のルールでプランを作りました。")
        else:
            messages.error(request, f"AIエラーが発生しました。仮のルールでプランを作りました。（詳細: {msg}）")

    # ===== フォールバック（疑似AI）=====
    if result is None:
        used_fallback = True
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
            result.append({"id": t.id, "estimated_minutes": t.estimated_minutes or 60, "order": order})
            order += 1

    # ===== PlanSuggestion 作成 =====
    base = window_start_dt
    created_count = 0  # ★実際に作れた件数
    skipped_count = 0  # ★スキップした件数（デバッグに便利）

    for r in sorted(result, key=lambda x: int(x.get("order", 999999))):
        task_id = r.get("id")
        if task_id is None:
            skipped_count += 1
            continue

        task = PlanTask.objects.filter(id=task_id).first()
        if not task:
            skipped_count += 1
            continue

        # ---- AIが返した日時を使う（あれば） ----
        start_at = r.get("start_at")
        end_at = r.get("end_at")

        start = end = None
        minutes = None

        if start_at and end_at:
            sdt = parse_datetime(start_at)
            edt = parse_datetime(end_at)

            if sdt and timezone.is_naive(sdt):
                sdt = timezone.make_aware(sdt, timezone.get_current_timezone())
            if edt and timezone.is_naive(edt):
                edt = timezone.make_aware(edt, timezone.get_current_timezone())

            if sdt and edt and edt > sdt:
                start, end = sdt, edt
                minutes = int((end - start).total_seconds() // 60)

        # ---- AI日時が無い/壊れている場合：仮詰め ----
        if not (start and end):
            est = r.get("estimated_minutes")
            try:
                minutes = int(est) if est is not None else (task.estimated_minutes or 60)
            except (TypeError, ValueError):
                minutes = task.estimated_minutes or 60

            if minutes <= 0:
                minutes = 60

            start = base
            end = start + timedelta(minutes=minutes)
            base = end + timedelta(minutes=30)

        # 所要時間をタスクに保存（未設定のときだけ）
        if task.estimated_minutes is None and minutes is not None:
            task.estimated_minutes = minutes
            task.save(update_fields=["estimated_minutes"])

        # 優先度をAIが返してきたら反映（1〜3のみ）
        p = r.get("priority")
        if p in (1, 2, 3) and task.priority != p:
            task.priority = p
            task.save(update_fields=["priority"])

        # order を安全に決める（AIがorder返さない場合に備える）
        try:
            order_val = int(r.get("order", 999999))
        except (TypeError, ValueError):
            order_val = 999999

        PlanSuggestion.objects.create(
            task=task,
            suggested_start=start,
            suggested_end=end,
            order=order_val,
        )
        created_count += 1

    # ===== メッセージ：ここが一番重要 =====
    if created_count == 0:
        # resultはあるのに保存できてないパターンを確実に拾う
        messages.error(request, "プランを作れませんでした（AI出力が不正か、タスクIDが一致していません）。")
    else:
        if used_fallback:
            messages.info(request, f"仮ルールでプランを {created_count} 件生成しました。")
        else:
            messages.success(request, f"AIプランを {created_count} 件生成しました。")

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
