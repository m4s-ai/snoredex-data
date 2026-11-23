"""Read the first IFD of a DNG and its embedded full-size JPEG preview (standard library only)."""

import struct

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
