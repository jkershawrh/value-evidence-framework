"""Synthetic structural mirror; contains no deployment or customer evidence."""

ROUTE_LEDGER_FIELDS = [
    "schema_version", "value_evidence", "validate", "baseline", "workload_digest",
    "total_signals", "actual_ai_calls", "input_tokens", "inference_cost",
    "engineering_effort", "recurring", "loaded_rate", "false_negative", "dropped",
    "reproducible", "outcome_id", "period", "timestamp", "source", "unknown",
    "product_share", "dangerous_miss", "financial",
]

PERSISTED_MEMORY_FIELDS = ["memory_id", "signal_type", "content"]
