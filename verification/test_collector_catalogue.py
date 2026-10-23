#!/usr/bin/env python3
"""Contract, graph-reference and reconciliation regressions for issue #254."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from itertools import permutations
from pathlib import Path
from unittest.mock import patch
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import collector_catalogue as collector  # noqa: E402
import collector_deployment as deployment  # noqa: E402
import authoritative_graph as graph_module  # noqa: E402
import reviewed_release_dates as dates  # noqa: E402
import source_registry as registry_module  # noqa: E402


def read(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def reviewed_release_date_regressions() -> None:
    evidence = "verification/evidence/release-dates-20261011/"
    completion = read(evidence + "completion.json")
    document, reviewed, legacy_dates = dates.load_reviewed_dates()
    catalogue = read("collector_catalogue.json")
    items = {row["itemId"]: row for row in catalogue["items"]}
    legacy = {row["checklistId"]: row for row in read("analysis_checklist.json")["items"]}
    dates.check_reviewed_targets(catalogue["items"], reviewed)
    assert len(completion["items"]) == 116
    assert len({row["itemId"] for row in completion["items"]}) == 116
    # Compare the overlay against the same current canonical inputs. The frozen
    # research baseline is delivery evidence, not a veto on future card intake.
    with patch.object(collector, "load_reviewed_dates", return_value=(document, {}, {})):
        without_dates, _ = collector.build_catalogue()
    base_items = {row["itemId"]: row for row in without_dates["items"]}
    assert set(items) == set(base_items), "date evidence cannot admit or remove items"
    excluded = {"releaseDate", "releaseDatePrecision", "releaseApproximate", "releaseSortKey", "sourceLinks", "evidenceLinks"}
    for item_id, item in items.items():
        assert {key: value for key, value in item.items() if key not in excluded} == {
            key: value for key, value in base_items[item_id].items() if key not in excluded
        }, "date evidence cannot change identity, finish or evidence state"
        if item_id not in reviewed:
            assert item == base_items[item_id], "an unreviewed neighbor cannot inherit a date"
    spec = importlib.util.spec_from_file_location("release_dates_site_owner", ROOT / "scripts/site.py")
    site = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(site)
    for item_id, row in reviewed.items():
        item = items[item_id]
        assert {key: item[key] for key in dates.DATE_FIELDS} == {key: row[key] for key in dates.DATE_FIELDS}
        assert item["releaseSortKey"].split("|", 1)[0] == row["releaseDate"]
        dates.guard_item(row, item)
        assert site.catalogue_date_source(item, {}, {}) == dates.date_source(row)
        for source in row["sources"]:
            assert (ROOT / source["evidencePath"]).is_file()
            assert collector.schema_uri(source["url"]) in item["sourceLinks"]
        for predecessor_id in row["legacyChecklistIds"]:
            assert {key: legacy[predecessor_id][key] for key in dates.DATE_FIELDS} == {key: row[key] for key in dates.DATE_FIELDS}
            assert legacy[predecessor_id]["releaseDateSource"] == dates.date_source(row)
    # #429: a reviewed date sourced from a Unicode page emits an RFC 3986 link and keeps the
    # stored observation URL as the source identity.
    sample_id, sample_row = next(iter(reviewed.items()))
    iri = "https://wiki.52poke.com/wiki/卡比兽（SVI）"
    unicode_row = copy.deepcopy(sample_row)
    unicode_row["sources"][0]["url"] = iri
    overlaid = dates.apply_item_date(
        copy.deepcopy(base_items[sample_id]), {sample_id: unicode_row}, link=collector.schema_uri
    )
    emitted = [value for value in overlaid["sourceLinks"] if unquote(value) == iri]
    assert len(emitted) == 1 and collector.RFC3986_URI.match(emitted[0]), overlaid["sourceLinks"]
    assert overlaid["evidenceLinks"] == overlaid["sourceLinks"]
    assert unicode_row["sources"][0]["url"] == iri
    broken = copy.deepcopy(catalogue)
    broken_items = {row["itemId"]: row for row in broken["items"]}
    broken_items[sample_id].update(
        dates.apply_item_date(copy.deepcopy(base_items[sample_id]), {sample_id: unicode_row})
    )
    broken["meta"]["catalogueFingerprint"] = collector.semantic_fingerprint(broken)
    assert any("RFC 3986" in error for error in collector.catalogue_uri_errors(broken)), \
        "an unencoded reviewed source link must still fail the producer gate"
    # The new registrations grant date metadata only, even on an official host.
    calls = []
    registry_module.record_reviewed_dates(document, lambda *args, **kwargs: calls.append((args, kwargs)), {})
    assert calls and all(args[2] == "date" for args, kwargs in calls)
    example = next(iter(reviewed.values()))
    for field in dates.IDENTITY_FIELDS:
        tampered = {**items[example["itemId"]], field: "different-identity"}
        try:
            dates.apply_item_date(tampered, reviewed)
        except ValueError:
            pass
        else:
            raise AssertionError("date evidence must fail when its guarded identity changes")
    for value, precision in (("2025-02-29", "day"), ("2025-13", "month"), ("2025-06", "day")):
        try:
            dates.validate_date({**example, "releaseDate": value, "releaseDatePrecision": precision})
        except ValueError:
            pass
        else:
            raise AssertionError("invalid calendar dates or precision must fail")
    try:
        dates.check_reviewed_targets([], reviewed)
    except ValueError:
        pass
    else:
        raise AssertionError("stale reviewed item targets must fail")
    invalid = copy.deepcopy(document)
    invalid["releaseDates"]["reviewedItems"].append(example)
    with patch.object(dates.json, "loads", return_value=invalid):
        try:
            dates.load_reviewed_dates()
        except ValueError:
            pass
        else:
            raise AssertionError("duplicate reviewed date targets must fail")
    # Retained excerpts are independently verifiable; full-response hashes are
    # explicitly acquisition metadata, not hashes of these excerpt-only files.
    pairs = (("excerptSha256", "excerpt"), ("excerptSha256", "relevantExcerpt"),
             ("excerptSha256", "content"), ("retainedExcerptSha256", "retainedContent"),
             ("identityExcerptSha256", "identityExcerpt"))
    checked = 0
    stack = [read(evidence + name + ".json") for name in (
        "japanese-promos", "taiwan-china", "korea-indonesia-thailand",
        "western-promos", "special-products", "historical-sets", "official-press-provenance")]
    while stack:
        value = stack.pop()
        if isinstance(value, list):
            stack.extend(value)
        elif isinstance(value, dict):
            for hash_key, text_key in pairs:
                if isinstance(value.get(hash_key), str) and isinstance(value.get(text_key), str):
                    assert hashlib.sha256(value[text_key].encode()).hexdigest() == value[hash_key]
                    checked += 1
            stack.extend(value.values())
    assert checked >= 100


def printing_identity_regressions() -> None:
    graph = read("verification/authoritative_graph.json")
    physicals = collector.entity_payloads(graph, "physical-printing")
    example = next(row for row in physicals if row["physicalPrintingId"] == "PHYSICAL:F0107-P02")
    scope = example["cardReleaseId"]
    original = copy.deepcopy(example)
    # ASTRA F02: the retained two-marking printing and a tied sort-prefix fixture.
    for markings in (
        example["markings"],
        [{**example["markings"][0], "detail": value} for value in ("α", "β", "γ")],
    ):
        keys, core_keys = set(), set()
        for order in permutations(markings):
            printing = {**example, "markings": list(order)}
            key = graph_module.printing_semantic_key(scope, printing).encode("utf-8")
            assert collector.printing_semantic_key(scope, printing) == key
            keys.add(key)
            core_keys.add(collector.printing_semantic_core_key(scope, printing))
        assert len(keys) == len(core_keys) == 1
    assert example == original, "normalization must not mutate source observations"

    key = collector.printing_semantic_key(scope, example)
    core_key = collector.printing_semantic_core_key(scope, example)
    without_edition = json.loads(key)
    del without_edition["edition"]
    assert core_key == collector.canonical_bytes(without_edition)
    for field, value in (
        ("finish", "holo"), ("foilPattern", "star"),
        ("distribution", {"kind": "fixture", "name": "distinct distribution"}),
        ("cardSize", "jumbo"),
    ):
        changed = {**example, field: value}
        assert collector.printing_semantic_key(scope, changed) != key
        assert collector.printing_semantic_core_key(scope, changed) != core_key
    for field, value in (("kind", "set-logo"), ("role", "distribution-promo"), ("text", "other text")):
        changed = copy.deepcopy(example)
        changed["markings"][0][field] = value
        assert collector.printing_semantic_key(scope, changed) != key
        assert collector.printing_semantic_core_key(scope, changed) != core_key
    changed = {**example, "edition": "1st Edition"}
    assert collector.printing_semantic_key(scope, changed) != key
    assert collector.printing_semantic_core_key(scope, changed) == core_key
    assert collector.printing_semantic_key("other release", example) != key
    assert collector.printing_semantic_core_key("other release", example) != core_key
    for semantic_key in (collector.printing_semantic_key, collector.printing_semantic_core_key):
        for invalid in ("stamp", ["stamp"], [{"kind": "stamp"}], [{"kind": "stamp", "role": "", "text": "x"}]):
            try:
                semantic_key(scope, {**example, "markings": invalid})
            except collector.ContractError:
                pass
            else:
                raise AssertionError("shared identity must retain collector input validation")

    # Existing semantic IDs must stay exact; all graph/collector keys must agree.
    for printing in physicals:
        release_id = printing["cardReleaseId"]
        semantic = graph_module.printing_semantic_key(release_id, printing)
        assert collector.printing_semantic_key(release_id, printing) == semantic.encode("utf-8")
        if printing.get("semanticPrintingId"):
            assert graph_module.stable_printing_id(semantic) == printing["semanticPrintingId"]

    legacy = next(row for row in read("analysis_checklist.json")["items"]
                  if row.get("printingId") == example["sourcePrintingId"])
    exact_legacy = {**legacy, "edition": example["edition"]}
    shifted = {**example, "sourcePrintingId": "fixture-new-ordinal",
               "markings": list(reversed(example["markings"]))}
    assert collector.legacy_match_for_physical(
        shifted, {}, set(), {collector.printing_semantic_key(scope, exact_legacy): exact_legacy}, {},
    ) is exact_legacy
    assert collector.legacy_match_for_physical(
        {**shifted, "sourcePrintingId": legacy["printingId"]},
        {legacy["printingId"]: (scope, legacy)}, set(), {}, {},
    ) is legacy
    assert collector.legacy_match_for_physical(
        {**shifted, "edition": "1st Edition"}, {}, set(), {},
        {collector.printing_semantic_core_key(scope, legacy): [legacy]},
    ) is legacy

    # Permuting predecessor observations must preserve every collection ID and
    # both published migration routes, byte for byte, including the catalogue.
    # The raw predecessor fingerprint must still report the changed source bytes.
    predecessor = read("analysis_checklist.json")
    for row in predecessor["items"]:
        if row.get("markings"):
            row["markings"].reverse()
    original_read = collector.read_json
    with patch.object(collector, "read_json", side_effect=lambda path:
                      predecessor if path == collector.CHECKLIST_PATH else original_read(path)):
        catalogue, migrations = collector.build_catalogue()
    assert catalogue == read("collector_catalogue.json")
    expected_migrations = read("collector_migrations.json")
    expected_migrations["meta"]["fromFingerprint"] = collector.sha256_bytes(
        collector.canonical_bytes(predecessor)
    )
    assert migrations == expected_migrations


def reinspection_regressions() -> None:
    items = read("collector_catalogue.json")["items"]
    for locality, code, number, name in (
        ("TH:th", "SV9s", "109", "Hop's Snorlax"),
        ("TW:zh-Hant", "AS5a", "222", "Eevee & Snorlax GX"),
        ("TW:zh-Hant", "sc1b F", "177", "Snorlax VMAX"),
        ("ID:id", "S-P", "052", "Snorlax"),
        ("JP:ja", "s8b", "126", "Snorlax"),
    ):
        matched = [row for row in items if row["localizationId"] == "LOCALIZATION:" + locality
                   and row["localSetCode"] == code and row["collectorNumber"] == number
                   and row["itemKind"] == "verified-printing"]
        assert len(matched) == 1
        assert matched[0]["cardName"] == name
        assert matched[0]["finish"] == "holo"
        assert matched[0]["imageScope"] == "exact-printing"
        assert matched[0]["completenessStatus"] == "positive-evidence-only"
    reverse = next(row for row in items if row.get("finishUnitId") == "F0363"
                   and row["finish"] == "reverse-holo")
    assert reverse["itemKind"] == "finish-candidate", "visible holo cannot confirm a reverse candidate"
    bridged_indonesian_promo = [
        row for row in items
        if row["localizationId"] == "LOCALIZATION:ID:id"
        and row["localSetCode"] == "SV-P"
        and row["collectorNumber"] == "117"
        and row["finish"] == "mirror-holo"
        and row["foilPattern"] == "poke-ball"
    ]
    assert len(bridged_indonesian_promo) == 1
    assert bridged_indonesian_promo[0]["imageScope"] == "exact-printing"


def source_first_finish_decision_regressions() -> None:
    release = {"cardReleaseId": "R", "localSetCode": "M6a", "localNumber": "095/103", "language": "Japanese"}
    decision = {"setCode": "M6a", "number": "095/103", "language": "Japanese",
                "authority": "collection-owner", "decision": "finish-complete", "availableFinishes": ["holo"]}
    printing = {"cardReleaseId": "R", "finish": "holo"}
    resolve = collector.source_first_finish_decisions
    assert resolve([decision], [], {"R": release}, {"P": printing}) == {"R": decision}
    assert collector.item_completeness(decision, None, None) == "owner-adjudicated"
    assert collector.item_completeness(None, None, None) == "positive-evidence-only"
    assert collector.item_completeness(None, None, {"completenessStatus": "pending"}) == "pending"
    assert collector.completeness_fields("positive-evidence-only", decision) == {
        "completenessStatus": "positive-evidence-only"}
    try:
        collector.completeness_fields("owner-adjudicated", None)
    except collector.ContractError:
        pass
    else:
        raise AssertionError("owner closure without its decision was accepted")
    assert resolve([], [], {"R": release}, {"P": printing}) == {}
    assert resolve([decision], [decision], {"R": release}, {}) == {}
    for decisions, releases, printings in (
        ([decision], {"R": release}, {}),
        ([{**decision, "availableFinishes": []}], {"R": release}, {}),
        ([decision], {"R": release}, {"P": printing, "Q": {**printing, "finish": "reverse-holo"}}),
        ([decision], {"R": release}, {"P": {**printing, "finish": None}}),
        ([{**decision, "authority": "external-source"}], {"R": release}, {"P": printing}),
        ([{**decision, "number": "095/105"}], {"R": release}, {"P": printing}),
        ([decision], {}, {"P": printing}),
    ):
        try:
            resolve(decisions, [], releases, printings)
        except collector.ContractError:
            pass
        else:
            raise AssertionError("unsupported source-first finish closure was accepted")


def unicode_source_uri_regressions() -> None:
    # #424: Unicode source IRIs must leave the producer as schema-valid URIs that
    # still name the same resource, and the gate must reject a raw IRI.
    for iri in (
        "https://wiki.52poke.com/wiki/PCG特别套装（TCG）",
        "https://wiki.52poke.com/index.php?title=卡比兽（S4）&oldid=2150661",
        "https://ojamacard.com/product/28693/056-071-คาบิกอน-r-s10bt",
        "https://example.com/a b#frag ment",
    ):
        uri = collector.schema_uri(iri)
        assert collector.RFC3986_URI.match(uri) and uri.isascii(), uri
        assert unquote(uri) == iri, (uri, iri)
        assert collector.schema_uri(uri) == uri
    for conforming in (
        "https://pokumon.com/card/snorlax-082-sv-p-thai-promo/",
        "https://example.com/x%20y?q=%E5%8D%A1&r=1#top",
    ):
        assert collector.schema_uri(conforming) == conforming
    assert collector.schema_uri("https://bücher.example/kabigon") == "https://xn--bcher-kva.example/kabigon"

    catalogue = read("collector_catalogue.json")
    for row in catalogue["items"]:
        for link in (*row["sourceLinks"], *row["evidenceLinks"]):
            assert collector.RFC3986_URI.match(link), (row["itemId"], link)
    broken = copy.deepcopy(catalogue)
    broken["items"][0]["evidenceLinks"] = ["https://wiki.52poke.com/wiki/卡比兽（SVI）"]
    broken["meta"]["catalogueFingerprint"] = collector.semantic_fingerprint(broken)
    assert any("RFC 3986" in error for error in collector.validate_catalogue(broken, check_asset_bytes=False))

    # #424: the catalogue snoredex-checklist actually deploys has a complete route.
    routes = {row["fromFingerprint"]: row for row in read("collector_migrations.json")["catalogueTransitions"]}
    live = routes[collector.LIVE_CONSUMER_CATALOGUE_FINGERPRINT]
    assert live["sourceArtifactCommit"] == "98700119700523ee4939b7539103f7ba61ab03e6"
    assert live["toFingerprint"] == catalogue["meta"]["catalogueFingerprint"]
    covered = [item for row in live["transitions"] for item in row["fromItemIds"]]
    assert sorted(covered) == live["sourceItemIds"], "every deployed item needs exactly one route"


def local_card_name_regressions() -> None:
    names = read("verification/local_card_names.json")
    graph = read("verification/authoritative_graph.json")
    releases = {row["cardReleaseId"] for row in collector.entity_payloads(graph, "card-release")}
    assert set(names["releases"]) <= releases, "local names must target existing card releases"
    assert all(row["value"] and row["evidence"] for row in names["releases"].values())
    assert all(row["value"] and row["evidence"] for row in names["speciesNames"].values())
    sample = {"meta": {"speciesOnlyCardNames": ["Snorlax"]},
              "speciesNames": {"L:de": {"value": "Relaxo"}}, "releases": {"R": {"value": "Hops Relaxo"}}}
    resolve = collector.local_card_name
    assert resolve(sample, "R", "L:de", "Hop's Snorlax", "Native") == "Native"
    assert resolve(sample, "R", "L:de", "Hop's Snorlax", None) == "Hops Relaxo"
    assert resolve(sample, "X", "L:de", "Snorlax", None) == "Relaxo"
    assert resolve(sample, "X", "L:de", "Hop's Snorlax", None) is None, "unlisted patterns are never derived"
    approved = {**sample, "meta": {**sample["meta"], "derivedPatternCardNames": {"Hop's Snorlax": "owner"}},
                "patterns": {"Hop's Snorlax": {"L:de": {"value": "Hops Relaxo"}}}}
    assert resolve(approved, "X", "L:de", "Hop's Snorlax", None) == "Hops Relaxo"
    assert resolve(approved, "X", "L:de", "Snorlax ex", None) is None
    assert resolve(approved, "R2", "L:fr", "Hop's Snorlax", None) is None
    assert resolve(sample, "X", "L:fr", "Snorlax", None) is None
    sources = {row["printId"]: row.get("name") for row in read("verification/source_first_prints.json")["prints"]}
    for item in read("collector_catalogue.json")["items"]:
        exact = names["releases"].get(item["cardReleaseId"])
        if exact and item["localCardName"] not in sources.values():
            assert item["localCardName"] == exact["value"], item["itemId"]
        if item["localCardName"] is None:
            assert item["cardName"] not in names["meta"]["speciesOnlyCardNames"] \
                or item["localizationId"] not in names["speciesNames"], item["itemId"]
            assert item["localizationId"] not in names["patterns"].get(item["cardName"], {}) \
                or item["cardName"] not in names["meta"]["derivedPatternCardNames"], item["itemId"]


def numbering_basis_regressions() -> None:
    # Owner decision 2026-10-22: an unnumbered DP1 card shows its DP Battle Pokédex identifier as
    # collector number, while the empty localNumber stays the finish-unit join key.
    graph = read("verification/authoritative_graph.json")
    release = next(row for row in collector.entity_payloads(graph, "card-release")
                   if row["cardReleaseId"] == "RELEASE:JP:Japanese:DP1:unnumbered:Snorlax-Lv35-Block-Ease-Up")
    assert release["localNumber"] == "" and release["numberingBasis"]["collectorNumber"] == "DPBP#174"
    items = [row for row in read("collector_catalogue.json")["items"] if row["cardReleaseId"] == release["cardReleaseId"]]
    assert items and all((row["collectorNumber"], row["collectorNumberDenominator"]) == ("DPBP#174", None)
                         for row in items)


def edition_rule_regressions() -> None:
    # Set facts decide whether an edition system exists, whatever source created the item.
    absent = collector.edition_system_absent
    assert absent("LOCALIZATION:KR:ko", "XY10", "2016-03-24")
    assert absent("LOCALIZATION:WEST:de", "30C DE", "2026-09-16")
    assert absent("LOCALIZATION:JP:ja", "M6a", "2026-09-16")
    assert not absent("LOCALIZATION:JP:ja", "XY10", "2016-03-18")
    assert not absent("LOCALIZATION:WEST:en", "JU", "1999-06-16")
    assert not absent("LOCALIZATION:JP:ja", "PJU", None)
    items = read("collector_catalogue.json")["items"]
    rule_free = [row["itemId"] for row in items if row["editionAssignmentStatus"] == "unresolved"
                 and absent(row["localizationId"], row["localSetCode"], row["releaseDate"])]
    assert not rule_free, rule_free
    # The printed set size reaches every item of the set in its own regional numbering.
    by_card = {(row["localizationId"], row["localSetCode"], row["collectorNumber"]): row for row in items}
    assert by_card[("LOCALIZATION:WEST:de", "FCO", "77")]["collectorNumberDenominator"] == "124"
    assert by_card[("LOCALIZATION:JP:ja", "XY10", "057")]["collectorNumberDenominator"] == "078"
    assert by_card[("LOCALIZATION:JP:ja", "20th", "047")]["collectorNumberDenominator"] == "072"
    assert by_card[("LOCALIZATION:KR:ko", "20th", "047")]["collectorNumberDenominator"] == "071"
    assert by_card[("LOCALIZATION:JP:ja", "Pt2", "070")]["collectorNumberDenominator"] == "090"
    # A gallery subset ships inside its main set and prints its own run (owner, 2026-10-23).
    assert by_card[("LOCALIZATION:WEST:de", "LOR", "TG10")]["collectorNumberDenominator"] == "TG30"
    assert by_card[("LOCALIZATION:WEST:de", "LOR", "143")]["collectorNumberDenominator"] == "196"
    # Unnumbered Japanese releases print no denominator; that is a fact, not a gap.
    assert all(row["collectorNumberDenominator"] is None for row in items if ":unnumbered:" in row["cardReleaseId"])
    # Card size defaults to standard (owner, 2026-10-23); a possible jumbo twin stays unknown.
    unknown = [row for row in items if row["cardSize"] == "unknown"]
    assert len(unknown) < 30 and any(row["localSetCode"] == "SSH" for row in unknown), len(unknown)


def main() -> None:
    edition_rule_regressions()
    numbering_basis_regressions()
    local_card_name_regressions()
    reviewed_release_date_regressions()
    unicode_source_uri_regressions()
    source_first_finish_decision_regressions()
    m6a = [row for row in read("collector_catalogue.json")["items"]
           if row["localSetCode"] == "M6a" and row["localizationId"] == "LOCALIZATION:JP:ja"]
    assert len(m6a) == 1
    assert (m6a[0]["finish"], m6a[0]["completenessStatus"], m6a[0]["itemKind"]) == (
        "holo", "owner-adjudicated", "verified-printing")
    decisions = {row["adjudicationId"]: row for row in read("verification/owner_adjudications.json")["finishDecisions"]}
    finish_units = {row["finishUnitId"]: row for row in read("verification/finish_units.json")["units"]}
    closed_items = [row for row in read("collector_catalogue.json")["items"]
                    if row["completenessStatus"] == "owner-adjudicated"]
    assert any(row["finishUnitId"] for row in closed_items), "exercise the legacy closure path too"
    for row in closed_items:
        evidence = row["completenessEvidence"]
        decision = decisions[evidence["adjudicationId"]]
        if row["finishUnitId"]:
            unit = finish_units[row["finishUnitId"]]
            assert all(decision[key] == unit[key] for key in ("setCode", "number", "language"))
        assert evidence["evidenceRefs"] == sorted(set(decision["evidenceRefs"]))
        assert all(link.startswith(("http://", "https://")) for link in row["evidenceLinks"])
    assert m6a[0]["completenessEvidence"]["adjudicationId"] == "OAF-20260929-M6a-095-ja"
    assert "verification/evidence/jp-finish-20260929/m6a-owner-determination.json" in m6a[0]["completenessEvidence"]["evidenceRefs"]
    assert all("completenessEvidence" not in row for row in read("collector_catalogue.json")["items"]
               if row["completenessStatus"] != "owner-adjudicated"), "positive evidence alone cannot imply closure"
    for value in (None, 7, "owner upload", "https:///missing-host", "javascript:alert(1)",
                  "https://example.org/a b", "https://[broken", "https://example.org:invalid"):
        assert collector.provenance_url(value) is None, value
    for value in ("https://example.org/a(b)", "https://example.org/a%20b?x=1&y=2#part"):
        assert collector.provenance_url(value) == value
    annotated = "https://www.instagram.com/p/DO6tQd5jNK8/ (carousel image 1)"
    assert collector.physical_specimen_links({"specimenIds": ["S"]},
        {"S": {"photographSource": annotated}}) == {"https://www.instagram.com/p/DO6tQd5jNK8/"}
    specimen = {"S": {"listingUrl": "https://example.org/listing", "photographSource": "owner upload"}}
    for physical in ({"physicalPrintingId": "PHYSICAL:specimen:S"}, {"specimenIds": ["S", "missing"]}):
        assert collector.physical_specimen_links(physical, specimen) == {"https://example.org/listing"}
    assert collector.physical_specimen_links(None, specimen) == set()
    retained = next(s for s in read('verification/specimens.json')['specimens'] if s['specimenId'] == 'SPEC-0146')
    items = read('collector_catalogue.json')['items']
    # The owner's number mapping establishes finish; the photographed editions stay distinct.
    spanish_jungle = [i for i in items if i.get("localizationId") == "LOCALIZATION:WEST:es-ES"
                      and i.get("localSetCode") == "JU" and i.get("collectorNumber") == "27"
                      and i.get("itemKind") == "verified-printing"]
    assert {"1st Edition", "Unlimited"} <= {i.get("edition") for i in spanish_jungle}
    assert all(i["finish"] == "non-holo" for i in spanish_jungle)
    specimens = {s["specimenId"]: s for s in read("verification/specimens.json")["specimens"]}
    assert specimens["SPEC-0522"]["physicalObservation"]["ownerAttestedFields"] == ["finish"]
    assert "ownerAttestedFields" not in specimens["SPEC-0523"]["physicalObservation"]
    matching = [item for item in items if ':CSM2cC:103:' in item['cardReleaseId']]
    assert matching and all({retained['listingUrl'], retained['photographSource']} <= set(item['evidenceLinks'])
                            for item in matching), 'identity-level specimen citations must reach collector provenance'
    assert not any(retained['photographSource'] in item['evidenceLinks'] for item in items
                   if ':CSM2cC:103:' not in item['cardReleaseId']), 'do not borrow the neighboring card evidence'
    for specimen_id in ("SPEC-0495", "SPEC-0496"):
        retained = next(s for s in read("verification/specimens.json")["specimens"] if s["specimenId"] == specimen_id)
        published = next(i for i in read("collector_catalogue.json")["items"]
                         if i.get("physicalPrintingId") == "PHYSICAL:specimen:" + specimen_id)
        assert {retained["listingUrl"], retained["photographSource"]} <= set(published["evidenceLinks"])
    printing_identity_regressions()
    reinspection_regressions()
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
    assert korean_names[("DP", "006")] == "잠만보 LV.X"
    source_first_by_print = {row["printId"]: row for row in source_first["prints"]}
    assert source_first_by_print["KR:sv5a:051/066:base"]["corroborated"] is True
    assert source_first_by_print["KR:sv9:075/100:base"]["corroborated"] is True
    assert source_first_by_print["KR:DP:006:base"]["corroborated"] is True
    assert "https://globalbunjang.com/product/416373605" in source_first_by_print[
        "KR:sv5a:051/066:base"
    ]["corroboratingSourceUrls"]
    assert source_first_by_print["KR:xsv2a:143/165:base"]["corroborated"] is True
    assert source_first_by_print["KR:xsv2a:143/165:base"].get("corroboratingSourceUrls") is None
    units = read("verification/units.json")
    units_by_id = {row["unitId"]: row for row in units}
    for unit_id in ("U0233", "U0257", "U0370", "U0413", "U0541", "U0561", "U0579", "U0623", "U0677", "U0780", "U0790"):
        assert units_by_id[unit_id]["corroborated"] is True
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
    cs2ac_086_release = "RELEASE:CN:S-Chinese:CS2aC:086/115:Snorlax-Gormandize-Body-Slam"
    cs2ac_086_items = [
        row for row in catalogue["items"] if row["cardReleaseId"] == cs2ac_086_release
    ]
    # Owner decision 2026-10-22: the s4 84 via-release is merged into CS2aC 086. Its marketplace
    # finish candidates stay candidates; only the reviewed finishes are verified printings.
    assert {row["finish"] for row in cs2ac_086_items if row["itemKind"] == "verified-printing"} \
        == {"holo", "reverse-holo"}
    assert {(row["finish"], tuple(row["legacyChecklistIds"])) for row in cs2ac_086_items
            if row["itemKind"] == "finish-candidate"} == {
        ("non-holo", ("s4-84-s-chinese-none-non-holo",)),
        ("reverse-holo", ("s4-84-s-chinese-none-reverse-holo",)),
    }
    cs2ac_086_items = [row for row in cs2ac_086_items if row["itemKind"] == "verified-printing"]
    assert all(
        row["collectorNumber"] == "086" and row["collectorNumberDenominator"] == "115"
        for row in cs2ac_086_items
    )
    reverse_086 = next(row for row in cs2ac_086_items if row["finish"] == "reverse-holo")
    assert reverse_086["foilPattern"] == "star"
    assert all(
        row["workId"] == "WORK:Snorlax-Gormandize-Body-Slam"
        and row["workMappingState"] == "mapped-by-explicit-equivalence"
        for row in cs2ac_086_items
    ), "the owner-confirmed s4 084 counterpart mapping must cover every CS2aC 086 variant"
    owner_mapping = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "equivalence-assertion"
        and row["entityId"] == "ASSERT:same-work:U0289:CN:CS2aC:086/115:base"
    )
    assert owner_mapping["assertedBy"] == "collection owner"
    assert owner_mapping["evidenceUrl"] == "https://github.com/m4s-ai/snoredex-data/issues/257"
    gold_mapping = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "equivalence-assertion"
        and row["entityId"] == "ASSERT:same-work:U0592:CN:CS2aC:142/115:base"
    )
    assert gold_mapping["assertedBy"] == "collection owner"
    assert gold_mapping["toId"] == "WORK:Snorlax-Gormandize-Body-Slam"
    cs2ac_142_release = "RELEASE:CN:S-Chinese:CS2aC:142/115:Snorlax-Gormandize-Body-Slam"
    cs2ac_142_items = [
        row for row in catalogue["items"] if row["cardReleaseId"] == cs2ac_142_release
    ]
    assert len(cs2ac_142_items) == 1
    assert cs2ac_142_items[0]["finish"] == "holo"
    assert cs2ac_142_items[0]["collectorNumber"] == "142"
    assert cs2ac_142_items[0]["collectorNumberDenominator"] == "115"
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
    assert korean_profiles["KR\x1fm2a"]["retrieved"] == "2026-09-01"
    assert korean_profiles["KR\x1fsv2a"]["retrieved"] == "2026-09-01"
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

    # GH 33: a generic API printing must not borrow the checklist row that an
    # independently observed 1st Edition printing already matches exactly.
    scope = shifted_physical["cardReleaseId"]
    generic = {**shifted_physical, "edition": None, "sourcePrintingId": "generic"}
    exact_key = collector.printing_semantic_key(scope, shifted_physical)
    for order in permutations([generic, shifted_physical]):
        physical_keys = {collector.printing_semantic_key(scope, row) for row in order}
        matches = [collector.legacy_match_for_physical(
            row, {}, set(), {exact_key: legacy_row},
            {collector.printing_semantic_core_key(scope, legacy_row): [legacy_row]},
            frozenset(physical_keys),
        ) for row in order]
        assert sum(row is legacy_row for row in matches) == 1
        assert matches[order.index(generic)] is None

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
    assert build_a_bear_predecessor["releaseDate"] == "2019-08-29"
    build_a_bear_release = next(
        row for row in releases["variants"]
        if row["setCode"] == "FLF" and row["number"] == "80" and row["variant"] == "V2"
    )
    assert build_a_bear_release["date"] == "2019-08-29"
    assert build_a_bear_release["dateSort"] == "2019-08-29"
    assert "Build-A-Bear_Workshop_collection" in build_a_bear_release["dateSource"]["url"]

    assert not collector.validate_catalogue(catalogue, graph)
    assert not collector.validate_migrations(migrations, catalogue, graph, predecessor)
    assets = {row["assetId"]: row for row in catalogue["assets"]}
    assert all(
        item["imageScope"] == (
            assets[item["imageAssetId"]]["imageScope"]
            if item["imageAssetId"] else "unknown"
        )
        for item in catalogue["items"]
    )
    items_by_asset: dict[str, list[dict]] = {}
    for item in catalogue["items"]:
        if item["imageAssetId"]:
            items_by_asset.setdefault(item["imageAssetId"], []).append(item)
    shared_specimen_assets = {
        asset_id for asset_id, linked_items in items_by_asset.items()
        if assets[asset_id]["path"].startswith("verification/specimens/")
        and len({item.get("physicalPrintingId") or item.get("sourcePrintingId")
                 for item in linked_items}) > 1
    }
    assert shared_specimen_assets
    assert all(assets[aid]["imageScope"] == "card-release" for aid in shared_specimen_assets)
    assert all(
        item["imageScope"] == "card-release"
        for item in catalogue["items"]
        if item["imageAssetId"] in shared_specimen_assets
    )
    mismatched_scope = copy.deepcopy(catalogue)
    mismatched_item = next(
        item for item in mismatched_scope["items"]
        if item["imageAssetId"] in shared_specimen_assets
    )
    mismatched_item["imageScope"] = "exact-printing"
    mismatched_scope["meta"]["catalogueFingerprint"] = collector.semantic_fingerprint(
        mismatched_scope
    )
    assert any(
        "image scope differs" in error
        for error in collector.validate_catalogue(
            mismatched_scope, graph, check_asset_bytes=False
        )
    )
    assert catalogue["meta"]["previousFingerprint"] == collector.PREVIOUS_CATALOGUE_FINGERPRINT
    assert migrations["meta"]["schemaVersion"] == "1.1.0"
    routes = {row["fromFingerprint"]: row for row in migrations["catalogueTransitions"]}
    assert set(routes) == {fingerprint for _commit, fingerprint in collector.PUBLISHED_CATALOGUE_SOURCES}
    current_item_ids = {row["itemId"] for row in catalogue["items"]}
    for commit, fingerprint in collector.PUBLISHED_CATALOGUE_SOURCES:
        source = collector.git_json_at(commit, "collector_catalogue.json")
        route = routes[fingerprint]
        source_item_ids = {row["itemId"] for row in source["items"]}
        old_s5a = next(row["itemId"] for row in source["items"] if row.get("cardReleaseId") == "RELEASE:TW:T-Chinese:via-s5a:unknown-local-set:via-93:Snorlax-Gormandize-Body-Slam:unknown-local-id")
        s5a = next(row for row in route["transitions"] if old_s5a in row["fromItemIds"])
        assert s5a["fromItemIds"] == [old_s5a]
        # A formerly unspecified finish now has observed Holo and an unverified
        # marketplace candidate: never assign the owner's copy automatically.
        assert s5a["toItemIds"] == [
            "item-35662349-00ed-54f6-a073-5ee93b850558",
            "item-b88ffbb2-da60-5a6c-8ab2-c85a5de59950",
        ]
        assert s5a["changeKind"] == "split-1:N"
        assert s5a["automaticStateAction"] == "none"
        assert s5a["reconciliation"] == "requires-user-resolution"
        covered_source_ids = [
            item_id
            for transition in route["transitions"]
            for item_id in transition["fromItemIds"]
        ]
        assert route["sourceArtifactCommit"] == commit
        assert route["sourceItemIds"] == sorted(source_item_ids)
        assert len(covered_source_ids) == len(set(covered_source_ids)) == len(source_item_ids)
        assert set(covered_source_ids) == source_item_ids
        assert route["toFingerprint"] == catalogue["meta"]["catalogueFingerprint"]
        assert route["compatibility"] == "compatible-data-only"
        assert route["rollbackFingerprint"] == fingerprint
        for transition in route["transitions"]:
            sources = transition["fromItemIds"]
            targets = transition["toItemIds"]
            assert transition["fromItemId"] == sources[0]
            assert set(targets) <= current_item_ids
            if transition["automaticStateAction"] == "preserve":
                assert len(sources) == len(targets) == 1
                assert transition["changeKind"] in {"retained", "rekey-1:1"}
            else:
                assert transition["automaticStateAction"] == "none"
                assert transition["reconciliation"] in {
                    "retire-to-orphan", "requires-user-resolution",
                }
    deployed_route = routes[collector.DEPLOYED_CATALOGUE_FINGERPRINT]
    old_bs2 = "item-aedf859e-be3c-5774-8750-b675f1ddd84d"
    current_bs2 = next(row for row in catalogue["items"]
                       if row["cardReleaseId"] == "RELEASE:KR:Korean:BS2:30/40:Snorlax-Lv35-Block-Ease-Up"
                       and row["active"] and row["finish"] == "non-holo")
    assert current_bs2["itemKind"] == "verified-printing"
    assert current_bs2["releaseDate"] == "2010-06-17"
    new_bs2 = current_bs2["itemId"]
    # The pre-#342 publications carry the original item ids; the live consumer
    # catalogue (#424) already holds BS2 as a research placeholder and both mirrors.
    historical_routes = [
        routes[collector.PREVIOUS_CATALOGUE_FINGERPRINT], deployed_route,
    ]
    live_route = routes[collector.LIVE_CONSUMER_CATALOGUE_FINGERPRINT]
    live_bs2 = next(row for row in live_route["transitions"]
                    if row["fromItemIds"] == ["item-20cf798c-be66-58e6-bf68-f3cc437822c4"])
    assert (live_bs2["toItemIds"], live_bs2["changeKind"], live_bs2["automaticStateAction"]) == (
        [new_bs2], "rekey-1:1", "preserve")
    for route in historical_routes:
        bs2 = next(
            row for row in route["transitions"] if old_bs2 in row["fromItemIds"]
        )
        assert bs2["fromItemIds"] == [old_bs2]
        assert bs2["toItemIds"] == [new_bs2]
        assert bs2["changeKind"] == "rekey-1:1"
        assert bs2["automaticStateAction"] == "preserve"
    old_promo_reverse = "item-ba258f3e-4106-5795-87f4-97d9c19a3e42"
    promo_mirror_targets = {
        "item-9e12f0a7-cf6b-58ac-bb90-0d82a72559e8",
        "item-c7eec9be-fb9a-5be1-a093-39b147541339",
    }
    for target in promo_mirror_targets:
        assert next(row for row in live_route["transitions"] if row["fromItemIds"] == [target])[
            "changeKind"] == "retained"
    for route in historical_routes:
        promo_reverse = next(
            row for row in route["transitions"]
            if old_promo_reverse in row["fromItemIds"]
        )
        assert set(promo_reverse["toItemIds"]) == promo_mirror_targets
        assert promo_reverse["changeKind"] == "split-1:N"
        assert promo_reverse["automaticStateAction"] == "none"
        assert promo_reverse["reconciliation"] == "requires-user-resolution"
    assert {
        row["changeKind"] for row in deployed_route["transitions"]
    } == {"retained", "rekey-1:1", "retired-1:0", "split-1:N", "merge-N:1", "unresolved"}
    assert all(
        not row["toItemIds"] and row.get("candidateItemIds")
        for row in deployed_route["transitions"] if row["changeKind"] == "unresolved"
    )
    assert not collector.validate_catalogue(
        fixture["catalogue"], check_asset_bytes=False
    )
    fixture_items = {row["itemId"]: row for row in fixture["catalogue"]["items"]}
    compatibility_cases = fixture["compatibilityCases"]
    assert {case["caseId"] for case in compatibility_cases} == {
        "provider-confirmed-printing",
        "marketplace-finish-candidate",
        "owner-attested-finish-candidate",
        "open-research-placeholder",
    }
    for case in compatibility_cases:
        item = fixture_items[case["collectorItemId"]]
        assert case["legacyChecklistId"] in item["legacyChecklistIds"]
        assert {
            key: item[key]
            for key in ("itemKind", "progressClass", "finishVerificationStatus")
        } == {
            key: case[key]
            for key in ("itemKind", "progressClass", "finishVerificationStatus")
        }
        assert case["expectedCollectionStatus"] == (
            "need" if item["progressClass"] == "current-known" else "research"
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
    # all fixture states) must carry an exact opaque item id and only the
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
    legacy_compatibility = catalogue["qualitySummary"]["legacyCompatibility"]
    predecessor_items = predecessor["items"]
    graph_printing_ids = {
        row["payload"].get("sourcePrintingId")
        for row in graph["entities"] if row["entityType"] == "physical-printing"
    }
    graph_release_ids = {
        row["payload"]["cardReleaseId"]
        for row in graph["entities"] if row["entityType"] == "card-release"
    }
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
    legacy_placeholders = sum(not row.get("printingId") for row in predecessor_items)
    legacy_verified = len(predecessor_items) - expected_candidates - legacy_placeholders
    assert legacy_compatibility == {
        "schema": "snoredex-legacy-collector-compatibility",
        "schemaVersion": "1.0.0",
        "legacyStableId": "checklistId",
        "collectorStableId": "itemId",
        "stateFields": ["itemKind", "progressClass", "finishVerificationStatus"],
        "collectionProjection": {"current-known": "need", "research": "research"},
        "counts": {
            "legacyRows": len(predecessor_items),
            "verifiedPrintings": legacy_verified,
            "finishCandidates": expected_candidates,
            "researchPlaceholders": legacy_placeholders,
            "currentKnown": legacy_verified,
            "research": expected_candidates + legacy_placeholders,
        },
    }
    # Issue #262: preserve exact Thai identity while admitting field-specific evidence.
    thai = [row for row in catalogue["items"]
            if row["active"] and row["localizationId"] == "LOCALIZATION:TH:th"]
    for code, date, url in (
        ("s5a T", "2021-04-30", "https://asia.pokemon-card.com/th/card-search/?pageNo=4"),
        ("s10a T", "2022-07-29", "https://asia.pokemon-card.com/th/archives/1596/"),
    ):
        rows = [row for row in thai if row["localSetCode"] == code]
        # Since the #431 merge, s10a T also holds 058/071, dated by its own source-first row.
        assert rows and all(row["releaseDate"] == date for row in rows)
        assert any(url in row["sourceLinks"] for row in rows)
    for release_fragment, finish, image_url in (
        (":sc3b T:126/158:", "holo", "https://down-th.img.susercontent.com/file/th-11134207-7rash-m5u9t0xfqxstb7"),
        (":sv4a:145/190:", "reverse-holo", "https://i.ebayimg.com/images/g/MkwAAeSw3zdpdq0P/s-l1600.jpg"),
    ):
        row = next(row for row in thai if release_fragment in row["cardReleaseId"]
                   and row["itemKind"] == "verified-printing")
        assert row["finish"] == finish
        assert image_url in row["evidenceLinks"]
    promo = next(row for row in thai if ":SV-P:082/SV-P:" in row["cardReleaseId"])
    assert promo["itemKind"] == "verified-printing" and promo["finish"] == "non-holo"
    assert promo["collectorNumber"] == "082/SV-P"
    assert any(mark["text"] == "CENTRAL PATTANA" for mark in promo["markings"])
    assert "https://pokumon.com/card/snorlax-082-sv-p-thai-promo/" in promo["sourceLinks"]

    build_a_bear_item = next(
        row for row in catalogue["items"]
        if row.get("localSetCode") == "FLF"
        and (row.get("distribution") or {}).get("name") == "Build-A-Bear Workshop"
    )
    assert build_a_bear_item["releaseDate"] == "2019-08-29"
    assert build_a_bear_item["releaseDatePrecision"] == "day"
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
    western_svp_labels = {"LOCALIZATION:WEST:es-ES": "Juntos de Aventuras"}
    western_svp_unknown_labels = {
        "LOCALIZATION:WEST:fr",
        "LOCALIZATION:WEST:de",
        "LOCALIZATION:WEST:it",
        "LOCALIZATION:WEST:pt",
    }
    western_svp_localizations = set(western_svp_labels) | western_svp_unknown_labels
    western_svp_regular = {
        row["localizationId"]: row
        for row in catalogue["items"]
        if row.get("collectorNumber") == "184"
        and (row.get("distribution") or {}).get("kind") == "prerelease"
        and row.get("localizationId") in western_svp_localizations
    }
    western_svp_rows = [
        row for row in catalogue["items"]
        if row.get("collectorNumber") == "184"
        and row.get("localizationId") in western_svp_localizations
    ]
    assert len(western_svp_rows) == 2 * len(western_svp_localizations)
    assert {
        (row.get("distribution") or {}).get("kind") for row in western_svp_rows
    } == {"prerelease", "prerelease-staff"}
    assert set(western_svp_regular) == western_svp_localizations
    for localization_id, label in western_svp_labels.items():
        row = western_svp_regular[localization_id]
        assert row["markings"] == [{
            "kind": "set-logo",
            "text": label,
            "role": "distribution-promo",
        }]
        assert row["distribution"] == {
            "kind": "prerelease",
            "name": f"{label} Prerelease",
        }
    for localization_id in western_svp_unknown_labels:
        rows = [row for row in western_svp_rows if row["localizationId"] == localization_id]
        regular = next(row for row in rows if row["distribution"]["kind"] == "prerelease")
        staff = next(row for row in rows if row["distribution"]["kind"] == "prerelease-staff")
        assert regular["markings"] == []
        assert regular["distribution"] == {"kind": "prerelease", "name": None}
        assert staff["markings"] == [{
            "kind": "staff",
            "text": "Staff",
            "role": "distribution-promo",
        }]
        assert staff["distribution"] == {"kind": "prerelease-staff", "name": None}
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
    ) == collector.state_transition(
        previous_placeholder,
        [
            row["itemId"]
            for row in catalogue["items"]
            if row["cardReleaseId"]
            == "RELEASE:LATAM:Spanish:SVP LA:184:unmapped-work:SPEC-0033"
        ],
    )
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
    placeholder_graph = copy.deepcopy(graph)
    placeholder_graph["entities"] = [
        row for row in placeholder_graph["entities"]
        if not (row["entityType"] == "physical-printing"
                and row["payload"].get("cardReleaseId") == current_bs2["cardReleaseId"])
    ]
    original_read = collector.read_json
    with patch.object(collector, "read_json", side_effect=lambda path:
                      placeholder_graph if path == collector.GRAPH_PATH else original_read(path)):
        placeholder_catalogue, _ = collector.build_catalogue()
    tampered = copy.deepcopy(placeholder_catalogue)
    release_placeholder = next(
        row for row in tampered["items"]
        if row["itemKind"] == "research-placeholder"
        and row["cardReleaseId"] == current_bs2["cardReleaseId"]
    )
    assert not release_placeholder["legacyChecklistIds"]
    assert release_placeholder["progressClass"] == "research"
    tampered["items"].remove(release_placeholder)
    assert any("card-release accounting" in error for error in collector.validate_catalogue(
        tampered, placeholder_graph, check_asset_bytes=False
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
    tampered_migrations["catalogueTransitions"][0]["transitions"].pop()
    assert any("published catalogue transition" in error for error in collector.validate_migrations(
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
    assert any("published catalogue transition" in error for error in collector.validate_migrations(
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
