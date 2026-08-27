"""Admit the 47 retained Japanese card images requested by issue #259 as specimens."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "verification" / "units.json"
CARDS = ROOT / "snorlax_cards.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SPECIMEN_DIR = ROOT / "verification" / "specimens"


UNIT_IDS = (
    "U0626", "U0412", "U0632", "U0556", "U0504", "U0427", "U0679", "U0575",
    "U0578", "U0439", "U0605", "U0458", "U0643", "U0585", "U0544", "U0380",
    "U0522", "U0343", "U0167", "U0201", "U0531", "U0290", "U0600", "U0172",
    "U0609", "U0640", "U0652", "U0656", "U0582", "U0769", "U0305", "U0465",
    "U0647", "U0660", "U0663", "U0540", "U0560", "U0401", "U0378", "U0476",
    "U0636", "U0751", "U0622", "U0510", "U0547", "U0286", "U0507",
)


# Only treatments visible in the retained card image are admitted. A flat-looking
# scan is not enough to assert non-holo, and no missing treatment is evidence.
FINISH_OBSERVATIONS: dict[str, tuple[str, str | None, str]] = {
    "U0439": ("holo", "speckled full-face", "Dense reflective speckling is visible across the border and card face."),
    "U0636": ("holo", "sparkle", "Reflective points are visible throughout the artwork window."),
    "U0622": ("holo", "sparkle", "Multicolour reflective points are visible throughout the artwork window."),
    "U0544": ("holo", None, "A reflective sheen is visible across the artwork window of the Holo Rare card."),
    "U0380": ("holo", "cosmos", "Large stars and reflective circles are visible throughout the artwork window."),
    "U0343": ("holo", "vertical-line", "Vertical rainbow foil lines are visible across the artwork window."),
    "U0167": ("holo", "full-art", "Reflective colour bands and texture are visible across the full-art card face."),
    "U0201": ("holo", "vertical-line", "Vertical rainbow foil lines are visible across the artwork window."),
    "U0510": ("holo", "full-art", "Reflective bands are visible across the Pokémon V card face."),
    "U0286": ("holo", "full-art", "Reflective sparkles and colour bands are visible across the Pokémon VMAX card face."),
    "U0547": ("holo", "textured full-art", "Diagonal texture and reflective colour are visible across the full-art Pokémon V card."),
    "U0507": ("holo", "rainbow textured", "The rainbow colour field and reflective texture are visible across the full card face."),
    "U0290": ("holo", "vertical-line", "Vertical rainbow foil lines are visible in the artwork window."),
    "U0600": ("holo", "gold textured", "Gold foil, texture and reflective stars are visible across the secret-rare card face."),
    "U0378": ("holo", "full-art", "Reflective rays and colour bands are visible across the Snorlax-GX card face."),
    "U0626": ("holo", "full-art", "Reflective colour bands are visible across the Eevee & Snorlax-GX promo face."),
    "U0412": ("holo", "full-art", "Reflective rays and colour bands are visible across the TAG TEAM GX card face."),
    "U0632": ("holo", "textured full-art", "Reflective geometric texture is visible across the full-art TAG TEAM GX card."),
    "U0556": ("holo", "rainbow textured", "The rainbow colour field and reflective texture are visible across the TAG TEAM GX card."),
    "U0769": ("holo", "diagonal rainbow", "Broad diagonal rainbow foil bands are visible across the lower card face."),
    "U0401": ("holo", "full-art", "Reflective streaks and sparkles are visible across the Snorlax ex card face."),
    "U0504": ("holo", "speckled", "Dense multicolour reflective speckles are visible in the artwork window."),
    "U0663": ("holo", "speckled", "Dense reflective speckles are visible throughout the artwork window."),
}


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encoded(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def variant_token(unit: dict[str, Any]) -> str:
    return str(unit.get("variant") or "base")


def specimen_rows() -> list[tuple[dict[str, Any], Path, bytes]]:
    units = {row["unitId"]: row for row in read(UNITS)}
    cards = {row["imageFile"]: row for row in read(CARDS)["cards"]}
    missing = sorted(set(UNIT_IDS) - set(units))
    if missing:
        raise ValueError(f"issue #259 units are missing: {missing}")

    result = []
    for index, unit_id in enumerate(UNIT_IDS, start=189):
        unit = units[unit_id]
        image_file = str(unit["image"])
        card = cards.get(image_file)
        if card is None:
            raise ValueError(f"{unit_id} has no retained Cardmarket product image record")
        source_path = ROOT / image_file
        blob = source_path.read_bytes()
        extension = source_path.suffix.lower()
        specimen_id = f"SPEC-{index:04d}"
        number = str(unit.get("number") or "")
        printed_identity = f"{unit['setCode']} {number}".strip()
        observed = (
            f"Complete retained Cardmarket catalogue scan for Japanese {unit['cardName']} "
            f"{printed_identity or 'unnumbered card'} ({variant_token(unit)}). Japanese text, artwork, "
            "set identity and the visible collector identity establish this exact card. The scan is "
            "positive evidence for the pictured card only; it is not a complete product or finish manifest."
        )
        row: dict[str, Any] = {
            "specimenId": specimen_id,
            "setCode": unit["setCode"],
            "number": number,
            "variant": variant_token(unit),
            "language": "Japanese",
            "heldBy": "marketplace catalogue",
            "inspectedFrom": "retained Cardmarket product scan",
            "photograph": specimen_id + extension,
            "photographSource": card["imageUrl"],
            "photographSha256": "sha256:" + hashlib.sha256(blob).hexdigest(),
            "observed": observed,
            "recordedAt": "2026-08-28",
            "citedBy": [unit_id],
            "listingUrl": card["productUrl"],
        }
        finish = FINISH_OBSERVATIONS.get(unit_id)
        if finish:
            finish_name, foil_pattern, basis = finish
            row["observed"] += " " + basis
            row["physicalObservation"] = {
                "finish": finish_name,
                "foilPattern": foil_pattern,
                "markings": None,
                "markingRole": None,
                "cardSize": "standard",
                "basis": basis,
            }
        result.append((row, SPECIMEN_DIR / row["photograph"], blob))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rows = specimen_rows()
    document = read(SPECIMENS)
    before = encoded(document)
    by_id = {row["specimenId"]: row for row in document["specimens"]}
    by_id.update({row["specimenId"]: row for row, _, _ in rows})
    document["specimens"] = sorted(
        by_id.values(), key=lambda row: int(row["specimenId"].split("-")[1])
    )

    stale_images = [
        row["specimenId"]
        for row, destination, blob in rows
        if not destination.is_file() or destination.read_bytes() != blob
    ]
    if args.check:
        if before != encoded(document) or stale_images:
            raise SystemExit(
                "issue #259 Japanese specimens are stale: "
                + ", ".join(stale_images or ["manifest"])
            )
        print("issue #259 Japanese specimen inputs are current")
        return 0

    SPECIMENS.write_text(encoded(document), encoding="utf-8", newline="\n")
    for _, destination, blob in rows:
        destination.write_bytes(blob)
    print(
        f"admitted {len(rows)} Japanese image specimens with "
        f"{len(FINISH_OBSERVATIONS)} visible positive finish observations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
