#!/usr/bin/env python3
"""Offline checks for the issue-image importer."""

from __future__ import annotations

import json
import sys
import tempfile
import io
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from copy import deepcopy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "verification"))
import fetch_attachment  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts"))
import finishes  # noqa: E402
import authoritative_graph as graph_module  # noqa: E402
import source_registry  # noqa: E402
from specimen_groups import group_specimens  # noqa: E402
from specimen_links import specimen_reference_index, release_specimens, item_specimen_links  # noqa: E402


def expect_failure(callable_: object) -> None:
    try:
        callable_()
    except SystemExit:
        return
    raise AssertionError("expected validation failure")


def verify_multiple_views_case(*, secondary_finish: bool, reverse: bool) -> None:
    """Distinct views survive import/replay without multiplying printing identity (#382)."""
    with tempfile.TemporaryDirectory() as directory:
        scratch = Path(directory)
        registry = scratch / "specimens.json"
        registry.write_text(json.dumps({"count": 0, "specimens": []}), encoding="utf-8")
        manifest = scratch / "intake.json"
        # Existing valid PNG/JPEG fixtures exercise storage; this is not a visual identity test.
        inputs = [ROOT / "verification/specimens/SPEC-0040.png",
                  ROOT / "images/151C_143_Snorlax_V1_819209.jpg"]
        rows = [{
            "specimenId": f"SPEC-{index:04d}", "attachment": str(source),
            "photographSource": f"https://example.test/card/view-{index}",
            "setCode": "JU", "number": "11/64", "variant": "V1", "language": "Dutch",
            "heldBy": "owner", "inspectedFrom": "photo", "recordedAt": "2026-09-14",
            "observed": "Owner identifies SPEC-0001 and SPEC-0002 as views of one card.",
            "physicalObservation": {"finish": "holo", "basis": "synthetic storage fixture"},
        } for index, source in enumerate(inputs, 1)]
        rows[1]["sameCardAs"] = {"specimenId": "SPEC-0001", "basis": "Owner identifies the same physical card."}
        rows[1]["physicalObservation"]["edition"] = "1st Edition"
        if not secondary_finish:
            del rows[1]["physicalObservation"]["finish"]
        if reverse:
            rows.reverse()
        manifest.write_text(json.dumps({"observations": rows}), encoding="utf-8")
        args = SimpleNamespace(issue=None, issue_html=None, manifest=str(manifest),
                               allow_small=False, replace=False, dry_run=False)
        with patch.multiple(fetch_attachment, SPECIMENS_JSON=registry,
                            SPECIMEN_DIR=scratch / "photos"):
            assert fetch_attachment.command_issue(fetch_attachment.load_registry(), args) == 0
            records = fetch_attachment.load_registry()["specimens"]
            assert len(records) == 2
            for record, source in zip(records, inputs):
                assert (scratch / "photos" / record["photograph"]).read_bytes() == source.read_bytes()
                assert record["photographSha256"] == fetch_attachment.content_hash(source.read_bytes())
            before = {path: path.read_bytes() for path in scratch.rglob("*") if path.is_file()}
            assert fetch_attachment.command_issue(fetch_attachment.load_registry(), args) == 0
            assert before == {path: path.read_bytes() for path in scratch.rglob("*") if path.is_file()}

            # Reusing an ID for the other view fails before either retained image is replaced.
            manifest.write_text(json.dumps({"observations": [
                {**rows[1], "specimenId": rows[0]["specimenId"]},
            ]}), encoding="utf-8")
            expect_failure(lambda: fetch_attachment.command_issue(fetch_attachment.load_registry(), args))
            assert all(path.read_bytes() == content for path, content in before.items() if path != manifest)
            # A replacement that contradicts another retained view must fail atomically too.
            changed = deepcopy(next(row for row in rows if row["specimenId"] == "SPEC-0001"))
            changed["physicalObservation"]["edition"] = "Unlimited"
            manifest.write_text(json.dumps({"observations": [changed]}), encoding="utf-8")
            args.replace = True
            for dry_run in (True, False):
                args.dry_run = dry_run
                expect_failure(lambda: fetch_attachment.command_issue(fetch_attachment.load_registry(), args))
                assert all(path.read_bytes() == content for path, content in before.items() if path != manifest)

        printings = []
        for record in group_specimens(records):
            finishes.add_printing(printings, finishes.specimen_printing(record))
        assert len(printings) == 1
        assert printings[0]["specimenIds"] == ["SPEC-0001", "SPEC-0002"]
        assert printings[0]["edition"] == "1st Edition"
        assert printings[0]["specimenFieldSources"]["edition"] == ["SPEC-0002"]
        assert records[0]["physicalObservation"].get("edition") is None
        if not secondary_finish:
            assert "finish" not in printings[0]["sources"][1]["claimFields"]
        other_finish = {**records[0], "specimenId": "SPEC-0003", "physicalObservation": {
            "finish": "non-holo", "basis": "a different synthetic card",
        }}
        finishes.add_printing(printings, finishes.specimen_printing(other_finish))
        assert len(printings) == 2
        assert {row["finish"] for row in printings} == {"holo", "non-holo"}
        verify_group_contract(records)
        if not reverse and not secondary_finish:
            verify_group_projection(records, scratch)


def verify_multiple_views() -> None:
    for reverse in (False, True):
        for secondary_finish in (False, True):
            verify_multiple_views_case(secondary_finish=secondary_finish, reverse=reverse)


def verify_duplicate_photo_batch() -> None:
    """One hash cannot create two SPEC IDs, even inside a new/replacement/dry-run batch."""
    with tempfile.TemporaryDirectory() as directory:
        scratch = Path(directory)
        registry, manifest = scratch / "specimens.json", scratch / "manifest.json"
        registry.write_text(json.dumps({"count": 0, "specimens": []}), encoding="utf-8")
        source = ROOT / "verification/specimens/SPEC-0041.png"
        rows = [{
            "specimenId": f"SPEC-99{index:02d}", "attachment": str(source),
            "photographSource": f"https://example.test/batch/view-{index}",
            "setCode": "JU", "number": "11/64", "variant": "V1", "language": "Dutch",
            "heldBy": "collection owner", "inspectedFrom": "synthetic storage fixture",
            "observed": "Same original bytes at distinct URLs do not establish another view.",
            "recordedAt": "2026-09-14", "physicalObservation": {"finish": "holo", "basis": "fixture"},
        } for index in (1, 2)]
        with patch.multiple(fetch_attachment, SPECIMENS_JSON=registry, SPECIMEN_DIR=scratch / "photos"):
            for linked in (False, True):
                if linked:
                    rows[1]["sameCardAs"] = {"specimenId": "SPEC-9901", "basis": "synthetic link"}
                for reverse in (False, True):
                    ordered = rows[::-1] if reverse else rows
                    manifest.write_text(json.dumps({"observations": ordered}), encoding="utf-8")
                    before = {path: path.read_bytes() for path in scratch.rglob("*") if path.is_file()}
                    for replace, dry_run in ((False, False), (True, False), (False, True), (True, True)):
                        args = SimpleNamespace(issue=None, issue_html=None, manifest=str(manifest),
                                               allow_small=False, replace=replace, dry_run=dry_run)
                        error_output = io.StringIO()
                        with redirect_stderr(error_output):
                            expect_failure(lambda: fetch_attachment.command_issue(fetch_attachment.load_registry(), args))
                        expected = (f"image bytes already belong to {ordered[0]['specimenId']}; "
                                    f"duplicate evidence cannot create {ordered[1]['specimenId']}")
                        assert expected in error_output.getvalue(), error_output.getvalue()
                        assert before == {path: path.read_bytes() for path in scratch.rglob("*") if path.is_file()}


def verify_group_contract(records) -> None:
    for invalid in (
        {"sameCardAs": {"specimenId": "SPEC-0002", "basis": "self"}},
        {"sameCardAs": {"specimenId": "SPEC-9999", "basis": "missing"}},
        {"sameCardAs": {"specimenId": "SPEC-0001", "basis": " "}},
        {"language": "English"}, {"number": "12/64"}, {"number": "11/100"}, {"variant": "V2"},
        {"physicalObservation": {"finish": "non-holo", "basis": "contradiction"}},
        {"physicalObservation": {"finish": "holo", "basis": "context", "coversMultipleCards": True}},
        {"physicalObservation": {"finish": "holo", "basis": "conflict", "conflictsWith": ["SPEC-0001"]}},
    ):
        try:
            group_specimens([records[0], {**records[1], **invalid}])
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid same-card group accepted: {invalid}")
    cyclic = deepcopy(records)
    cyclic[0]["sameCardAs"] = {"specimenId": "SPEC-0002", "basis": "cycle"}
    try:
        group_specimens(cyclic)
    except ValueError:
        pass
    else:
        raise AssertionError("cyclic sameCardAs accepted")
    # The same printed identity never itself authorizes merging complementary observations.
    separate = deepcopy(records)
    separate[1].pop("sameCardAs")
    separate[1]["physicalObservation"]["finish"] = "holo"
    printings = []
    for record in group_specimens(separate):
        finishes.add_printing(printings, finishes.specimen_printing(record))
    assert len(printings) == 2
    attested = deepcopy(records)
    attested[1]["physicalObservation"]["ownerAttestedFields"] = ["edition"]
    candidate = finishes.specimen_printing(group_specimens(attested)[0])
    sources = [source for source in candidate["sources"] if source["specimenId"] == "SPEC-0002"]
    assert "edition" not in sources[0]["claimFields"]
    assert sources[1]["claimFields"] == ["edition"] and "url" not in sources[1]
    equal = deepcopy(records)
    equal[1]["physicalObservation"] = deepcopy(equal[0]["physicalObservation"])
    assert finishes.specimen_printing(group_specimens(equal)[0])["specimenIds"] == ["SPEC-0001", "SPEC-0002"]
    identity_only = deepcopy(records)
    for row in identity_only:
        row.pop("physicalObservation")
    assert finishes.specimen_printing(group_specimens(identity_only)[0]) is None
    incoming = {**records[0], "specimenId": "SPEC-0003", "physicalObservation": {
        "finish": "non-holo", "basis": "conflicting independent observation", "conflictsWith": ["SPEC-0002"]}}
    candidate = finishes.specimen_printing(group_specimens([*records, incoming])[0])
    printings = []
    finishes.add_printing(printings, candidate)
    assert printings[0]["verificationStatus"] == "pending" and printings[0]["conflictsWith"] == ["SPEC-0003"]


def verify_group_projection(records, scratch) -> None:
    """Exercise the real finish/graph paths, including an already catalogued edition pair."""
    records = deepcopy(records)
    for index, record in enumerate(records, 1):
        record["specimenId"] = f"SPEC-99{index:02d}"
    records[1]["sameCardAs"]["specimenId"] = "SPEC-9901"
    # Matching a known printing requires the fixture's own positive stamp/size evidence.
    records[1]["physicalObservation"].update({"markings": "EDITIE 1", "markingRole": "print-identity"})
    records[1]["physicalObservation"]["ownerAttestedFields"] = ["edition"]
    records[0]["physicalObservation"]["cardSize"] = "standard"
    original_doc = json.loads((ROOT / "verification/specimens.json").read_text(encoding="utf-8"))
    document = {**original_doc, "specimens": original_doc["specimens"] + records}
    document["count"] = len(document["specimens"])
    path = scratch / "all-specimens.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with patch.object(finishes, "SPECIMENS_PATH", path):
        context = finishes._load_finish_context()
        assert finishes._resolve_tcgdex(context) is None
        finishes._prepare_finish_indexes(context)
        unit_index = sorted(context["grouped_units"], key=finishes.group_sort_key).index(("JU", "11", "Dutch"))
        unit = finishes._build_finish_unit(context, unit_index, ("JU", "11", "Dutch"))
    assert len(unit["printings"]) == 2, unit["printings"]
    matched = [row for row in unit["printings"] if "SPEC-9901" in row.get("specimenIds", [])]
    assert len(matched) == 1 and matched[0]["edition"] == "1st Edition"
    finish_doc = json.loads((ROOT / "verification/finish_units.json").read_text(encoding="utf-8"))
    finish_doc["units"] = [unit if row["finishUnitId"] == unit["finishUnitId"] else row
                           for row in finish_doc["units"]]
    finish_path = scratch / "finishes.json"
    graph = graph_module.read_graph()
    for standalone in (False, True):
        current_finishes = deepcopy(finish_doc)
        if standalone:
            # Keep legacy printings intact but remove fixture evidence to exercise the fallback.
            baseline = json.loads((ROOT / "verification/finish_units.json").read_text(encoding="utf-8"))
            current_finishes = baseline
        finish_path.write_text(json.dumps(current_finishes), encoding="utf-8")
        with patch.multiple(graph_module, SPECIMENS=path, FINISH_UNITS=finish_path):
            projected = graph_module.project_physical_evidence(deepcopy(graph))
        errors = graph_module.validate(projected, identity_inputs={"specimens": document, "finishes": current_finishes})
        assert not errors, errors
        physicals = [row["payload"] for row in projected["entities"]
                     if row["entityType"] == "physical-printing" and "SPEC-9901" in row["payload"].get("specimenIds", [])]
        assert len(physicals) == 1 and physicals[0]["edition"] == "1st Edition"
        assert {"SPEC-9901", "SPEC-9902"}.issubset(physicals[0]["specimenIds"])
        claim = next(row["payload"] for row in projected["entities"]
                     if row["entityId"] == "CLAIM:specimen:SPEC-9902")
        assert "edition" not in claim["observedFields"] and claim["ownerAttestedFields"] == ["edition"]
        changed = deepcopy(projected)
        bad_claim = next(row["payload"] for row in changed["entities"]
                         if row["entityId"] == "CLAIM:specimen:SPEC-9902")
        bad_claim["observedFields"].append("edition")
        assert any("specimen view provenance is stale" in error for error in graph_module.validate(
            changed, identity_inputs={"specimens": document, "finishes": current_finishes}))
        assert not any(edge["relation"] == "corroborates" and edge["fromId"].startswith("CLAIM:specimen:SPEC-99")
                       for edge in projected["edges"])
        verify_group_links(records, physicals[0])


def verify_group_links(records, physical) -> None:
    citation_index = specimen_reference_index(records)
    release = {"sourceFirstRecordIds": ["fixture-print"]}
    source_first = {"fixture-print": {"specimenId": "SPEC-9901"}}
    assert release_specimens(release, [], citation_index, source_first, {}) == ["SPEC-9901", "SPEC-9902"]
    assert item_specimen_links(release, physical, citation_index, source_first, {},
                              {row["specimenId"]: row for row in records}) == {
                                  row["photographSource"] for row in records}
    calls = []
    source_registry.record_linked_specimens(records, [], lambda *a, **kw: calls.append(a),
                                          [{"printId": "fixture-print", "specimenId": "SPEC-9901"}])
    assert any(call[3] == "SPEC-9902" for call in calls)
    assert any(call[0] == records[1]["photographSource"] and call[3] == "fixture-print" for call in calls)
    assert not any(call[0] == records[1]["photographSource"] and call[2] == "finish" for call in calls)
    assert any(call[0] is None and call[2] == "edition" and call[3] == "SPEC-9902" for call in calls)
    assert not any(call[0] == records[1]["photographSource"] and call[2] == "edition" for call in calls)
    # An observed-finish capability does not automatically authorize observed edition.
    calls = []
    source_registry.record_specimen_claim(
        "https://example.test/photo", "Retail listing", "retailer-listing", "identity", "SPEC-9902",
        "2026-09-14", {"edition": "1st Edition"}, lambda *a, **kw: calls.append((a, kw)),
        source_registry.specimen_surfaces(), fields=("edition",))
    edition_call = next(call for call in calls if call[0][2] == "edition")
    assert edition_call[0][0] is None and edition_call[1]["provider_id"] == "inspected-specimen"
    identity_primary = deepcopy(records)
    identity_primary[0].pop("physicalObservation")
    identity_primary[1]["physicalObservation"]["finish"] = "holo"
    calls = []
    source_registry.record_linked_specimens(identity_primary, [], lambda *a, **kw: calls.append(a))
    assert any(call[0] == identity_primary[0]["photographSource"] and call[3] == "SPEC-9901" for call in calls)
    assert not any(call[3] == "SPEC-9901" and call[2] == "finish" for call in calls)
    calls = []
    source_registry.record_printing_source({"specimenId": "SPEC-9902", "url": "https://example.test/photo",
        "sourceType": "Retail listing", "observedFields": ["edition"], "retrievedAt": "2026-09-14"},
        "F-TEST-P01", ["identity", "edition"], lambda *a, **kw: calls.append((a, kw)), source_registry.specimen_surfaces())
    edition_call = next(call for call in calls if call[0][2] == "edition")
    assert edition_call[0][0] is None and edition_call[1]["provider_id"] == "inspected-specimen"


def main() -> None:
    html = """
    <a href="https://github.com/user-attachments/assets/stable-a">
      <img src="https://private-user-images.githubusercontent.com/1/signed-a.png">
    </a>
    <a href="https://github.com/user-attachments/assets/stable-b">
      <img src="https://github.com/user-attachments/assets/stable-b">
    </a>
    """
    assert fetch_attachment.issue_attachments(html) == [
        (
            "https://github.com/user-attachments/assets/stable-a",
            [
                "https://github.com/user-attachments/assets/stable-a",
                "https://private-user-images.githubusercontent.com/1/signed-a.png",
            ],
        ),
        (
            "https://github.com/user-attachments/assets/stable-b",
            ["https://github.com/user-attachments/assets/stable-b"],
        ),
    ]
    signed_only = (
        '<img src="https://private-user-images.githubusercontent.com/1/signed-only.png">'
    )
    assert fetch_attachment.issue_attachments(signed_only) == [(
        "https://private-user-images.githubusercontent.com/1/signed-only.png",
        ["https://private-user-images.githubusercontent.com/1/signed-only.png"],
    )]
    assert fetch_attachment.canonical_issue_attachment_provenance(
        "https://github.com/m4s-ai/snoredex-data/issues/999",
        "https://github.com/user-attachments/assets/stable-a", 1,
    ) == "https://github.com/m4s-ai/snoredex-data/issues/999#attachment-1"
    assert fetch_attachment.canonical_issue_attachment_provenance(
        "https://github.com/m4s-ai/snoredex-data/issues/999",
        "https://private-user-images.githubusercontent.com/1/signed-only.png", 2,
    ) == "https://github.com/m4s-ai/snoredex-data/issues/999#attachment-2"
    assert fetch_attachment.canonical_issue_attachment_provenance(
        "https://github.com/m4s-ai/snoredex-data/issues/999",
        "https://cdn.example.test/card.png", 3,
    ) == "https://cdn.example.test/card.png"
    duplicate_html = html + html.split("</a>", 1)[0] + "</a>"
    assert len(fetch_attachment.issue_attachments(duplicate_html)) == 2
    image = (ROOT / "verification" / "specimens" / "SPEC-0040.png").read_bytes()
    digest = fetch_attachment.content_hash(image)
    assert digest.startswith("sha256:") and len(digest) == 71
    owners = {}
    fetch_attachment.ensure_unique_photo_hash(owners, digest, "SPEC-9999")
    expect_failure(lambda: fetch_attachment.ensure_unique_photo_hash(owners, digest, "SPEC-9998"))
    expect_failure(lambda: fetch_attachment.ensure_specimen_id_available(
        {"specimenId": "SPEC-9999", "photograph": None}, None, "SPEC-9999", False
    ))
    assert fetch_attachment.validate(image, allow_small=False)[0] == "png"
    rgb_jpeg = bytearray((ROOT / "images" / "151C_143_Snorlax_V1_819209.jpg").read_bytes())
    offset = 2
    while offset + 9 < len(rgb_jpeg):
        if rgb_jpeg[offset] == 0xFF and 0xC0 <= rgb_jpeg[offset + 1] <= 0xCF \
                and rgb_jpeg[offset + 1] not in (0xC4, 0xC8, 0xCC):
            rgb_jpeg[offset + 9] = 4
            break
        offset += 1
    assert fetch_attachment.jpeg_component_count(bytes(rgb_jpeg)) == 4
    expect_failure(lambda: fetch_attachment.validate(bytes(rgb_jpeg), allow_small=False))
    unsupported_frame = bytearray((ROOT / "images" / "151C_143_Snorlax_V1_819209.jpg").read_bytes())
    offset = 2
    while offset + 9 < len(unsupported_frame):
        if unsupported_frame[offset] == 0xFF and 0xC0 <= unsupported_frame[offset + 1] <= 0xCF \
                and unsupported_frame[offset + 1] not in (0xC4, 0xC8, 0xCC):
            unsupported_frame[offset + 1] = 0xC3  # lossless SOF3 is outside the decoder contract
            break
        offset += 1
    assert fetch_attachment.jpeg_frame_info(bytes(unsupported_frame))[0] == 0xC3
    expect_failure(lambda: fetch_attachment.validate(bytes(unsupported_frame), allow_small=False))
    unsupported_precision = bytearray((ROOT / "images" / "151C_143_Snorlax_V1_819209.jpg").read_bytes())
    offset = 2
    while offset + 9 < len(unsupported_precision):
        if unsupported_precision[offset] == 0xFF and 0xC0 <= unsupported_precision[offset + 1] <= 0xCF \
                and unsupported_precision[offset + 1] not in (0xC4, 0xC8, 0xCC):
            unsupported_precision[offset + 1] = 0xC1
            unsupported_precision[offset + 4] = 12
            break
        offset += 1
    precision_frame = fetch_attachment.jpeg_frame_info(bytes(unsupported_precision))
    assert precision_frame and precision_frame[:2] == (0xC1, 3) and precision_frame[2] == 12
    expect_failure(lambda: fetch_attachment.validate(bytes(unsupported_precision), allow_small=False))
    filled_markers = (ROOT / "images" / "151C_143_Snorlax_V1_819209.jpg").read_bytes()
    filled_markers = filled_markers[:2] + b"\xff\xff" + filled_markers[2:]
    assert fetch_attachment.validate(filled_markers, allow_small=False)[0] == "jpg"
    graph = json.loads(
        (ROOT / "verification" / "authoritative_graph.json").read_text(encoding="utf-8")
    )
    releases = [row["payload"] for row in graph["entities"]
                if row["entityType"] == "card-release"]
    source_first = fetch_attachment.source_first_release_for(releases, "S-P", "145", "T-Chinese")
    assert source_first and source_first["cardReleaseId"].startswith("RELEASE:TW:T-Chinese:S-P:145")
    expect_failure(lambda: fetch_attachment.validate(b"not an image", allow_small=False))
    expect_failure(lambda: fetch_attachment.validate(image[:-12], allow_small=False))
    expect_failure(lambda: fetch_attachment.select_issue_attachment([], None, 1))
    same_basename = [
        ("https://cdn.example.test/a/s-l1600.jpg", ["https://cdn.example.test/a/s-l1600.jpg"]),
        ("https://cdn.example.test/b/s-l1600.jpg", ["https://cdn.example.test/b/s-l1600.jpg"]),
    ]
    assert fetch_attachment.select_issue_attachment(
        same_basename, "https://cdn.example.test/b/s-l1600.jpg", 1
    ) == same_basename[1]
    expect_failure(lambda: fetch_attachment.build_specimen(
        {"setCode": "JU", "number": "11", "variant": "V1", "language": "Dutch"},
        "SPEC-9999", "SPEC-9999.png", "issue", digest
    ))

    original_download = fetch_attachment.download
    calls = []

    def fake_download(url: str) -> bytes:
        calls.append(url)
        if len(calls) == 1:
            raise fetch_attachment.SourceUnreachable("expired signed URL")
        return b"image bytes"

    fetch_attachment.download = fake_download
    try:
        assert fetch_attachment.download_candidates([
            "https://private-user-images.githubusercontent.com/1/expired.png",
            "https://cdn.example.test/card.png",
        ]) == b"image bytes"
    finally:
        fetch_attachment.download = original_download
    assert calls == [
        "https://private-user-images.githubusercontent.com/1/expired.png",
        "https://cdn.example.test/card.png",
    ]

    record = fetch_attachment.build_specimen(
        {
            "setCode": "JU", "number": "11", "variant": "V1", "language": "Dutch",
            "heldBy": "owner", "inspectedFrom": "photo", "observed": "positive",
            "recordedAt": "2026-08-24", "physicalObservation": {
                "finish": "holo", "basis": "observed card surface"
            },
        }, "SPEC-9999", "SPEC-9999.png", "issue", digest
    )
    assert record["photographSha256"] == digest
    identity_only = fetch_attachment.build_specimen(
        {
            "setCode": "JU", "number": "27", "variant": "V2", "language": "Spanish",
            "heldBy": "third-party database", "inspectedFrom": "database scan",
            "observed": "positive identity only", "recordedAt": "2026-08-27",
        }, "SPEC-9995", "SPEC-9995.png", "database", digest
    )
    assert "physicalObservation" not in identity_only
    seller_record = fetch_attachment.build_specimen(
        {
            "setCode": "JU", "number": "11", "variant": "V1", "language": "Dutch",
            "heldBy": "third-party seller", "inspectedFrom": "listing photograph",
            "observed": "positive", "recordedAt": "2026-08-24",
            "physicalObservation": {"finish": "holo", "basis": "observed card surface"},
        }, "SPEC-9998", "SPEC-9998.png", "issue", digest,
        listing_url="https://seller.example/listing/11",
    )
    assert seller_record["listingUrl"] == "https://seller.example/listing/11"
    allowed_small = fetch_attachment.build_specimen(
        {
            "setCode": "JU", "number": "11", "variant": "V1", "language": "Dutch",
            "heldBy": "owner", "inspectedFrom": "photo", "observed": "positive",
            "recordedAt": "2026-08-24",
            "physicalObservation": {"finish": "holo", "basis": "observed card surface"},
        }, "SPEC-9996", "SPEC-9996.png", "issue", digest, allow_small=True
    )
    assert allowed_small["photographAllowSmall"] is True
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "Reverse Holo", "basis": "observed card surface"}, "SPEC-9995"
    ))
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "holo", "basis": "observed card surface", "edition": "Unlimited-ish"},
        "SPEC-9995"
    ))
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "holo", "basis": "observed card surface", "foilPattern": ["poke-ball"]},
        "SPEC-9995"
    ))
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "holo", "basis": "observed card surface", "distribution": "fixed-deck"},
        "SPEC-9995"
    ))
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "holo", "basis": "observed card surface",
         "distribution": {"kind": 7}}, "SPEC-9995"
    ))
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "holo", "basis": "observed card surface", "cardSize": 1},
        "SPEC-9995"
    ))
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "holo", "basis": "observed card surface", "markings": "EDITIE 1"},
        "SPEC-9995"
    ))
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "holo", "basis": "observed card surface", "conflictsWith": "SPEC-0040"},
        "SPEC-9995", {"SPEC-9995", "SPEC-0040"}
    ))
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "holo", "basis": "observed card surface", "conflictsWith": ["SPEC-MISSING"]},
        "SPEC-9995", {"SPEC-9995", "SPEC-0040"}
    ))
    expect_failure(lambda: fetch_attachment.validate_observation(
        {"finish": "holo", "basis": "observed card surface", "conflictsWith": ["SPEC-0040"]},
        "SPEC-9995", {"SPEC-9995"}
    ))
    expect_failure(lambda: fetch_attachment.ensure_cited_identity(
        {"specimenId": "SPEC-9994", "setCode": "JU", "number": "11/64",
         "variant": "V1", "language": "Dutch", "citedBy": ["F0167-P01"]},
        {"setCode": "JU", "number": "27/64", "variant": "V1", "language": "Dutch"},
    ))
    expect_failure(lambda: fetch_attachment.build_specimen(
        {
            "setCode": "JU", "number": "11", "variant": "V1", "language": "Dutch",
            "heldBy": "third-party seller", "inspectedFrom": "listing photograph",
            "observed": "positive", "recordedAt": "2026-08-24",
            "physicalObservation": {"finish": "holo", "basis": "observed card surface"},
        }, "SPEC-9997", "SPEC-9997.png", "issue", digest,
    ))
    assert fetch_attachment.validate_specimen_id("SPEC-9999") == "SPEC-9999"
    expect_failure(lambda: fetch_attachment.validate_specimen_id("../../outside"))

    # Direct --specimen imports must reject bytes already filed under another specimen too.
    source = ROOT / ".fetch-attachment-test-card.png"
    source.write_bytes(image)
    original_specimen_dir = fetch_attachment.SPECIMEN_DIR
    fetch_attachment.SPECIMEN_DIR = ROOT
    try:
        expect_failure(lambda: fetch_attachment.command_file(
            {"specimens": [
                {"specimenId": "SPEC-0001", "photograph": None},
                {"specimenId": "SPEC-0002", "photographSha256": digest},
            ]},
            SimpleNamespace(
                specimen="SPEC-0001", source=str(source), attachment_url=None,
                replace=False, allow_small=False, dry_run=True,
            ),
        ))
    finally:
        fetch_attachment.SPECIMEN_DIR = original_specimen_dir
        source.unlink(missing_ok=True)

    # Hash validation covers photographs even when they are not finish projections.
    photo_paths = [ROOT / name for name in (
        ".fetch-attachment-test-plain.png",
        ".fetch-attachment-test-multiple.png",
        ".fetch-attachment-test-tmp.png",
    )]
    for path in photo_paths:
        path.write_bytes(image)
    records = [
        {"specimenId": "SPEC-PLAIN", "photograph": photo_paths[0].name,
         "photographSha256": digest, "photographAllowSmall": True},
        {"specimenId": "SPEC-MULTIPLE", "photograph": photo_paths[1].name,
         "photographSha256": digest,
         "physicalObservation": {"finish": "holo", "coversMultipleCards": True}},
        {"specimenId": "SPEC-TMP", "photograph": photo_paths[2].name,
         "photographSha256": digest,
         "photographSource": "/tmp/old.png",
         "physicalObservation": {"finish": "holo", "basis": "observed card surface"}},
    ]
    registry = ROOT / ".fetch-attachment-test-specimens.json"
    original_registry = fetch_attachment.SPECIMENS_JSON
    original_specimen_dir = fetch_attachment.SPECIMEN_DIR
    fetch_attachment.SPECIMENS_JSON = registry
    fetch_attachment.SPECIMEN_DIR = ROOT
    registry.write_text(json.dumps({"count": len(records), "specimens": records}), encoding="utf-8")
    try:
        seen_allow_small = []
        original_validate = fetch_attachment.validate
        fetch_attachment.validate = lambda blob, allow_small: (
            seen_allow_small.append(allow_small) or original_validate(blob, allow_small)
        )
        assert fetch_attachment.command_evidence_check(check_projection=False) == 0
        assert seen_allow_small == [True, False, False]
        fetch_attachment.validate = original_validate
        registry.write_text(
            json.dumps({"count": len(records) - 1, "specimens": records}), encoding="utf-8"
        )
        assert fetch_attachment.command_evidence_check(check_projection=False) == 1
        registry.write_text(
            json.dumps({"count": len(records), "specimens": records}), encoding="utf-8"
        )
        photo_paths[0].write_bytes(image[:-1] + b"\x00")
        assert fetch_attachment.command_evidence_check(check_projection=False) == 1
    finally:
        fetch_attachment.validate = original_validate
        fetch_attachment.SPECIMENS_JSON = original_registry
        fetch_attachment.SPECIMEN_DIR = original_specimen_dir
        registry.unlink(missing_ok=True)
        for path in photo_paths:
            path.unlink(missing_ok=True)

    # Issue imports validate their bytes immediately, but defer projection checks until regen.py.
    issue_html = ROOT / ".fetch-attachment-test-issue.html"
    issue_html.write_text(
        '<a href="https://github.com/user-attachments/assets/stable">'
        '<img src="https://cdn.example.test/card.png"></a>', encoding="utf-8"
    )
    manifest = ROOT / ".fetch-attachment-test-manifest.json"
    manifest.write_text(json.dumps({"issue": 999, "observations": [{
        "attachmentIndex": 1, "setCode": "JU", "number": "11/64", "variant": "V1",
        "language": "Dutch", "heldBy": "owner", "inspectedFrom": "photo",
        "observed": "positive", "recordedAt": "2026-08-24",
        "physicalObservation": {"finish": "holo", "basis": "observed card surface"},
    }]}), encoding="utf-8")
    registry = ROOT / ".fetch-attachment-test-import.json"
    registry.write_text(json.dumps({"count": 0, "specimens": []}), encoding="utf-8")
    original_registry = fetch_attachment.SPECIMENS_JSON
    original_specimen_dir = fetch_attachment.SPECIMEN_DIR
    original_download_candidates = fetch_attachment.download_candidates
    fetch_attachment.SPECIMENS_JSON = registry
    fetch_attachment.SPECIMEN_DIR = ROOT
    fetch_attachment.download_candidates = lambda candidates: image
    try:
        assert fetch_attachment.command_issue(
            {"count": 0, "specimens": []},
            SimpleNamespace(
                issue=999, issue_html=str(issue_html), manifest=str(manifest),
                allow_small=False, replace=False, dry_run=False,
            ),
        ) == 0
    finally:
        fetch_attachment.SPECIMENS_JSON = original_registry
        fetch_attachment.SPECIMEN_DIR = original_specimen_dir
        fetch_attachment.download_candidates = original_download_candidates
        issue_html.unlink(missing_ok=True)
        manifest.unlink(missing_ok=True)
        registry.unlink(missing_ok=True)
        (ROOT / "SPEC-0001.png").unlink(missing_ok=True)

    # The same manifest path accepts owner-supplied local or reachable images without an issue.
    direct_source = ROOT / ".fetch-attachment-test-direct-source.png"
    direct_source.write_bytes(image)
    direct_manifest = ROOT / ".fetch-attachment-test-direct-manifest.json"
    direct_manifest.write_text(json.dumps({"issue": 999, "observations": [{
        "attachment": str(direct_source),
        "photographSource": "https://drive.example.test/file/card/view",
        "setCode": "OWNER", "number": "001/001", "variant": "base",
        "language": "Dutch", "heldBy": "collection owner", "inspectedFrom": "photo",
        "observed": "positive", "recordedAt": "2026-08-29",
        "allowUnprojected": True,
        "physicalObservation": {"finish": "holo", "basis": "observed card surface"},
    }]}), encoding="utf-8")
    direct_registry = ROOT / ".fetch-attachment-test-direct-registry.json"
    direct_registry.write_text(json.dumps({"count": 0, "specimens": []}), encoding="utf-8")
    original_registry = fetch_attachment.SPECIMENS_JSON
    original_specimen_dir = fetch_attachment.SPECIMEN_DIR
    fetch_attachment.SPECIMENS_JSON = direct_registry
    fetch_attachment.SPECIMEN_DIR = ROOT
    try:
        direct_doc = {"count": 0, "specimens": []}
        assert fetch_attachment.command_issue(
            direct_doc,
            SimpleNamespace(
                issue=None, issue_html=None, manifest=str(direct_manifest),
                allow_small=False, replace=False, dry_run=False,
            ),
        ) == 0
        assert direct_doc["specimens"][0]["photographSource"] == (
            "https://drive.example.test/file/card/view"
        )
    finally:
        fetch_attachment.SPECIMENS_JSON = original_registry
        fetch_attachment.SPECIMEN_DIR = original_specimen_dir
        direct_source.unlink(missing_ok=True)
        direct_manifest.unlink(missing_ok=True)
        direct_registry.unlink(missing_ok=True)
        (ROOT / "SPEC-0001.png").unlink(missing_ok=True)

    # Source-first releases without a legacy finish unit use the authoritative card-release index.
    source_first_issue = ROOT / ".fetch-attachment-test-source-first.html"
    source_first_issue.write_text(
        '<a href="https://github.com/user-attachments/assets/source-first">'
        '<img src="https://cdn.example.test/card.png"></a>', encoding="utf-8"
    )
    source_first_manifest = ROOT / ".fetch-attachment-test-source-first-manifest.json"
    source_first_manifest.write_text(json.dumps({"issue": 999, "observations": [{
        "attachmentIndex": 1, "specimenId": "SPEC-0098", "setCode": "S-P", "number": "145",
        "variant": "base", "language": "T-Chinese", "heldBy": "owner",
        "inspectedFrom": "photo", "observed": "positive", "recordedAt": "2026-08-24",
        "physicalObservation": {"finish": "mirror-holo", "basis": "observed card surface"},
    }]}), encoding="utf-8")
    source_first_units = ROOT / ".fetch-attachment-test-source-first-units.json"
    source_first_units.write_text(json.dumps({"units": []}), encoding="utf-8")
    source_first_registry = ROOT / ".fetch-attachment-test-source-first-registry.json"
    source_first_registry.write_text(json.dumps({"count": 0, "specimens": []}), encoding="utf-8")
    original_registry = fetch_attachment.SPECIMENS_JSON
    original_specimen_dir = fetch_attachment.SPECIMEN_DIR
    original_finish_units = fetch_attachment.FINISH_UNITS
    original_download_candidates = fetch_attachment.download_candidates
    fetch_attachment.SPECIMENS_JSON = source_first_registry
    fetch_attachment.SPECIMEN_DIR = ROOT
    fetch_attachment.FINISH_UNITS = source_first_units
    fetch_attachment.download_candidates = lambda candidates: image
    try:
        source_first_doc = {"count": 0, "specimens": []}
        assert fetch_attachment.command_issue(
            source_first_doc,
            SimpleNamespace(
                issue=999, issue_html=str(source_first_issue), manifest=str(source_first_manifest),
                allow_small=False, replace=False, dry_run=False,
            ),
        ) == 0
        assert source_first_doc["specimens"][0]["setCode"] == "S-P"
    finally:
        fetch_attachment.SPECIMENS_JSON = original_registry
        fetch_attachment.SPECIMEN_DIR = original_specimen_dir
        fetch_attachment.FINISH_UNITS = original_finish_units
        fetch_attachment.download_candidates = original_download_candidates
        source_first_issue.unlink(missing_ok=True)
        source_first_manifest.unlink(missing_ok=True)
        source_first_units.unlink(missing_ok=True)
        source_first_registry.unlink(missing_ok=True)
        (ROOT / "SPEC-0098.png").unlink(missing_ok=True)

    # Identical bytes must still surface corrected metadata instead of returning an early no-op.
    metadata_issue = ROOT / ".fetch-attachment-test-metadata.html"
    metadata_issue.write_text(
        '<a href="https://github.com/user-attachments/assets/metadata">'
        '<img src="https://cdn.example.test/card.png"></a>', encoding="utf-8"
    )
    metadata_manifest = ROOT / ".fetch-attachment-test-metadata-manifest.json"
    metadata_manifest.write_text(json.dumps({"issue": 999, "observations": [{
        "attachmentIndex": 1, "specimenId": "SPEC-0098", "setCode": "JU", "number": "11",
        "variant": "V1", "language": "Dutch", "heldBy": "owner", "inspectedFrom": "photo",
        "observed": "positive", "recordedAt": "2026-08-24",
        "physicalObservation": {"finish": "holo", "basis": "corrected basis"},
    }]}), encoding="utf-8")
    metadata_registry = ROOT / ".fetch-attachment-test-metadata-registry.json"
    metadata_registry.write_text(json.dumps({"count": 1, "specimens": [{
        "specimenId": "SPEC-0098", "setCode": "JU", "number": "11", "variant": "V1",
        "language": "Dutch", "heldBy": "owner", "inspectedFrom": "photo", "observed": "positive",
        "recordedAt": "2026-08-24", "physicalObservation": {
            "finish": "holo", "basis": "old basis",
        }, "photograph": "SPEC-0098.png",
        "photographSource": "https://github.com/user-attachments/assets/metadata",
        "photographSha256": digest,
    }]}), encoding="utf-8")
    metadata_photo = ROOT / "SPEC-0098.png"
    metadata_photo.write_bytes(image)
    original_registry = fetch_attachment.SPECIMENS_JSON
    original_specimen_dir = fetch_attachment.SPECIMEN_DIR
    original_download_candidates = fetch_attachment.download_candidates
    fetch_attachment.SPECIMENS_JSON = metadata_registry
    fetch_attachment.SPECIMEN_DIR = ROOT
    fetch_attachment.download_candidates = lambda candidates: image
    try:
        expect_failure(lambda: fetch_attachment.command_issue(
            json.loads(metadata_registry.read_text(encoding="utf-8")),
            SimpleNamespace(
                issue=999, issue_html=str(metadata_issue), manifest=str(metadata_manifest),
                allow_small=False, replace=False, dry_run=False,
            ),
        ))
    finally:
        fetch_attachment.SPECIMENS_JSON = original_registry
        fetch_attachment.SPECIMEN_DIR = original_specimen_dir
        fetch_attachment.download_candidates = original_download_candidates
        metadata_issue.unlink(missing_ok=True)
        metadata_manifest.unlink(missing_ok=True)
        metadata_registry.unlink(missing_ok=True)
        metadata_photo.unlink(missing_ok=True)

    # Signed-only issue HTML must match the stable issue provenance from a prior run.
    signed_issue_html = ROOT / ".fetch-attachment-test-signed-only.html"
    signed_issue_html.write_text(
        '<a href="https://github.com/user-attachments/assets/ordinary">'
        '<img src="https://cdn.example.test/ordinary.png"></a>' + signed_only,
        encoding="utf-8"
    )
    signed_manifest = ROOT / ".fetch-attachment-test-signed-only-manifest.json"
    signed_manifest.write_text(json.dumps({"issue": 999, "observations": [{
        "attachmentIndex": 2, "setCode": "JU", "number": "11/64", "variant": "V1",
        "language": "Dutch", "heldBy": "owner", "inspectedFrom": "photo",
        "observed": "positive", "recordedAt": "2026-08-24",
        "physicalObservation": {"finish": "holo", "basis": "observed card surface"},
    }]}), encoding="utf-8")
    signed_registry = ROOT / ".fetch-attachment-test-signed-only-registry.json"
    signed_registry.write_text(json.dumps({"count": 1, "specimens": [{
        "specimenId": "SPEC-0099",
        "setCode": "JU", "number": "11/64", "variant": "V1", "language": "Dutch",
        "heldBy": "owner", "inspectedFrom": "photo", "observed": "positive",
        "recordedAt": "2026-08-24", "citedBy": ["F0167-P01"],
        "physicalObservation": {"finish": "holo", "basis": "observed card surface"},
        "photographSource": "https://github.com/m4s-ai/snoredex-data/issues/999#attachment-2",
    }]}), encoding="utf-8")
    original_registry = fetch_attachment.SPECIMENS_JSON
    original_specimen_dir = fetch_attachment.SPECIMEN_DIR
    original_download_candidates = fetch_attachment.download_candidates
    fetch_attachment.SPECIMENS_JSON = signed_registry
    fetch_attachment.SPECIMEN_DIR = ROOT
    fetch_attachment.download_candidates = lambda candidates: image
    signed_doc = json.loads(signed_registry.read_text(encoding="utf-8"))
    try:
        assert fetch_attachment.command_issue(
            signed_doc,
            SimpleNamespace(
                issue=999, issue_html=str(signed_issue_html), manifest=str(signed_manifest),
                allow_small=False, replace=False, dry_run=False,
            ),
        ) == 0
        assert signed_doc["specimens"][0]["specimenId"] == "SPEC-0099"
        assert signed_doc["specimens"][0]["citedBy"] == ["F0167-P01"]
        # A later render may wrap the same image in a stable GitHub link.  It must
        # resolve to the existing issue-scoped specimen, not allocate a duplicate.
        wrapped_issue_html = ROOT / ".fetch-attachment-test-wrapped.html"
        wrapped_issue_html.write_text(
            '<a href="https://github.com/user-attachments/assets/ordinary">'
            '<img src="https://cdn.example.test/ordinary.png"></a>'
            '<a href="https://github.com/user-attachments/assets/wrapped">'
            '<img src="https://cdn.example.test/card.png"></a>', encoding="utf-8"
        )
        wrapped_manifest = ROOT / ".fetch-attachment-test-wrapped-manifest.json"
        wrapped_manifest.write_text(json.dumps({"issue": 999, "observations": [{
            "attachmentIndex": 2, "setCode": "JU", "number": "11/64", "variant": "V1",
            "language": "Dutch", "heldBy": "owner", "inspectedFrom": "photo",
            "observed": "positive", "recordedAt": "2026-08-24",
            "physicalObservation": {"finish": "holo", "basis": "observed card surface"},
        }]}), encoding="utf-8")
        assert fetch_attachment.command_issue(
            signed_doc,
            SimpleNamespace(
                issue=999, issue_html=str(wrapped_issue_html), manifest=str(wrapped_manifest),
                allow_small=False, replace=False, dry_run=False,
            ),
        ) == 0
        assert len(signed_doc["specimens"]) == 1
    finally:
        fetch_attachment.SPECIMENS_JSON = original_registry
        fetch_attachment.SPECIMEN_DIR = original_specimen_dir
        fetch_attachment.download_candidates = original_download_candidates
        signed_issue_html.unlink(missing_ok=True)
        signed_manifest.unlink(missing_ok=True)
        (ROOT / ".fetch-attachment-test-wrapped.html").unlink(missing_ok=True)
        (ROOT / ".fetch-attachment-test-wrapped-manifest.json").unlink(missing_ok=True)
        signed_registry.unlink(missing_ok=True)
        (ROOT / "SPEC-0099.png").unlink(missing_ok=True)

    # Replacing a photograph must remove the superseded extension atomically.
    old_photo = ROOT / "SPEC-0001.jpg"
    new_photo = ROOT / "SPEC-0001.png"
    replace_registry = ROOT / ".fetch-attachment-test-replace.json"
    old_photo.write_bytes(b"old image")
    new_photo.write_bytes(b"new image")
    replace_registry.write_text(json.dumps({
        "count": 1,
        "specimens": [{"specimenId": "SPEC-0001", "photograph": old_photo.name}],
    }), encoding="utf-8")
    original_registry = fetch_attachment.SPECIMENS_JSON
    original_specimen_dir = fetch_attachment.SPECIMEN_DIR
    fetch_attachment.SPECIMENS_JSON = replace_registry
    fetch_attachment.SPECIMEN_DIR = ROOT
    try:
        fetch_attachment.commit_import(
            {"count": 1, "specimens": [{"specimenId": "SPEC-0001", "photograph": old_photo.name}]},
            [(new_photo, b"replacement")],
            [{"specimenId": "SPEC-0001", "photograph": new_photo.name}],
        )
        assert not old_photo.exists()
        assert new_photo.read_bytes() == b"replacement"
    finally:
        fetch_attachment.SPECIMENS_JSON = original_registry
        fetch_attachment.SPECIMEN_DIR = original_specimen_dir
        replace_registry.unlink(missing_ok=True)
        old_photo.unlink(missing_ok=True)
        new_photo.unlink(missing_ok=True)

    verify_multiple_views()
    verify_duplicate_photo_batch()
    print("fetch_attachment validation, hash, fallback and multiple-view regressions passed")


if __name__ == "__main__":
    main()
