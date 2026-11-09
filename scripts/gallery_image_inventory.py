"""Inventory local gallery image candidates without asserting a new printing identity."""

import hashlib
import json
import sys
from pathlib import Path

from file_digest import sha256_hex
from specimen_links import specimen_reference_index

ROOT = Path(__file__).resolve().parents[1]
SPECIMENS = "verification/specimens.json"
INPUTS = ("collector_catalogue.json", "verification/artwork_review_projection.json", "site/gallery-review.json", SPECIMENS)
sys.path.insert(0, str(ROOT / "verification"))
from fetch_attachment import image_format, image_size


def inventory_inputs(root):
    return {relative: sha256_hex(root / relative) for relative in INPUTS}


def local_source(root, relative):
    path = root / relative
    allowed = (root / "images", root / "verification/specimens", root / "verification/evidence")
    if not path.resolve().is_relative_to(root.resolve()) or not any(
        path.resolve().is_relative_to(folder.resolve()) for folder in allowed
    ):
        raise ValueError(f"Gallery source outside retained image directories: {relative}")
    return path


def source_info(root, relative):
    if relative.startswith(("https://", "http://")):
        return {"path": relative, "kind": "remote", "sha256": None, "dimensions": None}
    path = local_source(root, relative)
    data = path.read_bytes()
    kind = image_format(data)
    dimensions = image_size(data, kind) if kind else None
    if not dimensions:
        raise ValueError(f"Unreadable gallery source: {relative}")
    return {
        "path": relative, "kind": "unclassified",
        "sha256": hashlib.sha256(data).hexdigest(), "dimensions": list(dimensions),
        "resolution": "short-edge-below-600" if min(dimensions) < 600 else "crop-review-needed",
    }


def member_candidates(item, member, citations):
    specimen_ids = {
        specimen for printing in member.get("physicalPrintings", [])
        if printing["physicalPrintingId"] == item.get("physicalPrintingId")
        for specimen in printing.get("specimenIds", [])
    }
    cited_ids = citations.get(item.get("sourcePrintingId"), ())
    for image in member.get("images", []):
        reference = image.get("observationId") or ""
        specimen_id = reference.removeprefix("specimen:")
        basis = "release-image"
        if specimen_id in specimen_ids:
            basis = "physical-printing-specimen"
        elif specimen_id in cited_ids:
            basis = "finish-printing-citation"
        yield {
            "source": image["src"], "scope": "representative" if basis == "release-image" else "exact-printing",
            "identityBasis": basis,
            "sourceRef": reference,
        }


def item_candidates(item, member, assets, representative, citations):
    candidates = {}
    for candidate in member_candidates(item, member, citations):
        candidates[candidate["source"]] = candidate
    asset = assets.get(item.get("imageAssetId"))
    if asset and asset.get("path"):
        path = asset["path"]
        scope = "exact-printing" if item["imageScope"] == "exact-printing" else "representative"
        if scope == "exact-printing" or candidates.get(path, {}).get("scope") != "exact-printing":
            candidates[path] = {"source": path, "scope": scope,
                                "identityBasis": item["imageScope"], "sourceRef": asset["assetId"]}
    if source := representative.get(item["itemId"]):
        candidates.setdefault(source, {
            "source": source, "scope": "representative",
            "identityBasis": "gallery-representative", "sourceRef": "site/gallery-review.json",
        })
    return sorted(candidates.values(), key=lambda row: row["source"])


def build_inventory(catalogue, artwork, review, cards, root=ROOT):
    members = {member["cardReleaseId"]: member for group in artwork["groups"] for member in group["members"]}
    items = {item["itemId"]: item for item in catalogue["items"] if item["active"]}
    assets = {asset["assetId"]: asset for asset in catalogue["assets"]}
    specimens = json.loads((root / SPECIMENS).read_text(encoding="utf-8"))["specimens"]
    citations = specimen_reference_index(specimens)
    sources = {}
    entries = []
    for card in cards:
        item = items.get(card["id"], {"itemId": card["id"]})
        member = members.get(item.get("cardReleaseId"), {})
        candidates = item_candidates(item, member, assets, review["representativeImages"], citations)
        for candidate in candidates:
            source = candidate["source"]
            if source not in sources:
                sources[source] = source_info(root, source)
        entries.append({
            "itemId": card["id"], "cardReleaseId": item.get("cardReleaseId"),
            "artworkGroup": card["group"], "language": card["language"],
            "setCode": card["setCode"], "number": card["number"], "edition": card["edition"],
            "finish": card["finish"], "foilPattern": card["foilPattern"],
            "distribution": card["distribution"], "candidates": candidates,
            "legacyImage": card.get("imageSource"), "status": "awaiting-batch",
            "selectedRecipe": None,
        })
    return {
        "meta": {"generatedBy": "scripts/site.py", "schemaVersion": 1, "inputs": inventory_inputs(root),
                 "note": "Generated inventory; dimensions describe the source frame, not a reviewed card crop."},
        "sources": dict(sorted(sources.items())), "items": sorted(entries, key=lambda row: row["itemId"]),
    }
