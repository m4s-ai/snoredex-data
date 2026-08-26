#!/usr/bin/env python3
"""Regression tests for the source-first card discovery loop (#136)."""

from __future__ import annotations

import json
import copy
import tempfile
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import card_discovery as discovery  # noqa: E402
import source_registry as registry  # noqa: E402


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
</ul>
<div id="cards-load-more"><div><span>1 di 4</span>
  <a href="/it/gcc/archivio-carte?cardName=Snorlax&amp;page=2">next</a>
</div></div></body></html>
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

    def test_projection_only_contract_change_preserves_acquisition_contract(self):
        contract = json.loads(
            (ROOT / "verification" / "card_discovery_adapters.json").read_text(
                encoding="utf-8"
            )
        )
        previous = copy.deepcopy(contract)
        previous["meta"]["coverageVersion"] = "1.12.0"
        previous["meta"]["policies"].append("projection-only policy")
        previous["explicitMappings"].append({"retired": "projection-only"})
        previous["gaps"].append({"retired": "workflow-only"})
        self.assertEqual(
            discovery.acquisition_contract(previous),
            discovery.acquisition_contract(contract),
        )
        previous["adapters"][0]["pageSize"] += 1
        self.assertNotEqual(
            discovery.acquisition_contract(previous),
            discovery.acquisition_contract(contract),
        )

    def test_seller_photos_keep_marketplace_provenance(self):
        self.assertEqual(
            registry.resolve_provider(
                "https://i.ebayimg.com/images/g/example/s-l1600.jpg",
                "Seller listing photograph",
            ),
            "seller-listing-photo",
        )
        self.assertEqual(
            registry.resolve_provider(
                "https://marketplace-article-scans.s3.cardmarket.com/123/123.jpg",
                "Seller listing photograph",
            ),
            "cardmarket-listing-photo",
        )
        self.assertEqual(
            registry.resolve_provider(None, "Cardmarket seller listing photograph"),
            "cardmarket-listing-photo",
        )

    def test_pokecottage_is_positive_confirmation_evidence(self):
        self.assertEqual(
            registry.resolve_provider(None, "PokeCottage collector checklist"),
            "pokecottage",
        )
        self.assertEqual(
            registry.resolve_provider(None, "PokéCottage collector checklist"),
            "pokecottage",
        )
        capability = json.loads(
            (ROOT / "verification" / "source_capabilities.json").read_text(
                encoding="utf-8"
            )
        )
        surface = next(
            row for row in capability["surfaces"]
            if row["surfaceId"] == "pokecottage-master-lists"
        )
        provider = next(
            row for row in capability["providers"]
            if row["providerId"] == "pokecottage"
        )
        edge = surface["coverageEdges"][0]
        observation = next(
            row for row in capability["observations"]
            if row["observationId"] == "obs-pokecottage-snorlax-master-list"
        )
        fixture = observation["fixtureRef"]["record"]["examplePositiveRow"]
        external_cards = json.loads(
            (ROOT / "artists_pokemontcgio.json").read_text(encoding="utf-8")
        )
        external = next(
            row for row in external_cards
            if row["id"] == fixture["setId"] + "-" + fixture["cardNumber"]
        )
        registered = next(
            row for row in registry.PROVIDERS if row["providerId"] == "pokecottage"
        )
        self.assertEqual(provider["authorityTier"], 3)
        self.assertEqual(surface["providerId"], "pokecottage")
        self.assertEqual(surface["adapterState"], "planned")
        self.assertEqual(
            set(edge["positiveEvidenceCapabilities"]),
            {
                "language", "card-existence", "set-existence", "set-membership",
                "product", "finish", "named-variety", "date", "artist", "rarity",
                "cross-language-equivalence",
            },
        )
        self.assertFalse(edge["absenceCapability"]["enabled"])
        self.assertEqual(surface["finishCapability"]["mode"], "named-variety")
        self.assertTrue(
            observation["fixtureRef"]["record"]["confirmationCapability"]
        )
        self.assertFalse(observation["fixtureRef"]["record"]["absenceCapability"])
        self.assertEqual(
            fixture["releaseDate"], external["releaseDate"].replace("/", "-")
        )
        self.assertEqual(
            set(registered["usedFor"]),
            {"language", "finish", "product", "date", "artist", "rarity"},
        )

        contract = json.loads(
            (ROOT / "verification" / "card_discovery_adapters.json").read_text(
                encoding="utf-8"
            )
        )
        gap = next(
            row for row in contract["gaps"]
            if row["gapId"] == "pokecottage-new-snorlax-set-review"
        )
        self.assertEqual(gap["terminalState"], "needs-evidence")
        self.assertIn("newly announced or released set", gap["retryCondition"])
        self.assertIn("tier-3 confirmation", gap["retryCondition"])
        self.assertIn("matching release", gap["retryCondition"])
        self.assertNotIn("independently verify", gap["retryCondition"])

        staging = json.loads(
            (ROOT / "verification" / "card_discovery_staging.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            staging["meta"]["coverageVersion"], contract["meta"]["coverageVersion"]
        )
        self.assertEqual(staging["meta"]["contractHash"], discovery.content_hash(contract))
        self.assertEqual(staging["gaps"], contract["gaps"])

    def test_replay_destination_must_sort_after_every_retained_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            runs_dir = Path(temporary)
            (runs_dir / "20260813T135800Z").mkdir()
            with mock.patch.object(discovery, "RUNS_DIR", runs_dir):
                with self.assertRaisesRegex(
                    discovery.DiscoveryError,
                    "must sort after every retained run",
                ):
                    discovery.replay_run(
                        "20260813T135800Z", "20260813T135700Z", None
                    )

    def test_replay_source_must_be_newest_compatible_complete_run(self):
        contract = {
            "meta": {
                "coverageVersion": "current",
                "reviewedAt": "2026-08-13",
            },
            "adapters": [],
            "explicitMappings": [],
        }
        previous_contract = copy.deepcopy(contract)
        previous_contract["meta"]["coverageVersion"] = "previous"
        with tempfile.TemporaryDirectory() as temporary:
            runs_dir = Path(temporary)
            for run_id, snapshot in (
                ("20260813T135800Z", previous_contract),
                ("20260813T140000Z", contract),
            ):
                run_dir = runs_dir / run_id
                run_dir.mkdir()
                (run_dir / "contract.json").write_text(
                    json.dumps(snapshot), encoding="utf-8"
                )
                (run_dir / "manifest.json").write_text(
                    json.dumps({
                        "runId": run_id,
                        "status": "complete",
                        "contractHash": discovery.content_hash(snapshot),
                    }),
                    encoding="utf-8",
                )
            with (
                mock.patch.object(discovery, "RUNS_DIR", runs_dir),
                mock.patch.object(
                    discovery,
                    "load_inputs",
                    return_value=(contract, {}, {}),
                ),
                mock.patch.object(discovery, "validate_contract"),
            ):
                with self.assertRaisesRegex(
                    discovery.DiscoveryError,
                    "must be the newest compatible complete run",
                ):
                    discovery.replay_run(
                        "20260813T135800Z", "20260813T150000Z", None
                    )

    def test_resume_can_reuse_only_an_exact_unfinished_request(self):
        acquisition = {
            "adapterId": "fixture-adapter",
            "adapterVersion": "1.0.0",
            "sliceId": "fixture-slice",
            "providerId": "fixture-provider",
            "surfaceId": "fixture-surface",
            "coverageEdgeId": "fixture-edge",
            "rawLocale": "it",
            "endpoint": "https://example.invalid/it/cards",
            "queryParameters": {"nameQueries": ["Snorlax"]},
        }
        contract = {"fixture": True}
        with tempfile.TemporaryDirectory() as temporary:
            runs_dir = Path(temporary)
            source_id = "20260813T150337Z"
            source_dir = runs_dir / source_id
            source_raw = source_dir / "raw" / "fixture-slice"
            source_raw.mkdir(parents=True)
            (source_raw / "page.html").write_text("retained", encoding="utf-8")
            (source_dir / "contract.json").write_text(
                json.dumps(contract), encoding="utf-8"
            )
            source_request = {
                **acquisition,
                "runId": source_id,
                "retrievedAt": "2026-08-13T15:03:37Z",
                "pages": [{"rawPath": "raw/fixture-slice/page.html"}],
                "details": [], "sets": [], "assets": [], "error": None,
                "checkpoint": {"complete": True},
            }
            (source_dir / "manifest.json").write_text(json.dumps({
                "runId": source_id,
                "status": "complete",
                "contractHash": discovery.content_hash(contract),
                "requests": [source_request],
            }), encoding="utf-8")

            current_id = "20260820T122400Z"
            current_dir = runs_dir / current_id
            current_dir.mkdir()
            manifest = {
                "runId": current_id,
                "requests": [{
                    **acquisition,
                    "runId": current_id,
                    "retrievedAt": "2026-08-20T12:24:00Z",
                    "pages": [], "details": [], "sets": [], "assets": [],
                    "error": {"code": "blocked"},
                    "checkpoint": {"complete": False},
                }],
                "failures": [{"sliceId": "fixture-slice"}],
            }
            (current_dir / "manifest.json").write_text(
                json.dumps({**manifest, "status": "incomplete"}), encoding="utf-8"
            )
            with mock.patch.object(discovery, "RUNS_DIR", runs_dir):
                discovery.reuse_unfinished_requests(current_dir, manifest, source_id)

            carried = manifest["requests"][0]
            self.assertEqual(carried["runId"], current_id)
            self.assertEqual(carried["replayedFromRun"], source_id)
            self.assertEqual(carried["retrievedAt"], "2026-08-13T15:03:37Z")
            self.assertEqual(manifest["failures"], [])
            self.assertEqual(
                (current_dir / "raw" / "fixture-slice" / "page.html").read_text(
                    encoding="utf-8"
                ),
                "retained",
            )

            newer_id = "20260813T160000Z"
            newer_dir = runs_dir / newer_id
            second_source_request = copy.deepcopy(source_request)
            second_source_request["sliceId"] = "fixture-slice-2"
            second_source_raw = source_dir / "raw" / "fixture-slice-2"
            second_source_raw.mkdir()
            (second_source_raw / "page.html").write_text("second", encoding="utf-8")
            (source_dir / "manifest.json").write_text(json.dumps({
                "runId": source_id,
                "status": "complete",
                "contractHash": discovery.content_hash(contract),
                "requests": [source_request, second_source_request],
            }), encoding="utf-8")
            newer_raw = newer_dir / "raw" / "fixture-slice-2"
            newer_raw.mkdir(parents=True)
            (newer_raw / "page.html").write_text("newer", encoding="utf-8")
            (newer_dir / "contract.json").write_text(
                json.dumps(contract), encoding="utf-8"
            )
            newer_request = copy.deepcopy(second_source_request)
            newer_request["runId"] = newer_id
            newer_request["retrievedAt"] = "2026-08-13T16:00:00Z"
            (newer_dir / "manifest.json").write_text(json.dumps({
                "runId": newer_id,
                "status": "complete",
                "contractHash": discovery.content_hash(contract),
                "requests": [newer_request],
            }), encoding="utf-8")
            stale_target_dir = runs_dir / "20260820T130000Z"
            stale_target_dir.mkdir()
            stale_manifest = copy.deepcopy(manifest)
            stale_manifest["runId"] = "20260820T130000Z"
            stale_manifest["requests"][0]["runId"] = "20260820T130000Z"
            stale_manifest["requests"][0]["checkpoint"] = {"complete": False}
            second_target_request = copy.deepcopy(stale_manifest["requests"][0])
            second_target_request["sliceId"] = "fixture-slice-2"
            stale_manifest["requests"].append(second_target_request)
            (stale_target_dir / "manifest.json").write_text(
                json.dumps({**stale_manifest, "status": "incomplete"}), encoding="utf-8"
            )
            with mock.patch.object(discovery, "RUNS_DIR", runs_dir):
                with self.assertRaisesRegex(
                    discovery.DiscoveryError,
                    "not the newest compatible complete request",
                ):
                    discovery.reuse_unfinished_requests(
                        stale_target_dir, stale_manifest, source_id
                    )
            self.assertFalse(
                (stale_target_dir / "raw" / "fixture-slice").exists()
            )

    def test_diff_rekeys_every_old_observation_into_one_provider_listing(self):
        old = [
            {"stableKey": f"old-{unit}", "recordHash": unit,
             "identityHintHash": "shared", "locality": "LATAM"}
            for unit in ("U0192", "U0219")
        ]
        new = [{
            "stableKey": "listing-PPPS8-117b", "recordHash": "listing",
            "identityHintHash": "shared", "locality": "LATAM",
        }]

        delta = discovery.diff_records(new, old)

        self.assertEqual(delta["disappeared"], [])
        self.assertEqual(delta["added"], [])
        self.assertEqual(
            {(row["from"], row["to"]) for row in delta["rekeyedCandidates"]},
            {
                ("old-U0192", "listing-PPPS8-117b"),
                ("old-U0219", "listing-PPPS8-117b"),
            },
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
        self.assertEqual(parsed["totalPages"], 4)

    def test_official_declared_result_page_cannot_be_skipped(self):
        parsed = discovery.parse_list(
            OFFICIAL_LIST, "pokemon-official-localized-html", "it"
        )
        retained_pages = [{"pageNo": 1, "totalPages": parsed["totalPages"]}]
        self.assertFalse(discovery.pagination_complete(retained_pages))
        retained_pages.extend(
            {"pageNo": page_no, "totalPages": parsed["totalPages"]}
            for page_no in (2, 3, 4)
        )
        self.assertTrue(discovery.pagination_complete(retained_pages))

    def test_official_result_path_cannot_cross_a_page_boundary_twice(self):
        retained_pages = [
            {
                "pageNo": 1, "totalPages": 2,
                "detailIds": ["svp/51", "svp/184"],
            },
            {
                "pageNo": 2, "totalPages": 2,
                "detailIds": ["svp/184", "sv4/123"],
            },
        ]
        self.assertFalse(discovery.pagination_complete(retained_pages))
        retained_pages[1]["detailIds"][0] = "sv3/202"
        self.assertTrue(discovery.pagination_complete(retained_pages))

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
        self.assertEqual(len(english), 64)
        self.assertEqual(sum(row["bucket"] == "matched" for row in english), 57)
        excluded = [row for row in english if row["bucket"] == "positively-excluded"]
        self.assertEqual(
            {row["rawProviderId"] for row in excluded},
            {"A1-211", "A1-250", "A2a-063", "A3b-057", "A3b-084", "A3b-091", "P-A-049"},
        )
        self.assertTrue(all(row["sourceRecord"]["setSeries"]["id"] == "tcgp" for row in excluded))
        by_id = {row["rawProviderId"]: row for row in english}
        self.assertEqual(
            {raw_id: by_id[raw_id]["raw"]["localName"] for raw_id in (
                "swsh1-141", "sv09-117", "sv04-175",
            )},
            {
                "swsh1-141": "Snorlax V",
                "sv09-117": "Hop's Snorlax",
                "sv04-175": "Snorlax Doll",
            },
        )
        self.assertTrue(all(
            by_id[raw_id]["bucket"] == "matched"
            for raw_id in ("swsh1-141", "sv09-117", "sv04-175")
        ))
        self.assertEqual(
            by_id["swsh1-141"]["queryParameters"]["nameFilter"], "substring"
        )
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
            "de": ("German", "Relaxo", 39, 35),
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
            if row["rawProviderId"] == "swsh11tg-TG10"
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
            },
        )

        spanish = [
            row for row in records
            if row["providerId"] == "tcgdex" and row["rawLocale"] == "es"
        ]
        spanish_physical = [
            row for row in spanish
            if row["sourceRecord"]["productScope"] == "physical-tcg"
        ]
        self.assertEqual(len(spanish), 29)
        self.assertEqual(len(spanish_physical), 25)
        self.assertTrue(all(
            row["bucket"] == "needs-evidence"
            and row["localityEvidenceMode"] == "unqualified-language"
            and row["normalizationProposal"]["targetCardReleaseId"] is None
            for row in spanish_physical
        ))
        me03 = next(row for row in spanish if row["rawProviderId"] == "me03-063")
        self.assertIsNone(me03["normalizationProposal"]["targetCardReleaseId"])
        self.assertIn("Spanish language only", me03["bucketBasis"])
        tg10 = next(
            row for row in spanish if row["rawProviderId"] == "swsh11tg-TG10"
        )
        self.assertEqual(tg10["bucket"], "needs-evidence")
        self.assertIsNone(tg10["normalizationProposal"]["targetCardReleaseId"])

        contract = json.loads(
            (ROOT / "verification" / "card_discovery_adapters.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(any(
            mapping["providerId"] == "tcgdex" and mapping["rawLocale"] == "es"
            for mapping in contract["explicitMappings"]
        ))

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
        self.assertEqual(len(italian), 42)
        self.assertEqual(
            {bucket: sum(row["bucket"] == bucket for row in italian)
             for bucket in {row["bucket"] for row in italian}},
            {"matched": 12, "new-candidate": 30},
        )
        self.assertTrue(all(
            row["sourceRecord"]["recordSource"] == "localized-archive-list-entry"
            for row in italian
        ))
        self.assertNotIn("pl2/111", {row["rawProviderId"] for row in italian})
        stage = json.loads(
            (ROOT / "verification" / "card_discovery_staging.json").read_text(
                encoding="utf-8"
            )
        )
        retained_slice = next(
            row for row in stage["slices"] if row["sliceId"] == "tpci-it-snorlax"
        )
        self.assertEqual(retained_slice["checkpoint"]["completedPages"], [
            "Snorlax:1", "Snorlax:2", "Snorlax:3", "Snorlax:4",
        ])
        self.assertEqual(retained_slice["accounting"]["fetched"], 42)
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
        self.assertEqual(len(brazilian_frontier), 2)
        by_identity = {
            (row["raw"]["rawSetCode"], row["raw"]["localCollectorNumber"]): row
            for row in brazilian_frontier
        }
        self.assertEqual(set(by_identity), {("PPPS8", "117b"), ("PPPS7", "117")})
        self.assertEqual(
            {row["unitId"] for row in by_identity[("PPPS8", "117b")]["sourceRecord"]["observations"]},
            {"U0192", "U0219"},
        )
        self.assertEqual(
            {row["variant"] for row in by_identity[("PPPS8", "117b")]["sourceRecord"]["observations"]},
            {"V1", "V2"},
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

    def test_confirmed_source_groups_unit_observations_by_provider_listing(self):
        source_url = (
            "https://www.ligapokemon.com.br/?view=cards/card&"
            "card=Hop%27s%20Snorlax%20%28117b%2F90%29&ed=PPPS8&num=117b"
        )
        retained = [
            {"unitId": "U0192", "sourceUrl": source_url, "variant": "V2"},
            {"unitId": "U0219", "sourceUrl": source_url, "variant": "V1"},
            {"unitId": "U0329", "sourceUrl": source_url.replace("PPPS8", "PPPS7")
             .replace("117b", "117"), "variant": "base"},
        ]
        records = discovery.confirmed_source_records(retained, {
            "retainedUnitIds": ["U0192", "U0219", "U0329"],
            "nameQueries": ["Snorlax do Lupo"],
        })

        self.assertEqual(len(records), 2)
        shared = next(row for row in records if row["rawSetCode"] == "PPPS8")
        self.assertEqual(
            [(row["unitId"], row["variant"]) for row in shared["observations"]],
            [("U0192", "V2"), ("U0219", "V1")],
        )

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

    def test_historical_set_index_never_becomes_card_discovery(self):
        rows = [
            json.loads(line)
            for line in (
                ROOT / "verification" / "card_discovery_records.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            if line
        ]
        self.assertFalse(any(
            row["providerId"] == "bulbapedia"
            and row["surfaceId"] == "bulbapedia-mediawiki"
            for row in rows
        ))
        card_contract = json.loads(
            (ROOT / "verification" / "card_discovery_adapters.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn(
            "bulbapedia-historical-card-frontiers",
            {row["adapterId"] for row in card_contract["adapters"]},
        )
        set_contract = json.loads(
            (ROOT / "verification" / "source_adapters.json").read_text(
                encoding="utf-8"
            )
        )
        set_adapter = next(
            row for row in set_contract["adapters"]
            if row["adapterId"] == "bulbapedia-historical-language-index"
        )
        self.assertEqual(set_adapter["category"], "set")
        self.assertEqual(len(set_adapter["slices"]), 3)
        capability = json.loads(
            (ROOT / "verification" / "source_capability_graph.json").read_text(
                encoding="utf-8"
            )
        )
        edge = next(
            row for row in capability["coverageEdges"]
            if row["edgeId"] == "bulbapedia-historical-index-positive"
        )
        self.assertEqual(edge["coverage"]["productCategories"], ["set"])
        self.assertNotIn("card-existence", edge["positiveEvidenceCapabilities"])

        locality_matrix = json.loads(
            (ROOT / "verification" / "locality_era_matrix.json").read_text(
                encoding="utf-8"
            )
        )
        historical_tracks = {
            track["trackId"]: track
            for track in locality_matrix["tracks"]
            if track["trackId"] in {"west-nl", "west-pl", "west-ru"}
        }
        self.assertEqual(set(historical_tracks), {"west-nl", "west-pl", "west-ru"})
        for track in historical_tracks.values():
            refs = list(track["evidenceRefs"])
            refs.extend(track["discovery"]["sourceRefs"])
            for era in track["eraSegments"]:
                refs.extend(era["evidenceRefs"])
            self.assertFalse(
                any(ref.startswith("card-slice:bulbapedia-historical-") for ref in refs),
                f"{track['trackId']} must not promote a set-only index to card discovery",
            )

    def test_issue84_52poke_frontier_keeps_only_reviewed_numbered_rows(self):
        records = discovery.issue84_52poke_records()
        contract = json.loads(
            (ROOT / "verification" / "card_discovery_adapters.json").read_text(
                encoding="utf-8"
            )
        )
        adapter = next(
            row for row in contract["adapters"]
            if row["adapterId"] == "52poke-issue84-positive"
        )
        retained = set(adapter["slices"][0]["retainedRecordIds"])
        self.assertEqual(len(retained), 12)
        self.assertTrue(retained <= set(records))
        self.assertNotIn("DP1|DP1|", records)
        self.assertEqual(
            records["S10a|SVG|021/049"]["sourcePageKey"], "S10a"
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
