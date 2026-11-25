from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from apps.core.models import TimestampedModel


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    iso_code = models.CharField(max_length=2, unique=True, validators=[RegexValidator(r"^[A-Z]{2}$")])
    google_country_code = models.CharField(max_length=2, validators=[RegexValidator(r"^[a-z]{2}$")])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "countries"

    def save(self, *args, **kwargs):
        self.iso_code = self.iso_code.strip().upper()
        self.google_country_code = self.google_country_code.strip().lower()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Location(TimestampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="locations")
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="locations")
    region = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=150, blank=True)
    custom_name = models.CharField(max_length=200, blank=True)
    provider_location_id = models.CharField(max_length=100, blank=True)
    provider_location_name = models.CharField(max_length=250, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    language_code = models.CharField(max_length=10, default="en")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("country__name", "region", "city", "custom_name")
        constraints = [models.UniqueConstraint(fields=("owner", "country", "region", "city", "custom_name", "language_code"), name="location_owner_target_lang_uniq")]
        indexes = [models.Index(fields=("owner", "is_active"))]

    def clean(self):
        self.region = self.region.strip()
        self.city = self.city.strip()
        self.custom_name = self.custom_name.strip()
        self.language_code = self.language_code.strip().lower()
        if not any((self.region, self.city, self.custom_name)):
            from django.core.exceptions import ValidationError

            raise ValidationError("Specify a region, city, or custom location name.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.custom_name or ", ".join(filter(None, (self.city, self.region, self.country.name)))

    def __str__(self):
        return self.display_name
