# Adoption guide

VEF answers three different questions. They must not be collapsed into one score.

1. **ROI potential:** Is there a plausible, customer-observable outcome whose value could exceed
   the cost and risk of realizing it?
2. **Evidence readiness:** Can the project produce bounded, reproducible evidence to test that
   hypothesis? `vef inspect` is authoritative for this structural grade.
3. **Realized ROI:** Did a measured intervention outperform a credible counterfactual after
   attribution, safety failures, and fully loaded realization cost? Only a validated claim and
   evidence bundle can answer this.

## Recommended assessment flow

### Gate 1 — frame the hypothesis

Complete the project intake. Name one primary outcome, one population, one period, the customer
who observes the outcome, and the condition that would falsify the hypothesis. If the outcome is
only activity—requests, commits, rules, compression, benchmark score, or adoption—the hypothesis
is not ready.

**Deliverable:** pre-registered value hypothesis and owner map.

### Gate 2 — inspect readiness

Run:

```bash
vef inspect /path/to/project --format json --output readiness.json
vef inspect /path/to/project --format markdown --output readiness.md
```

Review the grade, hard caps, proof state, cost-plus state, findings, and safety warnings. Do not
edit the score manually. Product-specific `.vef/inspect.yaml` mappings may locate structures but
cannot award points.

**Deliverable:** deterministic readiness report and implementation options.

### Gate 3 — design the counterfactual

Choose the strongest feasible comparison before seeing the financial result: randomized or phased
rollout, matched control, difference-in-differences, interrupted time series, historical baseline,
or an explicitly modeled baseline. Define matching variables, contamination risks, competing
explanations, and negative-result handling.

For AI-routing products, separately measure total population, AI-eligible population, actual AI
requests, successful requests, retries, drops, unknown usage, tokens, latency, and pricing class.
“Handled by the product” is not equivalent to “would otherwise have reached AI.”

**Deliverable:** counterfactual protocol and bounded evidence contract.

### Gate 4 — instrument cost and safety

Instrument customer harm and quality thresholds alongside value. Capture initial and recurring
engineering effort, including ruleset design, review, testing, deployment, monitoring, and
maintenance. Use loaded role-level rates; never collect personal compensation or employee-level
time records in the portable claim.

**Deliverable:** safety gates, route/usage ledger, and realization-cost ledger.

### Gate 5 — run a bounded pilot

Capture immutable start and end anchors with matching ledger epochs, deployment revision, evidence
schema, calculation version, and workload identity. Store raw evidence privately. Export only the
sanitized aggregates required by the VEF contract.

**Deliverable:** reproducible evidence bundle and candidate claim.

### Gate 6 — decide

Validate the claim and render both scorecards. The decision is one of:

- **stop:** no credible value hypothesis, unacceptable safety, or no feasible counterfactual;
- **instrument:** plausible potential but important evidence remains unknown;
- **pilot:** bounded comparison and cost collection are feasible;
- **scale cautiously:** decision-grade positive evidence with measured marginal delivery cost;
- **do not scale:** negative or cost-plus result; or
- **retest:** evidence was invalidated by drift, contamination, ledger reset, or missing data.

## Minimum package for an assessment

- Completed intake, with unknowns stated explicitly.
- Local path or clone of the project repository.
- `vef inspect` JSON and Markdown reports.
- Proposed evidence locations and privacy classification.
- Counterfactual protocol.
- Pilot acceptance tests mapped to TDD, EDD, CDD, BDD, CBT, safety, and cost-plus.

Repository inspection is safe to share when it contains only structural references. Intake and
pilot evidence may be private; do not commit credentials, payloads, customer identifiers, raw
telemetry, cluster metadata, or deployment configuration to VEF.
