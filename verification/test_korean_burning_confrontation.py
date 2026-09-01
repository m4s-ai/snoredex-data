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
        self.assertNotIn("officialProviderSetId", snapshot["identity"])

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

    def test_capability_fixture_retains_the_indexed_publisher_fields(self) -> None:
        manifest = json.loads(
            (ROOT / "verification" / "source_capabilities.json").read_text(encoding="utf-8")
        )
        observation = next(row for row in manifest["observations"]
                           if row["observationId"] ==
                           "obs-pokemon-card-korea-bs2010002030")
        self.assertEqual(observation["fixtureRef"]["kind"], "inline-record")
        record = observation["fixtureRef"]["record"]
        self.assertEqual(record["providerRecordId"], "BS2010002030")
        self.assertEqual(record["cardName"], "잠만보 Lv. 35")
        self.assertEqual(record["collectorNumber"], "30/40")
        self.assertEqual(record["localSetName"], "불꽃 튀는 대결")
        self.assertFalse(record["absenceCapability"])
        self.assertFalse(record["finishCapability"])

    def test_store_has_one_resolved_specimen_release(self) -> None:
        source_first = json.loads(korean.PRINTS.read_text(encoding="utf-8"))
        matches = [row for row in source_first["prints"]
                   if row["printId"] == korean.ADMITTED_ENTRY["printId"]]
        self.assertEqual(len(matches), 1)
        admitted = matches[0]
        for field in (
            "printId", "locality", "localSetCode", "localNumber", "variant",
            "language", "script", "name", "cardName", "catchUpOf", "specimenId",
            "providerId", "providerRecordId", "catalogueSetId", "localSetName",
            "sourceUrl", "corroborated", "markAssetUrl",
        ):
            self.assertEqual(admitted[field], korean.ADMITTED_ENTRY[field])
        self.assertEqual(
            admitted["cardImageUrl"],
            "https://cards.image.pokemonkorea.co.kr/data/wmimages/DP/BS2/bs2_kr_30.jpg?w=512",
        )
        self.assertEqual(admitted["illustrator"], "Ken Sugimori")
        self.assertEqual(admitted["hp"], "HP100")
        self.assertEqual(admitted["localProductName"], "DP 확장팩 불꽃 튀는 대결")
        self.assertTrue(set(korean.ADMITTED_ENTRY["corroboratingSourceUrls"]) <=
                        set(admitted["corroboratingSourceUrls"]))
        self.assertFalse(any(row["specimenId"] == "SPEC-0037"
                             for row in source_first.get("held", [])))
        specimens = json.loads(korean.SPECIMENS.read_text(encoding="utf-8"))["specimens"]
        specimen = next(row for row in specimens if row["specimenId"] == "SPEC-0037")
        self.assertEqual(specimen["setCode"], "BS2")
        self.assertNotIn("finish", korean.ADMITTED_ENTRY)
        self.assertNotIn("providerSetId", korean.ADMITTED_ENTRY)
        self.assertIsNone(korean.ADMITTED_ENTRY["catchUpOf"])


if __name__ == "__main__":
    unittest.main()
