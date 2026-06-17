from django.db import models

from apps.core.models import TimeStampedModel


class Customer(TimeStampedModel):
    name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["name", "phone", "id"]

    def __str__(self) -> str:
        return self.name or "Walk-in"
