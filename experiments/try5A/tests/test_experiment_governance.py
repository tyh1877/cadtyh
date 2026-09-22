from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

EVALUATION = Path(__file__).resolve().parents[1] / "evaluation"
sys.path.insert(0, str(EVALUATION))

from experiment_governance import (  # noqa: E402
    CandidateController,
    acquire_holdout_lock,
    audit_condition_parity,
    canonical_hash,
    dump_json,
    file_sha256,
    split_cases,
    validate_claim_ledger,
)
from validate_experiment import validate_bundle  # noqa: E402


def config_fixture():
    return {
        "experiment_id": "fixture",
        "shared": {
            "split": {
                "method": "sha256_rank_v1",
                "salt": "fixture-salt",
                "development_count": 3,
                "holdout_count": 1,
                "holdout_evaluation_limit_per_condition": 1,
            },
            "mechanical_thresholds": {
                "artifact_valid": True,
                "bicr_min": 1.0,
                "physical_floating_count_max": 0,
                "forbidden_fusion_count_max": 0,
                "virtual_solid_count_max": 0,
                "meaningless_patch_count_max": 0,
                "relevant_jr3_min": 1.0,
                "gcfr_regression_max": 0.0,
            },
        },
        "conditions": {
            "C1_CONSTRAINED": {
                "mechanical_policy": {
                    "protected_interface_cuts": True,
                    "mechanical_rejection": True,
                    "rollback_on_failure": True,
                }
            },
            "C2_UNCONSTRAINED": {
                "mechanical_policy": {
                    "protected_interface_cuts": False,
                    "mechanical_rejection": False,
                    "rollback_on_failure": False,
                }
            },
        },
        "allowed_condition_differences": [
            "mechanical_policy.protected_interface_cuts",
            "mechanical_policy.mechanical_rejection",
            "mechanical_policy.rollback_on_failure",
        ],
    }


def failing_metrics():
    return {
        "artifact_valid": True,
        "bicr": 0.5,
        "physical_floating_count": 1,
        "forbidden_fusion_count": 0,
        "virtual_solid_count": 0,
        "meaningless_patch_count": 0,
        "relevant_jr3": 0.8,
        "gcfr_regression": 0.1,
    }


class GovernanceTests(unittest.TestCase):
    def test_split_is_deterministic_disjoint_and_complete(self):
        config = config_fixture()
        first = split_cases(["c0", "c1", "c2", "c3"], config["shared"]["split"])
        second = split_cases(["c3", "c2", "c1", "c0"], config["shared"]["split"])
        self.assertEqual(first, second)
        self.assertFalse(set(first["development"]["case_ids"]) & set(first["holdout"]["case_ids"]))
        self.assertEqual(first["source_case_count"], 4)

    def test_parity_allows_only_declared_policy_differences(self):
        config = config_fixture()
        self.assertEqual(audit_condition_parity(config)["status"], "PASS")
        config["conditions"]["C2_UNCONSTRAINED"]["seed"] = 99
        audit = audit_condition_parity(config)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("seed", audit["unexpected_differences"])

    def test_runtime_controller_rolls_back_constrained_candidate(self):
        config = config_fixture()
        condition = config["conditions"]["C1_CONSTRAINED"]
        controller = CandidateController("C1_CONSTRAINED", condition["mechanical_policy"], config["shared"]["mechanical_thresholds"])
        decision = controller.decide("F1", "F2", failing_metrics())
        self.assertEqual(decision.outcome, "ROLLBACK")
        self.assertEqual(decision.selected_candidate, "F1")
        self.assertTrue(controller.events)

    def test_runtime_controller_accepts_unconstrained_failure(self):
        config = config_fixture()
        condition = config["conditions"]["C2_UNCONSTRAINED"]
        controller = CandidateController("C2_UNCONSTRAINED", condition["mechanical_policy"], config["shared"]["mechanical_thresholds"])
        decision = controller.decide("F1", "F2", failing_metrics())
        self.assertEqual(decision.outcome, "ACCEPT_WITH_MECHANICAL_FAILURE")
        self.assertEqual(decision.selected_candidate, "F2")

    def test_asserted_evidence_cannot_close_hard_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump_json(root / "metrics.json", {"bicr": 1.0})
            audit = validate_claim_ledger(root, [{
                "claim_id": "bicr",
                "hard": True,
                "evidence_type": "asserted",
                "artifact": "metrics.json",
                "field": "bicr",
                "operator": "eq",
                "expected": 1.0,
            }])
            self.assertEqual(audit["status"], "FAIL")
            self.assertEqual(audit["hard_claims_with_noncomputed_evidence"], ["bicr"])

    def _write_bundle(self, root: Path, config_path: Path, holdout_events=2):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        split = split_cases(["c0", "c1", "c2", "c3"], config["shared"]["split"])
        parity = audit_condition_parity(config)
        dump_json(root / "experiment_config_snapshot.json", config)
        dump_json(root / "case_split.json", split)
        dump_json(root / "condition_parity.json", parity)
        dump_json(root / "failure_accounting.json", {"conditions": [
            {"condition": name, "requested_cases": 4, "completed_cases": 3, "failed_cases": 1}
            for name in config["conditions"]
        ]})
        condition_names = list(config["conditions"])
        events = [{"condition": name, "followed_by_tuning": False} for name in condition_names]
        if holdout_events > 2:
            events.append({"condition": condition_names[0], "followed_by_tuning": False})
        dump_json(root / "holdout_evaluation_log.json", {"events": events})
        dump_json(root / "metrics.json", {"bicr": 1.0})
        dump_json(root / "claim_ledger.json", {"claims": [{
            "claim_id": "bicr",
            "hard": True,
            "evidence_type": "computed",
            "artifact": "metrics.json",
            "field": "bicr",
            "operator": "eq",
            "expected": 1.0,
        }]})
        dump_json(root / "manifest.json", {
            "config_file_sha256": file_sha256(config_path),
            "config_canonical_sha256": canonical_hash(config),
            "case_split_sha256": split["split_sha256"],
        })

    def test_independent_validator_passes_complete_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            dump_json(config_path, config_fixture())
            result_root = root / "results"
            result_root.mkdir()
            self._write_bundle(result_root, config_path)
            self.assertEqual(validate_bundle(result_root, config_path)["status"], "PASS")

    def test_independent_validator_rejects_holdout_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            dump_json(config_path, config_fixture())
            result_root = root / "results"
            result_root.mkdir()
            self._write_bundle(result_root, config_path, holdout_events=3)
            result = validate_bundle(result_root, config_path)
            self.assertEqual(result["status"], "FAIL")
            self.assertFalse(result["checks"]["holdout_phase_correct"])

    def test_development_validator_requires_unused_holdout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.json"
            dump_json(config_path, config_fixture())
            result_root = root / "results"
            result_root.mkdir()
            self._write_bundle(result_root, config_path)
            dump_json(result_root / "holdout_evaluation_log.json", {"events": []})
            dump_json(result_root / "failure_accounting.json", {"conditions": [
                {"condition": name, "requested_cases": 3, "completed_cases": 3, "failed_cases": 0}
                for name in config_fixture()["conditions"]
            ]})
            self.assertEqual(validate_bundle(result_root, config_path, "development")["status"], "PASS")

    def test_holdout_lock_is_one_shot(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "holdout.lock"
            acquire_holdout_lock(lock, "fixture", "abc")
            with self.assertRaises(FileExistsError):
                acquire_holdout_lock(lock, "fixture", "abc")


if __name__ == "__main__":
    unittest.main()
