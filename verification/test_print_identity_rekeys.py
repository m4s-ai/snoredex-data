#!/usr/bin/env python3
"""Regression tests for many-to-many reviewed work relationships (#236)."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import print_identity_dryrun as identity  # noqa: E402


class RekeyRelationshipTests(unittest.TestCase):
    def test_many_to_many_relationships_remain_distinct(self) -> None:
        cards = identity.read_json(ROOT / "snorlax_cards.json")["cards"]
        units = identity.read_json(ROOT / "verification" / "units.json")
        finish_units = identity.read_json(
            ROOT / "verification" / "finish_units.json")["units"]
        excluded = identity.read_json(ROOT / "verification" / "excluded_codecards.json")
        specimens = identity.read_json(
            ROOT / "verification" / "specimens.json")["specimens"]
        baseline = identity.read_json(ROOT / "legacy-cardmarket-baseline.json")
        source_first = identity.read_json(
            ROOT / "verification" / "source_first_prints.json")
        rekeys = copy.deepcopy(identity.read_json(
            ROOT / "verification" / "legacy_issue_rekeys.json"))

        as5a = next(entry for entry in source_first["prints"]
                     if entry["printId"] == "TW:AS5a:142:base")
        as5a_v2 = {**as5a, "printId": "TW:AS5a:142:V2", "variant": "V2"}
        source_first["prints"].append(as5a_v2)

        template = rekeys["questionSets"][0]["mappings"][0]
        rekeys["questionSets"][0]["mappings"] = [
            {**template, "legacyUnitId": "U0382",
             "sourceFirstRecordId": "TW:AS5a:142:base"},
            {**template, "legacyUnitId": "U0665",
             "sourceFirstRecordId": "TW:AS5a:142:base"},
            {**template, "legacyUnitId": "U0382",
             "sourceFirstRecordId": "TW:AS5a:142:V2"},
            {**template, "legacyUnitId": "U0382",
             "sourceFirstRecordId": "TW:sc1a F:127/154:base"},
        ]

        result = identity.build(
            cards, units, finish_units, excluded, specimens, baseline, source_first, rekeys)
        releases = {
            source_id: release
            for release in result["cardReleases"]
            for source_id in release.get("sourceFirstRecordIds", [])
        }
        rows = {
            row["legacyUnitId"]: row
            for row in result["reports"]["legacyIssueRekeys"][0]["rows"]
        }

        self.assertEqual(
            releases["TW:AS5a:142:base"]["legacyCounterpartUnitIds"],
            ["U0382", "U0665"],
        )
        self.assertIs(
            releases["TW:AS5a:142:base"], releases["TW:AS5a:142:V2"])
        self.assertEqual(
            len(releases["TW:AS5a:142:base"]["establishingClaimIds"]), 2)
        self.assertEqual(len(rows["U0382"]["sourceFirstRecordIds"]), 3)
        self.assertEqual(len(rows["U0665"]["sourceFirstRecordIds"]), 1)
        self.assertEqual(len(result["equivalenceAssertions"]), 4)

        invalid_mappings = (
            ({**template, "assertionType": "same-work-proposal"},
             "not a reviewed decision"),
            ({**template, "evidence": " "}, "lacks positive evidence"),
        )
        for invalid_mapping, message in invalid_mappings:
            with self.subTest(message=message):
                invalid_rekeys = copy.deepcopy(rekeys)
                invalid_rekeys["questionSets"][0]["mappings"] = [invalid_mapping]
                with self.assertRaisesRegex(ValueError, message):
                    identity.build(
                        cards, units, finish_units, excluded, specimens,
                        baseline, source_first, invalid_rekeys)


if __name__ == "__main__":
    unittest.main()
