# Value Evidence Framework

Evidence-first ROI scorecards for products and portfolios. VEF connects an observed capability
to an operational outcome, a counterfactual, attributable financial value, and an auditable
confidence rating. It deliberately refuses to turn activity into "proven ROI."

The initial portfolio is:

- [governed-cognitive-loop](https://github.com/jkershawrh/governed-cognitive-loop)
- [are-immutable-ledger](https://github.com/jkershawrh/are-immutable-ledger)
- [llm-d-fleet](https://github.com/jkershawrh/llm-d-fleet)
- [cascade-compression](https://github.com/jkershawrh/cascade-compression)

## Why a separate repository?

Product repositories own telemetry and product-specific facts. VEF owns the shared language for
value claims, evidence quality, counterfactuals, attribution, cost-to-realize, and scorecard
projection. Products integrate through versioned claim documents rather than importing a large
shared runtime.

## Quick start

```bash
python -m value_evidence.cli validate examples/claims.json
python -m value_evidence.cli score examples/claims.json --audience customer
python -m value_evidence.cli score examples/claims.json --audience red-hat
python -m value_evidence.cli inspect /path/to/product --format markdown
```

The examples are deliberately incomplete and therefore score red/amber. They are research
backlog examples, not assertions of realized customer ROI.

## Core invariants

1. No financial result without an explicit baseline and counterfactual.
2. Gross value, attributable value, and confidence-adjusted value remain separate.
3. Evidence confidence never upgrades itself because the calculated value is large.
4. Every outcome has a stable ID so multiple products cannot claim 100% of the same value.
5. Customer inputs, benchmarks, and product telemetry remain distinguishable.
6. A historical test result is not current deployment evidence.
7. Scorecards expose assumptions and missing evidence alongside results.

See [docs/methodology.md](docs/methodology.md), [docs/integration.md](docs/integration.md),
[docs/pilot.md](docs/pilot.md), and [docs/readiness-inspector.md](docs/readiness-inspector.md).

## Repository readiness inspection

`vef inspect` performs a local, read-only structural review and reports ROI evidence readiness on
a red/amber/green 0–100 scale. It inspects tracked text structures without executing repository
code or reading ignored and untracked evidence. Its proof state and cost-plus state are separate
from the readiness grade; repository structure is never presented as proof of realized value.

The packaged `skills/roi-evidence-readiness` Agent Skill explains the deterministic result and
creates implementation plans. It cannot alter the grade or modify the inspected repository.
