# Product integration

The first integration should be file-based and read-only. Each product exports one claim document
from telemetry it already owns. CI validates the contract; it does not calculate favorable ROI.

Start every integration with [the project intake](project-intake.md) and a report-only
`vef inspect`. The intake owns semantic intent; the repository owns instrumentation and sanitized
export; VEF owns deterministic validation and scoring. An adapter must not fill missing intake
fields with favorable defaults.

## Candidate product claims

- **GCL OSS (planned authoritative source):** harmful or infeasible actions rejected before commit;
  ultimate value needs observed avoided-impact evidence, not DecisionPackage counts. The current
  `governed-cognitive-loop` example is a provisional hypothesis only. Add the production adapter
  after the OSS contract stabilizes; do not couple VEF to an in-progress repository shape.
- **are-immutable-ledger:** repeat validations avoided through accepted receipts; value needs
  consumer acceptance, time/cost per validation, and proof that checks were safely skipped.
- **llm-d-fleet:** capacity and placement efficiency; value needs comparable demand, service-level
  controls, infrastructure cost, and execution evidence.
- **cascade-compression:** model calls avoided while maintaining an agreed miss threshold; this has
  the shortest path to a defensible first pilot because compression and throughput are measured.

## Ownership

Product repos own raw metrics, extraction, privacy, and semantic correctness. VEF owns claim
validation, portfolio attribution, confidence policy, calculation versions, and scorecard views.
An immutable ledger may retain signed claim inputs and calculation receipts, but ledger inclusion
proves integrity and provenance—not truth or causation.

## Versioned contract

Adapters targeting `vef.claim.v1alpha2` validate their emitted claim against
[`schemas/claim.v1alpha2.json`](../schemas/claim.v1alpha2.json). See
[the claim contract](claim-contract.md) for the fail-closed eligibility and source-provenance
rules. An adapter may keep incomplete evidence visible as a hypothesis, but it must not mark the
claim value-eligible until the stricter branch of the schema passes.
