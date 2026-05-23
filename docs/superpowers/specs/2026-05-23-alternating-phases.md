# Alternating Phases: N+1 GP Conflict Resolution & Mode Orchestration

## 1. The N+1 GP Problem

When both meta-strategy (population of strategies) and individual strategy (population of hypotheses) genetic programming run concurrently, there are N+1 concurrent evolutionary processes:

- 1 meta-GP evolving the strategy pool
- N individual GPs (one per strategy) evolving hypothesis populations

These conflict across 9 categories (28 total conflicts identified):

| Category | Conflicts | Core Issue |
|----------|-----------|------------|
| Non-stationary fitness | 4 | Individual GP landscape shifts as meta-GP swaps strategies in/out |
| Circular dependencies | 3 | Meta-GP scores strategies whose hypotheses were built for different meta-context |
| Mode collapse | 3 | Both GPs converge on same narrow solution space |
| Timing/staleness | 4 | Phase misalignment produces stale evaluations |
| Resources | 3 | LLM calls, TabPFN, compute budget contention |
| GP population | 3 | Population sizes conflate strategy vs hypothesis diversity |
| Objective misalignment | 3 | Meta maximizes pool diversity; individual maximizes Sharpe |
| Data | 3 | Rolling windows differ between GP layers |
| Resource allocation feedback | 2 | Both GPs fight for compute, creating oscillating quality cycles |

### Mitigation Status

- **25/28 conflicts fully mitigable** via Scenario 2S (staggered phase alternation) + per-conflict mitigations
- **3 inherent limitations** (cannot fully solve):
  1. **Credit assignment**: Hard to attribute performance to meta vs individual GP changes
  2. **Diversification/performance trade-off**: Meta wants diversity, individual wants peak Sharpe — these pull against each other
  3. **Cross-strategy crossover**: No mechanism for hypotheses to recombine across strategies (not necessarily desirable, but a limitation)

## 2. Scenario 2S: Staggered Phase Alternation

The core architecture: **three alternating phases, never concurrent GP runs.**

```
Timeline:  Phase A  |  Phase B  |  Phase C  |  Phase A  |  Phase B  |  Phase C  |  ...
           <-------> <---------> <---------> <--------->
           ~15-30min  ~5-10min   immediate   repeat
```

### Phase A: Individual GP (Hypothesis Evolution)

**GP active:** Individual strategy GPs only. Meta-GP frozen.

- Each strategy runs its own genetic programming loop for K generations (default 10)
- Strategy pool is FROZEN — no strategies enter or leave
- Meta-strategy catalog hypotheses are used as seeding material, not evolved
- TabPFN cache is warm (shared across strategies within same cycle)
- LLM calls capped per cycle (configurable, default 5 per strategy)
- Convergence check at end: if ALL strategies meet convergence criteria, can skip to Phase C early

```
resources_per_cycle:
  llm_calls: min(5, max(1, floor(budget / N)))
  tabpfn_calls: per_generation * K
  generations: 10
```

### Phase B: Meta-GP (Strategy Pool Evolution)

**GP active:** Meta-GP only. Individual strategy GPs frozen.

- Meta-GP evaluates the frozen strategy pool from Phase A
- Scores each strategy using the frozen hypothesis populations
- Runs selection, crossover, mutation on the meta-population
- Strategy pool may change (add/remove strategies)
- Individual hypothesis populations tagged with the meta-context version they were evolved under
- Maximum 1-2 meta-generations per Phase B (quick evaluation, not full evolution)

```
meta_generations_per_cycle: 1-2
evaluation_snapshot: "meta_context_v{TIMESTAMP}"
```

### Phase C: Pool Update & Template Extraction

**No GP active.** Housekeeping phase.

- If meta-GP added new strategies: initialize them with base hypothesis populations
- If meta-GP removed strategies: archive their hypothesis populations (don't discard — may return)
- Extract new templates from KEPT hypotheses (cosine similarity > 0.85 dedup)
- Update strategy weights if meta-GP changed scoring
- Update convergence metrics for orchestration

## 3. Phase Alternation Scheduling

### Default Cycle

```
Phase A: Individual GP    15-30 min  (10 generations)
Phase B: Meta-GP           5-10 min  (1-2 generations)
Phase C: Update            <1 min

Total cycle: ~20-40 minutes
Cycles per day: ~36-72
```

### Dynamic Adjustment

Cycle durations adjust based on:
- **Strategy count**: N strategies amplify Phase A proportionally
- **Hypothesis convergence rate**: Fast convergence = shorter Phase A
- **Meta-GP stagnation**: No meta-improvement in 5+ cycles = enter maintenance mode (Phase A only)
- **LLM budget remaining**: Stretch or compress Phase A

```
phase_a_duration = base_duration * (1 + 0.1 * (N - 1))
  where base_duration = max(10, min(30, k_generations * generation_time))

phase_b_duration = base_meta * (1 + 0.05 * pool_changes)
  where base_meta = max(5, min(10, meta_generations * meta_generation_time))
```

### Resource Model

At most `max(N, 1)` concurrent research loops, not N+1:
- Phase A: N concurrent individual GP loops
- Phase B: 1 meta-GP loop
- Phase C: 1 update process

## 4. Mode Orchestration State Machine

The three hypothesis modes (from the template taxonomy) interact with the phase alternation:

```
                    CONSTRAINED_ALL
                    (fixed templates, no new)
                          |
                  plateau detected?
                 /                  \
               yes                  no
               /                      \
     UNCONSTRAINED               CONSTRAINED_ALL
   (any template, new OK)        (stay)

          |  plateau
          |  or template
          |  collapse
          v
     CONSTRAINED_ALL
   (re-stabilize with
    best templates)

          |
   user says "focus on X"
          |
          v
   CONSTRAINED_SELECTED
   (lock to domain, never
    auto-exit without
    user confirmation)
```

### Transition Rules

| From | To | Trigger | Cooldown |
|------|----|---------|----------|
| CONSTRAINED_ALL | UNCONSTRAINED | Score plateau (no improvement in 5 gen) OR template collapse (<3 active templates) | 5 generations |
| UNCONSTRAINED | CONSTRAINED_ALL | Score plateau OR template count stabilizes (no new templates for 10 gen) | 5 generations |
| CONSTRAINED_SELECTED | (none automatically) | Only on user command | N/A |

### Cooldown & Safeguards

- **5-generation cooldown** between any mode switch
- **Trial quota**: 10 generations before UNCONSTRAINED can suggest abandoning a new template
- **Hard cap**: `max(1, floor(N/3))` strategies can be in UNCONSTRAINED simultaneously
- **Oscillation prevention**: If mode oscillates 3+ times in 24 hours, lock to CONSTRAINED_ALL for 48 hours

## 5. Convergence Metrics

Mode orchestration decisions driven by:

```python
class ConvergenceMetrics:
    score_plateau: bool  # No significant score movement in N generations
    template_collapse: bool  # Active template count dropping
    variance_collapse: bool  # Hypothesis population diversity shrinking
    meta_stagnation: bool  # Meta-GP not improving pool quality
```

### Plateau Detection

```
score_plateau = true when:
  rolling_window(5).score_improvement < 0.01
  AND rolling_window(10).score_improvement < 0.02
  AND at least 10 generations have elapsed

template_collapse = true when:
  active_template_count < 3
  AND at least 5 generations since last template extraction
```

## 6. User Direction Override

`program_prompt` (from `program.md`) overrides ALL orchestration decisions:

| Prompt | Effect |
|--------|--------|
| "focus on momentum" | Locks CONSTRAINED_SELECTED with momentum templates. Blocks UNCONSTRAINED. Raises plateau threshold. |
| "try anything" | Unlocks UNCONSTRAINED. Lowers plateau threshold. Temporarily raises hard cap. |
| "don't change modes" | Freezes current mode. Only transitions on user command. |
| (empty/null) | Full autonomous orchestration. |

Priority: `program_prompt > orchestration_metrics > default_settings`

## 7. Constraint Cost Reporting

Every mode switch logs metrics before and after, so the user sees the trade-off:

```
[Orchestration] Switched from CONSTRAINED_ALL to UNCONSTRAINED (gen 42)
  Before: Sharpe 0.72, templates 5, diversity 0.31
  After (gen 52): Sharpe 0.85, templates 12, diversity 0.52
  Cost of constraint: +0.13 Sharpe, +7 templates

...

[Orchestration] Switched from CONSTRAINED_SELECTED to CONSTRAINED_ALL (user: "focus on momentum")
  Constraint cost estimation:
    Momentum-only achieved: Sharpe 0.68, templates 3
    Estimated unconstrained baseline: ~0.97 Sharpe (from historical gen 15-25)
    Estimated constraint cost: ~0.29 Sharpe
```

## 8. Template Extraction Protocol (Phase C)

When Phase C runs, new templates may be extracted from KEPT hypotheses:

```
Phase C:
  for each strategy:
    for each KEPT hypothesis since last Phase C:
      canonical = canonicalize(hypothesis.entry)  # Normalize: (feature, operator) -> canonical template key
      if cosine_similarity(canonical, existing_templates) > 0.85:
        merge: update template metadata with new observation
      else:
        candidate = llm_extract_template(hypothesis)
        if validate_template(candidate):
          insert into template_pool
          if pool_size > 200: evict_lru()
```

### Template Validation

A candidate template must satisfy:
- Has at least one concrete example hypothesis
- Is not a duplicate of existing templates (cosine < 0.85)
- Can be expressed as {feature, operator, threshold} tuple
- Has a human-readable name
- (Optional) Has LLM-generated description

### Pool Size Management

Soft cap at 200 templates. LRU eviction when exceeded. Templates with high KEPT rates excluded from eviction.

## 9. Phase C Integration with Artifact Marketplace

When templates are extracted in Phase C, the artifact system tracks them:

- New templates create `TemplateArtifact` records (or equivalent)
- Templates derived from KEPT hypotheses carry `source_iteration` reference
- User-winning templates can be flagged for marketplace visibility
- Clone count tracks how many strategies reuse a given template
