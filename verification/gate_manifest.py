#!/usr/bin/env python3
"""Create and validate the runtime handoff between CI gates and Pages deployment.

The manifest is deliberately ephemeral. It binds a successful L3/L4 run to the exact commit,
repository tree, and collector catalogue bytes that the workflow checked. It is never a canonical
data store and must not be added to ``scripts/regen.py``'s generated projections.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOGUE = ROOT / "collector_catalogue.json"
SCHEMA = "snoredex-gate-manifest"
VERSION = "1.0.0"
FIELDS = {
    "schema", "schemaVersion", "commit", "gateLevel", "gateResult", "treeFingerprint",
    "catalogueFingerprint", "catalogueDigest", "generatedAt", "workflow", "runId",
    "runnerOS", "manifestFingerprint",
}
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_fingerprint(manifest: dict[str, Any]) -> str:
    unsigned = dict(manifest)
    unsigned.pop("manifestFingerprint", None)
    return sha256_bytes(canonical(unsigned))


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def current_commit(explicit: str | None = None) -> str:
    value = explicit or os.environ.get("GITHUB_SHA") or git("rev-parse", "HEAD").decode().strip()
    if not FULL_SHA.fullmatch(value):
        raise ValueError(f"commit must be a full lowercase Git SHA: {value!r}")
    return value


def tree_fingerprint(commit: str) -> str:
    """Hash Git's sorted tree listing so the handoff is OS-independent."""
    return sha256_bytes(git("ls-tree", "-r", "--full-tree", commit).replace(b"\r\n", b"\n"))


def catalogue_state(path: pathlib.Path) -> tuple[str, str]:
    document = json.loads(path.read_text(encoding="utf-8"))
    fingerprint = document.get("meta", {}).get("catalogueFingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        raise ValueError("collector catalogue has no semantic fingerprint")
    return fingerprint, sha256_bytes(path.read_bytes())


def commit_contains_catalogue(commit: str, path: pathlib.Path) -> bool:
    try:
        return git("show", f"{commit}:collector_catalogue.json") == path.read_bytes()
    except (OSError, subprocess.CalledProcessError):
        return False


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def build_manifest(
    *,
    commit: str | None = None,
    gate_level: str = "L3",
    gate_result: str = "passed",
    catalogue: pathlib.Path = CATALOGUE,
    workflow: str | None = None,
    run_id: str | None = None,
    runner_os: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if gate_level not in {"L3", "L4"}:
        raise ValueError("gate level must be L3 or L4")
    if gate_result != "passed":
        raise ValueError("only a passed gate can be handed to deployment")
    commit = current_commit(commit)
    if not commit_contains_catalogue(commit, catalogue):
        raise ValueError("checked commit does not contain the exact collector catalogue bytes")
    catalogue_fingerprint, catalogue_digest = catalogue_state(catalogue)
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "schemaVersion": VERSION,
        "commit": commit,
        "gateLevel": gate_level,
        "gateResult": gate_result,
        "treeFingerprint": tree_fingerprint(commit),
        "catalogueFingerprint": catalogue_fingerprint,
        "catalogueDigest": catalogue_digest,
        "generatedAt": generated_at or now_utc(),
        "workflow": workflow or os.environ.get("GITHUB_WORKFLOW", "local"),
        "runId": run_id or os.environ.get("GITHUB_RUN_ID", "local"),
        "runnerOS": runner_os or os.environ.get("RUNNER_OS", os.name),
    }
    manifest["manifestFingerprint"] = manifest_fingerprint(manifest)
    return manifest


def validate_manifest(
    manifest: dict[str, Any],
    *,
    catalogue: pathlib.Path = CATALOGUE,
    expected_commit: str | None = None,
    expected_gate: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if set(manifest) != FIELDS:
        errors.append("gate manifest fields differ from the contract")
    if manifest.get("schema") != SCHEMA or manifest.get("schemaVersion") != VERSION:
        errors.append("unexpected gate manifest schema")
    commit = manifest.get("commit")
    if not isinstance(commit, str) or not FULL_SHA.fullmatch(commit):
        errors.append("commit is not a full lowercase Git SHA")
    elif expected_commit and commit != expected_commit:
        errors.append("commit differs from the checked-out publication commit")
    gate = manifest.get("gateLevel")
    if gate not in {"L3", "L4"}:
        errors.append("gateLevel must be L3 or L4")
    elif expected_gate and gate != expected_gate:
        errors.append(f"gateLevel differs from expected {expected_gate}")
    if manifest.get("gateResult") != "passed":
        errors.append("gateResult is not passed")
    if manifest.get("manifestFingerprint") != manifest_fingerprint(manifest):
        errors.append("manifestFingerprint does not match the manifest bytes")
    try:
        actual_commit = current_commit()
        if commit == actual_commit and manifest.get("treeFingerprint") != tree_fingerprint(actual_commit):
            errors.append("treeFingerprint differs from the checked-out commit")
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        errors.append(f"could not verify checked-out tree: {error}")
    try:
        catalogue_fingerprint, catalogue_digest = catalogue_state(catalogue)
        if manifest.get("catalogueFingerprint") != catalogue_fingerprint:
            errors.append("catalogueFingerprint differs from the checked-out catalogue")
        if manifest.get("catalogueDigest") != catalogue_digest:
            errors.append("catalogueDigest differs from the checked-out catalogue")
        if isinstance(commit, str) and FULL_SHA.fullmatch(commit) and not commit_contains_catalogue(commit, catalogue):
            errors.append("checked commit does not contain the exact collector catalogue bytes")
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        errors.append(f"could not verify catalogue: {error}")
    return errors


def validate_directory(
    directory: pathlib.Path,
    *,
    catalogue: pathlib.Path = CATALOGUE,
    expected_commit: str | None = None,
    expected_gate: str | None = None,
    minimum: int = 1,
) -> list[str]:
    paths = sorted(directory.glob("gate-manifest-*.json"))
    errors: list[str] = []
    if len(paths) < minimum:
        return [f"expected at least {minimum} gate manifests, found {len(paths)}"]
    manifests: list[dict[str, Any]] = []
    for path in paths:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{path.name}: cannot read manifest: {error}")
            continue
        errors.extend(f"{path.name}: {error}" for error in validate_manifest(
            manifest, catalogue=catalogue, expected_commit=expected_commit, expected_gate=expected_gate,
        ))
        manifests.append(manifest)
    if manifests:
        for key in ("commit", "gateLevel", "gateResult", "treeFingerprint", "catalogueFingerprint", "catalogueDigest"):
            if len({manifest.get(key) for manifest in manifests}) != 1:
                errors.append(f"gate manifests disagree on {key}")
    return errors


def write(path: pathlib.Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--out", type=pathlib.Path)
    source.add_argument("--check", type=pathlib.Path)
    source.add_argument("--check-dir", type=pathlib.Path)
    parser.add_argument("--catalogue", type=pathlib.Path, default=CATALOGUE)
    parser.add_argument("--commit")
    parser.add_argument("--gate-level", choices=("L3", "L4"), default="L3")
    parser.add_argument("--expected-gate", choices=("L3", "L4"))
    parser.add_argument("--minimum", type=int, default=1)
    args = parser.parse_args()
    try:
        if args.out:
            manifest = build_manifest(
                commit=args.commit, gate_level=args.gate_level, catalogue=args.catalogue,
            )
            write(args.out, manifest)
            print(
                f"gate manifest: commit={manifest['commit']} gate={manifest['gateLevel']} "
                f"result={manifest['gateResult']} tree={manifest['treeFingerprint']} "
                f"catalogue={manifest['catalogueFingerprint']} manifest={args.out}"
            )
            return 0
        if args.check:
            manifest = json.loads(args.check.read_text(encoding="utf-8"))
            errors = validate_manifest(
                manifest, catalogue=args.catalogue, expected_commit=args.commit, expected_gate=args.expected_gate,
            )
            summary = manifest
        else:
            errors = validate_directory(
                args.check_dir, catalogue=args.catalogue, expected_commit=args.commit,
                expected_gate=args.expected_gate, minimum=args.minimum,
            )
            paths = sorted(args.check_dir.glob("gate-manifest-*.json"))
            summary = json.loads(paths[0].read_text(encoding="utf-8")) if paths else {}
        if errors:
            for error in errors:
                print(f"gate manifest: {error}", file=sys.stderr)
            return 1
        print(
            f"gate manifest verified: commit={args.commit or summary.get('commit') or current_commit()} "
            f"gate={args.expected_gate or summary.get('gateLevel') or 'any'} result=passed "
            f"tree={summary.get('treeFingerprint')} catalogue={summary.get('catalogueFingerprint')}"
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"gate manifest failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
