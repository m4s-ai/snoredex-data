#!/usr/bin/env python3
"""Offline checks for the issue-image importer."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "verification"))
import fetch_attachment  # noqa: E402


def expect_failure(callable_: object) -> None:
    try:
        callable_()
    except SystemExit:
        return
    raise AssertionError("expected validation failure")


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

    print("fetch_attachment validation, hash and fallback regressions passed")


if __name__ == "__main__":
    main()
