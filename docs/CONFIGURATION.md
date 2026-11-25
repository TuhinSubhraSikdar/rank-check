# Configuration

Settings modules: base holds common defaults, development supports local
SQLite, and production requires a long secret plus PostgreSQL and HTTPS cookies.
Environment variables are documented in ENVIRONMENT_VARIABLES.md. Users choose
light or dark appearance under Settings; the preference is stored on Profile.
The app never exposes the Serper key to browser code.
