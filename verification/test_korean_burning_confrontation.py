#!/usr/bin/env python3
"""Regression tests for the reviewed Korean BS2 identity in issue #240."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "verification" / "passes"))

import admit_korean_burning_confrontation_20260820 as korean  # noqa: E402


class KoreanBurningConfrontationTests(unittest.TestCase):
    def test_reviewed_snapshot_is_exact(self) -> None:
        snapshot = korean.read_evidence()
        self.assertEqual(snapshot["identity"], korean.IDENTITY)

    def test_catalogue_code_drift_is_rejected(self) -> None:
        snapshot = korean.read_evidence()
        mutated = copy.deepcopy(snapshot)
        row = next(item for item in mutated["observations"]
                   if item["observationId"] == "KR-DALDAGURY-BS2-30")
        row["observed"]["localSetCode"] = "DP2"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(mutated, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "observed drifted"):
                korean.read_evidence(path)

    def test_store_has_one_resolved_specimen_release(self) -> None:
        source_first = json.loads(korean.PRINTS.read_text(encoding="utf-8"))
        matches = [row for row in source_first["prints"]
                   if row["printId"] == korean.ADMITTED_ENTRY["printId"]]
        self.assertEqual(matches, [korean.ADMITTED_ENTRY])
        self.assertFalse(any(row["specimenId"] == "SPEC-0037"
                             for row in source_first.get("held", [])))
        specimens = json.loads(korean.SPECIMENS.read_text(encoding="utf-8"))["specimens"]
        specimen = next(row for row in specimens if row["specimenId"] == "SPEC-0037")
        self.assertEqual(specimen["setCode"], "BS2")
        self.assertNotIn("finish", korean.ADMITTED_ENTRY)
        self.assertIsNone(korean.ADMITTED_ENTRY["catchUpOf"])


if __name__ == "__main__":
    unittest.main()
