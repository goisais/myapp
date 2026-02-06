from django import forms
from .models import Schedule


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = "__all__"
        new_var = "class"
        widgets = {
            "title": forms.TextInput(attrs={new_var: "input-box"}),
            "date": forms.DateTimeInput(
                attrs={"type": "datetime-local", new_var: "input-box"}
            ),
            "priority": forms.Select(attrs={new_var: "input-box"}),
            "duration": forms.TextInput(attrs={new_var: "input-box"}),
            "memo": forms.Textarea(attrs={new_var: "textarea-box"}),
        }