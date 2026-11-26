#!/usr/bin/env python3
"""Prepare a private Instagram draft from a verified Snoredex specimen."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import unicodedata

from gallery_prepare import coefficients, extract
from card_pages import read_social
from build import ASSET_BASE_URL, printed_number
from check import load
from owner_photo import verified_owner_photo

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "verification/cache/instagram"
POST_SIZE = (1080, 1350)
# The @SnoreDex account is kept in English (owner decision, 2026-11-23).
MONTHS = ("January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December")
FINISH = {"non-holo": "Non-Holo", "holo": "Holo", "reverse-holo": "Reverse Holo", "mirror-holo": "Mirror Holo"}
PATTERN = {"poke-ball": "Poké Ball pattern", "master-ball": "Master Ball pattern",
           "colorless-energy-star": "Colorless Energy pattern"}
CANVAS = "#0d0f10"
# The wall around the card is darkened, not blacked out (#691): to 60 % of its brightness beside the
# card and 40 % at the frame's edge, so even a dark wall and the stand stay visible.
DARKEN = (0.6, 0.4)
WATERMARK = "@SnoreDex"
# Instagram takes at most five hashtags per post (Help Center, 2026); they label, they do not reach
HASHTAGS = ("#Snorlax", "#PokemonTCG", "#PokemonCards")
SPECIES = ("カビゴン", "卡比兽", "卡比獸", "잠만보", "Relaxo", "Ronflex", "คาบิกอน", "Снорлакс")


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
        label = f"{int(parts[2])} {MONTHS[int(parts[1]) - 1]} {year}"
    return f"c. {label}" if source.get("releaseApproximate") else label


def caption_facts(model: dict, item: dict) -> tuple[str, str, str, str]:
    sets = model["sets"]
    edition = next(row for row in sets["setEditions"] if row["setEditionId"] == item["setEditionId"])
    local_set = next(row for row in sets["localSets"] if row["localSetId"] == edition["localSetId"])
    locale = next(row for row in sets["localizations"] if row["localizationId"] == edition["localizationId"])
    language = locale["displayName"]
    # a localized name joins Snorlax, it never replaces it
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


def hashtags(item: dict, set_name: str) -> str:
    """Three fixed tags, then the local name of Snorlax, the set and a reverse holo, five at most."""
    local = item.get("localCardName") or ""
    tags = [*HASHTAGS, *(f"#{name}" for name in SPECIES if name in local)][:4]
    plain = unicodedata.normalize("NFKD", set_name).encode("ascii", "ignore").decode()  # Pokémon -> Pokemon
    set_tag = "".join(word[:1].upper() + word[1:] for word in re.findall(r"[0-9A-Za-z]+", plain))
    if set_tag and len(set_tag) <= 24 and len(plain) >= len(set_name) - 2:
        tags.append(f"#{set_tag}")
    if item.get("finish") == "reverse-holo":
        tags.append("#ReverseHolo")
    return " ".join(tags[:5])


def post_copy(model: dict, item: dict, short_url: str | None) -> tuple[str, str]:
    card, set_name, facts, date = caption_facts(model, item)
    lines = [f"{card} · {set_name}", facts]
    if date:
        lines.append(f"Released: {date}")
    lines += ["", "Own collection photo for @SnoreDex.", f"Card details: {short_url or '[short link missing]'}",
              "", hashtags(item, set_name)]
    alt = f"Own photo of {card} from {set_name}."
    if facts:
        alt += f" Print variant: {facts}."
    return "\n".join(lines) + "\n", alt + "\n"


def watermark(image):
    """@SnoreDex in the bottom right corner, white at three quarters opacity."""
    from PIL import Image, ImageDraw, ImageFont

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).text((image.width - 40, image.height - 36), WATERMARK, anchor="rs",
                                 font=ImageFont.load_default(size=34), fill=(255, 255, 255, 190))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def card_to_photo(corners, size) -> list[float]:
    """Perspective coefficients mapping photo pixels into card space (the inverse of extract's)."""
    a, b, c, d, e, f, g, h = coefficients(corners, size)
    m = ((a, b, c), (d, e, f), (g, h, 1.0))
    adj = [[m[(j + 1) % 3][(i + 1) % 3] * m[(j + 2) % 3][(i + 2) % 3]
            - m[(j + 1) % 3][(i + 2) % 3] * m[(j + 2) % 3][(i + 1) % 3] for j in range(3)] for i in range(3)]
    return [value / adj[2][2] for row in adj for value in row][:8]


def card_mask(photo_size, corners, card_size):
    """The card face with its rounded corners, as a feathered mask over the photo."""
    from PIL import Image, ImageDraw, ImageFilter

    shape = Image.new("L", card_size, 0)
    ImageDraw.Draw(shape).rounded_rectangle((0, 0, card_size[0] - 1, card_size[1] - 1),
                                            radius=round(card_size[0] * 0.045), fill=255)
    mask = shape.transform(photo_size, Image.Transform.PERSPECTIVE, card_to_photo(corners, card_size),
                           Image.Resampling.BILINEAR)
    return mask.filter(ImageFilter.GaussianBlur(2))


def frame(photo_size, corners) -> tuple[int, int, int, int]:
    """A 4:5 window with the card at about 60 % width, nudged down to keep its stand in view."""
    xs, ys = [x for x, _ in corners], [y for _, y in corners]
    unit = int(min(photo_size[0] / 4, photo_size[1] / 5, (max(xs) - min(xs)) / 0.6 / 4))
    width, height = 4 * unit, 5 * unit
    centre_x = (min(xs) + max(xs)) / 2
    centre_y = (min(ys) + max(ys)) / 2 + 0.1 * (max(ys) - min(ys))
    left = min(max(0, round(centre_x - width / 2)), photo_size[0] - width)
    top = min(max(0, round(centre_y - height / 2)), photo_size[1] - height)
    return left, top, left + width, top + height


def dark_cover(photo, corners):
    """Darken everything but the card, in a vignette that keeps it visible; the card's own pixels stay
    untouched."""
    from PIL import Image, ImageChops

    face, geometry = extract(photo, corners)
    box = frame(photo.size, corners)
    window = photo.crop(box)
    mask = card_mask(photo.size, corners, face.size).crop(box)
    fade = Image.radial_gradient("L").resize(window.size)
    centre, edge = DARKEN
    factor = fade.point(lambda v: round(255 * (centre - (centre - edge) * v / 255)))
    dark = ImageChops.multiply(window, Image.merge("RGB", (factor,) * 3))
    return Image.composite(window, dark, mask), dict(geometry, frame=list(box))


def post_image(data: bytes, corners) -> tuple[bytes, dict]:
    """The cover: with card corners the darkened photo around the card, else the whole photo."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(data)) as image:
        upright = ImageOps.exif_transpose(image)
        rgba = upright.convert("RGBA")
        photo = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
        icc = upright.info.get("icc_profile") if upright.mode == "RGB" else None
    picture, geometry = dark_cover(photo, corners) if corners else (photo, {})
    picture.thumbnail(POST_SIZE, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", POST_SIZE, CANVAS)
    canvas.paste(picture, ((canvas.width - picture.width) // 2, (canvas.height - picture.height) // 2))
    output = io.BytesIO()
    watermark(canvas).save(output, "JPEG", quality=93, icc_profile=icc)
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
    watermark(canvas).save(output, "JPEG", quality=94, subsampling=0)
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


def shared(item_id: str, specimen_id: str):
    """The item's social row, its short URL, the approved cover's corners and the further carousel
    photos, when that row names this SPEC. They are kept with the share, so every machine builds the
    same draft (#646)."""
    share = read_social(ROOT).get(item_id)
    own = share if share and share["specimenId"] == specimen_id else {}
    alias = own.get("shortAlias")
    return (share, (f"https://go.m4s.eu/{alias}" if alias else None), corner_pairs(own.get("postCorners")),
            own.get("carousel", []))


def corner_pairs(corners):
    return [tuple(pair) for pair in corners] if corners else None


def carousel_files(model: dict, item_id: str, slides: list, archive: Path) -> dict:
    """The further carousel images (post-2.jpg, ...): each another own photo of the same printing,
    with its own alt text, in the order data/social.json gives (#646)."""
    files = {}
    for number, slide in enumerate(slides, start=2):
        _, item, original = verified_owner_photo(model, slide["specimenId"], archive)
        if item["itemId"] != item_id:
            raise ValueError(f"{slide['specimenId']}: shows another printing than the cover")
        files[f"post-{number}.jpg"] = post_image(original, corner_pairs(slide.get("postCorners")))[0]
        files[f"alt-text-{number}.txt"] = (slide["altText"].strip() + "\n").encode("utf-8")
    return files


def package(model: dict, specimen_id: str, archive: Path, corners=None, *,
            owner_feed_jpeg: Path | None = None, feed_alt: str | None = None) -> tuple[dict, dict]:
    specimen, item, original = verified_owner_photo(model, specimen_id, archive)
    item_id = item["itemId"]
    share, short, stored, slides = shared(item_id, specimen_id)
    if corners is None and owner_feed_jpeg is None:
        corners = stored
    caption, alt = post_copy(model, item, short)
    photo, geometry, feed = draft_photo(original, corners, owner_feed_jpeg, feed_alt)
    if feed_alt is not None:
        alt = feed_alt.strip() + "\n"
    files = {"post.jpg": photo, "caption-draft.txt": caption.encode("utf-8"), "alt-text.txt": alt.encode("utf-8")}
    if owner_feed_jpeg is None:
        files.update(carousel_files(model, item_id, slides, archive))
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
