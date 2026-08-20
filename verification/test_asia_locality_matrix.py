#!/usr/bin/env python3
"""Regression tests for the #238 matrix and #241 relationship hardening."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import asia_locality_matrix as matrix  # noqa: E402


class AsiaLocalityMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = matrix.read_json(matrix.MANIFEST)
        self.data = matrix.indexes(self.manifest)

    def test_current_matrix_is_valid(self) -> None:
        self.assertEqual(matrix.validate(self.manifest, self.data), [])

    def test_missing_track_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.manifest)
        mutated["tracks"].pop()
        self.assertTrue(any(
            "track universe differs" in error
            for error in matrix.validate(mutated, matrix.indexes(mutated))
        ))

    def test_unbalanced_complete_slice_is_rejected(self) -> None:
        data = copy.deepcopy(self.data)
        data["card-slice"]["pokemon-asia-id-snorlax"]["accounting"]["accounted"] -= 1
        self.assertTrue(any(
            "does not balance" in error
            for error in matrix.validate(self.manifest, data)
        ))

    def test_gap_cannot_masquerade_as_positive_node(self) -> None:
        mutated = copy.deepcopy(self.manifest)
        regression = next(
            item for item in mutated["minimumRegressions"]
            if item["regressionId"] == "cn-sv9-075"
        )
        regression["evidenceRefs"] = ["gap:official-asia-kr-cn"]
        regression["expectedPrints"] = []
        self.assertTrue(any(
            "positive-node lacks its required evidence kind" in error
            for error in matrix.validate(mutated, matrix.indexes(mutated))
        ))

    def test_positive_node_must_match_declared_print_identity(self) -> None:
        mutated = copy.deepcopy(self.manifest)
        regression = next(
            item for item in mutated["minimumRegressions"]
            if item["regressionId"] == "id-sv9s-i-109"
        )
        wrong_ref = "source-first:TW:SV-P:215:base"
        regression["evidenceRefs"] = [wrong_ref]
        regression["expectedPrints"][0]["reference"] = wrong_ref
        self.assertTrue(any(
            "identity differs" in error
            for error in matrix.validate(mutated, matrix.indexes(mutated))
        ))

    def test_unit_positive_node_requires_an_established_materialized_claim(self) -> None:
        data = copy.deepcopy(self.data)
        claim = data["unit-claim"]["U0761"][0]
        claim["disposition"] = "candidate-needs-evidence"
        claim["materializedTargetId"] = None
        self.assertTrue(any(
            "unit:U0761 does not materialize an established release" in error
            for error in matrix.validate(self.manifest, data)
        ))

    def test_unit_release_must_match_the_declared_positive_node(self) -> None:
        mutated = copy.deepcopy(self.manifest)
        regression = next(
            item for item in mutated["minimumRegressions"]
            if item["regressionId"] == "cn-sv9-075"
        )
        regression["expectedPrints"][0]["materializedTargetId"] = (
            "RELEASE:TW:T-Chinese:via-sv9:unknown-local-set:via-075:"
            "Hops-Snorlax-Extra-Helpings-Dynamic-Press:unknown-local-id"
        )
        self.assertTrue(any(
            "unit:U0761 materializes" in error
            for error in matrix.validate(mutated, matrix.indexes(mutated))
        ))

    def test_same_work_rejects_changes_to_either_unit(self) -> None:
        for unit_id in ("U0761", "U0371"):
            with self.subTest(unit_id=unit_id):
                data = copy.deepcopy(self.data)
                data["unit"][unit_id]["cardKey"] = "Different-Work"
                self.assertTrue(any(
                    f"unit:{unit_id} cardKey differs from expected work" in error
                    for error in matrix.validate(self.manifest, data)
                ))

    def test_same_work_rejects_changes_to_either_release_mapping(self) -> None:
        for unit_id in ("U0761", "U0371"):
            with self.subTest(unit_id=unit_id):
                data = copy.deepcopy(self.data)
                claim = data["unit-claim"][unit_id][0]
                data["release"][claim["materializedTargetId"]]["work"] = "Different-Work"
                self.assertTrue(any(
                    f"unit:{unit_id} release work differs" in error
                    for error in matrix.validate(self.manifest, data)
                ))

    def test_rekey_must_match_declared_relationship(self) -> None:
        mutated = copy.deepcopy(self.manifest)
        regression = next(
            item for item in mutated["minimumRegressions"]
            if item["regressionId"] == "tw-as5a-142"
        )
        regression["expectedRekeys"][0]["sourceFirstRecordId"] = "TW:SV-P:215:base"
        self.assertTrue(any(
            "relationship differs" in error
            for error in matrix.validate(mutated, matrix.indexes(mutated))
        ))


if __name__ == "__main__":
    unittest.main()
