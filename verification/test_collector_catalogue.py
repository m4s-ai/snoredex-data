#!/usr/bin/env python3
"""Contract, graph-reference and reconciliation regressions for issue #254."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import collector_catalogue as collector  # noqa: E402
import collector_deployment as deployment  # noqa: E402


def read(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    assert collector.collector_number("076/095") == collector.collector_number("076")
    source_backed_rarity = collector.normalized_rarity(
        "release:test",
        {"rarity": "Fixed"},
        {"release:test": [{
            "normalizedRarityId": "uncommon",
            "sourceNativeValue": "U",
            "rarityClaimId": "CLAIM:test",
        }]},
    )
    assert source_backed_rarity["display"] == "U"
    source_first = read("verification/source_first_prints.json")
    korean_names = {
        (row["localSetCode"], row["localNumber"]): row["name"]
        for row in source_first["prints"]
        if row["locality"] == "KR"
    }
    assert korean_names[("m2a", "136/193")] == "호브의 잠만보"
    assert korean_names[("sv4K", "060/066")] == "잠만보인형"
    assert korean_names[("svM", "094/175")] == "잠만보 ex"
    assert korean_names[("sv9", "075/100")] == "호브의 잠만보"
    assert korean_names[("DP", "006")] == "잠만보 Lv.X"
    source_first_by_print = {row["printId"]: row for row in source_first["prints"]}
    assert source_first_by_print["KR:sv5a:051/066:base"]["corroborated"] is True
    assert source_first_by_print["KR:sv9:075/100:base"]["corroborated"] is False
    assert source_first_by_print["KR:DP:006:base"]["corroborated"] is False
    assert "https://globalbunjang.com/product/416373605" in source_first_by_print[
        "KR:sv5a:051/066:base"
    ]["corroboratingSourceUrls"]
    assert source_first_by_print["KR:xsv2a:143/165:base"]["corroborated"] is True
    assert source_first_by_print["KR:xsv2a:143/165:base"].get("corroboratingSourceUrls") is None
    units = read("verification/units.json")
    units_by_id = {row["unitId"]: row for row in units}
    for unit_id in ("U0233", "U0257", "U0413", "U0541", "U0561", "U0579", "U0677", "U0780", "U0790"):
        assert units_by_id[unit_id]["corroborated"] is True
    for unit_id in ("U0370", "U0623"):
        assert units_by_id[unit_id]["corroborated"] is False
    assert units_by_id["U0775"]["corroborated"] is False
    specimens = read("verification/specimens.json")["specimens"]
    specimen_0061 = next(row for row in specimens if row["specimenId"] == "SPEC-0061")
    assert "U0780" in specimen_0061["citedBy"]
    assert "U0775" not in specimen_0061["citedBy"]
    specimen_0437 = next(row for row in specimens if row["specimenId"] == "SPEC-0437")
    assert "U0790" in specimen_0437["citedBy"]
    graph = read("verification/authoritative_graph.json")
    assert any(
        row["entityType"] == "card-release"
        and row["entityId"] == "RELEASE:KR:Korean:DP:006:Snorlax-LvX-Big-Appetite-Exercise"
        and row["payload"]["work"] == "Snorlax-LvX-Big-Appetite-Exercise"
        for row in graph["entities"]
    )
    catalogue = read("collector_catalogue.json")
    catalogue_by_release = {row["cardReleaseId"]: row for row in catalogue["items"]}
    for release_id in (
        "RELEASE:KR:Korean:sv4a:145/190:Snorlax-Voraciousness-Thudding-Press",
        "RELEASE:KR:Korean:mC:567/742:Snorlax-But-First-Food-Heavy-Impact",
        "RELEASE:KR:Korean:mC:568/742:Snorlax-Lazy-Press",
        "RELEASE:KR:Korean:mC:569/742:Hops-Snorlax-Extra-Helpings-Dynamic-Press",
    ):
        assert catalogue_by_release[release_id]["rarity"]["display"] == "N"
        assert catalogue_by_release[release_id]["rarity"]["normalizedId"] is None
    set_sources = read("verification/set_catalogue_sources.json")["sourceRecords"]
    korean_profiles = {
        row["providerRecordKey"]: row
        for row in set_sources
        if row["sourceKind"] == "source-first-local-set-profile"
        and row["providerRecordKey"].startswith("KR\x1f")
    }
    assert korean_profiles["KR\x1fm2a"]["retrieved"] == "2026-08-30"
    assert korean_profiles["KR\x1fsv2a"]["retrieved"] == "2026-08-30"
    legacy_row = {
        "checklistId": "legacy-semantic-row",
        "printingId": "F0167-P01",
        "finish": "holo",
        "edition": "1st Edition",
        "foilPattern": "Poké Ball mirror",
        "markings": [],
        "distribution": None,
        "cardSize": "standard",
    }
    shifted_physical = {
        "cardReleaseId": "RELEASE:JU:Dutch:JU:11",
        "sourcePrintingId": "F0167-P99",
        "finish": "holo",
        "edition": "1st Edition",
        "foilPattern": "poke-ball",
        "markings": None,
        "distribution": None,
        "cardSize": "standard",
    }
    assert collector.printing_semantic_key(
        shifted_physical["cardReleaseId"], legacy_row
    ) == collector.printing_semantic_key(
        shifted_physical["cardReleaseId"], shifted_physical
    )
    assert collector.legacy_match_for_physical(
        shifted_physical,
        {},
        set(),
        {collector.printing_semantic_key(shifted_physical["cardReleaseId"], legacy_row): legacy_row},
        {collector.printing_semantic_core_key(shifted_physical["cardReleaseId"], legacy_row): [legacy_row]},
    ) is legacy_row
    reused_ordinal = {**shifted_physical, "sourcePrintingId": "F0167-P01", "finish": "reverse-holo"}
    assert collector.legacy_match_for_physical(
        reused_ordinal,
        {legacy_row["printingId"]: (shifted_physical["cardReleaseId"], legacy_row)},
        set(),
        {collector.printing_semantic_key(shifted_physical["cardReleaseId"], legacy_row): legacy_row},
        {collector.printing_semantic_core_key(shifted_physical["cardReleaseId"], legacy_row): [legacy_row]},
    ) is None
    old_release = "RELEASE:JU:Dutch:legacy-JU:11"
    rekeyed_release = {**shifted_physical, "sourcePrintingId": "F0167-P01", "edition": None}
    source_candidate = {legacy_row["printingId"]: (old_release, legacy_row)}
    assert collector.legacy_match_for_physical(
        rekeyed_release, source_candidate, set(), {}, {}
    ) is None
    assert collector.legacy_match_for_physical(
        rekeyed_release, source_candidate,
        {(old_release, rekeyed_release["cardReleaseId"])}, {}, {}
    ) is legacy_row

    graph = read("verification/authoritative_graph.json")
    catalogue = read("collector_catalogue.json")
    migrations = read("collector_migrations.json")
    fixture = read("collector_catalogue.fixture.json")
    schema = read("collector_catalogue.schema.json")
    predecessor = read("analysis_checklist.json")
    releases = read("analysis_confirmed_releases.json")

    build_a_bear_predecessor = next(
        row for row in predecessor["items"]
        if row["checklistId"].startswith(
            "flf-80-english-none-non-holo-retailer-build-a-bear-workshop"
        )
    )
    assert build_a_bear_predecessor["releaseDate"] is None
    build_a_bear_release = next(
        row for row in releases["variants"]
        if row["setCode"] == "FLF" and row["number"] == "80" and row["variant"] == "V2"
    )
    assert build_a_bear_release["date"] == "9999"
    assert build_a_bear_release["dateSort"] == "9999-01-01"

    assert not collector.validate_catalogue(catalogue, graph)
    assert not collector.validate_migrations(migrations, catalogue, graph, predecessor)
    assert catalogue["meta"]["previousFingerprint"] == collector.PREVIOUS_CATALOGUE_FINGERPRINT
    assert migrations["meta"]["schemaVersion"] == "1.1.0"
    previous_route, = migrations["catalogueTransitions"]
    assert previous_route["fromFingerprint"] == catalogue["meta"]["previousFingerprint"]
    assert previous_route["toFingerprint"] == catalogue["meta"]["catalogueFingerprint"]
    previous_route_by_source = {
        row["fromItemId"]: row for row in previous_route["transitions"]
    }
    assert {
        row["fromItemId"] for row in previous_route["transitions"]
    } == (
        {row["itemId"] for row in catalogue["items"]}
        | set(collector.CUMULATIVE_CATALOGUE_REKEYS)
    )
    assert all(
        previous_route_by_source[row["itemId"]]
        == collector.retained_state_transition(row["itemId"])
        for row in catalogue["items"]
    )
    assert all(
        previous_route_by_source[old_id] == collector.state_transition(old_id, [new_id])
        for old_id, new_id in collector.CUMULATIVE_CATALOGUE_REKEYS.items()
    )
    assert not collector.validate_catalogue(
        fixture["catalogue"], check_asset_bytes=False
    )
    assert set(schema["properties"]["items"]["items"]["properties"]["workMappingState"]["enum"]) == collector.WORK_MAPPING_STATES
    for case in fixture["workMappingCases"]:
        case_catalogue = copy.deepcopy(fixture["catalogue"])
        case_catalogue["items"][0]["workId"] = case["workId"]
        case_catalogue["items"][0]["workMappingState"] = case["workMappingState"]
        case_catalogue["meta"]["catalogueFingerprint"] = collector.semantic_fingerprint(case_catalogue)
        case_errors = collector.validate_catalogue(case_catalogue, check_asset_bytes=False)
        assert bool(case_errors) is (not case["valid"]), (case["caseId"], case_errors)
    fixture_localizations = {
        row["languageTag"]: (row["locality"], row["script"])
        for row in fixture["catalogue"]["localizations"]
    }
    assert fixture_localizations["es-ES"] == ("WEST", "Latn")
    assert fixture_localizations["es-419"] == ("LATAM", "Latn")
    assert fixture_localizations["zh-Hans"] == ("CN", "Hans")
    assert fixture_localizations["zh-Hant"] == ("TW", "Hant")
    assert all(
        item["imageAssetId"] is None and item["imageScope"] == "unknown"
        for item in fixture["catalogue"]["items"]
    )
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["meta"]["properties"]["schemaVersion"]["const"] == "1.0.0"
    assert schema["properties"]["items"]["items"]["properties"]["correctionLink"]["maxLength"] == collector.CORRECTION_URL_MAX_LENGTH

    # Correction links are producer-owned deep links. Every generated item (including
    # all three fixture states) must carry an exact opaque item id and only the
    # reliable issue-form prefill fields.
    form = read(".github/ISSUE_TEMPLATE/printing-correction.yml")
    form_ids = {
        element.get("id") for element in form.get("body", [])
        if isinstance(element, dict)
    }
    assert {"row-id", "card-name", "set-code", "card-number", "current-state"} <= form_ids
    for document in (catalogue, fixture["catalogue"]):
        items = document["items"]
        links = [item["correctionLink"] for item in items]
        assert len(links) == len(set(links))
        assert all(len(link) <= collector.CORRECTION_URL_MAX_LENGTH for link in links)
        for item in items:
            params = collector.correction_link_params(item["correctionLink"])
            assert params["row-id"] == item["itemId"]
            assert params["card-name"] == item["cardName"]
            assert params["card-number"] == (item["collectorNumber"] or "unknown")
            expected_set = collector._public_text(item["localSetCode"])
            if item["localSetName"]:
                expected_set += " — " + item["localSetName"]
            assert params["set-code"] == expected_set

    bad_links = copy.deepcopy(catalogue)
    bad_links["items"][0]["correctionLink"] = bad_links["items"][1]["correctionLink"]
    assert any("correction link" in error for error in collector.validate_catalogue(
        bad_links, check_asset_bytes=False
    ))

    # Unicode, punctuation, nulls and private producer/consumer state stay bounded
    # and encoded without leaking into the public form context.
    synthetic = copy.deepcopy(fixture["catalogue"]["items"][0])
    synthetic.update({
        "itemId": "item-00000000-0000-5000-8000-000000000099",
        "cardName": "Café / Snorlax? & [proof]",
        "localSetCode": "A&B",
        "localSetName": "Set № / édition",
        "collectorNumber": None,
        "finish": None,
        "foilPattern": None,
        "markings": [{"kind": "stamp", "role": "print-identity", "text": "1st / édition?"}],
        "distribution": {"kind": "promo", "text": "Official & public"},
        "sourceClaimRefs": ["PRIVATE-CONSUMER-STATE"],
        "sourceLinks": ["https://private.invalid/should-not-leak"],
        "evidenceLinks": ["https://private.invalid/evidence"],
    })
    synthetic_link = collector.correction_link(synthetic)
    synthetic_params = collector.correction_link_params(synthetic_link)
    assert synthetic_params["row-id"] == synthetic["itemId"]
    assert synthetic_params["card-name"] == synthetic["cardName"]
    assert synthetic_params["card-number"] == "unknown"
    assert "Caf%C3%A9" in synthetic_link and "%2F" in synthetic_link
    assert "PRIVATE-CONSUMER-STATE" not in synthetic_link
    assert "private.invalid" not in synthetic_link
    assert "Finish%3A+unknown" in synthetic_link
    assert len(synthetic_link) <= collector.CORRECTION_URL_MAX_LENGTH
    assert collector.correction_link(synthetic) == synthetic_link

    long_item = copy.deepcopy(synthetic)
    long_item.update({
        "cardName": "界" * 10_000,
        "localSetName": "長" * 10_000,
        "markings": [{"kind": "stamp", "role": "print-identity", "text": "!" * 10_000}],
    })
    long_link = collector.correction_link(long_item)
    assert len(long_link) <= collector.CORRECTION_URL_MAX_LENGTH
    assert collector.correction_link_params(long_link)["row-id"] == long_item["itemId"]
    assert unquote(collector.correction_link_params(long_link)["current-state"]).startswith("Item kind:")

    counts = catalogue["qualitySummary"]["counts"]
    graph_printing_ids = {
        row["payload"].get("sourcePrintingId")
        for row in graph["entities"] if row["entityType"] == "physical-printing"
    }
    graph_release_ids = {
        row["payload"]["cardReleaseId"]
        for row in graph["entities"] if row["entityType"] == "card-release"
    }
    predecessor_items = predecessor["items"]
    expected_candidates = sum(
        bool(row.get("printingId")) and row["printingId"] not in graph_printing_ids
        for row in predecessor_items
    )
    prior_projection_release_ids = {
        row["cardReleaseId"] for row in catalogue["items"]
        if row["itemKind"] != "research-placeholder" or row["legacyChecklistIds"]
    }
    expected_placeholders = (
        sum(not row.get("printingId") for row in predecessor_items)
        + len(graph_release_ids - prior_projection_release_ids)
    )
    assert counts["items"] == len(catalogue["items"])
    assert counts["verifiedPrintings"] == len([
        row for row in graph["entities"] if row["entityType"] == "physical-printing"
    ])
    assert counts["finishCandidates"] == expected_candidates
    assert counts["researchPlaceholders"] == expected_placeholders
    assert {row["cardReleaseId"] for row in catalogue["items"]} == graph_release_ids
    assert counts["currentKnown"] == counts["verifiedPrintings"]
    assert counts["research"] == counts["finishCandidates"] + counts["researchPlaceholders"]
    build_a_bear_item = next(
        row for row in catalogue["items"]
        if row.get("sourcePrintingId") == "F0119-P01"
        and (row.get("distribution") or {}).get("name") == "Build-A-Bear Workshop"
    )
    assert build_a_bear_item["releaseDate"] is None
    assert build_a_bear_item["releaseDatePrecision"] is None
    dutch_printings = {
        row["physicalPrintingId"]: row
        for row in catalogue["items"]
        if row.get("physicalPrintingId") in {
            "PHYSICAL:F0167-P01", "PHYSICAL:F0167-P02",
            "PHYSICAL:F0174-P01", "PHYSICAL:F0174-P02",
        }
    }
    assert {
        printing_id: (row["finish"], row["edition"])
        for printing_id, row in dutch_printings.items()
    } == {
        "PHYSICAL:F0167-P01": ("holo", "1st Edition"),
        "PHYSICAL:F0167-P02": ("holo", "Unlimited"),
        "PHYSICAL:F0174-P01": ("non-holo", "1st Edition"),
        "PHYSICAL:F0174-P02": ("non-holo", "Unlimited"),
    }
    assert all(
        row["itemKind"] == "verified-printing"
        and row["imageScope"] == "exact-printing"
        and row["imageAssetId"]
        for row in dutch_printings.values()
    )
    latam_svp = next(
        row for row in catalogue["items"]
        if row["cardReleaseId"]
        == "RELEASE:LATAM:Spanish:SVP LA:184:unmapped-work:SPEC-0033"
    )
    assert {
        "kind": latam_svp["itemKind"],
        "progress": latam_svp["progressClass"],
        "work": latam_svp["workId"],
        "finish": latam_svp["finish"],
        "rarity": latam_svp["rarity"]["normalizedId"],
        "date": latam_svp["releaseDate"],
        "datePrecision": latam_svp["releaseDatePrecision"],
        "imageScope": latam_svp["imageScope"],
    } == {
        "kind": "verified-printing",
        "progress": "current-known",
        "work": "WORK:Hops-Snorlax-Extra-Helpings-Dynamic-Press",
        "finish": "holo",
        "rarity": "promo",
        "date": "2025-03-22",
        "datePrecision": "day",
        "imageScope": "exact-printing",
    }
    assert latam_svp["imageAssetId"]
    assert latam_svp["markings"] == [{
        "kind": "set-logo",
        "role": "distribution-promo",
        "text": "Aventuras Compartidas",
    }]
    assert latam_svp["distribution"] == {
        "kind": "prerelease",
        "name": "Aventuras Compartidas Prerelease",
        "region": "MX",
        "date": "2025-03-22",
    }
    assert {
        "https://antiquestore.com.mx/event/pokemon-tcg-journey-together-prerelease/",
        "https://www.pokemon.com/us/news/get-the-pokemon-tcg-scarlet-violet-journey-together-build-battle-box-early",
    } <= set(latam_svp["evidenceLinks"])
    normal_latam_expectations = {
        "RELEASE:LATAM:Spanish:JTG LA:117/159:unmapped-work:SPEC-0035": {
            "work": "WORK:Hops-Snorlax-Extra-Helpings-Dynamic-Press",
            "setName": "Aventuras Compartidas",
            "finish": "holo",
            "rarity": "rare",
            "date": "2025-03-28",
            "distribution": {
                "kind": "booster-set",
                "name": "Aventuras Compartidas",
                "region": "LATAM",
                "date": "2025-03-28",
            },
            "sources": {
                "https://www.pokemon.com/el/jcc-pokemon/cartas-pokemon/series/sv09/117/",
                "https://www.pokemon.com/el/jcc-pokemon/escarlata-y-purpura-aventuras-compartidas",
                "https://www.pokemon.com/static-assets/content-assets/cms2-es-xl/pdf/trading-card-game/checklist/jtg_web_cardlist_latam.pdf",
            },
        },
        "RELEASE:LATAM:Spanish:POR LA:063/088:unmapped-work:SPEC-0036": {
            "work": "WORK:Snorlax-Gormandizer-Collapse",
            "setName": "Equilibrio Perfecto",
            "finish": "non-holo",
            "rarity": "common",
            "date": "2026-03-27",
            "distribution": {
                "kind": "booster-set",
                "name": "Equilibrio Perfecto",
                "region": "LATAM",
                "date": "2026-03-27",
            },
            "sources": {
                "https://www.pokemon.com/el/jcc-pokemon/cartas-pokemon/series/me03/63/",
                "https://www.pokemon.com/el/jcc-pokemon/megaevolucion-equilibrio-perfecto",
                "https://www.pokemon.com/static-assets/content-assets/cms2-es-xl/pdf/trading-card-game/checklist/por_web_cardlist_latam.pdf",
            },
        },
    }
    normal_latam_rows = {
        row["cardReleaseId"]: row for row in catalogue["items"]
        if row["cardReleaseId"] in normal_latam_expectations
    }
    assert set(normal_latam_rows) == set(normal_latam_expectations)
    for release_id, expected in normal_latam_expectations.items():
        row = normal_latam_rows[release_id]
        assert {
            "kind": row["itemKind"],
            "progress": row["progressClass"],
            "work": row["workId"],
            "setName": row["localSetName"],
            "finish": row["finish"],
            "rarity": row["rarity"]["normalizedId"],
            "date": row["releaseDate"],
            "datePrecision": row["releaseDatePrecision"],
            "imageScope": row["imageScope"],
        } == {
            "kind": "verified-printing",
            "progress": "current-known",
            "work": expected["work"],
            "setName": expected["setName"],
            "finish": expected["finish"],
            "rarity": expected["rarity"],
            "date": expected["date"],
            "datePrecision": "day",
            "imageScope": "exact-printing",
        }
        assert row["imageAssetId"]
        assert row["markings"] == []
        assert row["distribution"] == expected["distribution"]
        assert expected["sources"] <= set(row["evidenceLinks"])
        prior_id = collector.item_id(f"research:card-release:{release_id}")
        assert next(
            transition for transition in migrations["transitions"]
            if transition["fromItemId"] == prior_id
        ) == collector.state_transition(prior_id, [row["itemId"]])
    previous_placeholder = collector.item_id(
        "research:card-release:"
        "RELEASE:LATAM:Spanish:SVP LA:184:unmapped-work:SPEC-0033"
    )
    assert next(
        row for row in migrations["transitions"]
        if row["fromItemId"] == previous_placeholder
    ) == collector.state_transition(previous_placeholder, [latam_svp["itemId"]])
    transition_by_source = {
        row["fromItemId"]: row for row in migrations["transitions"]
    }
    assert all(
        transition_by_source[old_id]["toItemIds"]
        == transition_by_source[new_id]["toItemIds"]
        for old_id, new_id in collector.CUMULATIVE_CHECKLIST_REKEYS.items()
    )
    assert catalogue["qualitySummary"]["candidateProgressPolicy"] == {
        "progressClass": "research",
        "status": "owner-decision-accepted",
        "basis": "positive-printing-evidence-or-later-dated-explicit-owner-decision-required-for-promotion",
        "decisionRef": "https://github.com/m4s-ai/snoredex-checklist/issues/5#issuecomment-5407399741",
    }
    assert all(
        isinstance(item["markings"], list)
        and all(marking.get("role") for marking in item["markings"])
        for item in catalogue["items"]
    )
    names_by_work: dict[str, set[str]] = {}
    for item in catalogue["items"]:
        if item["workId"]:
            names_by_work.setdefault(item["workId"], set()).add(item["cardName"])
    assert all(len(names) == 1 for names in names_by_work.values())

    # Fail closed if a research candidate is silently promoted into ordinary
    # collection progress or given an invented physical printing.
    tampered = copy.deepcopy(catalogue)
    candidate = next(row for row in tampered["items"] if row["itemKind"] == "finish-candidate")
    candidate["physicalPrintingId"] = "invented"
    candidate["progressClass"] = "current-known"
    assert any("finish candidate" in error for error in collector.validate_catalogue(
        tampered, graph, check_asset_bytes=False
    ))

    # An established graph release may have no physical printing or predecessor
    # row yet, but it must still remain visible as a neutral research item.
    tampered = copy.deepcopy(catalogue)
    release_placeholder = next(
        row for row in tampered["items"]
        if row["itemKind"] == "research-placeholder" and not row["legacyChecklistIds"]
    )
    tampered["items"].remove(release_placeholder)
    assert any("card-release accounting" in error for error in collector.validate_catalogue(
        tampered, graph, check_asset_bytes=False
    ))

    # Locality is identity: changing the LATAM record into WEST cannot leave a
    # catalogue that passes the contract boundary.
    tampered = copy.deepcopy(catalogue)
    next(row for row in tampered["localizations"] if row["languageTag"] == "es-419")[
        "locality"
    ] = "WEST"
    assert any("LATAM/es-419" in error for error in collector.validate_catalogue(
        tampered, graph, check_asset_bytes=False
    ))

    # Removing even one predecessor transition is data loss, and U0414 remains a
    # visible 1:N conflict rather than an automatic state copy.
    tampered_migrations = copy.deepcopy(migrations)
    predecessor_ids = {row["checklistId"] for row in predecessor_items}
    predecessor_transition = next(
        row for row in tampered_migrations["transitions"]
        if row["fromItemId"] in predecessor_ids
    )
    tampered_migrations["transitions"].remove(predecessor_transition)
    assert any("predecessor" in error for error in collector.validate_migrations(
        tampered_migrations, catalogue, graph, predecessor
    ))
    tampered_migrations = copy.deepcopy(migrations)
    old_id = next(iter(collector.CUMULATIVE_CHECKLIST_REKEYS))
    tampered_migrations["transitions"] = [
        row for row in tampered_migrations["transitions"] if row["fromItemId"] != old_id
    ]
    assert any("cumulative checklist" in error for error in collector.validate_migrations(
        tampered_migrations, catalogue, graph, predecessor
    ))
    tampered_migrations = copy.deepcopy(migrations)
    old_catalogue_id = next(iter(collector.CUMULATIVE_CATALOGUE_REKEYS))
    tampered_migrations["catalogueTransitions"][0]["transitions"] = [
        row for row in tampered_migrations["catalogueTransitions"][0]["transitions"]
        if row["fromItemId"] != old_catalogue_id
    ]
    assert any("previous catalogue" in error for error in collector.validate_migrations(
        tampered_migrations, catalogue, graph, predecessor
    ))

    # A graph-only placeholder has a deterministic alias. If a later catalogue
    # replaces it with multiple physical items, state is not copied blindly.
    split = collector.state_transition(
        release_placeholder["itemId"], ["future-item-b", "future-item-a"]
    )
    assert split == {
        "fromItemId": release_placeholder["itemId"],
        "toItemIds": ["future-item-a", "future-item-b"],
        "changeKind": "split-1:N",
        "automaticStateAction": "none",
        "reconciliation": "requires-user-resolution",
    }
    u0414 = next(row for row in fixture["reconciliationCases"] if row["caseId"] == "U0414-1-to-many")
    assert u0414["expectedAutomaticStateAction"] == "none"
    assert u0414["expectedResolution"] == "requires-user-resolution"

    cases = {row["caseId"]: row for row in fixture["reconciliationCases"]}
    assert set(cases) == {
        "retained-identity", "safe-1-to-1", "retired-to-orphan", "U0414-1-to-many",
        "merge-many-to-1", "unresolved-transition", "missing-transition-chain",
    }
    assert all(row["fromItemId"] == row["fromItemIds"][0] for row in cases.values())
    fixture_item_ids = {row["itemId"] for row in fixture["catalogue"]["items"]}
    assert all(set(row["toItemIds"]) <= fixture_item_ids for row in cases.values())
    assert cases["retained-identity"]["fromItemIds"] == cases["retained-identity"]["toItemIds"]
    assert cases["safe-1-to-1"]["expectedAutomaticStateAction"] == "preserve"
    assert cases["retired-to-orphan"]["expectedStateDisposition"] == "orphan"
    assert len(cases["U0414-1-to-many"]["toItemIds"]) == 2
    assert len(cases["merge-many-to-1"]["fromItemIds"]) == 2
    assert len(cases["merge-many-to-1"]["toItemIds"]) == 1
    for case_id in (
        "retired-to-orphan", "U0414-1-to-many", "merge-many-to-1",
        "unresolved-transition", "missing-transition-chain",
    ):
        assert cases[case_id]["expectedAutomaticStateAction"] == "none"
    assert cases["missing-transition-chain"]["expectedResolution"] == "fail-closed"
    assert cases["missing-transition-chain"]["expectedAdoption"] \
        == "blocked-with-stored-fingerprint-unchanged"

    tampered_migrations = copy.deepcopy(migrations)
    tampered_migrations["catalogueTransitions"][0]["transitions"].pop()
    assert any("previous catalogue" in error for error in collector.validate_migrations(
        tampered_migrations, catalogue, graph, predecessor
    ))

    # The semantic fingerprint excludes only its own field.
    tampered = copy.deepcopy(catalogue)
    tampered["meta"]["catalogueFingerprint"] = "sha256:" + "0" * 64
    assert collector.semantic_fingerprint(tampered) == catalogue["meta"]["catalogueFingerprint"]
    tampered["items"][0]["active"] = False
    assert collector.semantic_fingerprint(tampered) != catalogue["meta"]["catalogueFingerprint"]

    # Runtime publication metadata binds a real commit-shaped identity to the
    # exact deterministic catalogue bytes without contaminating regeneration.
    manifest = deployment.build_manifest(
        ROOT / "collector_catalogue.json", "a" * 40, "2026-08-24T12:00:00Z",
        deployment.DEFAULT_URL,
    )
    assert not deployment.validate_manifest(
        manifest, ROOT / "collector_catalogue.json", "a" * 40
    )
    manifest["byteDigest"] = "sha256:" + "0" * 64
    assert "catalogue byte digest differs" in deployment.validate_manifest(
        manifest, ROOT / "collector_catalogue.json", "a" * 40
    )
    manifest["unexpected"] = True
    assert "deployment manifest fields differ from the contract" in deployment.validate_manifest(
        manifest, ROOT / "collector_catalogue.json", "a" * 40
    )

    print(
        "collector contract regressions passed: "
        f"{counts['items']} items, {counts['assets']} assets, "
        f"{catalogue['meta']['catalogueFingerprint']}"
    )


if __name__ == "__main__":
    main()
