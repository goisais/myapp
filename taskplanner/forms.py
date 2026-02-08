from django import forms
from .models import Schedule
import itertools


def generate_duration_choices():
    choices = []
    for h, m in itertools.product(range(0, 24), [0, 15, 30, 45]):
        total_min = h * 60 + m
        if total_min == 0:
            continue
        label = f"{h}時間{m}分" if h > 0 else f"{m}分"
        choices.append((str(total_min), label))
    return choices


class ScheduleForm(forms.ModelForm):
    duration = forms.ChoiceField(
        choices=generate_duration_choices(),
        widget=forms.Select(attrs={"class": "input-box"}),
        required=False,
        label="所要時間",
    )

    class Meta:
        model = Schedule
        fields = ["title", "date", "priority", "duration", "memo"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "input-box"}),
            "date": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local", "class": "input-box"},
            ),
            "priority": forms.Select(attrs={"class": "input-box"}),
            "memo": forms.Textarea(attrs={"class": "textarea-box"}),
        }
