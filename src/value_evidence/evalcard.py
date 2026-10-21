"""Evaluation-card evidence sources.

Validates governed-agent-fabric evaluation cards against the pinned
``fabric.evaluation-card/v1`` schema and derives a structured VEF evidence
source. Cards are machine-derived qualification evidence: they can raise a
claim to candidate status at most, never to accepted, and a card is not
current deployment evidence. VEF derives source confidence from the card and
never upgrades it because a calculated value is large.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

CARD_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "fabric.evaluation-card-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _card_schema() -> dict[str, Any]:
    if not CARD_SCHEMA_PATH.is_file():
        raise FileNotFoundError(f"pinned card schema missing: {CARD_SCHEMA_PATH}")
    return json.loads(CARD_SCHEMA_PATH.read_text())


def validate_card(card: Any) -> list[str]:
    """Validate schema conformance and the card body digest. Returns errors."""
    if not isinstance(card, dict):
        return ["card must be a JSON object"]
    errors = [
        f"schema: {error.message} at {list(error.absolute_path) or '<root>'}"
        for error in Draft202012Validator(_card_schema()).iter_errors(card)
    ]
    if isinstance(card, dict) and "card_sha256" in card:
        body = {key: value for key, value in card.items() if key != "card_sha256"}
        if digest(body) != card["card_sha256"]:
            errors.append("card_sha256 does not match the card body")
    return errors


def _verdict_color(card: dict[str, Any]) -> str | None:
    verdict = card.get("verdict", {})
    if verdict.get("color"):
        return verdict["color"]
    if verdict.get("quality") == "passed":
        return "GREEN"
    if verdict.get("quality") == "failed":
        return "RED"
    return None


def confidence_policy(card: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Derive (confidence, validation_state, notes) under the VEF source policy."""
    systems = card.get("systems", [])
    notes: list[str] = []
    if _verdict_color(card) in {"RED"} or not systems:
        return "unverified", "rejected", ["card verdict is RED or no systems were measured"]
    labels = {system.get("evidence_label") for system in systems}
    claimable = {bool(system.get("reliability_claimable")) for system in systems}
    if labels != {"LIVE"}:
        notes.append("evidence labels are not all LIVE: " + ",".join(sorted(str(x) for x in labels)))
    if claimable != {True}:
        notes.append("pass-all-k reliability is not claimable for every system")
    if not notes:
        notes.append("machine-derived qualification evidence; acceptance requires human review")
        return "medium", "candidate", notes
    return "low", "candidate", notes


def derive_source(card: dict[str, Any], uri: str, retrieved_at: str | None = None) -> dict[str, Any]:
    """Derive a structured VEF evidence source from a valid evaluation card."""
    errors = validate_card(card)
    if errors:
        raise ValueError("; ".join(errors))
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError("uri is required so the card remains retrievable")
    confidence, state, notes = confidence_policy(card)
    systems = card["systems"]
    best_pass_all_k = max(system["pass_all_k"]["value"] for system in systems)
    ks = sorted({system["pass_all_k"]["k"] for system in systems})
    labels = sorted({system.get("evidence_label", "unknown") for system in systems})
    verdict = card.get("verdict", {})
    verdict_label = verdict.get("color") or verdict.get("quality") or "unknown"
    return {
        "id": "evalcard-" + card["card_sha256"][:12],
        "kind": "evaluation_card",
        "uri": uri,
        "content_sha256": "sha256:" + card["card_sha256"],
        "locator": f"{card['mode']}:{card['evaluation']['source_id']}",
        "retrieved_at": retrieved_at or card["issued_at"],
        "confidence": confidence,
        "validation_state": state,
        "transformation": (
            f"fabric evaluation card; {len(systems)} system(s); best pass_all_k {best_pass_all_k} "
            f"over k in {ks}; evidence {','.join(labels)}; verdict {verdict_label}; " + "; ".join(notes)
        ),
    }
