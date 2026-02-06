from django.db import models


class Schedule(models.Model):
    title = models.CharField(max_length=100)
    memo = models.TextField(blank=True)
    date = models.DateField()
    date = models.DateTimeField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    PRIORITY_CHOICES = [
        (1, "高"),
        (2, "中"),
        (3, "低"),
    ]
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)

    duration = models.CharField(max_length=50, blank=True)  # 例: 1時間
    memo = models.TextField(blank=True)

    def __str__(self):
        return self.title
# Create your models here.
