#!/usr/bin/env python3
"""Regression tests for the source-first adapter loop (#147)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import source_adapters as adapters  # noqa: E402


ADAPTER = {
    "adapterId": "fixture-set-list",
    "adapterVersion": "1.0.0",
    "providerId": "fixture-provider",
    "surfaceId": "fixture-surface",
    "category": "set",
    "endpointTemplate": "https://example.invalid/v2/{rawLocale}/sets",
}
SLICE_EN = {
    "sliceId": "fixture-en",
    "coverageEdgeId": "fixture-edge",
    "rawLocale": "en",
    "locality": "WEST",
    "language": "English",
    "script": "Latn",
}
REQUEST = {
    "runId": "20260809T000000Z",
    "adapterVersion": "1.0.0",
    "providerId": "fixture-provider",
    "surfaceId": "fixture-surface",
    "coverageEdgeId": "fixture-edge",
    "rawLocale": "en",
    "endpoint": "https://example.invalid/v2/en/sets",
    "queryParameters": {"rawLocale": "en", "resource": "sets"},
    "retrievedAt": "2026-08-09T00:00:00Z",
    "responseHash": "sha256:fixture",
}


class SourceAdapterTests(unittest.TestCase):
    def normalize(self, source_record, slice_row=SLICE_EN, duplicate_occurrence=None):
        errors = []
        row = adapters.normalize_record(
            ADAPTER, slice_row, REQUEST, source_record, {}, errors, duplicate_occurrence
        )
        return row, errors

    def test_locale_and_suffix_survive_without_automatic_merge(self):
        english, _ = self.normalize({
            "id": "SVP-F", "name": "Promo F", "releaseDate": "2026-08-01"
        })
        german_slice = {**SLICE_EN, "sliceId": "fixture-de", "rawLocale": "de", "language": "German"}
        german, _ = self.normalize({
            "id": "SVP-F", "name": "Promo F", "releaseDate": "2026-09-12"
        }, german_slice)
        self.assertEqual(english["raw"]["localCode"], "SVP-F")
        self.assertNotEqual(english["stableKey"], german["stableKey"])
        self.assertEqual(english["normalizationProposal"]["releaseDate"], "2026-08-01")
        self.assertEqual(german["normalizationProposal"]["releaseDate"], "2026-09-12")
        self.assertFalse(english["normalizationProposal"]["crossLocaleMerge"])
        self.assertIsNone(english["normalizationProposal"]["target"])

    def test_same_locale_provider_id_collision_is_parked_but_not_dropped(self):
        first, first_errors = self.normalize(
            {"id": "CSV1C", "name": "亘古开来"}, duplicate_occurrence=1
        )
        second, second_errors = self.normalize(
            {"id": "CSV1C", "name": "宝石包 第一卷"}, duplicate_occurrence=2
        )
        self.assertNotEqual(first["stableKey"], second["stableKey"])
        self.assertEqual(first["rawProviderId"], second["rawProviderId"])
        self.assertEqual(first["bucket"], "ambiguous/needs-evidence")
        self.assertEqual(second["bucket"], "ambiguous/needs-evidence")
        self.assertEqual(first_errors + second_errors, [])

    def test_release_precision_and_source_native_text_round_trip(self):
        row, errors = self.normalize({
            "id": "SET-F",
            "name": "ローカルセット F",
            "releaseDate": "2026-08",
            "finishProfileText": "Rare Holo except the explicitly listed deck cards.",
            "finishProfileSection": "Rarity",
            "finishProfileRevision": "12345",
            "finishProfileClauses": [
                {"verbatim": "Rare Holo", "disposition": "mapped"},
                {
                    "verbatim": "except the explicitly listed deck cards",
                    "disposition": "needs-evidence",
                },
            ],
            "finishProfileUnparsedText": "",
        })
        proposal = row["normalizationProposal"]
        self.assertEqual(proposal["releaseDate"], "2026-08")
        self.assertEqual(proposal["releaseDatePrecision"], "month")
        self.assertEqual(proposal["finishProfile"]["verbatim"], row["sourceRecord"]["finishProfileText"])
        self.assertEqual(proposal["finishProfile"]["disposition"], "needs-evidence")
        self.assertEqual(row["bucket"], "ambiguous/needs-evidence")
        self.assertEqual(errors, [])

    def test_silently_unparsed_finish_clause_is_a_run_error(self):
        row, errors = self.normalize({
            "id": "SET1",
            "name": "Set One",
            "finishProfileText": "Rare Holo except deck cards.",
            "finishProfileSection": "Rarity",
            "finishProfileRevision": "12345",
            "finishProfileClauses": [{"verbatim": "Rare Holo", "disposition": "mapped"}],
            "finishProfileUnparsedText": "except deck cards",
        })
        self.assertEqual(row["bucket"], "ambiguous/needs-evidence")
        self.assertIn("silently-unparsed-finish-clause", {error["code"] for error in errors})

    def test_empty_catalogue_is_needs_evidence_with_exact_accounting(self):
        contract = {
            "meta": {"coverageVersion": "test"},
            "adapters": [{**ADAPTER, "slices": [SLICE_EN]}],
            "explicitMappings": [],
            "gaps": [],
        }
        raw = b"[]"
        manifest = {
            "runId": "20260809T000000Z",
            "coverageVersion": "test",
            "contractHash": adapters.content_hash(contract),
            "capabilityGraphHash": "sha256:capability",
            "failures": [],
            "requests": [{
                **REQUEST,
                "adapterId": ADAPTER["adapterId"],
                "sliceId": SLICE_EN["sliceId"],
                "rawPath": "raw/sets.json",
                "responseHash": adapters.content_hash(raw),
                "recordCount": 0,
                "checkpoint": {"page": 1, "nextCursor": None, "complete": True},
                "error": None,
            }],
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "raw").mkdir()
            (run_dir / "raw" / "sets.json").write_bytes(raw)
            projection = adapters.build_projection(contract, manifest, run_dir, None)
        self.assertEqual(projection["slices"][0]["terminalState"], "needs-evidence")
        self.assertEqual(projection["slices"][0]["accounting"]["fetched"], 0)
        self.assertEqual(projection["slices"][0]["accounting"]["accounted"], 0)
        self.assertEqual(projection["runErrors"][0]["code"], "empty-catalogue")

    def test_diff_surfaces_rekeys_without_merging_them(self):
        old, _ = self.normalize({"id": "OLD", "name": "Stable Set"})
        new, _ = self.normalize({"id": "NEW", "name": "Stable Set"})
        diff = adapters.diff_records([new], [old])
        self.assertEqual(diff["counts"], {
            "added": 0, "changed": 0, "disappeared": 0, "rekeyedCandidates": 1
        })
        self.assertEqual(diff["rekeyedCandidates"][0]["from"], old["stableKey"])
        self.assertEqual(diff["rekeyedCandidates"][0]["to"], new["stableKey"])

    def test_incomplete_pagination_is_a_run_error(self):
        contract = {
            "meta": {"coverageVersion": "test"},
            "adapters": [{**ADAPTER, "slices": [SLICE_EN]}],
            "explicitMappings": [],
            "gaps": [],
        }
        raw = json.dumps([{"id": "SET1", "name": "Set One"}]).encode("utf-8")
        manifest = {
            "runId": "20260809T000000Z",
            "coverageVersion": "test",
            "contractHash": adapters.content_hash(contract),
            "capabilityGraphHash": "sha256:capability",
            "failures": [],
            "requests": [{
                **REQUEST,
                "adapterId": ADAPTER["adapterId"],
                "sliceId": SLICE_EN["sliceId"],
                "rawPath": "raw/sets.json",
                "responseHash": adapters.content_hash(raw),
                "recordCount": 1,
                "checkpoint": {"page": 1, "nextCursor": "page-2", "complete": False},
                "error": None,
            }],
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "raw").mkdir()
            (run_dir / "raw" / "sets.json").write_bytes(raw)
            projection = adapters.build_projection(contract, manifest, run_dir, None)
        self.assertEqual(projection["slices"][0]["terminalState"], "needs-evidence")
        self.assertIn("incomplete-pagination", {row["code"] for row in projection["runErrors"]})


if __name__ == "__main__":
    unittest.main()
