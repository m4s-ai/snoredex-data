#!/usr/bin/env python3
"""Independent database review harness.

Complements `verification/review_integrity.py`. That script validates invariants
*within* each store; this one validates consistency *between* the state stores and
the derived artifacts that consumers and the future public site actually read.

Most checks correspond to a finding in `verification/history/REVIEW-2026-07-25.md`; later checks protect
the release, portability, and transparency contracts added during remediation. Run it after any
write pass, and re-run it to confirm a fix:

    python verification/review_findings.py

Exit code 0 when no FAIL-severity check fires, 1 otherwise. Checks marked INFO
report drift without failing, so legitimate progress does not turn the suite red.

Runs on Python 3.9+ with no third-party dependencies and no network access.
"""

from __future__ import annotations

import json
import hashlib
import importlib.util
import os
import re
import contextlib
import subprocess
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any

from checks import Check, Note, Suite

ROOT = Path(__file__).resolve().parent.parent

FINISHES = ("non-holo", "holo", "reverse-holo", "mirror-holo")
STRENGTH = {"pending": 0, "marketplace-claimed": 1, "owner-attested": 2, "confirmed": 3}

# Words GitHub refuses as issue-form dropdown options, rejecting the entire template. Lower-case;
# compared case-insensitively. Learned from GitHub's own validator, not from any published schema.
RESERVED_DROPDOWN_OPTIONS = {"none"}

# Documentation roles (#100). The stage is the design constraint, not a label: `auto` is paid for
# on every task because CLAUDE.md and AGENTS.md are injected at session start, so only what changes
# behaviour before an agent acts belongs there. Everything else is opened deliberately.
# Files that quote the sensitive-expression patterns themselves, so P4 and P6 would otherwise
# match on the check's own vocabulary. Both paths of the readiness audit are listed on purpose:
# P6 walks *history*, where blobs carry the path the file had at the time, and #102 moved it to
# verification/history/. Rewriting the old path out is what broke P6 in that PR.
SENSITIVE_SCAN_EXEMPT = frozenset({
    "verification/PUBLIC-READINESS-AUDIT.md",          # pre-#102 path, still in history
    "verification/history/PUBLIC-READINESS-AUDIT.md",  # current path
    "verification/review_findings.py",
})

DOC_STAGES = ("auto", "task", "reference", "public", "generated", "history")
DOC_HEADER = re.compile(r"<!--\s*doc:\s*role=(?P<role>[^;]+);\s*stage=(?P<stage>[^\s>]+)\s*-->")

# The check protocol is shared with `review_integrity.py` — one implementation of how a check is
# declared and when the process exits non-zero. The output format below stays this suite's own.
suite = Suite()


def load(rel: str) -> Any:
    with open(ROOT / rel, encoding="utf-8") as handle:
        return json.load(handle)


def documentation_inventory() -> dict[str, dict[str, Any]]:
    """Every tracked markdown document, with the role and stage it declares for itself.

    Two directories are out of scope and stay that way. `LICENSES/` holds verbatim upstream licence
    text — editing it to add a header would make it no longer the licence. `verification/archive/`
    is hashed against MANIFEST.json by check X3, so a header there fails the build.
    """
    inventory: dict[str, dict[str, Any]] = {}
    for path in sorted(ROOT.rglob("*.md")):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(("LICENSES/", "verification/archive/", "_site/", "node_modules/")):
            continue
        text = path.read_text(encoding="utf-8")
        found = DOC_HEADER.search(text)
        inventory[rel] = {
            "text": text,
            "role": found.group("role").strip() if found else None,
            "stage": found.group("stage").strip() if found else None,
        }
    return inventory


def check(check_id: str, title: str, severity: str, ok: bool, detail: str = "") -> None:
    """Declare a finding. Severity INFO reports without ever failing the run."""
    if severity == "INFO":
        suite.note(check_id, title, detail)
    else:
        suite.check(title, ok, detail, ident=check_id)


def norm_number(value: Any) -> str:
    """Canonical collector number. Unnumbered cards are null in some stores and "" in others."""
    return str(value or "")


@contextlib.contextmanager
def guarded(ident: str, label: str):
    """Run one section; a failure inside it becomes a reported check, not a dead run (#82).

    #70 moved the suite out of import time so a crash could not swallow the whole report, and #83
    added the outer catch that renders whatever had run. This is the rest of it: a section that
    raises no longer costs the sections after it.

    A `with` block rather than a function per section, because the sections genuinely share state —
    304 names live in `collect()`, 41 of them read more than 500 lines after assignment — and `with`
    does not open a scope. Extracting functions would mean threading a context object through all of
    it, a large diff on this project's truth test that could not be verified by diffing output. This
    can: when nothing raises, the rendered bytes are unchanged, because a guard emits only on
    failure.

    A later section that depended on the failed one raises `NameError` and is reported the same
    way, which is the honest outcome — it did not run, and it says so — while independent sections
    still report their verdicts.
    """
    try:
        yield
    except Exception as error:  # noqa: BLE001 - the point is that no failure escapes a section
        check(ident, f"Section completed: {label}", "FAIL", False,
              f"{type(error).__name__}: {error}. Checks in this section did not run.")


def collect() -> None:
    """Run every check, appending results to the module-level `suite`.

    This body used to execute at import (#70). That meant a parse or key error in any one
    check's data loading aborted the process before a single result was reported, and that
    importing the module ran the whole suite against the live tree — so no check could be
    exercised against a fixture, and `verification/checks.py` had no tests at all.

    Nothing is reordered. The suites' output order is part of their contract, and this move is
    verified by diffing the rendered output byte for byte against the previous revision.
    """
    # --------------------------------------------------------------------------- #
    # Load stores and derived artifacts
    # --------------------------------------------------------------------------- #

    # Guarded like every other phase, and split in two, because they fail differently (#82 review).
    # Reading a file is all-or-nothing: a missing or unparseable store leaves nothing to check, and
    # every later section will say so. Indexing it is per-row, and a single malformed row must not
    # cost the sections that never touch the index.
    #
    # This was unguarded in the first cut, on the reasoning that a load failure is fatal anyway.
    # It is not: deleting `setCode` from one finish row raised while building `finish_by_key`,
    # before the first guard, and the run reported 0/1 — every verdict lost, which is the exact
    # failure this change exists to prevent.
    with guarded("G0", "loading the committed stores"):
        units = load("verification/units.json")
        finish_doc = load("verification/finish_units.json")
        finish_units = finish_doc["units"]
        dataset = load("snorlax_cards.json")
        cards = dataset["cards"]
        releases = load("analysis_confirmed_releases.json")["variants"]
        bulbapedia_release_dates = load("verification/bulbapedia_release_dates.json")["records"]
        finish_analysis = load("analysis_finishes.json")

    with guarded("G0b", "indexing the finish store"):
        finish_by_id = {unit["finishUnitId"]: unit for unit in finish_units}
        finish_by_key = {
            (unit["setCode"], norm_number(unit["number"]), unit["language"]): unit
            for unit in finish_units
        }


    with guarded("G1", "product view, pending semantics, public prose and AI declaration"):
        # --------------------------------------------------------------------------- #
        # F1 — confirmed printings must stay reachable from a product view
        # --------------------------------------------------------------------------- #

        reachable_printings = {
            printing["printingId"]
            for card in cards
            for row in (card.get("finishAvailability") or {}).get("byLanguage", [])
            for printing in row.get("printings", [])
        }
        confirmed_printings = {
            printing["printingId"]: (unit["setCode"], norm_number(unit["number"]), unit["language"],
                                     printing["finish"])
            for unit in finish_units
            for printing in unit["printings"]
            if printing["verificationStatus"] == "confirmed"
        }
        unreachable = sorted(set(confirmed_printings) - reachable_printings)
        check(
            "F1.1",
            "Every externally confirmed printing is reachable from at least one product view",
            "FAIL",
            not unreachable,
            f"{len(unreachable)} confirmed printings appear in no card view, no chronological row, and no "
            f"generated page. e.g. "
            f"{', '.join(f'{pid} {confirmed_printings[pid]}' for pid in unreachable[:3])}",
        )

        # The projected per-product view may hold less evidence than the store only where it says so.
        # "unmapped" and "other-product" are the two legitimate reasons; anything else is silent loss.
        projection_gaps: list[tuple[str, ...]] = []
        for card in cards:
            for row in (card.get("finishAvailability") or {}).get("byLanguage", []):
                unit = finish_by_id.get(row.get("finishUnitId"))
                if unit is None:
                    continue
                if row.get("unitFinishStatus") != unit["finishStatus"]:
                    projection_gaps.append(
                        (card["setCode"], norm_number(card.get("number")),
                         str(card.get("variantToken")), row["language"],
                         str(row.get("unitFinishStatus")), str(unit["finishStatus"]))
                    )
        check(
            "F1.2",
            "Projected rows carry unit-level finish status verbatim, so projection loses no evidence",
            "FAIL",
            not projection_gaps,
            f"{len(projection_gaps)} projected rows do not reproduce the store's finishStatus. Product "
            f"attribution is necessarily weaker than unit knowledge, so the unit view must travel with it. "
            f"e.g. {projection_gaps[:2]}",
        )

        blind_cells = []
        for row in releases:
            for cell in row.get("finishByLanguage") or []:
                unit = finish_by_key.get(
                    (row["setCode"], norm_number(row.get("number")), cell.get("language"))
                )
                if unit is None or not unit["availableFinishes"]:
                    continue
                if not cell.get("availableFinishes") and not cell.get("unitAvailableFinishes"):
                    blind_cells.append(
                        (row["setCode"], norm_number(row.get("number")), row["variant"],
                         cell["language"], unit["availableFinishes"])
                    )
        check(
            "F1.3",
            "Published table never renders a blind cell where the store holds evidence",
            "FAIL",
            not blind_cells,
            f"{len(blind_cells)} published cells expose neither product-attributed nor unit-level finishes "
            f"while finish_units.json holds positive evidence. e.g. {blind_cells[:3]}",
        )


        # --------------------------------------------------------------------------- #
        # F2 — `pending` must not conflate "no evidence" with "not attributable"
        # --------------------------------------------------------------------------- #

        missing_marker = [
            card["setCode"]
            for card in cards
            for row in (card.get("finishAvailability") or {}).get("byLanguage", [])
            if "productMappingStatus" not in row
        ]
        check(
            "F2.1",
            "Projected finish rows carry productMappingStatus so `pending` is unambiguous",
            "FAIL",
            not missing_marker,
            f"{len(missing_marker)} projected rows omit productMappingStatus. A consumer cannot distinguish "
            f"'no finish evidence exists' from 'evidence exists but is not attributable to this product', "
            f"though README directs consumers to use this view.",
        )


        # --------------------------------------------------------------------------- #
        # F3 — public prose must match generated facts
        # --------------------------------------------------------------------------- #

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        counts = finish_analysis["counts"]
        prose_errors = []
        reverse_family_units = sum(
            bool({"reverse-holo", "mirror-holo"} & set(unit["availableFinishes"]))
            for unit in finish_units
        )
        expected_finish_rows = {
            "Non-Holo": counts["withNonHolo"],
            "Holo": counts["withHolo"],
            "Reverse Holo family": reverse_family_units,
            "Both Non-Holo and Holo": counts["withBothNonHoloAndHolo"],
        }
        for label, expected in expected_finish_rows.items():
            matching = [line for line in readme.splitlines() if line.startswith(f"| {label} |")]
            if len(matching) != 1:
                prose_errors.append(f"README has {len(matching)} rows named '{label}', expected one")
                continue
            stated = matching[0].rstrip("| ").split("|")[-1].strip()
            if stated != str(expected):
                prose_errors.append(f"README '{label}' says {stated}, generated data says {expected}")
        if "| Mirror holo |" in readme or "| Mirror Holo |" in readme:
            prose_errors.append("README exposes Mirror Holo as a separate collector-facing finish")
        check(
            "F3.1",
            "README finish-family table matches the generated finish stores",
            "FAIL",
            not prose_errors,
            "; ".join(prose_errors),
        )

        jtg_english = finish_by_key.get(("JTG", "117", "English"))
        jtg_finishes = sorted(jtg_english["availableFinishes"]) if jtg_english else []
        jtg_prose_wrong = "JTG 117` now explicitly\nshows non-holo, holo," in readme or (
            "shows non-holo, holo, and intricate-tile reverse-holo" in readme.replace("\n", " ")
        )
        check(
            "F3.2",
            "README describes regular JTG 117 as holo + reverse holo only",
            "FAIL",
            not jtg_prose_wrong,
            f"README describes regular JTG 117 as non-holo + holo + reverse holo; the verified model and "
            f"review_integrity.py check 'regular JTG 117 discloses holo + reverse only' both say "
            f"{jtg_finishes}. The non-holo printing belongs to the Prize Pack product, not the regular card.",
        )


        # --------------------------------------------------------------------------- #
        # AI transparency — declaration and README must agree with specification 0.1.2
        # --------------------------------------------------------------------------- #

        ai_declaration_path = ROOT / "AI-DECLARATION.md"
        ai_declaration = (
            ai_declaration_path.read_text(encoding="utf-8") if ai_declaration_path.exists() else ""
        )
        frontmatter_match = re.match(r"\A---\n(.*?)\n---\n", ai_declaration, re.DOTALL)
        allowed_levels = ("none", "hint", "assist", "pair", "copilot", "auto")
        allowed_processes = {"design", "implementation", "testing", "documentation", "review", "deployment"}
        declaration_fields: dict[str, str] = {}
        declared_processes: dict[str, str] = {}
        unknown_frontmatter_fields: list[str] = []
        if frontmatter_match:
            in_processes = False
            for line in frontmatter_match.group(1).splitlines():
                if line == "processes:":
                    declaration_fields["processes"] = ""
                    in_processes = True
                    continue
                process_match = re.fullmatch(r"  ([a-z]+): ([a-z]+)", line)
                if in_processes and process_match:
                    declared_processes[process_match.group(1)] = process_match.group(2)
                    continue
                in_processes = False
                field_match = re.fullmatch(r"([a-z]+): [\"']?([^\"']+)[\"']?", line)
                if field_match:
                    key, value = field_match.groups()
                    declaration_fields[key] = value
                    if key not in {"version", "level"}:
                        unknown_frontmatter_fields.append(key)
                elif line.strip():
                    unknown_frontmatter_fields.append(line.strip())

        global_level = declaration_fields.get("level")
        process_levels_valid = bool(declared_processes) and all(
            process in allowed_processes and level in allowed_levels
            for process, level in declared_processes.items()
        )
        highest_process_level = (
            max(declared_processes.values(), key=allowed_levels.index)
            if process_levels_valid else None
        )
        check(
            "A1",
            "AI-DECLARATION.md conforms to AI-DECLARATION specification 0.1.2",
            "FAIL",
            bool(frontmatter_match)
            and declaration_fields.get("version") == "0.1.2"
            and global_level in allowed_levels
            and process_levels_valid
            and global_level == highest_process_level
            and not unknown_frontmatter_fields
            and "\n## Notes\n" in ai_declaration,
            "The declaration requires version and level fields, recognized process levels, a global level "
            "equal to the highest process level, no extra frontmatter fields, and a ## Notes section.",
        )
        check(
            "A2",
            "README and declaration expose the same copilot-level AI transparency contract",
            "FAIL",
            "](AI-DECLARATION.md)" in readme
            and "AI--DECLARATION-copilot" in readme
            and "https://ai-declaration.md/en/0.1.2/" in ai_declaration,
            "README must link the copilot badge to AI-DECLARATION.md, which must link specification 0.1.2.",
        )


    with guarded("G2", "documented build steps"):
        # --------------------------------------------------------------------------- #
        # B — the documented build is the build that can actually run
        # --------------------------------------------------------------------------- #
        # README and HANDOVER used to present one pipeline starting at `mkunits`, which no clean clone can
        # execute: the harvest reads _chunk1..3.json, which are not in the repository, and `mkunits`
        # rebuilds units.json from scratch and discards the verification state (#28). Following the
        # documented order destroyed data.

        handover = (ROOT / "HANDOVER.md").read_text(encoding="utf-8")

        # Reads inputs that are not in the repository. Historical record, never part of a rebuild.
        HARVEST_STEPS = {"build.ps1", "join.ps1", "getimages.ps1", "finalize.ps1"}
        # Runnable from what is committed. The gate regenerates these and diffs the result.
        LIVE_STEPS = {
            "analyze.py", "finishes.py", "language_status.py", "confirmed_releases.py",
            "source_registry.py", "source_capabilities.py", "checklist.py", "readme_stats.py",
            "open_items.py", "site.py", "editions.py", "publish.py", "legacy_baseline.py",
            "print_identity_dryrun.py",
            "evidence_semantics.py", "set_catalogue_dryrun.py", "source_adapters.py",
            "card_discovery.py",
        }

        # The harvest steps and `mkunits` moved to verification/archive/passes/ once #28 had captured the
        # data flow they encode (#68). They are still documented, so they must still exist and this check
        # must still find them — the point is that a named step is never a dangling reference — but the
        # archive is where a script that must never run belongs, and X3 hash-locks it there.
        ARCHIVED_STEPS = HARVEST_STEPS | {"mkunits.ps1"}
        missing_steps = sorted(
            [f"scripts/{s}" for s in LIVE_STEPS if not (ROOT / "scripts" / s).is_file()]
            + [f"archive/passes/{s}" for s in ARCHIVED_STEPS
               if not (ROOT / "verification" / "archive" / "passes" / s).is_file()]
        )
        # A step that must never run must not sit where the runnable ones do.
        stray_harvest = sorted(s for s in ARCHIVED_STEPS if (ROOT / "scripts" / s).is_file())
        check(
            "B1",
            "Every documented build step exists, and the unrunnable ones live in the archive",
            "FAIL",
            not missing_steps and not stray_harvest,
            f"missing {missing_steps}; still in scripts/ {stray_harvest}",
        )

        # A live step must not depend on an input the harvest was supposed to leave behind.
        absent_inputs = sorted(p.name for p in
                               [ROOT / "_chunk1.json", ROOT / "_cards_stage1.json",
                                ROOT / "_cards_stage2.json", ROOT / "_cards_stage3.json"]
                               if p.exists())
        live_sources = {s: (ROOT / "scripts" / s).read_text(encoding="utf-8") for s in LIVE_STEPS}
        hard_dependents = sorted(
            name for name, body in live_sources.items()
            if re.search(r"_chunk|_cards_stage", body) and "snorlax_cards.json" not in body
        )
        check(
            "B2",
            "No live build step depends on a harvest artifact without a committed fallback",
            "FAIL",
            not hard_dependents,
            f"{hard_dependents} read a stage or chunk file with no fallback to snorlax_cards.json, so a "
            f"clean clone cannot run them"
            + (f" (present here: {absent_inputs})" if absent_inputs else ""),
        )

        # The destructive one must never be presented as part of a rebuild. Checked as prose because that
        # is where the instruction lived, and prose is what a reader follows.
        rebuild_docs = {"README.md": readme, "HANDOVER.md": handover}
        resurrected = [
            name for name, text in rebuild_docs.items()
            if re.search(r"mkunits\s*(->|→)\s*build", text)
        ]
        check(
            "B3",
            "mkunits is not documented as the start of a rebuild",
            "FAIL",
            not resurrected,
            f"{resurrected} present mkunits as a build step. It rebuilds units.json with fresh ids and "
            f"discards the verification state of every unit.",
        )

        check(
            "B4",
            "Docs state that the harvest is not reproducible",
            "FAIL",
            all(re.search(r"not reproducible|nicht reproduzierbar", text) for text in rebuild_docs.values()),
            "README and HANDOVER must both say the harvest cannot be re-run, or the next reader will try.",
        )

    with guarded("G2b", "legacy candidate universe"):
        # --------------------------------------------------------------------------- #
        # B5-B7 — the harvest is a boundary, and the boundary is a contract (#133)
        # --------------------------------------------------------------------------- #
        # The candidate universe was one 2026-07-21 Cardmarket search. Verification can check what
        # that search returned and nothing else, so a closed queue is not a discovered catalogue —
        # the missing Traditional Chinese svQP F 012/023 is the worked case, and #132 is the fix.
        #
        # Loaded by path rather than by prepending scripts/ to sys.path: that directory holds a
        # `database`, a `site` and a `checklist` module, and putting it first shadows names for
        # every import after this one.
        spec = importlib.util.spec_from_file_location(
            "legacy_baseline", ROOT / "scripts" / "legacy_baseline.py")
        legacy_baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy_baseline)

        baseline_problems, reconstructed = legacy_baseline.manifest_problems()
        membership, added = legacy_baseline.membership_problems()
        scope_problems = legacy_baseline.scope_claim_problems()

        # Reconstruction reads git history, which a shallow clone does not have — the same
        # condition P6 reports. A clone that cannot answer the question has not answered it, so it
        # says so rather than passing quietly.
        check(
            "B5",
            "Legacy candidate universe still matches the files at its pinned commit",
            "FAIL" if reconstructed else "INFO",
            not baseline_problems,
            f"baseline problems: {baseline_problems[:4]}" if reconstructed
            else "shallow clone: reconstruction skipped, like P6. git fetch --unshallow to run it.",
        )
        # The one that earns the artifact. Without it the manifest verifies only itself, and a pass
        # could drop a legacy row, regenerate everything coherently and stay green everywhere.
        check(
            "B6",
            "Every frozen legacy member is still present in the live stores",
            "FAIL",
            not membership,
            f"membership problems: {membership[:4]}",
        )
        check(
            "B7",
            "Live and public surfaces qualify the legacy scope",
            "FAIL",
            not scope_problems,
            f"scope problems: {scope_problems[:6]}",
        )
        # Growth is the point of #132, so it is reported and never faulted.
        check(
            "B8",
            "Candidate rows added since the freeze",
            "INFO",
            True,
            f"+{added.get('cardsAdded', 0)} cards, +{added.get('unitsAdded', 0)} language units "
            f"beyond the frozen baseline",
        )

    with guarded("G2c", "print identity dry run"):
        # --------------------------------------------------------------------------- #
        # N1-N3 — claims, card releases and physical printings stay separate (#134/#145)
        # --------------------------------------------------------------------------- #
        # Every legacy/source input first becomes a candidate claim. Positive card-level evidence
        # may establish a language-bearing card release; positive finish evidence may then establish
        # a manufactured physical printing. Contradicted and marketplace-only inputs remain claims.
        # The dry run changes no store, so its useful exit condition is complete accounting plus no
        # claim-to-entity promotion across that boundary.
        dryrun = load("verification/print_identity_dryrun.json")
        cards_doc = load("snorlax_cards.json")
        units_doc = load("verification/units.json")
        finish_doc = load("verification/finish_units.json")
        excluded_doc = load("verification/excluded_codecards.json")
        source_first = load("verification/source_first_prints.json")
        unaccounted = []
        product_dispositions = dryrun["legacyProductDispositions"]
        expected_products = {card["productUrl"] for card in cards_doc["cards"]}
        actual_products = set(product_dispositions)
        if actual_products != expected_products:
            unaccounted.append(
                f"products missing={len(expected_products - actual_products)}, "
                f"extra={len(actual_products - expected_products)}")
        finish_printings = sum(len(unit.get("printings", [])) for unit in finish_doc["units"])
        # #150 added a third physical-claim grain: an identified physical scan. Every specimen that
        # records what it saw is a claim, whether or not it establishes a node.
        specimen_doc_dry = load("verification/specimens.json")
        specimen_observations = {s["specimenId"] for s in specimen_doc_dry["specimens"]
                                 if s.get("physicalObservation")}
        expected_claims = len(units_doc) + len(excluded_doc) + len(source_first["prints"]) \
            + finish_printings + len(specimen_observations)
        claims = dryrun["candidateClaims"]
        claim_ids = [claim["claimId"] for claim in claims]
        if len(claims) != expected_claims or len(set(claim_ids)) != len(claim_ids):
            unaccounted.append(
                f"claims {len(claims)}/{expected_claims}, unique={len(set(claim_ids))}")
        expected_sources = {
            "legacy-language-unit": {unit["unitId"] for unit in units_doc},
            "legacy-code-card-unit": {unit["unitId"] for unit in excluded_doc},
            "source-first-record": {entry["printId"] for entry in source_first["prints"]},
            "finish-printing-record": {
                printing["printingId"]
                for unit in finish_doc["units"]
                for printing in unit.get("printings", [])
            },
            "specimen-observation": specimen_observations,
        }
        actual_sources = {
            kind: {claim["sourceId"] for claim in claims if claim["sourceKind"] == kind}
            for kind in expected_sources
        }
        for kind, expected in expected_sources.items():
            if actual_sources[kind] != expected:
                unaccounted.append(
                    f"{kind} missing={len(expected - actual_sources[kind])}, "
                    f"extra={len(actual_sources[kind] - expected)}")
        blank = sorted(
            claim["claimId"] for claim in claims
            if claim.get("disposition") not in
            ("established-and-mapped", "candidate-needs-evidence",
             "bounded-contradicted", "positively-excluded")
        )
        check(
            "N1",
            "The identity dry run accounts for every legacy and source claim",
            "FAIL",
            not unaccounted and not blank,
            f"unaccounted: {unaccounted}; {len(blank)} claim(s) with no disposition {blank[:5]}",
        )

        claims_by_id = {claim["claimId"]: claim for claim in claims}
        editions_by_id = {edition["setEditionId"]: edition for edition in dryrun["setEditions"]}
        inherited = [release["cardReleaseId"] for release in dryrun["cardReleases"]
                     if not release["localIdentifierKnown"]
                     and (release["localSetCode"] is not None
                          or release["localNumber"] is not None)]
        inherited += [edition["setEditionId"] for edition in dryrun["setEditions"]
                      if not edition["localIdentifierKnown"]
                      and edition["localSetCode"] is not None]
        bad_release_grain = [
            release["cardReleaseId"] for release in dryrun["cardReleases"]
            if release["setEditionId"] not in editions_by_id
            or editions_by_id[release["setEditionId"]]["language"] != release["language"]
            or editions_by_id[release["setEditionId"]]["locality"] != release["locality"]
            or not isinstance(release.get("language"), str)
            or not release.get("language")
            or not isinstance(release.get("script"), str)
            or not release.get("script")
        ]
        illicit_promotions = [
            claim["claimId"] for claim in claims
            if claim.get("materializedTargetId") is not None
            and claim.get("disposition") != "established-and-mapped"
        ]
        ungrounded_releases = [
            release["cardReleaseId"] for release in dryrun["cardReleases"]
            if not release.get("establishingClaimIds")
            or any(claims_by_id[claim_id].get("evidenceStatus") != "confirmed"
                   for claim_id in release["establishingClaimIds"])
            or any(claims_by_id[claim_id].get("materializedTargetId")
                   != release["cardReleaseId"]
                   for claim_id in release["establishingClaimIds"])
        ]
        # Which evidence states may establish a physical printing. `confirmed` is the finish
        # store's verdict; `observed` is #150's — someone looked at the card. They are kept as
        # separate words because they are separate acts, and widening this set is the one edit
        # that would let a weaker claim mint a printing, so it is spelled out rather than implied.
        ESTABLISHING_PHYSICAL_STATES = {"confirmed", "observed"}
        ungrounded_physical = [
            printing["physicalPrintingId"] for printing in dryrun["physicalPrintings"]
            if claims_by_id[printing["establishingClaimId"]].get("evidenceStatus")
            not in ESTABLISHING_PHYSICAL_STATES
        ]
        release_ids = {release["cardReleaseId"] for release in dryrun["cardReleases"]}
        physical_ids = {
            printing["physicalPrintingId"] for printing in dryrun["physicalPrintings"]
        }
        dangling_promotions = [
            claim["claimId"] for claim in claims
            if claim.get("disposition") == "established-and-mapped"
            and claim.get("materializedTargetId") not in
            (release_ids if claim.get("claimKind") == "card-release" else physical_ids)
        ]
        bad_physical_edges = [
            printing["physicalPrintingId"] for printing in dryrun["physicalPrintings"]
            if printing["cardReleaseId"] not in release_ids
            or claims_by_id[printing["establishingClaimId"]].get("materializedTargetId")
            != printing["physicalPrintingId"]
        ]
        materialized_contradicted_only = [
            item["proposedCardReleaseId"]
            for item in dryrun["reports"]["contradictedOnlyCardReleaseProposals"]
            if item["materialized"]
        ]
        identity_errors = (inherited + bad_release_grain + illicit_promotions
                           + dangling_promotions + ungrounded_releases
                           + ungrounded_physical + bad_physical_edges
                           + materialized_contradicted_only
                           + dryrun["reports"]["crossLanguageIdentityMerges"]
                           + [item["legacyProduct"]
                              for item in dryrun["reports"]["unexplainedProductSplits"]])
        check(
            "N2",
            "Claims cannot mint entities or merge languages across the identity boundary",
            "FAIL",
            not identity_errors,
            f"{len(identity_errors)} identity/promotion error(s): "
            f"inherited={inherited[:3]}, release-grain={bad_release_grain[:3]}, "
            f"claim-promotions={illicit_promotions[:3]}, releases={ungrounded_releases[:3]}, "
            f"dangling={dangling_promotions[:3]}, physical={ungrounded_physical[:3]}, "
            f"physical-edges={bad_physical_edges[:3]}, "
            f"contradicted-only={materialized_contradicted_only[:3]}",
        )

        # The discovery queues are findings about the world, not defects in the tree.
        #
        # Named dryrun_counts, not counts: `guarded` is a `with` block and does not open a scope,
        # so a generic name here overwrites the one a later section reads. A bare `counts` shadowed
        # the finish counts and took out the regression guards two sections down.
        dryrun_counts = dryrun["counts"]
        check(
            "N3",
            "Identity dry-run migration queues",
            "INFO",
            True,
            f"{dryrun_counts['candidateClaims']} claims -> "
            f"{dryrun_counts['cardReleaseNodes']} card releases + "
            f"{dryrun_counts['physicalPrintingNodes']} physical printings; "
            f"{dryrun_counts['cardReleaseNodesNeedingLocalIdentifier']} releases need a local "
            f"identifier {dryrun_counts['needsLocalIdentifierByLocality']}; "
            f"{dryrun_counts['contradictedOnlyCardReleaseProposals']} contradicted-only release "
            f"proposals stay candidates; {dryrun_counts['orphanSpecimens']} orphan specimen(s)",
        )

        # N4-N5 — source-first prints admitted on their own evidence (ADR-0001 D1)
        # --------------------------------------------------------------------------- #
        # These are printings Cardmarket never listed, so they have no product row and cannot get
        # one: database.py derives a product id from a Cardmarket image URL. They are keyed by the
        # ADR identity instead, and they are the first rows in this repository that did not come
        # from the harvest.
        admitted = source_first["prints"]

        # What may ground an admitted print. D1 said a physical specimen and nothing else; D5
        # (owner, 2026-08-10) added a tier-1 publisher record, for language and identity only.
        # The two are spelled out as separate words because they are separate acts, and widening
        # this set is the one edit that lets a weaker claim mint a printing.
        #
        # Tier is read from the registry rather than hardcoded, so a provider that is re-graded
        # cannot keep grounding prints on a rank it no longer holds.
        # Named print_ground_registry, not registry: `guarded` is a `with` block and opens no
        # scope, and a later section binds `registry` to the same file. A bare name here would be
        # read by whichever section ran last, which is how the finish counts were clobbered once.
        print_ground_registry = load("verification/source_registry.json")
        tier_by_provider = {
            row["providerId"]: row["authorityTier"]
            for row in print_ground_registry["providers"]
        }
        ungrounded = [
            entry["printId"] for entry in admitted
            if not entry.get("evidence")
            or not entry.get("localSetCode") or not entry.get("localNumber")
            or not (
                entry.get("specimenId")
                or (tier_by_provider.get(entry.get("providerId")) == 1
                    and entry.get("sourceUrl"))
            )
        ]
        check(
            "N4",
            "Every admitted source-first print is grounded and names its own identifiers",
            "FAIL",
            not ungrounded,
            f"{len(ungrounded)} print(s) admitted without evidence, a complete local identifier, "
            f"or a ground — a cited specimen (D1) or a tier-1 publisher record with a URL (D5): "
            f"{ungrounded[:5]}",
        )

        # The other half of I7, on real data rather than on the projection: a printing whose set
        # code the evidence declines to state may not be admitted with one. Two are held for
        # exactly that reason, and holding them is the check passing, not failing.
        guessed = [entry["specimenId"] for entry in source_first["held"]
                   if entry.get("proposedSetCode") and not entry.get("blockedBy")]
        # N17-N18 — what each verdict rests on, inventoried and held (#137)
        # --------------------------------------------------------------------------- #
        # #137 asks for the inventory before the repair: classify every evidence record by
        # granularity, then inventory the verdicts derived from set-level or absence-based logic.
        # `scripts/evidence_semantics.py` produces it and changes nothing.
        #
        # The number that matters is not "confirmations resting on a set release". The step to the
        # card holds when the card is inside the set's numbered run, and also when the cited source
        # carries a closed card list containing it — a Prize Pack article lists the card row beside
        # its language table, and a closed list distributed as a whole reaches the card the same
        # way a numbered run does. The remainder is the finding: a container-level statement about
        # a promo, deck-fixed or secret-numbered card that no list reached.
        #
        # The baseline moved 83 -> 68 when the closed-list rule was added. Re-anchoring downward
        # after tightening a rule is the correct direction; never raise it to silence a rise.
        semantics = load("verification/evidence_semantics.json")
        semantic_counts = semantics["counts"]

        # Low-water marks. Both are queues: a rise means a new verdict was written on evidence
        # that cannot carry it, which is the losing direction. Never raise these to silence a
        # rise — find the pass that wrote the row.
        # Re-anchored 68 -> 56 across three corrections, each lowering a down-is-progress
        # baseline after the queue actually shrank, which is the move that tightens the check:
        #   -3  the report keyed its rarity lookup by (setCode, number) while a unit is keyed by
        #       variant too, so `RR 33 V1` — a Rare, inside the numbered run — read as the `V2`
        #       Promo sharing its collector number. Those rows were never unsound.
        #   -6  Cardmarket's "Ultra Rare" is era-dependent: modern Full Arts are secret, EX-era
        #       `ex` and DP-era LV.X cards are numbered inside the set. The deciding fact is the
        #       set's printed size, which nothing here records, so those rows now report
        #       `needs-set-size` instead of asserting an answer.
        #   -3  the Battle Academy 2020 article carries a half-deck list containing the card; the
        #       rows cited only its language table.
        #  -32  the same miss, at scale: thirty-two rows cited a product or set article whose page
        #       carries a closed card list containing the card, and in most cases the unit's own
        #       evidence already quoted the row. Only `sourceType` — the field this report reads —
        #       named the container alone. Twenty-one are Simplified Chinese set articles, where
        #       the list is the claimed edition's own; eleven are fixed products whose article
        #       states its language editions separately.
        #
        #   -5  the publisher's own Asia card database answers five Thai/Indonesian rows at card
        #       level, replacing a statement about the set with a record of the card.
        #
        #   -4  printed set sizes recorded in the set database (#146) decide the six rows that
        #       Cardmarket's era-dependent "Ultra Rare" could not: two are inside their numbered
        #       run and carry, four are secret-numbered and do not.
        #
        # The baseline tracks the AGGREGATE — rows whose inference does not reach the card, whether
        # because it demonstrably fails or because the report cannot yet say. Two counters for one
        # queue is how a real improvement reads as a loss: resolving an undecidable row into a
        # failing one lowers `needs-set-size` and raises `does-not-carry`, and a gate watching only
        # the second would redden while the queue shrank. That is the shape of gate this repository
        # has already learned to stop building.
        #
        #   -4  eight more printed set sizes, for the sets the queue was still judging by rarity,
        #       plus the guard that makes recording them safe. Three rows carrying the harvest
        #       rarity `Fixed` sit inside their set's main set list — `m2a 136` of 193, `s8b 126`
        #       of 184, `sv4a 145` of 190 — and two Simplified Chinese rows are reached by their
        #       own edition's card list rather than by a denominator. Against that, `RR 33 V2`
        #       returns to the queue: it is the Rival Season promo, and it had left only because a
        #       recorded size was allowed to overrule a distribution rarity. A promo's collector
        #       number is the number of the run card it reprints, so the size now yields to the
        #       exclusion and the three promo rows — `RR 33 V2`, `CL 33 V2`, `FLF 80 V2` — agree
        #       again.
        #
        # The 17 left cite the cross-language expansion index, which carries no card list at all,
        # for cards no locale catalogue here indexes, plus the three promo printings above.
        UNSOUND_SET_LEVEL_BASELINE = 17
        UNSCOPED_ABSENCE_BASELINE = 27
        unsound_now = semantic_counts["setLevelConfirmationsNotReachingTheCard"]
        unscoped_now = semantic_counts["contradictionsByBacking"].get("unscoped-absence", 0)
        check(
            "N17",
            "No new verdict rests on evidence that cannot reach the card",
            "FAIL",
            unsound_now <= UNSOUND_SET_LEVEL_BASELINE
            and unscoped_now <= UNSCOPED_ABSENCE_BASELINE,
            f"set-level confirmations not reaching the card: {unsound_now} "
            f"(baseline {UNSOUND_SET_LEVEL_BASELINE}); unscoped-absence contradictions: "
            f"{unscoped_now} (baseline {UNSCOPED_ABSENCE_BASELINE}). A rise means a pass wrote a "
            f"verdict on set-level or unscoped-absence reasoning.",
        )

        # N19 — one rule over the three queues above (#137)
        # --------------------------------------------------------------------------- #
        # #137 asks for the rules, not only the counts: "define which verdict transitions each
        # granularity may support". Until they were declared they lived in `evidence_semantics.py`'s
        # branching, so a reader could see what the report concluded but not what it was entitled
        # to conclude, and the residue was three ad-hoc counters that no single number covered.
        #
        # `VERDICT_TRANSITIONS` states them and every row is tested against them. This holds the
        # result. It is deliberately a superset of N17: a row can sit outside its granularity
        # without appearing on any one of the three queues, and 22 of the 66 do exactly that.
        #
        # The 66 are not data errors and nothing downgrades them here — the observation stays as
        # recorded and only the inference drawn from it is marked unsupported, which is the split
        # #137 asks for and the disposition #140 acts on.
        #
        #   27  unscoped absence — a contradiction with neither an exhaustive coverage edge nor an
        #       owner adjudication. 26 rest on a market-history article (#84/#88, the owner's call).
        #   14  a granularity that cannot support a confirmation at all — the Prize Pack rows,
        #       whose own evidence says the unit "rests on the owner attestation plus the uniform
        #       per-region Prize Pack distribution the corroborated languages demonstrate". That
        #       names other units as part of the basis, so `sibling-derived` is what they are.
        #
        #       This was 22, and the first reading of it was wrong in a way worth recording. All
        #       22 opened with an owner attestation, so the classifier looked like it was matching
        #       trailing context in every case. It was not: eight `xm2a 136` rows named a *set
        #       release schedule*, which is a fact about the set and not another unit's record, and
        #       those eight were genuinely card-level. The fourteen here name other units. A
        #       pattern being wrong about part of a group is not a reason to move the group.
        #   17  a product-level statement whose step to the card does not hold, the N17 queue.
        BEYOND_GRANULARITY_BASELINE = 58
        beyond_now = semantic_counts["verdictsBeyondTheirGranularity"]
        check(
            "N19",
            "Every verdict sits within what its evidence's granularity may support",
            "FAIL",
            beyond_now <= BEYOND_GRANULARITY_BASELINE,
            f"verdicts beyond their granularity: {beyond_now} "
            f"(baseline {BEYOND_GRANULARITY_BASELINE}) — "
            f"{semantic_counts['verdictsBeyondTheirGranularityByRule']}. A rise means a pass wrote "
            f"a verdict its evidence's granularity does not support.",
        )

        # The two stores that say which providers may carry absence at all must agree. They do
        # today — pokemon-official, elitefourum, play-pokemon — and a silent divergence would let
        # a contradiction claim backing from whichever store was consulted.
        absence_meta = semantics["meta"]["absenceCapableProviders"]
        check(
            "N18",
            "The source registry and the capability graph agree on who may carry absence",
            "FAIL",
            absence_meta["agree"],
            f"source_registry: {absence_meta['sourceRegistry']}; "
            f"capability graph: {absence_meta['capabilityGraph']}",
        )

        # N16 — a contradiction may not deny a printing another store establishes (#137)
        # --------------------------------------------------------------------------- #
        # #137's first named failure: a pass "contradicts a card because a cross-language
        # expansion index has no entry". Five units concluded "no T-Chinese printing of this card
        # should exist" from index silence, while a corroborated Traditional Chinese printing of
        # each sat in source_first_prints.json under its own catch-up code.
        #
        # The verdicts were right about the Japanese slot and wrong in the sentence they wrote, so
        # the repair narrowed the inference rather than flipping the verdict. This keeps the
        # narrowing: a contradiction that denies a card in a language, while an admitted print
        # establishes that card in that language, has to say which of the two it means.
        established_langs = {(p["cardName"], p["language"]) for p in source_first["prints"]}
        counterpart_langs = set()
        for entry in source_first["prints"]:
            catch_up = str(entry.get("catchUpOf") or "")
            match = re.search(r"\b([A-Za-z][A-Za-z0-9-]*)\s+0*(\d+)\b", catch_up)
            if match:
                counterpart_langs.add((match.group(1), str(int(match.group(2))),
                                       entry["language"]))
        CARD_LEVEL_ABSENCE = re.compile(
            r"no [^.]{0,30}printing of this card|this card [^.]{0,25}(?:does not|should not) exist",
            re.IGNORECASE)
        denies = []
        for unit in units:
            if unit["status"] != "contradicted":
                continue
            evidence = unit.get("evidence") or ""
            if not CARD_LEVEL_ABSENCE.search(evidence):
                continue
            number = str(unit.get("number") or "").lstrip("0") or "0"
            if (unit["setCode"], number, unit["language"]) in counterpart_langs \
                    and "SCOPE CORRECTION" not in evidence:
                denies.append(unit["unitId"])
        check(
            "N16",
            "No contradiction denies a printing that an admitted record establishes",
            "FAIL",
            not denies,
            f"{len(denies)} contradiction(s) claim this card has no printing in a language where "
            f"source_first_prints.json establishes one, with no scope correction: {denies[:5]}. "
            f"Narrow the inference to the slot the source covers; do not flip the verdict.",
        )

        # N7 — the migration contract's back-projection rule, enforced rather than asserted
        # --------------------------------------------------------------------------- #
        # print_identity_schema.json states "A back-projection reproduces the legacy/source
        # identifiers and statuses" and nothing checked it. It is the property #140 depends on
        # most: if the graph cannot rebuild the inputs it was built from, the mapping lost
        # something, and the mapping is wrong rather than the old store obsolete.
        source_truth = {
            "legacy-language-unit": {u["unitId"]: u["status"] for u in units_doc},
            "legacy-code-card-unit": {u["unitId"]: None for u in excluded_doc},
            "source-first-record": {e["printId"]: None for e in source_first["prints"]},
            "finish-printing-record": {
                printing["printingId"]: printing.get("verificationStatus")
                for unit in finish_doc["units"] for printing in unit.get("printings", [])
            },
        }
        projected: dict[str, dict[str, Any]] = {}
        for claim in claims:
            projected.setdefault(claim["sourceKind"], {})[claim["sourceId"]] = claim
        projection_faults = []
        for kind, truth in source_truth.items():
            got = projected.get(kind, {})
            missing = sorted(set(truth) - set(got))
            if missing:
                projection_faults.append(f"{kind}: {len(missing)} unreachable e.g. {missing[:3]}")
            drifted = sorted(sid for sid, status in truth.items()
                             if status is not None
                             and got.get(sid, {}).get("evidenceStatus") != status)
            if drifted:
                projection_faults.append(
                    f"{kind}: {len(drifted)} status(es) not reproduced e.g. {drifted[:3]}")
        check(
            "N7",
            "The graph back-projects to every source identifier and status it was built from",
            "FAIL",
            not projection_faults,
            f"{len(projection_faults)} projection fault(s): {projection_faults[:4]}",
        )

        # A printing that rests on a card someone examined must name the card. Without this the
        # highest rung of the ladder becomes the least traceable one, which is the failure
        # `S13`/`S14` already guard for language claims (#150).
        unnamed = [p["physicalPrintingId"] for p in dryrun.get("physicalPrintings", [])
                   if p.get("classificationState") == "classified-from-inspected-specimen"
                   and not (p.get("establishingSpecimenId") and p.get("basis"))]
        by_class = dryrun["counts"].get("physicalPrintingsByEvidenceClass", {})
        check(
            "N6",
            "A specimen-established printing names its specimen and quotes its basis",
            "FAIL",
            not unnamed,
            f"{len(unnamed)} printing(s) claim specimen authority without naming one: "
            f"{unnamed[:5]}. Evidence-class split: {by_class}.",
        )

        check(
            "N5",
            "A held print does not smuggle in the set code its evidence refuses to assert",
            "FAIL",
            not guessed,
            f"{len(guessed)} held entr(ies) carry a set code with no recorded reason it is "
            f"unconfirmed: {guessed[:5]}",
        )

        # N8-N11 — local sets, editions, events, finish profiles and rarity claims (#146)
        # --------------------------------------------------------------------------- #
        # Set discovery has its own immutable provider registry. ADR-0001 is consulted only for
        # already established editions/releases, never to decide whether a provider set exists.
        set_sources = load("verification/set_catalogue_sources.json")
        set_graph = load("verification/set_catalogue_dryrun.json")
        source_rows = set_sources["sourceRecords"]
        graph_sources = set_graph["sourceRecords"]
        source_ids = {row["sourceRecordId"] for row in source_rows}
        graph_source_ids = {row["sourceRecordId"] for row in graph_sources}
        dispositions = set_graph["sourceDispositions"]
        disposition_ids = [row["sourceRecordId"] for row in dispositions]

        legacy_profiles = {
            (card["market"], card["setCode"], card["setName"])
            for card in cards_doc["cards"]
        }
        stored_legacy_profiles = {
            (row["raw"]["market"], row["raw"]["localCode"], row["raw"]["localName"])
            for row in source_rows
            if row["sourceKind"] == "legacy-cardmarket-set-profile"
        }
        source_first_profiles = {
            (entry["locality"], entry["localSetCode"])
            for entry in source_first["prints"]
        }
        stored_source_first = {
            (row["raw"]["locality"], row["raw"]["localCode"])
            for row in source_rows
            if row["sourceKind"] == "source-first-local-set-profile"
        }
        date_rows = load("verification/bulbapedia_release_dates.json")["records"]
        availability_rows = load("verification/rarity_catalogue.json")["editionAvailability"]
        source_accounting_faults = []
        if legacy_profiles != stored_legacy_profiles:
            source_accounting_faults.append(
                f"legacy profiles {len(stored_legacy_profiles)}/{len(legacy_profiles)}")
        if source_first_profiles != stored_source_first:
            source_accounting_faults.append(
                f"source-first profiles {len(stored_source_first)}/{len(source_first_profiles)}")
        if sum(row["sourceKind"] == "release-date-record" for row in source_rows) != len(date_rows):
            source_accounting_faults.append("release-date registry does not match its reviewed seed")
        if sum(row["sourceKind"] == "edition-availability-record" for row in source_rows) \
                != len(availability_rows):
            source_accounting_faults.append("edition-availability registry does not match its seed")
        if source_ids != graph_source_ids or set(disposition_ids) != source_ids \
                or len(disposition_ids) != len(set(disposition_ids)):
            source_accounting_faults.append("source ids do not round-trip through one disposition")
        check(
            "N8",
            "The independent set registry accounts for every seed provider record exactly once",
            "FAIL",
            not source_accounting_faults and set_graph["reports"]["accounting"]["balanced"],
            f"{len(source_accounting_faults)} accounting fault(s): {source_accounting_faults[:5]}",
        )

        local_sets_by_id = {row["localSetId"]: row for row in set_graph["localSets"]}
        set_editions_by_id = {row["setEditionId"]: row for row in set_graph["setEditions"]}
        event_faults = [
            event["releaseEventId"] for event in set_graph["releaseEvents"]
            if event["localSetId"] not in local_sets_by_id
            or not event.get("setEditionIds") or not event.get("marketScopes")
            or not event.get("datePrecision") or not event.get("sourceRecordId")
            or any(edition_id not in set_editions_by_id
                   for edition_id in event.get("setEditionIds", []))
        ]
        edition_faults = [
            edition["setEditionId"] for edition in set_graph["setEditions"]
            if edition["localSetId"] not in local_sets_by_id
            or edition["locality"] != local_sets_by_id[edition["localSetId"]]["locality"]
            or not edition.get("language") or len(edition.get("script", "")) != 4
        ]
        alias_faults = [
            alias["aliasAssertionId"] for alias in set_graph["aliasAssertions"]
            if alias["sourceRecordId"] not in source_ids
            or alias.get("localSetId") not in local_sets_by_id
            or alias.get("reversibleProjection") is not True
            or not alias.get("rawIdentifier")
        ]
        fixture_faults = [fixture["fixtureId"] for fixture in set_graph["fixtures"]
                          if not fixture["passed"]]
        sqlite_faults = set_graph["reports"]["sqliteValidation"]["foreignKeyViolations"]
        check(
            "N9",
            "Set editions, release events and aliases survive the constrained graph round-trip",
            "FAIL",
            not edition_faults and not event_faults and not alias_faults
            and not fixture_faults and sqlite_faults == 0,
            f"edition={edition_faults[:3]}, event={event_faults[:3]}, alias={alias_faults[:3]}, "
            f"fixtures={fixture_faults}, sqlite={sqlite_faults}",
        )

        # Availability may decorate a card release ADR-0001 already established. It cannot invent a
        # collector-number slot, so both reference and projected-finish sets must be strict subsets.
        identity_release_ids = {row["cardReleaseId"] for row in dryrun["cardReleases"]}
        catalogue_release_ids = {row["cardReleaseId"] for row in set_graph["cardReleaseRefs"]}
        profile_release_ids = {
            row["cardReleaseId"] for row in set_graph["profileFinishClaims"]
        }
        minted = sorted(catalogue_release_ids - identity_release_ids)
        unreachable_profile_claims = sorted(profile_release_ids - catalogue_release_ids)
        duplicate_refs = len(catalogue_release_ids) != len(set_graph["cardReleaseRefs"])
        concept_card_claims = [
            assertion["sourceAssertionId"] for assertion in set_graph["sourceAssertions"]
            if assertion.get("assertionKind") in ("asserts-card-release", "confirms-card-from-concept")
        ]
        check(
            "N10",
            "Set availability and set concepts cannot create card-release nodes",
            "FAIL",
            not minted and not unreachable_profile_claims and not duplicate_refs
            and not concept_card_claims,
            f"minted={minted[:3]}, unreachable-profile={unreachable_profile_claims[:3]}, "
            f"duplicateRefs={duplicate_refs}, conceptClaims={concept_card_claims[:3]}",
        )

        source_by_id = {row["sourceRecordId"]: row for row in graph_sources}
        release_ref_by_id = {
            row["cardReleaseId"]: row for row in set_graph["cardReleaseRefs"]
        }
        rarity_faults = []
        for claim in set_graph["rarityClaims"]:
            release = release_ref_by_id.get(claim["cardReleaseId"])
            source = source_by_id.get(claim["sourceRecordId"])
            edition = set_editions_by_id.get(release["setEditionId"]) if release else None
            if not source or not edition or source["raw"].get("locality") != edition["locality"] \
                    or not claim.get("sourceNativeValue") or not claim.get("sourceVocabulary"):
                rarity_faults.append(claim["rarityClaimId"])
        profile_faults = [
            profile["finishProfileId"] for profile in set_graph["finishProfiles"]
            if not profile.get("languageScope") or not profile.get("rules")
            or not profile.get("sourceRecordId")
            or (profile.get("closedWithinScope")
                and not (profile.get("closureScope") and profile.get("closureAuthority")))
        ]
        overclosed = [
            row["profileFinishClaimId"] for row in set_graph["profileFinishClaims"]
            if row.get("closesCompleteFinishList") is not False
        ]
        check(
            "N11",
            "Rarity and finish claims retain source, locality, rule scope and closure precision",
            "FAIL",
            not rarity_faults and not profile_faults and not overclosed,
            f"rarity={rarity_faults[:3]}, profiles={profile_faults[:3]}, "
            f"overclosed={overclosed[:3]}; "
            f"{len(set_graph['reports']['crossLocalityRarityHeld'])} cross-locality rarity "
            f"claim(s) held for a local source",
        )

        # N12-N13 — provider-native catalogue runs remain staging, not verdicts (#147)
        adapter_contract = load("verification/source_adapters.json")
        adapter_stage = load("verification/source_adapter_staging.json")
        adapter_run_id = adapter_stage["meta"]["generatedFromRun"]
        adapter_run_root = ROOT / "verification" / "runs" / "source-adapters" / adapter_run_id
        adapter_manifest = load(
            f"verification/runs/source-adapters/{adapter_run_id}/manifest.json"
        )
        adapter_records_path = ROOT / adapter_stage["recordsPath"]
        adapter_records_bytes = adapter_records_path.read_bytes()
        adapter_records = [
            json.loads(line) for line in adapter_records_bytes.decode("utf-8").splitlines()
            if line.strip()
        ]
        adapter_buckets = Counter(row.get("bucket") for row in adapter_records)
        expected_bucket_counts = {
            "mapped": adapter_stage["meta"]["counts"]["mapped"],
            "new-candidate": adapter_stage["meta"]["counts"]["newCandidate"],
            "ambiguous/needs-evidence":
                adapter_stage["meta"]["counts"]["ambiguousNeedsEvidence"],
            "positively-excluded": adapter_stage["meta"]["counts"]["positivelyExcluded"],
        }
        raw_hash_faults = []
        for request in adapter_manifest["requests"]:
            if request.get("error") is not None:
                raw_hash_faults.append(f"{request['sliceId']}: request error")
                continue
            raw_path = adapter_run_root / request["rawPath"]
            actual = "sha256:" + hashlib.sha256(raw_path.read_bytes()).hexdigest()
            if actual != request["responseHash"]:
                raw_hash_faults.append(f"{request['sliceId']}: response hash")
        slice_accounting_faults = [
            row["sliceId"] for row in adapter_stage["slices"]
            if row["accounting"]["fetched"] != row["accounting"]["accounted"]
            or row["accounting"]["accounted"] != sum(
                row["accounting"][field] for field in (
                    "mapped", "newCandidate", "ambiguousNeedsEvidence", "positivelyExcluded"
                )
            )
        ]
        record_ids = [row["recordId"] for row in adapter_records]
        stable_keys = [row["stableKey"] for row in adapter_records]
        adapter_source = (ROOT / "scripts" / "source_adapters.py").read_text(encoding="utf-8")
        forbidden_seeds = [
            value for value in (
                "snorlax_cards.json", "units.json", "set_catalogue_sources.json",
                "set_catalogue_dryrun.json", "print_identity_dryrun.json",
            )
            if value in adapter_source
        ]
        check(
            "N12",
            "Source-first runs are immutable, exactly accounted and unable to mutate verdicts",
            "FAIL",
            not raw_hash_faults and not slice_accounting_faults and not forbidden_seeds
            and adapter_manifest["status"] == "complete"
            and not adapter_stage["runErrors"]
            and adapter_stage["meta"]["sourceFirst"] is True
            and adapter_stage["meta"]["verdictMutationAllowed"] is False
            and len(record_ids) == len(set(record_ids))
            and len(stable_keys) == len(set(stable_keys))
            and len(adapter_records) == adapter_stage["meta"]["counts"]["records"]
            and "sha256:" + hashlib.sha256(adapter_records_bytes).hexdigest()
                == adapter_stage["recordsHash"]
            and all(adapter_buckets[name] == count
                    for name, count in expected_bucket_counts.items())
            and sum(expected_bucket_counts.values()) == len(adapter_records),
            f"raw={raw_hash_faults[:3]}, accounting={slice_accounting_faults[:3]}, "
            f"forbiddenSeeds={forbidden_seeds}, runErrors={adapter_stage['runErrors'][:3]}",
        )

        required_provenance = set(adapter_contract["rawRecordContract"]["requiredProvenance"])
        provenance_faults = [
            row.get("recordId") for row in adapter_records
            if not required_provenance.issubset(row)
        ]
        preservation_faults = [
            row["recordId"] for row in adapter_records
            if row["raw"]["localCode"] != row["rawProviderId"]
            or row["raw"]["localName"] != row["sourceRecord"].get("name")
            or row["normalizationProposal"]["crossLocaleMerge"] is not False
            or (row["raw"].get("finishProfileText") is not None
                and row["normalizationProposal"]["finishProfile"]["verbatim"]
                != row["raw"]["finishProfileText"])
        ]
        same_id_locales: dict[tuple[str, str], set[str]] = {}
        same_id_keys: dict[tuple[str, str], set[str]] = {}
        for row in adapter_records:
            key = (row["providerId"], str(row["rawProviderId"]))
            same_id_locales.setdefault(key, set()).add(row["rawLocale"])
            same_id_keys.setdefault(key, set()).add(row["stableKey"])
        collapsed_locales = [
            key for key, locales in same_id_locales.items()
            if len(locales) > 1 and len(same_id_keys[key]) < len(locales)
        ]
        gap_text = " ".join(
            f"{row['track']} {row['reason']}" for row in adapter_contract["gaps"]
        ).lower()
        required_gap_terms = ("western", "japanese", "tw", "cn", "kr", "specialist", "non-expansion")
        missing_gap_terms = [term for term in required_gap_terms if term not in gap_text]
        check(
            "N13",
            "Local ids, locale boundaries, finish prose and unresolved catalogue tracks survive",
            "FAIL",
            not provenance_faults and not preservation_faults and not collapsed_locales
            and not missing_gap_terms
            and all(row["terminalState"] in {"complete", "needs-evidence", "blocked-by-source"}
                    for row in adapter_stage["slices"])
            and all(row["terminalState"] in {"needs-evidence", "blocked-by-source"}
                    for row in adapter_stage["gaps"]),
            f"provenance={provenance_faults[:3]}, preservation={preservation_faults[:3]}, "
            f"collapsedLocales={collapsed_locales[:3]}, missingGapTerms={missing_gap_terms}",
        )

        # N14-N15 — card discovery starts outside the candidate store and stops at staging (#136)
        card_contract = load("verification/card_discovery_adapters.json")
        card_stage = load("verification/card_discovery_staging.json")
        card_run_id = card_stage["meta"]["generatedFromRun"]
        card_run_root = ROOT / "verification" / "runs" / "card-discovery" / card_run_id
        card_manifest = load(f"verification/runs/card-discovery/{card_run_id}/manifest.json")
        card_records_path = ROOT / card_stage["recordsPath"]
        card_records_bytes = card_records_path.read_bytes()
        card_records = [
            json.loads(line) for line in card_records_bytes.decode("utf-8").splitlines()
            if line.strip()
        ]
        card_raw_hash_faults = []
        discovered_by_slice = {}
        for request in card_manifest["requests"]:
            discovered = set()
            for response in (
                request["pages"] + request["details"]
                + request.get("sets", []) + request.get("assets", [])
            ):
                raw_path = card_run_root / response["rawPath"]
                actual = "sha256:" + hashlib.sha256(raw_path.read_bytes()).hexdigest()
                if actual != response["responseHash"]:
                    card_raw_hash_faults.append(response["rawPath"])
            for page in request["pages"]:
                discovered.update(page["detailIds"])
            detail_ids = {row["rawProviderId"] for row in request["details"]}
            if discovered != detail_ids:
                card_raw_hash_faults.append(f"{request['sliceId']}: list/detail accounting")
            discovered_by_slice[request["sliceId"]] = discovered
        card_bucket_counts = Counter(row.get("bucket") for row in card_records)
        expected_card_buckets = {
            "matched": card_stage["meta"]["counts"]["matched"],
            "ambiguous": card_stage["meta"]["counts"]["ambiguous"],
            "new-candidate": card_stage["meta"]["counts"]["newCandidate"],
            "positively-excluded": card_stage["meta"]["counts"]["positivelyExcluded"],
            "needs-evidence": card_stage["meta"]["counts"]["needsEvidence"],
        }
        card_slice_faults = [
            row["sliceId"] for row in card_stage["slices"]
            if row["accounting"]["fetched"] != row["accounting"]["accounted"]
            or row["accounting"]["accounted"] != sum(
                row["accounting"][field] for field in (
                    "matched", "ambiguous", "newCandidate", "positivelyExcluded",
                    "needsEvidence",
                )
            )
            or row["accounting"]["fetched"] != len(discovered_by_slice[row["sliceId"]])
        ]
        card_adapters = {row["adapterId"]: row for row in card_contract["adapters"]}
        expected_query_fields = {
            "pokemon-asia-html": {"nameQueries", "cardType", "regulation", "pageParameter"},
            "tcgdex-json": {"nameQueries", "nameFilter", "pagination"},
            "confirmed-source-json": {
                "nameQueries", "retainedUnitIds", "sourceRecord", "pagination",
            },
            "bulbapedia-historical-json": {
                "nameQueries", "retainedUnitIds", "retainedSetNames", "sourceRecord",
                "pageTitle", "revisionId", "languageColumn", "pagination",
            },
            "source-first-print-json": {
                "nameQueries", "retainedPrintIds", "sourceRecord", "pagination",
            },
            "pokemon-official-localized-html": {
                "nameQueries", "nameFilter", "format", "pagination", "cacheKeyParameter",
            },
        }
        query_seed_faults = [
            request["sliceId"] for request in card_manifest["requests"]
            if set(request["queryParameters"]) != expected_query_fields[
                card_adapters[request["adapterId"]].get(
                    "responseFormat", "pokemon-asia-html"
                )
            ]
            or not request["queryParameters"]["nameQueries"]
            or (
                card_adapters[request["adapterId"]].get("responseFormat") == "tcgdex-json"
                and (
                    request["queryParameters"].get("nameFilter") != "strict-equality"
                    or request["queryParameters"].get("pagination")
                        != "disabled-provider-default"
                )
            )
            or (
                card_adapters[request["adapterId"]].get("responseFormat")
                    == "confirmed-source-json"
                and (
                    not request["queryParameters"].get("retainedUnitIds")
                    or request["queryParameters"].get("sourceRecord")
                        != "verification/confirmed_sources.json"
                    or request["queryParameters"].get("pagination")
                        != "exact-reviewed-positive-frontier"
                )
            )
            or (
                card_adapters[request["adapterId"]].get("responseFormat")
                    == "bulbapedia-historical-json"
                and (
                    request["queryParameters"].get("revisionId") != 4567865
                    or request["queryParameters"].get("pagination")
                        != "single-revision-positive-frontier"
                )
            )
            or (
                card_adapters[request["adapterId"]].get("responseFormat")
                    == "pokemon-official-localized-html"
                and (
                    request["queryParameters"].get("nameFilter")
                        != "provider-name-search"
                    or request["queryParameters"].get("format") != "unlimited"
                    or request["queryParameters"].get("pagination")
                        != "single-retained-response-no-archive-closure"
                    or request["queryParameters"].get("cacheKeyParameter")
                        != "snoredexRun"
                )
            )
            or (
                card_adapters[request["adapterId"]].get("responseFormat")
                    == "source-first-print-json"
                and (
                    not request["queryParameters"].get("retainedPrintIds")
                    or request["queryParameters"].get("sourceRecord")
                        != "verification/source_first_prints.json"
                    or request["queryParameters"].get("pagination")
                        != "exact-reviewed-positive-frontier"
                )
            )
        ]
        card_ids = [row["recordId"] for row in card_records]
        card_keys = [row["stableKey"] for row in card_records]
        check(
            "N14",
            "Card discovery retains and accounts for every provider-native record before matching",
            "FAIL",
            not card_raw_hash_faults and not card_slice_faults and not query_seed_faults
            and card_manifest["status"] == "complete"
            and not card_manifest["failures"] and not card_stage["runErrors"]
            and card_stage["meta"]["sourceFirst"] is True
            and card_stage["meta"]["verdictMutationAllowed"] is False
            and len(card_ids) == len(set(card_ids))
            and len(card_keys) == len(set(card_keys))
            and len(card_records) == card_stage["meta"]["counts"]["records"]
            and "sha256:" + hashlib.sha256(card_records_bytes).hexdigest()
                == card_stage["recordsHash"]
            and all(card_bucket_counts[name] == count
                    for name, count in expected_card_buckets.items())
            and sum(expected_card_buckets.values()) == len(card_records),
            f"raw={card_raw_hash_faults[:3]}, accounting={card_slice_faults[:3]}, "
            f"querySeeds={query_seed_faults}, runErrors={card_stage['runErrors'][:3]}",
        )

        required_card_provenance = set(card_contract["rawRecordContract"]["requiredProvenance"])
        card_provenance_faults = [
            row.get("recordId") for row in card_records
            if not required_card_provenance.issubset(row)
        ]
        card_preservation_faults = [
            row["recordId"] for row in card_records
            if row["raw"]["localName"] != row["sourceRecord"].get("localName")
            or row["raw"]["rawSetCode"] != row["sourceRecord"].get("rawSetCode")
            or row["raw"]["localCollectorNumber"]
                != row["sourceRecord"].get("localCollectorNumber")
            or row["normalizationProposal"]["destructiveMergeAllowed"] is not False
            or row["normalizationProposal"]["verdictMutationAllowed"] is not False
        ]
        svqp_rows = [
            row for row in card_records
            if row["rawLocale"] == "tw" and row["rawProviderId"] == "13148"
        ]
        svqp_ok = len(svqp_rows) == 1 and (
            svqp_rows[0]["bucket"] == "new-candidate"
            and svqp_rows[0]["raw"]["rawSetCode"] == "SVQP"
            and svqp_rows[0]["raw"]["localCollectorNumber"] == "012/023"
            and svqp_rows[0]["normalizationProposal"]["assertedLocalSetCode"] == "svQP F"
            and svqp_rows[0]["normalizationProposal"]["targetCardReleaseId"] is None
        )
        munchlax_faults = [
            row["recordId"] for row in card_records
            if row["raw"]["localName"].startswith("小卡比獸")
            and row["bucket"] != "positively-excluded"
        ]
        pocket_rows = [
            row for row in card_records
            if row["sourceRecord"].get("productScope") == "digital-pocket"
        ]
        pocket_faults = [
            row["recordId"] for row in pocket_rows
            if row["bucket"] != "positively-excluded"
            or row["sourceRecord"].get("setSeries", {}).get("id") != "tcgp"
            or not row.get("setResponseHash")
        ]
        western_locale_expectations = {
            "fr": ("French", "Ronflex", 38, 34),
            "de": ("German", "Relaxo", 40, 36),
            "es": ("Spanish", "Snorlax", 29, 25),
        }
        western_locale_faults = []
        for locale, (language, local_name, total, physical_total) in (
            western_locale_expectations.items()
        ):
            rows = [
                row for row in card_records
                if row["providerId"] == "tcgdex" and row["rawLocale"] == locale
            ]
            physical = [
                row for row in rows
                if row["sourceRecord"].get("productScope") == "physical-tcg"
            ]
            excluded = [row for row in rows if row["bucket"] == "positively-excluded"]
            if (
                len(rows) != total or len(physical) != physical_total or len(excluded) != 4
                or any(row["raw"].get("localName") != local_name for row in rows)
                or any(not row["sourceRecord"].get("setName") for row in rows)
                or any(
                    set(row["sourceRecord"].get("providerRecord", {}).get("legal", {}))
                    != {"standard", "expanded"}
                    for row in rows
                )
                or any(row["bucket"] != "matched" for row in physical)
                or any(
                    not (row["normalizationProposal"].get("targetCardReleaseId") or "").startswith(
                        f"RELEASE:WEST:{language}:"
                    )
                    for row in physical
                )
                or any(
                    not row["sourceUrl"].startswith(
                        f"https://api.tcgdex.net/v2/{locale}/cards/"
                    )
                    for row in rows
                )
            ):
                western_locale_faults.append(locale)
        spanish_targets = [
            row["normalizationProposal"].get("targetCardReleaseId") or ""
            for row in card_records
            if row["providerId"] == "tcgdex" and row["rawLocale"] == "es"
        ]
        if any("LATAM" in target for target in spanish_targets):
            western_locale_faults.append("es-cross-locality")
        expected_tg10 = {
            "fr": ("Origine Perdue Galerie de Dresseurs", "Ronflement Retentissant"),
            "de": ("Verlorener Ursprung Trainer-Galerie", "Dumpfes Geschnarche"),
            "es": ("Origen Perdido Galería de Entrenador", "Ronquido Descomunal"),
        }
        tg10_rows = {
            row["rawLocale"]: row for row in card_records
            if row["rawProviderId"] == "swsh11.5tg-TG10"
            and row["rawLocale"] in expected_tg10
        }
        if {
            locale: (
                row["sourceRecord"].get("setName"),
                (row["sourceRecord"].get("providerRecord", {}).get("attacks") or [{}])[0]
                    .get("name"),
            )
            for locale, row in tg10_rows.items()
        } != expected_tg10:
            western_locale_faults.append("localized-tg10")
        western_archive_gaps = {
            row["gapId"]: row for row in card_contract["gaps"]
            if row["gapId"] in {
                "official-french-card-archive",
                "official-german-card-archive",
                "official-european-spanish-card-archive",
            }
        }
        if len(western_archive_gaps) != 3 or any(
            row["terminalState"] != "needs-evidence"
            for row in western_archive_gaps.values()
        ):
            western_locale_faults.append("official-archive-gaps")
        portuguese_faults = []
        pt_rows = [
            row for row in card_records
            if row["providerId"] == "tcgdex" and row["rawLocale"] == "pt"
        ]
        if (
            len(pt_rows) != 26
            or any(row["bucket"] != "needs-evidence" for row in pt_rows)
            or any(row.get("localityEvidenceMode") != "unqualified-language"
                   for row in pt_rows)
            or any(row["normalizationProposal"].get("targetCardReleaseId") is not None
                   for row in pt_rows)
            or any(row["normalizationProposal"].get("localityEvidenceMode")
                   != "unqualified-language" for row in pt_rows)
        ):
            portuguese_faults.append("unqualified-pt")
        liga_rows = [
            row for row in card_records if row["providerId"] == "ligapokemon"
        ]
        expected_liga_identity = {
            ("U0192", "PPPS8", "117b"),
            ("U0219", "PPPS8", "117b"),
            ("U0329", "PPPS7", "117"),
        }
        if (
            {(row["rawProviderId"], row["raw"]["rawSetCode"],
              row["raw"]["localCollectorNumber"]) for row in liga_rows}
                != expected_liga_identity
            or any(row["bucket"] != "needs-evidence" for row in liga_rows)
            or any(row.get("localityEvidenceMode") != "market-only" for row in liga_rows)
            or any(row["normalizationProposal"].get("targetCardReleaseId") is not None
                   for row in liga_rows)
            or any(row["locality"] != "LATAM" for row in liga_rows)
            or any(not row["sourceUrl"].startswith("https://www.ligapokemon.com.br/")
                   for row in liga_rows)
        ):
            portuguese_faults.append("brazilian-positive-frontier")
        portuguese_gaps = {
            row["gapId"]: row for row in card_contract["gaps"]
            if row["gapId"] in {
                "official-portuguese-physical-locality",
                "official-brazilian-card-archive",
            }
        }
        if (
            len(portuguese_gaps) != 2
            or any(row["terminalState"] != "needs-evidence"
                   for row in portuguese_gaps.values())
            or "localityDeltas" not in card_stage["diff"]
            or "localityDeltas" not in card_stage["diff"]["counts"]
        ):
            portuguese_faults.append("locality-gaps-or-delta")
        italian_rows = [
            row for row in card_records
            if row["providerId"] == "pokemon-official" and row["rawLocale"] == "it"
        ]
        expected_italian_ids = {
            "svp/51", "svp/122", "svp/184", "smp/SM169",
            "swshp/SWSH032", "swshp/SWSH068", "swshp/SWSH119", "xy0/26",
            "swsh1/140", "swsh1/141", "swsh1/142", "swsh1/197",
        }
        italian_faults = [
            row["recordId"] for row in italian_rows
            if row["bucket"] != "matched"
            or row["sourceRecord"].get("recordSource")
                != "localized-archive-list-entry"
            or not row["sourceRecord"].get("detailPath", "").startswith(
                "/it/gcc/archivio-carte/series/"
            )
            or "cms2-it-it/img/cards/" not in row["raw"].get("cardImageUrl", "")
            or row["detailResponseHash"] not in row["listResponseHashes"]
        ]
        italian_gap = next(
            (row for row in card_contract["gaps"]
             if row["gapId"] == "official-italian-archive-filter-coverage"),
            None,
        )
        italian_slice_ok = (
            {row["rawProviderId"] for row in italian_rows} == expected_italian_ids
            and not italian_faults
            and all(row["rawProviderId"] != "pl2/111" for row in italian_rows)
            and italian_gap is not None
            and "pl2/111" in italian_gap["reason"]
            and italian_gap["terminalState"] == "needs-evidence"
        )
        card_gap_text = " ".join(
            f"{row['track']} {row['reason']}" for row in card_contract["gaps"]
        ).lower()
        required_card_gaps = ("japanese", "indonesian", "thai", "korean", "simplified-chinese",
                              "western", "latam", "specialist")
        missing_card_gaps = [term for term in required_card_gaps if term not in card_gap_text]
        card_source = (ROOT / "scripts" / "card_discovery.py").read_text(encoding="utf-8")
        check(
            "N15",
            "Local card identifiers, unmatched queues, failure states and non-destructive proposals survive",
            "FAIL",
            not card_provenance_faults and not card_preservation_faults
            and svqp_ok and not munchlax_faults and pocket_rows and not pocket_faults
            and not western_locale_faults and not portuguese_faults and italian_slice_ok
            and not missing_card_gaps
            and "--resume" in card_source and "source-failed" in card_source
            and all(row["terminalState"] in {"complete", "needs-evidence", "blocked-by-source"}
                    for row in card_stage["slices"])
            and all(row["terminalState"] in {"needs-evidence", "blocked-by-source"}
                    for row in card_stage["gaps"]),
            f"provenance={card_provenance_faults[:3]}, preservation={card_preservation_faults[:3]}, "
            f"svqp={svqp_ok}, munchlax={munchlax_faults[:3]}, "
            f"pocket={pocket_faults[:3] if pocket_rows else ['missing-positive-exclusion']}, "
            f"westernLocales={western_locale_faults[:3]}, "
            f"portuguese={portuguese_faults[:3]}, "
            f"italian={italian_faults[:3] if italian_rows else ['missing-positive-slice']}, "
            f"missingGaps={missing_card_gaps}",
        )

    with guarded("G3", "image formats"):
        # --------------------------------------------------------------------------- #
        # M — every referenced image is the format its name claims, and decodes
        # --------------------------------------------------------------------------- #
        # R5 pairs references with filenames. That cannot see inside a file, so an HTML error page, a
        # truncated download or a PNG called .jpg all passed it (#34). These read the bytes.
        #
        # Structural rather than pixel-accurate, and stdlib-only on purpose: a decoder would be a new
        # dependency in the release gate to prove a property the container already states. Truncation is
        # what actually happens to a downloaded file, and both formats mark their own end.

        IMAGE_MAGIC = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpg"}


        def image_format(data: bytes) -> str | None:
            return next((ext for sig, ext in IMAGE_MAGIC.items() if data.startswith(sig)), None)


        def image_complete(data: bytes, ext: str) -> bool:
            """Whether the file carries its own end marker, which a truncated download does not."""
            if ext == "png":
                return data.rstrip().endswith(b"IEND\xaeB`\x82")
            return data.rstrip().endswith(b"\xff\xd9")


        def image_size(data: bytes, ext: str) -> tuple[int, int] | None:
            """Dimensions from the header. None when the header is not where it should be."""
            if ext == "png":
                if len(data) < 24 or data[12:16] != b"IHDR":
                    return None
                return (int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big"))
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    return (int.from_bytes(data[i + 7:i + 9], "big"),
                            int.from_bytes(data[i + 5:i + 7], "big"))
                i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
            return None


        image_dir = ROOT / "images"
        mislabelled, unreadable, truncated, degenerate = [], [], [], []
        for image in sorted(image_dir.iterdir()) if image_dir.is_dir() else []:
            if not image.is_file():
                continue
            blob = image.read_bytes()
            actual = image_format(blob)
            if actual is None:
                unreadable.append(f"{image.name} ({len(blob)} bytes)")
                continue
            if image.suffix.lstrip(".").lower() != actual:
                mislabelled.append(f"{image.name} is {actual}")
            if not image_complete(blob, actual):
                truncated.append(image.name)
            size = image_size(blob, actual)
            if size is None or min(size) < 2:
                degenerate.append(f"{image.name} {size}")

        check(
            "M1",
            "Every image file is a decodable image",
            "FAIL",
            not unreadable,
            f"{len(unreadable)} files under images/ are not JPEG or PNG — an HTML error page or an empty "
            f"download looks exactly like this. e.g. {unreadable[:5]}",
        )
        check(
            "M2",
            "File extension matches the actual format",
            "FAIL",
            not mislabelled,
            f"{len(mislabelled)} images are served under the wrong extension. e.g. {mislabelled[:5]}",
        )
        check(
            "M3",
            "No image is truncated",
            "FAIL",
            not truncated,
            f"{len(truncated)} images lack their format's end marker, so the download did not finish. "
            f"e.g. {truncated[:5]}",
        )
        check(
            "M4",
            "Every image reports usable dimensions",
            "FAIL",
            not degenerate,
            f"{len(degenerate)} images have an unreadable or degenerate header. e.g. {degenerate[:5]}",
        )

    with guarded("G4", "evidence identity and documented policy"):
        # --------------------------------------------------------------------------- #
        # E — evidence identity is queryable, and the documented policy is the real one
        # --------------------------------------------------------------------------- #
        # `sourceUrl` used to hold either a URL or a sentence, and whether a second source agreed was
        # buried in prose. `providerId`, `sourceRef` and `corroborated` make all three queryable (#32).

        registry = load("verification/source_registry.json")
        provider_by_id = {p["providerId"]: p for p in registry["providers"]}
        resolved_units = [u for u in units if u["status"] in ("confirmed", "contradicted")]

        prose_urls = [u["unitId"] for u in resolved_units
                      if u.get("sourceUrl") and not str(u["sourceUrl"]).startswith("http")]
        check(
            "E1",
            "sourceUrl holds a URL or nothing, never prose",
            "FAIL",
            not prose_urls,
            f"{len(prose_urls)} resolved units describe their source in the URL field. e.g. {prose_urls[:5]}",
        )

        undeclared = [u["unitId"] for u in resolved_units
                      if u.get("providerId") not in provider_by_id]
        check(
            "E2",
            "Every resolved unit names a declared provider",
            "FAIL",
            not undeclared,
            f"{len(undeclared)} units carry no providerId or one absent from the registry. "
            f"e.g. {undeclared[:5]}",
        )

        # The policy, stated once here and in HANDOVER.md: a single non-URL source may confirm a unit, and
        # the count is published rather than left to be discovered. Attestation and a photographed
        # specimen are different classes — the registry ranks the photograph tier 1 and bare attestation
        # tier 2 — so they are counted separately.
        single_source = [u for u in resolved_units
                         if u.get("providerId") in provider_by_id
                         and provider_by_id[u["providerId"]]["category"] == "non-url-evidence"
                         and not u.get("corroborated")]
        by_provider = Counter(u["providerId"] for u in single_source)

        # Keyed on the absence of a URL, not on the provider's category. A URL is checkable by anyone,
        # whatever its tier; evidence with no URL is checkable by nobody, so only the strong classes may
        # carry a claim alone. Keying on category instead would make this vacuous — the only categories
        # that reach it would be the tier 1 and 2 ones it is meant to police.
        unverifiable = [u["unitId"] for u in resolved_units
                        if not u.get("sourceUrl")
                        and not u.get("corroborated")
                        and u.get("providerId") in provider_by_id
                        and provider_by_id[u["providerId"]]["authorityTier"] > 2]
        check(
            "E3",
            "A claim with no URL and no corroboration rests on a tier 1-2 source",
            "FAIL",
            not unverifiable,
            f"{len(unverifiable)} units are confirmed by a source that is neither checkable nor strong. "
            f"e.g. {unverifiable[:5]}",
        )

        # Three documents state this number, and each is read by someone deciding whether owner evidence
        # is acceptable — HANDOVER by a human, CLAUDE.md by an agent, RESUME by whoever is about to add a
        # confirmation. A number stated three times drifts three times, and this one did: RESUME.md said
        # "currently 0" while the other two said 16 and the data said 30 (#64). It is only in this check
        # that the sentence stays true, so every document that states it has to be inside the check.
        attestation_only = by_provider.get("owner-attestation", 0)
        # HANDOVER.md left this set in #103: it is orientation now, and no longer states the figure.
        # The rule is unchanged — every document that *does* state it stays inside the check.
        policy_docs = {"CLAUDE.md": (ROOT / "CLAUDE.md").read_text(encoding="utf-8"),
                       "verification/RESUME.md": (ROOT / "verification" / "RESUME.md")
                       .read_text(encoding="utf-8")}
        figure_docs = dict(policy_docs)
        figure_docs["README.md"] = (ROOT / "README.md").read_text(encoding="utf-8")

        single_source_units = [u for u in resolved_units if not u.get("corroborated")]
        weak_single = [u for u in single_source_units
                       if provider_by_id.get(u.get("providerId"), {}).get("authorityTier", 99) > 2]
        corroborated_units = [u for u in resolved_units if u.get("corroborated")]


        def figure_drift(patterns: list[str], expected: int, *, required: bool = False,
                         docs: dict[str, str] | None = None) -> dict[str, str]:
            """Find every document whose stated figure disagrees with `expected`.

            `required` marks a sentence a document must actually contain — the attestation count is
            published policy, and a document dropping it is as much a defect as one restating it wrongly.
            Everything else is checked only where it appears, because these are prose figures and not every
            document mentions every one.
            """
            drift: dict[str, str] = {}
            for name, text in (docs or figure_docs).items():
                matches = [re.search(pattern, text) for pattern in patterns]
                found = [m for m in matches if m]
                if required and not found:
                    drift[name] = "no such statement"
                for match in found:
                    if int(match.group(1)) != expected:
                        drift[f"{name}: {match.group(0)!r}"] = (
                            f"says {match.group(1)}, data says {expected}")
            return drift


        def documented_figures(ident: str, title: str,
                               figures: list[tuple[list[str], int]], *,
                               required: bool = False, docs: dict[str, str] | None = None) -> None:
            """Declare one check over several published figures.

            E4, E7 and E11 were three hand-rolled copies of the same loop, added one issue at a time
            (#64, #65, #66). They stay three checks — CLAUDE.md and HANDOVER.md name them, and each covers
            a distinct claim — but there is now one implementation, so the next figure someone writes into
            a document is a row rather than a fourth copy (#68).

            Emitted at each check's own position rather than from one table at the top of the file: the
            suites' output order is part of their contract, and the values these depend on are computed at
            different points.
            """
            drift: dict[str, str] = {}
            for patterns, expected in figures:
                drift.update(figure_drift(patterns, expected, required=required, docs=docs))
            check(ident, title, "FAIL", not drift,
                  f"{len(drift)} stated figure(s) disagree with the data: {drift}")


        documented_figures(
            "E4", "Every document stating the attestation-only count states the real one",
            [([r"\*?\*?(\d+) units rest on owner attestation alone"], attestation_only)],
            required=True, docs=policy_docs,
        )

        # E7 — how much rests on one source, held to the data wherever a document says it (#65)
        # --------------------------------------------------------------------------- #
        # README claimed "a single *weaker* source may not [stand alone], and a check enforces it". E3
        # enforces something looser — checkable *or* strong — so a tier-3 page with a URL may carry a claim
        # alone, and hundreds do. Correcting that prose meant writing the real figures down, and a figure
        # in prose is a figure that drifts, which is the habit E4 exists to break.
        documented_figures(
            "E7", "Documented single-source exposure matches the data",
            [([r"(\d+) of \d+ resolved units\*{0,2} do", r"(\d+) resolved units do"], len(weak_single)),
             ([r"\*{0,2}(\d+) of \d+ resolved claims rest on one provider"], len(single_source_units)),
             ([r"only (\d+) are corroborated", r"it\s+covers (\d+) of \d+ units"],
              len(corroborated_units))],
        )

        # E8 — absence is settled by someone taking responsibility, never by provider rank (#66)
        # --------------------------------------------------------------------------- #
        # `contradicted` says a source disagrees. `not-printed` says the question is closed, and rule 4
        # allows only two ways to close it: a complete official manifest, within its stated scope, or an
        # explicit collection-owner adjudication after reviewing every cited claim. Everything else stays
        # `disputed`, which DATABASE.md tells applications not to read as "does not exist".
        #
        # Nothing violated this when it was written — the guard was a property of the data rather than a
        # rule, because every scoped-source row happened to carry an adjudication too. A rule that holds by
        # coincidence is one nobody notices breaking.

        adjudicated_units = {d["unitId"] for d in
                             load("verification/owner_adjudications.json")["decisions"]}
        manifest_scopes = {url.rstrip("/") for provider in registry["providers"]
                           if provider.get("supportsAbsence")
                           for url in provider.get("absenceScopes") or []}
        def settles_absence(unit: dict) -> bool:
            # Only an adjudication settles anything (owner decision, 2026-08-03). A declared scope is
            # recorded rationale, checked by E9, and deliberately not consulted here.
            return unit["unitId"] in adjudicated_units


        # Checking the derivation against itself would be vacuous, so this checks what consumers are told:
        # every language a card publishes as not-printed must trace back to a unit that something actually
        # settled, and the two published lists must partition the contradicted set exactly. A generator
        # that widened `languagesNotPrinted` — or quietly dropped a disputed language from both lists —
        # fails here rather than on someone's collection plan.
        absence_backing: list[str] = []
        for card in cards:
            if card.get("isCodeCard"):
                continue
            identity = (str(card.get("setCode") or ""), norm_number(card.get("number")),
                        str(card.get("variantToken") or "base"))
            for language in card.get("languagesNotPrinted") or []:
                backing = [u for u in resolved_units
                           if (str(u.get("setCode") or ""), norm_number(u.get("number")),
                               str(u.get("variant") or "base")) == identity
                           and u["language"] == language and u["status"] == "contradicted"]
                if not backing or not all(settles_absence(u) for u in backing):
                    absence_backing.append(f"{identity[0]} {identity[1]} {identity[2]} {language}")
        check(
            "E8",
            "Every published not-printed language rests on an owner adjudication",
            "FAIL",
            not absence_backing,
            f"{len(absence_backing)} card-language(s) are published as settled absences with neither an "
            f"owner adjudication nor a manifest-scoped source: {absence_backing[:5]}",
        )

        mispartitioned = [
            f"{card.get('setCode')} {card.get('number')} {card.get('variantToken') or 'base'}"
            for card in cards if not card.get("isCodeCard")
            and sorted((card.get("languagesNotPrinted") or []) + (card.get("languagesDisputed") or []))
            != sorted(card.get("languagesContradicted") or [])
        ]
        check(
            "E10",
            "not-printed and disputed partition the contradicted set exactly",
            "FAIL",
            not mispartitioned,
            f"{len(mispartitioned)} card(s) where the split does not reconstruct languagesContradicted: "
            f"{mispartitioned[:5]}",
        )

        # #66 left this reporting because two readings of rule 4 disagreed and the choice was the
        # owner's. It was settled on 2026-08-03: dependability decides whether a source may carry an
        # absence scope, not whether it is a manufacturer — so Elite Fourum keeps its Black Star Promos
        # table and the rule stops saying "complete official manifest".
        #
        # What a scope may never do is settle a claim on its own; that is always an adjudication
        # (absence_model.absence_decision enforces it, and E8 checks the result). So the thing worth
        # checking is no longer *who* declared a scope but whether the declaration is honest: a scope
        # must name specific pages and the provider must say why they are exhaustive, because a blanket
        # "this source is absence-capable" is exactly the claim rule 4 refuses.
        unjustified_scopes = []
        for provider in registry["providers"]:
            if not provider.get("supportsAbsence"):
                continue
            scopes = provider.get("absenceScopes") or []
            if not scopes:
                unjustified_scopes.append(f"{provider['providerId']}: supportsAbsence with no scope")
                continue
            if not any(word in (provider.get("notes") or "").lower()
                       for word in ("scope", "complete", "exhaustive", "manifest", "checklist")):
                unjustified_scopes.append(
                    f"{provider['providerId']}: {len(scopes)} scope(s), notes do not say why")
        check(
            "E9",
            "Every absence scope names its pages and says why they are complete",
            "FAIL",
            not unjustified_scopes,
            f"{len(unjustified_scopes)} provider(s) claim absence capability without a justified "
            f"scope: {unjustified_scopes}",
        )

        # The split is stated in prose in three documents, so it is held to the data the same way the
        # attestation count is (E4) and the single-source exposure is (E7). Writing a number down without
        # a check is how RESUME.md came to say 0 when the answer was 30.
        settled_count = sum(len(c.get("languagesNotPrinted") or []) for c in cards)
        disputed_count = sum(len(c.get("languagesDisputed") or []) for c in cards)
        split_docs = dict(policy_docs)
        split_docs["README.md"] = (ROOT / "README.md").read_text(encoding="utf-8")
        documented_figures(
            "E11", "Documented not-printed / disputed split matches the data",
            [([r"\*{0,2}(\d+) are settled", r"\*{0,2}(\d+) settled and \d+ disputed"], settled_count),
             ([r"(\d+) are disputed", r"\d+ settled and \*{0,2}(\d+) disputed"], disputed_count)],
            docs=split_docs,
        )

        # E12 — HANDOVER states figures too, and nothing was reading them
        # --------------------------------------------------------------------------- #
        # E4, E7 and E11 hold the figures in CLAUDE.md, RESUME.md and README.md. HANDOVER.md was in
        # none of those sets, which left the one document a cold-start agent is told to read first as
        # the only loadable document whose numbers no check reads. Both of its drift-capable figures
        # had in fact drifted, and each drifted through a commit that was tidying documentation:
        #
        #   "the 85 refuted claims"          written 2026-08-02; the overturn in the 2026-08-03
        #                                    adjudication pass took CONTRADICTED.json to 84, and the
        #                                    2026-08-04 rewrite that removed HANDOVER's duplicated
        #                                    state copied this line through unchanged.
        #   "63 completed one-shot passes"   written 2026-08-01 by the commit that corrected the
        #                                    stale docs, and invalidated the next day by 191083e —
        #                                    "Stop stating numbers no check reads" — which moved the
        #                                    five harvest scripts in and made it 68.
        #
        # Both figures describe things this suite can count, so they become rows here rather than a
        # standing instruction to remember. The pass count is deliberately derived from the directory
        # rather than from archive/MANIFEST.json: the manifest also covers archive/scripts/, and the
        # sentence is about passes/.
        handover_docs = {"HANDOVER.md": (ROOT / "HANDOVER.md").read_text(encoding="utf-8")}
        archived_passes = sum(1 for path in (ROOT / "verification" / "archive" / "passes").iterdir()
                              if path.suffix in {".ps1", ".py"})
        documented_figures(
            "E12", "Documented archive and export figures match the repository",
            [([r"The (\d+) refuted claims"], len(load("verification/CONTRADICTED.json"))),
             ([r"(\d+) completed one-shot passes"], archived_passes)],
            docs=handover_docs,
        )

        # S15 — the store and the registry name the same source (#73)
        # --------------------------------------------------------------------------- #
        # scripts/source_registry.py can infer a provider from `sourceType` prose, and for records that
        # carry no provider it still must. Where a unit *does* name one, the two answers have to agree —
        # and for a long time they did not, with nothing looking. Fourteen units were the #64 data defect;
        # three more were the resolver preferring whichever pattern sat earliest in its list over the
        # source actually named first in the text.
        #
        # This is the check that would have surfaced #64 the day it landed, so it is worth more than either
        # fix: it makes a whole class of provenance drift loud instead of latent.
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            from source_registry import resolve_provider  # noqa: E402

            provider_disagreements = [
                f"{u['unitId']}: stored {u.get('providerId')} vs resolved "
                f"{resolve_provider(u.get('sourceUrl'), u.get('sourceType'))}"
                for u in resolved_units
                if resolve_provider(u.get("sourceUrl"), u.get("sourceType")) != u.get("providerId")
            ]
            check(
                "S15",
                "The stored provider and the registry's inference agree",
                "FAIL",
                not provider_disagreements,
                f"{len(provider_disagreements)} unit(s) would be credited to a different source in "
                f"verification/source_registry.json than units.json records: "
                f"{provider_disagreements[:5]}",
            )
        except ImportError as error:  # pragma: no cover - the generator is always present in a checkout
            check("S15", "The stored provider and the registry's inference agree", "FAIL", False,
                  f"could not import scripts/source_registry.py: {error}")

        # R7 — the finish store keeps up with the language store (#71)
    with guarded("G5", "finish store consistency"):
        # --------------------------------------------------------------------------- #
        # A finish unit is `not-applicable` when every Cardmarket product claim behind it is contradicted:
        # no physical printing is left to have a finish. That is decided by a *full* finishes.py run, and
        # the release gate runs `finishes.py --reproject`, which redoes only the card projection from the
        # committed store. So when the language review closed and moved fifteen claims to contradicted,
        # twelve finish units should have become not-applicable and did not. The artifacts disagreed with
        # units.json for two days and every check stayed green.
        #
        # review_integrity's identity and key-coverage checks both passed throughout because the right
        # rows existed, carrying the wrong verdict. This checks the verdict.
        finish_units_doc = load("verification/finish_units.json")["units"]
        claims_by_group: dict[tuple[str, str, str], list[str]] = {}
        for unit in units:
            key = (str(unit.get("setCode") or ""), norm_number(unit.get("number")), unit["language"])
            claims_by_group.setdefault(key, []).append(unit["status"])

        stale_applicability = []
        for finish_unit in finish_units_doc:
            key = (str(finish_unit["setCode"]), norm_number(finish_unit.get("number")),
                   finish_unit["language"])
            statuses = claims_by_group.get(key)
            if not statuses:
                continue
            expected = "not-applicable" if all(s == "contradicted" for s in statuses) else "applicable"
            if finish_unit["applicabilityStatus"] != expected:
                stale_applicability.append(
                    f"{finish_unit['finishUnitId']} {key[0]} {key[1]} {key[2]}: "
                    f"{finish_unit['applicabilityStatus']}, expected {expected}")
        check(
            "R7",
            "Finish applicability agrees with the language store",
            "FAIL",
            not stale_applicability,
            f"{len(stale_applicability)} finish unit(s) are stale against units.json — this needs a full "
            f"`python scripts/finishes.py`, not --reproject: {stale_applicability[:5]}",
        )

        # E13 — the finish half of rule 4, held to the same line as the language half (#119)
        # --------------------------------------------------------------------------- #
        # `owner-adjudicated` closes a unit's finish list on the collection owner's authority, which
        # is the only route to completeness for products no manifest covers. Three things keep it
        # from becoming a way to assert finishes rather than close a list:
        #
        #   * every such unit traces to a recorded decision, so the ruling is citable;
        #   * the decision names exactly the finishes the evidence already found, so it can never
        #     introduce one;
        #   * it never applies to a unit with no printings at all, which would be an absence
        #     argument wearing the owner's name rather than a decision about known evidence.
        #
        # `complete-manifest` stays source-derived and separate: E9 and the finish generator's own
        # policy keep it that way, and a consumer that trusts only manufacturer manifests must be
        # able to tell the two apart.
        finish_decisions = {
            (d["setCode"], d["number"], d["language"]): d
            for d in load("verification/owner_adjudications.json").get("finishDecisions", [])
        }
        adjudicated_finish_problems: list[str] = []
        for unit in finish_units:
            key = (unit["setCode"], unit["number"], unit["language"])
            decision = finish_decisions.get(key)
            if unit.get("completenessStatus") == "owner-adjudicated":
                if not decision:
                    adjudicated_finish_problems.append(
                        f"{unit['finishUnitId']} {key}: owner-adjudicated with no recorded decision")
                elif sorted(decision.get("availableFinishes") or []) != sorted(
                        unit.get("availableFinishes") or []):
                    adjudicated_finish_problems.append(
                        f"{unit['finishUnitId']} {key}: decision names "
                        f"{sorted(decision.get('availableFinishes') or [])}, unit has "
                        f"{sorted(unit.get('availableFinishes') or [])}")
            if decision and not (unit.get("printings") or []):
                adjudicated_finish_problems.append(
                    f"{unit['finishUnitId']} {key}: adjudicated with no printing evidence at all")
        check(
            "E13",
            "Every owner-adjudicated finish closes a list the evidence already established",
            "FAIL",
            not adjudicated_finish_problems,
            f"{len(adjudicated_finish_problems)} problem(s): {adjudicated_finish_problems[:5]}",
        )

        check(
            "I5",
            "Evidence strength",
            "INFO",
            True,
            f"{len(single_source_units)} of {len(resolved_units)} resolved claims rest on a single "
            f"provider ({len(corroborated_units)} corroborated); {len(weak_single)} of those single "
            f"sources are tier 3, every one carrying a URL. E3 permits this — it requires an "
            f"uncorroborated claim to be checkable or strong, not both.",
        )

        # The log is a journal, not a projection of the store: it records what was observed and when, and
        # replaying it does not reconstruct state. What it must do is account for every resolved unit.
        logged = set()
        for line in (ROOT / "verification" / "evidence.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                logged.add(json.loads(line).get("unitId"))
        unlogged = [u["unitId"] for u in resolved_units if u["unitId"] not in logged]
        check(
            "E5",
            "Every resolved unit appears in the evidence journal",
            "FAIL",
            not unlogged,
            f"{len(unlogged)} resolved units have no entry in evidence.jsonl. e.g. {unlogged[:5]}",
        )

        check(
            "E6",
            "Evidence provenance",
            "INFO",
            True,
            f"{len(resolved_units)} resolved units across {len({u['providerId'] for u in resolved_units})} "
            f"providers; {sum(1 for u in resolved_units if u.get('corroborated'))} corroborated by more "
            f"than one; {len(single_source)} resting on a single non-URL source "
            f"({', '.join(f'{n} {p}' for p, n in sorted(by_provider.items()))}).",
        )

    with guarded("G6", "specimen records"):
        # --------------------------------------------------------------------------- #
        # S7-S10 — physical specimens are identified, not described
        # --------------------------------------------------------------------------- #
        # A claim resting on a card the owner holds used to say "(physical specimen supplied by the user)"
        # in prose, which cannot be cited twice or pointed at (#32). Each inspected card now has a stable
        # id, and a claim references it. Photographs arrive over time, so every check here has to pass
        # both while `photograph` is null and after a file lands.

        specimen_doc = load("verification/specimens.json")
        specimens = specimen_doc["specimens"]
        specimen_by_id = {s["specimenId"]: s for s in specimens}
        specimen_dir = ROOT / "verification" / "specimens"

        duplicate_specimens = [sid for sid, n in Counter(s["specimenId"] for s in specimens).items() if n > 1]
        check(
            "S7",
            "Specimen ids are unique",
            "FAIL",
            not duplicate_specimens,
            f"duplicated: {duplicate_specimens}",
        )

        # Every specimen: reference resolves, and identifies the same printing as the unit citing it.
        dangling, mismatched = [], []
        for unit in resolved_units:
            ref = str(unit.get("sourceRef") or "")
            if not ref.startswith("specimen:"):
                continue
            specimen = specimen_by_id.get(ref.split(":", 1)[1])
            if specimen is None:
                dangling.append(f"{unit['unitId']} -> {ref}")
                continue
            same = (specimen["setCode"] == unit["setCode"]
                    and specimen["number"] == str(unit["number"])
                    and specimen["variant"] == (unit.get("variant") or "base")
                    and specimen["language"] == unit["language"])
            if not same:
                mismatched.append(f"{unit['unitId']} cites {ref}")
        check(
            "S8",
            "Every specimen reference resolves to the printing it is cited for",
            "FAIL",
            not dangling and not mismatched,
            f"unresolved={dangling[:5]} wrong-printing={mismatched[:5]}",
        )

        # A declared photograph must exist and be a real image; a missing one must be declared null rather
        # than pointed at a file that is not there.
        photo_problems = []
        for specimen in specimens:
            name = specimen.get("photograph")
            if name is None:
                continue
            path = specimen_dir / name
            if not path.is_file():
                photo_problems.append(f"{specimen['specimenId']}: {name} not on disk")
                continue
            blob = path.read_bytes()
            if image_format(blob) is None:
                photo_problems.append(f"{specimen['specimenId']}: {name} is not a decodable image")
        check(
            "S9",
            "Declared specimen photographs exist and decode",
            "FAIL",
            not photo_problems,
            f"{len(photo_problems)} problem(s): {photo_problems[:5]}",
        )

        # The reverse: a file nobody references is either a forgotten registry entry or an image that
        # should not be published, and both are worth catching before the artifact ships.
        declared_photos = {s["photograph"] for s in specimens if s.get("photograph")}
        stray_photos = sorted(p.name for p in specimen_dir.iterdir()
                              if p.is_file() and p.name not in declared_photos) if specimen_dir.is_dir() else []
        check(
            "S10",
            "No specimen photograph is unreferenced",
            "FAIL",
            not stray_photos,
            f"{len(stray_photos)} file(s) in verification/specimens/ that no registry entry claims: "
            f"{stray_photos[:5]}",
        )

        check(
            "S11",
            "Specimen registry carries schema and version metadata",
            "FAIL",
            bool(specimen_doc.get("schema") and specimen_doc.get("schemaVersion")),
            "schema and schemaVersion are required for a canonical store",
        )

        check(
            "S12",
            "Specimen photograph coverage",
            "INFO",
            True,
            f"{len(declared_photos)} of {len(specimens)} inspected specimens have their photograph "
            f"committed; the rest rest on the recorded inspection alone until one is supplied.",
        )

        # S13-S14 — the provenance fields say what the claim rests on, not what is nearby (#64)
        # --------------------------------------------------------------------------- #
        # Fourteen Prize Pack units were stored as `photographed-specimen` — tier 1, above an official
        # database — on evidence that opened "Owner (domain expert) confirms". Their `sourceRef` held the
        # sentence "(owner attestation, corroborated by LigaPokemon + photographed specimens)", which
        # names the confusion outright: the field had been set to the strongest item in the corroboration
        # mix rather than to the source the claim rests on. Nothing caught it, because S8 only inspects
        # references that already look like references, and E3/E4 read `providerId` — the field that moved.

        prose_refs = [f"{u['unitId']}: {u['sourceRef']!r}" for u in resolved_units
                      if u.get("sourceRef") and not str(u["sourceRef"]).startswith("specimen:")]
        check(
            "S13",
            "A reference field holds a reference, never prose",
            "FAIL",
            not prose_refs,
            f"{len(prose_refs)} unit(s) put a sentence in sourceRef; it belongs in evidence. "
            f"e.g. {prose_refs[:3]}",
        )

        # The converse of S8. S8 proves a citation points at the right printing; this proves the strongest
        # provider in the registry cannot be claimed without one. A specimen is the only tier-1 class whose
        # evidence lives entirely inside this repository, so it is the only one a writer can assert by
        # typing it.
        uncited_specimen_claims = [u["unitId"] for u in resolved_units
                                   if u.get("providerId") in ("inspected-specimen",
                                                              "cardmarket-listing-photo")
                                   and not str(u.get("sourceRef") or "").startswith("specimen:")]
        check(
            "S14",
            "A claim read off a card cites the specimen record",
            "FAIL",
            not uncited_specimen_claims,
            f"{len(uncited_specimen_claims)} unit(s) claim tier-1 specimen authority with no specimen "
            f"reference. e.g. {uncited_specimen_claims[:5]}",
        )

        # S18-S19 — the rarity catalogue is reference data with a source, not a lookup (#146)
        # --------------------------------------------------------------------------- #
        # Rarity was read three ways and written down none: Cardmarket's label per product,
        # Bulbapedia's per set, and Japan's letter codes. The catalogue records which vocabulary is
        # speaking. Two things must stay true of it, because both are how a rarity quietly becomes
        # a finish or crosses a locality it does not hold in.
        rarity_catalogue = load("verification/rarity_catalogue.json")
        RARITY_FINISHES = {"non-holo", "holo", "reverse-holo", "mirror-holo"}
        rarity_problems = []
        seen_rarity_ids = set()
        for entry in rarity_catalogue["rarities"]:
            rid = entry.get("rarityId")
            if not rid or rid in seen_rarity_ids:
                rarity_problems.append(f"duplicate or missing rarityId {rid!r}")
            seen_rarity_ids.add(rid)
            if not str(entry.get("basis") or "").strip():
                rarity_problems.append(f"{rid}: no basis quoted")
            implied = entry.get("impliesFinish")
            if implied is not None and implied not in RARITY_FINISHES:
                rarity_problems.append(f"{rid}: impliesFinish {implied!r}")
        check(
            "S18",
            "Every rarity in the catalogue quotes its source and names a real finish or none",
            "FAIL",
            not rarity_problems,
            f"{len(rarity_problems)} problem(s): {rarity_problems[:5]}",
        )

        # A rarity that merely tends to be foil must not carry a finish. The article says "Ultra
        # Rare … typically marked as Rare Holofoil cards", which describes the marker; promoting
        # that to a finish is the same move as reading SPEC-0008's "rainbow rare" as holo.
        unquoted_finish = [
            entry["rarityId"] for entry in rarity_catalogue["rarities"]
            if entry.get("impliesFinish")
            and entry["impliesFinish"].split("-")[0].lower() not in entry.get("basis", "").lower()
        ]
        check(
            "S19",
            "A rarity naming a finish says so in the sentence it quotes",
            "FAIL",
            not unquoted_finish,
            f"{len(unquoted_finish)} rarit(ies) claim a finish their own quotation does not state: "
            f"{unquoted_finish[:5]}",
        )

        # S16-S17 — a recorded finish quotes the record it came from (#150)
        # --------------------------------------------------------------------------- #
        # `FINISH_SOURCES.md` has always allowed an identified physical scan to establish "visible
        # finish, pattern, marking, and size on that specimen", and until #150 there was no field
        # to put it in. The risk the field introduces is the one this project keeps meeting: a
        # finish that nobody observed, arrived at from a rarity label or from the language claim
        # beside it. `basis` is what makes an assignment checkable — it quotes the record's own
        # words — so a block without one is an assertion with no author.
        SPECIMEN_FINISHES = {"non-holo", "holo", "reverse-holo", "mirror-holo"}
        SPECIMEN_MARKING_ROLES = {"print-identity", "reverse-holo-treatment", "distribution-promo"}
        malformed = []
        for specimen in specimens:
            observation = specimen.get("physicalObservation")
            if observation is None:
                continue
            sid = specimen["specimenId"]
            if observation.get("finish") not in SPECIMEN_FINISHES:
                malformed.append(f"{sid}: finish {observation.get('finish')!r}")
            if not str(observation.get("basis") or "").strip():
                malformed.append(f"{sid}: no basis quoted")
            role = observation.get("markingRole")
            if role is not None and role not in SPECIMEN_MARKING_ROLES:
                malformed.append(f"{sid}: markingRole {role!r}")
            if observation.get("markings") and role is None:
                malformed.append(f"{sid}: marking recorded with no role")
        check(
            "S16",
            "A specimen's recorded finish uses the technical vocabulary and quotes its basis",
            "FAIL",
            not malformed,
            f"{len(malformed)} malformed physical observation(s): {malformed[:5]}. Finish is one "
            f"of {sorted(SPECIMEN_FINISHES)}; markings.role is the trichotomy CLAUDE.md states.",
        )

        # Absence stays absence. A specimen with no observation says nothing about the card's
        # finish, and nothing may read the missing block as a negative.
        observed_finishes = [s for s in specimens if s.get("physicalObservation")]
        check(
            "S17",
            "Specimens carrying an observed finish",
            "INFO",
            True,
            f"{len(observed_finishes)} of {len(specimens)} specimens record a finish; the other "
            f"{len(specimens) - len(observed_finishes)} state nothing about finish, which is not "
            f"evidence that they are non-holo",
        )

    with guarded("G7", "dataset identity and typed fields"):
        # --------------------------------------------------------------------------- #
        # F3b — market and product type stay independent
        # --------------------------------------------------------------------------- #
        # `market` says which regional catalogue lists a product; `isCodeCard` says what kind of product
        # it is. They were entangled: a `$languages.Count -ge 10` branch in the generators returned the
        # market value "Global (code card)", so KSS 26 — an ordinary card sold in 17 languages — was
        # classified as a code card, four genuine code cards listed in six languages were not, and the
        # dataset reported a different code-card count from the README.
        #
        # These live here rather than in the generators because the generators are dormant PowerShell
        # heading for the archive (#28, #50 Wave 4). The invariant has to outlive them.

        typed_markets = sorted({c["market"] for c in cards
                                if "code card" in str(c.get("market", "")).lower()})
        check(
            "F3b.1",
            "No market value names a product type",
            "FAIL",
            not typed_markets,
            f"market must describe where a product is listed, not what it is. Found {typed_markets}",
        )

        # The count has to agree wherever it is stated, which is what the README got wrong.
        code_cards = [c for c in cards if c.get("isCodeCard")]
        readme_claim = re.search(r"(\d+)\s+retained products are code cards", readme)
        check(
            "F3b.2",
            "Dataset and README report the same code-card count",
            "FAIL",
            bool(readme_claim) and int(readme_claim.group(1)) == len(code_cards),
            f"dataset has {len(code_cards)}; README says "
            f"{readme_claim.group(1) if readme_claim else 'nothing matching'}",
        )

        # Language count must not be able to imply product type again, in either direction.
        many_languages = [c["name"] for c in cards
                          if len(c.get("languages") or []) >= 10 and not c.get("isCodeCard")]
        few_languages = [c["name"] for c in cards
                         if len(c.get("languages") or []) < 10 and c.get("isCodeCard")]
        check(
            "F3b.3",
            "Product type is not inferable from language count",
            "FAIL",
            bool(many_languages) and bool(few_languages),
            "the split is only meaningful while both sides are populated: "
            f"{len(many_languages)} non-code-card products list 10+ languages, "
            f"{len(few_languages)} code cards list fewer",
        )

        # --------------------------------------------------------------------------- #
        # F4 — refuted language claims must be marked in the main dataset
        # --------------------------------------------------------------------------- #

        contradicted: dict[tuple[str, str, str], set[str]] = {}
        for unit in units:
            if unit["status"] == "contradicted":
                key = (unit["setCode"], norm_number(unit["number"]), unit["variant"])
                contradicted.setdefault(key, set()).add(unit["language"])

        unflagged = []
        for card in cards:
            if card.get("isCodeCard"):
                continue
            key = (card["setCode"], norm_number(card.get("number")), card.get("variantToken") or "base")
            refuted = contradicted.get(key, set()) & set(card.get("languages") or [])
            if refuted and not (set(card.keys()) & {"languagesContradicted", "languagesConfirmed"}):
                unflagged.append((card["setCode"], norm_number(card.get("number")), sorted(refuted)))
        check(
            "F4.1",
            "Cards carrying refuted language claims expose a confirmed/contradicted breakdown",
            "FAIL",
            not unflagged,
            f"{len(unflagged)} of {sum(1 for c in cards if not c.get('isCodeCard'))} non-code-card products "
            f"still list languages this project has itself refuted, with no field separating confirmed from "
            f"contradicted. e.g. {unflagged[:4]}",
        )


        # --------------------------------------------------------------------------- #
        # F5/F6/F7 — canonical identity and typed fields
        # --------------------------------------------------------------------------- #

        release_keys = [
            (row["setCode"], norm_number(row.get("number")), row["variant"], row.get("edition"))
            for row in releases
        ]
        duplicate_keys = [key for key, count in Counter(release_keys).items() if count > 1]
        has_stable_id = all(row.get("rowId") for row in releases)
        check(
            "F5.1",
            "Every chronological row carries a stable identity independent of sort order",
            "FAIL",
            has_stable_id,
            f"No row in analysis_confirmed_releases.json has a rowId; correction links embed the generated "
            f"row number instead, so sorting or filtering (#10) would retarget them. The natural key "
            f"(setCode, number, variant, edition) is already unique across all {len(releases)} rows "
            f"({len(duplicate_keys)} collisions), so a stable ID is derivable today.",
        )

        null_number_stores = []
        for label, rows, field in (
            ("snorlax_cards.json", cards, "number"),
            ("verification/units.json", units, "number"),
            ("verification/finish_units.json", finish_units, "number"),
        ):
            kinds = {repr(row.get(field)) for row in rows if not row.get(field)}
            if kinds:
                null_number_stores.append(f"{label}={sorted(kinds)}")
        check(
            "F6.1",
            "Unnumbered cards use one canonical representation across every store",
            "FAIL",
            len({s.split("=")[1] for s in null_number_stores}) <= 1,
            f"Unnumbered products are represented inconsistently: {'; '.join(null_number_stores)}. "
            f"Consumers must coerce with `str(x or '')` before any join, and a null number cannot take part "
            f"in a stable checklist ID (#8) or natural-number sort (#10).",
        )


        def precision(value: Any) -> str:
            """Classify by validating, not by measuring length: "2025-26" is a year range, not a month."""
            text = str(value)
            if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])", text):
                return "day"
            if re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", text):
                return "month"
            return "year"


        # The defect was one boolean carrying two independent facts: how precise the value is, and
        # whether it is trusted at that precision. The fix is that precision is *derived*, so it can
        # never contradict the value it describes, and confidence stands alone.
        precision_conflicts = [
            (row["setCode"], norm_number(row.get("number")), row["date"], row.get("datePrecision"))
            for row in releases
            if row.get("datePrecision") != precision(row.get("date"))
        ]
        missing_confidence = [
            row["setCode"] for row in releases if not isinstance(row.get("dateApproximate"), bool)
        ]
        check(
            "F7.1",
            "Date precision is derived from the value, and confidence is a separate field",
            "FAIL",
            not precision_conflicts and not missing_confidence,
            f"{len(precision_conflicts)} rows carry a datePrecision that contradicts their date value; "
            f"{len(missing_confidence)} rows lack a boolean dateApproximate. e.g. {precision_conflicts[:3]}",
        )

        bad_sort = [
            (row["setCode"], row.get("date"), row.get("dateSort"))
            for row in releases
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row.get("dateSort") or ""))
        ]
        check(
            "F7.3",
            "Every normalized sort date is a valid full ISO date",
            "FAIL",
            not bad_sort,
            f"{len(bad_sort)} rows have a malformed dateSort. e.g. {bad_sort[:4]}",
        )

        has_sort_key = all(row.get("dateSort") for row in releases)
        check(
            "F7.2",
            "Rows expose a normalized sortable date alongside the display date",
            "FAIL",
            has_sort_key,
            f"`date` mixes YYYY, YYYY-MM and YYYY-MM-DD in one string field "
            f"({dict(Counter(precision(r.get('date')) for r in releases))}). #10 requires typed release "
            f"sorting that retains approximate-date display; no normalized sort key exists.",
        )

        bulbapedia_codes = [record["setCode"] for record in bulbapedia_release_dates]
        malformed_bulbapedia_dates = [
            (record.get("setCode"), record.get("date"))
            for record in bulbapedia_release_dates
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(record.get("date") or ""))
        ]
        check(
            "F7.4",
            "Reviewed Bulbapedia release records have unique set codes and full ISO dates",
            "FAIL",
            len(bulbapedia_codes) == len(set(bulbapedia_codes)) and not malformed_bulbapedia_dates,
            f"duplicate codes={sorted(code for code, count in Counter(bulbapedia_codes).items() if count > 1)}; "
            f"malformed dates={malformed_bulbapedia_dates[:4]}",
        )

        release_rows_by_code: dict[str, list[dict[str, Any]]] = {}
        for release_row in releases:
            release_rows_by_code.setdefault(release_row["setCode"], []).append(release_row)
        bulbapedia_projection_drift = []
        for source_record in bulbapedia_release_dates:
            for release_row in release_rows_by_code.get(source_record["setCode"], []):
                date_source = release_row.get("dateSource") or {}
                if (
                    release_row.get("date") != source_record["date"]
                    or release_row.get("dateApproximate")
                    or date_source.get("provider") != "Bulbapedia"
                    or date_source.get("page") != source_record["page"]
                    or date_source.get("field") != source_record["field"]
                    or not str(date_source.get("url") or "").startswith(
                        "https://bulbapedia.bulbagarden.net/wiki/"
                    )
                ):
                    bulbapedia_projection_drift.append((source_record["setCode"], release_row.get("rowId")))
        check(
            "F7.5",
            "Reviewed Bulbapedia dates and source fields reach every generated release row",
            "FAIL",
            not bulbapedia_projection_drift
            and set(bulbapedia_codes).issubset(release_rows_by_code),
            f"projection drift={bulbapedia_projection_drift[:5]}; "
            f"missing codes={sorted(set(bulbapedia_codes) - set(release_rows_by_code))}",
        )


    with guarded("G8", "publication readiness"):
        # --------------------------------------------------------------------------- #
        # Publication readiness (#5) — release blockers, not data defects
        # --------------------------------------------------------------------------- #

        required_licences = {
            "LICENSES/PolyForm-Noncommercial-1.0.0.md": {
                "url": "https://github.com/polyformproject/polyform-licenses/blob/1.0.0/PolyForm-Noncommercial-1.0.0.md",
                "sha256": "c0ea4a896d2c8c394b29f9427589996db826cd501c512279ff0ed3ef48fabbe5",
            },
            "LICENSES/CC-BY-NC-SA-4.0.md": {
                "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.txt",
                "sha256": "e66c269d4819aaab34b49ef5220c4ddab6756f21bb5180761a4eb8561f2b7bbd",
            },
        }
        missing_licences = [name for name in required_licences if not (ROOT / name).exists()]
        wrong_licence_hashes = []
        for name, source in required_licences.items():
            path = ROOT / name
            if path.exists():
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual != source["sha256"]:
                    wrong_licence_hashes.append(f"{name}: {actual}")
        check(
            "L1",
            "Verbatim licence texts match their canonical publisher bytes",
            "FAIL",
            not missing_licences and not wrong_licence_hashes,
            f"missing={missing_licences} wrong_hash={wrong_licence_hashes}. Canonical sources and pinned "
            f"SHA-256 values: {required_licences}",
        )

        for doc in ("LICENSE.md", "THIRD_PARTY_NOTICES.md", "verification/history/PUBLIC-READINESS-AUDIT.md"):
            check(
                f"P{1 + list(('LICENSE.md', 'THIRD_PARTY_NOTICES.md', 'verification/history/PUBLIC-READINESS-AUDIT.md')).index(doc)}",
                f"{doc} exists",
                "FAIL",
                (ROOT / doc).exists(),
                f"{doc} is required before publication (#5)",
            )

        secret_pattern = re.compile(
            r"(?:api[_-]?key|passwd|password|Bearer\s+[A-Za-z0-9._-]{8,}|Authorization:|Cookie:)"
            r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}"
            r"|C:\\Users\\|(?<![A-Za-z0-9._-])/(?:Users/[a-z]|home/[a-z]+/)",
            re.IGNORECASE,
        )
        def sensitive_matches(data: bytes, label: str) -> list[str]:
            if b"\0" in data:
                return []
            text = data.decode("utf-8", errors="ignore")
            found_hits = []
            for match in secret_pattern.finditer(text):
                found = match.group(0)
                preceding = text[match.start() - 1:match.start()]
                recent_url_start = text.rfind("https://", max(0, match.start() - 300), match.start())
                recent_url_prefix = (
                    text[recent_url_start:match.start()] if recent_url_start >= 0 else ""
                )
                inside_source_url = bool(recent_url_prefix) and not any(
                    delimiter in recent_url_prefix for delimiter in ('"', "'", "\n", "\r")
                )
                # Official source assets use names such as `S10a_F@4x.png`. In a URL path the
                # segment resembles an email syntactically but is an image-density filename, not
                # contact data. `SV2a F@4x.png` even contains a source-native space, so retain a
                # short URL-context check as well as the ordinary path-boundary check.
                source_asset_name = (
                    (preceding in {"/", "\\"} or inside_source_url)
                    and found.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                )
                if "noreply" not in found.lower() and not source_asset_name:
                    found_hits.append(f"{label}: {found[:80]}")
            return found_hits


        scanned, hits = 0, []
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
        for raw_name in tracked:
            if not raw_name:
                continue
            relative = raw_name.decode("utf-8", errors="surrogateescape")
            path = ROOT / relative
            if relative in SENSITIVE_SCAN_EXEMPT:
                continue  # These files quote the expressions and known historical finding.
            try:
                data = path.read_bytes()
            except OSError:
                continue
            scanned += 1
            hits.extend(sensitive_matches(data, relative))
        check(
            "P4",
            "No secrets, personal paths, or contact details in the complete tracked tree",
            "FAIL",
            not hits,
            f"{len(hits)} hits across {scanned} scanned files: {hits[:5]}",
        )


        def scan_history() -> tuple[bool, int, list[str]]:
            """Scan every reachable Git blob, not merely the current version of each filename."""
            try:
                shallow = subprocess.check_output(
                    ["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, text=True
                ).strip() == "true"
                objects = subprocess.check_output(
                    ["git", "rev-list", "--objects", "--all"], cwd=ROOT, text=True
                ).splitlines()
            except (OSError, subprocess.CalledProcessError):
                return True, 0, ["Git history could not be read"]

            process = subprocess.Popen(
                ["git", "cat-file", "--batch"], cwd=ROOT,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            )
            assert process.stdin is not None and process.stdout is not None
            history_hits: list[str] = []
            scanned_blobs = 0
            for entry in objects:
                sha, _, path = entry.partition(" ")
                process.stdin.write((sha + "\n").encode("ascii"))
                process.stdin.flush()
                header = process.stdout.readline().decode("ascii", errors="replace").strip().split()
                if len(header) < 3 or header[1] == "missing":
                    continue
                object_type, size = header[1], int(header[2])
                data = process.stdout.read(size)
                process.stdout.read(1)  # protocol newline
                if object_type != "blob" or size > 5_000_000:
                    continue
                if path in SENSITIVE_SCAN_EXEMPT:
                    continue
                scanned_blobs += 1
                history_hits.extend(sensitive_matches(data, f"{sha[:10]}:{path or '(unknown path)'}"))
            process.stdin.close()
            process.wait(timeout=10)
            return shallow, scanned_blobs, sorted(set(history_hits))


        history_shallow, history_scanned, history_hits = scan_history()
        decisions_path = ROOT / "publication-decisions.json"
        try:
            decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            decisions = {}

        decision_keys = {
            "repositoryVisibility", "repositoryPublicationApproved", "sitePublicationApproved",
            "licenseGrantsApproved", "licensor", "ownerAttestationsApproved",
            "thirdPartyImagesApproved", "approvedBy", "approvedAt",
        }
        check(
            "P5",
            "Publication decisions are explicit, complete, and well typed",
            "FAIL",
            decision_keys <= set(decisions)
            and decisions.get("repositoryVisibility") in {"private", "public"}
            and all(
                isinstance(decisions.get(key), bool)
                for key in {
                    "repositoryPublicationApproved", "sitePublicationApproved",
                    "licenseGrantsApproved", "ownerAttestationsApproved", "thirdPartyImagesApproved",
                }
            )
            and decisions.get("licensor") in {None, "M4S.Collection"}
            and (decisions.get("approvedBy") is None or isinstance(decisions.get("approvedBy"), str))
            and (
                decisions.get("approvedAt") is None
                or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decisions.get("approvedAt"))))
            ),
            "publication-decisions.json must contain every decision with valid value types; the separate "
            "publication gate enforces approval before deployment",
        )
        check(
            "P6",
            "Full history was available and public-repository approval accounts for its findings",
            "FAIL",
            not history_shallow and (
                not decisions.get("repositoryPublicationApproved") or not history_hits
            ),
            f"shallow={history_shallow}; {len(history_hits)} sensitive-history hits across "
            f"{history_scanned} blobs. Public repository approval must remain false unless these are "
            f"reviewed or history is rewritten. e.g. {history_hits[:4]}",
        )

        def published_refs() -> list[str]:
            """Every ref this repository publishes, minus GitHub's synthetic pull-request merge refs.

            A `pull_request` workflow builds a `refs/pull/N/merge` commit that exists only to be tested.
            Its identity fields belong to GitHub and to whoever opened the pull request, not to either
            branch, so auditing them reports a finding nobody can fix by changing this repository.

            This used to exempt exactly one commit — the one that happened to be `HEAD` — which made the
            verdict depend on the checkout rather than on the repository: the same commit passed on the
            Windows runner and failed on the Linux one, twice, on #49. Excluding the whole pull namespace
            is what makes the check deterministic. Branches and tags are still audited in full, because
            making a repository public publishes every one of them.
            """
            try:
                refs = subprocess.check_output(
                    ["git", "for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags",
                     "refs/remotes"], cwd=ROOT, text=True
                ).split()
            except (OSError, subprocess.CalledProcessError):
                return []
            return [ref for ref in refs if "/pull/" not in ref]


        try:
            audited = published_refs()
            identity_fields = subprocess.check_output(
                ["git", "log", "--format=%H%x00%ae%x00%ce"] + audited, cwd=ROOT
            ).decode("utf-8", errors="replace").splitlines() if audited else []
        except (OSError, subprocess.CalledProcessError):
            identity_fields = ["\0commit metadata unavailable\0"]
        personal_commit_emails = set()
        for record in identity_fields:
            commit_sha, _, addresses = record.partition("\0")
            for email in addresses.split("\0"):
                email = email.strip()
                if "@" in email and "noreply" not in email.lower():
                    personal_commit_emails.add(email)
        personal_commit_emails = sorted(personal_commit_emails)
        check(
            "P7",
            "No reachable commit exposes a personal email address",
            "FAIL",
            not personal_commit_emails,
            f"personal commit emails: {personal_commit_emails}",
        )
        check(
            "I3",
            "Full-history publication audit",
            "INFO",
            True,
            f"{history_scanned} reachable blobs scanned; {len(history_hits)} sensitive-history hits; "
            f"repository publication approved={decisions.get('repositoryPublicationApproved')}; "
            f"personal commit emails={len(personal_commit_emails)}",
        )

        # The site exists to collect corrections, and it collects them exclusively through links into
        # this repository's issue tracker. Publishing the site while the repository stays private turns
        # every one of those links into a 404 for exactly the people the site is asking for help — the
        # failure is silent, because the gate, the browser tests and the link audit all still pass.
        # So the site may only go public together with the tracker it points at.
        site_html = (ROOT / "index.html").read_text(encoding="utf-8") if (ROOT / "index.html").exists() else ""
        repo_links = len(re.findall(r"https://github\.com/m4s-ai/snoredex-data", site_html))
        tracker_public = (
            decisions.get("repositoryVisibility") == "public"
            and decisions.get("repositoryPublicationApproved") is True
        )
        check(
            "P8",
            "A published site never points its correction links into a private tracker",
            "FAIL",
            not (decisions.get("sitePublicationApproved") is True and repo_links and not tracker_public),
            f"the site embeds {repo_links} links to github.com/m4s-ai/snoredex-data (203 per-row "
            f"correction links plus repository and issue-tracker links). sitePublicationApproved="
            f"{decisions.get('sitePublicationApproved')}, repositoryVisibility="
            f"{decisions.get('repositoryVisibility')}, repositoryPublicationApproved="
            f"{decisions.get('repositoryPublicationApproved')}. Publish both together, or remove the "
            f"correction affordance from the site.",
        )
        check(
            "I4",
            "Correction-loop reachability",
            "INFO",
            True,
            f"{repo_links} repository links embedded in the site; tracker publicly reachable="
            f"{tracker_public}. Contributors can only file corrections once this is True.",
        )


    with guarded("G9", "portability contract"):
        # --------------------------------------------------------------------------- #
        # Portability contract (#19)
        # --------------------------------------------------------------------------- #

        gitattributes = (ROOT / ".gitattributes").read_text(encoding="utf-8") if (ROOT / ".gitattributes").exists() else ""
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8") if (ROOT / "requirements.txt").exists() else ""
        check("X1", "Git attributes enforce LF text and binary image handling", "FAIL",
              "* text=auto eol=lf" in gitattributes and "*.jpg binary" in gitattributes,
              ".gitattributes must normalize text and protect image bytes")
        check("X2", "Browser dependency is pinned in a manifest", "FAIL",
              bool(re.search(r"^playwright==\d+\.\d+\.\d+$", requirements, re.MULTILINE)),
              "requirements.txt must pin Playwright")

        # The archive is the record of how the committed evidence was produced. A rerun of it cannot be
        # reproduced and an edit of it cannot be detected by reading the file, so the hashes are the
        # check. This replaced X3 "Active PowerShell writers use UTF-8 without BOM" and X4 "PowerShell
        # path portability is not bypassed through direct System.IO calls" once no PowerShell was left to
        # police: both only ever constrained scripts that ran, and none do (#50).
        archive = ROOT / "verification" / "archive"
        manifest_path = archive / "MANIFEST.json"
        archive_drift: list[str] = []
        if not manifest_path.exists():
            archive_drift.append("verification/archive/MANIFEST.json is missing")
        else:
            recorded = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
            present = {
                str(path.relative_to(archive)).replace("\\", "/"): hashlib.sha256(
                    path.read_bytes()).hexdigest()
                for path in sorted(archive.rglob("*"))
                if path.is_file() and path.name != "MANIFEST.json"
            }
            archive_drift.extend(f"modified: {name}" for name, digest in present.items()
                                 if name in recorded and recorded[name] != digest)
            archive_drift.extend(f"added: {name}" for name in present if name not in recorded)
            archive_drift.extend(f"removed: {name}" for name in recorded if name not in present)
        check("X3", "The archived one-shot record is unmodified", "FAIL", not archive_drift,
              f"{len(archive_drift)} archive difference(s): {archive_drift[:5]}")

        bom_files = []
        for raw_name in tracked:
            if not raw_name:
                continue
            path = ROOT / raw_name.decode("utf-8", errors="surrogateescape")
            if path.suffix.lower() in {".json", ".jsonl", ".csv", ".md", ".py", ".ps1", ".js", ".css", ".html", ".yml", ".yaml"}:
                try:
                    if path.read_bytes().startswith(b"\xef\xbb\xbf"):
                        bom_files.append(str(path.relative_to(ROOT)))
                except OSError:
                    pass
        check("X5", "Tracked text artifacts contain no UTF-8 BOM", "FAIL", not bom_files,
              f"BOM files: {bom_files[:10]}")


    with guarded("G10", "source registry"):
        # --------------------------------------------------------------------------- #
        # S — source registry (#6)
        # --------------------------------------------------------------------------- #

        registry_path = ROOT / "verification" / "source_registry.json"
        if registry_path.exists():
            registry = load("verification/source_registry.json")
            declared = {provider["providerId"] for provider in registry["providers"]}
            orphans = [
                row.get("canonicalUrl") or row.get("nonUrlEvidenceId")
                for row in registry["evidence"]
                if row["providerId"] not in declared
            ]
            check(
                "S1",
                "Every evidence record maps to a declared provider",
                "FAIL",
                not orphans,
                f"{len(orphans)} orphaned evidence records: {orphans[:5]}",
            )
            malformed = [
                row["canonicalUrl"]
                for row in registry["evidence"]
                if row["canonicalUrl"] and not re.match(r"^https?://[^/\s]+", row["canonicalUrl"])
            ]
            check(
                "S2",
                "Every registry URL is well formed",
                "FAIL",
                not malformed,
                f"{len(malformed)} malformed URLs: {malformed[:5]}",
            )
            no_link_faked = [
                row["providerId"]
                for row in registry["evidence"]
                if row["nonUrlEvidenceId"] and row["canonicalUrl"]
            ]
            check(
                "S3",
                "Non-URL evidence is never given a hyperlink",
                "FAIL",
                not no_link_faked,
                f"{len(no_link_faked)} non-URL evidence classes carry a URL: {no_link_faked[:5]}",
            )
            missing_attribution = [
                provider["providerId"]
                for provider in registry["providers"]
                if not provider.get("attribution") or not provider.get("licenseOrTerms")
                or provider.get("supportsAbsence") is None
            ]
            check(
                "S4",
                "Every provider declares attribution, terms and its absence policy",
                "FAIL",
                not missing_attribution,
                f"providers missing required fields: {missing_attribution}",
            )

            capability_paths = [
                ROOT / "verification" / "source_capability_schema.json",
                ROOT / "verification" / "source_capabilities.json",
                ROOT / "verification" / "source_capability_graph.json",
            ]
            missing_capability_files = [
                str(path.relative_to(ROOT)) for path in capability_paths if not path.exists()
            ]
            if not missing_capability_files:
                capability_schema = load("verification/source_capability_schema.json")
                capability_manifest = load("verification/source_capabilities.json")
                capability_graph = load("verification/source_capability_graph.json")
                graph_providers = {
                    provider["providerId"] for provider in capability_graph["providers"]
                }
                graph_surfaces = {
                    surface["surfaceId"]: surface for surface in capability_graph["surfaces"]
                }
                graph_edges = {
                    edge["edgeId"]: edge for edge in capability_graph["coverageEdges"]
                }
                expected_source_keys = {
                    row.get("canonicalUrl") or row.get("nonUrlEvidenceId")
                    for row in registry["evidence"]
                }
                resolved_source_keys = [
                    row["sourceKey"] for row in capability_graph["sourceResolution"]
                ]
                bad_routes = [
                    row["sourceKey"] for row in capability_graph["sourceResolution"]
                    if row["providerId"] not in graph_providers
                    or row["surfaceId"] not in graph_surfaces
                    or graph_surfaces[row["surfaceId"]]["providerId"] != row["providerId"]
                    or not row["capabilityEdgeIds"]
                    or any(edge_id not in graph_edges for edge_id in row["capabilityEdgeIds"])
                ]
                capability_contract_ok = (
                    capability_schema.get("properties", {}).get("meta", {})
                    .get("properties", {}).get("schema", {}).get("const")
                    == capability_manifest.get("meta", {}).get("schema")
                    and capability_graph.get("meta", {}).get("schemaVersion")
                    == capability_manifest.get("meta", {}).get("schemaVersion")
                    and graph_providers == declared
                    and len(resolved_source_keys) == len(set(resolved_source_keys))
                    and set(resolved_source_keys) == expected_source_keys
                    and not bad_routes
                )
                check(
                    "S5",
                    "Every verdict source resolves through the versioned capability graph",
                    "FAIL",
                    capability_contract_ok,
                    f"missing={missing_capability_files}; bad routes={bad_routes[:5]}; "
                    f"registry/provider sets agree={graph_providers == declared}; "
                    f"resolved={len(resolved_source_keys)} expected={len(expected_source_keys)}",
                )

                observations = {
                    row["observationId"]: row for row in capability_graph["observations"]
                }
                bad_hashes = []
                for observation in observations.values():
                    canonical = json.dumps(
                        observation["rawRecord"], ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                    expected_hash = "sha256:" + hashlib.sha256(canonical).hexdigest()
                    if observation.get("rawRecordHash") != expected_hash:
                        bad_hashes.append(observation["observationId"])
                edge_contract_errors = []
                manifest_absence_scopes = set()
                for edge_id, edge in graph_edges.items():
                    positive = observations.get(edge.get("knownPositiveObservationId"))
                    if (not positive or positive.get("kind") != "known-positive"
                            or edge_id not in positive.get("validatesEdges", [])):
                        edge_contract_errors.append(f"{edge_id}: no positive fixture")
                    absence = edge["absenceCapability"]
                    if absence["enabled"]:
                        challenge = observations.get(
                            edge.get("outOfScopeChallengeObservationId"))
                        if (not edge["exhaustive"] or not absence["exactScopes"]
                                or edge["boundary"]["zeroResultMeans"] != "bounded-absence"
                                or not challenge
                                or challenge.get("kind") != "out-of-scope-challenge"):
                            edge_contract_errors.append(f"{edge_id}: unbounded absence")
                        manifest_absence_scopes.update(absence["exactScopes"])
                    elif (edge["exhaustive"] or absence["exactScopes"]
                          or edge["boundary"]["zeroResultMeans"] != "unknown"):
                        edge_contract_errors.append(f"{edge_id}: silence promoted to absence")
                    surface = graph_surfaces[edge["surfaceId"]]
                    if ("finish" in edge["positiveEvidenceCapabilities"]
                            and surface["finishCapability"]["mode"] == "none"):
                        edge_contract_errors.append(f"{edge_id}: finish inherited from card scope")
                    if (edge["providerId"] in {"psa", "cgc", "inspected-specimen"}
                            and absence["enabled"]):
                        edge_contract_errors.append(f"{edge_id}: specimen registry closes absence")
                registry_absence_scopes = {
                    scope for provider in registry["providers"]
                    if provider.get("supportsAbsence")
                    for scope in provider.get("absenceScopes") or []
                }
                check(
                    "S6",
                    "Coverage edges keep positive fixtures, hashes, finish scope and absence boundaries",
                    "FAIL",
                    not bad_hashes and not edge_contract_errors
                    and manifest_absence_scopes == registry_absence_scopes,
                    f"bad hashes={bad_hashes[:5]}; edge errors={edge_contract_errors[:5]}; "
                    f"absence scope drift={sorted(manifest_absence_scopes ^ registry_absence_scopes)[:5]}",
                )
            else:
                check(
                    "S5", "Every verdict source resolves through the versioned capability graph",
                    "FAIL", False, f"missing {missing_capability_files}",
                )
                check(
                    "S6", "Coverage edges keep positive fixtures, hashes, finish scope and absence boundaries",
                    "FAIL", False, f"missing {missing_capability_files}",
                )
        else:
            check("S1", "Source registry exists", "FAIL", False,
                  "verification/source_registry.json is missing; run python scripts/source_registry.py")


        def marking_text(item: dict) -> str:
            """Flatten an item's stamps to comparable text, for the xJTG three-stamp regression."""
            return "|".join(
                f"{m.get('kind')}:{m.get('text')}"
                for m in (item.get("markings") or [])
                if isinstance(m, dict)
            )


    with guarded("G11", "checklist export"):
        # --------------------------------------------------------------------------- #
        # C — canonical checklist export (#8)
        # --------------------------------------------------------------------------- #

        checklist_path = ROOT / "analysis_checklist.json"
        if checklist_path.exists():
            checklist_doc = load("analysis_checklist.json")
            items = checklist_doc["items"]

            dupes = [cid for cid, n in Counter(i["checklistId"] for i in items).items() if n > 1]
            check("C1", "Checklist IDs are unique", "FAIL", not dupes,
                  f"{len(dupes)} duplicates: {dupes[:5]}")

            check("C2", "Checklist carries schema and version metadata", "FAIL",
                  bool(checklist_doc["meta"].get("schema") and checklist_doc["meta"].get("schemaVersion")),
                  "meta.schema and meta.schemaVersion are required for a canonical export")

            # No contradicted language may enter, and no code card.
            #
            # Keyed by variant, because a variant is what a contradiction is about: a unit is
            # (setCode, number, variant, language). xJTG 117 French is confirmed on the GameStop
            # stamp and not-printed on the Journey Together stamp, and both are correct. Collapsing
            # to (setCode, number, language) reported the confirmed one as refuted.
            refuted = {
                (card["setCode"], norm_number(card.get("number")), card.get("variantToken"), language)
                for card in cards
                for language in card.get("languagesContradicted") or []
            }
            leaked = [
                i["checklistId"] for i in items
                if (i["setCode"], i["number"], i.get("cardmarketVariant"), i["language"]) in refuted
            ]
            check("C3", "No contradicted language enters the checklist", "FAIL", not leaked,
                  f"{len(leaked)} items rest on a refuted language claim: {leaked[:5]}")

            code_card_sets = {
                (c["setCode"], norm_number(c.get("number"))) for c in cards if c.get("isCodeCard")
            }
            code_leak = [i["checklistId"] for i in items if (i["setCode"], i["number"]) in code_card_sets]
            check("C4", "No code card enters the checklist", "FAIL", not code_leak,
                  f"{len(code_leak)} code-card items: {code_leak[:5]}")

            # Unknown finish detail must be an explicit placeholder, never an invented finish.
            bad_placeholder = [
                i["checklistId"] for i in items
                if i["finish"] == "unresolved" and i.get("finishVerificationStatus") != "pending"
            ]
            check("C5", "Unresolved items are explicit placeholders, not asserted finishes", "FAIL",
                  not bad_placeholder, f"{len(bad_placeholder)} malformed placeholders: {bad_placeholder[:5]}")

            # A disclosure is not enough: a concrete First Edition finish must have explicit scope.
            unsupported_first_editions = [
                i["checklistId"] for i in items
                if i["edition"] == "1st Edition" and i["finish"] != "unresolved"
                and i.get("editionScope") not in {"explicit-printing-mapping", "only-supported-edition"}
            ]
            check("C6", "No First Edition finish is asserted from edition-agnostic evidence", "FAIL",
                  not unsupported_first_editions,
                  f"{len(unsupported_first_editions)} unsupported assertions: {unsupported_first_editions[:5]}")

            # --- required regression fixtures (#8) ---
            def finishes_for(set_code: str, number: str, language: str) -> set[str]:
                return {
                    i["finish"] for i in items
                    if i["setCode"] == set_code and i["number"] == number and i["language"] == language
                }

            jtg_regular = finishes_for("JTG", "117", "English")
            check("C7", "Regular JTG 117 is holo + reverse holo only, never regular non-holo", "FAIL",
                  jtg_regular == {"holo", "reverse-holo"},
                  f"got {sorted(jtg_regular)}; the non-holo Hop's Snorlax is the PPS8 Prize Pack product")

            pps8 = finishes_for("PPS8 JTG", "JTG 117", "English")
            check("C8", "JTG Prize Pack stays a separate product with its own non-holo and Cosmos holo",
                  "FAIL", pps8 == {"non-holo", "holo"}, f"got {sorted(pps8)}")

            xjtg = [i for i in items if i["setCode"] == "xJTG" and i["language"] == "English"]
            xjtg_stamps = {marking_text(i) for i in xjtg}
            check("C9", "xJTG 117 keeps three distribution stamps as separate items", "FAIL",
                  len(xjtg) == 3 and len(xjtg_stamps) == 3,
                  f"{len(xjtg)} items with {len(xjtg_stamps)} distinct stamps: {sorted(xjtg_stamps)}")

            df_reverse = [
                i for i in items
                if i["setCode"] == "DF" and i["finish"] == "reverse-holo"
                and "reverse-holo-treatment" in (i.get("markingRoles") or [])
            ]
            check("C10", "Dragon Frontiers reverse holo retains its set-logo treatment role", "FAIL",
                  bool(df_reverse), f"{len(df_reverse)} DF reverse-holo items carry reverse-holo-treatment")

            promo_stamp_implies_reverse = [
                i["checklistId"] for i in items
                if "distribution-promo" in (i.get("markingRoles") or []) and i["finish"] == "reverse-holo"
            ]
            check("C11", "A distribution stamp never implies reverse holo", "FAIL",
                  not promo_stamp_implies_reverse,
                  f"{len(promo_stamp_implies_reverse)} items treat a distribution promo as reverse holo: "
                  f"{promo_stamp_implies_reverse[:5]}")

            balls = {
                i["foilPattern"] for i in items
                if i["setCode"] == "xsv2a" and i["finish"] == "mirror-holo"
            }
            check("C12", "Poke Ball and Master Ball mirror versions stay separate", "FAIL",
                  {"poke-ball", "master-ball"} <= balls, f"patterns found: {sorted(p for p in balls if p)}")

            jumbo = [i for i in items if i["cardSize"] == "jumbo"]
            jumbo_pairs = [
                i for i in jumbo
                if any(o["setCode"] == i["setCode"] and o["number"] == i["number"]
                       and o["language"] == i["language"] and o["cardSize"] == "standard" for o in items)
            ]
            check("C13", "Jumbo cards are separate items from their standard counterparts", "FAIL",
                  bool(jumbo) and len(jumbo_pairs) == len([
                      i for i in jumbo
                      if any(o["setCode"] == i["setCode"] and o["number"] == i["number"] for o in items
                             if o["cardSize"] == "standard")
                  ]),
                  f"{len(jumbo)} jumbo items, {len(jumbo_pairs)} with a standard sibling")

            check("C14", "Checklist warns that positive evidence is not proof of completeness", "FAIL",
                  "documented" in (checklist_doc["meta"].get("warning") or "").lower(),
                  "meta.warning must state that absence from the checklist is not absence of the printing")

            family_map = {
                "non-holo": "non-holo", "holo": "holo",
                "reverse-holo": "reverse-holo", "mirror-holo": "reverse-holo",
                "unresolved": "unresolved",
            }
            bad_families = [
                i["checklistId"] for i in items
                if i.get("finishFamily") != family_map.get(i["finish"]) or not i.get("finishGroupId")
            ]
            check("C15", "Every checklist item has the correct collector finish family and group ID",
                  "FAIL", not bad_families,
                  f"{len(bad_families)} malformed family projections: {bad_families[:5]}")

            xsv2a_ja = [
                i for i in items
                if i["setCode"] == "xsv2a" and i["language"] == "Japanese"
                and i["foilPattern"] in {"poke-ball", "master-ball"}
            ]
            check("C16", "Poke Ball and Master Ball stay separate items under one Reverse Holo group",
                  "FAIL",
                  len(xsv2a_ja) == 2
                  and len({i["checklistId"] for i in xsv2a_ja}) == 2
                  and {i["finishFamily"] for i in xsv2a_ja} == {"reverse-holo"}
                  and len({i["finishGroupId"] for i in xsv2a_ja}) == 1,
                  f"Japanese xsv2a items: {[(i.get('checklistId'), i.get('finishFamily'), i.get('finishGroupId')) for i in xsv2a_ja]}")

            exs = [
                i for i in items
                if i["setCode"] == "EXS" and i["number"] == "" and i["language"] == "Japanese"
            ]
            exs_dates = {i.get("releaseDate") for i in exs}
            exs_markings = {marking_text(i) for i in exs}
            check("C17", "EXS Snorlax keeps the Vending and Quick Starter printings separate", "FAIL",
                  len(exs) == 2
                  and exs_dates == {"1998-03-23", "1998-12-04"}
                  and len(exs_markings) == 2
                  and all("print-identity" in (i.get("markingRoles") or []) for i in exs),
                  f"{len(exs)} items, dates={sorted(d for d in exs_dates if d)}, "
                  f"markings={sorted(exs_markings)}")
        else:
            check("C1", "Canonical checklist export exists", "FAIL", False,
                  "analysis_checklist.json is missing; run python scripts/checklist.py")


    with guarded("G12", "correction issue form"):
        # --------------------------------------------------------------------------- #
        # T — community correction issue form (#20)
        # --------------------------------------------------------------------------- #

        form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "printing-correction.yml"
        if form_path.exists():
            form = form_path.read_text(encoding="utf-8")
            schema_problems: list[str] = []
            try:
                form_doc = json.loads(form)
            except json.JSONDecodeError as error:
                form_doc = None
                schema_problems.append(f"form is not valid JSON/YAML: {error}")

            required_ids = [
                "row-id", "card-name", "set-code", "card-number", "current-state",
                "correction-type", "finishes", "foil-pattern", "stamp", "language",
                "edition", "card-size", "description", "evidence", "acknowledgement",
            ]
            present_ids = {
                element.get("id") for element in (form_doc or {}).get("body", [])
                if isinstance(element, dict)
            }
            missing_ids = [field_id for field_id in required_ids if field_id not in present_ids]
            check("T1", "Correction form defines every required field", "FAIL", not missing_ids,
                  f"missing field ids: {missing_ids}")

            # The form's vocabulary is generated from the finish store, so the invariant is simply that
            # the generated file is current. Re-deriving the labels here with a second normalization
            # would just test this checker against itself — the first attempt did exactly that and
            # produced four false failures on accents and British spelling.
            try:
                sys.path.insert(0, str(ROOT / "scripts"))
                import issue_templates

                expected_form = issue_templates.build_form(issue_templates.collect_vocabularies())
                stale_form = expected_form != form
                vocab = issue_templates.collect_vocabularies()
                detail = (
                    "the form no longer matches the data; run python scripts/issue_templates.py"
                    if stale_form else ""
                )
                check("T2", "Correction form is generated from the current data vocabulary", "FAIL",
                      not stale_form, detail)

                # And the vocabulary must actually be complete, not merely current.
                store_patterns = {
                    p["foilPattern"] for u in finish_units for p in u["printings"] if p.get("foilPattern")
                }
                store_stamps = {
                    m["text"] for u in finish_units for p in u["printings"]
                    for m in (p.get("markings") or []) if isinstance(m, dict) and m.get("text")
                }
                missing_vocab = (
                    [f"pattern:{p}" for p in store_patterns if p not in vocab["patterns"]]
                    + [f"stamp:{s2}" for s2 in store_stamps if s2 not in vocab["stamps"]]
                )
                check("T2b", "Correction form covers every pattern and stamp in the store", "FAIL",
                      not missing_vocab, f"absent from the form: {sorted(missing_vocab)[:6]}")
                check("T2c", "Correction form exposes one Reverse Holo collector family", "FAIL",
                      '"label": "Reverse Holo"' in form and '"label": "Mirror Holo"' not in form
                      and "Reverse Holo includes patterned reverse and mirror treatments" in form,
                      "the form must group technical reverse-holo and mirror-holo treatments for reporters")
            except ImportError as error:  # pragma: no cover
                check("T2", "Correction form generator is importable", "FAIL", False, str(error))

            # The project's central discipline has to survive contact with the public.
            form_body = (form_doc or {}).get("body", [])
            evidence_fields = [
                element for element in form_body
                if isinstance(element, dict) and element.get("id") == "evidence"
            ]
            markdown_text = " ".join(
                str((element.get("attributes") or {}).get("value") or "")
                for element in form_body
                if isinstance(element, dict) and element.get("type") == "markdown"
            )
            check("T3", "Correction form requires positive evidence and warns against absence arguments",
                  "FAIL",
                  len(evidence_fields) == 1
                  and (evidence_fields[0].get("validations") or {}).get("required") is True
                  and ("not evidence of absence" in markdown_text or "gap in that source" in markdown_text),
                  "the form must ask for evidence and state that an absence is not a finding")

            # GitHub validates the form against its own schema and rejects the whole file when any
            # attribute fails, silently serving a blank issue instead. Nothing here could see that: the
            # form existed, was current, and every link pointed at it, so T1-T4 all passed while the
            # correction loop was dead in the browser. An empty `description: ""` was the actual cause.
            if form_doc is not None:
                for key in ("name", "description", "body"):
                    if not form_doc.get(key):
                        schema_problems.append(f"top-level {key!r} is missing or empty")
                allowed_types = {"markdown", "input", "textarea", "dropdown", "checkboxes"}
                for index, element in enumerate(form_doc.get("body") or []):
                    kind = element.get("type")
                    attributes = element.get("attributes") or {}
                    where = f"body[{index}] ({kind}/{element.get('id', 'no-id')})"
                    if kind not in allowed_types:
                        schema_problems.append(f"{where}: unsupported type")
                    # An attribute present but blank is what GitHub rejects, so blank is worse than absent.
                    for name, value in attributes.items():
                        if isinstance(value, str) and not value.strip():
                            schema_problems.append(f"{where}: attribute {name!r} is present but empty")
                    if kind == "markdown" and (element.get("id") or element.get("validations")):
                        schema_problems.append(f"{where}: markdown takes neither id nor validations")
                    if kind == "dropdown":
                        options = attributes.get("options") or []
                        if not options:
                            schema_problems.append(f"{where}: dropdown has no options")
                        if len(options) != len(set(options)):
                            schema_problems.append(f"{where}: dropdown has duplicate options")
                        if any(not str(option).strip() for option in options):
                            schema_problems.append(f"{where}: dropdown has an empty option")
                        # GitHub reserves "None" for its own empty entry and rejects the whole template
                        # if an option uses it. This is not in the published JSON Schema — validating
                        # against that schema reported zero errors while GitHub refused the file — so it
                        # has to be asserted here explicitly.
                        for option in options:
                            if str(option).strip().lower() in RESERVED_DROPDOWN_OPTIONS:
                                schema_problems.append(
                                    f"{where}: option {option!r} is a word GitHub reserves; "
                                    f"the entire template is rejected"
                                )
                    if kind == "checkboxes":
                        for option in attributes.get("options") or []:
                            if not (option or {}).get("label", "").strip():
                                schema_problems.append(f"{where}: checkbox option without a label")
                    if kind in {"input", "textarea", "dropdown", "checkboxes"}:
                        if not attributes.get("label", "").strip():
                            schema_problems.append(f"{where}: missing label")
                        if not element.get("id"):
                            schema_problems.append(f"{where}: missing id, so it cannot be prefilled")

            check("T7", "Correction form satisfies GitHub's issue-form schema",
                  "FAIL",
                  not schema_problems,
                  f"{len(schema_problems)} violations; GitHub rejects the whole form and serves a blank "
                  f"issue instead: {schema_problems[:4]}")

            # Correction links must reach the form with identity attached.
            index_html = (ROOT / "index.html")
            if index_html.exists():
                page = index_html.read_text(encoding="utf-8")
                links = re.findall(r"https://github\.com/m4s-ai/snoredex-data/issues/new\?[^\"\\]+", page)
                bad_template = [u for u in links if "template=printing-correction.yml" not in u]
                check("T4", "Every correction link targets the generated issue form", "FAIL",
                      bool(links) and not bad_template,
                      f"{len(links)} links found, {len(bad_template)} not targeting the form")

                # The per-row links must carry the full identity. The contribute section also offers one
                # general entry point with no row attached, which is the intended way in for a reader who
                # has not found the row yet — it is not a per-row link missing its prefill.
                row_links = [u for u in links if "row-id=" in u]
                general_links = {u for u in links if "row-id=" not in u}
                missing_prefill = [
                    u[:80] for u in row_links
                    if not all(k in u for k in ("card-name=", "set-code=", "current-state="))
                ]
                check("T5", "Every per-row correction link prefills the row identity", "FAIL",
                      bool(row_links) and not missing_prefill and len(general_links) <= 1,
                      f"{len(row_links)} per-row links, {len(missing_prefill)} missing a prefill parameter "
                      f"{missing_prefill[:2]}; {len(general_links)} unprefilled entry-point links "
                      f"(at most one is intended)")

                # GitHub rejects issue-creation URLs beyond roughly 8 KB.
                overlong = [(len(u), u[:60]) for u in links if len(u) > 6000]
                longest = max((len(u) for u in links), default=0)
                check("T6", "No correction link approaches GitHub's URL length limit", "FAIL",
                      not overlong, f"longest link is {longest} chars; {len(overlong)} exceed 6000")
        else:
            check("T1", "Correction issue form exists", "FAIL", False,
                  ".github/ISSUE_TEMPLATE/printing-correction.yml is missing; "
                  "run python scripts/issue_templates.py")


    with guarded("G13", "regression guards"):
        # --------------------------------------------------------------------------- #
        # Regression guards for invariants that currently hold — keep them holding
        # --------------------------------------------------------------------------- #

        check(
            "R2",
            "availableFinishes agrees with finishStatus in every finish unit",
            "FAIL",
            not [
                u["finishUnitId"]
                for u in finish_units
                if set(u["availableFinishes"])
                != {f for f in FINISHES if u["finishStatus"].get(f) in
                    ("confirmed", "owner-attested", "marketplace-claimed")}
            ],
            "",
        )

        referenced = {c["imageFile"].split("/")[-1] for c in cards if c.get("imageFile")}
        on_disk = {p.name for p in (ROOT / "images").iterdir() if p.is_file()}
        check(
            "R5",
            "Image references and files on disk agree exactly",
            "FAIL",
            referenced == on_disk,
            f"missing={sorted(referenced - on_disk)[:5]} orphaned={sorted(on_disk - referenced)[:5]}",
        )

        check(
            "R6",
            "meta.verification matches the language state store",
            "FAIL",
            dataset["meta"]["verification"]["totalUnits"] == len(units)
            and dataset["meta"]["verification"]["confirmed"]
            == sum(1 for u in units if u["status"] == "confirmed"),
            "",
        )

        # Reported, never failed: these move whenever real verification work lands.
        status_counts = Counter(u["status"] for u in units)
        check(
            "I1",
            "Language verification progress",
            "INFO",
            True,
            f"{status_counts['confirmed']} confirmed, {status_counts['contradicted']} contradicted, "
            f"{status_counts['needs-manual-review']} manual review, {status_counts['pending']} open "
            f"of {len(units)} units",
        )
        check(
            "I2",
            "Finish verification progress",
            "INFO",
            True,
            f"{counts['withConfirmedFinish']} confirmed, {counts['withOnlyMarketplaceClaim']} marketplace-only, "
            f"{counts['pendingFinish']} pending, {counts['notApplicableFinish']} not-applicable of "
            f"{counts['totalFinishUnits']} finish units; {counts['withUnresolvedProductMapping']} with "
            f"unresolved product mapping",
        )


    with guarded("G14", "documentation roles and load stages"):
        # --------------------------------------------------------------------------- #
        # D1-D4 — one job per document, loaded at the stage it is needed (#100)
        # --------------------------------------------------------------------------- #
        # Nothing read prose, so prose drifted: RESUME.md still described a PowerShell toolchain and
        # five harvest scripts a whole migration after they moved to the archive (#68). These four
        # report that class of drift.
        #
        # Each lands as INFO and is promoted to FAIL by the phase that clears its backlog, so the
        # gate is never red on main while the work is in flight. Reporting first and failing once
        # clean is how #69 handled metric drift. D2 and D3 were promoted in #102, D4 in #103,
        # so all four now enforce.
        docs = documentation_inventory()

        undeclared = sorted(
            rel for rel, doc in docs.items() if doc["role"] is None or doc["stage"] is None
        )
        bad_stage = sorted(
            f"{rel} declares stage={doc['stage']!r}"
            for rel, doc in docs.items()
            if doc["stage"] is not None and doc["stage"] not in DOC_STAGES
        )
        check(
            "D1",
            "Every tracked document declares a role and a load stage",
            "FAIL",
            not undeclared and not bad_stage,
            f"{len(docs)} documents in scope; {len(undeclared)} undeclared {undeclared[:5]}; "
            f"{len(bad_stage)} with an unknown stage {bad_stage[:3]}. "
            f"Exempt: LICENSES/ is verbatim upstream text, verification/archive/ is hashed by X3.",
        )

        # A live document must not describe tooling that no longer exists. A reference is allowed
        # when the same line says where the script actually lives now — that is provenance, not
        # instruction.
        dead_tooling = []
        for rel, doc in docs.items():
            if doc["stage"] not in ("auto", "task", "reference", "public"):
                continue
            for number, line in enumerate(doc["text"].splitlines(), 1):
                lowered = line.lower()
                hit = ".ps1" in lowered or "```powershell" in lowered
                if hit and "archive/" not in lowered:
                    dead_tooling.append(f"{rel}:{number}")
        check(
            "D2",
            "No live document describes tooling that has been archived",
            "FAIL",
            not dead_tooling,
            f"{len(dead_tooling)} reference(s) to .ps1 tooling outside an archive path: "
            f"{dead_tooling[:6]}. Rewrite each to point into verification/archive/passes/ and say "
            f"it is a one-shot that must not be rerun (#102).",
        )

        missing_banner = sorted(
            rel for rel, doc in docs.items()
            if doc["stage"] == "history" and "Historical record" not in doc["text"]
        )
        missing_generated = sorted(
            rel for rel, doc in docs.items()
            if doc["stage"] == "generated" and "do not hand-edit" not in doc["text"].lower()
        )
        check(
            "D3",
            "Frozen and generated documents say so in their own text",
            "FAIL",
            not missing_banner and not missing_generated,
            f"{len(missing_banner)} history document(s) without the 'Historical record' banner "
            f"{missing_banner}; {len(missing_generated)} generated document(s) without a "
            f"do-not-hand-edit header {missing_generated}.",
        )

        # "One job per document", stated mechanically: a heading that appears in two documents an
        # agent may load is a fact maintained twice.
        headings: dict[str, list[str]] = {}
        for rel, doc in docs.items():
            if doc["stage"] not in ("auto", "task"):
                continue
            for line in doc["text"].splitlines():
                if line.startswith("## "):
                    key = re.sub(r"[^a-z ]", "", line[3:].lower()).split("  ")[0].strip()
                    # Numbered HANDOVER headings ("## 2. Current state") normalise to the same key.
                    headings.setdefault(key, []).append(rel)
        shared = sorted(
            f"{key!r} in {sorted(set(where))}"
            for key, where in headings.items() if len(set(where)) > 1
        )
        check(
            "D4",
            "No section heading is maintained in two loadable documents",
            "FAIL",
            not shared,
            f"{len(shared)} heading(s) duplicated across auto/task documents: {shared[:6]} (#103).",
        )

        # D5 — the documented gate may not demand a byte match SQLite cannot give (#127)
        # --------------------------------------------------------------------------- #
        # A SQLite file records the version number of the library that wrote it in its own header,
        # so two environments on different builds produce different bytes from identical data. The
        # documented gate regenerated both .sqlite artifacts for real and then byte-diffed the whole
        # tree, which reported drift on a clean main every time the local SQLite differed from the
        # one that last wrote them. CI never saw it: it runs `database.py --check` and
        # `tracker.py check-template`, which compare content.
        #
        # Checked as an absence, which is unusual here and deliberate. The property worth holding is
        # that nobody restores a bare `git diff --exit-code`, and it is the restoring that has to
        # fail — not some artifact of how the exclusion happens to be spelled today.
        # Command lines only. Prose elsewhere in the document names the step while describing what
        # the Windows leg covers, and a sentence about the gate is not the gate.
        gate_diffs = [
            line.strip() for line in (ROOT / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("git diff --exit-code")
        ]
        unscoped = [line for line in gate_diffs if "sqlite" not in line]
        check(
            "D5",
            "The documented gate never byte-diffs the SQLite artifacts",
            "FAIL",
            bool(gate_diffs) and not unscoped,
            f"{len(unscoped)} documented `git diff --exit-code` line(s) do not exclude *.sqlite: "
            f"{unscoped}. Those files cannot reproduce byte-for-byte across SQLite versions; their "
            f"content is covered by `database.py --check` and `tracker.py check-template` instead."
            if unscoped else
            "CLAUDE.md states no gate diff at all, so the gate it documents cannot be run.",
        )


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #

def emit(result: Check | Note) -> None:
    """This suite's output format, unchanged by the move onto the shared protocol."""
    if isinstance(result, Note):
        print(f"[info] {result.ident} {result.name}: {result.detail}")
        return
    if result.ok:
        print(f"[ ok ] {result.ident} {result.name}")
        return
    print(f"[FAIL] {result.ident} {result.name}")
    if result.detail:
        print(f"       {result.detail}")


def main() -> int:
    # A crash used to take the whole run with it: the body executed at import, so a key error in
    # one check's data loading killed the process before a single result reached stdout, and the
    # forty checks that had already passed were never seen. Collecting first and rendering after
    # means a failure loses only what had not run yet, and arrives as a reported check rather than
    # a traceback — the reader gets the verdicts that were established plus the reason the rest
    # stopped. Full per-check isolation needs the section split tracked in #82.
    crashed: Exception | None = None
    try:
        collect()
    except Exception as error:  # noqa: BLE001 - any failure here must still render what ran
        crashed = error
        check("X0", "The suite ran to completion", "FAIL", False,
              f"{type(error).__name__}: {error}. Checks after this point did not run.")
    suite.render(emit)
    total = len(suite.checks)
    failures = len(suite.failed)
    print(f"\n{total - failures}/{total} checks passed, {failures} failing.")
    if crashed is not None:
        traceback.print_exception(type(crashed), crashed, crashed.__traceback__)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
