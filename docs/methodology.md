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

## Value dimensions

The claim chain begins at a product capability and ends at financial value, but the path between
them crosses several independent cost domains. A single gross_value number obscures where value
comes from and which inputs are observed versus assumed. Value dimensions make each contribution
a separate, typed, auditable line item.

A claim's `financial_model` may include an optional `value_dimensions` array. Each dimension is
an independent value contribution with its own inputs, evidence basis, confidence, and source.
When present, `gross_value` equals the sum of all dimension values. Claims without dimensions
continue to work exactly as before.

### Dimension types

**Inference cost avoided.** Model calls that did not happen because the product handled them
differently. Accepts either an observed cost difference or a call count with unit cost. This is
the original VEF value path, now available as an explicit dimension.

**Infrastructure cost avoided.** Hardware, power, or cloud API costs for serving inference that
was not needed. Supports on-premises (capex + power + amortization) and cloud (token-based)
modes. Sensible defaults from industry benchmarks (US EIA power rates, Uptime Institute PUE)
are applied when inputs are not provided.

**Human operational cost avoided.** Engineer time not spent triaging, investigating, and acting
on signals. This is often the largest real-world cost for operational products. Defaults to
industry benchmarks for triage time (3 min), investigation time (15 min), and blended SRE
hourly rate ($85/hr).

**Incident response value.** Value of faster incident detection and response. Captures MTTR
improvement multiplied by incident count and cost per minute of downtime. The baseline MTTR
defaults to the DORA State of DevOps median; cost per minute has no default because it is
too context-specific.

**Downstream business impact.** SLA penalties avoided, user productivity preserved, support
tickets prevented. Requires at least one impact pair (SLA, productivity, or support). Has no
defaults — these require customer-specific inputs and automatically receive an estimated
evidence basis.

**Organizational knowledge value (OKV).** Value of institutional knowledge captured, retained,
and made accessible across the organization — not just the ops team. Three independent value
paths, each calculated separately:

*Decision acceleration.* Time saved when anyone — SRE, sales engineer, support, product,
leadership — can recall institutional context instead of re-investigating or asking the one
person who knows. Measured in decisions informed per period × time saved × blended rate.

*Onboarding acceleration.* New hires across all functions reach productivity faster because
the knowledge system has answers that used to take months to absorb. Calculated from annual
hires × weeks saved × weekly loaded cost, amortized daily.

*Knowledge retention.* When people leave, the knowledge doesn't leave with them. Calculated
from knowledge consumers × departure rate × knowledge loss per departure × retention factor.
The retention factor (0–1) represents how much of the departing person's institutional
knowledge the system actually captures — operational patterns yes, relationships and judgment
no. This path directly connects to HCO: higher knowledge retention reduces the attrition
risk cost in the human cost of ownership dimension.

OKV also carries portfolio indicators (memories formed, causal links discovered, knowledge
domains) that are not directly costed but provide context for the value claim.

**Human cost of ownership (HCO).** The human price of automation. This is a *cost* dimension —
it subtracts from gross value rather than adding to it. When a product displaces human work,
there is a real transition cost: reskilling the affected people, productivity lost during role
transition, and the risk that displaced workers leave before knowledge transfers. HCO forces
this conversation to happen at claim time, not after the fact.

Inputs: fractional FTE displaced, loaded annual cost per FTE. Defaults from SHRM 2024 and
McKinsey workforce research cover reskilling cost ($24,800/FTE), transition duration (6 months),
productivity loss during transition (20%), attrition risk (15%), and replacement cost (50% of
annual salary). The total transition investment is amortized over 365 days to produce a
per-period cost comparable to the value dimensions.

HCO is not a moral judgment — it is an economic externality that most ROI frameworks ignore.
A product that creates $1,000/day of value but displaces $200/day of human transition cost
has a true gross value of $800/day. The framework makes this visible, auditable, and
impossible to hide.

### Evidence basis and confidence

Each dimension carries its own `evidence_basis` (observed, estimated, or industry_benchmark) and
`confidence` (unverified, low, medium, high) independent of the claim-level confidence. The
scorecard renders these per-dimension so reviewers can see which parts of the value are grounded
in measurement versus assumption.

### Auditable defaults

Every default value has a named source (e.g. "PagerDuty State of Digital Operations 2024",
"Gartner IT operations benchmark"). When a product omits an optional input and the framework
applies a default, the source is preserved in the dimension output. No default is silent.

### Schema

The `value_dimensions` array is validated against
[schemas/value-dimensions.v1alpha1.json](../schemas/value-dimensions.v1alpha1.json).

## Shared route and effort evidence

Compression is not an economic measure. Products may publish a route ledger that partitions the
observed population into terminal outcomes and identifies AI eligibility, actual calls, tokens,
runtime, and cost. An `unknown` route is valid and must not be silently counted as avoided AI.

Products may also publish initial and recurring engineering effort by activity, role category,
hours, loaded rate, and source. VEF includes those costs in realization cost and exposes them in
both scorecards. Raw time records stay with the product or customer; the portable claim contains
only the auditable aggregates needed for value analysis.
