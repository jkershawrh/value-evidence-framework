# Project intake for ROI potential and counterfactual readiness

This intake frames a testable value hypothesis. It is not a sales questionnaire and completing it
does not establish ROI. Use `unknown` when an answer is not supported. Never use zero to represent
missing evidence.

Use [the YAML template](../examples/project-intake.yaml) as the handoff artifact. Keep sensitive
answers in approved private storage and put only sanitized structure in the product repository.

## 1. Project and decision

- Project, product, and repository names.
- Assessment sponsor and the decision this evidence will inform.
- Product-semantic, evidence, finance, privacy, and customer-validation owners.
- Intended audience: engineering, Red Hat/internal, customer, or portfolio.
- Decision deadline and proposed observation period.

## 2. Customer-observable outcome (BDD)

- Who experiences or owns the outcome?
- What changes outside the product if the capability works?
- What is the unit, bounded population, inclusion/exclusion rule, and period?
- What is the minimum meaningful improvement?
- What result would falsify the hypothesis or stop the pilot?
- Which quality, reliability, or safety outcome must not regress?

Activity metrics such as calls, rules, signals, commits, compression, utilization, and benchmark
scores may support the chain, but are not business outcomes by themselves.

## 3. Evidence availability (EDD)

- Which events measure exposure, outcome, failures, drops, retries, and unknown states?
- Are timestamps, provenance, workload/cohort identity, and schema versions available?
- Can start and end anchors be captured with matching ledger epochs?
- What evidence is observed, estimated, benchmark-derived, or customer-validated?
- Where will raw evidence live, who can access it, and what is its retention period?
- Which sanitized aggregates can be exported without payloads or identifiers?

## 4. Contracts and reproducibility (CDD/TDD)

- What versioned schema will the product export?
- Which validation, compatibility, calculation, negative-result, and replay tests exist?
- Can another reviewer reproduce the result from the bounded evidence bundle?
- Which calculation version and pricing source will be recorded?
- How are resets, partial collection, duplicates, late events, and missing data handled?

## 5. Counterfactual (CBT)

- What would happen to the same population without the product?
- Which method will estimate that world?
- Is the control independent, contemporaneous, and matched to the treatment population?
- Which workload, cohort, severity, geography, hardware, service level, and time variables must
  match?
- What contamination, selection bias, seasonality, learning effect, or regression-to-the-mean
  risks exist?
- Which competing explanations will be measured?
- What evidence would invalidate the comparison?

If no feasible comparison exists, ROI remains a hypothesis even when operational metrics improve.

## 6. AI participation and unit consumption

Complete this section when AI is in the value or cost path.

- Total population and independently defined AI-eligible population.
- Actual AI-routed requests, successful requests, failures, retries, drops, and unknown usage.
- Input/output tokens or equivalent billable units, latency, and pricing class.
- Verified price source and effective period.
- Baseline AI participation without the product.
- Why avoided product work would otherwise have reached AI.

Do not infer AI avoidance from compression or product-handled counts.

## 7. Attribution and safety

- Stable outcome ID shared by every contributing product.
- Product contribution rule and owner.
- Other products, teams, process changes, or market factors that influence the outcome.
- Dangerous miss/false-negative definition and threshold.
- Fail-closed conditions that suppress financial claims.
- Customer approval or dispute status for assumptions and financial inputs.

Contribution shares across products must not exceed 100% of the same outcome.

## 8. Economics and cost-plus

- Financial conversion formula, currency, and source for each input.
- Infrastructure, inference, enablement, support, services, and customer-side costs.
- Initial versus recurring engineering effort.
- Ruleset design, review, testing, deployment, monitoring, and maintenance hours.
- Loaded role-level rates and their approved source.
- Per-customer/per-deployment work versus reusable shared work.
- Marginal delivery cost, automation rate, reuse across cohorts, and time-to-value.
- Human transition or knowledge-transfer costs where applicable.

Do not infer effort from code volume, contributor count, or elapsed calendar time.

## 9. Pilot acceptance

Before collection begins, the owners approve:

- success, failure, safety, and stop thresholds;
- evidence and counterfactual contracts;
- privacy, retention, and access boundaries;
- attribution and financial-input rules;
- handling of unknowns and negative ROI; and
- the decision that each possible result will trigger.

The intake is complete when every required field is either supported by a source or explicitly
marked `unknown` with an owner and plan to resolve it.
