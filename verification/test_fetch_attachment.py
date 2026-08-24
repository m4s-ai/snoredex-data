#!/usr/bin/env python3
"""Offline checks for the issue-image importer."""

from __future__ import annotations

import sys
from pathlib import Path

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
            "recordedAt": "2026-08-24", "physicalObservation": {"finish": "holo"},
        }, "SPEC-9999", "SPEC-9999.png", "issue", digest
    )
    assert record["photographSha256"] == digest
    print("fetch_attachment validation, hash and fallback regressions passed")


if __name__ == "__main__":
    main()
