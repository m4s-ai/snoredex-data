"""Derive the public archive copy of one inbox job: the photo's own JPEG, metadata cut to two fields.

A DNG gives its embedded full-size preview (the camera's rendering) byte for byte; a JPEG gives
itself. Of the metadata only the orientation tag and the ICC colour profile survive: GPS, XMP,
maker data and any further frame (an HDR gain map) go. The image data is copied, never re-encoded,
and the result must decode pixel-identical to its source.

    python verification/photo_inbox/derive.py <job folder> <SPEC-nnnn.jpg>
"""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct
import sys

from PIL import Image, ImageChops

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from check import carries_location  # noqa: E402  (stdlib-only gate module)

TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8, 12: 8, 13: 4}


def first_ifd(data):
    """IFD0 of a TIFF/DNG as {tag: [values]} for its SHORT and LONG entries."""
    order = {b"II": "<", b"MM": ">"}[data[:2]]
    offset = struct.unpack_from(order + "I", data, 4)[0]
    tags = {}
    for index in range(struct.unpack_from(order + "H", data, offset)[0]):
        tag, kind, count, raw = struct.unpack_from(order + "HHI4s", data, offset + 2 + 12 * index)
        if kind not in (3, 4):
            continue
        where = offset + 10 + 12 * index if TYPE_SIZES[kind] * count <= 4 else struct.unpack(order + "I", raw)[0]
        tags[tag] = list(struct.unpack_from(order + "HI"[kind - 3] * count, data, where))
    return tags


def dng_preview(data):
    """The JPEG stream IFD0 of a DNG stores, byte for byte."""
    tags = first_ifd(data)
    stream = b"".join(data[o:o + n] for o, n in zip(tags.get(273, []), tags.get(279, [])))
    if tags.get(259) != [7] or not stream.startswith(b"\xff\xd8"):
        raise ValueError("this DNG stores no full-size JPEG preview in its first IFD")
    return stream


def orientation(app1_body):
    tiff = app1_body[6:]
    tags = first_ifd(tiff) if tiff[:2] in (b"II", b"MM") else {}
    return tags.get(274, [None])[0]


def orientation_app1(value):
    tiff = b"MM\x00\x2a" + struct.pack(">IH", 8, 1) + struct.pack(">HHIHH", 274, 3, 1, value, 0) + bytes(4)
    return b"\xff\xe1" + struct.pack(">H", len(tiff) + 8) + b"Exif\x00\x00" + tiff


def reduce_metadata(jpeg):
    """Keep the tables, the ICC profile and the first scan; rebuild Exif with orientation only."""
    kept, turn, i = [], None, 2
    while jpeg[i + 1] != 0xDA:
        marker, length = jpeg[i + 1], struct.unpack_from(">H", jpeg, i + 2)[0]
        segment = jpeg[i:i + 2 + length]
        application = 0xE0 <= marker <= 0xEF or marker == 0xFE  # APPn and comments
        if marker == 0xE1 and segment[4:10] == b"Exif\x00\x00":
            turn = orientation(segment[4:])
        elif not application or (marker == 0xE2 and segment[4:16] == b"ICC_PROFILE\x00"):
            kept.append(segment)
        i += 2 + length
    scan = jpeg[i:jpeg.index(b"\xff\xd9", i) + 2]
    return b"\xff\xd8" + (orientation_app1(turn) if turn else b"") + b"".join(kept) + scan


def proven(source, result):
    """Raise unless the result shows the source's pixels, profile and orientation and no location."""
    with Image.open(BytesIO(source)) as before, Image.open(BytesIO(result)) as after:
        before.seek(0)
        same = ImageChops.difference(before.convert("RGB"), after.convert("RGB")).getbbox() is None
        if not same or before.info.get("icc_profile") != after.info.get("icc_profile"):
            raise ValueError("the derived copy does not decode identical to its source")
        if before.getexif().get(274) != after.getexif().get(274):
            raise ValueError("the derived copy lost its orientation")
    if carries_location(result):
        raise ValueError("the derived copy still carries location metadata")


def derive(job):
    photo = next(job.glob("photo.*"))
    data = photo.read_bytes()
    source = dng_preview(data) if photo.suffix == ".dng" else data
    result = reduce_metadata(source)
    proven(source, result)
    with Image.open(BytesIO(result)) as image:
        size, turn = image.size, image.getexif().get(274)
    summary = {"job": job.name, "file": photo.name, "jobSha256": sha256(data).hexdigest(),
               "sourceSha256": sha256(source).hexdigest(), "sha256": sha256(result).hexdigest(),
               "bytes": len(result), "width": size[0], "height": size[1], "orientation": turn}
    return result, summary


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    job, out = Path(sys.argv[1]), Path(sys.argv[2])
    result, summary = derive(job)
    with out.open("xb") as file:
        file.write(result)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
