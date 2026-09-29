import json
from copy import deepcopy
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "claim.v1alpha2.json").read_text())


def eligible_claim():
    return {
        "schema_version": "vef.claim.v1alpha2",
        "id": "launchpad.pilot.cost-per-successful-journey",
        "product": "launchpad",
        "outcome_id": "launchpad.cost-per-slo-qualified-journey",
        "value_type": "cost_avoidance",
        "measurement": {"successful_journeys": 68, "unit": "journeys"},
        "counterfactual": {
            "method": "matched_control",
            "expected_without_product": 14.5,
        },
        "attribution": {
            "product_share": 0.5,
            "competing_factors": ["facilitator_experience", "workload_mix"],
        },
        "financial_model": {
            "gross_value": 187.0,
            "currency": "USD",
            "customer_validated": True,
        },
        "evidence": {
            "confidence": "high",
            "sources": [
                {
                    "id": "launchpad-reconciled-pilot-receipt",
                    "kind": "launchpad_receipt",
                    "uri": "evidence://launchpad/pilot-2026-09",
                    "content_sha256": "sha256:" + "a" * 64,
                    "retrieved_at": "2026-09-28T12:00:00Z",
                    "confidence": "high",
                    "validation_state": "accepted",
                }
            ],
            "reproducible": True,
            "validation_state": "accepted",
            "value_eligible": True,
        },
        "realization_cost": 50.0,
    }


def assert_invalid(claim, expected):
    errors = sorted(jsonschema.Draft202012Validator(SCHEMA).iter_errors(claim), key=str)
    assert errors
    assert expected in " | ".join(error.message for error in errors)


def test_decision_grade_claim_conforms():
    jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker()).validate(
        eligible_claim()
    )


def test_eligible_claim_rejects_legacy_string_source():
    claim = eligible_claim()
    claim["evidence"]["sources"] = ["aggregate-receipt"]
    assert_invalid(claim, "is not of type 'object'")


def test_eligible_claim_rejects_weak_counterfactual():
    claim = eligible_claim()
    claim["counterfactual"]["method"] = "expert_estimate"
    assert_invalid(claim, "is not one of")


def test_industry_benchmark_requires_full_provenance():
    claim = eligible_claim()
    claim["evidence"]["sources"][0]["kind"] = "industry_benchmark"
    assert_invalid(claim, "is a required property")


def test_hypothesis_may_preserve_legacy_source_reference():
    claim = deepcopy(eligible_claim())
    claim.pop("schema_version")
    claim["counterfactual"]["method"] = "assertion"
    claim["financial_model"]["customer_validated"] = False
    claim["evidence"] = {
        "confidence": "low",
        "sources": ["research-backlog"],
        "reproducible": False,
        "validation_state": "hypothesis",
        "value_eligible": False,
    }
    jsonschema.Draft202012Validator(SCHEMA).validate(claim)
