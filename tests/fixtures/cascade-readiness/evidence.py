"""Synthetic structural mirror; contains no deployment or customer evidence."""

ROUTE_LEDGER_FIELDS = [
    "schema_version", "value_evidence", "validate", "baseline", "workload_digest",
    "total_signals", "actual_ai_calls", "input_tokens", "inference_cost_usd",
    "engineering_effort", "recurring", "loaded_rate_usd", "false_negative", "dropped",
    "reproducible", "outcome_id", "period", "timestamp", "source", "unknown",
    "product_share", "dangerous_misses", "value_eligible",
]

PERSISTED_MEMORY_FIELDS = ["memory_id", "signal_type", "content"]
