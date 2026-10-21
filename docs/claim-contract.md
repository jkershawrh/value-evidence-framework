# VEF claim contract

The canonical portable claim contract is
[`schemas/claim.v1alpha2.json`](../schemas/claim.v1alpha2.json), identified as
`vef.claim.v1alpha2`.

## Ownership

- Product repositories own raw measurements, extraction, privacy, provenance,
  and semantic correctness.
- Delivery systems such as Launchpad own their sanitized input contract and
  the adapter that maps it into this claim contract.
- VEF owns the canonical claim language, validation rules, counterfactual and
  attribution policy, confidence policy, calculations, and scorecard views.
- Presentation and sales systems may consume accepted claims. They do not
  create measurements, upgrade confidence, or mark a claim eligible.

The contract is file based and read only. Conformance does not grant deployment,
certification, promotion, financial approval, or remediation authority.

## Eligibility boundary

Hypothesis and directional claims may retain legacy string source references so
existing discovery work remains inspectable. A claim with
`evidence.value_eligible: true` fails closed unless it:

- declares `schema_version: vef.claim.v1alpha2`;
- uses an observed historical or stronger counterfactual;
- has customer-validated financial inputs;
- is reproducible and accepted at medium or high confidence; and
- uses structured evidence sources.

An `industry_benchmark` source additionally records its URL, table or section,
geography, effective date, retrieval timestamp, unit, transformation,
confidence, and validation state. This prevents a benchmark assumption from
silently becoming sales copy.

## Evaluation-card sources

An `evaluation_card` source references a governed-agent-fabric evaluation
card (`fabric.evaluation-card/v1`, pinned at
[`schemas/fabric.evaluation-card.v1.json`](../schemas/fabric.evaluation-card.v1.json)).
The card must validate against the pinned schema and carry a `card_sha256`
that matches its body. `vef evalcard <card> --uri <uri>` validates the card
and derives the structured source block, including `content_sha256`,
`locator`, and a transformation summary with the best pass-all-k rate.

VEF derives the source confidence from the card and never upgrades it:

- a RED or failed verdict derives `rejected` / `unverified`;
- LIVE evidence with claimable pass-all-k reliability for every system
  derives `candidate` at `medium` at most;
- anything else (rehearsal replay, unclaimable reliability, mixed labels)
  derives `candidate` at `low`.

Cards are machine-derived qualification evidence. They cannot make a claim
`accepted`, cannot supply the `high` confidence tier, and are not current
deployment evidence.

## Adapter conformance

An adapter proves conformance by validating its emitted `claim` object against
the immutable schema revision it declares. The adapter still owns sanitization,
population reconciliation, and evidence collection. VEF validation establishes
contract shape and calculation eligibility; it does not prove source truth or
causation.
