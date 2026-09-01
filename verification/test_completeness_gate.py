#!/usr/bin/env python3
"""Mutation tests for the #141 bounded completeness gate."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import completeness_gate as gate  # noqa: E402


class CompletenessGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = gate.read_json(gate.SOURCE_STAGING)
        self.card = gate.read_json(gate.CARD_STAGING)
        self.asia = gate.read_json(gate.ASIA_MATRIX)
        self.locality = gate.read_json(gate.LOCALITY_MATRIX)

    def test_current_inputs_pass(self) -> None:
        _, errors = gate.validate_inputs()
        self.assertEqual(errors, [])

    def test_korean_historical_gap_survives_summary(self) -> None:
        inputs, errors = gate.validate_inputs()
        self.assertEqual(errors, [])
        gaps = {row["id"]: row for row in gate.summary(inputs)["gaps"]}
        self.assertEqual(
            gaps["official-korean-historical-positive-frontier"]["state"],
            "needs-evidence",
        )

    def test_missing_svqp_regression_fails(self) -> None:
        mutated = copy.deepcopy(self.asia)
        mutated["minimumRegressions"] = [
            row for row in mutated["minimumRegressions"]
            if row["regressionId"] != "tw-svqp-f-012"
        ]
        errors = gate.validate_regressions(mutated)
        self.assertTrue(any("minimum-regression set differs" in error for error in errors))

    def test_collapsed_latam_boundary_fails(self) -> None:
        mutated = copy.deepcopy(self.locality)
        next(row for row in mutated["tracks"] if row["trackId"] == "latam-es")["locality"] = "WEST"
        errors = gate.validate_boundaries(mutated)
        self.assertTrue(any("latam-es locality boundary changed" in error for error in errors))

    def test_set_only_card_confirmation_fails(self) -> None:
        rows = [json.loads(line) for line in gate.CARD_RECORDS.read_text(encoding="utf-8").splitlines()]
        rows[0]["sourceRecord"].pop("detailId")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.jsonl"
            path.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )
            errors = gate.validate_card_records(path)
        self.assertTrue(any("is not card-level" in error for error in errors))

    def test_zero_result_provider_fails_closed(self) -> None:
        mutated = copy.deepcopy(self.source)
        mutated["slices"][0]["accounting"]["fetched"] = 0
        errors = gate.validate_staging(mutated, "set-discovery")
        self.assertTrue(any("zero-result complete slice" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
