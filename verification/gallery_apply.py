
"""Apply reviewed gallery manifests after checking the immutable photo archive."""
from __future__ import annotations

import math
import uuid
from pathlib import Path

from gallery_workflow import (
    IMAGES, PHOTO, REGISTER, digest, dump, index, local_path, photo_states,
    read, require, round_inputs, save, verify_bytes, write,
)

STAGING = "verification/cache/"
RELEASE_FIELDS = ("setEditionId", "collectorNumber", "cardReleaseId", "edition", "markings", "distribution", "cardSize")
ASSET_NAMESPACE = "https://github.com/m4s-ai/snoredex-data/asset/v1/"


def merge(rows, key, record):
    prior = rows.get(key)
    require(prior is None or prior == record, f"Existing row conflicts: {key}")
    rows[key] = record


def same_number(row, item):
    number, _, denominator = row["number"].partition("/")
    number = number.removeprefix("SWSH") if row["setCode"] == "SWSH" else number
    return (item["collectorNumber"].lstrip("0") == number.lstrip("0") and
            item["collectorNumberDenominator"] == (denominator or None))


def validate_targets(row, ids, targets, items):
    require(ids and len(ids) == len(set(ids)) and set(ids) <= targets.keys(), "Source targets outside the round.")
    require(row["scope"] != "exact-printing" or len(ids) == 1, "An exact source must name one printing.")
    first = items[ids[0]]
    require(row["setEditionId"].split(":")[-1] == row["setCode"], "Source set code mismatch.")
    for key in ids:
        item = items[key]
        require(all(item.get(field) == first.get(field) for field in RELEASE_FIELDS),
                f"One source would cross release, markings or distribution: {key}")
        require(item["setEditionId"] == row["setEditionId"], f"Set edition changed: {key}")
        require(item["setEditionId"].split(":")[-2] == row["language"], f"Source language mismatch: {key}")
        require(same_number(row, item), f"Printed number mismatch: {key}")


def face_width(stage):
    extraction = stage.get("faceExtraction")
    native = stage["source"]["nativeDimensions"]
    if not extraction:
        return native[0]
    corners = extraction["sourceCornersClockwiseTLTRBRBL"]
    require(all(0 <= x < native[0] and 0 <= y < native[1] for x, y in corners), "Crop extends outside the source.")
    width = extraction["outputDimensions"][0]
    limit = min(math.dist(corners[0], corners[1]), math.dist(corners[2], corners[3]))
    require(width <= limit, "Crop width exceeds the width of the photographed face.")
    return width


def prepared_bytes(root, output, prefix, dimensions):
    from PIL import Image

    dest = local_path(root, output["canonicalPath"], prefix)
    staged = local_path(root, output["stagingPath"], STAGING)
    data = (staged if staged.exists() else dest).read_bytes()
    require(digest(data) == output["sha256"], f"Prepared image hash mismatch: {staged.name}")
    import io

    with Image.open(io.BytesIO(data)) as image:
        require(tuple(dimensions) == image.size, f"Prepared image dimensions mismatch: {dest.name}")
        require(image.format == ("WEBP" if prefix == "images/gallery/" else "PNG"),
                f"Unexpected output format: {dest.name}")
        image.verify()
    require(not dest.exists() or dest.read_bytes() == data, f"Existing image has different bytes: {dest.name}")
    return dest, data


def prepare_outputs(root, stage, specimen_id):
    width = face_width(stage)
    renders = stage["galleryRenders"]
    require(width >= 600 and [r["width"] for r in renders] == [240, 480, min(1200, width)],
            f"Invalid native or responsive widths: {specimen_id}")
    files = []
    for output in renders:
        require(output["canonicalPath"] == f"images/gallery/{output['sha256']}.webp", "Non-canonical gallery path.")
        files.append(prepared_bytes(root, output, "images/gallery/", (output["width"], output["height"])))
    preview = stage["preview"]
    require(preview["canonicalPath"] == f"images/previews/{specimen_id}.png", "Non-canonical preview path.")
    require(preview["dimensions"][0] == 360, "Unexpected preview width.")
    files.append(prepared_bytes(root, preview, "images/previews/", preview["dimensions"]))
    return files, [{k: row[k] for k in ("width", "height", "path", "sha256")}
                   for row in [dict(output, path=output["canonicalPath"]) for output in renders]]


def specimen_matches(specimen, row):
    registered = specimen["number"]
    printed = row["number"].split("/")[0]
    return (specimen["language"] == row["language"] and
            registered.lstrip("0") in (row["number"].lstrip("0"), printed.lstrip("0")))


def verify_original_geometry(photos, row, stage):
    from PIL import Image

    source = row["photoRepositoryPath"]
    verify_bytes(photos, source, row["photoRepositorySha256"], PHOTO)
    if row["originalBytesUnchanged"] or row.get("losslessDecode"):
        with Image.open(local_path(photos, source, PHOTO)) as image:
            require(list(image.size) == stage["source"]["nativeDimensions"], f"Native dimensions differ: {source}")


def apply_source(root, row, stage, specimen, items, targets):
    ids = row["itemIds"]
    validate_targets(row, ids, targets, items)
    require(set(stage["targetIds"]) == set(ids), "Preparation and intake refer to different targets.")
    require(specimen_matches(specimen, row),
            f"Specimen language or number mismatch: {row['specimenId']}")
    require({items[key]["sourcePrintingId"] for key in ids} <= set(specimen["citedBy"]),
            "Specimen citations differ from the reviewed targets.")
    require(specimen["photographSha256"] == "sha256:" + row["photoRepositorySha256"]
            and row["photoRepositoryPath"] == PHOTO + specimen["photograph"], "Specimen hash or archive path mismatch.")
    require(stage["scope"] == row["scope"] and stage["mediaKind"] == row["mediaKind"], "Image scope or kind mismatch.")
    require(row["scope"] in ("representative", "exact-printing") and row["mediaKind"] in ("render", "photo"),
            "Unknown image scope or kind.")
    require(row["scope"] != "exact-printing" or row["mediaKind"] == "photo", "Exact scope requires a photograph.")
    require(row["originalSourceSha256"] == stage["source"]["sha256"], "Preparation references a different original.")
    if row["originalBytesUnchanged"]:
        require(row["originalSourceSha256"] == row["photoRepositorySha256"], "An unchanged original has different bytes.")
    return prepare_outputs(root, stage, row["specimenId"])


def gallery_row(row, key, renders):
    return {"itemId": key, "recipe": "intake-" + row["specimenId"].lower(), "mediaKind": row["mediaKind"],
            "scope": row["scope"], "source": row["photoRepositoryPath"], "images": renders}


def asset_row(row, stage, item):
    source = row["photoRepositoryPath"]
    scope = "exact-printing" if row["scope"] == "exact-printing" else "card-release"
    label = f"{row['language']} {item['cardName']} — {row['setCode']} {row['number']}; {scope}"
    return {"assetId": "asset-" + str(uuid.uuid5(uuid.NAMESPACE_URL, ASSET_NAMESPACE + source)),
            "path": source, "sha256": "sha256:" + row["photoRepositorySha256"], "imageScope": scope,
            "altTextBasis": label, "preview": stage["preview"]["canonicalPath"]}


def record_associations(gallery, accepted, row, renders):
    for key in row["itemIds"]:
        merge(gallery, key, gallery_row(row, key, renders))
        require(key not in accepted, f"Target assigned twice: {key}")
        accepted[key] = {"itemId": key, "specimenId": row["specimenId"], "source": row["photoRepositoryPath"],
                         "scope": row["scope"], "mediaKind": row["mediaKind"]}


def allow_reuse(items, gallery, row, photo_path):
    candidates = [g for g in gallery.values() if g["source"] == photo_path]
    target = items[row["itemId"]]
    for candidate in candidates:
        current = items[candidate["itemId"]]
        if current != target and all(current.get(field) == target.get(field) for field in RELEASE_FIELDS):
            return candidate
    raise ValueError(f"No same-release gallery image with matching edition, marks and size: {row['itemId']}")


def existing_association(gallery, accepted, registry, row, items, targets):
    key = row["itemId"]
    require(key in targets and row["scope"] == "representative", "Reuse requires a round target and representative scope.")
    spec = registry[row["specimenId"]]
    require(spec["language"] == items[key]["setEditionId"].split(":")[-2], f"Reused source language mismatch: {key}")
    photo_path = PHOTO + spec["photograph"]
    candidate = allow_reuse(items, gallery, row, photo_path)
    info = dict(row, itemIds=[key], photoRepositoryPath=photo_path, mediaKind=candidate["mediaKind"])
    record_associations(gallery, accepted, info, candidate["images"])
    accepted[key]["reused"] = True


def review_coverage(targets, review, accepted, candidates):
    require(targets.keys() == review.keys(), "Every frozen target needs a reviewed source decision.")
    for key, decision in review.items():
        if key in accepted:
            row = accepted[key]
            require(decision["decision"] in ("selected", "reuse-selected", "gallery-added")
                    and decision["scope"] == row["scope"], f"Review does not authorize assignment: {key}")
            if key in candidates:
                require(decision["candidateId"] == candidates[key], f"Applied source differs from the reviewed candidate: {key}")
            elif "specimenId" in decision:
                require(decision["specimenId"] == row["specimenId"], f"Applied specimen differs from review: {key}")
            continue
        require(decision["decision"] == "needs-image" and decision["reason"].strip(), f"Missing gap reason: {key}")


def ensure_unique_original(registry, sid, specimen):
    for key, prior in registry.items():
        require(key == sid or prior.get("photographSha256") != specimen["photographSha256"],
                f"Identical bytes are already registered as {key}.")


def write_round_outputs(root, folder, number, files, register, registry, images, assets, gallery, accepted):
    for path, data in files:
        save(path, data)
    register.update(count=len(registry), specimens=[registry[key] for key in sorted(registry)])
    write(root / REGISTER, register)
    images.update(assets=[assets[key] for key in sorted(assets)], galleryImages=[gallery[key] for key in sorted(gallery)])
    save(root / IMAGES, dump(images).encode())
    write(folder / "accepted.json", {"round": number, "targets": [accepted[key] for key in sorted(accepted)]})


def apply_round(root, folder, photos):
    number, targets, review, items = round_inputs(root, folder)
    intake = read(folder / "intake.json")
    sources = index(intake["intake"], "specimenId")
    stages = index(read(folder / "preparation.json")["specimens"], "candidateId")
    additions = index(read(folder / "registry-additions.json")["specimens"], "specimenId")
    require(sources.keys() == additions.keys(), "Intake and specimen additions differ.")
    archived = photo_states(photos, list(sources.values()))
    require(all(value == "archived" for value in archived.values()), "Archive originals first and update origin/main.")
    images = read(root / IMAGES)
    register = read(root / REGISTER)
    registry = index(register["specimens"], "specimenId")
    gallery = index(images["galleryImages"], "itemId")
    assets = index(images["assets"], "assetId")
    files, accepted = [], {}
    for sid, row in sources.items():
        stage = stages[row["candidateId"]]
        verify_original_geometry(photos, row, stage)
        outputs, renders = apply_source(root, row, stage, additions[sid], items, targets)
        files.extend(outputs)
        ensure_unique_original(registry, sid, additions[sid])
        merge(registry, sid, additions[sid])
        asset = asset_row(row, stage, items[row["itemIds"][0]])
        merge(assets, asset["assetId"], asset)
        record_associations(gallery, accepted, row, renders)
    for row in intake.get("reusedSpecimens", []):
        existing_association(gallery, accepted, registry, row, items, targets)
    candidates = {key: row["candidateId"] for row in sources.values() for key in row["itemIds"]}
    review_coverage(targets, review, accepted, candidates)
    require(not (targets.keys() & gallery.keys() - accepted.keys()), "A gap already has a gallery image.")
    require(len(accepted) == intake["acceptedAssociationCount"], "Intake count differs from resolved assignments.")
    write_round_outputs(root, folder, number, files, register, registry, images, assets, gallery, accepted)
    print(f"Round {number}: {len(accepted)} gallery assignments, {len(targets) - len(accepted)} documented gaps.")
