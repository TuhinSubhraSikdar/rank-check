from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import TimestampedModel
from apps.projects.models import normalize_domain


class Competitor(TimestampedModel):
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="competitors")
    name = models.CharField(max_length=150)
    domain = models.CharField(max_length=253)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(Lower("domain"), "project", name="competitor_project_domain_ci_uniq")]
        indexes = [models.Index(fields=("project", "is_active"))]

    def clean(self):
        self.name = self.name.strip()
        self.domain = normalize_domain(self.domain)
        if self.project_id and self.domain == self.project.root_domain:
            raise ValidationError("The competitor domain must differ from the project domain.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class CompetitorResult(models.Model):
    rank_check = models.ForeignKey("ranktracker.RankCheck", on_delete=models.PROTECT, related_name="competitor_results")
    competitor = models.ForeignKey(Competitor, on_delete=models.PROTECT, related_name="results")
    position = models.PositiveSmallIntegerField()
    ranking_url = models.URLField(max_length=1000)
    checked_at = models.DateTimeField()

    class Meta:
        ordering = ("-checked_at",)
        constraints = [models.UniqueConstraint(fields=("rank_check", "competitor"), name="competitor_one_result_per_check")]
        indexes = [models.Index(fields=("competitor", "checked_at"))]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Historical competitor observations are immutable.")
        super().save(*args, **kwargs)
