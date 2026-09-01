#!/usr/bin/env python3
"""Regression tests for the CI-to-Pages gate and artifact handoff contract."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from gate_manifest import build_manifest, manifest_fingerprint, validate_directory, validate_manifest


ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    temp = ROOT / "verification" / "cache" / "gate-handoff-test"
    temp.mkdir(parents=True, exist_ok=True)
    try:
        committed_catalogue = temp / "collector_catalogue.json"
        committed_catalogue.write_bytes(subprocess.check_output(
            ["git", "show", f"{commit}:collector_catalogue.json"], cwd=ROOT,
        ))
        linux = build_manifest(
            commit=commit, gate_level="L4", runner_os="Linux", workflow="test", run_id="test-run",
            generated_at="2026-01-01T00:00:00Z", catalogue=committed_catalogue,
        )
        windows = build_manifest(
            commit=commit, gate_level="L4", runner_os="Windows", workflow="test", run_id="test-run",
            generated_at="2026-01-01T00:00:01Z", catalogue=committed_catalogue,
        )
        assert not validate_manifest(
            linux, catalogue=committed_catalogue, expected_commit=commit, expected_gate="L4"
        )
        (temp / "gate-manifest-Linux.json").write_text(json.dumps(linux), encoding="utf-8")
        (temp / "gate-manifest-Windows.json").write_text(json.dumps(windows), encoding="utf-8")
        assert not validate_directory(
            temp, catalogue=committed_catalogue,
            expected_commit=commit, expected_gate="L4", minimum=2,
        )

        tampered = dict(linux)
        tampered["gateResult"] = "failed"
        assert "gateResult is not passed" in validate_manifest(
            tampered, catalogue=committed_catalogue, expected_commit=commit
        )
        tampered = dict(linux)
        tampered["manifestFingerprint"] = manifest_fingerprint({**tampered, "gateResult": "passed"})
        tampered["catalogueFingerprint"] = "sha256:stale"
        assert "catalogueFingerprint differs from the checked-out catalogue" in validate_manifest(
            tampered, catalogue=committed_catalogue,
            expected_commit=commit, expected_gate="L4"
        )
    finally:
        for path in temp.glob("gate-manifest-*.json"):
            path.unlink(missing_ok=True)
        (temp / "collector_catalogue.json").unlink(missing_ok=True)
        try:
            temp.rmdir()
        except OSError:
            pass
        try:
            temp.parent.rmdir()
        except OSError:
            pass

    release = (ROOT / ".github" / "workflows" / "release-gate.yml").read_text(encoding="utf-8")
    pages = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "push:" in release and "branches: [main]" in release
    assert "github.event_name != 'pull_request'" in release
    assert "matrix:\n        os: [ubuntu-latest, windows-latest]" in release
    assert "runner.os == 'Linux' && github.event_name != 'pull_request'" in release
    assert "post-push" in release and "P6/P7" in release
    assert "verification/gate_manifest.py" in release
    assert "actions/upload-artifact@v4" in release
    assert "name: pages-artifact\n          path: _site\n          include-hidden-files: true" in release
    assert "actions/download-artifact@v4" in pages
    assert "pages-artifact" in pages
    assert "--check-dir" in pages and "--expected-gate L4" in pages
    assert "Regenerate site artifacts" not in pages
    assert "collector_deployment.py" in pages and "publication_gate.py" in pages
    print("gate handoff contract passed: PR=L3, push=P6/P7, Pages=L4 artifact handoff")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
