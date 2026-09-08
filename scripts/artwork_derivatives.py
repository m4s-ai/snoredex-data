#!/usr/bin/env python3
"""Create deterministic, dependency-free artwork preview images.

The repository keeps original evidence bytes untouched.  This module only creates the small
derivative used by the review UI.  PNG decoding is complete for the colour types used by the
specimen archive; baseline JPEGs use their DC samples for a faithful low-frequency preview.  A
new image therefore never depends on a manually run desktop tool or a non-standard Python module.
"""

from __future__ import annotations

import binascii
import hashlib
import math
import struct
import zlib
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
PREVIEW_WIDTH = 360
THUMBNAIL_WIDTH = 120


class ImageError(ValueError):
    """Raised when an image cannot be decoded by the stdlib derivative path."""


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR":
        raise ImageError("not a PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _png_payload(data: bytes) -> tuple[int, int, int, int, list[tuple[int, int, int]], bytes]:
    width, height = _png_dimensions(data)
    bit_depth, colour_type = data[24:26]
    interlace = data[28]
    if interlace or bit_depth not in (8, 16):
        raise ImageError("PNG requires non-interlaced 8/16-bit samples")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(colour_type)
    if channels is None:
        raise ImageError(f"unsupported PNG colour type {colour_type}")
    palette: list[tuple[int, int, int]] = []
    raw_parts: list[bytes] = []
    position = 8
    while position + 12 <= len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        payload = data[position + 8:position + 8 + length]
        position += 12 + length
        if kind == b"PLTE":
            palette = [tuple(payload[index:index + 3]) for index in range(0, len(payload), 3)]
        elif kind == b"IDAT":
            raw_parts.append(payload)
        elif kind == b"IEND":
            break
    decoded = zlib.decompress(b"".join(raw_parts))
    return width, height, bit_depth, colour_type, palette, decoded


def _png_unfilter(decoded: bytes, width: int, height: int, channels: int,
                  bit_depth: int) -> list[bytes]:
    sample_bytes = 2 if bit_depth == 16 else 1
    bytes_per_pixel = channels * sample_bytes
    row_bytes = width * bytes_per_pixel
    if len(decoded) != height * (row_bytes + 1):
        raise ImageError("PNG scanline length does not match dimensions")

    rows: list[bytes] = []
    offset = 0
    previous = bytes(row_bytes)
    for _ in range(height):
        filter_type = decoded[offset]
        encoded = decoded[offset + 1:offset + 1 + row_bytes]
        offset += row_bytes + 1
        row = _png_unfilter_row(encoded, previous, bytes_per_pixel, filter_type)
        rows.append(bytes(row))
        previous = bytes(row)

    return rows


def _png_unfilter_row(encoded: bytes, previous: bytes, bytes_per_pixel: int,
                      filter_type: int) -> bytearray:
    if filter_type not in range(5):
        raise ImageError(f"unsupported PNG filter {filter_type}")
    row = bytearray(len(encoded))
    for index, value in enumerate(encoded):
        left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        above = previous[index]
        upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        predictor = _png_predictor(filter_type, left, above, upper_left)
        row[index] = (value + predictor) & 0xFF
    return row


def _png_predictor(filter_type: int, left: int, above: int, upper_left: int) -> int:
    if filter_type == 0:
        return 0
    if filter_type == 1:
        return left
    if filter_type == 2:
        return above
    if filter_type == 3:
        return (left + above) // 2
    estimate = left + above - upper_left
    distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
    return (left, above, upper_left)[distances.index(min(distances))]


def _png_rgb(rows: list[bytes], width: int, colour_type: int, bit_depth: int,
             channels: int, palette: list[tuple[int, int, int]],
             target_width: int | None = None) -> tuple[int, int, list[tuple[int, int, int]]]:
    sample_bytes = 2 if bit_depth == 16 else 1
    bytes_per_pixel = channels * sample_bytes
    target_width = min(width, target_width) if target_width else width
    target_height = max(1, round(len(rows) * target_width / width))
    pixels: list[tuple[int, int, int]] = []
    for output_y in range(target_height):
        row = rows[min(len(rows) - 1, output_y * len(rows) // target_height)]
        for output_x in range(target_width):
            index = min(width - 1, output_x * width // target_width)
            start = index * bytes_per_pixel
            values = row[start:start + bytes_per_pixel]
            if bit_depth == 16:
                values = values[::2]
            if colour_type == 0:
                pixels.append((values[0], values[0], values[0]))
            elif colour_type == 2:
                pixels.append(tuple(values[:3]))
            elif colour_type == 3:
                pixels.append(palette[values[0]])
            elif colour_type == 4:
                pixels.append((values[0], values[0], values[0]))
            else:
                pixels.append(tuple(values[:3]))
    return target_width, target_height, pixels


def _png_pixels(data: bytes, target_width: int | None = None) -> tuple[int, int, list[tuple[int, int, int]]]:
    width, height, bit_depth, colour_type, palette, decoded = _png_payload(data)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[colour_type]
    rows = _png_unfilter(decoded, width, height, channels, bit_depth)
    return _png_rgb(rows, width, colour_type, bit_depth, channels, palette, target_width)


class _Bits:
    def __init__(self, data: bytes):
        self.data = data
        self.index = 0
        self.bits = 0
        self.count = 0

    def read(self, count: int) -> int:
        while self.count < count:
            if self.index >= len(self.data):
                raise ImageError("JPEG entropy stream ended early")
            byte = self.data[self.index]
            self.index += 1
            if byte == 0xFF:
                if self.index >= len(self.data):
                    raise ImageError("JPEG entropy stream ended after marker")
                marker = self.data[self.index]
                if marker == 0:
                    self.index += 1
                elif marker in range(0xD0, 0xD8):
                    self.bits = 0
                    self.count = 0
                    self.index += 1
                    continue
                else:
                    raise ImageError("unexpected JPEG marker in entropy stream")
            self.bits = (self.bits << 8) | byte
            self.count += 8
        self.count -= count
        value = (self.bits >> self.count) & ((1 << count) - 1)
        self.bits &= (1 << self.count) - 1 if self.count else 0
        return value


def _huffman_table(bits: bytes, values: bytes) -> dict[tuple[int, int], int]:
    table: dict[tuple[int, int], int] = {}
    code = 0
    offset = 0
    for length, count in enumerate(bits, 1):
        for _ in range(count):
            table[(length, code)] = values[offset]
            offset += 1
            code += 1
        code <<= 1
    return table


def _huffman_read(reader: _Bits, table: dict[tuple[int, int], int]) -> int:
    code = 0
    for length in range(1, 17):
        code = (code << 1) | reader.read(1)
        value = table.get((length, code))
        if value is not None:
            return value
    raise ImageError("invalid JPEG Huffman code")


def _receive_extend(reader: _Bits, size: int) -> int:
    if not size:
        return 0
    value = reader.read(size)
    return value if value & (1 << (size - 1)) else value - ((1 << size) - 1)


def _jpeg_quant_tables(payload: bytes, quant: dict[int, list[int]]) -> None:
    cursor = 0
    while cursor < len(payload):
        info = payload[cursor]
        cursor += 1
        precision, table_id = info >> 4, info & 15
        if precision:
            raise ImageError("16-bit JPEG quantization is unsupported")
        quant[table_id] = list(payload[cursor:cursor + 64])
        cursor += 64


def _jpeg_frame(payload: bytes, progressive: bool) -> tuple[int, int, list[dict[str, int]], bool]:
    if payload[0] != 8:
        raise ImageError("JPEG precision is unsupported")
    height, width, count = struct.unpack(">HHB", payload[1:6])
    components = []
    cursor = 6
    for _ in range(count):
        identifier, sampling, table_id = payload[cursor:cursor + 3]
        cursor += 3
        components.append({"id": identifier, "h": sampling >> 4, "v": sampling & 15,
                           "q": table_id, "dc": 0, "ac": 0})
    return width, height, components, progressive


def _jpeg_huffman_tables(payload: bytes, huffman: dict[tuple[int, int], dict[tuple[int, int], int]]) -> None:
    cursor = 0
    while cursor < len(payload):
        info = payload[cursor]
        cursor += 1
        table_class, table_id = info >> 4, info & 15
        bits = payload[cursor:cursor + 16]
        cursor += 16
        total = sum(bits)
        values = payload[cursor:cursor + total]
        cursor += total
        huffman[(table_class, table_id)] = _huffman_table(bits, values)


def _jpeg_scan(payload: bytes, progressive: bool) -> tuple[list[dict[str, int]], int, int, int]:
    count = payload[0]
    cursor = 1
    scan = []
    for _ in range(count):
        identifier, selector = payload[cursor:cursor + 2]
        cursor += 2
        scan.append({"id": identifier, "dc": selector >> 4, "ac": selector & 15})
    spectral_start = spectral_end = approx_low = 0
    if len(payload) >= cursor + 3:
        spectral_start, spectral_end = payload[cursor:cursor + 2]
        approx_low = payload[cursor + 2] & 15
    if progressive and (spectral_start or spectral_end):
        raise ImageError("progressive JPEG AC scans are not preview-decodable")
    return scan, spectral_start, spectral_end, approx_low


def _jpeg_segment(marker: int, payload: bytes, quant: dict[int, list[int]],
                  huffman: dict[tuple[int, int], dict[tuple[int, int], int]],
                  components: list[dict[str, int]], scan: list[dict[str, int]],
                  progressive: bool, spectral_start: int, spectral_end: int,
                  approx_low: int) -> tuple[list[dict[str, int]], list[dict[str, int]], bool,
                                             int, int, int, int, int]:
    width = height = 0
    if marker == 0xDB:
        _jpeg_quant_tables(payload, quant)
    elif marker in (0xC0, 0xC1, 0xC2):
        width, height, components, progressive = _jpeg_frame(payload, marker == 0xC2)
    elif marker == 0xC4:
        _jpeg_huffman_tables(payload, huffman)
    elif marker == 0xDA:
        scan, spectral_start, spectral_end, approx_low = _jpeg_scan(payload, progressive)
    return components, scan, progressive, spectral_start, spectral_end, approx_low, width, height


def _jpeg_read_segment(data: bytes, position: int) -> tuple[int, bytes, int] | None:
    if data[position] != 0xFF:
        return None
    while position < len(data) and data[position] == 0xFF:
        position += 1
    marker = data[position]
    position += 1
    if marker in (0xD8, 0xD9):
        return 0, b"", position
    length = struct.unpack(">H", data[position:position + 2])[0]
    payload = data[position + 2:position + length]
    return marker, payload, position + length


def _jpeg_marker_state(data: bytes) -> tuple[int, int, int, dict[int, list[int]], dict[tuple[int, int], dict[tuple[int, int], int]], list[dict[str, int]], list[dict[str, int]], bool, int, int, int]:
    if not data.startswith(b"\xff\xd8"):
        raise ImageError("not a JPEG")
    quant: dict[int, list[int]] = {}
    huffman: dict[tuple[int, int], dict[tuple[int, int], int]] = {}
    components: list[dict[str, int]] = []
    scan: list[dict[str, int]] = []
    progressive = False
    spectral_start = spectral_end = approx_low = 0
    width = height = 0
    position = 2
    entropy_start = None
    while position + 3 < len(data):
        segment = _jpeg_read_segment(data, position)
        if segment is None:
            position += 1
            continue
        marker, payload, position = segment
        (components, scan, progressive, spectral_start, spectral_end, approx_low,
         segment_width, segment_height) = _jpeg_segment(
             marker, payload, quant, huffman, components, scan, progressive,
             spectral_start, spectral_end, approx_low)
        width = segment_width or width
        height = segment_height or height
        if marker == 0xDA:
            entropy_start = position
            break
    if entropy_start is None or not components or not scan:
        raise ImageError("JPEG has no baseline scan")
    return (width, height, entropy_start, quant, huffman, components, scan, progressive,
            spectral_start, spectral_end, approx_low)


def _jpeg_header(data: bytes) -> tuple[int, int, dict[int, list[int]], dict[tuple[int, int], dict[tuple[int, int], int]], list[dict[str, int]], list[dict[str, int]], bool, int, int, int]:
    (width, height, entropy_start, quant, huffman, components, scan, progressive,
     spectral_start, spectral_end, approx_low) = _jpeg_marker_state(data)
    if len(components) != 3:
        raise ImageError("only three-component JPEGs are supported")
    for component in components:
        selected = next((item for item in scan if item["id"] == component["id"]), {"dc": 0, "ac": 0})
        component.update(dc=selected["dc"], ac=selected["ac"])
    return (width, height, entropy_start, quant, huffman, components, scan, progressive,
            spectral_start, spectral_end, approx_low)


def _jpeg_read_block(reader: _Bits, dc_table: dict[tuple[int, int], int],
                     ac_table: dict[tuple[int, int], int] | None,
                     qtable: list[int], previous: int, progressive: bool,
                     approx_low: int) -> tuple[int, int]:
    size = _huffman_read(reader, dc_table)
    previous += _receive_extend(reader, size) << approx_low
    average = max(0, min(255, 128 + (previous * qtable[0]) // 8))
    if not progressive and ac_table is not None:
        coefficient = 0
        while coefficient < 63:
            symbol = _huffman_read(reader, ac_table)
            if symbol == 0:
                break
            run, bits = symbol >> 4, symbol & 15
            if bits:
                reader.read(bits)
            coefficient += 16 if not bits and run == 15 else run + 1
    return previous, average


def _jpeg_decode_mcu(reader: _Bits, components: list[dict[str, int]], active_ids: set[int],
                     huffman: dict[tuple[int, int], dict[tuple[int, int], int]],
                     quant: dict[int, list[int]], planes: list[tuple[int, int, list[int]]],
                     mcu_x: int, mcu_y: int, previous_dc: list[int], progressive: bool,
                     approx_low: int) -> None:
    for component_index, component in enumerate(components):
        if component["id"] not in active_ids:
            continue
        plane_width, _, plane = planes[component_index]
        dc_table = huffman[(0, component["dc"])]
        ac_table = None if progressive else huffman[(1, component["ac"])]
        for block_y in range(component["v"]):
            for block_x in range(component["h"]):
                previous_dc[component_index], average = _jpeg_read_block(
                    reader, dc_table, ac_table, quant[component["q"]],
                    previous_dc[component_index], progressive, approx_low)
                origin_x = mcu_x * component["h"] + block_x
                origin_y = mcu_y * component["v"] + block_y
                plane[origin_y * plane_width + origin_x] = average


def _jpeg_decode_planes(data: bytes, entropy_start: int, width: int, height: int,
                        quant: dict[int, list[int]],
                        huffman: dict[tuple[int, int], dict[tuple[int, int], int]],
                        components: list[dict[str, int]], scan: list[dict[str, int]],
                        progressive: bool, approx_low: int) -> list[tuple[int, int, list[int]]]:
    active_ids = {item["id"] for item in scan}
    active_components = [component for component in components if component["id"] in active_ids]
    max_h = max(component["h"] for component in active_components)
    max_v = max(component["v"] for component in active_components)
    blocks_x = math.ceil(width / (8 * max_h))
    blocks_y = math.ceil(height / (8 * max_v))
    planes = []
    previous_dc = [0, 0, 0]
    reader = _Bits(data[entropy_start:])
    for component_index, component in enumerate(components):
        plane_width = blocks_x * component["h"]
        plane_height = blocks_y * component["v"]
        planes.append((plane_width, plane_height, [128] * (plane_width * plane_height)))

    for mcu_y in range(blocks_y):
        for mcu_x in range(blocks_x):
            _jpeg_decode_mcu(reader, components, active_ids, huffman, quant, planes,
                             mcu_x, mcu_y, previous_dc, progressive, approx_low)
    return planes


def _jpeg_dc_pixels(data: bytes, target_width: int | None = None) -> tuple[int, int, list[tuple[int, int, int]]]:
    (width, height, entropy_start, quant, huffman, components, scan, progressive,
     _spectral_start, _spectral_end, approx_low) = _jpeg_header(data)
    planes = _jpeg_decode_planes(data, entropy_start, width, height, quant, huffman,
                                 components, scan, progressive, approx_low)

    pixels: list[tuple[int, int, int]] = []
    output_width = min(width, target_width) if target_width else width
    output_height = max(1, round(height * output_width / width))
    for y in range(output_height):
        for x in range(output_width):
            values = []
            for plane_width, plane_height, plane in planes:
                source_x = min(plane_width - 1, x * plane_width // output_width)
                source_y = min(plane_height - 1, y * plane_height // output_height)
                values.append(plane[source_y * plane_width + source_x])
            red = max(0, min(255, round(values[0] + 1.402 * (values[1] - 128))))
            green = max(0, min(255, round(values[0] - 0.344136 * (values[1] - 128) - 0.714136 * (values[2] - 128))))
            blue = max(0, min(255, round(values[0] + 1.772 * (values[2] - 128))))
            pixels.append((red, green, blue))
    return output_width, output_height, pixels


def decode(path: Path, target_width: int | None = None) -> tuple[int, int, list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG"):
        return _png_pixels(data, target_width)
    return _jpeg_dc_pixels(data, target_width)


def resize(width: int, height: int, pixels: list[tuple[int, int, int]], max_width: int) -> tuple[int, int, list[tuple[int, int, int]]]:
    target_width = min(width, max_width)
    target_height = max(1, round(height * target_width / width))
    if target_width == width and target_height == height:
        return width, height, pixels
    result: list[tuple[int, int, int]] = []
    for y in range(target_height):
        source_y = min(height - 1, y * height // target_height)
        for x in range(target_width):
            source_x = min(width - 1, x * width // target_width)
            result.append(pixels[source_y * width + source_x])
    return target_width, target_height, result


def encode_png(width: int, height: int, pixels: Iterable[tuple[int, int, int]]) -> bytes:
    # A deterministic RGB332 palette keeps photographic previews compact without a dependency.
    palette = [(r, g, b) for r in range(0, 256, 51) for g in range(0, 256, 43) for b in range(0, 256, 85)]
    palette_bytes = b"".join(bytes(item) for item in palette)
    indexed = bytearray()
    for red, green, blue in pixels:
        red_index = min(5, red * 6 // 256)
        green_index = min(5, green * 6 // 256)
        blue_index = min(3, blue * 4 // 256)
        indexed.append((red_index * 24) + (green_index * 4) + blue_index)
    rows = b"".join(b"\x00" + bytes(indexed[row * width:(row + 1) * width]) for row in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"PLTE", palette_bytes) + _chunk(b"IDAT", zlib.compress(rows, 9)) + _chunk(b"IEND", b"")


def derivative_path(source: Path, kind: str) -> Path:
    root = ROOT / "images" / ("previews" if kind == "preview" else "thumbs")
    return root / f"{source.stem}.png"


def ensure_derivative(source: Path, kind: str) -> Path:
    root = ROOT / "images" / ("previews" if kind == "preview" else "thumbs")
    for suffix in (".jpg", ".png"):
        existing = root / f"{source.stem}{suffix}"
        if existing.is_file():
            return existing
    destination = derivative_path(source, kind)
    target = PREVIEW_WIDTH if kind == "preview" else THUMBNAIL_WIDTH
    width, height, pixels = decode(source, target)
    width, height, pixels = resize(width, height, pixels, target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(encode_png(width, height, pixels))
    return destination


def ensure_for_sources(sources: Iterable[Path]) -> None:
    for source in sorted(set(sources), key=lambda item: str(item)):
        if not source.is_file():
            continue
        preview = derivative_path(source, "preview")
        thumbnail = derivative_path(source, "thumbnail")
        preview_exists = any((preview.with_suffix(suffix)).is_file() for suffix in (".jpg", ".png"))
        thumbnail_exists = any((thumbnail.with_suffix(suffix)).is_file() for suffix in (".jpg", ".png"))
        if preview_exists and thumbnail_exists:
            continue
        width, height, pixels = decode(source, PREVIEW_WIDTH)
        if not preview_exists:
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview.write_bytes(encode_png(width, height, pixels))
        if not thumbnail_exists:
            thumb_width, thumb_height, thumb_pixels = resize(width, height, pixels, THUMBNAIL_WIDTH)
            thumbnail.parent.mkdir(parents=True, exist_ok=True)
            thumbnail.write_bytes(encode_png(thumb_width, thumb_height, thumb_pixels))


__all__ = ["ImageError", "ensure_for_sources", "ensure_derivative", "decode", "derivative_path"]
