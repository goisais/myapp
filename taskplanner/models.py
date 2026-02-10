from django.db import models


class Schedule(models.Model):
    title = models.CharField(max_length=100)
    memo = models.TextField(blank=True)
    date = models.DateTimeField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    PRIORITY_CHOICES = [
        (1, "高"),
        (2, "中"),
        (3, "低"),
    ]
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)

    duration = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.title

    def get_duration_display(self):
        if not self.duration:
            return "0分"
        text = str(self.duration)

        if "分" in text or "時間" in text:
            return text

        try:
            total = int(text)
        except ValueError:
            return text

        h = total // 60
        m = total % 60

        if h > 0:
            return f"{h}時間{m}分"
        return f"{m}分"


class PlanTask(models.Model):
    title = models.CharField(max_length=100)
    memo = models.TextField(blank=True)

    estimated_minutes = models.IntegerField(null=True, blank=True)

    PRIORITY_CHOICES = [
        (1, "高"),
        (2, "中"),
        (3, "低"),
    ]
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)

    desired_at = models.DateTimeField(null=True, blank=True)

    deadline = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class PlanSuggestion(models.Model):
    task = models.ForeignKey("PlanTask", on_delete=models.CASCADE)
    suggested_start = models.DateTimeField()
    suggested_end = models.DateTimeField()
    order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    memo = models.TextField(blank=True)
