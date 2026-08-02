#!/usr/bin/env python3
"""Independent database review harness.

Complements `verification/review_integrity.py`. That script validates invariants
*within* each store; this one validates consistency *between* the state stores and
the derived artifacts that consumers and the future public site actually read.

Most checks correspond to a finding in `verification/REVIEW-2026-07-25.md`; later checks protect
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
import os
import re
import subprocess
import sys
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

# The check protocol is shared with `review_integrity.py` — one implementation of how a check is
# declared and when the process exits non-zero. The output format below stays this suite's own.
suite = Suite()


def load(rel: str) -> Any:
    with open(ROOT / rel, encoding="utf-8") as handle:
        return json.load(handle)


def check(check_id: str, title: str, severity: str, ok: bool, detail: str = "") -> None:
    """Declare a finding. Severity INFO reports without ever failing the run."""
    if severity == "INFO":
        suite.note(check_id, title, detail)
    else:
        suite.check(title, ok, detail, ident=check_id)


def norm_number(value: Any) -> str:
    """Canonical collector number. Unnumbered cards are null in some stores and "" in others."""
    return str(value or "")


# --------------------------------------------------------------------------- #
# Load stores and derived artifacts
# --------------------------------------------------------------------------- #

units = load("verification/units.json")
finish_doc = load("verification/finish_units.json")
finish_units = finish_doc["units"]
dataset = load("snorlax_cards.json")
cards = dataset["cards"]
releases = load("analysis_confirmed_releases.json")["variants"]
bulbapedia_release_dates = load("verification/bulbapedia_release_dates.json")["records"]
finish_analysis = load("analysis_finishes.json")

finish_by_id = {unit["finishUnitId"]: unit for unit in finish_units}
finish_by_key = {
    (unit["setCode"], norm_number(unit["number"]), unit["language"]): unit
    for unit in finish_units
}


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
    "source_registry.py", "checklist.py", "readme_stats.py", "issue_templates.py",
    "open_items.py", "site.py", "editions.py", "publish.py",
}

missing_steps = sorted(s for s in LIVE_STEPS | HARVEST_STEPS | {"mkunits.ps1"}
                       if not (ROOT / "scripts" / s).is_file())
check(
    "B1",
    "Every documented build step exists",
    "FAIL",
    not missing_steps,
    f"scripts/ is missing {missing_steps}",
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
policy_docs = {"HANDOVER.md": handover,
               "CLAUDE.md": (ROOT / "CLAUDE.md").read_text(encoding="utf-8"),
               "verification/RESUME.md": (ROOT / "verification" / "RESUME.md")
               .read_text(encoding="utf-8")}
disagreeing = {}
for name, text in policy_docs.items():
    found = re.search(r"\*?\*?(\d+) units rest on owner attestation alone", text)
    if not found or int(found.group(1)) != attestation_only:
        disagreeing[name] = found.group(1) if found else "no such statement"
check(
    "E4",
    "Every document stating the attestation-only count states the real one",
    "FAIL",
    not disagreeing,
    f"data has {attestation_only} attestation-only units; {disagreeing}",
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
                           if u.get("providerId") == "photographed-specimen"
                           and not str(u.get("sourceRef") or "").startswith("specimen:")]
check(
    "S14",
    "A claim attributed to a photographed specimen cites one",
    "FAIL",
    not uncited_specimen_claims,
    f"{len(uncited_specimen_claims)} unit(s) claim tier-1 specimen authority with no specimen "
    f"reference. e.g. {uncited_specimen_claims[:5]}",
)

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

for doc in ("LICENSE.md", "THIRD_PARTY_NOTICES.md", "verification/PUBLIC-READINESS-AUDIT.md"):
    check(
        f"P{1 + list(('LICENSE.md', 'THIRD_PARTY_NOTICES.md', 'verification/PUBLIC-READINESS-AUDIT.md')).index(doc)}",
        f"{doc} exists",
        "FAIL",
        (ROOT / doc).exists(),
        f"{doc} is required before publication (#5)",
    )

secret_pattern = re.compile(
    r"(?:api[_-]?key|passwd|password|Bearer\s+[A-Za-z0-9._-]{8,}|Authorization:|Cookie:)"
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}"
    r"|C:\\Users\\|/Users/[a-z]|/home/[a-z]+/",
    re.IGNORECASE,
)
def sensitive_matches(data: bytes, label: str) -> list[str]:
    if b"\0" in data:
        return []
    text = data.decode("utf-8", errors="ignore")
    found_hits = []
    for match in secret_pattern.finditer(text):
        found = match.group(0)
        if "noreply" not in found.lower():
            found_hits.append(f"{label}: {found[:80]}")
    return found_hits


scanned, hits = 0, []
tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
for raw_name in tracked:
    if not raw_name:
        continue
    relative = raw_name.decode("utf-8", errors="surrogateescape")
    path = ROOT / relative
    if relative in {"verification/PUBLIC-READINESS-AUDIT.md", "verification/review_findings.py"}:
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
        if path in {"verification/PUBLIC-READINESS-AUDIT.md", "verification/review_findings.py"}:
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
    refuted = {
        (card["setCode"], norm_number(card.get("number")), language)
        for card in cards
        for language in card.get("languagesContradicted") or []
    }
    leaked = [
        i["checklistId"] for i in items
        if (i["setCode"], i["number"], i["language"]) in refuted
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


# --------------------------------------------------------------------------- #
# T — community correction issue form (#20)
# --------------------------------------------------------------------------- #

form_path = ROOT / ".github" / "ISSUE_TEMPLATE" / "printing-correction.yml"
if form_path.exists():
    form = form_path.read_text(encoding="utf-8")

    required_ids = [
        "row-id", "card-name", "set-code", "card-number", "current-state",
        "correction-type", "finishes", "foil-pattern", "stamp", "language",
        "edition", "card-size", "description", "evidence", "acknowledgement",
    ]
    missing_ids = [i for i in required_ids if f"id: {i}\n" not in form]
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
              'label: "Reverse Holo"' in form and 'label: "Mirror Holo"' not in form
              and "Reverse Holo includes patterned reverse and mirror treatments" in form,
              "the form must group technical reverse-holo and mirror-holo treatments for reporters")
    except ImportError as error:  # pragma: no cover
        check("T2", "Correction form generator is importable", "FAIL", False, str(error))

    # The project's central discipline has to survive contact with the public.
    check("T3", "Correction form requires positive evidence and warns against absence arguments",
          "FAIL",
          "id: evidence" in form and "required: true" in form
          and "not evidence of absence" in form.replace("\n", " ").replace("  ", " ")
          or "gap in that source" in form,
          "the form must ask for evidence and state that an absence is not a finding")

    # GitHub validates the form against its own schema and rejects the whole file when any
    # attribute fails, silently serving a blank issue instead. Nothing here could see that: the
    # form existed, was current, and every link pointed at it, so T1-T4 all passed while the
    # correction loop was dead in the browser. An empty `description: ""` was the actual cause.
    schema_problems: list[str] = []
    yaml_available = True
    try:
        import yaml  # type: ignore

        form_doc = yaml.safe_load(form)
    except ImportError:
        # Never pass silently. A check that quietly does nothing is how the empty attribute
        # survived in the first place.
        form_doc, yaml_available = None, False
        schema_problems = ["PyYAML is not installed, so the form could not be validated"]
    except yaml.YAMLError as error:  # type: ignore[name-defined]
        form_doc, schema_problems = None, [f"form is not valid YAML: {error}"]

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
          "FAIL" if yaml_available else "INFO",
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


# --------------------------------------------------------------------------- #
# Regression guards for invariants that currently hold — keep them holding
# --------------------------------------------------------------------------- #

check(
    "R1",
    "finishUnitId, unitId and printingId are unique",
    "FAIL",
    len({u["unitId"] for u in units}) == len(units)
    and len(finish_by_id) == len(finish_units)
    and len({p["printingId"] for u in finish_units for p in u["printings"]})
    == sum(len(u["printings"]) for u in finish_units),
    "",
)

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

check(
    "R3",
    "Every resolved language unit has a non-trivial evidence string and a sourceType",
    "FAIL",
    not [
        u["unitId"]
        for u in units
        if u["status"] in ("confirmed", "contradicted")
        and (len(u.get("evidence") or "") < 12 or not u.get("sourceType"))
    ],
    "",
)

check(
    "R4",
    "Every confirmed printing cites at least one source",
    "FAIL",
    not [
        p["printingId"]
        for u in finish_units
        for p in u["printings"]
        if p["verificationStatus"] == "confirmed" and not p.get("sources")
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
    suite.render(emit)
    total = len(suite.checks)
    failures = len(suite.failed)
    print(f"\n{total - failures}/{total} checks passed, {failures} failing.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
