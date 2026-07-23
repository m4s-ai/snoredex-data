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
import json, io, os
from pathlib import Path

B = Path(__file__).resolve().parent.parent
data = json.load(io.open(os.path.join(B, "snorlax_cards.json"), encoding="utf-8"))
cards = data["cards"]

WEST = {"English","French","German","Italian","Spanish","Portuguese","Dutch","Polish","Russian"}

# setCodes whose Western (WOTC) release had a 1st edition (Base Set..Neo Destiny, minus Base Set 2)
WEST_1ST = {"JU", "GH"}   # Jungle, Gym Heroes - the only Base..Neo-Destiny Snorlax sets we hold
# WOTC-era Western sets that were explicitly unlimited-only
WEST_UNLIMITED_ONLY = {"B2", "LC"}   # Base Set 2 (the documented exception), Legendary Collection
# Japanese sets (ADV/e-Card era through XY/Evolutions) whose JP release had 1st + unlimited
JP_1ST = {"EC5", "PCG1", "PCG3", "PCG9", "DP1", "Pt2", "BW7", "XY2", "XY10"}
# In the JP 1st-edition era but on the Elite Fourum "omitted" list (no 1st-edition run):
#   Lost Link and BREAK Starter Pack are named there explicitly. Lost Link's Bulbapedia line
#   {{TCG|1st Edition|Unlimited Edition}} renders as "Unlimited Edition" - unlimited only.
JP_UNLIMITED_ONLY = {"LL", "20th"}

SRC = {
  "west": 'Bulbapedia "1st Edition (TCG)": WOTC printed 1st editions for English+European releases, every set Base Set through Neo Destiny except Base Set 2.',
  "jp":   'Bulbapedia set articles: Japanese release available in both 1st and unlimited edition (ADV/e-Card era through XY). "Since the Sun & Moon era, Japanese 1st edition cards are no longer printed."',
  "unl":  'Bulbapedia: set released only in unlimited edition.',
  "none": 'Post-Neo-Destiny Western / Sun & Moon-era-onward Japanese / Korean-Chinese-SEA: the 1st-edition system does not apply. Cards have a single edition.',
  "kor":  'Bulbapedia (e.g. Plasma Gale, Wild Blaze): the Korean set is only available in unlimited edition; Korean never had 1st editions.',
}

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
                "source": SRC["jp"] + (" " + SRC["kor"] if any(l!="Japanese" for l in conf) else "")}
    if sc in WEST_UNLIMITED_ONLY:
        return {"hasFirstEdition": False, "system": "WOTC-unlimited-only",
                "firstEditionLanguages": [], "unlimitedLanguages": conf, "source": SRC["unl"]}
    if sc in JP_UNLIMITED_ONLY:
        return {"hasFirstEdition": False, "system": "JP-unlimited-only",
                "firstEditionLanguages": [], "unlimitedLanguages": conf,
                "source": 'Elite Fourum "1st Edition Timeline" - listed among Japanese sets omitted from 1st-edition printing.'}
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

data["meta"]["editionRuleset"] = {
    "westernFirstEdition": "Base Set through Neo Destiny except Base Set 2 (WOTC, English+European)",
    "japaneseFirstEdition": "ADV/e-Card era through XY era; none from Sun & Moon era onward; none 1996-2001",
    "koreanChineseSEA": "unlimited only, never 1st edition",
    "note": "Cardmarket's First Edition filter axis was NOT used (unreliable: present on 83/198 incl. modern cards). Starter/beginning products had no 1st-edition run. Lost Link and BREAK Starter Pack are on the Elite Fourum omitted list. Jungle 1st edition existed in all seven Western languages including Brazilian Portuguese (owner-confirmed).",
    "source": "Bulbapedia + Elite Fourum '1st Edition Timeline' (t/16054), verified 2026-07-23",
}
json.dump(data, io.open(os.path.join(B, "snorlax_cards.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

for k, v in summary.items():
    print(f"\n{k} ({len(v)}):")
    for x in v: print("  " + x)
