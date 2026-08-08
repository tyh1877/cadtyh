from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from compile_blueprint import compile_cadir, compile_direct  # noqa: E402
from robot_blueprint import BlueprintError, validate_blueprint  # noqa: E402


def fixture() -> dict:
    return {
        "schema_version": "1.0", "units": "mm",
        "links": [
            {"name": "base", "primitives": [
                {"type": "box", "center": [0, 0, 25], "size": [100, 80, 50]}
            ]},
            {"name": "arm", "primitives": [
                {"type": "cylinder", "center": [0, 0, 100], "radius": 20,
                 "height": 200, "axis": [0, 0, 2]}
            ]},
        ],
        "joints": [{
            "name": "joint_1", "parent": "base", "child": "arm",
            "type": "revolute", "origin_xyz": [0, 0, 50],
            "origin_rpy": [0, 0, 0], "axis": [0, 0, 5],
            "lower": -3.14, "upper": 3.14,
        }],
    }


class RobotBlueprintTests(unittest.TestCase):
    def test_validation_normalizes_axes(self) -> None:
        value = validate_blueprint(fixture(), expected_links=2, expected_joints=1, expected_dof=1)
        self.assertEqual(value["joints"][0]["axis"], [0.0, 0.0, 1.0])
        self.assertEqual(value["links"][1]["primitives"][0]["axis"], [0.0, 0.0, 1.0])

    def test_wrong_dof_is_rejected(self) -> None:
        value = fixture()
        value["joints"][0]["type"] = "fixed"
        with self.assertRaisesRegex(BlueprintError, "actuated DOF"):
            validate_blueprint(value, expected_links=2, expected_joints=1, expected_dof=1)

    def test_both_compilers_write_meshes_and_urdf(self) -> None:
        for compiler in (compile_direct, compile_cadir):
            with self.subTest(compiler=compiler.__name__), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)
                blueprint = validate_blueprint(
                    fixture(), expected_links=2, expected_joints=1, expected_dof=1
                )
                urdf = compiler(blueprint, output)
                self.assertTrue(urdf.is_file())
                self.assertEqual(len(list((output / "meshes").glob("*.stl"))), 2)
                if compiler is compile_cadir:
                    self.assertEqual(len(list((output / "step").glob("*.step"))), 2)
                    self.assertEqual(len(list((output / "cadir_graphs").glob("*.model.json"))), 2)


if __name__ == "__main__":
    unittest.main()
