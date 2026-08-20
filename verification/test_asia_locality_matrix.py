#!/usr/bin/env python3
"""Regression tests for the #238 Asian locality terminal matrix."""

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
