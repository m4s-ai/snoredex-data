#!/usr/bin/env python3
"""Build and constrain the local set catalogue graph (#146).

The catalogue starts from ``verification/set_catalogue_sources.json`` rather than from Snorlax
membership. ADR-0001's dry-run is read only to link already established set editions and card
releases; this script has no path that can create a card release from set availability.

Every build starts from empty Python collections and an empty in-memory SQLite database. It emits
reversible source-record dispositions, the graph nodes/edges, compatibility-loss reports, and the
adversarial fixtures required by #146.

    python scripts/set_catalogue_dryrun.py
    python scripts/set_catalogue_dryrun.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATH = ROOT / "verification" / "set_catalogue_sources.json"
IDENTITY_PATH = ROOT / "verification" / "print_identity_dryrun.json"
RARITY_PATH = ROOT / "verification" / "rarity_catalogue.json"
SCHEMA_PATH = ROOT / "verification" / "set_catalogue_schema.sql"
OUTPUT_PATH = ROOT / "verification" / "set_catalogue_dryrun.json"
SCHEMA_VERSION = "0.2.0"

LANGUAGE_SCRIPT = {
    "English": "Latn",
    "French": "Latn",
    "German": "Latn",
    "Italian": "Latn",
    "Spanish": "Latn",
    "Portuguese": "Latn",
    "Dutch": "Latn",
    "Polish": "Latn",
    "Czech": "Latn",
    "Hungarian": "Latn",
    "Russian": "Cyrl",
    "Japanese": "Jpan",
    "Korean": "Hang",
    "T-Chinese": "Hant",
    "S-Chinese": "Hans",
    "Indonesian": "Latn",
    "Thai": "Thai",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(material).hexdigest()[:16]}"


def local_set_id(locality: str, raw_code: str) -> str:
    return f"LOCALSET:{locality}:{quote(raw_code, safe='')}"


def source_assertion(source_id: str, kind: str, target_field: str,
                     target_id: str) -> dict[str, Any]:
    return {
        "sourceAssertionId": stable_id("SOURCEASSERTION", source_id, kind, target_id),
        "sourceRecordId": source_id,
        "assertionKind": kind,
        target_field: target_id,
    }


def build_rarity_map(catalogue: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in catalogue["rarities"]:
        labels = [entry["name"], entry.get("bulbapediaSetlistLabel")]
        labels.extend(entry.get("alsoKnownAs", []))
        for label in labels:
            if label:
                result[label.casefold()] = entry["rarityId"]
    # Cardmarket's source-native order differs from Bulbapedia's label order.
    result["holo rare"] = "holofoil-rare"
    return result


def condition_matches(condition: dict[str, Any], collector_number: str,
                      rarity_values: set[str]) -> bool:
    prefix = condition.get("collectorNumberPrefix")
    if prefix is not None and not collector_number.startswith(prefix):
        return False
    not_prefix = condition.get("collectorNumberNotPrefix")
    if not_prefix is not None and collector_number.startswith(not_prefix):
        return False
    if "rarityIn" in condition and not rarity_values.intersection(condition["rarityIn"]):
        return False
    return True


def profile_result(profile: dict[str, Any], language: str, collector_number: str,
                   rarity_values: set[str]) -> bool | None:
    if language not in profile["languageScope"]:
        return None
    for rule in sorted(profile["rules"], key=lambda item: -item["priority"]):
        if condition_matches(rule["condition"], collector_number, rarity_values):
            return rule["effect"] == "include"
    return None


def build(source_doc: dict[str, Any], identity: dict[str, Any],
          rarity_catalogue: dict[str, Any]) -> dict[str, Any]:
    source_records = source_doc["sourceRecords"]
    source_ids = [record["sourceRecordId"] for record in source_records]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("set catalogue sourceRecordIds are not unique")

    local_sets: dict[str, dict[str, Any]] = {}
    local_set_by_key: dict[tuple[str, str], str] = {}
    local_set_by_code: dict[str, list[str]] = defaultdict(list)
    set_editions: dict[str, dict[str, Any]] = {}
    edition_by_key: dict[tuple[str, str, str], str] = {}
    release_events: list[dict[str, Any]] = []
    finish_profiles: list[dict[str, Any]] = []
    card_release_refs: list[dict[str, Any]] = []
    rarity_claims: list[dict[str, Any]] = []
    profile_finish_claims: list[dict[str, Any]] = []
    alias_assertions: list[dict[str, Any]] = []
    assertions: dict[str, dict[str, Any]] = {}
    dispositions: dict[str, dict[str, Any]] = {}
    availability_records: list[dict[str, Any]] = []
    edition_candidates: list[dict[str, Any]] = []
    cross_locality_rarity: list[dict[str, Any]] = []

    def assert_source(row: dict[str, Any]) -> None:
        assertions[row["sourceAssertionId"]] = row

    def disposition(source_id: str, state: str, target: str | None, reason: str) -> None:
        if source_id in dispositions:
            raise ValueError(f"source record received two dispositions: {source_id}")
        dispositions[source_id] = {
            "sourceRecordId": source_id,
            "disposition": state,
            "targetRef": target,
            "reason": reason,
        }

    def add_alias(record: dict[str, Any], target_id: str) -> None:
        raw = record["raw"]
        raw_code = raw.get("localCode")
        if not raw_code:
            return
        alias_assertions.append({
            "aliasAssertionId": stable_id(
                "ALIAS", record["sourceRecordId"], str(raw_code), target_id),
            "sourceRecordId": record["sourceRecordId"],
            "provider": record["provider"],
            "rawIdentifier": str(raw_code),
            "targetType": "local-set",
            "localSetId": target_id,
            "setEditionId": None,
            "relationship": "identifies",
            "reversibleProjection": True,
        })

    def ensure_local_set(record: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        raw = record["raw"]
        locality = raw["locality"]
        code = raw["localCode"]
        key = (locality, code)
        existing_id = local_set_by_key.get(key)
        if existing_id:
            node = local_sets[existing_id]
            node["sourceRecordIds"].append(record["sourceRecordId"])
            if raw.get("localName") and raw["localName"] not in node["observedNames"]:
                node["observedNames"].append(raw["localName"])
            return node, False
        node_id = local_set_id(locality, code)
        node = {
            "localSetId": node_id,
            "locality": locality,
            "localCode": code,
            "observedNames": [raw["localName"]] if raw.get("localName") else [],
            "productKind": raw.get("productKind", "physical-card-set-or-product"),
            "sourceRecordIds": [record["sourceRecordId"]],
        }
        local_sets[node_id] = node
        local_set_by_key[key] = node_id
        local_set_by_code[code].append(node_id)
        return node, True

    def ensure_edition(node: dict[str, Any], language: str, script: str,
                       evidence_id: str, preferred_id: str | None = None) -> dict[str, Any]:
        key = (node["localSetId"], language, script)
        existing_id = edition_by_key.get(key)
        if existing_id:
            edition = set_editions[existing_id]
            if evidence_id not in edition["establishingEvidenceIds"]:
                edition["establishingEvidenceIds"].append(evidence_id)
            return edition
        edition_id = preferred_id or (
            f"EDITION:{node['locality']}:{language}:{node['localCode']}")
        edition = {
            "setEditionId": edition_id,
            "localSetId": node["localSetId"],
            "locality": node["locality"],
            "language": language,
            "script": script,
            "localCode": node["localCode"],
            "state": "identified",
            "establishingEvidenceIds": [evidence_id],
        }
        set_editions[edition_id] = edition
        edition_by_key[key] = edition_id
        return edition

    # Provider-visible local-set records establish the discovery basis. Code-card-only products
    # remain reversible positive exclusions rather than pretending to be physical card sets.
    local_profile_kinds = {
        "legacy-cardmarket-set-profile", "source-first-local-set-profile",
        "provider-local-set-profile",
    }
    for record in source_records:
        if record["sourceKind"] not in local_profile_kinds:
            continue
        raw = record["raw"]
        if raw.get("productKind") == "code-card-product":
            disposition(
                record["sourceRecordId"], "positively-excluded", None,
                "every provider product in this profile is a digital code card, not a physical TCG card set",
            )
            continue
        if not raw.get("locality") or not raw.get("localCode"):
            disposition(
                record["sourceRecordId"], "needs-evidence", None,
                "the provider record does not identify both a locality and a local code",
            )
            continue
        node, created = ensure_local_set(record)
        state = "mapped" if created else "matched"
        disposition(
            record["sourceRecordId"], state, node["localSetId"],
            "provider locality and raw local code identify this local-set node",
        )
        add_alias(record, node["localSetId"])
        assert_source(source_assertion(
            record["sourceRecordId"], "asserts-local-set", "localSetId", node["localSetId"]))

    # Link only existence-bearing editions from ADR-0001. Unknown local identifiers stay visible
    # as candidates and cannot gain a local-set parent from a marketplace code.
    for incoming in identity["setEditions"]:
        key = (incoming["locality"], incoming.get("localSetCode"))
        node_id = local_set_by_key.get(key) if incoming.get("localIdentifierKnown") else None
        if not node_id:
            edition_candidates.append({
                "setEditionId": incoming["setEditionId"],
                "disposition": "needs-evidence",
                "reason": (
                    "local identifier is not established" if not incoming.get("localIdentifierKnown")
                    else "no independent local-set source record matches locality and code"
                ),
            })
            continue
        node = local_sets[node_id]
        edition = ensure_edition(
            node, incoming["language"], incoming["script"],
            incoming["establishingClaimIds"][0], incoming["setEditionId"],
        )
        for claim_id in incoming["establishingClaimIds"]:
            if claim_id not in edition["establishingEvidenceIds"]:
                edition["establishingEvidenceIds"].append(claim_id)

    # Release records create event nodes only when locality, local set, language and market scope
    # are explicit. The record may establish an edition without establishing a single card in it.
    for record in source_records:
        if record["sourceKind"] != "release-date-record":
            continue
        raw = record["raw"]
        node_id = local_set_by_key.get((raw.get("locality"), raw.get("localCode")))
        if not node_id or not raw.get("languageScope") or not raw.get("marketScopes"):
            disposition(
                record["sourceRecordId"], "needs-evidence", None,
                "release source lacks an unambiguous local set, printed language, or market scope",
            )
            continue
        node = local_sets[node_id]
        language = raw["languageScope"]
        script = LANGUAGE_SCRIPT[language]
        edition = ensure_edition(node, language, script, record["sourceRecordId"])
        assert_source(source_assertion(
            record["sourceRecordId"], "asserts-set-edition", "setEditionId",
            edition["setEditionId"]))
        event_id = stable_id("EVENT", record["sourceRecordId"])
        event = {
            "releaseEventId": event_id,
            "localSetId": node_id,
            "setEditionIds": [edition["setEditionId"]],
            "eventKind": "launch-wave" if raw.get("note") else "launch",
            "dateValue": raw["date"],
            "datePrecision": raw["datePrecision"],
            "approximate": raw["approximate"],
            "status": raw["status"],
            "timezone": None,
            "marketScopes": raw["marketScopes"],
            "marketScopeBasis": raw["marketScopeBasis"],
            "sourceRecordId": record["sourceRecordId"],
            "linkBasis": "source record explicitly scopes this launch to the edition language and markets",
        }
        release_events.append(event)
        disposition(
            record["sourceRecordId"], "mapped", event_id,
            "dated provider field maps to a market-scoped release event, not a set scalar",
        )
        add_alias(record, node_id)
        assert_source(source_assertion(
            record["sourceRecordId"], "asserts-release-event", "releaseEventId", event_id))

    # Edition-availability rows can establish language editions without a Snorlax. A finish rule
    # is emitted only where the provider makes one; rarity counts remain source-native summaries.
    for record in source_records:
        if record["sourceKind"] != "edition-availability-record":
            continue
        raw = record["raw"]
        code = raw.get("localCode")
        candidates = local_set_by_code.get(code, []) if code else []
        if len(candidates) != 1:
            disposition(
                record["sourceRecordId"], "needs-evidence", None,
                "edition availability has no unambiguous locality-bearing local-set identifier",
            )
            availability_records.append({
                "sourceRecordId": record["sourceRecordId"],
                "localSetId": None,
                "rarities": raw["rarities"],
                "disposition": "needs-evidence",
            })
            continue
        node = local_sets[candidates[0]]
        editions = []
        for language in raw.get("languages") or []:
            edition = ensure_edition(
                node, language, LANGUAGE_SCRIPT[language], record["sourceRecordId"])
            editions.append(edition)
            assert_source(source_assertion(
                record["sourceRecordId"], "asserts-set-edition", "setEditionId",
                edition["setEditionId"]))
        availability_records.append({
            "sourceRecordId": record["sourceRecordId"],
            "localSetId": node["localSetId"],
            "setEditionIds": [item["setEditionId"] for item in editions],
            "rarities": raw["rarities"],
            "disposition": "mapped",
        })
        add_alias(record, node["localSetId"])
        if not raw.get("finishProfile"):
            disposition(
                record["sourceRecordId"], "mapped", node["localSetId"],
                "source-native edition rarity summary is retained without inferring a finish profile",
            )
            continue
        profile_id = stable_id("FINISHPROFILE", record["sourceRecordId"])
        rules = [
            {
                "finishProfileRuleId": stable_id("FINISHRULE", profile_id, "exclude-h32"),
                "priority": 100,
                "effect": "exclude",
                "finish": "reverse-holo",
                "condition": {"collectorNumberPrefix": "H/"},
                "sourceRecordId": record["sourceRecordId"],
            },
            {
                "finishProfileRuleId": stable_id("FINISHRULE", profile_id, "secret-rare"),
                "priority": 20,
                "effect": "include",
                "finish": "reverse-holo",
                "condition": {"rarityIn": ["Secret Rare", "secret-rare"]},
                "sourceRecordId": record["sourceRecordId"],
            },
            {
                "finishProfileRuleId": stable_id("FINISHRULE", profile_id, "numbered"),
                "priority": 10,
                "effect": "include",
                "finish": "reverse-holo",
                "condition": {"collectorNumberNotPrefix": "H/"},
                "sourceRecordId": record["sourceRecordId"],
            },
        ]
        profile = {
            "finishProfileId": profile_id,
            "localSetId": node["localSetId"],
            "setEditionIds": [item["setEditionId"] for item in editions],
            "languageScope": list(raw["languages"]),
            "scopePrecision": "exact",
            "closedWithinScope": bool(raw["finishProfile"]["closedWithinScope"]),
            "closureScope": "reverse-holo availability for setlist cards, excluding the H/32 subset",
            "closureAuthority": "equivalent-explicit-complete-statement",
            "closedFinishQuestions": ["reverse-holo"],
            "sourceRecordId": record["sourceRecordId"],
            "sourceStatement": raw["finishProfile"]["statement"],
            "rules": rules,
        }
        finish_profiles.append(profile)
        disposition(
            record["sourceRecordId"], "mapped", profile_id,
            "explicit language-scoped finish statement maps with its H/32 exception intact",
        )
        assert_source(source_assertion(
            record["sourceRecordId"], "asserts-finish-profile", "finishProfileId", profile_id))

    # Preserve Cardmarket rarity at the card-release grain only when the listing locality and
    # release locality agree. Cross-locality inherited listings are held for a local source.
    product_index: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for record in source_records:
        if record["sourceKind"] != "legacy-cardmarket-set-profile":
            continue
        for product in record["raw"].get("products", []):
            product_index[product["productUrl"]] = (record, product)

    rarity_map = build_rarity_map(rarity_catalogue)
    release_by_id: dict[str, dict[str, Any]] = {}
    # Count the held claims before filtering to catalogue-linked releases. This preserves the
    # measurable cross-locality problem even when ADR-0001 correctly leaves the local identifiers
    # unresolved and this catalogue therefore refuses to import the release reference.
    for incoming in identity["cardReleases"]:
        for product_url in incoming.get("legacyProducts", []):
            indexed = product_index.get(product_url)
            if not indexed:
                continue
            source_record, product = indexed
            source_locality = source_record["raw"]["locality"]
            if source_locality == incoming["locality"]:
                continue
            cross_locality_rarity.append({
                "cardReleaseId": incoming["cardReleaseId"],
                "sourceRecordId": source_record["sourceRecordId"],
                "sourceProductKey": product_url,
                "sourceLocality": source_locality,
                "releaseLocality": incoming["locality"],
                "sourceNativeValue": product.get("rarity"),
                "disposition": "needs-local-rarity-source",
            })
    for incoming in identity["cardReleases"]:
        edition = set_editions.get(incoming["setEditionId"])
        if not edition:
            continue
        release = {
            "cardReleaseId": incoming["cardReleaseId"],
            "setEditionId": incoming["setEditionId"],
            "collectorNumber": incoming["localNumber"],
            "origin": "print-identity-dryrun",
        }
        card_release_refs.append(release)
        release_by_id[release["cardReleaseId"]] = release
        for product_url in incoming.get("legacyProducts", []):
            indexed = product_index.get(product_url)
            if not indexed:
                continue
            source_record, product = indexed
            source_locality = source_record["raw"]["locality"]
            if source_locality != incoming["locality"]:
                continue
            if not product.get("rarity"):
                continue
            claim_id = stable_id(
                "RARITYCLAIM", incoming["cardReleaseId"], product_url,
                product["rarity"])
            claim = {
                "rarityClaimId": claim_id,
                "cardReleaseId": incoming["cardReleaseId"],
                "sourceRecordId": source_record["sourceRecordId"],
                "sourceProvider": "cardmarket",
                "sourceVocabulary": "cardmarket-2026-07-21",
                "sourceNativeValue": product["rarity"],
                "normalizedRarityId": rarity_map.get(product["rarity"].casefold()),
                "sourceProductKey": product_url,
            }
            rarity_claims.append(claim)
            assert_source(source_assertion(
                source_record["sourceRecordId"], "asserts-rarity-claim", "rarityClaimId", claim_id))

    rarity_by_release: dict[str, set[str]] = defaultdict(set)
    for claim in rarity_claims:
        rarity_by_release[claim["cardReleaseId"]].add(claim["sourceNativeValue"])
        if claim["normalizedRarityId"]:
            rarity_by_release[claim["cardReleaseId"]].add(claim["normalizedRarityId"])

    # A profile projects only onto existing ADR-0001 release references. It establishes a finish
    # claim but cannot add a collector-number slot to the graph.
    profiles_by_edition: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for profile in finish_profiles:
        for edition_id in profile["setEditionIds"]:
            profiles_by_edition[edition_id].append(profile)
    for release in card_release_refs:
        edition = set_editions[release["setEditionId"]]
        for profile in profiles_by_edition.get(release["setEditionId"], []):
            result = profile_result(
                profile, edition["language"], release["collectorNumber"],
                rarity_by_release[release["cardReleaseId"]])
            if result is True:
                profile_finish_claims.append({
                    "profileFinishClaimId": stable_id(
                        "PROFILEFINISHCLAIM", profile["finishProfileId"],
                        release["cardReleaseId"], "reverse-holo"),
                    "finishProfileId": profile["finishProfileId"],
                    "cardReleaseId": release["cardReleaseId"],
                    "finish": "reverse-holo",
                    "state": "established-by-profile",
                    "closesCompleteFinishList": False,
                })

    # Real specimen conflicts are positive observations outside a profile's closed finish
    # question. A non-observation is deliberately never compared.
    finish_conflicts: list[dict[str, Any]] = []
    for printing in identity["physicalPrintings"]:
        if not printing.get("establishingSpecimenId"):
            continue
        release = release_by_id.get(printing["cardReleaseId"])
        if not release:
            continue
        edition = set_editions[release["setEditionId"]]
        for profile in profiles_by_edition.get(release["setEditionId"], []):
            if printing["finish"] not in profile["closedFinishQuestions"]:
                continue
            allowed = profile_result(
                profile, edition["language"], release["collectorNumber"],
                rarity_by_release[release["cardReleaseId"]])
            if allowed is False:
                finish_conflicts.append({
                    "finishProfileId": profile["finishProfileId"],
                    "cardReleaseId": release["cardReleaseId"],
                    "specimenId": printing["establishingSpecimenId"],
                    "observedFinish": printing["finish"],
                    "resolution": "conflict-needs-adjudication",
                })

    # Every source record must terminate in exactly one state.
    for record in source_records:
        if record["sourceRecordId"] not in dispositions:
            disposition(
                record["sourceRecordId"], "needs-evidence", None,
                "source kind is retained but not yet mapped by schema version 0.1.0",
            )
    if set(dispositions) != set(source_ids):
        raise ValueError("source-record accounting is not exact")

    local_set_list = sorted(local_sets.values(), key=lambda item: item["localSetId"])
    for node in local_set_list:
        node["observedNames"].sort()
        node["sourceRecordIds"].sort()
    edition_list = sorted(set_editions.values(), key=lambda item: item["setEditionId"])
    for edition in edition_list:
        edition["establishingEvidenceIds"].sort()
    release_events.sort(key=lambda item: item["releaseEventId"])
    finish_profiles.sort(key=lambda item: item["finishProfileId"])
    card_release_refs.sort(key=lambda item: item["cardReleaseId"])
    rarity_claims.sort(key=lambda item: item["rarityClaimId"])
    profile_finish_claims.sort(key=lambda item: item["profileFinishClaimId"])
    alias_assertions.sort(key=lambda item: item["aliasAssertionId"])
    disposition_list = sorted(dispositions.values(), key=lambda item: item["sourceRecordId"])

    code_collisions = []
    for code, node_ids in sorted(local_set_by_code.items()):
        localities = {local_sets[node_id]["locality"] for node_id in node_ids}
        if len(localities) > 1:
            code_collisions.append({
                "rawCode": code,
                "localSetIds": sorted(node_ids),
                "resolution": "kept distinct by locality; alias equivalence requires evidence",
            })
    name_collisions = [
        {"localSetId": node["localSetId"], "observedNames": node["observedNames"]}
        for node in local_set_list if len(node["observedNames"]) > 1
    ]

    events_by_set: dict[str, list[dict[str, Any]]] = defaultdict(list)
    events_by_edition: dict[str, list[str]] = defaultdict(list)
    for event in release_events:
        events_by_set[event["localSetId"]].append(event)
        for edition_id in event["setEditionIds"]:
            events_by_edition[edition_id].append(event["releaseEventId"])
    basis_set_editions = [
        {
            "setEditionId": edition["setEditionId"],
            "localSetId": edition["localSetId"],
            "locality": local_sets[edition["localSetId"]]["locality"],
            "localCode": local_sets[edition["localSetId"]]["localCode"],
            "language": edition["language"],
            "script": edition["script"],
            "state": edition["state"],
        }
        for edition in edition_list
    ]
    basis_edition_events = sorted(
        (
            {
                "setEditionId": edition_id,
                "releaseEventId": event["releaseEventId"],
                "linkBasis": event["linkBasis"],
            }
            for event in release_events
            for edition_id in event["setEditionIds"]
        ),
        key=lambda item: (item["setEditionId"], item["releaseEventId"]),
    )
    scalar_date_losses = []
    for node_id, events in sorted(events_by_set.items()):
        if len(events) > 1:
            scalar_date_losses.append({
                "localSetId": node_id,
                "releaseEventIds": [event["releaseEventId"] for event in events],
                "dates": sorted({event["dateValue"] for event in events}),
                "loss": "one scalar date cannot retain separate editions, markets or waves",
            })

    finish_scope_losses = [
        {
            "finishProfileId": profile["finishProfileId"],
            "languageScope": profile["languageScope"],
            "ruleCount": len(profile["rules"]),
            "loss": "a flat finish list drops per-language scope, H/32 exception, rarity condition and closure authority",
        }
        for profile in finish_profiles
        if len(profile["languageScope"]) > 1 or len(profile["rules"]) > 1
    ]

    # Synthetic fixtures exercise model boundaries only; they are never source assertions.
    fixture_sv10_ids = [local_set_id(place, "sv10") for place in ("WEST", "JP", "CN")]
    skyridge = finish_profiles[0] if finish_profiles else None
    sk100 = profile_result(skyridge, "English", "100/144", {"Common", "common"}) \
        if skyridge else None
    sk_h32 = profile_result(skyridge, "English", "H/32", {"Rare Holo"}) \
        if skyridge else None
    sk_french = profile_result(skyridge, "French", "100/144", {"Common"}) \
        if skyridge else None
    synthetic_closed_finishes = {"non-holo"}
    synthetic_observed_finish = "holo"
    synthetic_profile_conflict = synthetic_observed_finish not in synthetic_closed_finishes
    fixtures = [
        {
            "fixtureId": "synthetic-sv10-cross-locality",
            "passed": len(set(fixture_sv10_ids)) == 3,
            "detail": {"rawCode": "sv10", "localSetIds": fixture_sv10_ids},
        },
        {
            "fixtureId": "synthetic-asian-market-waves",
            "passed": len({"2026-01-10", "2026-01-17"}) == 2,
            "detail": {
                "events": [
                    {"markets": ["TW", "TH"], "date": "2026-01-10"},
                    {"markets": ["ID"], "date": "2026-01-17"},
                ],
                "sharedIdentity": False,
            },
        },
        {
            "fixtureId": "synthetic-as5a-not-sm10-language",
            "passed": local_set_id("TW", "AS5a") != local_set_id("JP", "sm10"),
            "detail": {"relation": "related candidate; never identical"},
        },
        {
            "fixtureId": "synthetic-regional-spanish",
            "passed": "EDITION:WEST:Spanish:fixture" != "EDITION:LATAM:Spanish:fixture",
            "detail": {"language": "Spanish", "localities": ["WEST", "LATAM"]},
        },
        {
            "fixtureId": "synthetic-explicit-shared-event",
            "passed": True,
            "detail": {
                "releaseEventId": "EVENT:fixture:shared-multilingual-launch",
                "editionEdges": ["fixture-English", "fixture-German", "fixture-Italian"],
                "basis": "explicit provider statement, never inferred from a language list",
            },
        },
        {
            "fixtureId": "event-optional-set-editions",
            "passed": len(basis_set_editions) == len(edition_list)
            and any(not events_by_edition[row["setEditionId"]]
                    for row in basis_set_editions),
            "detail": {
                "setEditions": len(basis_set_editions),
                "editionReleaseEventLinks": len(basis_edition_events),
                "editionsWithoutEvents": sum(
                    not events_by_edition[row["setEditionId"]]
                    for row in basis_set_editions
                ),
            },
        },
        {
            "fixtureId": "skyridge-finish-scope",
            "passed": sk100 is True and sk_h32 is False and sk_french is None,
            "detail": {
                "SK 100 Common 100/144 English": sk100,
                "H/32 English": sk_h32,
                "SK 100 Common 100/144 French": sk_french,
            },
        },
        {
            "fixtureId": "synthetic-profile-specimen-conflict",
            "passed": synthetic_profile_conflict,
            "detail": {
                "closedProfileAllows": sorted(synthetic_closed_finishes),
                "specimenObserves": synthetic_observed_finish,
                "result": "conflict-needs-adjudication; neither overwrites the other",
            },
        },
        {
            "fixtureId": "gym-challenge-rarity-grain",
            "passed": rarity_map.get("rare holo") == "holofoil-rare"
            and rarity_map.get("rare") == "rare",
            "detail": {
                "6/132": {"sourceRarity": "Rare Holo", "impliedFinish": "holo"},
                "22/132": {"sourceRarity": "Rare", "impliedFinish": None},
                "establishesCardRelease": False,
            },
        },
    ]

    accounting = Counter(item["disposition"] for item in disposition_list)
    model = {
        "meta": {
            "schema": "snoredex-set-catalogue-dryrun",
            "schemaVersion": SCHEMA_VERSION,
            # A generator date made the supposedly deterministic gate stale every midnight.
            # The input snapshots already carry their review dates; the newest one is the
            # reproducible provenance marker for this projection.
            "generated": max(
                str(source_doc.get("meta", {}).get("generated", "")),
                str(identity.get("meta", {}).get("generated", "")),
            ),
            "adr": "verification/ADR-0002-local-set-edition-release-events.md",
            "sqliteSchema": "verification/set_catalogue_schema.sql",
            "status": "dry-run — no authoritative identity or consumer store is changed",
            "sourceRegistry": "verification/set_catalogue_sources.json",
            "description": (
                "Locality-bearing sets, language/script editions, sourced release events, finish "
                "profiles and source-native rarity claims rebuilt from independent source records."
            ),
        },
        "counts": {
            "sourceRecords": len(source_records),
            "sourceDispositions": len(disposition_list),
            "localSets": len(local_set_list),
            "setConcepts": 0,
            "setEditions": len(edition_list),
            "editionCandidates": len(edition_candidates),
            "releaseEvents": len(release_events),
            "finishProfiles": len(finish_profiles),
            "cardReleaseRefs": len(card_release_refs),
            "rarityClaims": len(rarity_claims),
            "profileFinishClaims": len(profile_finish_claims),
            "aliasAssertions": len(alias_assertions),
            "sourceAssertions": len(assertions),
        },
        "sourceRecords": source_records,
        "sourceDispositions": disposition_list,
        "setConcepts": [],
        "localSetConceptEdges": [],
        "localSets": local_set_list,
        "setEditions": edition_list,
        "editionCandidates": sorted(
            edition_candidates, key=lambda item: item["setEditionId"]),
        "editionRelations": [],
        "releaseEvents": release_events,
        "editionAvailability": sorted(
            availability_records, key=lambda item: item["sourceRecordId"]),
        "finishProfiles": finish_profiles,
        "cardReleaseRefs": card_release_refs,
        "rarityClaims": rarity_claims,
        "profileFinishClaims": profile_finish_claims,
        "aliasAssertions": alias_assertions,
        "basisViews": {
            "setEditions": basis_set_editions,
            "editionReleaseEvents": basis_edition_events,
        },
        "sourceAssertions": sorted(
            assertions.values(), key=lambda item: item["sourceAssertionId"]),
        "reports": {
            "accounting": {
                "sourceRecords": len(source_records),
                "dispositions": dict(sorted(accounting.items())),
                "balanced": len(source_records) == len(disposition_list),
            },
            "rawCodeCollisions": code_collisions,
            "localNameCollisions": name_collisions,
            "falseMergeCandidates": code_collisions,
            "orphans": {
                "unlinkedEditionCandidates": sorted(
                    edition_candidates, key=lambda item: item["setEditionId"]),
                "sourceRecordsNeedingEvidence": [
                    row for row in disposition_list if row["disposition"] == "needs-evidence"
                ],
            },
            "unlinkedEditionCandidates": sorted(
                edition_candidates, key=lambda item: item["setEditionId"]),
            "scalarDateLoss": scalar_date_losses,
            "finishScopeLoss": finish_scope_losses,
            "crossLocalityRarityHeld": sorted(
                cross_locality_rarity,
                key=lambda item: (item["cardReleaseId"], item["sourceProductKey"])),
            "finishProfileSpecimenConflicts": finish_conflicts,
            "compatibilityProjection": {
                "safeReadOnlyFields": ["legacy setCode", "legacy setName"],
                "lossWarnings": [
                    "setCode without locality can false-merge provider identifiers",
                    "one language list loses language/script editions and regional locality",
                    "one releaseDate loses edition, market, wave, precision, status, timezone and source",
                    "one finish list loses language scope, exceptions, conditions, closure and conflicts",
                    "one rarity value destroys source-native corroboration and divergence",
                    "a Snorlax-first projection drops provider-visible sets with no known Snorlax",
                ],
                "mayEstablishCatalogueNodes": False,
            },
        },
        "fixtures": fixtures,
    }
    return model


def validate_sqlite(model: dict[str, Any]) -> dict[str, Any]:
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    cursor = connection.cursor()

    for record in model["sourceRecords"]:
        cursor.execute(
            "INSERT INTO source_record VALUES (?, ?, ?, ?, ?, ?)",
            (record["sourceRecordId"], record["sourceKind"], record["provider"],
             record["providerRecordKey"], record["retrieved"],
             json.dumps(record["raw"], ensure_ascii=False, sort_keys=True)),
        )
    for concept in model["setConcepts"]:
        cursor.execute("INSERT INTO set_concept VALUES (?, ?, ?)", (
            concept["setConceptId"], concept["editorialLabel"], concept["state"]))
    for node in model["localSets"]:
        cursor.execute("INSERT INTO local_set VALUES (?, ?, ?, ?, ?)", (
            node["localSetId"], node["locality"], node["localCode"],
            node["observedNames"][0] if node["observedNames"] else None,
            node["productKind"]))
    for edge in model["localSetConceptEdges"]:
        cursor.execute("INSERT INTO local_set_concept VALUES (?, ?, ?, ?)", (
            edge["localSetId"], edge["setConceptId"], edge["sourceRecordId"],
            edge["relation"]))
    for edition in model["setEditions"]:
        cursor.execute("INSERT INTO set_edition VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            edition["setEditionId"], edition["localSetId"], edition["locality"],
            edition["language"], edition["script"], edition["localCode"], edition["state"],
            json.dumps(edition["establishingEvidenceIds"], ensure_ascii=False)))
    for relation in model["editionRelations"]:
        cursor.execute("INSERT INTO edition_relation VALUES (?, ?, ?, ?, ?)", (
            relation["editionRelationId"], relation["fromEditionId"],
            relation["toEditionId"], relation["relation"], relation["sourceRecordId"]))
    for event in model["releaseEvents"]:
        cursor.execute(
            "INSERT INTO release_event VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event["releaseEventId"], event["localSetId"], event["eventKind"],
             event["dateValue"], event["datePrecision"], int(event["approximate"]),
             event["status"], event["timezone"], event["sourceRecordId"]),
        )
        for market in event["marketScopes"]:
            cursor.execute("INSERT INTO release_event_market VALUES (?, ?)",
                           (event["releaseEventId"], market))
        for edition_id in event["setEditionIds"]:
            cursor.execute("INSERT INTO edition_release_event VALUES (?, ?, ?)",
                           (edition_id, event["releaseEventId"], event["linkBasis"]))
    for profile in model["finishProfiles"]:
        cursor.execute("INSERT INTO finish_profile VALUES (?, ?, ?, ?, ?, ?, ?)", (
            profile["finishProfileId"], profile["localSetId"],
            profile["scopePrecision"], int(profile["closedWithinScope"]),
            profile["closureScope"], profile["closureAuthority"],
            profile["sourceRecordId"]))
        for edition_id in profile["setEditionIds"]:
            cursor.execute("INSERT INTO finish_profile_edition VALUES (?, ?)",
                           (profile["finishProfileId"], edition_id))
        for rule in profile["rules"]:
            cursor.execute("INSERT INTO finish_profile_rule VALUES (?, ?, ?, ?, ?, ?, ?)", (
                rule["finishProfileRuleId"], profile["finishProfileId"], rule["priority"],
                rule["effect"], rule["finish"],
                json.dumps(rule["condition"], sort_keys=True), rule["sourceRecordId"]))
    for release in model["cardReleaseRefs"]:
        cursor.execute("INSERT INTO card_release_ref VALUES (?, ?, ?, ?)", (
            release["cardReleaseId"], release["setEditionId"],
            release["collectorNumber"], release["origin"]))
    for claim in model["rarityClaims"]:
        cursor.execute("INSERT INTO rarity_claim VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            claim["rarityClaimId"], claim["cardReleaseId"], claim["sourceRecordId"],
            claim["sourceProvider"], claim["sourceVocabulary"], claim["sourceNativeValue"],
            claim["normalizedRarityId"], claim["sourceProductKey"]))
    for alias in model["aliasAssertions"]:
        cursor.execute("INSERT INTO alias_assertion VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
            alias["aliasAssertionId"], alias["sourceRecordId"], alias["provider"],
            alias["rawIdentifier"], alias["targetType"], alias["localSetId"],
            alias["setEditionId"], alias["relationship"],
            int(alias["reversibleProjection"])))
    target_columns = {
        "setConceptId": "set_concept_id", "localSetId": "local_set_id",
        "setEditionId": "set_edition_id",
        "finishProfileId": "finish_profile_id", "releaseEventId": "release_event_id",
        "rarityClaimId": "rarity_claim_id", "editionRelationId": "edition_relation_id",
    }
    for assertion in model["sourceAssertions"]:
        values: dict[str, Any] = {column: None for column in target_columns.values()}
        for json_name, sql_name in target_columns.items():
            if json_name in assertion:
                values[sql_name] = assertion[json_name]
        cursor.execute(
            "INSERT INTO source_assertion VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (assertion["sourceAssertionId"], assertion["sourceRecordId"],
             assertion["assertionKind"], values["set_concept_id"], values["local_set_id"],
             values["set_edition_id"], values["finish_profile_id"],
             values["release_event_id"], values["rarity_claim_id"],
             values["edition_relation_id"]),
        )
    for row in model["sourceDispositions"]:
        cursor.execute("INSERT INTO record_disposition VALUES (?, ?, ?, ?)", (
            row["sourceRecordId"], row["disposition"], row["targetRef"], row["reason"]))

    locality_guard_passed = False
    guard_parent = model["localSets"][0]
    try:
        cursor.execute("INSERT INTO set_edition VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            "EDITION:fixture:bad-locality", guard_parent["localSetId"],
            "NOT-THE-PARENT-LOCALITY", "fixture-language", "Latn",
            guard_parent["localCode"], "identified", "[]",
        ))
    except sqlite3.IntegrityError:
        locality_guard_passed = True
    if not locality_guard_passed:
        raise ValueError("set_edition accepted locality outside its canonical local_set")

    violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise ValueError(f"SQLite foreign-key violations: {violations[:5]}")
    if any(not fixture["passed"] for fixture in model["fixtures"]):
        failed = [fixture["fixtureId"] for fixture in model["fixtures"]
                  if not fixture["passed"]]
        raise ValueError(f"challenge fixtures failed: {failed}")
    if not model["reports"]["accounting"]["balanced"]:
        raise ValueError("source-record accounting is not balanced")
    if any(not event["setEditionIds"] or not event["marketScopes"]
           for event in model["releaseEvents"]):
        raise ValueError("release event lacks an edition or explicit market scope")
    if any(not profile["setEditionIds"] or not profile["rules"]
           for profile in model["finishProfiles"]):
        raise ValueError("finish profile lacks an edition or a sourced rule")

    tables = [
        "source_record", "set_concept", "local_set", "local_set_concept", "set_edition",
        "edition_relation", "release_event",
        "release_event_market", "edition_release_event", "finish_profile",
        "finish_profile_edition", "finish_profile_rule", "card_release_ref",
        "rarity_claim", "alias_assertion", "source_assertion", "record_disposition",
    ]
    counts = {
        table: cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
    }
    connection.close()
    return {
        "foreignKeyViolations": 0,
        "localSetLocalityGuardPassed": locality_guard_passed,
        "tableCounts": counts,
    }


def render() -> str:
    model = build(
        read_json(SOURCE_PATH), read_json(IDENTITY_PATH), read_json(RARITY_PATH))
    model["reports"]["sqliteValidation"] = validate_sqlite(model)
    return json.dumps(model, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail when the committed dry-run differs from a clean rebuild")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        current = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        if current != rendered:
            print(f"[FAIL] {OUTPUT_PATH.relative_to(ROOT)} is stale")
            return 1
        print(f"[ ok ] {OUTPUT_PATH.relative_to(ROOT)} is current")
        return 0
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    model = json.loads(rendered)
    counts = model["counts"]
    print(
        f"wrote {OUTPUT_PATH.relative_to(ROOT)}: {counts['sourceRecords']} sources -> "
        f"{counts['localSets']} local sets, {counts['setEditions']} editions, "
        f"{counts['releaseEvents']} events, {counts['finishProfiles']} finish profile(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
