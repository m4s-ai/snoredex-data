#!/usr/bin/env python3
"""Regenerate the generated blocks in README.md and FINDINGS.md from the current data.

The finish coverage table drifted twice by being hand-maintained: it claimed 276 non-holo and
24 both-non-holo-and-holo units while the generated data said 270 and 18, and the wrong numbers
were typed in the same commit that regenerated the data. Prose that restates generated facts
has to be generated, or it will disagree with them again.

The top-level status, badge counts, and finish table all come from the canonical stores. This keeps
the repository's front page honest as verification progresses or publication decisions change.

Blocks are delimited by `<!-- generated:NAME -->` / `<!-- /generated:NAME -->`. Everything between
the markers is replaced; everything outside is left alone. Most blocks live in README.md; the
market split lives in FINDINGS.md, next to the drift tables it belongs with.

    python scripts/readme_stats.py          # rewrite
    python scripts/readme_stats.py --check  # fail if stale, for the release gate
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
README_PATH = ROOT / "README.md"
FINDINGS_PATH = ROOT / "FINDINGS.md"
# The evidence ladder is published in four places and had drifted in all four (#67). Each keeps
# its own framing around the table; the table itself comes from source_registry.json.
# The ladder is generated once, into README.md, and linked from everywhere else. Three synced
# copies needed a writer, a --check mode and a check (E12) to stay honest; one copy needs none.
LADDER_PATHS = (README_PATH,)
ANALYSIS_PATH = ROOT / "analysis_finishes.json"
DATASET_PATH = ROOT / "snorlax_cards.json"
UNITS_PATH = ROOT / "verification" / "units.json"
FINISH_UNITS_PATH = ROOT / "verification" / "finish_units.json"
CHECKLIST_PATH = ROOT / "analysis_checklist.json"
SOURCE_REGISTRY_PATH = ROOT / "verification" / "source_registry.json"
DECISIONS_PATH = ROOT / "publication-decisions.json"


def read_json(path: Path) -> Any:
    # Tolerate historical PowerShell 5.1 BOM output; all active writers now emit UTF-8 no-BOM.
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def finish_coverage_block(counts: dict[str, int], finish_units: list[dict[str, Any]]) -> str:
    reverse_family = sum(
        bool({"reverse-holo", "mirror-holo"} & set(unit["availableFinishes"]))
        for unit in finish_units
    )
    rows = (
        ("Non-Holo", counts["withNonHolo"]),
        ("Holo", counts["withHolo"]),
        ("Reverse Holo family", reverse_family),
        ("Both Non-Holo and Holo", counts["withBothNonHoloAndHolo"]),
    )
    lines = ["| Known available finish | Set-number-language units |", "|---|---:|"]
    lines += [f"| {label} | {value} |" for label, value in rows]
    return "\n".join(lines)


def authority_tiers_block(sources: dict[str, Any]) -> str:
    """The evidence ladder, from the registry that defines it (#67).

    Four documents published this table by hand and all four had drifted. Every one listed a
    "tier 4 — other collector community" that no provider occupies, and none mentioned tier 5,
    which is where the marketplace being checked actually sits. CONTRIBUTING.md ran a different
    ladder again, ranking a photographed specimen *fourth of five* — below an independent database
    — while the registry ranks it first. That is the document the project asks collectors to read
    before sending evidence, and it told them their card in hand was nearly worthless.

    The gap at 4 is deliberate and worth keeping: tiers 1-3 grade external evidence, tier 5 marks
    things that are not evidence at all — the Cardmarket catalogue this project exists to check,
    and attributes carried across from a sibling printing. Numbering them adjacent would imply
    they are the weak end of one scale rather than a different kind of thing.
    """
    # Named providers, not category slugs. "marketplace catalogue" covers both TCGCSV at tier 3 and
    # Cardmarket at tier 5, so a category table reads as though one label holds two ranks; and
    # "non url evidence" hides that tier 1 means a card someone actually inspected.
    by_tier: dict[int, set[str]] = {}
    for provider in sources["providers"]:
        by_tier.setdefault(int(provider["authorityTier"]), set()).add(provider["displayName"])

    lines = ["| Tier | Sources |", "|---|---|"]
    for tier in sorted(by_tier):
        lines.append(f"| {tier} | {' · '.join(sorted(by_tier[tier]))} |")
    lines.append("")
    lines.append(
        f"Tiers {', '.join(str(t) for t in sorted(by_tier) if t < 5)} grade external evidence, "
        f"strongest first. Tier 5 is not a weaker rung: it marks what is **not** external evidence "
        f"— the marketplace catalogue this project exists to check, and attributes carried across "
        f"from a sibling printing of the same card. There is deliberately no tier 4."
    )
    return "\n".join(lines)


def evidence_strength_block(units: list[dict[str, Any]], sources: dict[str, Any]) -> str:
    """How much of the data rests on a single source, and how strong that source is (#65).

    The README used to claim "a single *weaker* source may not [stand alone], and a check enforces
    it". No check enforced that: `E3` requires an uncorroborated claim to be *checkable* or
    *strong*, so a tier-3 source with a URL may carry a claim alone — and hundreds do. Stating the
    stricter rule made the data look better sourced than it is.

    The honest version is a count, so it is generated rather than typed. It is deliberately
    unflattering: corroboration is preferred everywhere in the documentation and is in fact rare,
    and a reader deciding how far to trust `languagesConfirmed` needs that in front of them rather
    than reachable by writing their own query.
    """
    tier = {p["providerId"]: p["authorityTier"] for p in sources["providers"]}
    resolved = [u for u in units if u["status"] in ("confirmed", "contradicted")]
    corroborated = [u for u in resolved if u.get("corroborated")]
    single = [u for u in resolved if not u.get("corroborated")]
    strong = [u for u in single if tier.get(u["providerId"], 99) <= 2]
    weak = [u for u in single if tier.get(u["providerId"], 99) > 2]
    unlinkable = [u for u in single if not u.get("sourceUrl")]

    rows = (
        ("Corroborated by a second provider", len(corroborated)),
        ("Single tier 1-2 source", len(strong)),
        ("Single tier 3 source", len(weak)),
    )
    lines = ["| How the claim is sourced | Resolved claims |", "|---|---:|"]
    lines += [f"| {label} | {value} |" for label, value in rows]
    lines.append("")
    lines.append(
        f"{len(single)} of {len(resolved)} resolved claims rest on one provider. Check `E3` does "
        f"not forbid that: it requires an uncorroborated claim to be **checkable or strong**, so "
        f"a tier-3 page anyone can open may carry one alone, and {len(weak)} do. What it forbids "
        f"is a claim that is neither — all {len(unlinkable)} claims with no URL come from tier 1 "
        f"or 2, where the evidence is the owner's own cards."
    )
    return "\n".join(lines)


def badges_block(dataset: dict[str, Any], checklist: dict[str, Any],
                 decisions: dict[str, Any]) -> str:
    cards = dataset["meta"]["singlesCaptured"]
    items = checklist["meta"]["counts"]["items"]
    publication_approved = decisions.get("sitePublicationApproved") is True
    grants_approved = decisions.get("licenseGrantsApproved") is True
    publication = "approved" if publication_approved else "owner_approval_required"
    publication_color = "2ea44f" if publication_approved else "d97706"
    licence = "grants_in_force" if grants_approved else "grants_not_in_force"
    licence_color = "2ea44f" if grants_approved else "d97706"
    return "\n".join((
        "[![Release gate](https://github.com/m4s-ai/snoredex-data/actions/workflows/"
        "release-gate.yml/badge.svg)](https://github.com/m4s-ai/snoredex-data/actions/"
        "workflows/release-gate.yml)",
        f"[![Cards](https://img.shields.io/badge/cards-{cards}-2563eb)](snorlax_cards.json)",
        f"[![Checklist](https://img.shields.io/badge/checklist-{items}_items-2563eb)]"
        "(analysis_checklist.json)",
        f"[![Publication](https://img.shields.io/badge/publication-{publication}-"
        f"{publication_color})](publication-decisions.json)",
        f"[![Licence](https://img.shields.io/badge/licence-{licence}-{licence_color})]"
        "(LICENSE.md)",
        "[![AI-DECLARATION: copilot](https://img.shields.io/badge/"
        "%E4%B7%BC%20AI--DECLARATION-copilot-fee2e2?labelColor=fee2e2)]"
        "(AI-DECLARATION.md)",
    ))


def current_state_block(dataset: dict[str, Any], units: list[dict[str, Any]],
                        finish_doc: dict[str, Any], checklist: dict[str, Any],
                        sources: dict[str, Any], decisions: dict[str, Any]) -> str:
    meta = dataset["meta"]
    verification = Counter(unit["status"] for unit in units)
    finishes = finish_doc["meta"]["counts"]
    checklist_meta = checklist["meta"]
    checklist_counts = checklist_meta["counts"]
    source_meta = sources["meta"]
    source_counts = source_meta["counts"]
    dates = [
        meta["verification"]["lastUpdated"],
        finish_doc["meta"]["generated"],
        checklist_meta["generated"],
        source_meta["generated"],
    ]
    snapshot = max(dates)
    code_cards = sum(bool(card.get("isCodeCard")) for card in dataset["cards"])
    repository_visibility = decisions.get("repositoryVisibility", "unknown")
    publication_state = (
        "approved by the owner but still requires a manual workflow run"
        if decisions.get("sitePublicationApproved") is True
        else "manual and blocked until every required owner decision is recorded"
    )
    licence_state = (
        "active under the recorded owner approvals"
        if decisions.get("licenseGrantsApproved") is True
        else "inactive pending owner approval and licensor selection"
    )
    lines = [
        f"Status snapshot: **{snapshot}**, after the database review and release-readiness audit "
        "of the current repository state.",
        "",
        "| Area | Current state |",
        "|---|---|",
        f"| Cardmarket catalogue | **{meta['totalProductsOnCardmarket']} products** harvested: "
        f"**{meta['singlesCaptured']} singles** retained and {meta['nonCardProductsExcluded']} "
        f"accessories excluded. {code_cards} retained products are code cards and are explicitly "
        "flagged. |",
        f"| Language verification | **{len(units)} claims**: {verification['confirmed']} externally "
        f"confirmed, {verification['contradicted']} contradicted, "
        f"{verification['needs-manual-review']} awaiting manual review, and "
        f"{verification['pending']} still open. Raw Cardmarket languages remain preserved beside "
        "their verdicts. |",
        f"| Physical checklist | **{checklist_counts['items']} items** across "
        f"{checklist_counts['cards']} cards and {checklist_counts['languages']} languages: "
        f"{checklist_counts['documentedPrintings']} documented printings plus "
        f"{checklist_counts['unresolvedPlaceholders']} explicit unresolved placeholders. |",
        f"| Finish evidence | **{finishes['totalFinishUnits']} card-number × language units**: "
        f"{finishes['withConfirmedFinish']} externally confirmed, "
        f"{finishes['withOnlyMarketplaceClaim']} marketplace-only positives, "
        f"{finishes['pendingFinish']} without positive finish evidence, and "
        f"{finishes['notApplicableFinish']} not applicable. The remaining detail/mapping queue "
        f"contains {finishes['withAnyUnresolvedDetail']} units. |",
        f"| Evidence registry | **{source_counts['providers']} providers**, "
        f"{source_counts['evidenceRecords']} evidence records, "
        f"{source_counts['uniqueUrls']} unique URLs, and "
        f"{source_counts['claimsAttributed']:,} attributed claims. Complete official manifests "
        "and the separate owner-adjudication store records final cross-source absence decisions. |",
        "| Quality gate | Deterministic generators, structural and evidence audits, cross-artifact "
        "consistency checks, and browser regressions run on Ubuntu and Windows for pull requests. |",
        f"| Site and publication | The repository is {repository_visibility}. The interactive site "
        f"is generated and usable locally; Pages deployment is {publication_state}. |",
        "| Licensing | Verbatim PolyForm Noncommercial 1.0.0 and CC BY-NC-SA 4.0 texts are present "
        f"and hash-verified. The intended mixed-work grants are {licence_state}. |",
        "| AI transparency | Development used AI in a human-directed copilot workflow. Scope and "
        "safeguards are declared in [`AI-DECLARATION.md`](AI-DECLARATION.md). |",
    ]
    return "\n".join(lines)


def market_split_block(dataset: dict[str, Any]) -> str:
    """The market distribution, counted rather than typed (#37).

    This line was hand-written prose and went stale when the code-card market value was removed
    (#31): the README claimed a "global code cards" bucket that no longer existed. It is a count
    of a committed field, so it belongs to the generator like every other count in this file.

    Ordered by size so the shape of the catalogue is readable, with ties broken by name to keep
    the output stable.
    """
    counts = Counter(card["market"] for card in dataset["cards"])
    parts = " · ".join(f"{market} {n}" for market, n in
                       sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return f"The market split across all {len(dataset['cards'])}: {parts}."


def replace_block(text: str, name: str, body: str, where: str = "README.md") -> str:
    pattern = re.compile(
        rf"(<!-- generated:{re.escape(name)}[^>]*-->\n).*?(\n<!-- /generated:{re.escape(name)} -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"{where} has no generated:{name} block")
    return pattern.sub(lambda m: m.group(1) + body + m.group(2), text)


def status_block(decisions: dict[str, Any]) -> str:
    """The front-page status callout.

    This was hand-written and went stale twice — once claiming the licence grants were not in
    force after they were, once claiming the repository was private after it was public. A
    prominent claim about the project's legal and publication state is exactly the kind that must
    not be maintained by hand, so it is derived from the decision record like everything else.
    """
    grants = decisions.get("licenseGrantsApproved") is True
    site = decisions.get("sitePublicationApproved") is True
    public = decisions.get("repositoryVisibility") == "public"
    licensor = decisions.get("licensor") or "an unrecorded licensor"
    approved_at = decisions.get("approvedAt") or "an unrecorded date"

    licence = (
        f"The licence grants are **in force**, granted by `{licensor}`."
        if grants
        else "The licence grants are **not yet in force**."
    )
    if site and public:
        publication = (
            f"Publication was approved on {approved_at}: the repository is **public** and the site "
            "may be deployed. Deployment stays a manual workflow run — merging never publishes."
        )
    elif site:
        publication = (
            "Site publication is approved but the repository is **not public**, so the correction "
            "links would 404. Check P8 blocks this."
        )
    else:
        publication = (
            "Publication is a separate decision and is **not yet approved**: GitHub Pages requires "
            "a manual run that the publication gate still blocks."
        )
    return "\n".join([
        "> [!IMPORTANT]",
        f"> {licence} {publication} See",
        "> [`publication-decisions.json`](publication-decisions.json), "
        "[`LICENSE.md`](LICENSE.md), and",
        "> [`verification/history/LAUNCH-RUNBOOK.md`](verification/history/LAUNCH-RUNBOOK.md).",
    ])


def main() -> int:
    counts = read_json(ANALYSIS_PATH)["counts"]
    dataset = read_json(DATASET_PATH)
    units = read_json(UNITS_PATH)
    finish_doc = read_json(FINISH_UNITS_PATH)
    checklist = read_json(CHECKLIST_PATH)
    sources = read_json(SOURCE_REGISTRY_PATH)
    decisions = read_json(DECISIONS_PATH)
    original = README_PATH.read_text(encoding="utf-8")
    updated = replace_block(original, "badges", badges_block(dataset, checklist, decisions))
    updated = replace_block(updated, "status", status_block(decisions))
    updated = replace_block(
        updated,
        "current-state",
        current_state_block(dataset, units, finish_doc, checklist, sources, decisions),
    )
    updated = replace_block(
        updated, "evidence-strength", evidence_strength_block(units, sources)
    )
    updated = replace_block(
        updated, "finish-coverage", finish_coverage_block(counts, finish_doc["units"])
    )

    findings_original = FINDINGS_PATH.read_text(encoding="utf-8")
    findings_updated = replace_block(
        findings_original, "market-split", market_split_block(dataset), "FINDINGS.md"
    )

    # One ladder, four readers. Each document keeps its own surrounding framing — an agent's
    # working rules, a cold-start guide, a contributor's introduction — but the table between the
    # markers is the same generated bytes, so a tier cannot mean one thing in CONTRIBUTING.md and
    # another in the registry (#67).
    ladder = authority_tiers_block(sources)
    documents = [
        (README_PATH, original, replace_block(updated, "authority-tiers", ladder)),
        (FINDINGS_PATH, findings_original, findings_updated),
    ]
    for path in LADDER_PATHS:
        if path == README_PATH:
            continue
        before = path.read_text(encoding="utf-8")
        documents.append((path, before, replace_block(before, "authority-tiers", ladder, path.name)))

    if "--check" in sys.argv:
        stale = [path.name for path, before, after in documents if before != after]
        if stale:
            print(f"{', '.join(stale)} generated blocks are stale; "
                  "run python scripts/readme_stats.py")
            return 1
        print(f"{len(documents)} documents' generated blocks are current")
        return 0

    written = []
    for path, before, after in documents:
        if before != after:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(after)
            written.append(path.name)
    print(f"{', '.join(written)} updated" if written
          else "README.md and FINDINGS.md already current")
    return 0


if __name__ == "__main__":
    sys.exit(main())
