# -*- coding: utf-8 -*-
"""Classify each Snorlax card's edition status (1st Edition / Unlimited) and write it
back into snorlax_cards.json as an `editions` object.

Ruleset (all from Bulbapedia, verified this session):
  * 1st Edition (TCG): WOTC used it for English + European releases, every set from Base Set
    through Neo Destiny EXCEPT Base Set 2. No Western 1st editions after Neo Destiny.
    "Japanese cards did not have 1st Edition runs at this time."
  * Japanese sets gained 1st editions from the ADV/e-Card era and ran through the XY era;
    "Since the Sun & Moon era, Japanese 1st edition cards are no longer printed."
    Early Japanese sets (1996-2001) had no 1st edition.
  * Korean/Chinese/SEA: only ever unlimited (e.g. Plasma Gale, Wild Blaze articles:
    "the Korean set is only available in unlimited edition").
  * Promos and fixed starter/beginning products did not have 1st-edition print runs
    (the concept applies to booster-pack sets). [assumption, flagged]

Cardmarket's own "First Edition?" filter axis is NOT used - it is present on 83/198 cards
including SwSh/SM-era cards that never had a 1st edition, so it is unreliable.
"""
import json, io, os, sys
from pathlib import Path

B = Path(__file__).resolve().parent.parent
data = json.load(io.open(os.path.join(B, "snorlax_cards.json"), encoding="utf-8"))
cards = data["cards"]
RULES = json.load(io.open(os.path.join(B, "verification", "edition_rules.json"), encoding="utf-8"))
if RULES.get("meta", {}).get("schema") != "snoredex-edition-rules":
    raise SystemExit("invalid verification/edition_rules.json schema")
WEST = set(RULES["westernLanguages"])
WEST_1ST = set(RULES["westernFirstEditionSetCodes"])
WEST_UNLIMITED_ONLY = set(RULES["westernUnlimitedOnlySetCodes"])
JP_1ST = set(RULES["japaneseFirstEditionSetCodes"])
JP_UNLIMITED_ONLY = set(RULES["japaneseUnlimitedOnlySetCodes"])
SRC = RULES["sources"]

def classify(c):
    sc = c["setCode"]
    conf = c.get("languages", [])
    west_langs = [l for l in conf if l in WEST]
    if sc in WEST_1ST:
        # WOTC 1st edition applied to all its Western-language releases
        src = SRC["west"]
        if sc == "JU":
            # Brazilian Portuguese Jungle 1st edition specifically confirmed by the owner
            # (domain expert has seen the cards; does not personally own them).
            src += " Portuguese (Brazilian) Jungle 1st edition confirmed by owner attestation."
        return {"hasFirstEdition": True, "system": "WOTC",
                "firstEditionLanguages": west_langs,
                "unlimitedLanguages": conf,
                "source": src}
    if sc in JP_1ST:
        # only the Japanese print had a 1st edition; Korean/Chinese were unlimited-only
        fe = ["Japanese"] if "Japanese" in conf else []
        return {"hasFirstEdition": True, "system": "Japanese",
                "firstEditionLanguages": fe,
                "unlimitedLanguages": conf,
                "source": SRC["jp"] + (" " + SRC["korean"] if any(l!="Japanese" for l in conf) else "")}
    if sc in WEST_UNLIMITED_ONLY:
        return {"hasFirstEdition": False, "system": "WOTC-unlimited-only",
                "firstEditionLanguages": [], "unlimitedLanguages": conf, "source": SRC["unlimited"]}
    if sc in JP_UNLIMITED_ONLY:
        return {"hasFirstEdition": False, "system": "JP-unlimited-only",
                "firstEditionLanguages": [], "unlimitedLanguages": conf,
                "source": SRC["japaneseUnlimitedOnly"]}
    return {"hasFirstEdition": False, "system": "none",
            "firstEditionLanguages": [], "unlimitedLanguages": conf, "source": SRC["none"]}

summary = {"1st+Unlimited (WOTC)": [], "1st+Unlimited (Japanese)": [],
           "Unlimited only": [], "No edition system": []}
for c in cards:
    e = classify(c)
    c["editions"] = e
    tag = ("1st+Unlimited (WOTC)" if e["system"]=="WOTC" else
           "1st+Unlimited (Japanese)" if e["system"]=="Japanese" else
           "Unlimited only" if e["system"]=="WOTC-unlimited-only" else
           "No edition system")
    if e["hasFirstEdition"] or e["system"]=="WOTC-unlimited-only":
        summary[tag].append(f'{c["name"]} {c["setCode"]} {c.get("number") or ""}'.strip())

data["meta"]["editionRuleset"] = RULES["rulesetSummary"]
# The trailing newline matters, and this was the only writer of this file omitting it. Every other
# generator that touches snorlax_cards.json ends it with one, so the file's final byte depended on
# which generator happened to run last — and CI's determinism step does not run this script, so its
# rebuild always ended with a newline while a local run following the documented order might not.
# That is a one-byte diff that fails `database.py --check` through the source fingerprint, with a
# message about canonical inputs that says nothing about a newline. Writing it here makes the
# generator order irrelevant.
output_path = B / "snorlax_cards.json"
rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
if "--check" in sys.argv:
    if output_path.read_text(encoding="utf-8") != rendered:
        print("snorlax_cards.json editions are stale")
        sys.exit(1)
    print("snorlax_cards.json editions are current")
    sys.exit(0)

output_path.write_text(rendered, encoding="utf-8", newline="\n")

for k, v in summary.items():
    print(f"\n{k} ({len(v)}):")
    for x in v: print("  " + x)
