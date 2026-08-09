#!/usr/bin/env python3
"""Freeze the historical Cardmarket candidate universe, and hold the live stores to it (#133).

This catalogue started from one Cardmarket search captured on 2026-07-21. That capture is good
provenance and a bad boundary: it can tell you whether an inherited claim survives outside
verification, but it can never discover a printing Cardmarket never listed. The missing Traditional
Chinese `svQP F 012/023` is the worked failure case, and #132 is the rebuild.

`legacy-cardmarket-baseline.json` records what that harvest actually contained — which products,
which language units, which excluded code-card claims — so the boundary stays nameable after the
current stores have grown past it.

**The manifest is the candidate universe, not a snapshot of verification.** Only the three stores
that define membership are pinned. Evidence, finish state, owner adjudications and every generated
artifact are deliberately absent: they change on every pass, and a frozen copy of them would be a
second set of counts going stale in public the moment it was written.

Three separate contracts, because they fail for different reasons and one of them needs git:

``manifest_problems()``     the artifact still matches the files at its pinned commit.
``membership_problems()``   every frozen member is still present in the live stores.
``scope_claim_problems()``  no public surface has gone back to claiming global completeness.

The second one is the one that earns the file. Freezing an artifact nothing compares against
produces a museum piece: the manifest stays pristine while the data it describes quietly loses
rows. Membership is a floor, never a ceiling — source-first candidates are expected to arrive, are
counted as additions, and never touch this artifact.

    python scripts/legacy_baseline.py --check

Reconstruction needs full git history, like check `P6`. On a shallow clone that half is skipped
with a note rather than failed; CI checks out with `fetch-depth: 0`, so there it is a real check.

When #134 migrates identities and #140 disposes of legacy rows, a member that legitimately moves
needs a recorded disposition here — a row may be re-keyed, but it may not simply stop existing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "legacy-cardmarket-baseline.json"
SCHEMA_VERSION = "1.0.0"
BASELINE_ID = "cardmarket-search-2026-07-21"
FROZEN_AT = "2026-08-09"

# Set once, after the one-time freeze. Changing the manifest therefore takes a code change as well
# as a data change, and no generator can rewrite the historical boundary as a side effect.
EXPECTED_MANIFEST_SHA256 = "17b43aa7a892431b98baf9aa8b2302681ea44e853e30ec0d2cf509826a99d2d3"

# Only what defines membership. The verification stores are not the candidate universe: pinning
# `evidence.jsonl` or `owner_adjudications.json` here would publish counts that are wrong by the
# next pass — the first draft of this file did, and shipped 12 owner adjudications against a real
# 58.
PINNED_FILES = {
    "snorlax_cards.json": "legacy Cardmarket product store",
    "verification/units.json": "legacy non-code language-unit state store",
    "verification/excluded_codecards.json": "legacy excluded code-card language claims",
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

# A completeness claim is a vocabulary, not two sentences. The first version of this guard held one
# regex per phrase that existed on the day it was written, so #133's "a test fails if an unqualified
# global completeness claim is reintroduced" was really "a test fails if the *old wording* comes
# back" — a reworded claim walked straight through it.
#
# So: match the vocabulary, then require the claim to say what it is complete *of*. Every hit needs
# a scope qualifier in the same block, which is what an honest claim carries anyway.
#
# It matches the shape of a *claim*, not the word. "every" is the working vocabulary of this
# repository — every unit carries evidence, every write pass runs the checks — and a guard that
# fires on the distributive quantifier is a guard that gets muted. What makes a completeness claim
# is the word attached to catalogue scope: a complete catalogue *of*, every Snorlax *product*,
# all localities, nothing open.
COMPLETENESS_VOCABULARY = {
    "complete-catalogue": re.compile(
        r"\b(?:complete|exhaustive)\s+(?:\w+[- ]){0,3}?"
        r"(?:catalogue|catalog|manifest|list|record|dataset|inventory)\b", re.IGNORECASE),
    "every-product": re.compile(
        r"\b(?:(?:catalogue|catalog|list|index|record)\s+of\s+every"
        r"|every\s+Snorlax"
        r"|every\s+known\s+(?:product|printing|release|card)"
        r"|every\s+(?:product|printing|release|card)\s+(?:ever|in\s+existence|worldwide))",
        re.IGNORECASE),
    "all-localities": re.compile(r"\ball\s+(?:localities|locales|markets)\b", re.IGNORECASE),
    "nothing-open": re.compile(r"\b(?:0|zero|no)\s+open\s+(?:items?|claims?|units?)\b",
                               re.IGNORECASE),
}

# Wording that makes a completeness claim honest by naming its boundary.
SCOPE_QUALIFIERS = (
    "legacy", "candidate universe", "all-locality", "cardmarket-derived", "current-known",
    "inherited", "within its scope", "within scope", "frozen", "baseline",
)

# Domain terms that contain the vocabulary and are not global claims. `complete official manifest`
# is rule 4 — a source that states a closed list within its own declared scope — and
# `complete-manifest` is the finish layer's status value for exactly that. Neither says anything
# about the catalogue being finished.
CLAIM_ALLOWLIST = (
    "complete official manifest",
    "complete-manifest",
    "complete manifest",
    "complete list of finishes",
    "complete all-locality",       # only ever appears inside a denial of one
    "complete verification",
)

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


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=ROOT, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False)


def history_available(commit: str) -> bool:
    """Is the pinned commit in this clone?

    A shallow checkout has the tree but not the history, so reconstruction cannot run. That is a
    property of the clone, not a finding about the data — check `P6` has the same shape.
    """
    return bool(commit) and git("cat-file", "-e", f"{commit}^{{commit}}").returncode == 0


def git_bytes(commit: str, relative: str) -> bytes:
    result = git("show", f"{commit}:{relative}")
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"cannot reconstruct {relative} from {commit}: {error}")
    return result.stdout


def json_at(commit: str, relative: str) -> Any:
    return json.loads(git_bytes(commit, relative).decode("utf-8-sig"))


IMAGE_ID = re.compile(r"(?:/|_)(\d+)\.(?:jpe?g|png|webp)$", re.IGNORECASE)


def image_product_id(card: dict[str, Any]) -> int | None:
    """The numeric id Cardmarket puts in a product's image path.

    Derived, not read: it is the image id, and the raw source record is the `productUrl` kept
    beside it. It is unique across all 198 harvested rows, which is what makes it usable as the
    member key; a source-first card from anywhere else has no such id and returns None.
    """
    for field in ("imageUrl", "imageFile"):
        match = IMAGE_ID.search(str(card.get(field) or ""))
        if match:
            return int(match.group(1))
    return None


def card_member(card: dict[str, Any]) -> dict[str, Any]:
    product_id = image_product_id(card)
    if product_id is None:
        raise ValueError(f"no Cardmarket image id on {card.get('productUrl')!r}")
    return {
        "sourceProductId": product_id,
        "sourceRecord": card["productUrl"],
        "name": card["name"],
        "setCode": card["setCode"],
        "number": str(card.get("number") or ""),
        "variant": card.get("variantToken") or "base",
    }


def build_manifest(commit: str) -> dict[str, Any]:
    dataset = json_at(commit, "snorlax_cards.json")
    units = json_at(commit, "verification/units.json")
    excluded = json_at(commit, "verification/excluded_codecards.json")

    cards = sorted((card_member(card) for card in dataset["cards"]),
                   key=lambda item: item["sourceProductId"])
    unit_ids = sorted(unit["unitId"] for unit in units)
    excluded_ids = sorted(unit["unitId"] for unit in excluded)

    files = {}
    for relative, role in PINNED_FILES.items():
        payload = git_bytes(commit, relative)
        files[relative] = {"role": role, "bytes": len(payload), "sha256": sha256(payload)}

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
            "contract": (
                "Membership is a floor, not a ceiling. Every member listed here must still be "
                "present in the current stores; source-first candidates are added to those stores "
                "and never to this artifact."
            ),
            "notRecordedHere": (
                "Verification state — evidence, finishes, owner adjudications — and every "
                "generated artifact are deliberately excluded: they change every pass, and a "
                "frozen copy would publish counts that are wrong by the next one."
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
            "languageUnits": len(unit_ids),
            "excludedCodeCardUnits": len(excluded_ids),
        },
        "files": files,
        "memberKeys": {
            "cards": (
                "sourceProductId is the numeric id in the Cardmarket product image path, derived "
                "rather than read; sourceRecord beside it is the raw productUrl."
            ),
            "languageUnitIds": "unitId in verification/units.json",
            "excludedCodeCardUnitIds": "unitId in verification/excluded_codecards.json",
        },
        "membershipDigests": {
            "cardsSha256": canonical_digest(cards),
            "languageUnitIdsSha256": canonical_digest(unit_ids),
            "excludedCodeCardUnitIdsSha256": canonical_digest(excluded_ids),
        },
        "members": {
            "cards": cards,
            "languageUnitIds": unit_ids,
            "excludedCodeCardUnitIds": excluded_ids,
        },
    }


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def manifest_problems() -> tuple[list[str], bool]:
    """Does the artifact still match the files at its pinned commit?

    Returns the problems and whether reconstruction actually ran. A shallow clone cannot answer
    the question, and saying so is not the same as passing.
    """
    if not MANIFEST_PATH.is_file():
        return ["legacy-cardmarket-baseline.json is missing"], True

    raw = MANIFEST_PATH.read_bytes()
    problems: list[str] = []
    actual_hash = sha256(raw)
    if actual_hash != EXPECTED_MANIFEST_SHA256:
        problems.append(
            f"manifest byte hash changed: expected {EXPECTED_MANIFEST_SHA256}, found {actual_hash}"
        )

    try:
        document = json.loads(raw.decode("utf-8"))
        commit = str(document.get("meta", {}).get("sourceCommit") or "")
    except json.JSONDecodeError as error:
        return problems + [f"manifest is not readable JSON: {error}"], True

    if not history_available(commit):
        return problems, False

    try:
        expected = build_manifest(commit)
    except (KeyError, OSError, TypeError, ValueError) as error:
        return problems + [f"manifest cannot be reconstructed: {error}"], True

    if document != expected:
        problems.append(
            "manifest does not match the files and memberships at its pinned sourceCommit"
        )
    return problems, True


def membership_problems() -> tuple[list[str], dict[str, int]]:
    """Is every frozen member still in the live stores?

    The contract the artifact exists for. Without it the manifest verifies only itself: a pass
    could drop a legacy card and a legacy unit, regenerate everything coherently, and every check
    in the repository would stay green.

    Additions are counted, never faulted — a candidate universe that cannot grow is the problem
    #132 is solving.
    """
    if not MANIFEST_PATH.is_file():
        return ["legacy-cardmarket-baseline.json is missing"], {}

    document = load_manifest()
    members = document["members"]
    problems: list[str] = []

    live_cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    live_card_ids = {i for i in (image_product_id(card) for card in live_cards) if i is not None}
    live_unit_ids = {unit["unitId"] for unit in read_json(ROOT / "verification" / "units.json")}
    live_excluded_ids = {unit["unitId"] for unit
                         in read_json(ROOT / "verification" / "excluded_codecards.json")}

    frozen_card_ids = {card["sourceProductId"] for card in members["cards"]}
    frozen_unit_ids = set(members["languageUnitIds"])
    frozen_excluded_ids = set(members["excludedCodeCardUnitIds"])

    for label, frozen, live in (
        ("legacy card", frozen_card_ids, live_card_ids),
        ("legacy language unit", frozen_unit_ids, live_unit_ids),
        ("legacy excluded code-card unit", frozen_excluded_ids, live_excluded_ids),
    ):
        missing = sorted(frozen - live, key=str)
        if missing:
            shown = ", ".join(str(m) for m in missing[:8])
            more = f" (+{len(missing) - 8} more)" if len(missing) > 8 else ""
            problems.append(
                f"{len(missing)} {label}(s) in the baseline are absent from the live store: "
                f"{shown}{more}"
            )

    counts = {
        "cardsAdded": len(live_card_ids - frozen_card_ids),
        "unitsAdded": len(live_unit_ids - frozen_unit_ids),
        "excludedAdded": len(live_excluded_ids - frozen_excluded_ids),
        "cardsWithoutCardmarketImageId": sum(
            1 for card in live_cards if image_product_id(card) is None),
    }
    return problems, counts


def blocks(text: str) -> list[tuple[int, str]]:
    """Split into paragraph-ish blocks, keeping the line number each one starts on."""
    out: list[tuple[int, str]] = []
    line_no = 1
    for chunk in re.split(r"\n\s*\n", text):
        out.append((line_no, chunk))
        line_no += chunk.count("\n") + 2
    return out


def scope_claim_problems() -> list[str]:
    """Has any surface gone back to claiming completeness without saying completeness of what?"""
    problems: list[str] = []
    texts: dict[str, str] = {}
    for relative in SCOPE_GUARD_FILES:
        path = ROOT / relative
        if not path.is_file():
            problems.append(f"scope-guard file is missing: {relative}")
            continue
        texts[relative] = path.read_text(encoding="utf-8")

    for relative, text in texts.items():
        for start_line, block in blocks(text):
            lowered = block.lower()
            if any(qualifier in lowered for qualifier in SCOPE_QUALIFIERS):
                continue
            for name, pattern in COMPLETENESS_VOCABULARY.items():
                for match in pattern.finditer(block):
                    # Collapsed, because prose wraps: "complete\n  official manifest" is the
                    # allowlisted term and a raw-substring test would miss it.
                    context = " ".join(
                        block[max(0, match.start() - 60):match.end() + 60].lower().split())
                    if any(allowed in context for allowed in CLAIM_ALLOWLIST):
                        continue
                    line = start_line + block.count("\n", 0, match.start())
                    problems.append(
                        f"{relative}:{line} claims completeness ({name}) with no scope qualifier "
                        f"in the same block: {match.group(0)!r}"
                    )

    for relative, marker in REQUIRED_SCOPE_MARKERS.items():
        # Collapsed for the same reason the allowlist is: these markers are prose, and prose wraps.
        if marker.lower() not in " ".join(texts.get(relative, "").split()).lower():
            problems.append(f"{relative} is missing required scope marker {marker!r}")
    return problems


def freeze(commit: str) -> int:
    if MANIFEST_PATH.exists():
        print(f"refusing to overwrite immutable {MANIFEST_PATH.name}", file=sys.stderr)
        return 1
    resolved = git("rev-parse", f"{commit}^{{commit}}")
    if resolved.returncode:
        print(f"cannot resolve {commit}", file=sys.stderr)
        return 1
    sha = resolved.stdout.decode().strip()
    document = build_manifest(sha)
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"froze {document['counts']['singlesCaptured']} cards and "
          f"{document['counts']['languageUnits']} language units from {sha[:12]}")
    print(f"manifest sha256: {sha256(MANIFEST_PATH.read_bytes())}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Legacy candidate-universe contract (#133).")
    parser.add_argument("--freeze", metavar="COMMIT", nargs="?", const="HEAD",
                        help="create the baseline once, from COMMIT (default HEAD)")
    parser.add_argument("--check", action="store_true",
                        help="validate the manifest, its membership contract and scope wording")
    args = parser.parse_args()
    if args.freeze:
        return freeze(args.freeze)

    manifest, reconstructed = manifest_problems()
    membership, added = membership_problems()
    scope = scope_claim_problems()
    problems = manifest + membership + scope

    if problems:
        print("legacy baseline check failed:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    document = load_manifest()
    where = (f"reconstructed from {document['meta']['sourceCommit'][:12]}" if reconstructed
             else "reconstruction skipped — shallow clone, like P6")
    print(f"legacy baseline holds: {document['counts']['singlesCaptured']} cards, "
          f"{document['counts']['languageUnits']} units, all still present ({where})")
    if any(added.values()):
        print(f"  since the freeze: +{added['cardsAdded']} cards, +{added['unitsAdded']} units, "
              f"+{added['excludedAdded']} excluded code-card claims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
