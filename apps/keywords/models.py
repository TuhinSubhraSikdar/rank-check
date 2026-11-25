from django.db import models
from django.db.models.functions import Lower

from apps.core.models import TimestampedModel


class Keyword(TimestampedModel):
    class Intent(models.TextChoices):
        INFORMATIONAL = "INFORMATIONAL", "Informational"
        NAVIGATIONAL = "NAVIGATIONAL", "Navigational"
        COMMERCIAL = "COMMERCIAL", "Commercial"
        TRANSACTIONAL = "TRANSACTIONAL", "Transactional"

    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="keywords")
    text = models.CharField(max_length=300)
    target_url = models.URLField(max_length=500, blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    search_intent = models.CharField(max_length=20, choices=Intent.choices, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("text", "id")
        constraints = [models.UniqueConstraint(Lower("text"), "project", name="keyword_project_text_ci_uniq")]
        indexes = [models.Index(fields=("project", "is_active"))]

    def clean(self):
        self.text = " ".join(self.text.split())
        self.tags = ", ".join(dict.fromkeys(tag.strip() for tag in self.tags.split(",") if tag.strip()))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text
