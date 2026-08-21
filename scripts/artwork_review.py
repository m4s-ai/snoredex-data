#!/usr/bin/env python3
"""Build the static artwork/detection review projection for #120.

The authoritative graph remains the source of truth.  This pass only joins graph identities to
the existing image/evidence stores so the browser can review them without inventing a second
catalogue.  Browser actions are proposals; this file never imports them or changes a verdict.

    python scripts/artwork_review.py
    python scripts/artwork_review.py --check
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "verification" / "artwork_review_projection.json"


def load(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value: Any) -> str:
    return str(value or "").strip()


def identity_key(set_code: Any, card_number: Any, language: Any, variant: Any = None) -> tuple[str, str, str, str]:
    return (number(set_code), number(card_number), number(language), number(variant))


def number_match(left: Any, right: Any) -> bool:
    left_value, right_value = number(left), number(right)
    if left_value == right_value:
        return True
    # Some providers omit the denominator.  Only use the short form as a fallback after the set,
    # language and card work already match; never treat a different denominator as identical.
    return bool(left_value and right_value and "/" not in left_value and right_value.startswith(left_value + "/"))


def source_observation(kind: str, identifier: str, payload: dict[str, Any], *, url: str | None = None,
                       evidence: str | None = None, provider: str | None = None,
                       image: str | None = None) -> dict[str, Any]:
    record = {
        "observationId": f"{kind}:{identifier}",
        "kind": kind,
        "provider": provider,
        "url": url,
        "evidence": evidence,
        "contentHash": digest(payload),
        "image": image,
    }
    return record


def build() -> dict[str, Any]:
    graph = load(ROOT / "verification" / "authoritative_graph.json")
    units = load(ROOT / "verification" / "units.json")
    finishes = load(ROOT / "verification" / "finish_units.json")["units"]
    cards = load(ROOT / "snorlax_cards.json")["cards"]
    releases = load(ROOT / "analysis_confirmed_releases.json")["variants"]
    source_first = load(ROOT / "verification" / "source_first_prints.json").get("prints", [])
    specimens = load(ROOT / "verification" / "specimens.json").get("specimens", [])

    entities = {entry["entityId"]: entry for entry in graph["entities"]}
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in graph["entities"]:
        by_type[entry["entityType"]].append(entry)

    edges = graph["edges"]
    release_to_work = {
        edge["fromId"]: edge["toId"]
        for edge in edges
        if edge["fromType"] == "card-release" and edge["relation"] == "implements"
        and edge["toType"] == "work"
    }
    release_to_physical: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge["fromType"] == "physical-printing" and edge["relation"] == "realizes":
            release_to_physical[edge["toId"]].append(edge["fromId"])

    unit_by_id = {row["unitId"]: row for row in units}
    specimen_by_id = {row["specimenId"]: row for row in specimens}
    source_first_by_id = {row["printId"]: row for row in source_first}
    finish_by_printing: dict[str, dict[str, Any]] = {}
    for finish_unit in finishes:
        for printing in finish_unit.get("printings") or []:
            finish_by_printing[printing.get("printingId")] = {
                "finishUnit": finish_unit,
                "printing": printing,
            }

    # Product and unit rows are the best available local image/evidence bridge for legacy claims.
    # The graph still controls identity; these indexes only enrich the review card.
    row_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    row_by_short_key: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in releases:
        for cell in row.get("finishByLanguage") or []:
            language = cell.get("language")
            row_by_key[identity_key(row.get("setCode"), row.get("number"), language, row.get("variant"))].append(row)
            row_by_short_key[(number(row.get("setCode")), number(row.get("number")), number(language))].append(row)

    card_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for card in cards:
        for language in card.get("languagesConfirmed") or card.get("languages") or []:
            card_by_key[identity_key(card.get("setCode"), card.get("number"), language, card.get("variantToken"))].append(card)

    def add_image(images: list[dict[str, Any]], src: str | None, *, label: str, observation_id: str | None = None) -> None:
        if not src:
            return
        if any(item["src"] == src for item in images):
            return
        local = ROOT / src if not re.match(r"^https?://", src) else None
        content_hash = file_digest(local) if local else None
        images.append({
            "src": src,
            "label": label,
            "observationId": observation_id,
            "contentHash": content_hash,
            "kind": "repository" if local else "source-url",
            "reviewable": bool(content_hash),
        })

    def unit_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for claim_id in payload.get("claimIds") or []:
            match = re.fullmatch(r"CLAIM:legacy:(U\d+)", claim_id)
            if match and match.group(1) in unit_by_id:
                candidates.append(unit_by_id[match.group(1)])
        if candidates:
            return candidates
        set_code = payload.get("viaLegacySetCode")
        card_number = payload.get("viaLegacyNumber")
        language = payload.get("language")
        variant = (payload.get("legacyVariants") or [None])[0]
        for row in units:
            if row.get("language") != language or row.get("setCode") != set_code:
                continue
            if not number_match(card_number, row.get("number")):
                continue
            if variant and row.get("variant") != variant:
                continue
            candidates.append(row)
        return candidates

    def release_projection(entity: dict[str, Any]) -> dict[str, Any]:
        payload = entity["payload"]
        release_id = entity["entityId"]
        work_id = release_to_work.get(release_id) or payload.get("work")
        images: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        detection = {
            "state": "catalogue-derived",
            "cardName": None,
            "artist": None,
            "variant": ", ".join(payload.get("legacyVariants") or []) or None,
            "finish": [],
            "foilPattern": [],
            "markings": [],
            "confidence": None,
            "note": "No separate ML/OCR confidence is stored; these are the current canonical detection fields.",
        }

        for unit in unit_candidates(payload):
            observation_payload = {
                "unitId": unit["unitId"],
                "sourceUrl": unit.get("sourceUrl"),
                "sourceType": unit.get("sourceType"),
                "providerId": unit.get("providerId"),
                "sourceRef": unit.get("sourceRef"),
                "evidence": unit.get("evidence"),
            }
            observations.append(source_observation(
                "unit", unit["unitId"], observation_payload,
                url=unit.get("sourceUrl"), evidence=unit.get("evidence"),
                provider=unit.get("providerId"), image=unit.get("image"),
            ))
            add_image(images, unit.get("image"), label="legacy product image", observation_id=f"unit:{unit['unitId']}")
            detection["cardName"] = detection["cardName"] or unit.get("cardName")
            detection["artist"] = detection["artist"] or unit.get("artist")
            if unit.get("sourceRef"):
                specimen_id = str(unit["sourceRef"]).removeprefix("specimen:")
                specimen = specimen_by_id.get(specimen_id)
                if specimen:
                    photograph = specimen.get("photograph")
                    if photograph and not re.match(r"^https?://", str(photograph)) and "/" not in str(photograph):
                        photograph = f"verification/specimens/{photograph}"
                    observations.append(source_observation(
                        "specimen", specimen_id, specimen,
                        evidence=specimen.get("observed"), image=photograph,
                        provider="collection-owner",
                    ))
                    add_image(images, photograph, label="inspected specimen", observation_id=f"specimen:{specimen_id}")

        for print_id in payload.get("sourceFirstRecordIds") or []:
            record = source_first_by_id.get(print_id)
            if not record:
                continue
            observations.append(source_observation(
                "source-first", print_id, record,
                url=record.get("sourceUrl"), evidence=record.get("evidence"),
                provider=record.get("providerId"), image=record.get("cardImageUrl"),
            ))
            add_image(images, record.get("cardImageUrl"), label="publisher card image", observation_id=f"source-first:{print_id}")
            detection["cardName"] = detection["cardName"] or record.get("name") or record.get("cardName")

        # A legacy row can provide the artist and finish context even when a graph release is a
        # source-first re-key with no direct unit id.
        candidates = []
        for set_code in (payload.get("localSetCode"), payload.get("viaLegacySetCode")):
            for row in row_by_short_key.get((number(set_code), number(payload.get("localNumber")), number(payload.get("language"))), []):
                candidates.append(row)
            for row in row_by_short_key.get((number(set_code), number(payload.get("viaLegacyNumber")), number(payload.get("language"))), []):
                candidates.append(row)
        if candidates:
            row = candidates[0]
            detection["cardName"] = detection["cardName"] or row.get("name")
            detection["artist"] = detection["artist"] or row.get("artist")
            for cell in row.get("finishByLanguage") or []:
                if cell.get("language") != payload.get("language"):
                    continue
                for printing in cell.get("printings") or []:
                    if printing.get("finish"):
                        detection["finish"].append(printing["finish"])
                    if printing.get("foilPattern"):
                        detection["foilPattern"].append(printing["foilPattern"])
                    for marking in printing.get("markings") or []:
                        text = marking.get("text") if isinstance(marking, dict) else marking
                        if text:
                            detection["markings"].append(text)

        physical = []
        for physical_id in sorted(release_to_physical.get(release_id, [])):
            physical_entity = entities.get(physical_id)
            if not physical_entity:
                continue
            printing = dict(physical_entity["payload"])
            finish_source = finish_by_printing.get(printing.get("sourcePrintingId") or printing.get("physicalPrintingId"))
            if finish_source:
                finish_unit = finish_source["finishUnit"]
                source_printing = finish_source["printing"]
                printing["sources"] = source_printing.get("sources") or []
                for source_index, source in enumerate(printing["sources"]):
                    source_tag = f"{source_index}:{digest(source)[:16]}"
                    observations.append(source_observation(
                        "finish", f"{printing.get('sourcePrintingId') or physical_id}:{source_tag}",
                        {"finishUnitId": finish_unit.get("finishUnitId"), "printing": source_printing, "source": source},
                        url=source.get("url"), evidence=source.get("evidence"), provider=source.get("sourceType"),
                    ))
            physical.append(printing)
            detection["finish"].append(printing.get("finish"))
            if printing.get("foilPattern"):
                detection["foilPattern"].append(printing["foilPattern"])
            for marking in printing.get("markings") or []:
                text = marking.get("text") if isinstance(marking, dict) else marking
                if text:
                    detection["markings"].append(text)

        for key in ("finish", "foilPattern", "markings"):
            detection[key] = sorted({value for value in detection[key] if value})
        unique_observations = {item["observationId"]: item for item in observations}
        return {
            "cardReleaseId": release_id,
            "workId": work_id,
            "locality": payload.get("locality"),
            "language": payload.get("language"),
            "script": payload.get("script"),
            "setEditionId": payload.get("setEditionId"),
            "localSetCode": payload.get("localSetCode"),
            "localNumber": payload.get("localNumber"),
            "localIdentifierKnown": bool(payload.get("localIdentifierKnown")),
            "state": payload.get("state"),
            "workMappingState": payload.get("workMappingState"),
            "legacyCounterpartUnitIds": payload.get("legacyCounterpartUnitIds") or [],
            "legacyVariants": payload.get("legacyVariants") or [],
            "physicalPrintings": physical,
            "detection": detection,
            "images": images,
            "observations": sorted(unique_observations.values(), key=lambda item: item["observationId"]),
        }

    releases_projection = [release_projection(entity) for entity in by_type.get("card-release", [])]
    releases_projection.sort(key=lambda item: item["cardReleaseId"])

    groups: dict[str, dict[str, Any]] = {}
    work_entities = {entity["entityId"]: entity for entity in by_type.get("work", [])}
    for member in releases_projection:
        group_id = member["workId"] or f"UNMAPPED:{member['cardReleaseId']}"
        if group_id not in groups:
            work = work_entities.get(group_id)
            card_key = (work or {}).get("payload", {}).get("cardKey") if work else None
            groups[group_id] = {
                "groupId": group_id,
                "groupKind": "mapped-work" if work else "unmapped-release",
                "workId": group_id if work else None,
                "cardKey": card_key,
                "label": card_key or "Unmapped source-first release",
                "members": [],
            }
        groups[group_id]["members"].append(member)

    projection = {
        "schema": "snoredex-artwork-review",
        "schemaVersion": "1.0.0",
        "proposalSchema": "snoredex-artwork-review-proposal",
        "proposalSchemaVersion": "1.0.0",
        "generated": graph["meta"].get("generated"),
        "projectionVersion": digest({
            "graph": graph["meta"].get("inputs"),
            "graphSchemaVersion": graph["meta"].get("schemaVersion"),
            "units": digest(units),
            "finishes": digest(finishes),
            "sourceFirst": digest(source_first),
        }),
        "identitySource": "verification/authoritative_graph.json",
        "reviewBoundary": "Browser proposals never write authoritative stores; reviewed imports must validate stale ids, hashes and before-values.",
        "summary": {
            "groups": len(groups),
            "mappedWorks": sum(1 for group in groups.values() if group["groupKind"] == "mapped-work"),
            "unmappedReleases": sum(1 for group in groups.values() if group["groupKind"] == "unmapped-release"),
            "cardReleases": len(releases_projection),
            "physicalPrintings": sum(len(member["physicalPrintings"]) for member in releases_projection),
            "sourceObservations": sum(len(member["observations"]) for member in releases_projection),
        },
        "groups": sorted(groups.values(), key=lambda group: (group["groupKind"], group["label"], group["groupId"])),
    }
    return projection


def main() -> int:
    projection = build()
    rendered = json.dumps(projection, ensure_ascii=False, indent=2) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != rendered:
            print(f"stale: {OUT.relative_to(ROOT)}; run python scripts/artwork_review.py")
            return 1
        print(f"artwork review projection is current ({projection['summary']['groups']} groups)")
        return 0
    OUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"{OUT.relative_to(ROOT)}: {projection['summary']['groups']} groups, "
          f"{projection['summary']['cardReleases']} releases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
