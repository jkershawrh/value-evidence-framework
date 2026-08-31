# Product integration

The first integration should be file-based and read-only. Each product exports one claim document
from telemetry it already owns. CI validates the contract; it does not calculate favorable ROI.

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
