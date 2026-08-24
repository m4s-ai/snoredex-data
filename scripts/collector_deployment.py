#!/usr/bin/env python3
"""Emit or validate the non-deterministic collector deployment manifest (#254).

This script is intentionally absent from ``scripts/regen.py``. It runs only after
the catalogue's containing commit exists and records the exact published bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOGUE = ROOT / "collector_catalogue.json"
DEFAULT_URL = "https://m4s-ai.github.io/snoredex-data/collector_catalogue.json"
MANIFEST_FIELDS = {
    "schema", "schemaVersion", "catalogueSchemaVersion", "catalogueFingerprint",
    "artifactCommit", "publishedAt", "publishedUrl", "byteDigest", "byteLength",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def valid_timestamp(value: str) -> bool:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return value.endswith("Z") and parsed.tzinfo is not None


def build_manifest(
    catalogue_path: Path, artifact_commit: str, published_at: str, published_url: str
) -> dict[str, Any]:
    catalogue = read_json(catalogue_path)
    return {
        "schema": "snoredex-collector-deployment",
        "schemaVersion": "1.0.0",
        "catalogueSchemaVersion": catalogue["meta"]["schemaVersion"],
        "catalogueFingerprint": catalogue["meta"]["catalogueFingerprint"],
        "artifactCommit": artifact_commit,
        "publishedAt": published_at,
        "publishedUrl": published_url,
        "byteDigest": digest(catalogue_path),
        "byteLength": catalogue_path.stat().st_size,
    }


def validate_manifest(
    manifest: dict[str, Any], catalogue_path: Path, expected_commit: str | None = None
) -> list[str]:
    errors: list[str] = []
    catalogue = read_json(catalogue_path)
    if set(manifest) != MANIFEST_FIELDS:
        errors.append("deployment manifest fields differ from the contract")
    if manifest.get("schema") != "snoredex-collector-deployment" \
            or manifest.get("schemaVersion") != "1.0.0":
        errors.append("unexpected deployment manifest schema")
    commit = manifest.get("artifactCommit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        errors.append("artifactCommit is not a full lowercase Git SHA")
    if expected_commit and commit != expected_commit:
        errors.append("artifactCommit differs from the checked-out publication commit")
    if not valid_timestamp(str(manifest.get("publishedAt") or "")):
        errors.append("publishedAt is not an RFC 3339 UTC timestamp")
    if not str(manifest.get("publishedUrl") or "").startswith("https://"):
        errors.append("publishedUrl is not HTTPS")
    if manifest.get("catalogueSchemaVersion") != catalogue.get("meta", {}).get("schemaVersion"):
        errors.append("catalogue schema version differs")
    if manifest.get("catalogueFingerprint") != catalogue.get("meta", {}).get("catalogueFingerprint"):
        errors.append("catalogue fingerprint differs")
    if manifest.get("byteDigest") != digest(catalogue_path):
        errors.append("catalogue byte digest differs")
    if manifest.get("byteLength") != catalogue_path.stat().st_size:
        errors.append("catalogue byte length differs")
    return errors


def commit_contains_catalogue(commit: str, catalogue_path: Path) -> bool:
    """The deployment identity must name the commit containing these bytes."""
    result = subprocess.run(
        ["git", "show", f"{commit}:collector_catalogue.json"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0 and result.stdout == catalogue_path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--artifact-commit")
    parser.add_argument("--published-at")
    parser.add_argument("--published-url", default=DEFAULT_URL)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            manifest = read_json(args.out)
            errors = validate_manifest(manifest, args.catalogue, args.artifact_commit)
            if errors:
                for error in errors:
                    print(f"deployment manifest: {error}", file=sys.stderr)
                return 1
            print(
                f"collector deployment valid: {manifest['artifactCommit']} "
                f"{manifest['byteDigest']}"
            )
            return 0
        if not args.artifact_commit or not args.published_at:
            parser.error("--artifact-commit and --published-at are required when emitting")
        if not commit_contains_catalogue(args.artifact_commit, args.catalogue):
            print(
                "deployment manifest: artifact commit does not contain the exact catalogue bytes",
                file=sys.stderr,
            )
            return 1
        manifest = build_manifest(
            args.catalogue, args.artifact_commit, args.published_at, args.published_url
        )
        errors = validate_manifest(manifest, args.catalogue, args.artifact_commit)
        if errors:
            raise ValueError("; ".join(errors))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"collector deployment manifest: {args.out}")
        return 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"collector deployment failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
