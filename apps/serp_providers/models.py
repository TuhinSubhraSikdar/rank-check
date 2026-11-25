from django.db import models


class ProviderConfiguration(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    max_requests_per_minute = models.PositiveIntegerField(default=30)
    timeout_seconds = models.PositiveSmallIntegerField(default=20)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
