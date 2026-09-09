#!/usr/bin/env python3
"""Build the static artwork/detection review projection for #120.

The authoritative graph remains the source of truth.  This pass only joins graph identities to
the existing image/evidence stores so the browser can review them without inventing a second
catalogue.  Browser actions are proposals; this file never imports them or changes a verdict.
The normal write pass also creates missing deterministic preview/thumbnail derivatives before
writing the projection, so a newly admitted local image cannot leave an invalid projection.

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

import artwork_derivatives
from source_registry import provenance_url

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "verification" / "artwork_review_projection.json"
OUT_JS = ROOT / "verification" / "artwork_review_projection.js"


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


def image_derivatives(src: str, content_hash: str | None) -> dict[str, str]:
    if not content_hash:
        return {}
    result = {"originalHash": content_hash}
    for key, kind in (("previewSrc", "preview"), ("thumbnailSrc", "thumbnail")):
        candidate = artwork_derivatives.current_derivatives(ROOT / src, content_hash).get(kind)
        if candidate:
            path = candidate.resolve().relative_to(ROOT.resolve()).as_posix()
            result[key] = f"{path}?v={content_hash}"
    return result


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
        "contentHash": semantic_digest(payload),
        "image": image,
    }
    return record


def image_identity(images: list[dict[str, Any]]) -> tuple[str | None, str]:
    """Return a stable automatic image-group anchor and its non-reviewed state."""
    reviewable = [image for image in images
                  if image.get("reviewable") and image.get("contentHash")]
    if not reviewable:
        return None, "unresolved-release"
    return f"IMAGE-GROUP:{reviewable[0]['contentHash'][:24]}", "unreviewed-image-group"


def first_sorted_variant(payload: dict[str, Any]) -> str | None:
    variants = sorted(payload.get("legacyVariants") or [], key=digest)
    return variants[0] if variants else None


SET_LIKE_FIELDS = frozenset({
    "alternateCardImageUrls", "cardImageUrls", "cardReleaseIds", "claimFields", "claimIds",
    "corroboratingSourceUrls", "citedBy", "evidenceRefs", "establishingClaimIds",
    "establishingEvidenceIds", "expectedSubtypes", "finish", "foilPattern", "languages",
    "legacyCounterpartUnitIds", "legacyIdentityAliases", "legacyProducts", "legacyVariants",
    "mappedVariants", "markings", "marketScopes", "observedCollectorNumbers", "observedNames",
    "ownerAttestedFields", "pairedCodes", "printIds", "productIds", "providerRecordIds", "providers",
    "raritySupportingSourceUrls", "setEditionIds", "snorlaxPrintIds", "snorlaxUnitIds",
    "sourceFirstRecordIds", "sourceRecordIds", "sourceUrls", "sources", "specimenIds",
    "supportingSourceUrls", "targetRefs", "viaLegacySetCodes",
})


def normalize_semantic(value: Any) -> Any:
    """Canonicalize set-like fields recursively at the data/hash boundary."""
    if isinstance(value, list):
        return [normalize_semantic(item) for item in value]
    if not isinstance(value, dict):
        return value
    normalized = {key: normalize_semantic(child) for key, child in value.items()}
    for key in SET_LIKE_FIELDS:
        child = normalized.get(key)
        if isinstance(child, list):
            normalized[key] = sorted(child, key=digest)
        elif isinstance(child, dict):
            normalized[key] = {
                entry_key: sorted(entry_value, key=digest) if isinstance(entry_value, list) else entry_value
                for entry_key, entry_value in sorted(child.items())
            }
    return normalized


def semantic_digest(value: Any) -> str:
    return digest(normalize_semantic(value))


def semantic_detection_payload(detection: dict[str, Any]) -> dict[str, Any]:
    return {key: detection.get(key) for key in
            ("state", "cardName", "artist", "variant", "finish", "foilPattern", "markings", "confidence")}


def semantic_member_payload(member: dict[str, Any]) -> dict[str, Any]:
    return {
        key: member.get(key)
        for key in ("cardReleaseId", "workId", "cardKey", "reviewedAppearanceId", "imageGroupId",
                    "appearanceIdentityState", "locality", "language", "script", "setEditionId",
                    "localSetCode", "localNumber", "localIdentifierKnown", "state", "workMappingState",
                    "legacyCounterpartUnitIds", "legacyVariants")
    } | {
        "detection": semantic_detection_payload(member.get("detection") or {}),
        "physicalPrintings": [
            {key: printing.get(key) for key in printing if key != "sources"}
            for printing in member.get("physicalPrintings") or []
        ],
        "images": [{"contentHash": image.get("contentHash"), "reviewable": image.get("reviewable")}
                   for image in member.get("images") or []],
        "observations": [{"observationId": observation.get("observationId"),
                          "contentHash": observation.get("contentHash")}
                         for observation in member.get("observations") or []],
    }


def semantic_projection_payload(projection: dict[str, Any]) -> dict[str, Any]:
    """Return proposal-validation fields, excluding public and nested display metadata."""
    return {
        "schemaVersion": projection["schemaVersion"],
        "proposalSchemaVersion": projection["proposalSchemaVersion"],
        "groups": [{key: group.get(key) for key in
                    ("groupId", "groupKind", "reviewedAppearanceId", "imageGroupId",
                     "appearanceIdentityState", "workIds", "cardKeys")}
                   | {"members": [semantic_member_payload(member)
                                  for member in group.get("members") or []]}
                   for group in projection.get("groups") or []],
    }


def build_groups(releases_projection: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group releases by automatic image anchor while keeping unresolved releases isolated."""
    groups: dict[str, dict[str, Any]] = {}
    for member in releases_projection:
        group_id = member["imageGroupId"] or f"RELEASE-GROUP:{member['cardReleaseId']}"
        group_kind = "image-group" if member["imageGroupId"] else "unmapped-release"
        if group_id not in groups:
            groups[group_id] = {
                "groupId": group_id,
                "groupKind": group_kind,
                "reviewedAppearanceId": None,
                "imageGroupId": member["imageGroupId"],
                "appearanceIdentityState": member["appearanceIdentityState"],
                "workIds": [],
                "cardKeys": [],
                "label": member.get("cardKey") or "Unresolved artwork appearance",
                "members": [],
            }
        if member.get("workId"):
            groups[group_id]["workIds"].append(member["workId"])
        if member.get("cardKey"):
            groups[group_id]["cardKeys"].append(member["cardKey"])
        groups[group_id]["members"].append(member)

    for group in groups.values():
        group["workIds"] = sorted(set(group["workIds"]))
        group["cardKeys"] = sorted(set(group["cardKeys"]))
    return groups


def specimen_citations(specimens: list[dict[str, Any]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for specimen in specimens:
        for citation in specimen.get("citedBy") or []:
            result[citation].add(specimen["specimenId"])
    return result


def release_specimens(payload: dict, physical: list[dict], citations: dict, records: dict) -> list[str]:
    linked = set()
    for print_id in payload.get("sourceFirstRecordIds") or []:
        linked.update(citations.get(print_id, set()))
        specimen_id = records.get(print_id, {}).get("specimenId")
        if specimen_id:
            linked.add(specimen_id)
    for printing in physical:
        linked.update(printing.get("specimenIds") or [])
        printing_id = printing.get("physicalPrintingId", "")
        if printing_id.startswith("PHYSICAL:specimen:"):
            linked.add(printing_id.removeprefix("PHYSICAL:specimen:"))
    return sorted(linked)


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
        for edge in sorted(edges, key=lambda item: (item.get("fromId", ""), item.get("toId", "")))
        if edge["fromType"] == "card-release" and edge["relation"] == "implements"
        and edge["toType"] == "work"
    }
    release_to_physical: dict[str, list[str]] = defaultdict(list)
    for edge in sorted(edges, key=lambda item: (item.get("toId", ""), item.get("fromId", ""))):
        if edge["fromType"] == "physical-printing" and edge["relation"] == "realizes":
            release_to_physical[edge["toId"]].append(edge["fromId"])

    unit_by_id = {row["unitId"]: row for row in units}
    specimen_by_id = {row["specimenId"]: row for row in specimens}
    specimens_by_citation = specimen_citations(specimens)
    source_first_by_id = {row["printId"]: row for row in source_first}
    finish_by_printing: dict[str, dict[str, Any]] = {}
    for finish_unit in sorted(finishes, key=lambda item: item.get("finishUnitId", "")):
        for printing in sorted(finish_unit.get("printings") or [], key=lambda item: item.get("printingId", "")):
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
        image = {
            "src": src,
            "label": label,
            "observationId": observation_id,
            "contentHash": content_hash,
            "kind": "repository" if local else "source-url",
            "reviewable": bool(content_hash),
        }
        if local:
            image.update(image_derivatives(src, content_hash))
        images.append(image)

    def add_specimen(specimen_id: str, observations: list, images: list) -> None:
        specimen = specimen_by_id.get(specimen_id)
        if not specimen:
            return
        photograph = specimen.get("photograph")
        if photograph and not re.match(r"^https?://", str(photograph)) and "/" not in str(photograph):
            photograph = f"verification/specimens/{photograph}"
        observations.append(source_observation(
            "specimen", specimen_id, specimen,
            evidence=specimen.get("observed"), image=photograph,
            url=provenance_url(specimen.get("listingUrl")) or provenance_url(specimen.get("photographSource")),
        ))
        add_image(images, photograph, label="inspected specimen", observation_id=f"specimen:{specimen_id}")

    def unit_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for claim_id in sorted(payload.get("claimIds") or []):
            match = re.fullmatch(r"CLAIM:legacy:(U\d+)", claim_id)
            if match and match.group(1) in unit_by_id:
                candidates.append(unit_by_id[match.group(1)])
        if candidates:
            return sorted(candidates, key=lambda item: item.get("unitId", ""))
        set_code = payload.get("viaLegacySetCode")
        card_number = payload.get("viaLegacyNumber")
        language = payload.get("language")
        variant = first_sorted_variant(payload)
        for row in sorted(units, key=lambda item: item.get("unitId", "")):
            if row.get("language") != language or row.get("setCode") != set_code:
                continue
            if not number_match(card_number, row.get("number")):
                continue
            if variant and row.get("variant") != variant:
                continue
            candidates.append(row)
        return sorted(candidates, key=lambda item: item.get("unitId", ""))

    def release_projection(entity: dict[str, Any]) -> dict[str, Any]:
        payload = entity["payload"]
        release_id = entity["entityId"]
        legacy_variants = sorted(payload.get("legacyVariants") or [], key=digest)
        work_id = release_to_work.get(release_id) or payload.get("work")
        work_entity = entities.get(work_id)
        card_key = (work_entity or {}).get("payload", {}).get("cardKey")
        images: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        detection = {
            "state": "catalogue-derived",
            "cardName": None,
            "artist": None,
            "variant": ", ".join(legacy_variants) or None,
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
                add_specimen(specimen_id, observations, images)

        for print_id in sorted(payload.get("sourceFirstRecordIds") or []):
            record = source_first_by_id.get(print_id)
            if not record:
                continue
            normalized_record = normalize_semantic(record)
            observations.append(source_observation(
                "source-first", print_id, normalized_record,
                url=normalized_record.get("sourceUrl"), evidence=normalized_record.get("evidence"),
                provider=normalized_record.get("providerId"), image=normalized_record.get("cardImageUrl"),
            ))
            add_image(images, normalized_record.get("cardImageUrl"), label="publisher card image", observation_id=f"source-first:{print_id}")
            detection["cardName"] = detection["cardName"] or normalized_record.get("name") or normalized_record.get("cardName")

        # A legacy row can provide the artist and finish context even when a graph release is a
        # source-first re-key with no direct unit id.
        candidates = []
        for set_code in (payload.get("localSetCode"), payload.get("viaLegacySetCode")):
            for row in sorted(row_by_short_key.get((number(set_code), number(payload.get("localNumber")), number(payload.get("language"))), []),
                              key=lambda item: (item.get("rowId", ""), item.get("setCode", ""), item.get("number", ""))):
                candidates.append(row)
            for row in sorted(row_by_short_key.get((number(set_code), number(payload.get("viaLegacyNumber")), number(payload.get("language"))), []),
                              key=lambda item: (item.get("rowId", ""), item.get("setCode", ""), item.get("number", ""))):
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
            printing = normalize_semantic(physical_entity["payload"])
            finish_source = finish_by_printing.get(printing.get("sourcePrintingId") or printing.get("physicalPrintingId"))
            if finish_source:
                finish_unit = finish_source["finishUnit"]
                source_printing = finish_source["printing"]
                normalized_source_printing = normalize_semantic(source_printing)
                normalized_sources = normalized_source_printing.get("sources") or []
                printing["sources"] = normalized_sources
                for source_index, source in enumerate(normalized_sources):
                    source_tag = f"{source_index}:{semantic_digest(source)[:16]}"
                    observations.append(source_observation(
                        "finish", f"{printing.get('sourcePrintingId') or physical_id}:{source_tag}",
                        {"finishUnitId": finish_unit.get("finishUnitId"),
                         "printing": normalized_source_printing, "source": source},
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

        for specimen_id in release_specimens(payload, physical, specimens_by_citation, source_first_by_id):
            add_specimen(specimen_id, observations, images)

        for key in ("finish", "foilPattern", "markings"):
            detection[key] = sorted({value for value in detection[key] if value})
        # This is an automatically derived image group, not a reviewed artwork identity.  The
        # first canonical reviewable image is the stable anchor so adding a later specimen
        # records new evidence without renaming the existing group. Releases without pinned bytes
        # remain isolated until a reviewer supplies explicit appearance evidence.
        image_group_id, appearance_state = image_identity(images)
        unique_observations = {item["observationId"]: item for item in observations}
        return {
            "cardReleaseId": release_id,
            "workId": work_id,
            "cardKey": card_key,
            "reviewedAppearanceId": None,
            "imageGroupId": image_group_id,
            "appearanceIdentityState": appearance_state,
            "locality": payload.get("locality"),
            "language": payload.get("language"),
            "script": payload.get("script"),
            "setEditionId": payload.get("setEditionId"),
            "localSetCode": payload.get("localSetCode"),
            "localNumber": payload.get("localNumber"),
            "localIdentifierKnown": bool(payload.get("localIdentifierKnown")),
            "state": payload.get("state"),
            "workMappingState": payload.get("workMappingState"),
            "legacyCounterpartUnitIds": sorted(payload.get("legacyCounterpartUnitIds") or []),
            "legacyVariants": legacy_variants,
            "physicalPrintings": physical,
            "detection": detection,
            "images": images,
            "observations": sorted(unique_observations.values(), key=lambda item: item["observationId"]),
        }

    releases_projection = [release_projection(entity) for entity in by_type.get("card-release", [])]
    releases_projection.sort(key=lambda item: item["cardReleaseId"])

    groups = build_groups(releases_projection)

    projection = {
        "schema": "snoredex-artwork-review",
        "schemaVersion": "1.2.0",
        "proposalSchema": "snoredex-artwork-review-proposal",
        "proposalSchemaVersion": "1.2.0",
        "generated": graph["meta"].get("generated"),
        # Filled after the semantic projection is normalized below. Keeping the placeholder here
        # makes it explicit that no partial input digest can be mistaken for the version.
        "projectionVersion": None,
        "identitySource": "verification/authoritative_graph.json",
        "appearanceIdentity": "Automatic image groups use a stable pinned-image anchor and are review suggestions only; reviewedAppearanceId remains null until a human artwork decision is imported.",
        "reviewBoundary": "Browser proposals never write authoritative stores; reviewed imports must validate stale ids, hashes and before-values.",
        "summary": {
            "groups": len(groups),
            "mappedWorks": len({member["workId"] for member in releases_projection if member.get("workId") and member.get("workMappingState") == "mapped"}),
            "imageGroups": sum(1 for group in groups.values() if group["groupKind"] == "image-group"),
            "reviewedAppearances": sum(1 for group in groups.values() if group.get("reviewedAppearanceId")),
            # Kept as an explicit zero for consumers that still read the old field; automatic image
            # groups must never be counted as reviewed appearances.
            "mappedAppearances": sum(1 for group in groups.values() if group.get("reviewedAppearanceId")),
            "unmappedReleases": sum(1 for group in groups.values() if group["groupKind"] == "unmapped-release"),
            "cardReleases": len(releases_projection),
            "physicalPrintings": sum(len(member["physicalPrintings"]) for member in releases_projection),
            "sourceObservations": sum(len(member["observations"]) for member in releases_projection),
        },
        "groups": sorted(groups.values(), key=lambda group: ({"image-group": 0, "unmapped-release": 1}[group["groupKind"]], group["label"], group["groupId"])),
    }
    projection["groups"] = normalize_semantic(projection["groups"])
    # Bind the version to the review semantics after all order-independent normalization above.
    # Public explanatory copy and source paths stay outside this digest so editorial changes do
    # not invalidate locally saved proposals.
    # The generated timestamp describes when the snapshot was built, not what a reviewer can
    # inspect.  Keep it in the public projection for provenance, but exclude it from the semantic
    # version so a routine refresh does not invalidate every saved proposal.
    projection["projectionVersion"] = semantic_digest(semantic_projection_payload(projection))
    return projection


def projection_sources(projection: dict[str, Any]) -> list[Path]:
    return [ROOT / image["src"]
            for group in projection["groups"]
            for member in group["members"]
            for image in member["images"]
            if image.get("kind") == "repository" and image.get("src")]


def rendered_outputs(projection: dict[str, Any]) -> tuple[str, str]:
    rendered = json.dumps(projection, ensure_ascii=False, indent=2) + "\n"
    rendered_js = "// Generated by scripts/artwork_review.py; do not edit.\n" \
        "window.__SNOREDEX_ARTWORK_REVIEW__ = " \
        + json.dumps(projection, ensure_ascii=False, separators=(",", ":")) + ";\n"
    return rendered, rendered_js


def outputs_current(rendered: str, rendered_js: str) -> bool:
    return (OUT.exists() and OUT.read_text(encoding="utf-8") == rendered
            and OUT_JS.exists() and OUT_JS.read_text(encoding="utf-8") == rendered_js)


def main() -> int:
    check_only = "--check" in sys.argv
    projection = build()
    if not check_only:
        artwork_derivatives.ensure_for_sources(projection_sources(projection))
        projection = build()
    rendered, rendered_js = rendered_outputs(projection)
    if check_only:
        if not outputs_current(rendered, rendered_js):
            print(f"stale: {OUT.relative_to(ROOT)} or {OUT_JS.relative_to(ROOT)}; "
                  "run python scripts/artwork_review.py")
            return 1
        print(f"artwork review projection is current ({projection['summary']['groups']} groups)")
        return 0
    OUT.write_text(rendered, encoding="utf-8", newline="\n")
    OUT_JS.write_text(rendered_js, encoding="utf-8", newline="\n")
    print(f"{OUT.relative_to(ROOT)}: {projection['summary']['groups']} groups, "
          f"{projection['summary']['cardReleases']} releases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
