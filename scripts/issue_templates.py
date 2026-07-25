#!/usr/bin/env python3
"""Generate the community correction issue form (#20) from the live taxonomies.

The form's dropdowns list real foil patterns, stamps, languages and distribution channels. Those
vocabularies are generated from `verification/finish_units.json`, not typed by hand, for the same
reason the README finish table is generated: hand-maintained copies of generated facts drift, and
a correction form offering a pattern the project does not model produces reports nobody can act on.

Prefill strategy is deliberate. GitHub issue forms accept URL query parameters keyed on each
field's `id`, but support is most reliable for `input` and `textarea`. So every field the *site*
must fill — row identity, card, set, number, and the current recorded state — is an `input` or
`textarea`, and every field the *reporter* sets by hand is a `dropdown` or `checkboxes`. Prefill
never has to work for the form to be usable.

Labels must match the repository's existing label names **exactly**. GitHub silently drops a
label that does not resolve, so a near-miss produces a form that looks fine and quietly fails to
triage. See ISSUE_LABELS below.

    python scripts/issue_templates.py
    python scripts/issue_templates.py --check   # fail if regeneration would change the output
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = ROOT / ".github" / "ISSUE_TEMPLATE"
FORM_PATH = TEMPLATE_DIR / "printing-correction.yml"
CONFIG_PATH = TEMPLATE_DIR / "config.yml"

# Human labels for the machine vocabulary. Anything not listed falls back to a title-cased slug,
# so a newly modelled pattern still appears rather than being silently dropped.
PATTERN_LABELS = {
    "cosmos": "Cosmos",
    "crosshatch": "Crosshatch",
    "poke-ball": "Poké Ball",
    "master-ball": "Master Ball",
    "colorless-energy-star": "Colorless energy star",
    "energy-symbol-artwork-poke-ball": "Energy symbol + Poké Ball artwork",
    "tiled-type-symbol": "Tiled type symbol",
    "intricate-tiled-type-symbol": "Intricate tiled type symbol",
    "type-symbol-background": "Type symbol background",
    "large-type-symbol-left": "Large type symbol (left)",
    "plain-foil-background": "Plain foil background",
    "plain-foil-on-pokemon": "Plain foil on the Pokémon",
    "flat-foil-card-body": "Flat foil card body",
    "fireworks": "Fireworks",
}

# Applied to every submitted correction. These must match the repository's labels character for
# character - GitHub drops anything that does not resolve, without warning. Verified against the
# repository on 2026-07-25: the labels are capitalised and "Needs Evidence" uses a space, not a
# hyphen, so the obvious kebab-case guess would silently never apply.
ISSUE_LABELS = ["Correction", "Needs Evidence"]

FINISH_LABELS = {
    "non-holo": "Non-Holo",
    "holo": "Holo",
    "reverse-holo": "Reverse Holo",
    "mirror-holo": "Mirror Holo",
}


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def yaml_quote(value: str) -> str:
    """Double-quoted YAML scalar. Card and set names contain colons, quotes and accents."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def label_for(slug: str) -> str:
    return PATTERN_LABELS.get(slug) or slug.replace("-", " ").capitalize()


def collect_vocabularies() -> dict[str, list[str]]:
    units = read_json(ROOT / "verification" / "finish_units.json")["units"]
    releases = read_json(ROOT / "analysis_confirmed_releases.json")["variants"]

    patterns = sorted(
        {p["foilPattern"] for u in units for p in u["printings"] if p.get("foilPattern")}
    )
    stamps = sorted(
        {
            m["text"]
            for u in units
            for p in u["printings"]
            for m in (p.get("markings") or [])
            if isinstance(m, dict) and m.get("text")
        }
    )
    languages = sorted({u["language"] for u in units})
    editions = sorted({r["edition"] for r in releases})
    distributions = sorted(
        {
            p["distribution"]["kind"]
            for u in units
            for p in u["printings"]
            if p.get("distribution") and p["distribution"].get("kind")
        }
    )
    return {
        "patterns": patterns,
        "stamps": stamps,
        "languages": languages,
        "editions": editions,
        "distributions": distributions,
    }


def dropdown(field_id: str, label: str, description: str, options: list[str],
             required: bool = False) -> list[str]:
    lines = [
        "  - type: dropdown",
        f"    id: {field_id}",
        "    attributes:",
        f"      label: {yaml_quote(label)}",
        f"      description: {yaml_quote(description)}",
        "      options:",
    ]
    lines += [f"        - {yaml_quote(option)}" for option in options]
    if required:
        lines += ["    validations:", "      required: true"]
    return lines


def checkboxes(field_id: str, label: str, description: str,
               options: list[tuple[str, bool]]) -> list[str]:
    lines = [
        "  - type: checkboxes",
        f"    id: {field_id}",
        "    attributes:",
        f"      label: {yaml_quote(label)}",
        f"      description: {yaml_quote(description)}",
        "      options:",
    ]
    for text, required in options:
        lines.append(f"        - label: {yaml_quote(text)}")
        if required:
            lines.append("          required: true")
    return lines


def text_field(field_id: str, label: str, description: str, placeholder: str = "",
               required: bool = False, multiline: bool = False) -> list[str]:
    lines = [
        f"  - type: {'textarea' if multiline else 'input'}",
        f"    id: {field_id}",
        "    attributes:",
        f"      label: {yaml_quote(label)}",
        f"      description: {yaml_quote(description)}",
    ]
    if placeholder:
        lines.append(f"      placeholder: {yaml_quote(placeholder)}")
    if required:
        lines += ["    validations:", "      required: true"]
    return lines


def build_form(vocab: dict[str, list[str]]) -> str:
    lines = [
        "# GENERATED by scripts/issue_templates.py — do not hand-edit.",
        "# Dropdown options come from verification/finish_units.json so they cannot drift from",
        "# the vocabulary the project actually models.",
        "name: Printing correction",
        "description: Correct or add a physical printing — finish, foil pattern, stamp, language, or size.",
        "title: \"[Correction] \"",
        "labels: [" + ", ".join(yaml_quote(l) for l in ISSUE_LABELS) + "]",
        "body:",
        "  - type: markdown",
        "    attributes:",
        "      value: |",
        "        Thanks for helping correct the catalogue.",
        "",
        "        **Most fields below are pre-filled** if you arrived from a *Correction?* link on the",
        "        collection page. You normally only need to tick the right boxes and describe what is",
        "        wrong.",
        "",
        "        Two things worth knowing before you fill this in:",
        "",
        "        - **`pending` means *not yet established*, never *does not exist*.** If the site shows",
        "          a finish as pending, that is not a claim that it is unavailable — so there is nothing",
        "          to correct unless you have seen the printing.",
        "        - **We cannot act on \"it isn't listed anywhere\".** A source failing to mention a",
        "          printing is a gap in that source, not evidence of absence. This rule exists because",
        "          an absence argument once produced a false correction here that had to be reverted.",
        "          Positive evidence — a photo, a listing, a card in your hands — is what moves a claim.",
    ]

    lines += ["  - type: markdown", "    attributes:", "      value: \"### Which row\""]
    lines += text_field(
        "row-id", "Row ID",
        "Stable identifier of the row you are correcting. Pre-filled from the link; leave it as-is.",
        "e.g. jtg-117-v1-unl", required=True)
    lines += text_field("card-name", "Card name", "Pre-filled from the link.", "e.g. Hop's Snorlax")
    lines += text_field("set-code", "Set code and expansion", "Pre-filled from the link.",
                        "e.g. JTG — Journey Together")
    lines += text_field("card-number", "Collector number", "Pre-filled from the link.", "e.g. 117")
    lines += text_field(
        "current-state", "What the site currently records",
        "Pre-filled from the link so we can see exactly what you saw. Please do not edit it.",
        multiline=True)

    lines += ["  - type: markdown", "    attributes:",
              "      value: \"### What is wrong\""]
    lines += checkboxes(
        "correction-type", "What needs correcting",
        "Tick everything that applies.",
        [(text, False) for text in [
            "A finish is missing (the card exists in a finish not shown)",
            "A finish is shown that does not exist",
            "The foil pattern is wrong or missing",
            "The stamp / marking is wrong or missing",
            "A language is missing",
            "A language is shown that was never printed",
            "The edition (1st Edition / Unlimited) is wrong",
            "The card size (standard / jumbo) is wrong",
            "The release date is wrong",
            "The artist is wrong or missing",
            "The image is wrong",
            "Something else (described below)",
        ]])

    lines += ["  - type: markdown", "    attributes:", "      value: |",
              "        ### The printing you are reporting",
              "",
              "        Describe **the physical card you have seen**, not what the site shows.",
              "        Leave a field blank if you are not sure — a blank is far more useful than a guess."]

    lines += checkboxes(
        "finishes", "Finishes that DO exist",
        "Tick every finish you can positively confirm for this card, language and edition.",
        [(FINISH_LABELS[f], False) for f in ("non-holo", "holo", "reverse-holo", "mirror-holo")])

    lines += dropdown(
        "foil-pattern", "Foil pattern",
        "The pattern of the foil itself. Poké Ball and Master Ball are Mirror Holo patterns, "
        "not Reverse Holo — pick the pattern you can see and we will map it to the right finish.",
        ["Not applicable / non-holo", "I do not know"]
        + [label_for(p) for p in vocab["patterns"]]
        + ["Other (describe below)"])

    lines += dropdown(
        "stamp", "Stamp or marking on the card",
        "A physical stamp printed on the card. A distribution stamp does not by itself make a "
        "card Reverse Holo.",
        ["None", "I do not know"] + vocab["stamps"] + ["Other (describe below)"])

    lines += dropdown(
        "language", "Language",
        "The language of the card you are reporting.",
        ["Not language-specific"] + vocab["languages"], required=True)

    lines += dropdown(
        "edition", "Edition",
        "Only Base Set through Neo Destiny (Western) and ADV/e-Card through XY (Japanese) have a "
        "1st Edition run.",
        ["Not applicable / no edition system", "I do not know"] + vocab["editions"])

    lines += dropdown(
        "card-size", "Card size",
        "Jumbo cards are separate printings from their standard counterparts.",
        ["Standard", "Jumbo", "I do not know"])

    lines += dropdown(
        "distribution", "How it was distributed",
        "If you know how this specific printing was released.",
        ["I do not know"] + [label_for(d) for d in vocab["distributions"]]
        + ["Other (describe below)"])

    lines += ["  - type: markdown", "    attributes:", "      value: \"### Details and evidence\""]
    lines += text_field(
        "description", "What needs to be corrected?",
        "Describe the correction in your own words.",
        "e.g. This card also exists in a non-holo version in German — I have one in hand.",
        required=True, multiline=True)

    lines += text_field(
        "evidence", "Evidence",
        "Link a photo, marketplace listing, official checklist, or database entry. If the card is "
        "in your own collection, say so — that is recorded as an owner attestation and is graded "
        "accordingly. Attach photos by dragging them into this box.",
        "e.g. https://… , or: photo attached, card in my collection",
        required=True, multiline=True)

    lines += checkboxes(
        "acknowledgement", "Before submitting",
        "",
        [("This is **positive** evidence — I have seen this printing, rather than inferring it "
          "from something not being listed.", True)])

    lines += ["  - type: markdown", "    attributes:", "      value: |",
              "        ---",
              "        Corrections are reviewed against the source ladder in",
              "        [`verification/FINISH_SOURCES.md`](https://github.com/m4s-ai/snoredex-data/blob/main/verification/FINISH_SOURCES.md).",
              "        Thank you — specimen reports have already overturned three databases at once here."]

    return "\n".join(lines) + "\n"


def build_config() -> str:
    return "\n".join([
        "# GENERATED by scripts/issue_templates.py — do not hand-edit.",
        "blank_issues_enabled: true",
        "contact_links:",
        "  - name: Dataset scope and caveats",
        "    url: https://github.com/m4s-ai/snoredex-data/blob/main/README.md#scope-and-caveats--read-before-using",
        "    about: Before reporting, check whether the behaviour is a documented limitation.",
        "  - name: How evidence is graded",
        "    url: https://github.com/m4s-ai/snoredex-data/blob/main/verification/FINISH_SOURCES.md",
        "    about: The source ladder, and why an absence is not evidence.",
    ]) + "\n"


def main() -> int:
    vocab = collect_vocabularies()
    form = build_form(vocab)
    config = build_config()

    if "--check" in sys.argv:
        stale = []
        if not FORM_PATH.exists() or FORM_PATH.read_text(encoding="utf-8") != form:
            stale.append(str(FORM_PATH.relative_to(ROOT)))
        if not CONFIG_PATH.exists() or CONFIG_PATH.read_text(encoding="utf-8") != config:
            stale.append(str(CONFIG_PATH.relative_to(ROOT)))
        if stale:
            print(f"stale: {', '.join(stale)}; run python scripts/issue_templates.py")
            return 1
        print("issue templates are current")
        return 0

    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    FORM_PATH.write_text(form, encoding="utf-8", newline="\n")
    CONFIG_PATH.write_text(config, encoding="utf-8", newline="\n")
    print(f"printing-correction.yml: {len(vocab['patterns'])} foil patterns, "
          f"{len(vocab['stamps'])} stamps, {len(vocab['languages'])} languages, "
          f"{len(vocab['distributions'])} distribution channels")
    return 0


if __name__ == "__main__":
    sys.exit(main())
