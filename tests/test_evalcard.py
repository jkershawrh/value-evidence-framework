import json
from pathlib import Path

from jsonschema import Draft202012Validator

from value_evidence.evalcard import canonical, derive_source, digest, validate_card

CLAIM_SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "claim.v1alpha2.json").read_text())


def card(**overrides):
    value = {
        "schema_version": "fabric.evaluation-card/v1",
        "issued_at": "2026-10-21T00:00:00+00:00",
        "mode": "workload-pipeline",
        "construct": {
            "statement": "Whether a candidate interprets one bounded operational snapshot correctly.",
            "metric": "Exact-output GREEN grade per case against frozen references within the deadline.",
            "gaming_analysis": "A digest-keyed replay table could pass without interpretation capability.",
            "construct_sha256": "a" * 64,
        },
        "evaluation": {
            "source_schema_version": "folsom.workload-pipeline/v1",
            "source_id": "card-test-suite",
            "binding_sha256": "b" * 64,
            "measured_sha256": "c" * 64,
            "split": "development",
        },
        "systems": [
            {
                "system_id": "c1",
                "scaffold": {"adapter": "replay", "procedure_revision": "test-procedure-v1"},
                "model_binding": {"candidate_kind": "recorded-model", "profile_sha256": "d" * 64},
                "evidence_label": "REHEARSAL",
                "repetition": {"trials_per_case": 2, "case_count": 2, "total_trials": 4, "incomplete_trials": 0},
                "single_attempt_rate": {"value": 0.5, "passed": 2, "total": 4, "wilson_95": [0.15, 0.85]},
                "pass_at_k": {"value": 0.5, "passed": 1, "total": 2, "wilson_95": [0.09, 0.91]},
                "pass_all_k": {"value": 0.5, "passed": 1, "total": 2, "k": 2, "wilson_95": [0.09, 0.91]},
                "reliability_claimable": False,
                "reliability_note": "Incomplete trials are present; consistency is not claimable here.",
                "performance": {
                    "latency": {"unit": "seconds", "mean": 0.1, "max": 0.2},
                    "model_calls": 0,
                    "deadline": {"unit": "seconds", "value": 60},
                },
                "scope": "synthetic test cohort with retained replay responses only",
            }
        ],
        "uncertainty": {
            "method": "Wilson score interval on binomial case outcomes",
            "judge_error_included": False,
            "grading_basis": ["imported exact-output grades; no verifier ran"],
            "notes": "Reference-authoring error remains unquantified for this cohort.",
        },
        "holdout_policy": {
            "split": "development",
            "case_origins": ["synthetic"],
            "statement": "Declared held-out status does not independently establish non-contamination.",
        },
        "verdict": {"color": "AMBER", "authorizes_execution": False},
        "limits": "Bounded local execution; no operational claim follows from this card.",
    }
    value.update(overrides)
    value["card_sha256"] = digest({key: item for key, item in value.items() if key != "card_sha256"})
    return value


def live_green_card():
    value = card()
    system = dict(value["systems"][0])
    system["evidence_label"] = "LIVE"
    system["reliability_claimable"] = True
    system["reliability_note"] = "All k runs per case completed; pass-all-k on the measured case set."
    value["systems"] = [system]
    value["verdict"] = {"color": "GREEN", "authorizes_execution": False}
    return card(**{"systems": [system], "verdict": {"color": "GREEN", "authorizes_execution": False}})


def test_valid_card_passes_validation():
    assert validate_card(card()) == []


def test_rehearsal_card_derives_low_confidence_candidate_source():
    source = derive_source(card(), uri="file://runs/evalcard-smoke/evaluation-card.json")
    assert source["kind"] == "evaluation_card"
    assert source["confidence"] == "low"
    assert source["validation_state"] == "candidate"
    assert source["content_sha256"] == "sha256:" + card()["card_sha256"]
    assert source["id"].startswith("evalcard-")
    assert "pass_all_k 0.5" in source["transformation"]


def test_live_claimable_green_card_reaches_medium_but_never_accepted():
    source = derive_source(live_green_card(), uri="file://runs/live/evaluation-card.json")
    assert source["confidence"] == "medium"
    assert source["validation_state"] == "candidate"


def test_red_verdict_is_rejected_and_unverified():
    value = card(verdict={"color": "RED", "authorizes_execution": False})
    source = derive_source(value, uri="file://runs/red/evaluation-card.json")
    assert source["confidence"] == "unverified"
    assert source["validation_state"] == "rejected"


def test_failed_pilot_verdict_is_rejected():
    value = card(
        mode="portable-pilot",
        verdict={"quality": "failed", "authorizes_execution": False},
    )
    source = derive_source(value, uri="file://runs/pilot/evaluation-card.json")
    assert source["validation_state"] == "rejected"
    assert source["confidence"] == "unverified"


def test_digest_mismatch_is_rejected():
    value = card()
    value["card_sha256"] = "0" * 64
    errors = validate_card(value)
    assert any("card_sha256" in error for error in errors)
    try:
        derive_source(value, uri="file://runs/tampered/evaluation-card.json")
        raise AssertionError("tampered card must be refused")
    except ValueError as exc:
        assert "card_sha256" in str(exc)


def test_schema_violation_is_rejected():
    value = card()
    del value["systems"]
    value["card_sha256"] = digest({key: item for key, item in value.items() if key != "card_sha256"})
    assert validate_card(value)


def test_derived_source_conforms_to_claim_source_contract():
    source = derive_source(card(), uri="file://runs/evalcard-smoke/evaluation-card.json")
    Draft202012Validator(CLAIM_SCHEMA["$defs"]["source"]).validate(source)


def test_claim_with_evaluation_card_source_validates():
    source = derive_source(card(), uri="file://runs/evalcard-smoke/evaluation-card.json")
    claim = {
        "schema_version": "vef.claim.v1alpha2",
        "id": "fabric.qualification-coverage",
        "product": "governed-agent-fabric",
        "outcome_id": "outcome-qualification",
        "value_type": "cost_avoidance",
        "measurement": {"observed": 1, "unit": "qualifications"},
        "counterfactual": {"method": "historical_baseline", "expected_without_product": 0},
        "attribution": {"product_share": 0.5, "competing_factors": ["manual review discipline"]},
        "financial_model": {"gross_value": 0, "currency": "USD", "customer_validated": False},
        "evidence": {
            "confidence": "low",
            "sources": [source],
            "reproducible": True,
            "validation_state": "candidate",
            "value_eligible": False,
        },
        "realization_cost": 0,
    }
    Draft202012Validator(CLAIM_SCHEMA).validate(claim)


def test_canonical_matches_fabric_digest_rules():
    body = {"b": 1, "a": "é"}
    assert canonical(body) == b'{"a":"\xc3\xa9","b":1}'
