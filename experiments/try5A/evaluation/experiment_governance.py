"""Deterministic governance primitives for RobotCAD paper experiments."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EVIDENCE_TYPES = {"computed", "copied", "asserted", "inferred"}


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _diff_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if isinstance(left, dict) and isinstance(right, dict):
        result = []
        for key in sorted(set(left) | set(right)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in left or key not in right:
                result.append(path)
            else:
                result.extend(_diff_paths(left[key], right[key], path))
        return result
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return [prefix]
        result = []
        for index, (a, b) in enumerate(zip(left, right)):
            result.extend(_diff_paths(a, b, f"{prefix}[{index}]"))
        return result
    return [] if left == right else [prefix]


def audit_condition_parity(config: dict) -> dict:
    conditions = config["conditions"]
    names = list(conditions)
    if len(names) != 2:
        raise ValueError("paired ablation requires exactly two conditions")
    differences = _diff_paths(conditions[names[0]], conditions[names[1]])
    allowed = set(config["allowed_condition_differences"])
    unexpected = [path for path in differences if path not in allowed]
    missing = sorted(allowed - set(differences))
    return {
        "status": "PASS" if not unexpected and not missing else "FAIL",
        "conditions": names,
        "shared_sha256": canonical_hash(config["shared"]),
        "observed_differences": differences,
        "allowed_differences": sorted(allowed),
        "unexpected_differences": unexpected,
        "declared_but_equal": missing,
    }

def split_cases(case_ids: list[str], split_config: dict) -> dict:
    unique = sorted(set(case_ids))
    if len(unique) != len(case_ids):
        raise ValueError("case IDs must be unique")
    development_count = int(split_config["development_count"])
    holdout_count = int(split_config["holdout_count"])
    if development_count + holdout_count != len(unique):
        raise ValueError("split counts must preserve the full denominator")
    salt = split_config["salt"]
    ranked = sorted(unique, key=lambda item: hashlib.sha256(f"{salt}|{item}".encode()).hexdigest())
    development = ranked[:development_count]
    holdout = ranked[development_count:]
    payload = {
        "schema_version": "robotcad_case_split_v1",
        "method": split_config["method"],
        "salt": salt,
        "source_case_count": len(unique),
        "source_case_ids_sha256": canonical_hash(sorted(unique)),
        "development": {
            "count": len(development),
            "case_ids": development,
            "case_ids_sha256": canonical_hash(development),
        },
        "holdout": {
            "count": len(holdout),
            "case_ids": holdout,
            "case_ids_sha256": canonical_hash(holdout),
            "locked": True,
            "evaluation_limit_per_condition": int(split_config["holdout_evaluation_limit_per_condition"]),
        },
    }
    payload["split_sha256"] = canonical_hash(payload)
    return payload


def evaluate_mechanical_gates(metrics: dict, thresholds: dict) -> dict:
    checks = {
        "artifact_valid": bool(metrics.get("artifact_valid")) is bool(thresholds["artifact_valid"]),
        "bicr": float(metrics.get("bicr", -1)) >= float(thresholds["bicr_min"]),
        "physical_floating_count": int(metrics.get("physical_floating_count", 10**9)) <= int(thresholds["physical_floating_count_max"]),
        "forbidden_fusion_count": int(metrics.get("forbidden_fusion_count", 10**9)) <= int(thresholds["forbidden_fusion_count_max"]),
        "virtual_solid_count": int(metrics.get("virtual_solid_count", 10**9)) <= int(thresholds["virtual_solid_count_max"]),
        "meaningless_patch_count": int(metrics.get("meaningless_patch_count", 10**9)) <= int(thresholds["meaningless_patch_count_max"]),
        "relevant_jr3": float(metrics.get("relevant_jr3", -1)) >= float(thresholds["relevant_jr3_min"]),
        "gcfr_regression": float(metrics.get("gcfr_regression", float("inf"))) <= float(thresholds["gcfr_regression_max"]),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed_gates": [name for name, passed in checks.items() if not passed],
    }


@dataclass(frozen=True)
class CandidateDecision:
    condition: str
    previous_candidate: str | None
    proposed_candidate: str
    selected_candidate: str | None
    outcome: str
    mechanical_status: str
    failed_gates: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "condition": self.condition,
            "previous_candidate": self.previous_candidate,
            "proposed_candidate": self.proposed_candidate,
            "selected_candidate": self.selected_candidate,
            "outcome": self.outcome,
            "mechanical_status": self.mechanical_status,
            "failed_gates": list(self.failed_gates),
        }


class CandidateController:
    """Make a real runtime accept/reject/rollback decision from computed metrics."""

    def __init__(self, condition: str, policy: dict, thresholds: dict):
        self.condition = condition
        self.policy = dict(policy)
        self.thresholds = dict(thresholds)
        self.events: list[dict] = []

    def decide(self, previous_candidate: str | None, proposed_candidate: str, metrics: dict) -> CandidateDecision:
        gate = evaluate_mechanical_gates(metrics, self.thresholds)
        if gate["status"] == "PASS":
            selected, outcome = proposed_candidate, "ACCEPT"
        elif not self.policy["mechanical_rejection"]:
            selected, outcome = proposed_candidate, "ACCEPT_WITH_MECHANICAL_FAILURE"
        elif self.policy["rollback_on_failure"] and previous_candidate is not None:
            selected, outcome = previous_candidate, "ROLLBACK"
        else:
            selected, outcome = None, "REJECT"
        decision = CandidateDecision(
            condition=self.condition,
            previous_candidate=previous_candidate,
            proposed_candidate=proposed_candidate,
            selected_candidate=selected,
            outcome=outcome,
            mechanical_status=gate["status"],
            failed_gates=tuple(gate["failed_gates"]),
        )
        self.events.append({**decision.as_dict(), "metrics_sha256": canonical_hash(metrics)})
        return decision


def resolve_field(payload: Any, dotted_path: str) -> Any:
    current = payload
    for token in dotted_path.split("."):
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "eq":
        return actual == expected
    if operator == "ge":
        return actual >= expected
    if operator == "le":
        return actual <= expected
    raise ValueError(f"unsupported claim operator: {operator}")


def validate_claim_ledger(result_root: str | Path, claims: list[dict]) -> dict:
    root = Path(result_root)
    rows = []
    for claim in claims:
        evidence_type = claim["evidence_type"]
        if evidence_type not in EVIDENCE_TYPES:
            raise ValueError(f"unknown evidence type: {evidence_type}")
        artifact = root / claim["artifact"]
        actual = None
        error = None
        if not artifact.is_file():
            error = "artifact_missing"
        else:
            try:
                actual = resolve_field(load_json(artifact), claim["field"])
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                error = f"field_error:{type(exc).__name__}"
        direct = evidence_type == "computed"
        value_pass = error is None and compare(actual, claim["operator"], claim["expected"])
        hard_pass = value_pass and (direct or not claim.get("hard", False))
        rows.append({
            "claim_id": claim["claim_id"],
            "hard": bool(claim.get("hard", False)),
            "evidence_type": evidence_type,
            "direct_computed_evidence": direct,
            "artifact": claim["artifact"],
            "artifact_sha256": file_sha256(artifact) if artifact.is_file() else None,
            "field": claim["field"],
            "actual": actual,
            "operator": claim["operator"],
            "expected": claim["expected"],
            "error": error,
            "status": "PASS" if hard_pass else "FAIL",
        })
    return {
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "claims": rows,
        "hard_claims_with_noncomputed_evidence": [row["claim_id"] for row in rows if row["hard"] and not row["direct_computed_evidence"]],
    }
