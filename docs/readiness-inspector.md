# ROI evidence readiness inspector

`vef inspect <repo>` statically examines Git-tracked Python and JSON structures. It does not run
target code, read ignored or untracked files, inspect environment variables, contact deployments,
or collect evidence. Reports contain structural references rather than source or telemetry values.

The 100-point rubric is BDD 10, EDD 20, CDD 10, CBT 20, attribution/safety 10, economics and
cost-plus 20, and TDD/reproducibility 10. Green is 80–100, amber 50–79, and red 0–49. Missing
counterfactual or validated safety structures cap the score at 49; missing realization-cost
structure caps it at 69; sensitive payload fields in evidence stores cap it at 49.

Readiness, proof state, and cost-plus state are separate. A green-ready repository can have
unproven ROI. Missing inputs remain unknown and are never interpreted as zero.

## Optional policy

`.vef/inspect.yaml` may list repository-relative `exporters`, `evidence_schemas`, `test_commands`,
and `ignore_paths`. These mappings document integration points and narrow inspection, but cannot
award points. The initial CI mode is report-only.

```yaml
exporters:
  - src/product/value_export.py
evidence_schemas:
  - contracts/value-evidence.json
test_commands:
  - pytest tests/test_value_export.py
ignore_paths:
  - vendor
```

The JSON output implements `vef.readiness.v1alpha1`. Scoring or compatibility changes require a
new schema version or an explicitly documented rubric calibration revision.
