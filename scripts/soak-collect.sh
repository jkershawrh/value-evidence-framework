#!/usr/bin/env bash
#
# VEF Soak Collection Script
#
# Snapshots cascade API state at the start and end of a soak period.
# Run once at T=0, then again at T=72h. The script produces timestamped
# JSON snapshots that feed into soak-to-claim.py to generate a VEF claim.
#
# Usage:
#   export CASCADE_K8S_URL=https://cascade-k8s-cascade-compression.apps.ocpv-infra01.dal12.infra.demo.redhat.com
#   export CASCADE_MEMORY_URL=https://cascade-memory-cascade-compression.apps.ocpv-infra01.dal12.infra.demo.redhat.com
#
#   # At soak start:
#   ./scripts/soak-collect.sh start
#
#   # At soak end (72h later):
#   ./scripts/soak-collect.sh end
#
#   # Generate claim from both snapshots:
#   python scripts/soak-to-claim.py

set -euo pipefail

PHASE="${1:-}"
if [[ "$PHASE" != "start" && "$PHASE" != "end" ]]; then
    echo "Usage: $0 <start|end>"
    echo "  start  — collect baseline snapshot at soak start"
    echo "  end    — collect final snapshot at soak end"
    exit 1
fi

CASCADE_K8S_URL="${CASCADE_K8S_URL:?Set CASCADE_K8S_URL to the cascade-k8s route}"
CASCADE_MEMORY_URL="${CASCADE_MEMORY_URL:-}"

OUTDIR="$(cd "$(dirname "$0")/.." && pwd)/soak-data"
mkdir -p "$OUTDIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
SNAPSHOT="$OUTDIR/snapshot-${PHASE}-${TS}.json"

echo "=== VEF Soak Collection: $PHASE at $TS ==="

fetch() {
    local label="$1" url="$2"
    echo "  Fetching $label ..."
    local result
    if result=$(curl -sf --connect-timeout 10 --max-time 30 "$url" 2>/dev/null); then
        echo "$result"
    else
        echo "  WARNING: $label failed (url: $url)" >&2
        echo "null"
    fi
}

{
    echo "{"
    echo "  \"phase\": \"$PHASE\","
    echo "  \"timestamp\": \"$TS\","
    echo "  \"cascade_k8s_url\": \"$CASCADE_K8S_URL\","

    # Cascade stats (signal counts, compression, AI calls)
    echo "  \"stats\": $(fetch 'cascade stats' "$CASCADE_K8S_URL/stats"),"

    # Classifier stats (comparison metrics)
    echo "  \"classifier_stats\": $(fetch 'classifier stats' "$CASCADE_K8S_URL/classifier/stats"),"

    # Agent status
    echo "  \"agents\": $(fetch 'agents' "$CASCADE_K8S_URL/agents"),"

    # Health
    echo "  \"health\": $(fetch 'health' "$CASCADE_K8S_URL/health"),"

    # Memory stats (if memory URL is set)
    if [[ -n "$CASCADE_MEMORY_URL" ]]; then
        echo "  \"cascade_memory_url\": \"$CASCADE_MEMORY_URL\","
        echo "  \"memory_stats\": $(fetch 'memory stats' "$CASCADE_MEMORY_URL/memories/stats"),"
        echo "  \"memory_search_stats\": $(fetch 'memory search stats' "$CASCADE_MEMORY_URL/memories/search/stats"),"
        echo "  \"biography\": $(fetch 'biography' "$CASCADE_MEMORY_URL/biography"),"
    else
        echo "  \"cascade_memory_url\": null,"
        echo "  \"memory_stats\": null,"
        echo "  \"memory_search_stats\": null,"
        echo "  \"biography\": null,"
    fi

    echo "  \"_collected\": \"$TS\""
    echo "}"
} > "$SNAPSHOT"

echo ""
echo "Snapshot written to: $SNAPSHOT"
echo ""

if [[ "$PHASE" == "start" ]]; then
    echo "Soak started. Run this again with 'end' after 72 hours:"
    echo "  $0 end"
elif [[ "$PHASE" == "end" ]]; then
    START_FILE=$(ls -t "$OUTDIR"/snapshot-start-*.json 2>/dev/null | head -1)
    if [[ -n "$START_FILE" ]]; then
        echo "Start snapshot: $START_FILE"
        echo "End snapshot:   $SNAPSHOT"
        echo ""
        echo "Generate the VEF claim:"
        echo "  python scripts/soak-to-claim.py --start '$START_FILE' --end '$SNAPSHOT'"
    else
        echo "WARNING: No start snapshot found in $OUTDIR"
        echo "  Run '$0 start' first, then '$0 end' after the soak period."
    fi
fi
