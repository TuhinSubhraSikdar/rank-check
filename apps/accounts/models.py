from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    monthly_request_quota = models.PositiveIntegerField(default=1000)

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Profile(models.Model):
    class Theme(models.TextChoices):
        LIGHT = "LIGHT", "Light"
        DARK = "DARK", "Dark"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    company_name = models.CharField(max_length=150, blank=True)
    contact_information = models.CharField(max_length=250, blank=True)
    brand_color = models.CharField(max_length=7, default="#2563EB")
    theme = models.CharField(max_length=5, choices=Theme.choices, default=Theme.LIGHT)
