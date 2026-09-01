"""Read-only, deterministic repository evidence-readiness inspection."""

from __future__ import annotations

import ast
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "vef.readiness.v1alpha1"
MAX_FILE_BYTES = 1_000_000
GENERATED_PARTS = {".git", ".venv", "venv", "node_modules", "dist", "build",
                   "local-evidence", "__pycache__"}


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    points: int
    terms: tuple[str, ...]
    missing: str
    falsification: str
    needs_test: bool = False


RULES = (
    Rule("BDD-001", "BDD", 10, ("outcome_id", "period", "total_signals"),
         "Define a bounded, customer-observable outcome and measured population.",
         "No executable contract binds the outcome, period, and population."),
    Rule("EDD-001", "EDD", 10, ("timestamp", "source", "unknown"),
         "Capture timestamped provenance and preserve unknown measurements.",
         "Evidence records cannot distinguish observed, missing, and asserted values."),
    Rule("EDD-002", "EDD", 10, ("false_negative", "dropped", "reproducible"),
         "Record quality failures, dropped work, and reproducibility metadata.",
         "Safety or collection failures are absent from validated evidence."),
    Rule("CDD-001", "CDD", 10, ("schema_version", "validate", "value_evidence"),
         "Add a versioned, validated VEF export contract.",
         "The exporter and its compatibility contract are not tested together.", True),
    Rule("CBT-001", "CBT", 10, ("baseline", "workload_digest", "total_signals"),
         "Add an independently observed baseline matched to the measured population.",
         "Baseline and treatment populations cannot be reconciled.", True),
    Rule("CBT-002", "CBT", 10, ("counterfactual", "competing_factors", "method"),
         "Record the comparison method and competing explanations.",
         "The no-product world or alternative explanations are not represented."),
    Rule("SAFE-001", "Safety", 10,
         ("product_share", "dangerous_misses", "value_eligible"),
         "Fail financial claims closed on safety failures and constrain attribution.",
         "Unsafe outcomes or shared value can still produce an uncapped claim.", True),
    Rule("ECON-001", "Economics", 10,
         ("actual_ai_calls", "input_tokens", "inference_cost_usd"),
         "Measure actual AI participation, tokens, and inference cost.",
         "Compression is used without measured AI consumption."),
    Rule("ECON-002", "Economics", 10,
         ("engineering_effort", "recurring", "loaded_rate_usd"),
         "Capture initial and recurring ruleset/engineering effort at loaded rates.",
         "Realization cost omits bounded engineering effort."),
    Rule("TDD-001", "TDD", 10, ("negative", "replay", "deterministic"),
         "Test negative value, deterministic replay, and reproducible reporting.",
         "The calculation can only demonstrate favorable or non-reproducible results.", True),
)

CATEGORY_MAX = {"BDD": 10, "EDD": 20, "CDD": 10, "CBT": 20,
                "Safety": 10, "Economics": 20, "TDD": 10}


def load_policy(path: str) -> dict[str, Any]:
    """Load the deliberately small, non-scoring inspect policy format."""
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"inspection policy not found: {source}")
    text = source.read_text()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = _simple_yaml(text)
    if not isinstance(value, dict):
        raise TypeError("inspection policy must be a mapping")
    allowed = {"exporters", "evidence_schemas", "test_commands", "ignore_paths"}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"unknown inspection policy keys: {', '.join(sorted(unknown))}")
    for key, item in value.items():
        if not isinstance(item, list) or not all(isinstance(v, str) for v in item):
            raise ValueError(f"inspection policy {key} must be a list of strings")
        if key != "test_commands" and any(Path(v).is_absolute() or ".." in Path(v).parts
                                          for v in item):
            raise ValueError(f"inspection policy {key} paths must stay within the repository")
    return value


def _simple_yaml(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    current: str | None = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "-")) and line.endswith(":"):
            current = line[:-1].strip()
            result[current] = []
        elif current and line.lstrip().startswith("- "):
            result[current].append(line.lstrip()[2:].strip().strip("'\""))
        else:
            raise ValueError(f"invalid inspection policy YAML at line {number}")
    return result


def _tracked_files(repo: Path, ignored: set[str]) -> list[Path]:
    try:
        proc = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], check=True,
                              capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise ValueError(f"not a readable git repository: {repo}") from exc
    paths = []
    for raw in proc.stdout.split(b"\0"):
        if not raw:
            continue
        rel = Path(raw.decode("utf-8", errors="surrogateescape"))
        if any(part in GENERATED_PARTS for part in rel.parts):
            continue
        if any(rel == Path(item) or Path(item) in rel.parents for item in ignored):
            continue
        full = repo / rel
        if full.is_symlink() or not full.is_file() or full.stat().st_size > MAX_FILE_BYTES:
            continue
        paths.append(rel)
    return sorted(paths, key=lambda p: p.as_posix())


def _symbols(path: Path) -> dict[str, list[int]]:
    try:
        raw = path.read_bytes()
        if b"\0" in raw:
            return {}
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    found: dict[str, list[int]] = {}
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return {}
        for node in ast.walk(tree):
            values: list[str] = []
            if isinstance(node, (ast.Name, ast.Attribute)):
                values.append(node.id if isinstance(node, ast.Name) else node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                values.append(node.value)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                values.append(node.name)
            for value in values:
                for token in _tokens(value):
                    found.setdefault(token, []).append(getattr(node, "lineno", 1))
    elif path.suffix == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return {}
        def walk(item: Any) -> None:
            if isinstance(item, dict):
                for key, child in item.items():
                    for token in _tokens(str(key)):
                        found.setdefault(token, []).append(1)
                    walk(child)
            elif isinstance(item, list):
                for child in item:
                    walk(child)
        walk(value)
    return found


def _tokens(value: str) -> set[str]:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    pieces = {p for p in normalized.split("_") if len(p) > 2}
    pieces.add(normalized)
    return pieces


def _revision(repo: Path) -> str:
    proc = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True)
    return proc.stdout.strip()


def inspect_repository(path: str | Path, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(path).resolve()
    if not repo.is_dir():
        raise ValueError(f"repository not found: {repo}")
    policy = policy or {}
    ignored = set(policy.get("ignore_paths", []))
    files = _tracked_files(repo, ignored)
    index: dict[str, list[dict[str, Any]]] = {}
    test_tokens: set[str] = set()
    for rel in files:
        symbols = _symbols(repo / rel)
        is_test = any(part in {"test", "tests"} or part.startswith("test_") for part in rel.parts)
        for token, lines in symbols.items():
            ref = {"path": rel.as_posix(), "line": min(lines), "kind": "structural"}
            index.setdefault(token, []).append(ref)
            if is_test:
                test_tokens.add(token)

    findings = []
    category_scores = {name: 0 for name in CATEGORY_MAX}
    for rule in RULES:
        matched = [term for term in rule.terms if term in index]
        test_ok = not rule.needs_test or any(term in test_tokens for term in rule.terms)
        passed = len(matched) == len(rule.terms) and test_ok
        refs = []
        for term in matched:
            refs.extend(index[term][:1])
        refs = sorted({(r["path"], r["line"]): r for r in refs}.values(),
                      key=lambda r: (r["path"], r["line"]))
        status = "met" if passed else ("partial" if matched else "missing")
        awarded = rule.points if passed else 0
        category_scores[rule.category] += awarded
        findings.append({"id": rule.id, "category": rule.category, "criterion": rule.id,
                         "status": status, "severity": "info" if passed else "high",
                         "points_awarded": awarded, "points_available": rule.points,
                         "evidence": refs, "missing_capability": None if passed else rule.missing,
                         "falsification_condition": rule.falsification})

    safety_warnings = _safety_warnings(index)
    raw_score = sum(category_scores.values())
    caps: list[tuple[int, str]] = []
    if not any(f["id"].startswith("CBT") and f["status"] == "met" for f in findings):
        caps.append((49, "no counterfactual structure"))
    if next(f for f in findings if f["id"] == "SAFE-001")["status"] != "met":
        caps.append((49, "no validated safety/failure structure"))
    if next(f for f in findings if f["id"] == "ECON-002")["status"] != "met":
        caps.append((69, "no realization-cost structure"))
    if safety_warnings:
        caps.append((49, "sensitive payload fields in evidence/report structures"))
    score = min([raw_score, *(cap for cap, _ in caps)])
    rating = "green" if score >= 80 else "amber" if score >= 50 else "red"
    proof_state = _proof_state(findings, safety_warnings)
    cost_plus = _cost_plus_state(index)
    categories = [{"id": name, "score": category_scores[name], "max_score": maximum}
                  for name, maximum in CATEGORY_MAX.items()]
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": {"name": repo.name, "revision": _revision(repo)},
        "grade": {"score": score, "rating": rating, "raw_score": raw_score,
                  "caps": [{"maximum": cap, "reason": reason} for cap, reason in sorted(caps)]},
        "proof_state": proof_state, "cost_plus_state": cost_plus,
        "categories": categories, "findings": findings,
        "implementation_options": _implementation_options(findings, safety_warnings),
        "safety_warnings": safety_warnings,
        "disclaimer": "Repository structure indicates readiness; it is not proof of realized value.",
    }


def _safety_warnings(index: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    sensitive = {"signal_content", "customer_payload", "raw_payload", "secret_value"}
    warnings = []
    for token in sorted(sensitive & set(index)):
        refs = [r for r in index[token] if any(word in r["path"].lower()
                for word in ("evidence", "report", "export", "scorecard"))]
        if refs:
            warnings.append({"id": "DATA-001", "severity": "critical",
                             "message": "Sensitive payload field appears in an evidence/report structure.",
                             "evidence": refs[:3]})
    # A signal payload persisted in a memory/evidence record is sensitive even when its
    # contract represents the two fields separately. Only paths and field names influence this.
    paths = {token: {r["path"] for r in refs} for token, refs in index.items()}
    signal_paths = paths.get("signal", set()) | paths.get("signal_type", set())
    content_paths = paths.get("content", set())
    persistence_paths: set[str] = set()
    for token in ("memory_id", "archive", "persisted", "jsonl", "evidence"):
        persistence_paths |= paths.get(token, set())
    raw_paths = sorted(signal_paths & content_paths & persistence_paths)
    if raw_paths and not warnings:
        refs = []
        for path in raw_paths[:3]:
            candidates = [r for r in index.get("content", []) if r["path"] == path]
            refs.append(candidates[0] if candidates else {"path": path, "line": 1,
                                                          "kind": "structural"})
        warnings.append({"id": "DATA-001", "severity": "critical",
                         "message": "Raw signal content appears in a persisted evidence/memory structure.",
                         "evidence": refs})
    return warnings


def _proof_state(findings: list[dict[str, Any]], safety_warnings: list[dict[str, Any]]) -> str:
    met = {f["id"] for f in findings if f["status"] == "met"}
    if not safety_warnings and {"CBT-001", "SAFE-001", "ECON-001", "TDD-001"} <= met:
        return "decision-grade"
    if met & {"EDD-001", "CDD-001", "CBT-001"}:
        return "directional"
    return "unproven"


def _cost_plus_state(index: dict[str, list[dict[str, Any]]]) -> str:
    required = {"recurring", "marginal_cost", "automation_rate", "time_to_value", "cohort"}
    if not required <= set(index):
        return "unknown"
    risk = {"per_customer_hours", "manual_report"} & set(index)
    return "risk" if risk else "scalable"


def _implementation_options(findings: list[dict[str, Any]],
                            safety_warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps = [f["id"] for f in findings if f["status"] != "met"]
    gaps.extend(warning["id"] for warning in safety_warnings)
    if not gaps:
        return []
    if safety_warnings and not any(f["status"] != "met" for f in findings):
        return [
            {"level": "minimum", "title": "Minimum privacy structure", "addresses": gaps,
             "changes": ["Exclude raw payload fields from ROI exports and document retention."]},
            {"level": "recommended", "title": "Privacy-safe persistence", "addresses": gaps,
             "changes": ["Persist hashes and approved aggregates; migrate and expire raw evidence."]},
            {"level": "advanced", "title": "Automated privacy governance", "addresses": gaps,
             "changes": ["Enforce field allowlists, retention controls, and privacy contract tests."]},
        ]
    return [
        {"level": "minimum", "title": "Minimum evidence structure", "addresses": gaps,
         "changes": ["Add versioned aggregate evidence fields and validation tests."]},
        {"level": "recommended", "title": "Pilot-ready structure", "addresses": gaps,
         "changes": ["Add a bounded usage ledger, independent baseline, safety gates, and effort ledger."]},
        {"level": "advanced", "title": "Automated portfolio structure", "addresses": gaps,
         "changes": ["Automate sanitized evidence receipts, cohort economics, and portfolio exports."]},
    ]


def render_inspection_markdown(report: dict[str, Any]) -> str:
    grade = report["grade"]
    lines = [f"# ROI Evidence Readiness — {report['repository']['name']}", "",
             f"**{grade['rating'].upper()} — {grade['score']}/100**",
             f"Proof state: **{report['proof_state']}**  ",
             f"Cost-plus state: **{report['cost_plus_state']}**", "",
             report["disclaimer"], "", "## Category scores", ""]
    for category in report["categories"]:
        lines.append(f"- {category['id']}: {category['score']}/{category['max_score']}")
    lines += ["", "## Evidence gaps", ""]
    gaps = [f for f in report["findings"] if f["status"] != "met"]
    if gaps:
        lines.extend(f"- **{f['id']} ({f['status']}):** {f['missing_capability']}" for f in gaps)
    else:
        lines.append("- None in the structural rubric.")
    if report["safety_warnings"]:
        lines += ["", "## Safety warnings", ""]
        lines.extend(f"- **{w['id']}:** {w['message']}" for w in report["safety_warnings"])
    lines += ["", "## Implementation options", ""]
    for option in report["implementation_options"]:
        lines.append(f"- **{option['title']}:** {option['changes'][0]}")
    return "\n".join(lines) + "\n"
