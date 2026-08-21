# 0002 — Core AI systems are kept and hardened, not cut

Status: accepted (2026-08)

## Context

A security teardown found RCE (LLM code exec'd with full builtins), arbitrary file
read (RLM scans), path traversal (git_manager), broken tool-calling, and uncancellable
sub-agents. An initial remediation pass deleted these systems wholesale. The PRD
defines them as core: Hermes-Agent orchestration (Layer 2), RLM + pi-autoresearch
(Layer 3), LanceDB/DuckDB (Layer 5).

## Decision

Restore every removed system and fix the security issues in place, borrowing
isolation patterns from NousResearch/hermes-agent (container backends, restricted
execution, approval boundaries):

- Skill creation: RestrictedPython safe builtins + AST forbid-list + smoke test;
  container path runs `--network=none --read-only --user 65534`.
- RLM: all scan paths confined to `RLM_ARCHIVE_ROOT`; source hashes cover contents.
- git_manager: skill names validated `^[A-Za-z0-9_]{1,64}$`, paths resolved inside
  the skills dir; commit hashes validated.
- agent_spawner: stores asyncio task handles; terminate cancels for real; spawned
  agents get the shared tool registry.
- orchestrator: sessions namespaced per user and bounded; async tool execution.

## Consequences

- The full PRD Layer 2/3 surface is available again with defense-in-depth.
- RestrictedPython is a convenience boundary, not a sandbox guarantee; the
  containerized skill path remains the strong isolation tier.
