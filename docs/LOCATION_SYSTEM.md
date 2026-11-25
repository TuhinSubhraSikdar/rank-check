# Location System

Implemented: administrators maintain the shared Country catalog using two-letter
ISO and Google country codes. Users own Location rows containing region, city or
custom names, language, optional coordinates and reserved provider identifiers.
Run `.venv/bin/python manage.py seed_countries` after migrations to add a
starter catalog. The command is repeatable and preserves existing admin edits;
administrators can add further countries or deactivate entries in Django admin.
At least one geographical name is required. Coordinates remain metadata and are
never converted into undocumented provider request parameters.

KeywordLocation joins one active keyword to one location and device. A database
constraint prevents duplicate keyword/location/device combinations; model and
service validation reject cross-owner assignments. Requested Top 10/50/100 is
stored as user intent, while provider execution remains gated by verified actual
coverage.

The Location form can optionally select a project. Saving that choice makes the
location the project's default and assigns all active existing keywords. Manual
keyword creation and CSV import assign future keywords automatically. Project
Edit can change the default. Automatic configurations for the previous default
are archived when it changes; manually assigned configurations remain active.
Archiving a default location clears the project association and archives its
automatic configurations. Existing ranking history is preserved.
