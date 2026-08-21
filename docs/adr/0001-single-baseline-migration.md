# 0001 — Single baseline migration

Status: accepted (2026-08)

## Context

The original alembic chain was broken: migration 002 altered `paper_orders` which no
migration created, ten model tables appeared in zero migrations, `create_all()` at
startup masked the drift, and `alembic revision --autogenerate` would have emitted
DROP TABLEs for live tables. Migration 003 used SQLite-only server defaults
(`server_default='1'`) that fail on PostgreSQL.

## Decision

Replace the chain with a single hand-written baseline (`0001_initial_schema`)
matching the current models exactly, postgres-safe and sqlite-compatible. Alembic is
the only schema authority; `create_all()` was removed from app startup. There was no
production database to preserve.

## Consequences

- Fresh installs run `alembic upgrade head` and get the full schema.
- Pre-existing dev SQLite files must be deleted (they were disposable).
- Future changes use normal incremental revisions; autogenerate is now safe because
  `env.py` imports every model module.
