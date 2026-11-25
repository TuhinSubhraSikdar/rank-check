from django.core.management.base import BaseCommand

from apps.locations.models import Country

# Starter catalog; administrators may add or deactivate countries in Django admin.
COUNTRIES = (
    ("Argentina", "AR"), ("Australia", "AU"), ("Austria", "AT"),
    ("Bangladesh", "BD"), ("Belgium", "BE"), ("Brazil", "BR"),
    ("Canada", "CA"), ("China", "CN"), ("Denmark", "DK"),
    ("Finland", "FI"), ("France", "FR"), ("Germany", "DE"),
    ("Hong Kong", "HK"), ("India", "IN"), ("Indonesia", "ID"),
    ("Ireland", "IE"), ("Israel", "IL"), ("Italy", "IT"),
    ("Japan", "JP"), ("Malaysia", "MY"), ("Mexico", "MX"),
    ("Netherlands", "NL"), ("New Zealand", "NZ"), ("Nigeria", "NG"),
    ("Norway", "NO"), ("Pakistan", "PK"), ("Philippines", "PH"),
    ("Poland", "PL"), ("Portugal", "PT"), ("Saudi Arabia", "SA"),
    ("Singapore", "SG"), ("South Africa", "ZA"), ("South Korea", "KR"),
    ("Spain", "ES"), ("Sri Lanka", "LK"), ("Sweden", "SE"),
    ("Switzerland", "CH"), ("Thailand", "TH"), ("Turkey", "TR"),
    ("United Arab Emirates", "AE"), ("United Kingdom", "GB"),
    ("United States", "US"), ("Vietnam", "VN"),
)


class Command(BaseCommand):
    help = "Add the starter country catalog without changing existing entries."

    def handle(self, *args, **options):
        created = 0
        for name, code in COUNTRIES:
            _, was_created = Country.objects.get_or_create(
                iso_code=code,
                defaults={"name": name, "google_country_code": code.lower()},
            )
            created += was_created
        self.stdout.write(self.style.SUCCESS(f"Added {created} countries; {len(COUNTRIES) - created} already existed."))
