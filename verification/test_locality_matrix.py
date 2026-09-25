#!/usr/bin/env python3
"""Regression tests for manifest-owned locality exclusions (#400)."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import locality_matrix as matrix  # noqa: E402


class LocalityMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = matrix.read_json(matrix.MANIFEST)
        self.indexes = matrix.reference_indexes()

    def test_current_matrix_is_valid(self) -> None:
        self.assertEqual(matrix.validate(self.manifest, self.indexes), [])

    def test_new_valid_exclusion_is_manifest_driven(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        indexes = copy.deepcopy(self.indexes)
        indexes["unit"]["U9999"] = {
            "unitId": "U9999", "language": "Czech", "status": "contradicted"
        }
        manifest["excludedLegacyClaims"].append({
            "unitId": "U9999", "language": "Czech",
            "reason": "Regression fixture for manifest-owned exclusions.",
        })
        self.assertEqual(matrix.validate(manifest, indexes), [])

    def test_duplicate_exclusion_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["excludedLegacyClaims"].append(copy.deepcopy(
            manifest["excludedLegacyClaims"][0]
        ))
        self.assertTrue(any(
            "duplicate excluded legacy claims" in error
            for error in matrix.validate(manifest, self.indexes)
        ))


if __name__ == "__main__":
    unittest.main()
