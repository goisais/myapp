from django import forms
from .models import Schedule


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = "__all__"
        widgets = {
            "title": forms.TextInput(attrs={"class": "input-box"}),
            "date": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "input-box"}),
            "priority": forms.Select(attrs={"class": "input-box"}),
            "duration": forms.TextInput(attrs={"class": "input-box"}),
            "memo": forms.Textarea(attrs={"class": "textarea-box"}),
        }