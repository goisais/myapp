from django.db import models


class Schedule(models.Model):
    title = models.CharField(max_length=100)
    memo = models.TextField(blank=True)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return self.title
# Create your models here.
