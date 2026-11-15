"""Active catalogue totals and the owner-closed Italian KSS gallery regression."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build import quality_summary


class SummaryTests(unittest.TestCase):
    def test_active_totals_keep_retained_items_and_legacy_accounting(self):
        items = [
            {"active": active, "itemKind": kind, "progressClass": progress,
             "legacyChecklistIds": [str(index)], "cardReleaseId": str(index),
             "physicalPrintingId": str(index) if kind == "verified-printing" else None}
            for index, (active, kind, progress) in enumerate([
                (True, "verified-printing", "current-known"),
                (True, "finish-candidate", "research"),
                (False, "verified-printing", "current-known"),
                (False, "finish-candidate", "research")])]
        document = {name: [] for name in ("localizations", "localSets", "setEditions", "works", "assets")}
        document["items"] = items
        for active in (True, False):
            for item in items[:2]:
                item["active"] = active
            summary = quality_summary({"predecessor": {}}, document)
            self.assertEqual(summary["counts"], {
                "localizations": 0, "localSets": 0, "setEditions": 0, "works": 0, "items": 4,
                "activeItems": 2 * active, "inactiveItems": 4 - 2 * active,
                "verifiedPrintings": int(active), "finishCandidates": int(active),
                "researchPlaceholders": 0, "currentKnown": int(active), "research": int(active), "assets": 0})
            self.assertEqual(summary["graphAccounting"], {"cardReleases": 2 * active,
                                                        "physicalPrintings": int(active)})
            self.assertEqual(summary["legacyCompatibility"]["counts"]["legacyRows"], 4)
            self.assertEqual(len(document["items"]), 4)

    def test_italian_kss_wave_hypothesis_respects_closed_finish_list(self):
        images = json.loads((ROOT / "data/images.json").read_text(encoding="utf-8"))
        owner = json.loads((ROOT / "verification/owner_adjudications.json").read_text(encoding="utf-8"))
        decision = next(row for row in owner["finishDecisions"]
                        if row["adjudicationId"] == "OAF-20261101-KSS-26-it")
        self.assertEqual(decision["availableFinishes"], ["non-holo"])
        self.assertNotIn("research-kss-26-it-wave-holo", {row["id"] for row in images["placeholders"]})


if __name__ == "__main__":
    unittest.main()
