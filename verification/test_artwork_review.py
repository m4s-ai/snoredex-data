#!/usr/bin/env python3
"""Regression checks for the generated #120 artwork review projection."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import artwork_review  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit(f"[FAIL] artwork review: {message}")


def main() -> int:
    path = ROOT / "verification" / "artwork_review_projection.json"
    if not path.exists():
        fail("projection is missing")
    projection = json.loads(path.read_text(encoding="utf-8"))
    if projection != artwork_review.build():
        fail("projection is stale; run python scripts/artwork_review.py")
    if projection.get("schemaVersion") != "1.0.0" or projection.get("proposalSchemaVersion") != "1.0.0":
        fail("unexpected projection or proposal schema version")

    groups = projection.get("groups") or []
    members = [member for group in groups for member in group.get("members") or []]
    ids = [member.get("cardReleaseId") for member in members]
    if len(ids) != len(set(ids)):
        fail("a card release appears in more than one review group")
    if len(ids) != projection["summary"]["cardReleases"]:
        fail("summary card-release count does not match the projection")
    if sum(len(member.get("physicalPrintings") or []) for member in members) != projection["summary"]["physicalPrintings"]:
        fail("physical-printing accounting drift")

    for member in members:
        if not member.get("cardReleaseId") or not member.get("locality") or not member.get("language"):
            fail(f"incomplete stable identity: {member}")
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
            elif not str(image.get("src", "")).startswith(("http://", "https://")):
                fail(f"external image has no URL: {image.get('src')}")

    print(f"artwork review projection: {len(groups)} groups, {len(members)} releases, "
          f"{projection['summary']['physicalPrintings']} physical printings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
