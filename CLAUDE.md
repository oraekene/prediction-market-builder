When starting a new project from scratch, the first automatic step must be to create a GitHub repository: initialize git, add a .gitignore, make an initial commit, create the remote repo (via `gh repo create`), and push.

Any mention of "commit" from the user (in any phrasing) means commit local changes AND push to origin/main immediately — never hold commits locally without pushing.

## Agent skills

### Issue tracker

Issues and PRDs live as GitHub issues on `oraekene/prediction-market-builder`, via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

The five canonical roles, label strings equal to their names: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
