import json
import subprocess
from pathlib import Path

import jsonschema

from value_evidence.inspector import inspect_repository, load_policy, render_inspection_markdown


def repo(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "product"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=VEF",
                    "-c", "user.email=vef@example.invalid", "commit", "-qm", "fixture"], check=True)
    return root


def test_empty_repository_is_red_and_unproven(tmp_path):
    result = inspect_repository(repo(tmp_path, {"README.md": "baseline tokens safety"}))
    assert result["grade"]["score"] == 0
    assert result["grade"]["rating"] == "red"
    assert result["proof_state"] == "unproven"


def test_comments_and_filenames_do_not_award_points(tmp_path):
    root = repo(tmp_path, {"baseline_counterfactual.py":
        "# baseline workload_digest total_signals\n# dangerous_miss product_share financial\n"})
    result = inspect_repository(root)
    assert result["grade"]["raw_score"] == 0


def test_pilot_ready_structure_is_green(tmp_path):
    fields = [term for rule in __import__("value_evidence.inspector", fromlist=["RULES"]).RULES
              for term in rule.terms]
    source = "FIELDS = " + repr(fields + ["marginal_cost", "automation_rate", "time_to_value", "cohort"])
    tests = "def test_negative_replay_is_deterministic():\n    value_evidence = validate = baseline = workload_digest = total_signals = dangerous_miss = product_share = financial = True\n"
    result = inspect_repository(repo(tmp_path, {"evidence.py": source, "tests/test_evidence.py": tests}))
    assert result["grade"]["score"] == 100
    assert result["grade"]["rating"] == "green"
    assert result["cost_plus_state"] == "scalable"


def test_unknown_is_not_zero_and_realization_cost_caps_grade(tmp_path):
    fields = ["outcome_id", "period", "total_signals", "timestamp", "source", "unknown",
              "false_negative", "dropped", "reproducible", "schema_version", "validate",
              "value_evidence", "baseline", "workload_digest", "counterfactual",
              "competing_factors", "method", "product_share", "dangerous_miss", "financial",
              "actual_ai_calls", "input_tokens", "inference_cost", "negative", "replay",
              "deterministic"]
    tests = "def test_contract():\n    baseline = workload_digest = total_signals = validate = value_evidence = dangerous_miss = product_share = financial = negative = replay = deterministic = True\n"
    result = inspect_repository(repo(tmp_path, {"model.py": "FIELDS=" + repr(fields),
                                                "tests/test_model.py": tests}))
    assert result["cost_plus_state"] == "unknown"
    assert result["grade"]["score"] <= 69


def test_sensitive_report_field_warns_without_copying_value(tmp_path):
    secret = "do-not-copy-this-customer-value"
    result = inspect_repository(repo(tmp_path, {"evidence/export.py":
        f"FIELDS = ['signal_content']\nVALUE = '{secret}'\n"}))
    serialized = json.dumps(result)
    assert result["safety_warnings"][0]["severity"] == "critical"
    assert secret not in serialized
    assert result["grade"]["score"] <= 49


def test_cascade_shaped_fixture_flags_persisted_content_and_economic_gaps(tmp_path):
    fixture = Path(__file__).parent / "fixtures/cascade-readiness/evidence.py"
    tests = "def test_contract():\n    baseline = workload_digest = total_signals = validate = value_evidence = True\n"
    root = repo(tmp_path, {"cascade/evidence.py": fixture.read_text(),
                           "tests/test_contract.py": tests})
    result = inspect_repository(root)
    assert result["safety_warnings"][0]["id"] == "DATA-001"
    assert next(f for f in result["findings"] if f["id"] == "ECON-001")["status"] == "met"
    assert result["cost_plus_state"] == "unknown"
    assert result["proof_state"] != "decision-grade"
    assert "DATA-001" in result["implementation_options"][1]["addresses"]
    assert result["implementation_options"][1]["title"] == "Privacy-safe persistence"


def test_ignored_and_untracked_files_are_not_inspected(tmp_path):
    root = repo(tmp_path, {"README.md": "safe"})
    (root / "untracked.py").write_text("signal_content = 'private'")
    result = inspect_repository(root)
    assert result["safety_warnings"] == []


def test_policy_is_non_scoring_and_markdown_has_disclaimer(tmp_path):
    policy = tmp_path / "inspect.yaml"
    policy.write_text("exporters:\n  - src/export.py\nignore_paths:\n  - vendor\n")
    assert load_policy(str(policy))["exporters"] == ["src/export.py"]
    result = inspect_repository(repo(tmp_path / "r", {"src/export.py": "FIELDS=[]"}),
                                policy=load_policy(str(policy)))
    assert "not proof of realized value" in render_inspection_markdown(result)


def test_report_matches_public_schema(tmp_path):
    result = inspect_repository(repo(tmp_path, {"model.py": "FIELDS=[]"}))
    schema = json.loads((Path(__file__).parents[1] /
                         "schemas/readiness-report.v1alpha1.json").read_text())
    jsonschema.validate(result, schema)


def test_agent_skill_preserves_authoritative_grade_and_is_read_only():
    skill = (Path(__file__).parents[1] /
             "skills/roi-evidence-readiness/SKILL.md").read_text()
    assert "Preserve the CLI's score" in skill
    assert "Work read-only" in skill
    assert "must not implement changes" in skill
