# Value Evidence Framework

Evidence-first ROI scorecards for products and portfolios. VEF connects an observed capability
to an operational outcome, a counterfactual, attributable financial value, and an auditable
confidence rating. It deliberately refuses to turn activity into "proven ROI."

VEF is ready to use as a **discovery and evidence-readiness framework**. It can determine whether
a project has the structures and proposed evidence needed to test an ROI hypothesis. It cannot
determine that a project has positive ROI from repository structure, benchmark results, adoption,
compression, or activity counts alone.

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
python -m pip install -e '.[dev]'
vef inspect /path/to/product --format markdown --output readiness.md
python -m value_evidence.cli validate examples/claims.json
python -m value_evidence.cli score examples/claims.json --audience customer
python -m value_evidence.cli score examples/claims.json --audience red-hat
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

The portable claim language is published as
[`vef.claim.v1alpha2`](schemas/claim.v1alpha2.json). Its ownership and adapter
boundary are documented in [the claim contract](docs/claim-contract.md).

See [docs/methodology.md](docs/methodology.md), [docs/integration.md](docs/integration.md),
[docs/project-intake.md](docs/project-intake.md), [docs/adoption-guide.md](docs/adoption-guide.md),
[docs/pilot.md](docs/pilot.md), and [docs/readiness-inspector.md](docs/readiness-inspector.md).

## Using VEF with a new project

1. Ask the project owner to complete [the project intake](docs/project-intake.md) without placing
   credentials, customer data, raw telemetry, or personal compensation in Git.
2. Run `vef inspect` against the project repository. This grades evidence readiness, not ROI.
3. Reconcile the intake with the deterministic findings. Repository names and comments cannot
   substitute for executable contracts, tests, or measured evidence.
4. Pre-register the value hypothesis, bounded population, counterfactual, safety threshold,
   attribution rule, pricing basis, and realization-cost method before collecting results.
5. Run a bounded pilot and emit a versioned VEF claim. Missing values remain `unknown`.
6. Validate the claim and render customer and Red Hat scorecards from the same calculation kernel.

The first useful outcome may be “not currently measurable” or “unlikely to scale.” Both are valid
results. See [the adoption guide](docs/adoption-guide.md) for decision gates and deliverables.

## Repository readiness inspection

`vef inspect` performs a local, read-only structural review and reports ROI evidence readiness on
a red/amber/green 0–100 scale. It inspects tracked text structures without executing repository
code or reading ignored and untracked evidence. Its proof state and cost-plus state are separate
from the readiness grade; repository structure is never presented as proof of realized value.

The packaged `skills/roi-evidence-readiness` Agent Skill explains the deterministic result and
creates implementation plans. It cannot alter the grade or modify the inspected repository.

## What to send

For a new assessment, send the project owner this repository and ask for:

- a completed intake using [examples/project-intake.yaml](examples/project-intake.yaml);
- read access to the source repository for structural inspection;
- named owners for product semantics, evidence, finance, privacy, and customer validation; and
- an agreement that raw/private evidence stays in approved private storage.

Do not request production credentials or raw customer payloads as part of repository intake.
