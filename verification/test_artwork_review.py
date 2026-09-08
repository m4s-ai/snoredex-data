#!/usr/bin/env python3
"""Regression checks for the generated #120 artwork review projection."""

from __future__ import annotations

import base64
import hashlib
import json
import struct
import sys
import tempfile
import zlib
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import artwork_review  # noqa: E402
import artwork_derivatives  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"[FAIL] artwork review: {message}")


def image_dimensions(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    if raw.startswith(b"\x89PNG\r\n\x1a\n") and len(raw) >= 24:
        return int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
    if raw[:2] != b"\xff\xd8":
        fail(f"unsupported derivative image format: {path}")
    offset = 2
    while offset + 9 < len(raw):
        if raw[offset] != 0xFF:
            offset += 1
            continue
        marker = raw[offset + 1]
        offset += 2
        if marker in (0xD8, 0xD9):
            continue
        if offset + 2 > len(raw):
            break
        length = int.from_bytes(raw[offset:offset + 2], "big")
        if marker in set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) | set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0)):
            if offset + 7 > len(raw):
                break
            return int.from_bytes(raw[offset + 5:offset + 7], "big"), int.from_bytes(raw[offset + 3:offset + 5], "big")
        offset += max(length, 2)
    fail(f"could not read JPEG dimensions: {path}")


def png_fixture(width: int, height: int, bit_depth: int, colour_type: int,
                interlace: int, scanlines: bytes, palette: bytes = b"") -> bytes:
    header = struct.pack(">IIBBBBB", width, height, bit_depth, colour_type, 0, 0, interlace)
    chunks = [artwork_derivatives._chunk(b"IHDR", header)]
    if palette:
        chunks.append(artwork_derivatives._chunk(b"PLTE", palette))
    chunks.extend((artwork_derivatives._chunk(b"IDAT", zlib.compress(scanlines, 9)),
                   artwork_derivatives._chunk(b"IEND", b"")))
    return b"\x89PNG\r\n\x1a\n" + b"".join(chunks)


def verify_png_formats() -> None:
    """Cover the valid PNG forms accepted by the specimen importer."""
    grayscale = png_fixture(2, 2, 1, 0, 0, b"\x00\x40\x00\x80")
    width, height, pixels = artwork_derivatives._png_pixels(grayscale)
    if (width, height) != (2, 2) or pixels != [(0, 0, 0), (255, 255, 255),
                                                (255, 255, 255), (0, 0, 0)]:
        fail(f"1-bit grayscale PNG decoded incorrectly: {(width, height, pixels)}")

    indexed = png_fixture(2, 1, 4, 3, 0, b"\x00\x01",
                          bytes((255, 0, 0, 0, 255, 0)))
    width, height, pixels = artwork_derivatives._png_pixels(indexed)
    if (width, height, pixels) != (2, 1, [(255, 0, 0), (0, 255, 0)]):
        fail(f"4-bit indexed PNG decoded incorrectly: {(width, height, pixels)}")

    adam7 = png_fixture(
        2, 2, 8, 2, 1,
        b"\x00\xff\x00\x00"  # pass 1: red at (0, 0)
        b"\x00\x00\xff\x00"  # pass 6: green at (1, 0)
        b"\x00\x00\x00\xff\xff\xff\xff"  # pass 7: blue, white at y=1
    )
    width, height, pixels = artwork_derivatives._png_pixels(adam7)
    if (width, height, pixels) != (2, 2, [(255, 0, 0), (0, 255, 0),
                                         (0, 0, 255), (255, 255, 255)]):
        fail(f"Adam7 PNG decoded incorrectly: {(width, height, pixels)}")


def verify_derivative_writer() -> None:
    """Exercise source replacement, progressive JPEG decoding, and RGB channel order."""
    verify_png_formats()
    for relative in ("images/151C_143_Snorlax_V1_819209.jpg",
                     "images/TEU_171_Eevee___Snorlax_GX_V2_369096.jpg",
                     "images/TEU_191_Eevee___Snorlax_GX_V3_369116.jpg",
                     "images/EXS__Snorlax_548656.jpg",
                     "images/s5a_93_Snorlax_552704.jpg",
                     "images/xJTG_117_Hop_s_Snorlax_V2_817770.jpg"):
        width, height, pixels = artwork_derivatives.decode(ROOT / relative, 64)
        if width <= 0 or height <= 0 or not pixels:
            fail(f"progressive JPEG did not produce preview pixels: {relative}")
        if len(set(pixels)) < 2:
            fail(f"JPEG preview unexpectedly contains one flat color: {relative}")

    # A grayscale JPEG has one component.  Keep the decoder's component handling covered even
    # though the repository's retained photographs are all RGB or YCbCr sources.
    grayscale = base64.b64decode(
        "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMU"
        "FRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQU"
        "FBQUFBQUFBQUFBT/wAALCAABAAIBASIA/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9"
        "AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNk"
        "ZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo"
        "6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSEx"
        "BhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0"
        "dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3"
        "+Pn6/9oACAEBAAA/APv79k7/AJNY+Df/AGJmjf8ApDDRRRQH/9k=")
    if len(artwork_derivatives._jpeg_header(grayscale)[4]) != 1:
        fail("grayscale JPEG fixture was not parsed as one component")
    width, height, pixels = artwork_derivatives._jpeg_dc_pixels(grayscale)
    if (width, height) != (2, 1) or len(set(pixels)) != 1 or any(len(set(pixel)) != 1 for pixel in pixels):
        fail(f"grayscale JPEG was not expanded to equal RGB channels: {(width, height, pixels)}")

    # Adobe APP14 transform 0 with explicit RGB component identifiers must bypass YCbCr math.
    source_rgb = (ROOT / "images" / "s5a_93_Snorlax_552704.jpg").read_bytes()
    adobe_app14 = b"\xff\xee\x00\x0eAdobe\x00\x64\x00\x00\x00\x00"
    direct_rgb = bytearray(source_rgb[:2] + adobe_app14 + source_rgb[2:])
    offset = 2
    while offset + 9 < len(direct_rgb):
        if direct_rgb[offset] != 0xFF:
            offset += 1
            continue
        marker = direct_rgb[offset + 1]
        if marker == 0xEE:
            length = int.from_bytes(direct_rgb[offset + 2:offset + 4], "big")
            payload = offset + 4
            if direct_rgb[payload:payload + 5] == b"Adobe" and length >= 14:
                direct_rgb[payload + 11] = 0
        elif marker in (0xC0, 0xC1, 0xC2):
            payload = offset + 4
            if direct_rgb[payload + 5] == 3:
                direct_rgb[payload + 6:payload + 9] = b"RGB"
        if marker in (0xD8, 0xD9) or marker in range(0xD0, 0xD8) or marker == 0x01:
            offset += 2
        else:
            offset += 2 + int.from_bytes(direct_rgb[offset + 2:offset + 4], "big")
    direct_header = artwork_derivatives._jpeg_header(bytes(direct_rgb))
    if [component.get("rgb_channel") for component in direct_header[4]] != [0, 1, 2]:
        fail("Adobe transform-0 RGB components were not identified")
    original_header = artwork_derivatives._jpeg_header
    original_decode_planes = artwork_derivatives._jpeg_decode_planes
    try:
        artwork_derivatives._jpeg_header = lambda data: (
            1, 1, {}, {},
            [{"id": ord("R"), "h": 1, "v": 1, "q": 0, "dc": 0, "ac": 0, "rgb": 1, "rgb_channel": 0},
             {"id": ord("G"), "h": 1, "v": 1, "q": 0, "dc": 0, "ac": 0, "rgb": 1, "rgb_channel": 1},
             {"id": ord("B"), "h": 1, "v": 1, "q": 0, "dc": 0, "ac": 0, "rgb": 1, "rgb_channel": 2}],
            [], False)
        artwork_derivatives._jpeg_decode_planes = lambda *args: [
            (1, 1, [10]), (1, 1, [20]), (1, 1, [30])]
        width, height, pixels = artwork_derivatives._jpeg_dc_pixels(b"direct-rgb", 1)
    finally:
        artwork_derivatives._jpeg_header = original_header
        artwork_derivatives._jpeg_decode_planes = original_decode_planes
    if (width, height, pixels) != (1, 1, [(10, 20, 30)]):
        fail(f"direct RGB JPEG channels were converted as YCbCr: {(width, height, pixels)}")

    # Restart intervals must reset predictors even when entropy padding contains decodable bits.
    original_read_block = artwork_derivatives._jpeg_read_block_restart
    restart_calls: list[object] = []
    def fake_read_block(reader, dc_table, ac_table, qtable, previous, progressive, approx_low):
        restart_calls.append(previous)
        return previous + 1, 128
    artwork_derivatives._jpeg_read_block_restart = fake_read_block
    try:
        restart_plane = (2, 1, [0, 0])
        artwork_derivatives._jpeg_decode_noninterleaved(
            artwork_derivatives._Bits(b"\xff\xd0"),
            {"id": 1, "h": 1, "v": 1, "q": 0, "dc": 0, "ac": 0},
            restart_plane, {(0, 0): {}}, {0: [1]}, True, 0, 2, 1, 1)
    finally:
        artwork_derivatives._jpeg_read_block_restart = original_read_block
    if restart_calls != [0, 0] or restart_plane[2] != [128, 128]:
        fail(f"DRI restart did not reset the DC predictor: {restart_calls}, {restart_plane[2]}")

    # Padded storage is an implementation detail; visible coordinate scaling uses the actual grid.
    original_header = artwork_derivatives._jpeg_header
    original_decode_planes = artwork_derivatives._jpeg_decode_planes
    try:
        artwork_derivatives._jpeg_header = lambda data: (
            2, 3, {}, {}, [{"id": 1, "h": 1, "v": 2, "q": 0, "dc": 0, "ac": 0}], [], False)
        artwork_derivatives._jpeg_decode_planes = lambda *args: [(1, 2, [10, 20])]
        width, height, pixels = artwork_derivatives._jpeg_dc_pixels(b"padded")
    finally:
        artwork_derivatives._jpeg_header = original_header
        artwork_derivatives._jpeg_decode_planes = original_decode_planes
    if (width, height, pixels) != (2, 3, [(10, 10, 10)] * 6):
        fail(f"padded JPEG storage leaked into visible coordinate scaling: {(width, height, pixels)}")

    original_root = artwork_derivatives.ROOT
    original_manifest = artwork_derivatives.MANIFEST
    original_cache = artwork_derivatives._MANIFEST_CACHE
    original_review_root = artwork_review.ROOT
    try:
        with tempfile.TemporaryDirectory(prefix="artwork-derivative-test-") as temporary:
            test_root = Path(temporary)
            source = test_root / "images" / "replacement.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(artwork_derivatives.encode_png(
                4, 2, [(220, 20, 20)] * 8))
            artwork_derivatives.ROOT = test_root
            artwork_derivatives.MANIFEST = test_root / "verification" / "artwork_derivative_manifest.json"
            artwork_derivatives._MANIFEST_CACHE = None
            progressive_source = test_root / "images" / "progressive.jpg"
            progressive_source.write_bytes((original_root / "images" /
                                             "TEU_171_Eevee___Snorlax_GX_V2_369096.jpg").read_bytes())
            artwork_derivatives.ensure_for_sources([progressive_source])
            progressive_entry = json.loads(artwork_derivatives.MANIFEST.read_text(
                encoding="utf-8"))["sources"]["images/progressive.jpg"]
            if not (test_root / progressive_entry["preview"]["path"]).is_file():
                fail("progressive JPEG derivative was not written")
            artwork_derivatives.ensure_for_sources([source])
            manifest_path = artwork_derivatives.MANIFEST
            first = json.loads(manifest_path.read_text(encoding="utf-8"))
            key = "images/replacement.png"
            first_entry = first["sources"][key]
            first_preview = test_root / first_entry["preview"]["path"]
            first_bytes = first_preview.read_bytes()
            source.write_bytes(artwork_derivatives.encode_png(
                4, 2, [(20, 20, 220)] * 8))
            artwork_derivatives.ensure_for_sources([source])
            second = json.loads(manifest_path.read_text(encoding="utf-8"))
            second_entry = second["sources"][key]
            second_preview = test_root / second_entry["preview"]["path"]
            if first_entry["sourceHash"] == second_entry["sourceHash"]:
                fail("source replacement leaves derivative manifest hash unchanged")
            if first_bytes == second_preview.read_bytes():
                fail("source replacement leaves derivative bytes unchanged")
            artwork_review.ROOT = test_root
            versioned = artwork_review.image_derivatives(key, second_entry["sourceHash"])
            if not versioned.get("previewSrc", "").endswith(f"?v={second_entry['sourceHash']}"):
                fail("source replacement leaves the preview URL unversioned")
            extension_source = test_root / "images" / "extension.png"
            extension_source.write_bytes(artwork_derivatives.encode_png(
                4, 2, [(20, 220, 20)] * 8))
            legacy = test_root / "images" / "previews" / "extension.jpg"
            legacy.parent.mkdir(parents=True, exist_ok=True)
            legacy.write_bytes(first_bytes)
            artwork_derivatives.ensure_for_sources([extension_source])
            extension_entry = json.loads(manifest_path.read_text(
                encoding="utf-8"))["sources"]["images/extension.png"]
            if not extension_entry["preview"]["path"].endswith(".png"):
                fail("extension replacement reused a legacy derivative")
            if (test_root / extension_entry["preview"]["path"]).read_bytes() == first_bytes:
                fail("extension replacement copied stale derivative bytes")
    finally:
        artwork_review.ROOT = original_review_root
        artwork_derivatives.ROOT = original_root
        artwork_derivatives.MANIFEST = original_manifest
        artwork_derivatives._MANIFEST_CACHE = original_cache


def main() -> int:
    path = ROOT / "verification" / "artwork_review_projection.json"
    if not path.exists():
        fail("projection is missing")
    projection = json.loads(path.read_text(encoding="utf-8"))
    if projection != artwork_review.build():
        fail("projection is stale; run python scripts/artwork_review.py")
    if projection.get("schemaVersion") != "1.2.0" or projection.get("proposalSchemaVersion") != "1.2.0":
        fail("unexpected projection or proposal schema version")
    verify_derivative_writer()

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

    local_originals: dict[str, int] = {}
    local_previews: dict[str, int] = {}
    local_thumbnails: dict[str, int] = {}
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
                if image.get("originalHash") != expected:
                    fail(f"original image hash is not retained: {image['src']}")
                for key, maximum, totals in (("previewSrc", 360, local_previews),
                                             ("thumbnailSrc", 120, local_thumbnails)):
                    derivative = image.get(key)
                    if not derivative:
                        fail(f"repository image lacks {key}: {image['src']}")
                    derivative_path = ROOT / derivative.split("?", 1)[0]
                    if not derivative_path.is_file():
                        fail(f"image derivative is missing: {derivative}")
                    if derivative != f"{derivative_path.relative_to(ROOT).as_posix()}?v={expected}":
                        fail(f"image derivative URL is not source-versioned: {derivative}")
                    width, height = image_dimensions(derivative_path)
                    if width > maximum or height <= 0:
                        fail(f"{key} exceeds its max width: {derivative} ({width}x{height})")
                    totals[derivative] = derivative_path.stat().st_size
                local_originals[image["src"]] = image_path.stat().st_size
            elif not str(image.get("src", "")).startswith(("http://", "https://")):
                fail(f"external image has no URL: {image.get('src')}")

    if sum(local_previews.values()) >= sum(local_originals.values()):
        fail("preview derivatives do not reduce image bytes")
    if sum(local_thumbnails.values()) >= sum(local_previews.values()):
        fail("thumbnail derivatives do not reduce image bytes")
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
    nested_copy = deepcopy(projection)
    nested_member = nested_copy["groups"][0]["members"][0]
    nested_member["detection"]["note"] = "updated nested display guidance"
    if nested_member.get("images"):
        nested_member["images"][0]["label"] = "updated nested image label"
    if artwork_review.semantic_digest(artwork_review.semantic_projection_payload(nested_copy)) != before_version:
        fail("nested display metadata changes the semantic projectionVersion")

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
