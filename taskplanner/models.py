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

        # すでに「分」や「時間」が含まれている場合はそのまま返す
        if "分" in text or "時間" in text:
            return text

        # 数字だけのときだけ計算
        try:
            total = int(text)
        except ValueError:
            return text  # 変な値でも落ちないようにする

        h = total // 60
        m = total % 60

        if h > 0:
            return f"{h}時間{m}分"
        return f"{m}分"
