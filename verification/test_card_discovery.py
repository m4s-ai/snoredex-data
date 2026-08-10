#!/usr/bin/env python3
"""Regression tests for the source-first card discovery loop (#136)."""

from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import card_discovery as discovery  # noqa: E402


ADAPTER = {
    "adapterId": "fixture-native-name",
    "adapterVersion": "1.0.0",
    "providerId": "fixture-provider",
    "surfaceId": "fixture-surface",
    "listEndpointTemplate": "https://example.invalid/{rawLocale}/cards",
    "detailEndpointTemplate": "https://example.invalid/{rawLocale}/cards/{rawProviderId}",
    "category": "card",
    "pageParameter": "pageNo",
    "pageSize": 20,
}
SLICE_TW = {
    "sliceId": "fixture-tw",
    "coverageEdgeId": "fixture-edge",
    "rawLocale": "tw",
    "locality": "TW",
    "language": "T-Chinese",
    "script": "Hant",
    "nameQueries": ["卡比獸"],
    "positiveNameExclusions": [{
        "prefix": "小卡比獸", "identity": "Munchlax",
        "reason": "source-native name identifies Munchlax",
    }],
}
REQUEST = {
    "runId": "20260809T000000Z",
    "retrievedAt": "2026-08-09T00:00:00Z",
    "queryParameters": {"nameQueries": ["卡比獸"]},
    "pages": [{"responseHash": "sha256:list"}],
    "details": [{"rawProviderId": "13148", "responseHash": "sha256:detail"}],
}
SVQP_ASSERTION = {
    "providerId": "fixture-provider",
    "surfaceId": "fixture-surface",
    "rawLocale": "tw",
    "rawSetCode": "SVQP",
    "assertedLocalSetCode": "svQP F",
    "assetUrl": "https://example.invalid/SVQP.png",
    "evidence": "official symbol visibly reads svQP F",
}


def source_record(**overrides):
    row = {
        "detailId": "13148",
        "localName": "卡比獸",
        "rawSetCode": "SVQP",
        "localCollectorNumber": "012/023",
        "cardImageUrl": "https://example.invalid/card.png",
        "setSymbolUrl": "https://example.invalid/SVQP.png",
        "productScope": "physical-tcg",
    }
    row.update(overrides)
    return row


class CardDiscoveryTests(unittest.TestCase):
    def normalize(self, record=None, releases=None, mappings=None, assertions=None, slice_row=None):
        return discovery.normalize_record(
            ADAPTER,
            slice_row or SLICE_TW,
            REQUEST,
            record or source_record(),
            releases or [],
            mappings or {},
            assertions or {
                discovery.raw_key("fixture-provider", "fixture-surface", "tw", "SVQP"):
                    SVQP_ASSERTION
            },
        )

    def test_official_html_parser_preserves_set_code_and_collector_suffix(self):
        raw = """
        <h1 class="pageHeader cardDetail"><span class="evolveMarker">基礎</span>卡比獸</h1>
        <img src="https://example.invalid/tw/card-img/tw00013148.png">
        <section class="expansionColumn"><span class="expansionSymbol">
          <img src="https://asia.pokemon-card.com/tw/card-img/mark/twhk_exp_SVQP.png">
        </span><span class="alpha">H</span>
        <span class="collectorNumber">012/023</span></section>
        <a href="/tw/card-search/list/?expansionCodes=SVQP">ex初階牌組 皮卡丘</a>
        """.encode()
        parsed = discovery.parse_detail(raw, "13148")
        self.assertEqual(parsed["localName"], "卡比獸")
        self.assertEqual(parsed["rawSetCode"], "SVQP")
        self.assertEqual(parsed["localCollectorNumber"], "012/023")

    def test_missing_svqp_identity_enters_as_new_candidate_without_identifier_loss(self):
        row = self.normalize()
        self.assertEqual(row["bucket"], "new-candidate")
        self.assertEqual(row["raw"]["rawSetCode"], "SVQP")
        self.assertEqual(
            row["normalizationProposal"]["assertedLocalSetCode"], "svQP F"
        )
        self.assertEqual(
            row["normalizationProposal"]["localCollectorNumber"], "012/023"
        )
        self.assertIsNone(row["normalizationProposal"]["targetCardReleaseId"])

    def test_exact_local_tuple_matches_without_an_equivalence_merge(self):
        release = {
            "cardReleaseId": "RELEASE:TW:T-Chinese:svQP F:012/023:work",
            "locality": "TW", "language": "T-Chinese",
            "localSetCode": "svQP F", "localNumber": "012/023",
        }
        row = self.normalize(releases=[release])
        self.assertEqual(row["bucket"], "matched")
        self.assertEqual(row["normalizationProposal"]["targetCardReleaseId"], release["cardReleaseId"])
        self.assertFalse(row["normalizationProposal"]["destructiveMergeAllowed"])

    def test_changed_number_creates_proposal_and_never_overwrites_target(self):
        release = {
            "cardReleaseId": "RELEASE:TW:T-Chinese:svQP F:012:work",
            "locality": "TW", "language": "T-Chinese",
            "localSetCode": "svQP F", "localNumber": "012",
        }
        key = discovery.raw_key("fixture-provider", "fixture-surface", "tw", "13148")
        row = self.normalize(releases=[release], mappings={key: {
            "mode": "equivalence-proposal",
            "targetCardReleaseId": release["cardReleaseId"],
            "evidence": "same inspected work; local number changed and needs review",
        }})
        proposal = row["normalizationProposal"]
        self.assertEqual(row["bucket"], "ambiguous")
        self.assertIsNone(proposal["targetCardReleaseId"])
        self.assertEqual(proposal["equivalenceProposals"][0]["targetCardReleaseId"], release["cardReleaseId"])
        self.assertFalse(proposal["equivalenceProposals"][0]["destructiveMergeAllowed"])

    def test_same_provider_id_in_two_localities_stays_traceable(self):
        tw = self.normalize()
        hk_slice = {**SLICE_TW, "rawLocale": "hk", "locality": "HK"}
        hk_request = {
            **REQUEST,
            "details": [{"rawProviderId": "13148", "responseHash": "sha256:detail-hk"}],
        }
        hk = discovery.normalize_record(
            ADAPTER, hk_slice, hk_request, source_record(), [], {}, {}
        )
        self.assertNotEqual(tw["stableKey"], hk["stableKey"])
        self.assertEqual(tw["rawProviderId"], hk["rawProviderId"])
        self.assertFalse(tw["normalizationProposal"]["destructiveMergeAllowed"])
        self.assertFalse(hk["normalizationProposal"]["destructiveMergeAllowed"])

    def test_source_native_pocket_record_is_positively_excluded(self):
        row = self.normalize(record=source_record(productScope="digital-pocket"))
        self.assertEqual(row["bucket"], "positively-excluded")
        self.assertIn("Pocket", row["bucketBasis"])

    def test_native_name_false_positive_is_excluded_by_positive_identity(self):
        row = self.normalize(record=source_record(localName="小卡比獸"))
        self.assertEqual(row["bucket"], "positively-excluded")
        self.assertIn("Munchlax", row["bucketBasis"])

    def test_zero_result_is_source_failure_not_absence(self):
        raw = b"""
        <p class="resultNumber">0</p>
        <p class="resultTotalPages">/ 1</p>
        """
        contract = {
            "meta": {"coverageVersion": "test"},
            "adapters": [{**ADAPTER, "slices": [SLICE_TW]}],
            "setCodeAssertions": [], "explicitMappings": [], "gaps": [],
        }
        capability = {"fixture": True}
        manifest = {
            "runId": "20260809T000000Z",
            "coverageVersion": "test",
            "contractHash": discovery.content_hash(contract),
            "capabilityGraphHash": discovery.capability_pin(capability),
            "failures": [],
            "requests": [{
                "runId": "20260809T000000Z",
                "adapterId": ADAPTER["adapterId"],
                "sliceId": SLICE_TW["sliceId"],
                "endpoint": "https://example.invalid/tw/cards",
                "queryParameters": {"nameQueries": ["卡比獸"]},
                "retrievedAt": "2026-08-09T00:00:00Z",
                "pages": [{
                    "query": "卡比獸", "pageNo": 1, "rawPath": "raw/page-1.html",
                    "responseHash": discovery.content_hash(raw),
                    "resultCount": 0, "totalPages": 1, "detailIds": [],
                }],
                "details": [], "assets": [],
                "checkpoint": {"complete": True}, "error": None,
            }],
        }
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            (run_dir / "raw").mkdir()
            (run_dir / "raw" / "page-1.html").write_bytes(raw)
            projection = discovery.build_projection(
                contract, capability, {"cardReleases": []}, manifest, run_dir, None
            )
        self.assertEqual(projection["slices"][0]["terminalState"], "needs-evidence")
        self.assertEqual(projection["slices"][0]["sourceFailureState"], "source-failed")
        self.assertEqual(projection["runErrors"][0]["code"], "zero-result")
        self.assertNotIn("absent", projection["slices"][0]["terminalMeaning"])


if __name__ == "__main__":
    unittest.main()
