#!/usr/bin/env python3
"""Freeze and verify the historical Cardmarket candidate universe (#133).

The current catalogue started from one Cardmarket search captured on 2026-07-21.  That capture is
useful provenance, but it is not a discovery-complete list of every Snorlax printing in every
locality.  ``legacy-cardmarket-baseline.json`` records exactly what the pre-migration repository
held, including every product and language-unit membership, without adding provenance fields to
the historical state stores themselves.

The baseline is deliberately immutable.  ``--freeze`` is a one-time creation operation and
refuses to overwrite an existing file.  Normal use is read-only:

    python scripts/legacy_baseline.py --check

The check rebuilds the manifest from its pinned Git commit, verifies its exact byte hash, and
guards the live/public surfaces against the unqualified completeness wording that caused #133.
The release gate checks out full history, so the pinned source bytes remain reconstructible after
future source-first candidates are added to the current stores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "legacy-cardmarket-baseline.json"
SCHEMA_VERSION = "1.0.0"
BASELINE_ID = "cardmarket-search-2026-07-21"
FROZEN_AT = "2026-08-09"

# Set after the one-time freeze.  Changing the manifest requires an explicit code review change as
# well as a data change; ordinary generators can never silently rewrite the historical boundary.
EXPECTED_MANIFEST_SHA256 = "17f0c1bcdf24700e94032eaefe605d3eab0658ef30ed1e554fd81c28533eaddb"

PINNED_FILES = {
    "snorlax_cards.json": "legacy Cardmarket product store",
    "verification/units.json": "legacy non-code language-unit state store",
    "verification/excluded_codecards.json": "legacy excluded code-card language claims",
    "verification/evidence.jsonl": "evidence journal at the freeze boundary",
    "verification/finish_units.json": "finish state store at the freeze boundary",
    "verification/owner_adjudications.json": "owner decisions at the freeze boundary",
    "analysis_checklist.json": "generated checklist at the freeze boundary",
    "snoredex.sqlite": "generated application database at the freeze boundary",
    "index.html": "generated public site at the freeze boundary",
}

SCOPE_GUARD_FILES = (
    "CLAUDE.md",
    "HANDOVER.md",
    "README.md",
    "DATABASE.md",
    "verification/RESUME.md",
    "verification/open-items.html",
    "index.html",
    "scripts/readme_stats.py",
    "scripts/site.py",
)

UNQUALIFIED_COMPLETENESS = {
    "complete-every-snorlax": re.compile(
        r"\ba complete catalogue of every\s+(?:<strong>)?Snorlax", re.IGNORECASE
    ),
    "every-cardmarket-product": re.compile(
        r"^\*\*Every Snorlax Pok(?:é|&eacute;)mon TCG product on Cardmarket", re.IGNORECASE | re.MULTILINE
    ),
}

REQUIRED_SCOPE_MARKERS = {
    "CLAUDE.md": "legacy Cardmarket-derived candidate universe",
    "HANDOVER.md": "legacy Cardmarket-derived candidate universe",
    "README.md": "not a complete all-locality catalogue",
    "verification/RESUME.md": "legacy Cardmarket candidate universe",
    "scripts/site.py": "not a complete all-locality catalogue",
    "index.html": "not a complete all-locality catalogue",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(payload)


def git_bytes(commit: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"cannot reconstruct {relative} from {commit}: {error}")
    return result.stdout


def json_at(commit: str, relative: str) -> Any:
    return json.loads(git_bytes(commit, relative).decode("utf-8-sig"))


def source_product_id(card: dict[str, Any]) -> int:
    for field in ("imageUrl", "imageFile"):
        match = re.search(r"(?:/|_)(\d+)\.(?:jpe?g|png|webp)$", str(card.get(field) or ""), re.I)
        if match:
            return int(match.group(1))
    raise ValueError(f"cannot derive Cardmarket product id from {card.get('productUrl')!r}")


def card_member(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "sourceProductId": source_product_id(card),
        "sourceRecord": card["productUrl"],
        "name": card["name"],
        "setCode": card["setCode"],
        "number": str(card.get("number") or ""),
        "variant": card.get("variantToken") or "base",
    }


def unit_member(unit: dict[str, Any]) -> dict[str, Any]:
    return {
        "unitId": unit["unitId"],
        "sourceRecord": unit["cmUrl"],
        "setCode": unit["setCode"],
        "number": str(unit.get("number") or ""),
        "variant": unit.get("variant") or "base",
        "language": unit["language"],
    }


def build_manifest(commit: str) -> dict[str, Any]:
    dataset = json_at(commit, "snorlax_cards.json")
    units = json_at(commit, "verification/units.json")
    excluded = json_at(commit, "verification/excluded_codecards.json")
    finish_doc = json_at(commit, "verification/finish_units.json")
    owner_doc = json_at(commit, "verification/owner_adjudications.json")
    checklist = json_at(commit, "analysis_checklist.json")
    evidence_lines = [
        line for line in git_bytes(commit, "verification/evidence.jsonl").decode("utf-8-sig").splitlines()
        if line.strip()
    ]

    cards = sorted((card_member(card) for card in dataset["cards"]),
                   key=lambda item: item["sourceProductId"])
    language_units = sorted((unit_member(unit) for unit in units), key=lambda item: item["unitId"])
    excluded_units = sorted((unit_member(unit) for unit in excluded), key=lambda item: item["unitId"])
    verification = Counter(unit["status"] for unit in units)

    files = {}
    for relative, role in PINNED_FILES.items():
        payload = git_bytes(commit, relative)
        files[relative] = {"role": role, "bytes": len(payload), "sha256": sha256(payload)}

    members = {
        "cardSourceProductIds": [item["sourceProductId"] for item in cards],
        "languageUnitIds": [item["unitId"] for item in language_units],
        "excludedCodeCardUnitIds": [item["unitId"] for item in excluded_units],
    }
    meta = dataset["meta"]
    return {
        "meta": {
            "schema": "snoredex-legacy-candidate-universe",
            "schemaVersion": SCHEMA_VERSION,
            "baselineId": BASELINE_ID,
            "status": "immutable-legacy-baseline",
            "frozenAt": FROZEN_AT,
            "sourceCommit": commit,
            "scope": (
                "Historical Snorlax candidate universe captured from one Cardmarket search; "
                "not a complete all-locality Pokémon TCG print manifest."
            ),
            "currentCatalogue": (
                "Future source-first candidates belong in the current catalogue and must not "
                "rewrite this baseline."
            ),
        },
        "source": {
            "provider": "Cardmarket",
            "captureType": "historical-marketplace-search",
            "searchUrl": meta["source"],
            "retrieved": meta["retrieved"],
            "query": "snorlax",
        },
        "counts": {
            "marketplaceProductsReturned": meta["totalProductsOnCardmarket"],
            "singlesCaptured": len(cards),
            "nonCardProductsExcluded": meta["nonCardProductsExcluded"],
            "languageUnits": len(language_units),
            "excludedCodeCardUnits": len(excluded_units),
            "confirmedLanguageUnits": verification["confirmed"],
            "contradictedLanguageUnits": verification["contradicted"],
            "pendingLanguageUnits": verification["pending"],
            "manualReviewLanguageUnits": verification["needs-manual-review"],
            "evidenceRecords": len(evidence_lines),
            "finishUnits": len(finish_doc["units"]),
            "ownerAdjudications": len(owner_doc["decisions"]),
            "checklistItems": len(checklist["items"]),
        },
        "files": files,
        "membershipDigests": {
            "cardsSha256": canonical_digest(cards),
            "languageUnitsSha256": canonical_digest(language_units),
            "excludedCodeCardUnitsSha256": canonical_digest(excluded_units),
        },
        "memberKeys": {
            "cards": "Cardmarket numeric source product id derived from the pinned card image",
            "languageUnits": "unitId in the pinned verification/units.json",
            "excludedCodeCardUnits": "unitId in the pinned verification/excluded_codecards.json",
        },
        "members": members,
    }


def manifest_problems() -> list[str]:
    problems: list[str] = []
    if not MANIFEST_PATH.is_file():
        return ["legacy-cardmarket-baseline.json is missing"]
    raw = MANIFEST_PATH.read_bytes()
    actual_hash = sha256(raw)
    if actual_hash != EXPECTED_MANIFEST_SHA256:
        problems.append(
            f"manifest byte hash changed: expected {EXPECTED_MANIFEST_SHA256}, found {actual_hash}"
        )
    try:
        document = json.loads(raw.decode("utf-8"))
        expected = build_manifest(str(document.get("meta", {}).get("sourceCommit") or ""))
    except (json.JSONDecodeError, KeyError, OSError, TypeError, ValueError) as error:
        return problems + [f"manifest cannot be reconstructed: {error}"]
    if document != expected:
        problems.append(
            "manifest does not exactly match the files and memberships at its pinned sourceCommit"
        )
    return problems


def scope_claim_problems() -> list[str]:
    problems: list[str] = []
    texts: dict[str, str] = {}
    for relative in SCOPE_GUARD_FILES:
        path = ROOT / relative
        if not path.is_file():
            problems.append(f"scope-guard file is missing: {relative}")
            continue
        texts[relative] = path.read_text(encoding="utf-8")

    for relative, text in texts.items():
        for name, pattern in UNQUALIFIED_COMPLETENESS.items():
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                problems.append(f"{relative}:{line} reintroduces unqualified claim {name}")

    for relative, marker in REQUIRED_SCOPE_MARKERS.items():
        if marker not in texts.get(relative, ""):
            problems.append(f"{relative} is missing required scope marker {marker!r}")
    return problems


def check() -> list[str]:
    return manifest_problems() + scope_claim_problems()


def freeze() -> int:
    if MANIFEST_PATH.exists():
        print(f"refusing to overwrite immutable {MANIFEST_PATH.name}", file=sys.stderr)
        return 1
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True,
    ).stdout.strip()
    document = build_manifest(commit)
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        f"froze {document['counts']['singlesCaptured']} cards and "
        f"{document['counts']['languageUnits']} language units from {commit[:12]}"
    )
    print(f"manifest sha256: {sha256(MANIFEST_PATH.read_bytes())}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true", help="create the baseline once")
    parser.add_argument("--check", action="store_true", help="validate manifest and scope guards")
    args = parser.parse_args()
    if args.freeze:
        return freeze()
    problems = check()
    if problems:
        print("legacy baseline check failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    document = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    print(
        f"legacy baseline is immutable and reconstructible: "
        f"{document['counts']['singlesCaptured']} cards, "
        f"{document['counts']['languageUnits']} units, "
        f"source {document['meta']['sourceCommit'][:12]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
