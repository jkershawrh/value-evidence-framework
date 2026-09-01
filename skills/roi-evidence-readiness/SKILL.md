---
name: roi-evidence-readiness
description: Assess a software repository's readiness to produce defensible ROI evidence, explain deterministic VEF findings, and create a read-only implementation plan. Use for ROI evidence gaps, counterfactual readiness, cost-plus readiness, or product scorecard instrumentation planning.
---

# ROI Evidence Readiness

Use the repository's `vef inspect` command as the authoritative grader. Run it against a local
repository or consume an existing `vef.readiness.v1alpha1` JSON report.

## Invariants

- Preserve the CLI's score, rating, proof state, cost-plus state, finding statuses, and caps exactly.
- Treat structure as readiness, never proof of realized value or causation.
- Work read-only: do not edit, commit, open pull requests, access deployments, query databases, or
  collect production evidence while using this skill.
- Cite only structural evidence returned by the inspector. Do not reproduce raw telemetry,
  credentials, environment values, customer content, or sensitive excerpts.
- Keep public OSS structure separate from private production evidence and deployment files. Direct
  raw evidence and customer economics to ignored or private storage.
- Label uncertain product semantics instead of inferring them from names or compression ratios.

## Deliverable

Explain the highest-impact gaps and why they prevent defensible ROI. Then produce a patch plan with
minimum, recommended pilot-ready, and advanced portfolio-ready options when the report supplies
them. Map proposed work to TDD, EDD, CDD, BDD, CBT, safety, and cost-plus acceptance tests.

Plans may identify likely integration points, interfaces, schemas, tests, rollout, and monitoring,
but must not implement changes. Missing measurements remain unknown rather than zero. Specifically
include ruleset design, testing, deployment, monitoring, and maintenance effort when the economics
finding is incomplete.
