#!/usr/bin/env python3
"""Regression checks for the generated #120 artwork review projection."""

from __future__ import annotations

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import artwork_review  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"[FAIL] artwork review: {message}")


def main() -> int:
    path = ROOT / "verification" / "artwork_review_projection.json"
    if not path.exists():
        fail("projection is missing")
    projection = json.loads(path.read_text(encoding="utf-8"))
    if projection != artwork_review.build():
        fail("projection is stale; run python scripts/artwork_review.py")
    if projection.get("schemaVersion") != "1.2.0" or projection.get("proposalSchemaVersion") != "1.2.0":
        fail("unexpected projection or proposal schema version")

    groups = projection.get("groups") or []
    members = [member for group in groups for member in group.get("members") or []]
    ids = [member.get("cardReleaseId") for member in members]
    if len(ids) != len(set(ids)):
        fail("a card release appears in more than one review group")
    if len(ids) != projection["summary"]["cardReleases"]:
        fail("summary card-release count does not match the projection")
    if sum(len(member.get("physicalPrintings") or []) for member in members) != projection["summary"]["physicalPrintings"]:
        fail("physical-printing accounting drift")
    if not projection.get("appearanceIdentity"):
        fail("appearance identity policy is missing")
    if any(member.get("imageGroupId") != group.get("imageGroupId")
           for group in groups for member in group.get("members") or []):
        fail("release image-group identity does not match its review group")
    if any(member.get("reviewedAppearanceId") is not None
           for group in groups for member in group.get("members") or []):
        fail("generated projection invents a reviewed appearance identity")
    if any(group.get("reviewedAppearanceId") is not None for group in groups):
        fail("generated group invents a reviewed appearance identity")
    if any(group.get("groupId", "").startswith("WORK:")
           for group in groups):
        fail("review groups still use work ids as artwork identity")

    for member in members:
        if not member.get("cardReleaseId") or not member.get("locality") or not member.get("language"):
            fail(f"incomplete stable identity: {member}")
        if member.get("appearanceIdentityState") == "unreviewed-image-group" and not any(
                image.get("reviewable") and image.get("contentHash") for image in member.get("images") or []):
            fail(f"image group has no pinned image: {member['cardReleaseId']}")
        if member.get("workId") and member["workId"] not in member["cardReleaseId"] and member["workMappingState"] == "mapped":
            # The work id is allowed to be unrelated text; this branch only protects accidental
            # empty values while keeping the assertion readable for the graph-backed mapping.
            if not member["workId"].startswith("WORK:"):
                fail(f"mapped release has an invalid work id: {member['cardReleaseId']}")
        observation_ids = [item.get("observationId") for item in member.get("observations") or []]
        if len(observation_ids) != len(set(observation_ids)):
            fail(f"duplicate observation id in release: {member['cardReleaseId']}")
        for observation in member.get("observations") or []:
            if len(observation.get("contentHash", "")) != 64:
                fail(f"observation lacks a SHA-256 content hash: {observation.get('observationId')}")
        for image in member.get("images") or []:
            if image.get("reviewable") != bool(image.get("contentHash")):
                fail(f"image reviewability does not match its hash: {image.get('src')}")
            if image.get("kind") == "repository":
                image_path = ROOT / image["src"]
                if not image_path.is_file():
                    fail(f"repository image is missing: {image['src']}")
                expected = hashlib.sha256(image_path.read_bytes()).hexdigest()
                if image.get("contentHash") != expected:
                    fail(f"repository image hash drift: {image['src']}")
            elif not str(image.get("src", "")).startswith(("http://", "https://")):
                fail(f"external image has no URL: {image.get('src')}")

    if not all(group.get("groupKind") in {"image-group", "unmapped-release"} for group in groups):
        fail("unknown artwork group kind")
    if projection["summary"].get("mappedAppearances") != 0:
        fail("automatic image groups are counted as reviewed appearances")

    # F07: changing a semantic graph field must change the version even when graph metadata stays
    # identical.  The output itself must also carry the changed field.
    original_load = artwork_review.load
    original_graph = original_load(ROOT / "verification" / "authoritative_graph.json")
    changed_graph = deepcopy(original_graph)
    work = next(entity for entity in changed_graph["entities"] if entity["entityType"] == "work")
    work["payload"]["cardKey"] = work["payload"].get("cardKey", "") + "-changed"
    def load_changed_graph(path: Path):
        if path.name == "authoritative_graph.json":
            return changed_graph
        return original_load(path)
    before_version = projection["projectionVersion"]
    artwork_review.load = load_changed_graph
    try:
        changed_projection = artwork_review.build()
    finally:
        artwork_review.load = original_load
    if changed_projection["projectionVersion"] == before_version:
        fail("semantic graph change leaves projectionVersion unchanged")

    # A refresh timestamp is provenance only; changing it must not make semantic proposals stale.
    timestamp_graph = deepcopy(original_graph)
    timestamp_graph["meta"]["generated"] = "2099-12-31"
    def load_timestamp_graph(path: Path):
        if path.name == "authoritative_graph.json":
            return timestamp_graph
        return original_load(path)
    artwork_review.load = load_timestamp_graph
    try:
        timestamp_projection = artwork_review.build()
    finally:
        artwork_review.load = original_load
    if timestamp_projection["projectionVersion"] != before_version:
        fail("generated timestamp changes the semantic projectionVersion")

    # Public explanatory copy and source-path metadata do not change review semantics.
    copy_projection = deepcopy(projection)
    copy_projection["appearanceIdentity"] = "updated explanatory copy"
    copy_projection["reviewBoundary"] = "updated review guidance"
    copy_projection["identitySource"] = "verification/renamed-source.json"
    if artwork_review.digest(artwork_review.semantic_projection_payload(copy_projection)) != before_version:
        fail("explanatory projection metadata changes the semantic projectionVersion")

    # A pure permutation of set-like input collections is presentation-neutral.
    def load_permuted(path: Path):
        data = original_load(path)
        if path.name == "authoritative_graph.json":
            data["entities"] = list(reversed(data["entities"]))
            data["edges"] = list(reversed(data["edges"]))
            for entity in data["entities"]:
                payload = entity.get("payload") or {}
                if payload.get("legacyCounterpartUnitIds"):
                    payload["legacyCounterpartUnitIds"] = list(reversed(payload["legacyCounterpartUnitIds"]))
                if entity.get("entityType") == "physical-printing" and payload.get("markings"):
                    payload["markings"] = list(reversed(payload["markings"]))
                for key in ("specimenIds", "sourceRecordIds"):
                    if payload.get(key):
                        payload[key] = list(reversed(payload[key]))
                if entity.get("entityType") == "card-release" and payload.get("legacyVariants"):
                    payload["legacyVariants"] = list(reversed(payload["legacyVariants"]))
        elif path.name == "finish_units.json":
            data["units"] = list(reversed(data["units"]))
            for unit in data["units"]:
                unit["printings"] = list(reversed(unit.get("printings") or []))
                for printing in unit["printings"]:
                    printing["sources"] = list(reversed(printing.get("sources") or []))
                    for source in printing["sources"]:
                        for key in ("languages", "claimFields", "productIds", "expectedSubtypes"):
                            value = source.get(key)
                            if isinstance(value, list):
                                source[key] = list(reversed(value))
                            elif isinstance(value, dict):
                                source[key] = {
                                    entry_key: list(reversed(entry_value)) if isinstance(entry_value, list) else entry_value
                                    for entry_key, entry_value in reversed(list(value.items()))
                                }
                    for key in ("mappedVariants", "specimenIds", "markings"):
                        if printing.get(key):
                            printing[key] = list(reversed(printing[key]))
        elif path.name == "units.json":
            data = list(reversed(data))
        elif path.name == "snorlax_cards.json":
            data["cards"] = list(reversed(data["cards"]))
        elif path.name == "analysis_confirmed_releases.json":
            data["variants"] = list(reversed(data["variants"]))
        elif path.name == "source_first_prints.json":
            data["prints"] = list(reversed(data["prints"]))
            for record in data["prints"]:
                for key in ("corroboratingSourceUrls", "providerRecordIds",
                            "alternateCardImageUrls", "raritySupportingSourceUrls"):
                    if record.get(key):
                        record[key] = list(reversed(record[key]))
        elif path.name == "specimens.json":
            data["specimens"] = list(reversed(data["specimens"]))
        return data
    artwork_review.load = load_permuted
    try:
        permuted_projection = artwork_review.build()
    finally:
        artwork_review.load = original_load
    if permuted_projection != projection:
        fail("permuting set-like inputs changes the projection")

    # F18: adding a later image is new evidence, not a new reviewed artwork identity or image-group
    # anchor.  The current graph has no reviewed appearance registry, so the reviewed id stays null.
    unit_data = original_load(ROOT / "verification" / "units.json")
    specimen_data = original_load(ROOT / "verification" / "specimens.json")
    candidate_unit = next(row for row in unit_data
                          if row.get("image") and not row.get("sourceRef"))
    candidate_member = next(member for member in members
                            if any(image.get("observationId") == f"unit:{candidate_unit['unitId']}"
                                   for image in member.get("images") or []))
    extra_unit_data = deepcopy(unit_data)
    extra_specimen_data = deepcopy(specimen_data)
    next(row for row in extra_unit_data if row["unitId"] == candidate_unit["unitId"])["sourceRef"] = "specimen:TEST-ARTWORK-EXTRA"
    extra_specimen_data.setdefault("specimens", []).append({
        "specimenId": "TEST-ARTWORK-EXTRA",
        "photograph": "extra-artwork-test.png",
        "observed": "additional image evidence fixture",
    })
    original_file_digest = artwork_review.file_digest
    def load_extra_image(path: Path):
        if path.name == "units.json":
            return extra_unit_data
        if path.name == "specimens.json":
            return extra_specimen_data
        return original_load(path)
    artwork_review.load = load_extra_image
    artwork_review.file_digest = lambda path: "f" * 64 if path.name == "extra-artwork-test.png" else original_file_digest(path)
    try:
        extra_projection = artwork_review.build()
    finally:
        artwork_review.load = original_load
        artwork_review.file_digest = original_file_digest
    extra_member = next(member for group in extra_projection["groups"] for member in group["members"]
                        if member["cardReleaseId"] == candidate_member["cardReleaseId"])
    if extra_member["imageGroupId"] != candidate_member["imageGroupId"]:
        fail("adding a later image renames the automatic image-group anchor")
    if extra_member["reviewedAppearanceId"] is not None:
        fail("additional image creates an invented reviewed appearance id")
    if extra_projection["projectionVersion"] == projection["projectionVersion"]:
        fail("additional image evidence does not change projectionVersion")

    print(f"artwork review projection: {len(groups)} groups, {len(members)} releases, "
          f"{projection['summary']['physicalPrintings']} physical printings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
