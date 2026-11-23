#!/usr/bin/env python3
"""Prepare a private Instagram draft from a verified Snoredex specimen."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from gallery_prepare import extract
from card_pages import read_social
from build import ASSET_BASE_URL, printed_number
from check import load
from owner_photo import verified_owner_photo

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "verification/cache/instagram"
POST_SIZE = (1080, 1350)
MONTHS = ("Januar", "Februar", "März", "April", "Mai", "Juni",
          "Juli", "August", "September", "Oktober", "November", "Dezember")
LANGUAGES = {"zh-Hans": "Vereinfachtes Chinesisch", "zh-Hant": "Traditionelles Chinesisch"}
FINISH = {"non-holo": "Non-Holo", "holo": "Holo", "reverse-holo": "Reverse Holo", "mirror-holo": "Mirror Holo"}
PATTERN = {"poke-ball": "Pokéball-Muster", "master-ball": "Meisterball-Muster"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def release_label(item: dict, edition: dict) -> str:
    source = item if item.get("releaseDate") else edition
    date = source.get("releaseDate")
    precision = source.get("releaseDatePrecision")
    if not date or precision not in ("day", "month", "year"):
        return ""
    parts = date.split("-")
    year = parts[0]
    if precision == "year":
        label = year
    elif precision == "month":
        label = f"{MONTHS[int(parts[1]) - 1]} {year}"
    else:
        label = f"{int(parts[2])}. {MONTHS[int(parts[1]) - 1]} {year}"
    return f"ca. {label}" if source.get("releaseApproximate") else label


def caption_facts(model: dict, item: dict) -> tuple[str, str, str, str]:
    sets = model["sets"]
    edition = next(row for row in sets["setEditions"] if row["setEditionId"] == item["setEditionId"])
    local_set = next(row for row in sets["localSets"] if row["localSetId"] == edition["localSetId"])
    locale = next(row for row in sets["localizations"] if row["localizationId"] == edition["localizationId"])
    language = LANGUAGES.get(locale["languageTag"], locale["displayName"])
    name = item.get("localCardName") or item["cardName"]
    if name != item["cardName"]:
        name += f" ({item['cardName']})"
    number = printed_number(item)
    card = " ".join(filter(None, (name, number)))
    finish = FINISH.get(item.get("finish"), "")
    pattern = PATTERN.get(item.get("foilPattern"), "")
    markings = [mark["text"] for mark in item["markings"] if mark.get("text")]
    facts = " · ".join(value for value in (language, item.get("edition"), finish, pattern, *markings)
                       if value and value != "unknown")
    return card, local_set["localSetName"], facts, release_label(item, edition)


def post_copy(model: dict, item: dict, short_url: str | None) -> tuple[str, str]:
    card, set_name, facts, date = caption_facts(model, item)
    lines = [f"{card} · {set_name}", facts]
    if date:
        lines.append(f"Veröffentlicht: {date}")
    lines += ["", "Eigenes Sammlungsfoto für @SnoreDex.", f"Kartendetails: {short_url or '[Kurzlink fehlt]'}"]
    alt = f"Eigene Aufnahme der Vorderseite von {card} aus {set_name}."
    if facts:
        alt += f" Druckvariante: {facts}."
    return "\n".join(lines) + "\n", alt + "\n"


def post_image(data: bytes, corners) -> tuple[bytes, dict]:
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(data)) as image:
        upright = ImageOps.exif_transpose(image)
        rgba = upright.convert("RGBA")
        face = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
        icc = upright.info.get("icc_profile") if upright.mode == "RGB" else None
    face, geometry = extract(face, corners)
    if face.width < 600 or face.width >= face.height:
        raise ValueError("Die vollständige Kartenfront muss hochkant und mindestens 600 Pixel breit sein.")
    face.thumbnail((1000, 1270), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", POST_SIZE, "#f2ede5")
    canvas.paste(face, ((canvas.width - face.width) // 2, (canvas.height - face.height) // 2))
    output = io.BytesIO()
    canvas.save(output, "JPEG", quality=93, icc_profile=icc)
    return output.getvalue(), geometry


def edited_post_image(data: bytes) -> bytes:
    from PIL import Image, ImageCms, ImageOps

    with Image.open(io.BytesIO(data)) as image:
        if image.format != "JPEG":
            raise ValueError("Für das bearbeitete Feed-Foto bitte ein JPEG verwenden.")
        upright = ImageOps.exif_transpose(image)
        if not upright.height > upright.width >= 600:
            raise ValueError("Das bearbeitete Feed-Foto muss hochkant und mindestens 600 Pixel breit sein.")
        profile = upright.info.get("icc_profile")
        if profile:
            srgb = ImageCms.createProfile("sRGB")
            try:
                photo = ImageCms.profileToProfile(upright, io.BytesIO(profile), srgb, outputMode="RGB")
            except (ImageCms.PyCMSError, OSError, ValueError) as error:
                raise ValueError("Das Farbprofil konnte nicht verarbeitet werden. Bitte als sRGB-JPEG exportieren.") from error
        elif upright.mode in ("RGB", "L"):
            photo = upright.convert("RGB")
        else:
            raise ValueError("Bitte das bearbeitete Feed-Foto als sRGB-JPEG exportieren.")

    width, height = POST_SIZE
    if photo.width >= width and photo.height >= height and abs(photo.height - photo.width * height / width) <= 2:
        photo = photo.resize(POST_SIZE, Image.Resampling.LANCZOS)
    else:
        photo.thumbnail(POST_SIZE, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", POST_SIZE, "#171a1c")
    canvas.paste(photo, ((width - photo.width) // 2, (height - photo.height) // 2))
    output = io.BytesIO()
    # The pixels are already sRGB. Omitting the generated ICC profile keeps repeated exports byte-identical.
    canvas.save(output, "JPEG", quality=94, subsampling=0)
    return output.getvalue()


def draft_photo(original: bytes, corners, owner_feed_jpeg: Path | None, feed_alt: str | None) -> tuple[bytes, dict, dict | None]:
    if not owner_feed_jpeg:
        if feed_alt is not None:
            raise ValueError("Ein eigener Feed-Alt-Text gehört zu einem bearbeiteten Feed-Foto.")
        photo, geometry = post_image(original, corners)
        return photo, geometry, None
    if corners or feed_alt is None or not feed_alt.strip():
        raise ValueError("Für das bearbeitete Feed-Foto bitte einen Alt-Text angeben und keine Kartenecken übergeben.")
    feed = owner_feed_jpeg.read_bytes()
    return edited_post_image(feed), {}, {
        "role": "edited feed photo", "sha256": f"sha256:{digest(feed)}",
        "basis": "Owner confirms they took the photo and it shows the exact printing for this SPEC",
    }


def package(model: dict, specimen_id: str, archive: Path, corners=None, *,
            owner_feed_jpeg: Path | None = None, feed_alt: str | None = None) -> tuple[dict, dict]:
    specimen, item, original = verified_owner_photo(model, specimen_id, archive)
    item_id = item["itemId"]
    share = read_social(ROOT).get(item_id)
    alias = share.get("shortAlias") if share and share["specimenId"] == specimen_id else None
    short = f"https://go.m4s.eu/{alias}" if alias else None
    caption, alt = post_copy(model, item, short)
    photo, geometry, feed = draft_photo(original, corners, owner_feed_jpeg, feed_alt)
    if feed_alt is not None:
        alt = feed_alt.strip() + "\n"
    files = {"post.jpg": photo, "caption-draft.txt": caption.encode("utf-8"), "alt-text.txt": alt.encode("utf-8")}
    manifest = {
        "status": "draft", "requiredBeforePosting": ["Owner review"] + (
            [] if short else ["Register a permanent short link for this card"]
        ) + ["Verify the public short link and matching preview"],
        "specimenId": specimen_id, "itemId": item_id, "photoSha256": specimen["photographSha256"],
        "photographedByBasis": specimen["photographedByBasis"], "crop": geometry,
        "dataAsOf": model["printings"]["meta"]["dataAsOf"], "shortUrl": short,
        "targetUrl": f"{ASSET_BASE_URL}cards/{item_id}/" if share else None,
        "files": {name: digest(contents) for name, contents in files.items()},
    }
    if feed is not None:
        manifest["feedPhoto"] = feed
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return files, manifest


def save_package(out: Path, files: dict) -> None:
    if out.exists():
        if all((out / name).is_file() and (out / name).read_bytes() == data for name, data in files.items()):
            return
        raise ValueError("Der Zielordner enthält bereits einen anderen Entwurf. Bitte neuen Ordner wählen.")
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent, ignore_cleanup_errors=True) as temp:
        staged = Path(temp) / "package"
        staged.mkdir()
        for name, data in files.items():
            (staged / name).write_bytes(data)
        staged.rename(out)


def draft_path(out: Path, archive: Path) -> Path:
    out = out.resolve()
    if out.is_relative_to(archive.resolve()) or (out.is_relative_to(ROOT) and not out.is_relative_to(CACHE)):
        raise ValueError("Entwürfe bitte unter verification/cache/instagram oder außerhalb der Checkouts ablegen.")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("specimen", help="registered owner photograph, e.g. SPEC-0774")
    parser.add_argument("--photos", type=Path, required=True, help="local checkout of snoredex-photos")
    parser.add_argument("--out", type=Path, help="new directory for the draft package")
    parser.add_argument("--corners", type=int, nargs=8, metavar="PX",
                        help="four corners after EXIF rotation, clockwise from top left")
    parser.add_argument("--owner-feed-jpeg", type=Path,
                        help="edited JPEG you photographed and confirm shows the exact printing for this SPEC")
    parser.add_argument("--feed-alt", help="alt text describing the actual edited feed photo")
    args = parser.parse_args()
    try:
        corners = list(zip(args.corners[::2], args.corners[1::2])) if args.corners else None
        files, manifest = package(load(), args.specimen, args.photos, corners,
                                  owner_feed_jpeg=args.owner_feed_jpeg, feed_alt=args.feed_alt)
        out = draft_path(args.out or CACHE / args.specimen, args.photos)
        save_package(out, files)
    except (ImportError, OSError, ValueError) as error:
        parser.exit(2, f"Entwurf zurückgestellt: {error}\n")
    print(out)
    for item in manifest["requiredBeforePosting"]:
        print(f"Open: {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
