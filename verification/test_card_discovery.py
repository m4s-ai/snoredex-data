#!/usr/bin/env python3
"""Regression tests for the source-first card discovery loop (#136)."""

from __future__ import annotations

import json
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
TCGDEX_ADAPTER = {
    **ADAPTER,
    "adapterId": "fixture-tcgdex",
    "providerId": "tcgdex",
    "surfaceId": "tcgdex-api",
    "responseFormat": "tcgdex-json",
    "listEndpointTemplate": "https://api.tcgdex.net/v2/{rawLocale}/cards",
    "detailEndpointTemplate": "https://api.tcgdex.net/v2/{rawLocale}/cards/{rawProviderId}",
    "setEndpointTemplate": "https://api.tcgdex.net/v2/{rawLocale}/sets/{rawSetCode}",
}
TCGDEX_SLICE = {
    **SLICE_TW,
    "sliceId": "fixture-en",
    "coverageEdgeId": "tcgdex-west-positive",
    "rawLocale": "en",
    "locality": "WEST",
    "language": "English",
    "script": "Latn",
    "nameQueries": ["Snorlax"],
    "positiveNameExclusions": [],
}
TCGDEX_REQUEST = {
    **REQUEST,
    "queryParameters": {"nameQueries": ["Snorlax"], "nameFilter": "strict-equality"},
    "details": [{"rawProviderId": "base2-11", "responseHash": "sha256:detail"}],
}
OFFICIAL_ADAPTER = {
    **ADAPTER,
    "adapterId": "fixture-tpci",
    "providerId": "pokemon-official",
    "surfaceId": "tpci-localized-card-archive",
    "responseFormat": "pokemon-official-localized-html",
    "listEndpointTemplate": "https://www.pokemon.com/{rawLocale}/gcc/archivio-carte/",
    "detailEndpointTemplate": (
        "https://www.pokemon.com/{rawLocale}/gcc/archivio-carte/series/{rawProviderId}/"
    ),
}
OFFICIAL_SLICE = {
    **SLICE_TW,
    "sliceId": "fixture-it",
    "coverageEdgeId": "tpci-it-card-archive-positive",
    "rawLocale": "it",
    "locality": "WEST",
    "language": "Italian",
    "script": "Latn",
    "nameQueries": ["Snorlax"],
    "positiveNameExclusions": [],
}
OFFICIAL_LIST = b"""
<html lang="it"><body>
<form id="filters"><input id="cardName" name="cardName" value="Snorlax"></form>
<ul class="cards-grid" id="cardResults">
  <li><a href="/it/gcc/archivio-carte/series/svp/51/">
    <img src="https://assets.pokemon.com/cms2-it-it/img/cards/web/SVP/SVP_IT_51.png"
         alt="Snorlax"></a></li>
  <li><a href="/it/gcc/archivio-carte/series/svp/184/">
    <img src="https://assets.pokemon.com/cms2-it-it/img/cards/web/SVP/SVP_IT_184.png"
         alt="Snorlax di Hop"></a></li>
</ul></body></html>
"""
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

    def test_unqualified_language_never_inherits_a_legacy_west_locality(self):
        source_url = "https://example.invalid/pt/cards/13148"
        row = self.normalize(
            record=source_record(sourceUrl=source_url),
            releases=[{
                "cardReleaseId": "RELEASE:WEST:Portuguese:SVQP:012/023:work",
                "locality": "WEST", "language": "Portuguese",
                "localSetCode": "svQP F", "localNumber": "012/023",
                "sourceRecords": [source_url],
            }],
            slice_row={
                **SLICE_TW, "locality": "WEST", "language": "Portuguese",
                "localityEvidenceMode": "unqualified-language",
            },
        )
        self.assertEqual(row["bucket"], "needs-evidence")
        self.assertIsNone(row["normalizationProposal"]["targetCardReleaseId"])
        self.assertIn("physical locality remains unresolved", row["bucketBasis"])

    def test_brazilian_market_record_does_not_create_a_physical_locality(self):
        row = self.normalize(
            slice_row={
                **SLICE_TW, "locality": "LATAM", "language": "Portuguese",
                "localityEvidenceMode": "market-only",
            }
        )
        self.assertEqual(row["bucket"], "needs-evidence")
        self.assertIsNone(row["normalizationProposal"]["targetCardReleaseId"])
        self.assertIn("market record", row["bucketBasis"])

    def test_diff_reports_locality_evidence_mode_changes(self):
        previous = [{
            "stableKey": "provider|surface|pt|1", "recordHash": "sha256:old",
            "identityHintHash": "sha256:hint", "locality": "WEST",
        }]
        current = [{
            "stableKey": "provider|surface|pt|1", "recordHash": "sha256:new",
            "identityHintHash": "sha256:hint", "locality": "WEST",
            "localityEvidenceMode": "unqualified-language",
        }]
        delta = discovery.diff_records(current, previous)
        self.assertEqual(delta["counts"]["localityDeltas"], 1)
        self.assertEqual(
            delta["localityDeltas"][0]["toEvidenceMode"], "unqualified-language"
        )

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

    def test_tcgdex_json_uses_set_series_as_the_pocket_discriminator(self):
        listing = b'[{"id":"A1-211","localId":"211","name":"Snorlax"}]'
        self.assertEqual(
            discovery.parse_list(listing, "tcgdex-json")["detailIds"], ["A1-211"]
        )
        detail = b'{"id":"A1-211","localId":"211","name":"Snorlax","set":{"id":"A1","name":"Genetic Apex"}}'
        parsed = discovery.parse_detail(
            detail, "A1-211", "tcgdex-json",
            {"id": "A1", "name": "Genetic Apex", "serie": {"id": "tcgp", "name": "Pok\u00e9mon TCG Pocket"}},
        )
        self.assertEqual(parsed["productScope"], "digital-pocket")
        self.assertEqual(parsed["setSeries"]["id"], "tcgp")

    def test_official_italian_filter_retains_exact_paths_names_and_images(self):
        query, entries = discovery.parse_official_localized_entries(OFFICIAL_LIST, "it")
        self.assertEqual(query, "Snorlax")
        self.assertEqual([row["detailId"] for row in entries], ["svp/51", "svp/184"])
        self.assertEqual(entries[1]["localName"], "Snorlax di Hop")
        self.assertEqual(entries[0]["localCollectorNumber"], "51")
        self.assertTrue(entries[0]["cardImageUrl"].endswith("SVP_IT_51.png"))
        self.assertEqual(entries[0]["recordSource"], "localized-archive-list-entry")
        parsed = discovery.parse_list(
            OFFICIAL_LIST, "pokemon-official-localized-html", "it"
        )
        self.assertEqual(parsed["resultCount"], 2)
        self.assertEqual(parsed["totalPages"], 1)

    def test_official_italian_filter_challenge_is_a_source_failure(self):
        with self.assertRaisesRegex(discovery.DiscoveryError, "access challenge"):
            discovery.parse_official_localized_entries(
                b"<html><title>Pardon Our Interruption</title></html>", "it"
            )

    def test_official_italian_entry_matches_only_through_reviewed_mapping(self):
        source = discovery.parse_detail(
            OFFICIAL_LIST, "svp/51", "pokemon-official-localized-html"
        )
        target = "RELEASE:WEST:Italian:SVP:051:work"
        request = {
            **REQUEST,
            "queryParameters": {"nameQueries": ["Snorlax"]},
            "pages": [{"responseHash": "sha256:list"}],
            "details": [{"rawProviderId": "svp/51", "responseHash": "sha256:list"}],
        }
        mapping_key = discovery.raw_key(
            "pokemon-official", "tpci-localized-card-archive", "it", "svp/51"
        )
        row = discovery.normalize_record(
            OFFICIAL_ADAPTER, OFFICIAL_SLICE, request, source,
            [{
                "cardReleaseId": target, "locality": "WEST", "language": "Italian",
                "localSetCode": "SVP", "localNumber": "051", "sourceRecords": [],
            }],
            {mapping_key: {
                "mode": "exact-match", "targetCardReleaseId": target,
                "evidence": "reviewed official path and CMS identity",
            }},
            {},
        )
        self.assertEqual(row["bucket"], "matched")
        self.assertEqual(row["sourceUrl"], (
            "https://www.pokemon.com/it/gcc/archivio-carte/series/svp/51/"
        ))
        self.assertEqual(row["normalizationProposal"]["targetCardReleaseId"], target)

    def test_exact_provider_url_matches_one_existing_release(self):
        source = source_record(
            detailId="base2-11", localName="Snorlax", rawSetCode="base2",
            localCollectorNumber="11", productScope="physical-tcg",
        )
        release = {
            "cardReleaseId": "RELEASE:WEST:English:JU:11:work",
            "locality": "WEST", "language": "English",
            "localSetCode": "JU", "localNumber": "11",
            "sourceRecords": ["https://api.tcgdex.net/v2/en/cards/base2-11"],
        }
        row = discovery.normalize_record(
            TCGDEX_ADAPTER, TCGDEX_SLICE, TCGDEX_REQUEST,
            source, [release], {}, {},
        )
        self.assertEqual(row["bucket"], "matched")
        self.assertEqual(row["normalizationProposal"]["targetCardReleaseId"], release["cardReleaseId"])

    def test_committed_english_slice_is_fully_accounted_without_regional_invention(self):
        records = [
            json.loads(line) for line in (ROOT / "verification" / "card_discovery_records.jsonl")
            .read_text(encoding="utf-8").splitlines()
            if line
        ]
        english = [row for row in records if row["stableKey"].startswith("tcgdex|tcgdex-api|en|")]
        self.assertEqual(len(english), 45)
        self.assertEqual(sum(row["bucket"] == "matched" for row in english), 41)
        excluded = [row for row in english if row["bucket"] == "positively-excluded"]
        self.assertEqual(
            {row["rawProviderId"] for row in excluded},
            {"A1-211", "A1-250", "A2a-063", "P-A-049"},
        )
        self.assertTrue(all(row["sourceRecord"]["setSeries"]["id"] == "tcgp" for row in excluded))
        self.assertTrue(all(row["locality"] == "WEST" for row in english))
        self.assertTrue(all("distributionRegion" not in row["sourceRecord"] for row in english))

    def test_committed_shared_western_slices_preserve_locale_identity(self):
        records = [
            json.loads(line) for line in (ROOT / "verification" / "card_discovery_records.jsonl")
            .read_text(encoding="utf-8").splitlines()
            if line
        ]
        expected = {
            "fr": ("French", "Ronflex", 38, 34),
            "de": ("German", "Relaxo", 40, 36),
            "es": ("Spanish", "Snorlax", 29, 25),
        }
        for locale, (language, local_name, total, physical_total) in expected.items():
            rows = [
                row for row in records
                if row["stableKey"].startswith(f"tcgdex|tcgdex-api|{locale}|")
            ]
            physical = [
                row for row in rows
                if row["sourceRecord"]["productScope"] == "physical-tcg"
            ]
            pocket = [
                row for row in rows
                if row["sourceRecord"]["productScope"] == "digital-pocket"
            ]
            self.assertEqual(len(rows), total)
            self.assertEqual(len(physical), physical_total)
            self.assertEqual(len(pocket), 4)
            self.assertTrue(all(row["raw"]["localName"] == local_name for row in rows))
            self.assertTrue(all(row["bucket"] == "matched" for row in physical))
            self.assertTrue(all(row["bucket"] == "positively-excluded" for row in pocket))
            self.assertTrue(all(row["sourceRecord"]["setName"] for row in rows))
            self.assertTrue(all(
                set(row["sourceRecord"]["providerRecord"]["legal"])
                == {"standard", "expanded"}
                for row in rows
            ))
            self.assertTrue(all(
                row["sourceUrl"].startswith(f"https://api.tcgdex.net/v2/{locale}/cards/")
                for row in rows
            ))
            self.assertTrue(all(
                row["normalizationProposal"]["targetCardReleaseId"].startswith(
                    f"RELEASE:WEST:{language}:"
                )
                for row in physical
            ))

        tg10 = {
            row["rawLocale"]: row for row in records
            if row["rawProviderId"] == "swsh11.5tg-TG10"
            and row["rawLocale"] in expected
        }
        self.assertEqual(
            {
                locale: (
                    row["sourceRecord"]["setName"],
                    row["sourceRecord"]["providerRecord"]["attacks"][0]["name"],
                )
                for locale, row in tg10.items()
            },
            {
                "fr": ("Origine Perdue Galerie de Dresseurs", "Ronflement Retentissant"),
                "de": ("Verlorener Ursprung Trainer-Galerie", "Dumpfes Geschnarche"),
                "es": ("Origen Perdido Galería de Entrenador", "Ronquido Descomunal"),
            },
        )
        self.assertNotIn("LATAM", tg10["es"]["normalizationProposal"]["targetCardReleaseId"])

    def test_committed_italian_slice_accounts_for_filter_without_claiming_history(self):
        records = [
            json.loads(line) for line in (ROOT / "verification" / "card_discovery_records.jsonl")
            .read_text(encoding="utf-8").splitlines()
            if line
        ]
        italian = [
            row for row in records
            if row["stableKey"].startswith(
                "pokemon-official|tpci-localized-card-archive|it|"
            )
        ]
        self.assertEqual(len(italian), 12)
        self.assertTrue(all(row["bucket"] == "matched" for row in italian))
        self.assertTrue(all(
            row["sourceRecord"]["recordSource"] == "localized-archive-list-entry"
            for row in italian
        ))
        self.assertNotIn("pl2/111", {row["rawProviderId"] for row in italian})
        contract = json.loads(
            (ROOT / "verification" / "card_discovery_adapters.json").read_text(
                encoding="utf-8"
            )
        )
        gap = next(
            row for row in contract["gaps"]
            if row["gapId"] == "official-italian-archive-filter-coverage"
        )
        self.assertIn("pl2/111", gap["reason"])
        self.assertEqual(gap["terminalState"], "needs-evidence")

    def test_committed_portuguese_slices_never_infer_a_physical_region(self):
        records = [
            json.loads(line) for line in (ROOT / "verification" / "card_discovery_records.jsonl")
            .read_text(encoding="utf-8").splitlines()
            if line
        ]
        unqualified = [
            row for row in records
            if row["providerId"] == "tcgdex" and row["rawLocale"] == "pt"
        ]
        self.assertEqual(len(unqualified), 26)
        self.assertTrue(all(row["bucket"] == "needs-evidence" for row in unqualified))
        self.assertTrue(all(
            row["localityEvidenceMode"] == "unqualified-language"
            and row["normalizationProposal"]["targetCardReleaseId"] is None
            for row in unqualified
        ))

        brazilian_frontier = [
            row for row in records if row["providerId"] == "ligapokemon"
        ]
        self.assertEqual(
            {
                (row["rawProviderId"], row["raw"]["rawSetCode"],
                 row["raw"]["localCollectorNumber"])
                for row in brazilian_frontier
            },
            {
                ("U0192", "PPPS8", "117b"),
                ("U0219", "PPPS8", "117b"),
                ("U0329", "PPPS7", "117"),
            },
        )
        self.assertTrue(all(
            row["bucket"] == "needs-evidence"
            and row["localityEvidenceMode"] == "market-only"
            and row["normalizationProposal"]["targetCardReleaseId"] is None
            for row in brazilian_frontier
        ))

        staging = json.loads(
            (ROOT / "verification" / "card_discovery_staging.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("localityDeltas", staging["diff"])
        self.assertIn("localityDeltas", staging["diff"]["counts"])

    def test_native_name_false_positive_is_excluded_by_positive_identity(self):
        row = self.normalize(record=source_record(localName="小卡比獸"))
        self.assertEqual(row["bucket"], "positively-excluded")
        self.assertIn("Munchlax", row["bucketBasis"])

    def test_source_first_json_preserves_printed_language_modifier(self):
        record = {
            "detailId": "LATAM:SVP LA:184:base",
            "localName": "Snorlax de Paul",
            "rawSetCode": "SVP LA",
            "localCollectorNumber": "184",
            "cardImageUrl": "https://assets.pokemon.com/SVP_LA_184.png",
            "setSymbolUrl": None,
            "productScope": "physical-tcg",
            "sourceUrl": "https://assets.pokemon.com/SVP_LA_184.png",
            "providerRecord": {"printId": "LATAM:SVP LA:184:base"},
        }
        raw = discovery.canonical_bytes([record])
        parsed = discovery.parse_list(raw, "source-first-print-json")
        self.assertEqual(parsed["detailIds"], ["LATAM:SVP LA:184:base"])
        self.assertEqual(
            discovery.parse_detail(
                discovery.canonical_bytes(record),
                "LATAM:SVP LA:184:base",
                "source-first-print-json",
            )["rawSetCode"],
            "SVP LA",
        )

    def test_latam_source_records_keep_la_and_es_as_different_codes(self):
        document = json.loads(
            (ROOT / "verification" / "source_first_prints.json").read_text(
                encoding="utf-8"
            )
        )
        records = {row["printId"]: row for row in document["prints"]}
        self.assertEqual(
            records["LATAM:SVP LA:184:base"]["localSetCode"], "SVP LA"
        )
        self.assertEqual(
            records["WEST:SVP ES:184:base"]["localSetCode"], "SVP ES"
        )
        self.assertEqual(
            {
                records["LATAM:JTG LA:117/159:base"]["localSetCode"],
                records["LATAM:POR LA:063/088:base"]["localSetCode"],
            },
            {"JTG LA", "POR LA"},
        )
        self.assertNotIn(
            "LATAM:xJTG LA:117/159:base", records,
            "xJTG must remain a positive-evidence gap",
        )

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
