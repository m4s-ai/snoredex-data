
"""Create reproducible gallery and preview files from an inspected local original."""
from __future__ import annotations

import io
import math
from pathlib import Path

from gallery_workflow import REGISTER, digest, local_path, read, read_optional, require, save, write


def coefficients(corners, size):
    w, h = size
    rows = []
    for (x, y), (u, v) in zip(((0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1)), corners):
        rows.extend(([x, y, 1, 0, 0, 0, -u*x, -u*y, u],
                     [0, 0, 0, x, y, 1, -v*x, -v*y, v]))
    for j in range(8):
        pivot = max(range(j, 8), key=lambda k: abs(rows[k][j]))
        rows[j], rows[pivot] = rows[pivot], rows[j]
        require(abs(rows[j][j]) > 1e-9, "Degenerate card corners.")
        rows[j] = [a / rows[j][j] for a in rows[j]]
        for k in set(range(8)) - {j}:
            rows[k] = [a - rows[k][j]*b for a, b in zip(rows[k], rows[j])]
    return [row[-1] for row in rows]


def extract(image, corners):
    from PIL import Image

    if not corners:
        return image, {}
    require(all(0 <= x < image.width and 0 <= y < image.height for x, y in corners),
            "Card corners fall outside the image.")
    top_left, top_right, bottom_right, bottom_left = corners
    width = math.floor(min(math.dist(top_left, top_right), math.dist(bottom_left, bottom_right)))
    height = math.floor(min(math.dist(top_left, bottom_left), math.dist(top_right, bottom_right)))
    require(width >= 600 and height > width, "Insufficient or invalid native card dimensions.")
    options = coefficients(corners, (width, height))
    face = image.transform((width, height), Image.Transform.PERSPECTIVE, options, Image.Resampling.BICUBIC)
    return face, {"sourceCornersClockwiseTLTRBRBL": corners, "outputDimensions": [width, height],
                  "outputToSourceHomographyCoefficients": options, "faceRGBPixelSha256": digest(face.tobytes())}


def resize(face, width):
    from PIL import Image

    return face.resize((width, round(face.height * width / face.width)), Image.Resampling.LANCZOS)


# one encoder for the card face, used by the gallery workflow and the inbox intake alike (#680): the same
# face gives the same bytes on the same package versions, whichever way it came
WEBP_OPTIONS = {"quality": 90, "method": 6}
PREVIEW_WIDTH = 360


def encode(image, fmt, **options):
    buffer = io.BytesIO()
    image.save(buffer, fmt, **options)
    return buffer.getvalue(), image.size


def webp_renditions(face):
    """The gallery's WebP renditions of an upright card face: 240 and 480 px wide and the face's own width
    up to 1200 px, each as (bytes, size)."""
    return [encode(resize(face, width), "WEBP", **WEBP_OPTIONS) for width in (240, 480, min(1200, face.width))]


def png_preview(face, icc):
    """The 360 px PNG preview of an upright card face: 256 colours by median cut with Floyd-Steinberg
    dithering, optimised, carrying the source's ICC profile; as (bytes, size)."""
    from PIL import Image

    thumb = resize(face, PREVIEW_WIDTH).quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                                                 dither=Image.Dither.FLOYDSTEINBERG)
    return encode(thumb, "PNG", optimize=True, icc_profile=icc)


def output(root, stage, name, data, size):
    sha = digest(data)
    target = name or f"images/gallery/{sha}.webp"
    path = stage / target
    save(path, data)
    return {"canonicalPath": target, "stagingPath": path.relative_to(root).as_posix(), "sha256": sha,
            "width": size[0], "height": size[1], "dimensions": list(size)}


def preview_output(root, stage, row, face, icc):
    from PIL import Image

    specimen = row["specimenId"]
    target = f"images/previews/{specimen}.png"
    existing = local_path(root, target, "images/previews/")
    if existing.is_file():
        registry = read(root / REGISTER)["specimens"]
        require(any(spec["specimenId"] == specimen and
                    spec.get("photographSha256") == "sha256:" + row["photoRepositorySha256"]
                    for spec in registry), f"Existing preview belongs to another original: {specimen}")
        data = existing.read_bytes()
        with Image.open(io.BytesIO(data)) as image:
            dimensions = list(image.size)
            require(image.format == "PNG" and image.width == PREVIEW_WIDTH, f"Invalid retained preview: {specimen}")
        staged = stage / target
        save(staged, data)
        return {"canonicalPath": target, "stagingPath": staged.relative_to(root).as_posix(),
                "sha256": digest(data), "width": dimensions[0], "height": dimensions[1], "dimensions": dimensions}
    return output(root, stage, target, *png_preview(face, icc))


def render(root, folder, candidate, specimen, photo, corners):
    from PIL import Image

    plan = read(folder / "intake.json")
    row = next(entry for entry in plan["intake"] if entry["candidateId"] == candidate)
    require(row["specimenId"] == specimen, "Specimen ID differs from the intake plan.")
    manifest_path = folder / "preparation.json"
    manifest = read_optional(manifest_path, {"round": plan["round"], "specimens": []})
    stage = local_path(root, f"verification/cache/gallery-workflow/{plan['round']}/{specimen}", "verification/cache/")
    data = photo.read_bytes()
    require(digest(data) == row["originalSourceSha256"], "Input bytes differ from the reviewed original.")
    with Image.open(io.BytesIO(data)) as image:
        require(image.getexif().get(274, 1) == 1, "Use an upright source for its recorded pixel coordinates.")
        rgba = image.convert("RGBA")
        rgb = Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB")
        face, geometry = extract(rgb, corners)
        icc = image.info.get("icc_profile")
        source = {"sha256": digest(data), "nativeDimensions": list(image.size),
                  "rgbPixelReconstructionSha256": digest(rgb.tobytes()), "imageUrl": row["sourceUrl"]}
    require(face.width >= 600, "The native face must be at least 600 pixels wide.")
    renders = [output(root, stage, None, data, size) for data, size in webp_renditions(face)]
    preview = preview_output(root, stage, row, face, icc)
    record = {"candidateId": candidate, "targetIds": row["itemIds"], "source": source, "scope": row["scope"],
              "mediaKind": row["mediaKind"], "galleryRenders": renders, "preview": preview,
              "faceExtraction": geometry}
    other = [entry for entry in manifest["specimens"] if entry["candidateId"] != candidate]
    manifest["specimens"] = other + [record]
    write(manifest_path, manifest)
    row.update(previewPath=preview["canonicalPath"], previewSha256=preview["sha256"])
    write(folder / "intake.json", plan)
    print("Prepared three WebP renditions and one PNG preview. Inspect the final card face before applying.")
