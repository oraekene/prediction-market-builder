# ADRs

Architecture Decision Records. One file per decision, numbered `NNNN-short-title.md`.

Format: Status (accepted/superseded) · Context · Decision · Consequences.

Seed entries:

- `0001-single-baseline-migration.md` — replaced the broken 001–003 alembic chain with one postgres-safe baseline.
- `0002-restored-core-ai-systems.md` — Hermes orchestration, RLM, pi-autoresearch, LanceDB/DuckDB are core per the PRD; security issues are fixed in place, features are not cut.
