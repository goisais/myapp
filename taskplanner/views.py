from .forms import ScheduleForm, PlanTaskForm, PlanSuggestionForm, UsernameChangeForm, EmailChangeForm
from django.shortcuts import render, redirect, get_object_or_404
from .models import Schedule, PlanTask, PlanSuggestion
from datetime import date, datetime, timedelta, time , timezone as dt_timezone
from django.utils import timezone
from .ai_service import ai_plan_tasks
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
import calendar


@login_required
@require_POST
def schedule_delete(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk, user=request.user)
    schedule.delete()
    return redirect("schedule_list")


@login_required
def settings_username_view(request):
    if request.method == "POST":
        form = UsernameChangeForm(request.POST)
        if form.is_valid():
            request.user.username = form.cleaned_data["username"]
            request.user.save(update_fields=["username"])
            messages.success(request, "ユーザー名を変更しました。")
            return redirect("settings")
    else:
        form = UsernameChangeForm(initial={"username": request.user.username})

    return render(request, "saving/settings_username.html", {"form": form})


@login_required
def settings_email_view(request):
    if request.method == "POST":
        form = EmailChangeForm(request.POST)
        if form.is_valid():
            request.user.email = form.cleaned_data["email"]
            request.user.save(update_fields=["email"])
            messages.success(request, "メールアドレスを変更しました。")
            return redirect("settings")
    else:
        form = EmailChangeForm(initial={"email": request.user.email})

    return render(request, "saving/settings_email.html", {"form": form})


class PasswordChangeFormStyled(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({"class": "input-box"})


@login_required
def settings_view(request):
    return render(request, "saving/settings.html")


def signup_view(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""

        if not username or not email or not password:
            messages.error(request, "全て入力してください")
            return redirect("signup")

        if User.objects.filter(username=username).exists():
            messages.error(request, "そのユーザー名は既に使われています")
            return redirect("signup")

        if User.objects.filter(email=email).exists():
            messages.error(request, "そのメールアドレスは既に使われています")
            return redirect("signup")

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "登録しました。ログインしてください。")
        return redirect("login")

    return render(request, "saving/signup.html")


def login_view(request):
    if request.method == "POST":
        login_id = (request.POST.get("login_id") or "").strip()
        password = request.POST.get("password") or ""

        if not login_id or not password:
            messages.error(request, "IDとパスワードを入力してください")
            return redirect("login")

        # メールアドレスで来た場合はusernameに変換して認証
        username = login_id
        if "@" in login_id:
            user_obj = User.objects.filter(email=login_id).first()
            if not user_obj:
                messages.error(request, "ユーザー名/メールアドレス または パスワードが違います")
                return redirect("login")
            username = user_obj.username

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "ユーザー名/メールアドレス または パスワードが違います")
            return redirect("login")

        login(request, user)
        return redirect("calendar")  # ログイン後：カレンダーへ

    return render(request, "saving/login.html")


def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def schedule_edit(request, pk):
    schedule = get_object_or_404(
        Schedule,
        pk=pk,
        user=request.user
    )

    if request.method == "POST":
        form = ScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            return redirect("schedule_list")
    else:
        form = ScheduleForm(instance=schedule)

    return render(request, "saving/schedule_edit.html", {"form": form, "schedule": schedule})


@login_required
def schedule_list_view(request):
    qs = Schedule.objects.filter(user=request.user).order_by("-date")

    q = request.GET.get("q", "").strip()
    priority = request.GET.get("priority", "").strip()
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()

    if q:
        qs = qs.filter(title__icontains=q)

    if priority:
        try:
            qs = qs.filter(priority=int(priority))
        except ValueError:
            pass

    # ✅ JSTで日付範囲を作って絞り込む（これが一番安定）
    jst = timezone.get_current_timezone()

    if date_from:
        try:
            d = datetime.strptime(date_from, "%Y-%m-%d").date()
            start_dt = timezone.make_aware(datetime.combine(d, time.min), jst)  # 00:00
            qs = qs.filter(date__gte=start_dt)
        except ValueError:
            pass

    if date_to:
        try:
            d = datetime.strptime(date_to, "%Y-%m-%d").date()
            end_dt = timezone.make_aware(datetime.combine(d + timedelta(days=1), time.min), jst)  # 翌日00:00
            qs = qs.filter(date__lt=end_dt)  # <= ではなく < にするのが安全
        except ValueError:
            pass

    return render(request, "saving/schedule_list.html", {
        "schedules": qs,
        "q": q,
        "priority": priority,
        "date_from": date_from,
        "date_to": date_to,
    })


@login_required
def plan_suggestion_edit(request, pk):
    suggestion = get_object_or_404(PlanSuggestion, pk=pk, user=request.user)

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


@login_required
@require_POST
def plan_suggestion_delete(request, pk):
    suggestion = get_object_or_404(PlanSuggestion, pk=pk, user=request.user)
    suggestion.delete()
    return redirect("plan_ai")


@login_required
def plan_task_edit(request, pk):
    task = get_object_or_404(PlanTask, pk=pk, user=request.user)

    if request.method == "POST":
        form = PlanTaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect(f"{reverse('plan_ai')}?open={task.id}")
    else:
        form = PlanTaskForm(instance=task)

    return render(request, "saving/plan_task_edit.html", {"form": form, "task": task})


@login_required
@require_POST
def plan_task_delete(request, pk):
    task = get_object_or_404(PlanTask, pk=pk, user=request.user)
    task.delete()
    return redirect(f"{reverse('plan_ai')}?open=1")


@login_required
def plan_task_view(request):
    if request.method == "POST":
        form = PlanTaskForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            return redirect("plan_task")
    else:
        form = PlanTaskForm()

    tasks = PlanTask.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "saving/plan_task.html", {"form": form, "tasks": tasks})


@login_required
def plan_ai_view(request):
    tasks = PlanTask.objects.filter(user=request.user).order_by("-created_at")
    suggestions = PlanSuggestion.objects.filter(user=request.user).order_by("order")

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


@login_required
def plan_apply(request):
    if request.method != "POST":
        return redirect("plan_task")

    suggestions = PlanSuggestion.objects.filter(user=request.user).select_related("task")

    for s in suggestions:
        Schedule.objects.create(
            user=request.user,
            title=s.task.title,
            memo=s.task.memo,
            date=s.suggested_start,
            start_time=s.suggested_start.time(),
            end_time=s.suggested_end.time(),
            priority=s.task.priority,
            duration=str(s.task.estimated_minutes or 60),
        )

    return redirect("calendar")


@login_required
@require_POST
def plan_generate(request):
    if request.method != "POST":
        return redirect("plan_ai")

    # 既存の提案を削除
    PlanSuggestion.objects.filter(user=request.user).delete()

    tasks = PlanTask.objects.filter(user=request.user)
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

    schedules = Schedule.objects.filter(
        user=request.user,
        date__gte=window_start_dt,
        date__lt=window_end_dt
    ).order_by("date")

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

        task = PlanTask.objects.filter(id=task_id, user=request.user).first()
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
            user=request.user,
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


@login_required
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
        user=request.user,
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


@login_required
def schedule_create(request):
    if request.method == "POST":
        form = ScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.user = request.user

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


@login_required
def base(request):
    return render(request, "saving/base.html")
