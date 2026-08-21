# CONTEXT — Domain & System Map

Single-context repo. Glossary below; decisions in `docs/adr/`.

## Domain glossary

| Term | Meaning |
|---|---|
| **Strategy** | A user-authored node graph (sources → filters → conditions → actions) evaluated by the strategy engine against live market data. Has versions (`version`, `version_history`) and a lifecycle: draft → active → paused → archived. |
| **Node** | One step in a strategy graph. Backend types are registered in `NodeRegistry` (risk, action, performance, palette, NASDAQ, SHAP handlers). Frontend visual types map via `nodeTypeRegistry`. |
| **Risk Manager** | Full rule-based template system over the same node primitives (not just Kelly). Rules = condition + action pairs evaluated per trade. |
| **Paper Trading** | Simulated fills against synthetic order books with honest PnL: entry debits/credits cost/proceeds, PnL realized on resolution or cancel. Kill-switch cancels a user's open orders. |
| **Safe Wallet** | Per-user internal ledger (USDC/USDT/…). No payout path exists yet — transfers are ledger entries only. |
| **Withdrawal Strategy** | Auto-withdrawal rules (profit threshold / pct steps) evaluated by `withdrawal_engine`; steps validate pct ∈ [0,100], amount ≥ 0. |
| **Research Session** | Autonomous hypothesis loop run by `ResearchScheduler`: generate hypotheses → TabPFN quick-rejection → Monte Carlo backtest → NSGA-II ranking → verdict (KEPT/WARN/REVERTED), persisted as ExperimentResults. Modes: manual, continuous, cron. |
| **RLM** | dspy.RLM deep-archive mining. Scans are confined to `RLM_ARCHIVE_ROOT` (default `./data/archives`); output is an AlphaVector stored per-user. |
| **Hermes Sidecar** | LLM chat adapter with tool-calling via `ToolRegistry`. Tool results are wrapped in `<untrusted>` tags; args validated as dicts; handlers may be async (`registry.execute`). |
| **Orchestrator** | `HermesOrchestrator` — intent classification, memory recall, skill creation, sub-agent spawning, self-correction loop. Sessions are namespaced `{user_id}:{session_id}` and bounded. |
| **Skill** | An LLM-generated node handler. Compiled under RestrictedPython safe builtins (no imports, no dunder access, AST forbid-list), smoke-tested before registration; optional containerized execution (`--network=none --read-only`). |
| **Sub-agent** | Spawned background Hermes task with the shared tool registry; cancellable via stored asyncio task handle. |
| **Alchemy** | Cross-domain connection finder over domain providers (market/news/on-chain/macro/social/legal/memory). |
| **Agentic Search** | SearXNG → Scrapling → Camoufox pipeline. Crawler rejects non-public URLs (SSRF guard). |

## Security invariants

1. Identity always comes from the JWT (`get_current_user`); client-supplied `user_id` is never trusted.
2. Every owned resource is queried with `user_id == current_user.id`; cross-tenant access returns 404.
3. Secrets fail fast at boot (`SECRET_KEY` ≥ 32 chars, `ENCRYPTION_KEY` required); exchange keys are encrypted at rest (PBKDF2-derived Fernet, versioned `v1:` ciphertext).
4. WebSockets authenticate via `?token=` and verify resource ownership before accepting messages.
5. LLM-generated code never runs with real builtins; filesystem access is confined to declared roots.

## Current state (2026-08)

- Backend: 981 tests passing. All PRD Layer 2–5 systems present and hardened.
- Frontend: tsc clean, 345 tests passing.
- Infra: compose stack builds from repo layout; monitoring wired (metrics middleware registered, alerts mounted, alertmanager + grafana provisioning present).
- Known gaps: Rust execution bridge (PRD Phase 4), copy trading, distillation engine, WhatsApp/social bots (post-v1).
