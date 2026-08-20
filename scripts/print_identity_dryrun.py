#!/usr/bin/env python3
"""Dry-run the claim -> card release -> physical printing boundary (#145).

The legacy stores mix three different questions:

* a language unit is a claim that a localized card release exists;
* a localized card release is one numbered card in one language-bearing set edition; and
* a physical printing is a positively evidenced manufactured finish/treatment of that release.

This dry-run separates those grains without changing an authoritative store. Every legacy unit,
source-first record, finish-printing claim and excluded code-card claim becomes a candidate-claim
node. Only positive evidence is allowed to materialize an existence-bearing target:

* ``units.json`` status ``confirmed`` may establish a card release;
* ``finish_units.json`` verificationStatus ``confirmed`` may establish a physical printing;
* contradicted and marketplace-only claims remain visible candidates.

The report is deliberately a migration plan. #140, not this script, changes consumer identities.

    python scripts/print_identity_dryrun.py
    python scripts/print_identity_dryrun.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "verification" / "print_identity_dryrun.json"
SCHEMA_VERSION = "0.3.0"

LOCALITIES = {
    "WEST": "Western distribution (EU/NA)",
    "LATAM": "Latin-American distribution",
    "JP": "Japan",
    "KR": "South Korea",
    "TW": "Taiwan / Traditional-Chinese distribution",
    "CN": "Mainland China / Simplified-Chinese distribution",
    "ID": "Indonesia",
    "TH": "Thailand",
    "SEA": "South-East Asian regional promo distribution",
}

MARKET_LOCALITY = {
    "Western": "WEST",
    "Japanese": "JP",
    "Simplified Chinese": "CN",
    "Traditional Chinese": "TW",
    "SEA promo": "SEA",
}

LANGUAGE_LOCALITY = {
    "Japanese": "JP",
    "Korean": "KR",
    "T-Chinese": "TW",
    "S-Chinese": "CN",
    "Thai": "TH",
    "Indonesian": "ID",
}

LANGUAGE_SCRIPT = {
    "Japanese": "Jpan",
    "Korean": "Hang",
    "T-Chinese": "Hant",
    "S-Chinese": "Hans",
    "Thai": "Thai",
    "Russian": "Cyrl",
}

WESTERN_LANGUAGES = {
    "English", "French", "German", "Italian", "Spanish", "Portuguese",
    "Russian", "Dutch", "Polish", "Czech", "Hungarian",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def resolve_locality(language: str, market: str) -> tuple[str | None, str]:
    """Resolve a locality while retaining the rule that made the proposal."""
    if language in LANGUAGE_LOCALITY:
        return LANGUAGE_LOCALITY[language], "language names its locality"
    if language in WESTERN_LANGUAGES:
        if market == "SEA promo":
            return "SEA", "Western language under SEA regional distribution"
        return "WEST", "Western language under Western distribution"
    return None, "no locality rule for this language"


def resolve_script(language: str) -> str:
    return LANGUAGE_SCRIPT.get(language, "Latn")


def set_edition_id(locality: str, language: str, set_code: str,
                   identifier_known: bool) -> str:
    if identifier_known:
        return f"EDITION:{locality}:{language}:{set_code}"
    return f"EDITION:{locality}:{language}:via-{set_code}:unknown-local-set"


def card_release_id(edition_id: str, number: str, work: str,
                    identifier_known: bool) -> str:
    edition_tail = edition_id.removeprefix("EDITION:")
    if identifier_known:
        return f"RELEASE:{edition_tail}:{number or 'unnumbered'}:{work}"
    return f"RELEASE:{edition_tail}:via-{number or 'unnumbered'}:{work}:unknown-local-id"


def target_for_legacy(unit: dict, card: dict) -> dict[str, Any]:
    market = card["market"]
    locality, rule = resolve_locality(unit["language"], market)
    if locality is None:
        return {"locality": None, "localityRule": rule}
    identifier_known = locality == MARKET_LOCALITY.get(market)
    edition_id = set_edition_id(locality, unit["language"], unit["setCode"],
                                identifier_known)
    release_id = card_release_id(
        edition_id,
        str(unit.get("number") or ""),
        unit["cardKey"],
        identifier_known,
    )
    return {
        "locality": locality,
        "localityRule": rule,
        "language": unit["language"],
        "script": resolve_script(unit["language"]),
        "localIdentifierKnown": identifier_known,
        "setEditionId": edition_id,
        "cardReleaseId": release_id,
        "localSetCode": unit["setCode"] if identifier_known else None,
        "localNumber": str(unit.get("number") or "") if identifier_known else None,
        "viaLegacySetCode": unit["setCode"],
        "viaLegacyNumber": str(unit.get("number") or ""),
        "work": unit["cardKey"],
        "workMappingState": "mapped",
    }


def target_for_source_first(entry: dict, work: str | None = None) -> dict[str, Any]:
    language = entry["language"]
    locality = entry["locality"]
    edition_id = set_edition_id(locality, language, entry["localSetCode"], True)
    # source_first_prints.json intentionally preserves prose equivalence proposals. Until an
    # explicit edge is accepted, each specimen has an unmapped work anchor rather than a guessed
    # work id. The physical local release itself is still positively established.
    work_anchor = work or f"unmapped-work:{entry['specimenId']}"
    return {
        "locality": locality,
        "localityRule": "source-first record names its locality",
        "language": language,
        "script": entry["script"],
        "localIdentifierKnown": True,
        "setEditionId": edition_id,
        "cardReleaseId": card_release_id(
            edition_id, str(entry["localNumber"]), work_anchor, True),
        "localSetCode": entry["localSetCode"],
        "localNumber": str(entry["localNumber"]),
        "viaLegacySetCode": None,
        "viaLegacyNumber": None,
        "work": work,
        "workMappingState": ("mapped-by-explicit-equivalence"
                             if work else "needs-explicit-equivalence"),
    }


def build(cards: list[dict], units: list[dict], finish_units: list[dict],
          excluded: list[dict], specimens: list[dict], baseline: dict,
          source_first: dict, rekeys: dict) -> dict[str, Any]:
    cards_by_key: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for card in cards:
        key = (card["setCode"], str(card.get("number") or ""),
               card.get("variantToken") or "base")
        cards_by_key[key].append(card)

    candidate_claims: dict[str, dict[str, Any]] = {}
    set_editions: dict[str, dict[str, Any]] = {}
    card_releases: dict[str, dict[str, Any]] = {}
    physical_printings: dict[str, dict[str, Any]] = {}
    unresolved_units: list[dict[str, Any]] = []
    unresolved_physical: list[dict[str, Any]] = []
    equivalence_assertions: list[dict[str, Any]] = []
    legacy_issue_rekeys: list[dict[str, Any]] = []

    proposed_release_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    product_claims: dict[str, list[str]] = defaultdict(list)
    product_releases: dict[str, set[str]] = defaultdict(set)

    units_by_id = {unit["unitId"]: unit for unit in units}
    source_first_by_id = {
        entry["printId"]: entry for entry in source_first.get("prints", [])
    }
    mappings_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    mappings_by_unit: dict[str, list[dict[str, Any]]] = defaultdict(list)
    mapping_pairs: set[tuple[str, str]] = set()
    for question_set in rekeys.get("questionSets", []):
        scope = question_set["legacyUnitIds"]
        if len(scope) != len(set(scope)):
            raise ValueError(f"issue #{question_set['issueNumber']} repeats a legacy unit")
        for unit_id in scope:
            unit = units_by_id.get(unit_id)
            if unit is None or unit["language"] != question_set["language"]:
                raise ValueError(f"issue #{question_set['issueNumber']} has invalid unit {unit_id}")
        for mapping in question_set.get("mappings", []):
            unit_id = mapping["legacyUnitId"]
            print_id = mapping["sourceFirstRecordId"]
            if mapping.get("assertionType") != "same-work-decision":
                raise ValueError(
                    f"re-key mapping is not a reviewed decision: {unit_id} -> {print_id}")
            if not str(mapping.get("evidence") or "").strip():
                raise ValueError(
                    f"re-key mapping lacks positive evidence: {unit_id} -> {print_id}")
            if unit_id not in scope or print_id not in source_first_by_id:
                raise ValueError(f"invalid re-key mapping {unit_id} -> {print_id}")
            pair = (unit_id, print_id)
            if pair in mapping_pairs:
                raise ValueError(f"duplicate re-key mapping {unit_id} -> {print_id}")
            entry = source_first_by_id[print_id]
            if entry["locality"] != question_set["locality"] \
                    or entry["language"] != question_set["language"]:
                raise ValueError(f"re-key mapping crosses locality/language: {unit_id} -> {print_id}")
            mapping_pairs.add(pair)
            mappings_by_unit[unit_id].append(mapping)
            mappings_by_source[print_id].append(mapping)

    def register_edition(target: dict[str, Any], claim_id: str) -> None:
        eid = target["setEditionId"]
        edition = set_editions.setdefault(eid, {
            "setEditionId": eid,
            "locality": target["locality"],
            "language": target["language"],
            "script": target["script"],
            "localSetCode": target["localSetCode"],
            "localIdentifierKnown": target["localIdentifierKnown"],
            "state": ("identified" if target["localIdentifierKnown"]
                      else "needs-local-identifier"),
            "viaLegacySetCodes": set(),
            "establishingClaimIds": [],
        })
        if target.get("viaLegacySetCode"):
            edition["viaLegacySetCodes"].add(target["viaLegacySetCode"])
        if claim_id not in edition["establishingClaimIds"]:
            edition["establishingClaimIds"].append(claim_id)

    # Every language unit becomes a claim first. No entity is created in this pass.
    for unit in units:
        key = (unit["setCode"], str(unit.get("number") or ""),
               unit.get("variant") or "base")
        matched_cards = cards_by_key.get(key, [])
        claim_id = f"CLAIM:legacy:{unit['unitId']}"
        if len(matched_cards) != 1:
            reason = ("no product node for the unit" if not matched_cards
                      else "legacy identity tuple resolves to multiple products")
            candidate_claims[claim_id] = {
                "claimId": claim_id,
                "claimKind": "card-release",
                "sourceKind": "legacy-language-unit",
                "sourceId": unit["unitId"],
                "evidenceStatus": unit["status"],
                "disposition": ("bounded-contradicted"
                                if unit["status"] == "contradicted"
                                else "candidate-needs-evidence"),
                "proposedTargetId": None,
                "materializedTargetId": None,
                "reason": reason,
            }
            unresolved_units.append({"unitId": unit["unitId"], "reason": reason})
            continue

        card = matched_cards[0]
        target = target_for_legacy(unit, card)
        if target["locality"] is None:
            reason = target["localityRule"]
            candidate_claims[claim_id] = {
                "claimId": claim_id,
                "claimKind": "card-release",
                "sourceKind": "legacy-language-unit",
                "sourceId": unit["unitId"],
                "evidenceStatus": unit["status"],
                "disposition": ("bounded-contradicted"
                                if unit["status"] == "contradicted"
                                else "candidate-needs-evidence"),
                "proposedTargetId": None,
                "materializedTargetId": None,
                "reason": reason,
            }
            unresolved_units.append({"unitId": unit["unitId"], "reason": reason})
            continue

        disposition = ("established-and-mapped" if unit["status"] == "confirmed"
                       else "bounded-contradicted")
        candidate_claims[claim_id] = {
            "claimId": claim_id,
            "claimKind": "card-release",
            "sourceKind": "legacy-language-unit",
            "sourceId": unit["unitId"],
            "sourceRecord": unit.get("sourceUrl"),
            "evidenceStatus": unit["status"],
            "disposition": disposition,
            "proposedTargetId": target["cardReleaseId"],
            "materializedTargetId": None,
            "reason": target["localityRule"],
        }
        proposed_release_groups[target["cardReleaseId"]].append({
            "claimId": claim_id, "unit": unit, "card": card, "target": target,
        })
        product_claims[card["productUrl"]].append(claim_id)

    # A card release exists only when at least one claim positively establishes it. Claims in
    # another language cannot share a release id because language is part of setEditionId.
    for release_id, members in proposed_release_groups.items():
        confirmed = [m for m in members if m["unit"]["status"] == "confirmed"]
        if not confirmed:
            for member in members:
                candidate_claims[member["claimId"]]["reason"] = (
                    "recorded contradiction remains a claim and cannot establish a release")
            continue

        target = confirmed[0]["target"]
        for member in confirmed:
            register_edition(member["target"], member["claimId"])
        release = {
            "cardReleaseId": release_id,
            "setEditionId": target["setEditionId"],
            "locality": target["locality"],
            "language": target["language"],
            "script": target["script"],
            "localSetCode": target["localSetCode"],
            "localNumber": target["localNumber"],
            "localIdentifierKnown": target["localIdentifierKnown"],
            "state": ("identified" if target["localIdentifierKnown"]
                      else "needs-local-identifier"),
            "work": target["work"],
            "workMappingState": target["workMappingState"],
            "viaLegacySetCode": target["viaLegacySetCode"],
            "viaLegacyNumber": target["viaLegacyNumber"],
            "claimIds": sorted(m["claimId"] for m in members),
            "establishingClaimIds": sorted(m["claimId"] for m in confirmed),
            "nonEstablishingClaimIds": sorted(
                m["claimId"] for m in members if m not in confirmed),
            "legacyVariants": sorted({m["unit"].get("variant") or "base" for m in members}),
            "legacyProducts": sorted({m["card"]["productUrl"] for m in members}),
            "sourceRecords": sorted({
                m["unit"]["sourceUrl"] for m in confirmed if m["unit"].get("sourceUrl")
            }),
        }
        card_releases[release_id] = release
        for member in members:
            claim = candidate_claims[member["claimId"]]
            unit = member["unit"]
            if unit["status"] == "confirmed":
                claim["materializedTargetId"] = release_id
            else:
                claim["reason"] = (
                    "candidate remains non-establishing; another confirmed claim establishes "
                    "the release without transferring status")
            product_releases[member["card"]["productUrl"]].add(release_id)

    # Source-first records are positive card-release claims with their own identifiers. Their raw
    # printId survives in source_first_prints.json as a legacy alias; this dry run does not rewrite
    # that evidence record or guess its work equivalence.
    for entry in source_first.get("prints", []):
        claim_id = f"CLAIM:source-first:{entry['printId']}"
        mappings = mappings_by_source.get(entry["printId"], [])
        mapped_units = [units_by_id[mapping["legacyUnitId"]] for mapping in mappings]
        mapped_works = {unit["cardKey"] for unit in mapped_units}
        if len(mapped_works) > 1:
            raise ValueError(f"re-key mappings assign multiple works to {entry['printId']}")
        mapped_work = next(iter(mapped_works), None)
        target = target_for_source_first(entry, mapped_work)
        register_edition(target, claim_id)
        release_id = target["cardReleaseId"]
        release = card_releases.get(release_id)
        if release is None:
            release = {
                "cardReleaseId": release_id,
                "setEditionId": target["setEditionId"],
                "locality": target["locality"],
                "language": target["language"],
                "script": target["script"],
                "localSetCode": target["localSetCode"],
                "localNumber": target["localNumber"],
                "localIdentifierKnown": True,
                "state": "identified",
                "work": target["work"],
                "workMappingState": target["workMappingState"],
                "viaLegacySetCode": None,
                "viaLegacyNumber": None,
                "claimIds": [],
                "establishingClaimIds": [],
                "nonEstablishingClaimIds": [],
                "legacyVariants": [],
                "legacyProducts": [],
                "sourceRecords": [],
                "sourceFirstRecordIds": [],
            }
            card_releases[release_id] = release
        elif any(release[field] != target[field] for field in
                 ("setEditionId", "locality", "language", "script",
                  "localSetCode", "localNumber", "work")):
            raise ValueError(f"source-first records collide across release grain: {release_id}")

        release.setdefault("sourceFirstRecordIds", [])
        release["claimIds"].append(claim_id)
        release["establishingClaimIds"].append(claim_id)
        release["sourceFirstRecordIds"].append(entry["printId"])
        if entry.get("sourceUrl") and entry["sourceUrl"] not in release["sourceRecords"]:
            release["sourceRecords"].append(entry["sourceUrl"])
        if mapped_units:
            release["legacyCounterpartUnitIds"] = sorted(
                set(release.get("legacyCounterpartUnitIds", []))
                | {unit["unitId"] for unit in mapped_units})
        candidate_claims[claim_id] = {
            "claimId": claim_id,
            "claimKind": "card-release",
            "sourceKind": "source-first-record",
            "sourceId": entry["printId"],
            "sourceRecord": entry.get("sourceUrl"),
            "evidenceStatus": "confirmed",
            "disposition": "established-and-mapped",
            "proposedTargetId": release_id,
            "materializedTargetId": release_id,
            "reason": "positive source-first specimen/card record",
        }
        for mapping in mappings:
            mapped_unit = units_by_id[mapping["legacyUnitId"]]
            equivalence_assertions.append({
                "assertionId": f"ASSERT:same-work:{mapping['legacyUnitId']}:{entry['printId']}",
                "assertionType": mapping["assertionType"],
                "fromId": release_id,
                "toId": f"WORK:{mapped_unit['cardKey']}",
                "legacyUnitId": mapping["legacyUnitId"],
                "sourceFirstRecordId": entry["printId"],
                "assertedBy": mapping["assertedBy"],
                "assertedAt": mapping["assertedAt"],
                "evidenceUrl": mapping["evidenceUrl"],
                "evidence": mapping["evidence"],
                "destructiveMergeAllowed": False,
            })

    release_by_source_first = {
        source_id: release["cardReleaseId"]
        for release in card_releases.values()
        for source_id in release.get("sourceFirstRecordIds", [])
    }
    for question_set in rekeys.get("questionSets", []):
        rows = []
        for unit_id in question_set["legacyUnitIds"]:
            unit = units_by_id[unit_id]
            mappings = mappings_by_unit.get(unit_id, [])
            source_ids = sorted(mapping["sourceFirstRecordId"] for mapping in mappings)
            rows.append({
                "legacyUnitId": unit_id,
                "legacyClaimId": f"CLAIM:legacy:{unit_id}",
                "legacyStatus": unit["status"],
                "legacyProduct": f"{unit['setCode']} {unit.get('number') or 'unnumbered'}",
                "disposition": ("linked-local-counterpart" if mappings
                                else question_set["defaultDisposition"]),
                "sourceFirstRecordIds": source_ids,
                "localCardReleaseIds": [
                    release_by_source_first[print_id] for print_id in source_ids
                ],
                "assertionIds": [
                    f"ASSERT:same-work:{unit_id}:{print_id}" for print_id in source_ids
                ],
            })
        legacy_issue_rekeys.append({
            "issueNumber": question_set["issueNumber"],
            "locality": question_set["locality"],
            "language": question_set["language"],
            "accountedLegacyUnits": len(rows),
            "linkedLocalCounterparts": sum(
                row["disposition"] == "linked-local-counterpart" for row in rows),
            "needsPositiveLocalIdentity": sum(
                row["disposition"] == "needs-positive-local-identity" for row in rows),
            "rows": rows,
        })
    # A finish-store printing is a second claim grain. Only externally confirmed rows become a
    # physical-printing entity; Cardmarket catalogue hints remain candidate claims.
    releases_by_finish_key: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    releases_by_specimen_key: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for release_id, release in card_releases.items():
        if release["viaLegacySetCode"] is not None:
            key = (release["viaLegacySetCode"], release["viaLegacyNumber"], release["language"])
            releases_by_finish_key[key].append(release_id)
        else:
            key = (release["localSetCode"], release["localNumber"], release["language"])
        releases_by_specimen_key[key].append(release_id)

    for finish_unit in finish_units:
        key = (finish_unit["setCode"], str(finish_unit.get("number") or ""),
               finish_unit["language"])
        release_ids = sorted(set(releases_by_finish_key.get(key, [])))
        for printing in finish_unit.get("printings", []):
            source_printing_id = printing["printingId"]
            claim_id = f"CLAIM:finish:{source_printing_id}"
            proposed_id = f"PHYSICAL:{source_printing_id}"
            confirmed = printing.get("verificationStatus") == "confirmed"
            can_materialize = confirmed and len(release_ids) == 1
            if confirmed and len(release_ids) != 1:
                unresolved_physical.append({
                    "printingId": source_printing_id,
                    "releaseCandidates": release_ids,
                    "reason": "confirmed physical claim does not resolve to exactly one card release",
                })
            disposition = ("established-and-mapped" if can_materialize
                           else "candidate-needs-evidence")
            reason = (
                "externally confirmed finish/treatment claim"
                if can_materialize else
                "marketplace-only or unresolved physical classification cannot establish a node"
            )
            candidate_claims[claim_id] = {
                "claimId": claim_id,
                "claimKind": "physical-printing",
                "sourceKind": "finish-printing-record",
                "sourceId": source_printing_id,
                "evidenceStatus": printing.get("verificationStatus"),
                "disposition": disposition,
                "proposedTargetId": proposed_id,
                "materializedTargetId": proposed_id if can_materialize else None,
                "reason": reason,
            }
            if can_materialize:
                physical_printings[proposed_id] = {
                    "physicalPrintingId": proposed_id,
                    "cardReleaseId": release_ids[0],
                    "finish": printing.get("finish"),
                    "foilPattern": printing.get("foilPattern"),
                    "markings": printing.get("markings"),
                    "distribution": printing.get("distribution"),
                    "cardSize": printing.get("cardSize"),
                    "errorClass": None,
                    "classificationState": "classified-from-positive-evidence",
                    "sourceFinishUnitId": finish_unit["finishUnitId"],
                    "sourcePrintingId": source_printing_id,
                    "establishingClaimId": claim_id,
                }

    # An identified physical scan is the third claim grain, and the one the ladder ranks highest.
    # FINISH_SOURCES.md always allowed it — "Identified physical scan | Visible finish, pattern,
    # marking, and size on that specimen" — and until #150 a specimen had no field to say it in, so
    # every physical printing came from the finish store. A specimen that records what it saw may
    # now establish one; a specimen that records nothing still says nothing.
    specimen_printings = 0
    specimen_corroborations = 0
    for specimen in specimens:
        observation = specimen.get("physicalObservation")
        if not observation:
            continue
        specimen_id = specimen["specimenId"]
        claim_id = f"CLAIM:specimen:{specimen_id}"
        proposed_id = f"PHYSICAL:specimen:{specimen_id}"
        key = (specimen["setCode"], str(specimen.get("number") or ""), specimen["language"])
        release_ids = sorted(set(releases_by_specimen_key.get(key, [])))

        # One image of two cards cannot establish *a* printing. SPEC-0013 photographs the sealed
        # Indonesian pair; its per-card crops are the records that establish.
        covers_many = bool(observation.get("coversMultipleCards"))
        # Does the finish store already carry this exact printing? Then the specimen corroborates
        # it rather than adding a second node for the same physical object.
        duplicate_of = next(
            (pid for pid, existing in physical_printings.items()
             if existing["cardReleaseId"] in release_ids
             and existing.get("finish") == observation.get("finish")
             and (existing.get("foilPattern") or None) == (observation.get("foilPattern") or None)),
            None,
        )
        can_materialize = len(release_ids) == 1 and not covers_many and duplicate_of is None

        if covers_many:
            reason = "observation depicts more than one card; the per-card crops establish"
        elif len(release_ids) != 1:
            reason = "specimen does not resolve to exactly one card release"
            unresolved_physical.append({
                "printingId": proposed_id,
                "releaseCandidates": release_ids,
                "reason": "specimen observation does not resolve to exactly one card release",
            })
        elif duplicate_of is not None:
            reason = f"corroborates {duplicate_of}, already established from the finish store"
            specimen_corroborations += 1
        else:
            reason = "finish observed on an identified physical scan"

        candidate_claims[claim_id] = {
            "claimId": claim_id,
            "claimKind": "physical-printing",
            "sourceKind": "specimen-observation",
            "sourceId": specimen_id,
            "evidenceStatus": "observed",
            "disposition": "established-and-mapped" if can_materialize else "candidate-needs-evidence",
            "proposedTargetId": proposed_id,
            "materializedTargetId": proposed_id if can_materialize else None,
            "reason": reason,
        }
        if can_materialize:
            specimen_printings += 1
            physical_printings[proposed_id] = {
                "physicalPrintingId": proposed_id,
                "cardReleaseId": release_ids[0],
                "finish": observation.get("finish"),
                "foilPattern": observation.get("foilPattern"),
                "markings": observation.get("markings"),
                "distribution": None,
                "cardSize": observation.get("cardSize"),
                "errorClass": None,
                "classificationState": "classified-from-inspected-specimen",
                "sourceFinishUnitId": None,
                "sourcePrintingId": None,
                "establishingClaimId": claim_id,
                "establishingSpecimenId": specimen_id,
                "basis": observation.get("basis"),
            }

    # Exclusions are candidate claims with a positive product-scope disposition, not missing rows.
    for unit in excluded:
        claim_id = f"CLAIM:excluded:{unit['unitId']}"
        candidate_claims[claim_id] = {
            "claimId": claim_id,
            "claimKind": "card-release",
            "sourceKind": "legacy-code-card-unit",
            "sourceId": unit["unitId"],
            "evidenceStatus": "out-of-scope-product",
            "disposition": "positively-excluded",
            "proposedTargetId": None,
            "materializedTargetId": None,
            "reason": "code card, excluded from the physical-card catalogue",
        }
    identity_collisions: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for card in cards:
        key = (card["setCode"], str(card.get("number") or ""),
               card.get("variantToken") or "base")
        identity_collisions[key].append(card["productUrl"])
    collision_keys = {key for key, urls in identity_collisions.items() if len(urls) > 1}
    positively_excluded_collision_keys = {
        key for key in collision_keys if all(card.get("isCodeCard") for card in cards_by_key[key])
    }
    unexplained_collision_keys = collision_keys - positively_excluded_collision_keys

    card_disposition = {}
    for card in cards:
        claims = sorted(product_claims.get(card["productUrl"], []))
        releases = sorted(product_releases.get(card["productUrl"], set()))
        key = (card["setCode"], str(card.get("number") or ""),
               card.get("variantToken") or "base")
        if card.get("isCodeCard"):
            disposition = "positively-excluded"
            reason = "code-card product is outside the physical-card catalogue"
        elif len(identity_collisions[key]) > 1:
            disposition = "candidate-needs-evidence"
            reason = "legacy identity tuple is shared by multiple products"
        elif not claims:
            disposition = "candidate-needs-evidence"
            reason = "no language claim in the legacy store"
        elif not releases:
            disposition = "candidate-needs-evidence"
            reason = "no positive language claim establishes a release"
        else:
            disposition = "split" if len(releases) > 1 else "carried"
            reason = f"{len(releases)} established language-bearing card release(s)"
        card_disposition[card["productUrl"]] = {
            "disposition": disposition,
            "claimIds": claims,
            "cardReleaseIds": releases,
            "reason": reason,
        }

    # Specimen reachability is retained from the accepted D1 decision. A source-first record gives
    # the specimen a card-release claim even when its work equivalence remains unresolved.
    product_codes = {(c["setCode"], str(c.get("number") or "")) for c in cards}
    # `.get`, not `[...]`, and None filtered out: since ADR-0001 D5 a print may rest on a tier-1
    # publisher record instead of a specimen, and those carry no specimen id to collect. A missing
    # id here is a record grounded another way, never a record grounded in nothing — `N4` is what
    # enforces that a print has a ground at all.
    admitted_specimens = {
        entry.get("specimenId") for entry in source_first.get("prints", [])} - {None}
    held_specimens = {
        entry.get("specimenId") for entry in source_first.get("held", [])} - {None}
    orphan_specimens = []
    held_specimen_dispositions = []
    for spec in specimens:
        code = str(spec.get("setCode") or "")
        base_code = code.split("/")[0].strip()
        number = str(spec.get("number") or "")
        if spec.get("specimenId") in admitted_specimens:
            continue
        if (code, number) not in product_codes and (base_code, number) not in product_codes:
            report = {
                "specimenId": spec.get("specimenId"), "setCode": code, "number": number,
                "language": spec.get("language"),
            }
            if spec.get("specimenId") in held_specimens:
                report["reason"] = "held pending a positively identified source-native set code"
                held_specimen_dispositions.append(report)
            else:
                report["reason"] = "no product or source-first release carries these identifiers"
                orphan_specimens.append(report)

    contradicted_only = []
    mixed_status = []
    for release_id, members in proposed_release_groups.items():
        statuses = {member["unit"]["status"] for member in members}
        item = {
            "proposedCardReleaseId": release_id,
            "locality": members[0]["target"]["locality"],
            "language": members[0]["unit"]["language"],
            "unitIds": sorted(member["unit"]["unitId"] for member in members),
            "statuses": sorted(statuses),
            "materialized": release_id in card_releases,
        }
        if statuses == {"contradicted"}:
            contradicted_only.append(item)
        elif len(statuses) > 1:
            mixed_status.append(item)

    multi_variant = [
        {
            "cardReleaseId": release["cardReleaseId"],
            "language": release["language"],
            "legacyVariants": release["legacyVariants"],
            "claimIds": release["claimIds"],
        }
        for release in card_releases.values() if len(release["legacyVariants"]) > 1
    ]
    needs_identifier = [
        release for release in card_releases.values()
        if not release["localIdentifierKnown"]
    ]
    legacy_language_by_claim = {
        f"CLAIM:legacy:{unit['unitId']}": unit["language"] for unit in units
    }
    cross_language_merges = [
        release["cardReleaseId"] for release in card_releases.values()
        if len({legacy_language_by_claim[claim_id]
                for claim_id in release["claimIds"]
                if claim_id in legacy_language_by_claim}) > 1
    ]
    unexplained_splits = []
    for product_url, disposition in card_disposition.items():
        by_edition_profile: dict[tuple[str, str], list[str]] = defaultdict(list)
        for release_id in disposition["cardReleaseIds"]:
            release = card_releases[release_id]
            by_edition_profile[(release["locality"], release["language"])].append(release_id)
        duplicate_profiles = {
            f"{locality}/{language}": sorted(release_ids)
            for (locality, language), release_ids in by_edition_profile.items()
            if len(release_ids) > 1
        }
        if duplicate_profiles:
            unexplained_splits.append({
                "legacyProduct": product_url,
                "duplicateEditionProfiles": duplicate_profiles,
            })

    for edition in set_editions.values():
        edition["viaLegacySetCodes"] = sorted(edition["viaLegacySetCodes"])
        edition["establishingClaimIds"].sort()

    release_by_locality = Counter(r["locality"] for r in card_releases.values())
    unknown_by_locality = Counter(r["locality"] for r in needs_identifier)
    claim_dispositions = Counter(c["disposition"] for c in candidate_claims.values())

    return {
        "meta": {
            "schema": "snoredex-print-identity-dryrun",
            "schemaVersion": SCHEMA_VERSION,
            "generated": date.today().isoformat(),
            "adr": "verification/ADR-0001-locality-aware-print-identity.md",
            "status": "dry-run — proposes nothing to authoritative stores, migrates nothing",
            "baselineId": baseline["meta"]["baselineId"],
            "description": (
                "Maps claims onto language-bearing card releases and positively evidenced "
                "physical printings. Candidate-only claims remain visible and cannot mint an "
                "existence-bearing node."
            ),
        },
        "localities": LOCALITIES,
        "counts": {
            "legacyProducts": len(cards),
            "legacyProductIdentityTuples": len(cards_by_key),
            "legacyLanguageUnits": len(units),
            "legacyExcludedCodeCardUnits": len(excluded),
            "sourceFirstRecords": len(source_first.get("prints", [])),
            "finishPrintingClaims": sum(len(u.get("printings", [])) for u in finish_units),
            "candidateClaims": len(candidate_claims),
            "candidateClaimDispositions": dict(sorted(claim_dispositions.items())),
            "setEditionNodes": len(set_editions),
            "cardReleaseNodes": len(card_releases),
            "cardReleaseNodesIdentified": len(card_releases) - len(needs_identifier),
            "cardReleaseNodesNeedingLocalIdentifier": len(needs_identifier),
            "physicalPrintingNodes": len(physical_printings),
            "physicalPrintingsByEvidenceClass": {
                "finish-store": len(physical_printings) - specimen_printings,
                "inspected-specimen": specimen_printings,
            },
            "specimenObservationsCorroboratingFinishStore": specimen_corroborations,
            "contradictedOnlyCardReleaseProposals": len(contradicted_only),
            "mixedStatusCardReleaseProposals": len(mixed_status),
            "multiVariantCardReleases": len(multi_variant),
            "crossLanguageIdentityMerges": len(cross_language_merges),
            "unexplainedProductSplits": len(unexplained_splits),
            "identityCollisions": len(unexplained_collision_keys),
            "positivelyExcludedIdentityCollisions": len(positively_excluded_collision_keys),
            "unresolvedUnits": len(unresolved_units),
            "unresolvedPhysicalClaims": len(unresolved_physical),
            "orphanSpecimens": len(orphan_specimens),
            "heldSpecimenDispositions": len(held_specimen_dispositions),
            "sourceFirstPrintsAdmitted": len(source_first.get("prints", [])),
            "sourceFirstPrintsHeld": len(source_first.get("held", [])),
            "equivalenceAssertions": len(equivalence_assertions),
            "legacyIssueRekeySets": len(legacy_issue_rekeys),
            "cardReleaseNodesByLocality": dict(
                sorted(release_by_locality.items(), key=lambda kv: -kv[1])),
            "needsLocalIdentifierByLocality": dict(
                sorted(unknown_by_locality.items(), key=lambda kv: -kv[1])),
        },
        "legacyProductDispositions": dict(sorted(card_disposition.items())),
        "reports": {
            "contradictedOnlyCardReleaseProposals": sorted(
                contradicted_only, key=lambda item: item["proposedCardReleaseId"]),
            "mixedStatusCardReleaseProposals": sorted(
                mixed_status, key=lambda item: item["proposedCardReleaseId"]),
            "multiVariantCardReleases": sorted(
                multi_variant, key=lambda item: item["cardReleaseId"]),
            "needsLocalIdentifier": sorted(
                ({
                    "cardReleaseId": r["cardReleaseId"],
                    "locality": r["locality"],
                    "language": r["language"],
                    "viaProduct": f"{r['viaLegacySetCode']} {r['viaLegacyNumber']}",
                    "claimIds": r["claimIds"],
                } for r in needs_identifier),
                key=lambda item: (item["locality"], item["language"], item["viaProduct"]),
            ),
            "crossLanguageIdentityMerges": sorted(cross_language_merges),
            "unexplainedProductSplits": sorted(
                unexplained_splits, key=lambda item: item["legacyProduct"]),
            "identityCollisions": [
                {"setCode": k[0], "number": k[1], "variant": k[2],
                 "sourceRecords": sorted(v)}
                for k, v in sorted(identity_collisions.items()) if k in unexplained_collision_keys
            ],
            "positivelyExcludedIdentityCollisions": [
                {"setCode": k[0], "number": k[1], "variant": k[2],
                 "sourceRecords": sorted(identity_collisions[k]),
                 "reason": "all colliding records are code-card products outside the physical-card catalogue"}
                for k in sorted(positively_excluded_collision_keys)
            ],
            "unresolvedUnits": sorted(unresolved_units, key=lambda item: item["unitId"]),
            "unresolvedPhysicalClaims": sorted(
                unresolved_physical, key=lambda item: item["printingId"]),
            "orphanSpecimens": sorted(
                orphan_specimens, key=lambda item: str(item["specimenId"])),
            "heldSpecimenDispositions": sorted(
                held_specimen_dispositions, key=lambda item: str(item["specimenId"])),
            "legacyIssueRekeys": legacy_issue_rekeys,
        },
        "equivalenceAssertions": sorted(
            equivalence_assertions, key=lambda item: item["assertionId"]),
        "candidateClaims": [candidate_claims[cid] for cid in sorted(candidate_claims)],
        "setEditions": [set_editions[eid] for eid in sorted(set_editions)],
        "cardReleases": [card_releases[rid] for rid in sorted(card_releases)],
        "physicalPrintings": [
            physical_printings[pid] for pid in sorted(physical_printings)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the report is stale")
    args = parser.parse_args()

    cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    units = read_json(ROOT / "verification" / "units.json")
    finish_units = read_json(ROOT / "verification" / "finish_units.json")["units"]
    excluded = read_json(ROOT / "verification" / "excluded_codecards.json")
    specimen_doc = read_json(ROOT / "verification" / "specimens.json")
    specimens = specimen_doc["specimens"] if isinstance(specimen_doc, dict) else specimen_doc
    baseline = read_json(ROOT / "legacy-cardmarket-baseline.json")
    source_first = read_json(ROOT / "verification" / "source_first_prints.json")
    rekeys = read_json(ROOT / "verification" / "legacy_issue_rekeys.json")

    document = build(
        cards, units, finish_units, excluded, specimens, baseline, source_first, rekeys)

    if args.check:
        if not OUTPUT_PATH.is_file():
            print("print_identity_dryrun.json missing; run python scripts/print_identity_dryrun.py")
            return 1
        existing = read_json(OUTPUT_PATH)
        comparable = {k: v for k, v in document.items() if k != "meta"}
        if {k: v for k, v in existing.items() if k != "meta"} != comparable:
            print("print_identity_dryrun.json is stale; run python scripts/print_identity_dryrun.py")
            return 1
        counts = document["counts"]
        print(
            "print identity dry run is current "
            f"({counts['cardReleaseNodes']} card releases, "
            f"{counts['physicalPrintingNodes']} physical printings)"
        )
        return 0

    OUTPUT_PATH.write_bytes(
        (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    counts = document["counts"]
    print(
        f"{OUTPUT_PATH.relative_to(ROOT)}: {counts['candidateClaims']} claims -> "
        f"{counts['cardReleaseNodes']} card releases + "
        f"{counts['physicalPrintingNodes']} physical printings"
    )
    print(
        f"  {counts['contradictedOnlyCardReleaseProposals']} contradicted-only release "
        f"proposal(s) remain candidates; {counts['crossLanguageIdentityMerges']} "
        f"cross-language merge(s); {counts['unresolvedUnits']} unresolved unit(s); "
        f"{counts['unresolvedPhysicalClaims']} unresolved confirmed physical claim(s)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
