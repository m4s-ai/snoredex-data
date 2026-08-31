#!/usr/bin/env python3
"""Small end-to-end regression for the physical-card evidence loop (#269)."""

from __future__ import annotations

import json
import importlib.util
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent


def read(name: str) -> dict:
    return json.loads((ROOT / "verification" / name).read_text(encoding="utf-8"))


def observation_signature(specimen: dict) -> tuple:
    observation = specimen["physicalObservation"]
    markings = observation.get("markings")
    if isinstance(markings, list):
        markings = tuple(json.dumps(marking, sort_keys=True) for marking in markings)
    return (
        specimen["setCode"],
        specimen["number"].split("/", 1)[0],
        specimen["language"],
        specimen["variant"],
        observation.get("finish"),
        observation.get("edition"),
        markings,
        observation.get("foilPattern"),
        observation.get("cardSize"),
    )


def finish_projector():
    spec = importlib.util.spec_from_file_location("finishes", ROOT / "scripts" / "finishes.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    specimens = read("specimens.json")["specimens"]
    manifest_specimens: dict[str, list[dict]] = defaultdict(list)
    for manifest_path in (ROOT / "verification" / "evidence").glob("issue-*.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for observation in manifest.get("observations", []):
            if observation.get("specimenId"):
                manifest_specimens[observation["specimenId"]].append(observation)
    expected_manifest_specimens = {f"SPEC-{number:04d}" for number in range(120, 146)}
    assert {specimen_id for specimen_id in expected_manifest_specimens
            if len(manifest_specimens[specimen_id]) != 1} == set(), (
        "every PR #323 specimen must occur in exactly one reviewed issue manifest"
    )
    specimen_by_id = {row["specimenId"]: row for row in specimens}
    cardmarket_catalogue_specimens = [
        row for row in specimens
        if urlparse(row.get("photographSource", "")).hostname
        == "product-images.s3.cardmarket.com"
    ]
    assert cardmarket_catalogue_specimens
    assert {
        row["language"] for row in cardmarket_catalogue_specimens
    } <= {"Japanese", "English"}, (
        "Cardmarket product images may support pictured Japanese or English cards only; "
        "catalogue language filters do not establish another localized release"
    )
    manifest_fields = {
        "setCode", "number", "variant", "language", "heldBy", "inspectedFrom",
        "observed", "recordedAt", "citedBy", "physicalObservation", "listingUrl",
    }
    for specimen_id in expected_manifest_specimens:
        manifest_row = manifest_specimens[specimen_id][0]
        specimen_row = specimen_by_id[specimen_id]
        assert {field: manifest_row.get(field) for field in manifest_fields
                if field in manifest_row or field in specimen_row} == {
            field: specimen_row.get(field) for field in manifest_fields
            if field in manifest_row or field in specimen_row
        }
    fixture = [row for row in specimens if row["specimenId"] in {
        "SPEC-0040", "SPEC-0041", "SPEC-0042", "SPEC-0043", "SPEC-0044",
    }]
    assert len(fixture) == 5, "#269 fixture must contain five physical specimens"
    assert len({observation_signature(row) for row in fixture}) == 4

    # A missing edition observation remains missing; the projector must not turn the absence of
    # a stamp into an Unlimited claim.
    no_edition = dict(fixture[0])
    no_edition["physicalObservation"] = {
        key: value for key, value in fixture[0]["physicalObservation"].items()
        if key != "edition"
    }
    assert "edition" not in finish_projector().specimen_printing(no_edition)

    by_signature: dict[tuple, list[str]] = defaultdict(list)
    for specimen in fixture:
        observation = specimen["physicalObservation"]
        assert observation.get("finish") in {"holo", "non-holo"}
        assert observation.get("edition") in {"1st Edition", "Unlimited"}
        if observation["edition"] == "Unlimited":
            assert "explicitly identified" in observation["basis"]
        by_signature[observation_signature(specimen)].append(specimen["specimenId"])
    assert sorted(by_signature.values(), key=lambda ids: ids[0]) == [
        ["SPEC-0040"], ["SPEC-0041"], ["SPEC-0042", "SPEC-0043"], ["SPEC-0044"],
    ]

    finish_units = read("finish_units.json")["units"]
    simplified_chinese_promo = next(
        unit for unit in finish_units if unit["finishUnitId"] == "F0456"
    )
    assert simplified_chinese_promo["finishStatus"]["holo"] == "pending"
    assert all(
        printing["verificationStatus"] != "confirmed"
        for printing in simplified_chinese_promo["printings"]
    ), "the R/C/U finish guide does not establish a Promo-card finish"
    source_first_prints = read("source_first_prints.json")["prints"]
    single_provider_counts = {
        ("ID", "pokemon-card-asia"): 30,
        ("KR", "pokemon-card-korea"): 19,
        ("TH", "pokemon-card-asia"): 25,
        ("TW", "pokemon-card-asia"): 40,
    }
    independently_corroborated_prints = {
        "KR:BS2:30/40:base", "KR:S-P:101:base", "KR:BW7:055/070:base",
        "KR:XY2:066/080:base", "KR:sv5a:051/066:base",
    }
    for provider_key, expected_count in single_provider_counts.items():
        official_prints = [
            row for row in source_first_prints
            if (row["locality"], row["providerId"]) == provider_key
            and row["printId"] not in independently_corroborated_prints
        ]
        assert len(official_prints) == expected_count
        assert all(row["corroborated"] is False for row in official_prints), (
            "matching an existing graph identity is not independent corroboration"
        )
    independently_corroborated_promos = {
        "KR:S-P:101:base", "KR:SM-P:140:base", "KR:XY-P:167:base",
        "TH:SM-P:083:base",
    }
    corroborated_promo_rows = {
        row["printId"]: row for row in source_first_prints
        if row["printId"] in independently_corroborated_promos
    }
    assert set(corroborated_promo_rows) == independently_corroborated_promos
    assert all(row["corroborated"] is True for row in corroborated_promo_rows.values())
    pokumon_only_promos = {
        row["printId"]: row for row in source_first_prints
        if row["printId"] in {"ID:SV-P:278:base", "ID:SV-P:286:base"}
    }
    assert set(pokumon_only_promos) == {"ID:SV-P:278:base", "ID:SV-P:286:base"}
    assert all(row["providerId"] == "pokumon" for row in pokumon_only_promos.values())
    assert all(row["corroborated"] is False for row in pokumon_only_promos.values())
    clf_row = next(
        row for row in source_first_prints if row["printId"] == "TW:CLF:016/032:base"
    )
    assert clf_row["providerId"] == "shopee-tw"
    assert clf_row["corroborated"] is False
    assert "corroboratingSourceUrls" not in clf_row
    s10a_chr_row = next(
        row for row in source_first_prints if row["printId"] == "TW:S10a F:077/071:base"
    )
    assert s10a_chr_row["providerId"] == "ruten"
    assert s10a_chr_row["corroborated"] is True
    assert set(s10a_chr_row["corroboratingSourceUrls"]) == {
        "https://www.nacg.tw/product-details.php?id=149595",
        "https://www.ruten.com.tw/item/22223353127192/",
    }
    svg_row = next(
        row for row in source_first_prints if row["printId"] == "TW:SVG:021/049:base"
    )
    assert svg_row["corroborated"] is False
    assert (svg_row["releaseDate"], svg_row["releaseDatePrecision"]) == (
        "2023-11-10", "day",
    )
    marketplace_override_sources = {
        source["url"]: source
        for unit in finish_units if unit["finishUnitId"] in {"F0037", "F0331"}
        for printing in unit["printings"]
        for source in printing["sources"]
        if source.get("authorityTier") == "seller-listing-photo"
    }
    assert set(marketplace_override_sources) == {
        "https://shopee.tw/product/9736187/25206242683",
        "https://shopee.tw/product/4914178/22786197647",
        "https://shopee.tw/product/6777510/50602680694",
        "https://shopee.tw/product/16896213/51412187955",
        "https://www.ruten.com.tw/item/22223353127192/",
    }
    assert all(
        source["sourceType"] == "Seller listing photograph"
        for source in marketplace_override_sources.values()
    )
    assert all(
        source.get("authorityTier") != "physical-specimen"
        for unit in finish_units if unit["finishUnitId"] in {"F0037", "F0331"}
        for printing in unit["printings"]
        for source in printing["sources"]
    )
    dutch = {
        (unit["number"], printing["edition"]): printing
        for unit in finish_units
        if unit["setCode"] == "JU" and unit["language"] == "Dutch"
        and unit["number"] in {"11", "27"}
        for printing in unit["printings"]
        if printing.get("edition") in {"1st Edition", "Unlimited"}
    }
    assert set(dutch) == {
        ("11", "1st Edition"), ("11", "Unlimited"),
        ("27", "1st Edition"), ("27", "Unlimited"),
    }
    assert len(dutch[("27", "1st Edition")]["sources"]) == 2
    assert dutch[("27", "1st Edition")]["specimenIds"] == ["SPEC-0042", "SPEC-0043"]

    projector = finish_projector()
    standard_scoped = {
        "cardSize": "unknown",
        "sources": [{"evidenceScope": "standard-set"}],
    }
    projector.apply_standard_scope_card_size(standard_scoped)
    assert standard_scoped["cardSize"] == "standard"
    seller_source = projector.specimen_printing(fixture[2])["sources"][0]
    assert seller_source["sourceType"] == "Seller listing photograph"
    archived_seller = next(row for row in specimens if row["specimenId"] == "SPEC-0107")
    assert archived_seller["heldBy"] == "third-party seller"
    assert projector.specimen_printing(archived_seller)["sources"][0]["sourceType"] == (
        "Seller listing photograph"
    )
    pokecardex = specimen_by_id["SPEC-0145"]
    assert projector.specimen_printing(pokecardex)["sources"][0]["sourceType"] == (
        "Third-party scan archive"
    )
    owner_specimen = next(row for row in specimens if row["specimenId"] == "SPEC-0105")
    owner_sources = projector.specimen_printing(owner_specimen)["sources"]
    assert [source["sourceType"] for source in owner_sources] == [
        "Owner-supplied physical card photograph", "Owner attestation (domain expert)"
    ]
    assert owner_specimen["photographSource"] == (
        "https://github.com/m4s-ai/snoredex-data/issues/265#attachment-1"
    )
    assert "retained owner-supplied physical card photograph" in owner_sources[1]["evidence"]
    assert "seller photograph" not in owner_sources[1]["evidence"]
    portuguese_owner_confirmed = {
        row["specimenId"]: projector.specimen_printing(row)
        for row in specimens
        if row["specimenId"] in {"SPEC-0053", "SPEC-0054", "SPEC-0055", "SPEC-0056"}
    }
    assert set(portuguese_owner_confirmed) == {
        "SPEC-0053", "SPEC-0054", "SPEC-0055", "SPEC-0056"
    }
    for specimen_id, printing in portuguese_owner_confirmed.items():
        assert [source["sourceType"] for source in printing["sources"]] == [
            "Seller listing photograph", "Owner attestation (domain expert)"
        ]
        owner_evidence = printing["sources"][1]["evidence"]
        expected_property = "edition" if specimen_id == "SPEC-0055" else "finish"
        assert expected_property in owner_evidence
        assert "retained seller listing photograph" in owner_evidence
        assert printing["sources"][1]["claimFields"] == [expected_property]
        expected_photo_fields = ["identity", "finish"] if specimen_id == "SPEC-0055" else ["identity"]
        assert printing["sources"][0]["claimFields"] == expected_photo_fields

    source_registry = read("source_registry.json")["evidence"]
    for specimen_id in {f"SPEC-{number:04d}" for number in range(319, 325)}:
        marketplace_specimen = specimen_by_id[specimen_id]
        assert marketplace_specimen["heldBy"] == "third-party seller"
        assert projector.specimen_source(marketplace_specimen)["sourceType"] == (
            "Seller listing photograph"
        )
    pokecardex_source = next(
        row for row in source_registry
        if row.get("canonicalUrl") == pokecardex["photographSource"]
    )
    assert pokecardex_source["providerId"] == "pokecardex"
    database_provider_by_specimen = {
        "SPEC-0131": "pkparaiso",
        "SPEC-0132": "wikidex",
        "SPEC-0133": "wikidex",
        "SPEC-0134": "wikidex",
        "SPEC-0135": "wikidex",
        "SPEC-0136": "wikidex",
    }
    registry_by_source = {
        row.get("canonicalUrl") or row["nonUrlEvidenceId"]: row for row in source_registry
    }
    capability_by_source = {
        row["sourceKey"]: row for row in read("source_capability_graph.json")["sourceResolution"]
    }
    for specimen_id, provider_id in database_provider_by_specimen.items():
        specimen = next(row for row in specimens if row["specimenId"] == specimen_id)
        canonical_source = unquote(specimen["photographSource"])
        registry_row = registry_by_source[canonical_source]
        assert registry_row["providerId"] == provider_id
        assert registry_row["dimensions"] == ["identity"]
        assert specimen_id in registry_row["stableIds"]
        assert set(specimen["citedBy"]) <= set(registry_row["stableIds"])
        capability_row = capability_by_source[canonical_source]
        assert capability_row["providerId"] == provider_id
        assert capability_row["dimensions"] == ["identity"]
    target_specimens = {
        row["specimenId"]: row for row in specimens if row["specimenId"] in portuguese_owner_confirmed
    }
    target_urls = {row["photographSource"] for row in target_specimens.values()}
    seller_dimensions = {
        source["canonicalUrl"]: source["dimensions"]
        for source in source_registry
        if source.get("canonicalUrl") in target_urls
    }
    assert seller_dimensions == {
        target_specimens["SPEC-0053"]["photographSource"]: ["identity"],
        target_specimens["SPEC-0054"]["photographSource"]: ["identity"],
        target_specimens["SPEC-0055"]["photographSource"]: ["finish", "identity"],
        target_specimens["SPEC-0056"]["photographSource"]: ["identity"],
    }
    portuguese_ju27 = next(row for row in specimens if row["specimenId"] == "SPEC-0120")
    portuguese_ju27_printing = projector.specimen_printing(portuguese_ju27)
    assert portuguese_ju27_printing["finish"] == "non-holo"
    assert "edition" not in portuguese_ju27_printing
    assert portuguese_ju27_printing["sources"][0]["sourceType"] == "Seller listing photograph"
    portuguese_ju27_source = next(
        source for source in source_registry
        if source.get("canonicalUrl") == portuguese_ju27["photographSource"]
    )
    assert portuguese_ju27_source["dimensions"] == ["finish", "identity"]
    archived_registry_source = next(
        source for source in source_registry
        if source.get("canonicalUrl") == archived_seller["photographSource"]
    )
    assert archived_registry_source["providerId"] == "seller-listing-photo"
    omitted_size = dict(fixture[0])
    omitted_size["physicalObservation"] = {
        key: value for key, value in fixture[0]["physicalObservation"].items()
        if key != "cardSize"
    }
    assert projector.specimen_printing(omitted_size)["cardSize"] == "unknown"
    unknown_specimen = projector.specimen_printing(omitted_size)
    standard_source = {**unknown_specimen, "cardSize": "standard", "sources": []}
    standard_source.pop("specimenIds")
    standard_source.pop("image", None)

    def finalize_sizes(candidates: list[dict]) -> list[dict]:
        projector.refine_specimen_card_sizes(candidates)
        deduplicated: list[dict] = []
        for candidate in candidates:
            projector.add_printing(deduplicated, candidate)
        return deduplicated

    merged_size = [dict(standard_source)]
    projector.add_printing(merged_size, unknown_specimen)
    merged_size = finalize_sizes(merged_size)
    assert len(merged_size) == 1
    assert merged_size[0]["cardSize"] == "standard"
    assert merged_size[0]["specimenIds"] == [fixture[0]["specimenId"]]
    unknown_first = projector.specimen_printing(omitted_size)
    merged_reverse_order = [unknown_first]
    projector.add_printing(merged_reverse_order, dict(standard_source))
    merged_reverse_order = finalize_sizes(merged_reverse_order)
    assert len(merged_reverse_order) == 1
    assert merged_reverse_order[0]["cardSize"] == "standard"
    ambiguous = [dict(standard_source), {**standard_source, "cardSize": "jumbo"}]
    projector.add_printing(ambiguous, projector.specimen_printing(omitted_size))
    projector.refine_specimen_card_sizes(ambiguous)
    assert len(ambiguous) == 3
    assert {printing["cardSize"] for printing in ambiguous} == {"standard", "jumbo", "unknown"}
    assert next(printing for printing in ambiguous if printing.get("specimenIds"))["cardSize"] == "unknown"
    ambiguous_unknown_first = [projector.specimen_printing(omitted_size)]
    projector.add_printing(ambiguous_unknown_first, dict(standard_source))
    projector.add_printing(
        ambiguous_unknown_first, {**standard_source, "cardSize": "jumbo"}
    )
    projector.refine_specimen_card_sizes(ambiguous_unknown_first)
    assert len(ambiguous_unknown_first) == 3
    assert {printing["cardSize"] for printing in ambiguous_unknown_first} == {
        "standard", "jumbo", "unknown"
    }
    assert next(
        printing for printing in ambiguous_unknown_first if printing.get("specimenIds")
    )["cardSize"] == "unknown"
    merged_without_image = projector.specimen_printing(fixture[0])
    merged_without_image.pop("image")
    merged_without_image["_origin"] = "auto"
    merged: list[dict] = [merged_without_image]
    projector.add_printing(merged, projector.specimen_printing(fixture[0]))
    assert merged[0]["image"] == "verification/specimens/SPEC-0040.png"
    assert merged[0]["_origin"] == "specimen"
    patterned = dict(fixture[0])
    patterned["physicalObservation"] = {
        **fixture[0]["physicalObservation"], "foilPattern": "Poké Ball mirror"
    }
    assert projector.specimen_printing(patterned)["foilPattern"] == "poke-ball"
    assert projector.specimen_markings({
        "markings": "STAFF", "markingRole": "distribution-promo"
    }) == [{"kind": "staff", "role": "distribution-promo", "text": "Staff"}]
    assert projector.specimen_markings({
        "markings": "Mewtwo deck silhouette", "markingRole": "distribution-promo"
    }) == [{"kind": "deck-logo", "role": "distribution-promo", "text": "Mewtwo"}]
    assert projector.specimen_markings({
        "markings": "EDIZIONE 1", "markingRole": "print-identity"
    }) == [{"kind": "edition-stamp", "role": "print-identity", "text": "EDIZIONE 1"}]
    mp1_specimen = next(row for row in specimens if row["specimenId"] == "SPEC-0025")
    mp1_candidate = projector.specimen_printing(mp1_specimen)
    assert mp1_candidate is not None
    assert projector.merge_curated_specimen_identity(
        mp1_candidate,
        {
            "finish": "non-holo", "mappedVariants": ["base"],
            "distribution": {"kind": "fixed-deck", "text": "Start Deck 100"},
            "sourceRefs": ["snkrdunk-mp1-012"],
        },
        {"snkrdunk-mp1-012": {"url": mp1_specimen["photographSource"]}},
    )
    assert mp1_candidate["distribution"]["kind"] == "fixed-deck"
    mp1 = next(unit for unit in finish_units
               if unit["setCode"] == "mP1" and unit["number"] == "012"
               and unit["language"] == "Japanese")
    assert len(mp1["printings"]) == 1
    assert mp1["printings"][0]["specimenIds"] == ["SPEC-0025"]
    assert mp1["printings"][0]["distribution"]["kind"] == "fixed-deck"
    indonesian = next(unit for unit in finish_units
                      if unit["setCode"] == "SV-P/ID" and unit["number"] == "117"
                      and unit["language"] == "Indonesian")
    assert len(indonesian["printings"]) == 2
    assert {printing["foilPattern"] for printing in indonesian["printings"]} == {
        "poke-ball", "master-ball"
    }
    italian_cl = next(unit for unit in finish_units
                      if unit["setCode"] == "CL" and unit["number"] == "33"
                      and unit["language"] == "Italian")
    cl_reverse = next(printing for printing in italian_cl["printings"]
                      if printing["finish"] == "reverse-holo")
    assert cl_reverse["mappedVariants"] == ["V1"]
    assert cl_reverse["specimenIds"] == ["SPEC-0106"]
    italian_rr = next(unit for unit in finish_units
                      if unit["setCode"] == "RR" and unit["number"] == "33"
                      and unit["language"] == "Italian")
    rr_reverse = next(printing for printing in italian_rr["printings"]
                      if printing["finish"] == "reverse-holo")
    assert rr_reverse["mappedVariants"] == ["V1"]
    assert rr_reverse["specimenIds"] == ["SPEC-0117"]
    portuguese_ju27_unit = next(unit for unit in finish_units
                                if unit["setCode"] == "JU" and unit["number"] == "27"
                                and unit["language"] == "Portuguese")
    assert portuguese_ju27_unit["availabilityStatus"] == "confirmed"
    assert portuguese_ju27_unit["printings"][0]["specimenIds"] == ["SPEC-0120"]
    italian_wcd = next(unit for unit in finish_units
                       if unit["setCode"] == "WCD23 LOR" and unit["number"] == "LOR 143"
                       and unit["language"] == "Italian")
    assert len(italian_wcd["printings"]) == 1
    wcd_printing = italian_wcd["printings"][0]
    assert wcd_printing["specimenIds"] == ["SPEC-0115", "SPEC-0116"]
    wcd_sources = {source["url"]: source for source in wcd_printing["sources"]}
    assert wcd_sources["https://i.ebayimg.com/images/g/BOgAAOSw6odmeCkP/s-l1600.jpg"][
        "claimFields"
    ] == ["identity"]
    assert wcd_sources["https://i.ebayimg.com/images/g/VzAAAOSw-mhmJCok/s-l1600.jpg"][
        "claimFields"
    ] == ["identity"]
    bulbapedia_url = "https://bulbapedia.bulbagarden.net/wiki/Colorless_Lugia_(TCG)"
    assert wcd_sources[bulbapedia_url]["claimFields"] == ["finish"]
    wcd_registry = next(source for source in source_registry
                        if source.get("canonicalUrl") == bulbapedia_url)
    assert wcd_registry["providerId"] == "bulbapedia"
    assert "finish" in wcd_registry["dimensions"]
    german_units = {
        unit["finishUnitId"]: unit for unit in finish_units
        if unit["language"] == "German"
        and unit["finishUnitId"] in {"F0008", "F0137", "F0527", "F0586", "F0633"}
    }
    assert set(german_units) == {"F0008", "F0137", "F0527", "F0586", "F0633"}
    assert all(unit["availabilityStatus"] == "confirmed" for unit in german_units.values())
    assert german_units["F0008"]["printings"][0]["specimenIds"] == [
        "SPEC-0121", "SPEC-0122"
    ]
    assert german_units["F0008"]["printings"][0]["markings"] == [{
        "kind": "deck-logo", "role": "distribution-promo", "text": "Mewtwo"
    }]
    assert {
        printing["finish"]: printing["specimenIds"]
        for printing in german_units["F0137"]["printings"]
    } == {"non-holo": ["SPEC-0123"], "reverse-holo": ["SPEC-0124"]}
    assert german_units["F0527"]["printings"][0]["specimenIds"] == ["SPEC-0125"]
    german_wcd = german_units["F0586"]["printings"][0]
    assert german_wcd["specimenIds"] == ["SPEC-0126", "SPEC-0127"]
    german_wcd_sources = {source["url"]: source for source in german_wcd["sources"]}
    assert german_wcd_sources[bulbapedia_url]["claimFields"] == ["finish"]
    assert german_wcd_sources[
        "https://i.ebayimg.com/images/g/P9gAAeSwG55ptwIt/s-l1600.jpg"
    ]["claimFields"] == ["identity"]
    assert german_units["F0633"]["printings"][0]["specimenIds"] == ["SPEC-0128"]
    spanish_ju11 = next(unit for unit in finish_units if unit["finishUnitId"] == "F0165")
    assert spanish_ju11["availabilityStatus"] == "confirmed"
    assert len(spanish_ju11["printings"]) == 1
    spanish_ju11_holo = spanish_ju11["printings"][0]
    assert spanish_ju11_holo["printingId"] == "F0165-P01"
    assert spanish_ju11_holo["finish"] == "holo"
    assert "edition" not in spanish_ju11_holo
    assert spanish_ju11_holo["specimenIds"] == ["SPEC-0129", "SPEC-0130"]
    spanish_archive = {
        row["specimenId"]: row for row in specimens
        if row["specimenId"] in {
            "SPEC-0131", "SPEC-0132", "SPEC-0133",
            "SPEC-0134", "SPEC-0135", "SPEC-0136",
        }
    }
    assert len(spanish_archive) == 6
    assert all("physicalObservation" not in row for row in spanish_archive.values())
    corroboration = {
        "U0094": ["SPEC-0120"],
        "U0295": ["SPEC-0121", "SPEC-0122"],
        "U0244": ["SPEC-0123", "SPEC-0124"],
        "U0417": ["SPEC-0125"],
        "U0434": ["SPEC-0126", "SPEC-0127"],
        "U0228": ["SPEC-0128"],
        "U0122": ["SPEC-0129", "SPEC-0130", "SPEC-0133"],
        "U0245": ["SPEC-0131"],
        "U0482": ["SPEC-0132"],
        "U0092": ["SPEC-0134"],
        "U0229": ["SPEC-0135"],
        "U0418": ["SPEC-0136"],
        "U0416": ["SPEC-0137", "SPEC-0138", "SPEC-0139", "SPEC-0143"],
        "U0527": ["SPEC-0140", "SPEC-0141", "SPEC-0142"],
        "U0452": ["SPEC-0144"],
        "U0294": ["SPEC-0145"],
    }
    units = {row["unitId"]: row for row in read("units.json")}
    corroborated_unit_ids = {
        unit_id for unit_id, unit in units.items() if unit.get("corroborated") is True
    }
    for specimen in specimens:
        cited_units = set(specimen.get("citedBy") or []) & corroborated_unit_ids
        if not cited_units:
            continue
        source_key = (
            unquote(specimen["photographSource"])
            if specimen.get("photographSource") else "evidence:inspected-specimen"
        )
        if source_key not in registry_by_source:
            source_key = source_key.split("#", 1)[0]
        if source_key not in registry_by_source:
            source_key = "evidence:inspected-specimen"
        registry_row = registry_by_source[source_key]
        assert "identity" in registry_row["dimensions"]
        assert specimen["specimenId"] in registry_row["stableIds"]
        assert cited_units <= set(registry_row["stableIds"])
        capability_row = capability_by_source[source_key]
        assert "identity" in capability_row["dimensions"]
    primary_checked_at = {
        "U0094": "2026-07-21T16:41:51", "U0295": "2026-07-22T09:26:20",
        "U0244": "2026-07-21T16:41:51", "U0417": "2026-07-21T14:59:21",
        "U0434": "2026-07-22T11:00:43", "U0228": "2026-07-22T17:04:58",
        "U0122": "2026-07-21T16:41:51", "U0245": "2026-07-21T16:41:51",
        "U0482": "2026-07-21T16:56:33", "U0092": "2026-07-21T16:41:51",
        "U0229": "2026-07-22T17:04:58", "U0418": "2026-07-21T14:59:21",
        "U0416": "2026-07-21T14:59:21", "U0527": "2026-07-21T14:59:21",
        "U0452": "2026-07-22T00:41:51", "U0294": "2026-07-22T09:26:20",
    }
    for unit_id, specimen_ids in corroboration.items():
        assert units[unit_id]["corroborated"] is True
        assert units[unit_id]["checkedAt"] == primary_checked_at[unit_id]
        assert all(unit_id in specimen_by_id[specimen_id]["citedBy"]
                   for specimen_id in specimen_ids)
    assert projector.specimen_markings(
        specimen_by_id["SPEC-0145"]["physicalObservation"]
    ) == [{"kind": "deck-logo", "role": "distribution-promo", "text": "Mewtwo"}]
    archive_only_finish_statuses = {
        unit["finishUnitId"]: unit["availabilityStatus"] for unit in finish_units
        if unit["finishUnitId"] in {"F0139", "F0172", "F0179", "F0529", "F0635"}
    }
    assert archive_only_finish_statuses == {
        "F0139": "marketplace-claimed",
        "F0172": "marketplace-claimed",
        "F0179": "marketplace-claimed",
        "F0529": "pending",
        "F0635": "pending",
    }
    conflict = dict(fixture[0])
    conflict["physicalObservation"] = {
        **fixture[0]["physicalObservation"],
        "conflictsWith": ["SPEC-0044"],
    }
    conflicted = projector.specimen_printing(conflict)
    assert conflicted["conflictsWith"] == ["SPEC-0044"]
    reverse = projector.add_reverse_specimen_conflicts(
        projector.specimen_printing(fixture[1]), "SPEC-0041", {"SPEC-0041": {"SPEC-0040"}}
    )
    assert reverse["conflictsWith"] == ["SPEC-0040"]
    projected: list[dict] = []
    projector.add_printing(projected, conflicted)
    assert projected[0]["verificationStatus"] == "pending"
    assert projected[0]["conflictsWith"] == ["SPEC-0044"]
    # A later clean candidate must not promote a printing whose earlier specimen conflict is
    # still present; the conflict remains pending until explicitly resolved.
    clean_candidate = dict(projected[0])
    clean_candidate.pop("conflictsWith")
    clean_candidate["verificationStatus"] = "confirmed"
    projector.add_printing(projected, clean_candidate)
    assert projected[0]["verificationStatus"] == "pending"
    assert projected[0]["conflictsWith"] == ["SPEC-0044"]
    projector.validate_specimen_conflicts({"specimens": [
        {"specimenId": "SPEC-A", "physicalObservation": {"conflictsWith": ["SPEC-B"]}},
        {"specimenId": "SPEC-B"},
    ]})
    try:
        projector.validate_specimen_conflicts({
            "specimens": [{"specimenId": "SPEC-A", "physicalObservation": {
                "conflictsWith": ["SPEC-MISSING"]
            }}]
        })
    except ValueError:
        pass
    else:
        raise AssertionError("unknown conflict target must fail closed")

    graph = read("authoritative_graph.json")
    physical_ids = {
        row["entityId"] for row in graph["entities"]
        if row["entityType"] == "physical-printing"
    }
    assert {"PHYSICAL:F0167-P01", "PHYSICAL:F0167-P02",
            "PHYSICAL:F0174-P01", "PHYSICAL:F0174-P02"} <= physical_ids

    print("physical evidence workflow regression passed: 5 specimens -> 4 printings")


if __name__ == "__main__":
    main()
