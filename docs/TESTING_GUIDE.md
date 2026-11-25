# Testing Guide

Tests will use pytest-django fixtures and mock all Serper transport. Required coverage includes authentication, isolation, normalization, domain matching, immutable history, reporting, usage and scheduling. PostgreSQL concurrency and Docker runtime checks must be distinguished from SQLite unit tests.
