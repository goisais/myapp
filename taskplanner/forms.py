from django import forms
from .models import Schedule


class ScheduleForm(forms.ModelForm):
    DURATION_CHOICES = [
        ("15", "15分"),
        ("30", "30分"),
        ("45", "45分"),
        ("60", "1時間"),
        ("90", "1時間30分"),
        ("120", "2時間"),
        ("other", "その他"),
    ]

    duration_choice = forms.ChoiceField(
        choices=DURATION_CHOICES,
        widget=forms.Select(attrs={"class": "input-box", "onchange": "toggleDurationInput(this)"}),
        required=False,
        label="所要時間"
    )
    duration = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "input-box", "placeholder": "例: 2時間15分", "style": "display:none;"}),
        label="所要時間(その他)"
    )

    class Meta:
        model = Schedule
        fields = [
            "title",
            "date",
            "priority",
            "duration_choice",
            "duration",
            "memo",
        ]
        new_var = "class"
        widgets = {
            "title": forms.TextInput(attrs={new_var: "input-box"}),
            "date": forms.DateTimeInput(
                attrs={"type": "datetime-local", new_var: "input-box"}
            ),
            "priority": forms.Select(attrs={new_var: "input-box"}),
            "memo": forms.Textarea(attrs={new_var: "textarea-box"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        duration_choice = cleaned_data.get("duration_choice")
        duration = cleaned_data.get("duration")
        if duration_choice == "other":
            if not duration:
                self.add_error("duration", "所要時間を入力してください")
            cleaned_data["duration"] = duration
        else:
            cleaned_data["duration"] = dict(self.DURATION_CHOICES).get(duration_choice, "")
        return cleaned_data