import itertools
from django import forms
from django.forms import HiddenInput
from .models import Schedule, PlanTask, PlanSuggestion
from django.utils import timezone



# =========================
# 共通：時間の選択肢
# =========================
def duration_hour_choices():
    return [(str(h), f"{h}時間") for h in range(0, 24)]


# =========================
# PlanTask（タスク追加）用：分の選択肢（未定あり）
# =========================
def duration_minute_choices_with_undecided():
    return [
        ("", "未定"),
        ("0", "0分"),
        ("1", "1分"),
        ("2", "2分"),
        ("3", "3分"),
        ("4", "4分"),
        ("5", "5分"),
        ("10", "10分"),
        ("15", "15分"),
        ("30", "30分"),
        ("45", "45分"),
    ]


# =========================
# Schedule（予定入力）用：分の選択肢（未定なし）
# ※ 必ず選ばせたいので "" を入れない
# =========================
def duration_minute_choices_no_undecided():
    return [
        ("0", "0分"),
        ("1", "1分"),
        ("2", "2分"),
        ("3", "3分"),
        ("4", "4分"),
        ("5", "5分"),
        ("10", "10分"),
        ("15", "15分"),
        ("30", "30分"),
        ("45", "45分"),
    ]


# =========================
# Schedule（予定入力）用：時間＋分（未定なし）
# duration は CharField なので「合計分を文字」で保存
# =========================
class ScheduleForm(forms.ModelForm):
    duration_hours = forms.ChoiceField(
        choices=duration_hour_choices(),
        required=True,
        label="時間",
        widget=forms.Select(attrs={"class": "input-box"}),
        initial="0",
    )

    duration_minutes = forms.ChoiceField(
        choices=duration_minute_choices_no_undecided(),
        required=True,
        label="分",
        widget=forms.Select(attrs={"class": "input-box"}),
        initial="30",  # 好きな初期値に変えてOK
    )

    # DB保存用（ユーザーには見せない）
    duration = forms.CharField(required=False, widget=HiddenInput())

    class Meta:
        model = Schedule
        fields = [
            "title",
            "date",
            "priority",
            "memo",
            "duration_hours",
            "duration_minutes",
            "duration",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input-box"}),
            "date": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "input-box"},
            ),
            "priority": forms.Select(attrs={"class": "input-box"}),
            "memo": forms.Textarea(attrs={"class": "textarea-box"}),
        }

    def clean(self):
        cleaned = super().clean()

        h = cleaned.get("duration_hours")
        m = cleaned.get("duration_minutes")

        try:
            total = int(h) * 60 + int(m)
        except (TypeError, ValueError):
            raise forms.ValidationError("所要時間を正しく選択してください。")

        # 0分を禁止したい場合はここを有効化
        if total <= 0:
            raise forms.ValidationError("所要時間は0分以外を選んでください。")

        cleaned["duration"] = str(total)
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 編集時：保存済み duration（"75" など）から hours/minutes を復元
        inst = getattr(self, "instance", None)
        if inst and getattr(inst, "duration", ""):
            text = str(inst.duration)

            # "2時間15分" のような形式が入っていたら復元できないので初期値にする
            if ("時間" in text) or ("分" in text):
                return

            try:
                total = int(text)
            except ValueError:
                return

            hh = total // 60
            mm = total % 60

            allowed = {v for v, _ in duration_minute_choices_no_undecided()}
            self.fields["duration_hours"].initial = str(hh)
            self.fields["duration_minutes"].initial = str(mm) if str(mm) in allowed else self.fields["duration_minutes"].initial


# =========================
# PlanTask（プラン設計：タスク追加）用：時間＋分（未定あり）
# estimated_minutes は IntegerField なので int/None 保存
# =========================
class PlanTaskForm(forms.ModelForm):
    duration_hours = forms.ChoiceField(
        choices=duration_hour_choices(),
        required=False,
        label="時間",
        widget=forms.Select(attrs={"class": "input-box"}),
        initial="0",
    )

    duration_minutes = forms.ChoiceField(
        choices=duration_minute_choices_with_undecided(),
        required=False,
        label="分",
        widget=forms.Select(attrs={"class": "input-box"}),
        initial="",
    )

    estimated_minutes = forms.IntegerField(required=False, widget=HiddenInput())

    class Meta:
        model = PlanTask
        fields = [
            "title",
            "desired_at",
            "deadline",
            "priority",
            "memo",
            "duration_hours",
            "duration_minutes",
            "estimated_minutes",
        ]
        labels = {
            "title": "やりたい事",
            "desired_at": "日時",
            "deadline": "締切",
            "priority": "優先度",
            "memo": "メモ",
            "duration_hours": "所要時間",
            "duration_minutes": "所要時間（分）",
            "estimated_minutes": "合計分（自動）",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "input-box"}),
            "desired_at": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "input-box"},
            ),
            "deadline": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "input-box"},
            ),
            "priority": forms.Select(attrs={"class": "input-box"}),
            "memo": forms.Textarea(attrs={"class": "textarea-box"}),
        }

    def clean(self):
        cleaned = super().clean()

        h = cleaned.get("duration_hours") or "0"
        m = cleaned.get("duration_minutes")  # "" なら未定

        if m in (None, ""):
            cleaned["estimated_minutes"] = None
            return cleaned

        try:
            total = int(h) * 60 + int(m)
        except (TypeError, ValueError):
            cleaned["estimated_minutes"] = None
            return cleaned

        cleaned["estimated_minutes"] = total if total > 0 else None
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        inst = getattr(self, "instance", None)

        if inst and getattr(inst, "desired_at", None):
            dt = timezone.localtime(inst.desired_at) if timezone.is_aware(inst.desired_at) else inst.desired_at
            self.initial["desired_at"] = dt.strftime("%Y-%m-%dT%H:%M")

        if inst and getattr(inst, "deadline", None):
            dt = timezone.localtime(inst.deadline) if timezone.is_aware(inst.deadline) else inst.deadline
            self.initial["deadline"] = dt.strftime("%Y-%m-%dT%H:%M")

        # estimated_minutes → hours/minutes復元（ここは今のままでOK）
        if inst and getattr(inst, "estimated_minutes", None):
            total = inst.estimated_minutes
            hh = total // 60
            mm = total % 60

            self.fields["duration_hours"].initial = str(hh)
            allowed = {v for v, _ in duration_minute_choices_with_undecided()}
            self.fields["duration_minutes"].initial = str(mm) if str(mm) in allowed else ""
        else:
            self.fields["duration_hours"].initial = "0"
            self.fields["duration_minutes"].initial = ""


class PlanSuggestionForm(forms.ModelForm):
    class Meta:
        model = PlanSuggestion
        fields = ["task", "suggested_start", "suggested_end", "order", "memo"]
        labels = {
            "task": "対象タスク",
            "suggested_start": "開始",
            "suggested_end": "終了",
            "order": "順番",
            "memo": "メモ",
        }
        widgets = {
            "task": forms.Select(attrs={"class": "input-box"}),
            "suggested_start": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "input-box"},
            ),
            "suggested_end": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "input-box"},
            ),
            "order": forms.NumberInput(attrs={"class": "input-box"}),
            "memo": forms.Textarea(attrs={"class": "textarea-box", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        inst = getattr(self, "instance", None)
        if inst and getattr(inst, "suggested_start", None):
            self.initial["suggested_start"] = inst.suggested_start.strftime("%Y-%m-%dT%H:%M")
        if inst and getattr(inst, "suggested_end", None):
            self.initial["suggested_end"] = inst.suggested_end.strftime("%Y-%m-%dT%H:%M")
