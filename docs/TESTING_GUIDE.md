# Testing Guide

Tests will use pytest-django fixtures and mock all Serper transport. Required coverage includes authentication, isolation, normalization, domain matching, immutable history, reporting, usage and scheduling. PostgreSQL concurrency and Docker runtime checks must be distinguished from SQLite unit tests.

Search Console tests mock service-account credential loading, refresh and
Google HTTP responses. They cover project/property boundaries, tenant scoping,
quota reservations, UI queueing, verdict mapping and private reports. No real
Google credentials or external requests are used by the test suite.
