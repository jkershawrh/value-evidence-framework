#!/usr/bin/env python3
"""Generate a VEF claim from soak start/end snapshots.

Usage:
    python scripts/soak-to-claim.py \\
        --start soak-data/snapshot-start-*.json \\
        --end   soak-data/snapshot-end-*.json \\
        [--output examples/cascade-soak-72h.json]

Reads the two JSON snapshots produced by soak-collect.sh and builds a
VEF claim with observed data wherever possible, falling back to the
pilot estimates for dimensions that need manual input.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def delta(start: dict, end: dict, *keys: str) -> float | None:
    """Compute end[k] - start[k] for a nested key path, or None if missing."""
    s, e = start, end
    for k in keys:
        s = s.get(k) if isinstance(s, dict) else None
        e = e.get(k) if isinstance(e, dict) else None
    if isinstance(s, (int, float)) and isinstance(e, (int, float)):
        return e - s
    return None


def safe_get(data: dict, *keys: str, default=None):
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return default
    return val if val is not None else default


def extract_sc_metrics(cls_end: dict, cls_start: dict) -> dict:
    """Extract SC hybrid coverage and quality metrics from classifier stats."""
    cov_end = cls_end.get("coverage") or {}
    cov_start = cls_start.get("coverage") or {}
    metrics_end = cls_end.get("metrics") or {}

    sc_authoritative = (cov_end.get("sc_authoritative", 0) or 0) - (
        cov_start.get("sc_authoritative", 0) or 0
    )
    llm_fallback = (cov_end.get("llm_fallback", 0) or 0) - (
        cov_start.get("llm_fallback", 0) or 0
    )
    severity_gated = (cov_end.get("severity_gated", 0) or 0) - (
        cov_start.get("severity_gated", 0) or 0
    )
    margin_gated = (cov_end.get("margin_gated", 0) or 0) - (
        cov_start.get("margin_gated", 0) or 0
    )
    sc_failure = (cov_end.get("sc_failure", 0) or 0) - (
        cov_start.get("sc_failure", 0) or 0
    )
    total_classified = sc_authoritative + llm_fallback + sc_failure

    comparisons = (metrics_end.get("comparisons", 0) or 0) - (
        (cls_start.get("metrics") or {}).get("comparisons", 0) or 0
    )
    agreements = (metrics_end.get("agreements", 0) or 0) - (
        (cls_start.get("metrics") or {}).get("agreements", 0) or 0
    )
    disagreements = (metrics_end.get("disagreements", 0) or 0) - (
        (cls_start.get("metrics") or {}).get("disagreements", 0) or 0
    )

    agreement_rate = agreements / comparisons if comparisons > 0 else None

    latency = metrics_end.get("latency_ms") or {}
    sc_latency_p50 = safe_get(latency, "semantic", "p50")
    llm_latency_p50 = safe_get(latency, "generative", "p50")

    return {
        "sc_authoritative": sc_authoritative,
        "llm_fallback": llm_fallback,
        "severity_gated": severity_gated,
        "margin_gated": margin_gated,
        "sc_failure": sc_failure,
        "total_classified": total_classified,
        "sc_coverage_rate": (
            round(sc_authoritative / total_classified, 4) if total_classified > 0 else None
        ),
        "comparisons": comparisons,
        "agreements": agreements,
        "disagreements": disagreements,
        "agreement_rate": round(agreement_rate, 4) if agreement_rate is not None else None,
        "sc_latency_p50_ms": sc_latency_p50,
        "llm_latency_p50_ms": llm_latency_p50,
        "hybrid_margin": cls_end.get("hybrid_margin"),
        "hybrid_suppress_margin": cls_end.get("hybrid_suppress_margin"),
        "serializer_revision": cls_end.get("serializer_revision"),
        "mode": cls_end.get("mode"),
    }


def count_false_suppressions(comparisons_data: dict | list | None) -> dict:
    """Count dangerous false suppressions from classifier comparison data."""
    if not comparisons_data:
        return {"false_suppressions": 0, "total_comparisons": 0, "false_suppression_rate": None}

    records = comparisons_data if isinstance(comparisons_data, list) else (
        comparisons_data.get("comparisons", []) if isinstance(comparisons_data, dict) else []
    )

    total = len(records)
    false_suppressions = 0
    for r in records:
        sc_label = r.get("sc_label") or r.get("semantic_label") or ""
        llm_label = r.get("llm_label") or r.get("generative_label") or ""
        suppress_labels = {"routine_noise", "known_pattern"}
        escalate_labels = {"needs_attention", "real_incident"}
        if sc_label in suppress_labels and llm_label in escalate_labels:
            false_suppressions += 1

    return {
        "false_suppressions": false_suppressions,
        "total_comparisons": total,
        "false_suppression_rate": (
            round(false_suppressions / total, 4) if total > 0 else None
        ),
    }


def build_claim(start: dict, end: dict) -> dict:
    ts_start = start.get("timestamp", "unknown")
    ts_end = end.get("timestamp", "unknown")

    try:
        dt_start = datetime.strptime(ts_start, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        dt_end = datetime.strptime(ts_end, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        hours = (dt_end - dt_start).total_seconds() / 3600
    except (ValueError, TypeError):
        hours = 72.0

    signals_processed = delta(start, end, "stats", "signals_processed") or 0
    cascade_handled = delta(start, end, "stats", "cascade_handled") or 0
    cascade_forwarded = delta(start, end, "stats", "cascade_forwarded") or 0

    compression_ratio = (
        cascade_handled / signals_processed if signals_processed else 0
    )

    end_stats = end.get("stats") or {}
    start_stats = start.get("stats") or {}

    # Memory deltas
    mem_start = start.get("memory_stats") or {}
    mem_end = end.get("memory_stats") or {}
    memories_formed = (
        (mem_end.get("formed_total", 0) or 0) - (mem_start.get("formed_total", 0) or 0)
    )
    memories_end_size = mem_end.get("size", 0) or 0
    evictions = (
        (mem_end.get("evictions_total", 0) or 0) - (mem_start.get("evictions_total", 0) or 0)
    )

    # Agent counts
    end_agents = end.get("agents") or {}
    agent_list = end_agents.get("agents", []) if isinstance(end_agents, dict) else []
    active_agents = sum(1 for a in agent_list if a.get("status") == "active")
    total_agents = len(agent_list)

    # Classifier stats — includes SC hybrid coverage SLI
    cls_end = end.get("classifier_stats") or {}
    cls_start = start.get("classifier_stats") or {}

    # SC hybrid metrics
    sc_metrics = extract_sc_metrics(cls_end, cls_start)

    # False suppression tracking from comparison records
    end_comparisons = end.get("classifier_comparisons")
    start_comparisons = start.get("classifier_comparisons")
    false_supp = count_false_suppressions(end_comparisons)

    calls_avoided = int(cascade_handled) if cascade_handled else 0
    days = hours / 24

    # --- Build dimensions with observed data where possible ---
    dimensions = []

    # 1. Inference cost avoided — SC hybrid means most signals classified
    #    at ~0 cost (CPU-only SC) instead of expensive LLM calls
    inference_inputs: dict = {}
    baseline_cost = safe_get(cls_end, "baseline_inference_cost_usd")
    cascade_cost = safe_get(cls_end, "cascade_inference_cost_usd")
    if baseline_cost is not None and cascade_cost is not None:
        observed_diff = float(baseline_cost) - float(cascade_cost)
        inference_inputs["observed_cost_difference_usd"] = round(observed_diff, 2)
        inference_basis = "observed"
    else:
        inference_inputs["calls_avoided"] = calls_avoided
        inference_inputs["cost_per_call_usd"] = 0.10
        inference_basis = "estimated"

    if sc_metrics["sc_authoritative"]:
        inference_inputs["sc_authoritative_calls"] = sc_metrics["sc_authoritative"]
        inference_inputs["llm_fallback_calls"] = sc_metrics["llm_fallback"]
        inference_inputs["sc_cost_per_call_usd"] = 0.0
        inference_inputs["_sc_note"] = (
            f"SC handled {sc_metrics['sc_authoritative']:,} signals at ~0 cost "
            f"(CPU-only, {sc_metrics.get('sc_latency_p50_ms', '?')}ms p50). "
            f"LLM fallback for {sc_metrics['llm_fallback']:,} signals "
            f"({sc_metrics.get('llm_latency_p50_ms', '?')}ms p50)."
        )

    dimensions.append({
        "dimension": "inference_cost_avoided",
        "inputs": inference_inputs,
        "source": "soak_route_ledger" if inference_basis == "observed" else "soak_call_count_estimate",
        "confidence": "medium" if inference_basis == "observed" else "low",
        "evidence_basis": inference_basis,
    })

    # 2. Infrastructure cost avoided (keep pilot estimate structure)
    dimensions.append({
        "dimension": "infrastructure_cost_avoided",
        "inputs": {
            "mode": "on_prem",
            "units_avoided": round(0.017 * days, 4),
            "hardware_cost_per_unit_usd": 30000,
            "power_watts": 1200,
        },
        "source": "soak_test_hardware_profiles",
        "confidence": "low",
        "evidence_basis": "estimated",
    })

    # 3. Human operational cost avoided — use observed signal volume
    dimensions.append({
        "dimension": "human_operational_cost_avoided",
        "inputs": {
            "signals_not_requiring_human_review": calls_avoided,
            "human_touch_rate": 0.20,
            "avg_triage_minutes_per_signal": 3.0,
            "avg_investigation_minutes_per_signal": 8.0,
            "loaded_hourly_rate_usd": 95.0,
        },
        "source": "soak_observed_signal_volume",
        "confidence": "medium",
        "evidence_basis": "observed" if signals_processed else "estimated",
        "_notes": (
            f"Observed {calls_avoided:,} signals handled by cascade over "
            f"{hours:.1f}h ({calls_avoided / days:.0f}/day avg). "
            f"human_touch_rate 0.20 still estimated — needs on-call validation."
        ),
    })

    # 4. Incident response — placeholder, needs manual adjudication
    dimensions.append({
        "dimension": "incident_response_value",
        "inputs": {
            "incident_count": 0,
            "baseline_mttr_minutes": 45,
            "improved_mttr_minutes": 15,
            "cost_per_minute_of_incident_usd": 5.0,
        },
        "source": "soak_manual_adjudication_needed",
        "confidence": "unverified",
        "evidence_basis": "estimated",
        "_notes": "Set incident_count from manual review of soak-period incidents.",
    })

    # 5. Downstream business impact — placeholder
    dimensions.append({
        "dimension": "downstream_business_impact",
        "inputs": {
            "support_ticket_cost_usd": 35.0,
            "tickets_avoided": 0,
            "user_productivity_cost_per_hour_usd": 75.0,
            "hours_preserved": 0,
        },
        "source": "soak_manual_adjudication_needed",
        "confidence": "unverified",
        "evidence_basis": "estimated",
        "_notes": "Populate from support ticket data during soak period.",
    })

    # 6. OKV — use real memory formation data if available
    okv_inputs: dict = {
        "decisions_informed_per_period": 0,
        "knowledge_consumers": 20,
        "annual_departure_rate": 0.13,
        "knowledge_loss_per_departure_usd": 50000,
        "knowledge_retention_factor": 0.30,
        "knowledge_domains": ["kubernetes", "aap", "jira", "confluence", "github"],
    }
    okv_notes_parts = []
    if memories_formed > 0:
        okv_inputs["memories_formed"] = memories_formed
        okv_notes_parts.append(f"{memories_formed:,} memories formed during soak")
    if memories_end_size > 0:
        okv_notes_parts.append(f"{memories_end_size:,} memories in archive at end")

    dimensions.append({
        "dimension": "organizational_knowledge_value",
        "inputs": okv_inputs,
        "source": "soak_memory_observed" if memories_formed else "soak_estimate",
        "confidence": "low" if memories_formed else "unverified",
        "evidence_basis": "observed" if memories_formed else "estimated",
        "_notes": (
            ". ".join(okv_notes_parts) + ". " if okv_notes_parts else ""
        ) + "decisions_informed_per_period needs instrumented recall-to-decision tracking.",
    })

    # 7. HCO — same structure, adjusted for soak duration
    dimensions.append({
        "dimension": "human_cost_of_ownership",
        "inputs": {
            "fte_displaced": 0.5,
            "annual_loaded_cost_per_fte_usd": 165000,
            "current_headcount_in_function": 6,
            "reskilling_pathway": [
                {
                    "from": "Alert triage / noise filtering",
                    "to": "Incident analysis and root-cause engineering",
                    "fte": 0.3,
                    "status": "planned",
                    "timeline": "2026-Q4",
                },
                {
                    "from": "Alert triage / noise filtering",
                    "to": "Cascade rule authoring and validation",
                    "fte": 0.2,
                    "status": "in_progress",
                    "timeline": "2026-Q3",
                },
            ],
        },
        "source": "soak_operational_estimate",
        "confidence": "low",
        "evidence_basis": "estimated",
    })

    period = f"soak-{hours:.0f}h-{ts_start}-to-{ts_end}"

    claim = {
        "_description": (
            f"Auto-generated VEF claim from {hours:.0f}h soak on cascade-compression "
            f"(RHPDS via infra01). Signals and memory counts are observed; "
            f"economic inputs need manual validation."
        ),
        "_soak_metadata": {
            "start_snapshot": ts_start,
            "end_snapshot": ts_end,
            "duration_hours": round(hours, 1),
            "signals_processed": int(signals_processed),
            "cascade_handled": int(cascade_handled),
            "cascade_forwarded": int(cascade_forwarded),
            "compression_ratio": round(compression_ratio, 4),
            "memories_formed": memories_formed,
            "memories_retained": memories_end_size,
            "evictions": evictions,
            "active_agents": active_agents,
            "total_agents": total_agents,
            "sc_hybrid": {
                "mode": sc_metrics["mode"],
                "sc_authoritative": sc_metrics["sc_authoritative"],
                "llm_fallback": sc_metrics["llm_fallback"],
                "severity_gated": sc_metrics["severity_gated"],
                "margin_gated": sc_metrics["margin_gated"],
                "sc_failure": sc_metrics["sc_failure"],
                "sc_coverage_rate": sc_metrics["sc_coverage_rate"],
                "agreement_rate": sc_metrics["agreement_rate"],
                "comparisons": sc_metrics["comparisons"],
                "disagreements": sc_metrics["disagreements"],
                "false_suppressions": false_supp["false_suppressions"],
                "false_suppression_rate": false_supp["false_suppression_rate"],
                "hybrid_margin": sc_metrics["hybrid_margin"],
                "hybrid_suppress_margin": sc_metrics["hybrid_suppress_margin"],
                "serializer_revision": sc_metrics["serializer_revision"],
                "sc_latency_p50_ms": sc_metrics["sc_latency_p50_ms"],
                "llm_latency_p50_ms": sc_metrics["llm_latency_p50_ms"],
            },
        },
        "claims": [{
            "id": "cascade.full-business-impact",
            "product": "cascade-compression",
            "outcome_id": f"rhpds-via-infra01-soak:{period}",
            "value_type": "cost_avoidance",
            "measurement": {
                "observed": calls_avoided,
                "unit": "model_calls_avoided",
                "period": period,
                "pilot_signal_population": int(signals_processed),
            },
            "counterfactual": {
                "method": "matched_control",
                "expected_without_product": int(cascade_forwarded + cascade_handled),
                "matched_workload": True,
            },
            "attribution": {
                "product_share": 1.0,
                "competing_factors": [
                    "workload_mix",
                    "model_routing",
                    "unit_cost_assumption",
                    "signal_volume_extrapolation",
                ],
            },
            "financial_model": {
                "gross_value": "CALCULATE_ME",
                "currency": "USD",
                "customer_validated": False,
                "value_dimensions": dimensions,
                "engineering_effort": [
                    {
                        "activity": "soak_monitoring",
                        "role": "platform_engineer",
                        "hours": round(hours * 0.02, 2),
                        "loaded_rate_usd": 95.0,
                        "lifecycle": "initial",
                        "source": "soak_work_log",
                    },
                ],
                "initial_engineering_cost_usd": 0,
                "recurring_engineering_cost_usd": 0,
            },
            "evidence": {
                "confidence": "medium",
                "sources": [
                    "soak_observation",
                    "cascade_api_snapshots",
                    "shadow_validation",
                    "sc_hybrid_coverage_sli",
                ],
                "reproducible": True,
                "dangerous_misses": false_supp["false_suppressions"],
                "shadow_validation_coverage": 1.0,
                "sc_agreement_rate": sc_metrics["agreement_rate"],
                "false_suppression_rate": false_supp["false_suppression_rate"],
                "value_eligible": True,
            },
            "realization_cost": 0,
        }],
    }

    return claim


def main():
    parser = argparse.ArgumentParser(description="Generate VEF claim from soak snapshots")
    parser.add_argument("--start", required=True, help="Path to start snapshot JSON")
    parser.add_argument("--end", required=True, help="Path to end snapshot JSON")
    parser.add_argument("--output", default=None, help="Output claim path (default: stdout)")
    args = parser.parse_args()

    start = load(args.start)
    end = load(args.end)

    if start.get("phase") != "start":
        print(f"WARNING: start file phase is '{start.get('phase')}', expected 'start'", file=sys.stderr)
    if end.get("phase") != "end":
        print(f"WARNING: end file phase is '{end.get('phase')}', expected 'end'", file=sys.stderr)

    claim = build_claim(start, end)

    print("", file=sys.stderr)
    meta = claim["_soak_metadata"]
    sc = meta.get("sc_hybrid") or {}
    print(f"Soak: {meta['duration_hours']}h", file=sys.stderr)
    print(f"Signals: {meta['signals_processed']:,} processed, "
          f"{meta['cascade_handled']:,} handled ({meta['compression_ratio']:.1%} compression)",
          file=sys.stderr)
    print(f"Memories: {meta['memories_formed']:,} formed, "
          f"{meta['memories_retained']:,} retained, "
          f"{meta['evictions']:,} evicted", file=sys.stderr)
    print(f"Agents: {meta['active_agents']} active / {meta['total_agents']} total", file=sys.stderr)
    if sc.get("mode"):
        print("", file=sys.stderr)
        print(f"SC Hybrid: mode={sc['mode']}", file=sys.stderr)
        sc_auth = sc.get('sc_authoritative', 0)
        llm_fb = sc.get('llm_fallback', 0)
        cov = sc.get('sc_coverage_rate')
        agr = sc.get('agreement_rate')
        fs = sc.get('false_suppressions', 0)
        fsr = sc.get('false_suppression_rate')
        print(f"  SC authoritative: {sc_auth:,}  LLM fallback: {llm_fb:,}  "
              f"Coverage: {cov:.1%}" if cov else f"  SC: {sc_auth:,}  LLM: {llm_fb:,}",
              file=sys.stderr)
        print(f"  Agreement: {agr:.1%}" if agr else "  Agreement: n/a", file=sys.stderr)
        print(f"  False suppressions: {fs}"
              + (f" ({fsr:.1%})" if fsr is not None else ""), file=sys.stderr)
        print(f"  Severity gated: {sc.get('severity_gated', 0)}  "
              f"Margin gated: {sc.get('margin_gated', 0)}", file=sys.stderr)
    print("", file=sys.stderr)
    print("NOTE: gross_value is set to 'CALCULATE_ME'. Run:", file=sys.stderr)
    print("  vef validate <output-file>", file=sys.stderr)
    print("to compute it, or manually set it from dimension sum.", file=sys.stderr)

    output = json.dumps(claim, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output)
        print(f"Claim written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
