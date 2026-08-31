# Methodology

## Claim chain

`capability → product event → operational outcome → business outcome → financial value`

Every arrow is an assumption until supported. VEF stores the links instead of hiding them in a
dashboard formula.

## Counterfactual ladder

Strongest to weakest: randomized/phased rollout, matched control, difference-in-differences,
interrupted time series, historical baseline, modeled baseline, expert estimate, assertion.
A weak method can guide discovery but cannot produce a green claim.

## Value layers

- **Gross value:** financial conversion before attribution.
- **Attributable value:** gross value × product contribution.
- **Confidence-adjusted value:** attributable value × evidence factor.
- **Net value:** confidence-adjusted value − fully loaded realization cost.

Confidence factors are conservative defaults, visible in code, and should be calibrated with
real validation data rather than negotiated per deal.

## TDD / EDD / CDD / BDD / CBT

- **TDD:** executable tests establish calculation behavior before implementation.
- **EDD (evidence-driven development):** every claim starts with the evidence needed to falsify it.
- **CDD (contract-driven development):** product adapters emit versioned, validated claim records.
- **BDD:** scenarios describe the customer-observable outcome and honesty boundaries.
- **CBT (counterfactual-based testing):** each claim is challenged against alternate explanations,
  sensitivity ranges, and a world in which the product was not used.

## Red / amber / green rubric

A green claim requires high-confidence evidence, a matched or stronger counterfactual,
customer-validated financial inputs, reproducibility, and recorded competing factors. Amber is
directional with limited gaps. Red means the value hypothesis is useful but not decision-grade.

## Cost-plus test

The internal scorecard compares confidence-adjusted value with fully loaded realization cost.
That is necessary but insufficient. A future maturity dimension will also score marginal delivery
cost, customer-specific engineering, time-to-value, evidence automation, and cohort repeatability.
High value that depends on proportional services labor is still a cost-plus warning.

