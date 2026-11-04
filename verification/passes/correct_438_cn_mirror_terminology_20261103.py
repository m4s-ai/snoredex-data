"""Correct the Simplified Chinese "mirror" finish mapping from #257 (#438, 2026-11-03).

The #257 admission read the official Mainland China finish guide
(https://www.pokemon.cn/tcg/product/16377.html) and stored its 镜面 ("mirror") processing as the
technical `mirror-holo`. The collection owner corrected that reading on 2026-11-03: "die nennen
das was wir im Westen 'holo' nennen 'mirror holo'", which is something else than a reverse holo
with a mirror finish, where everything outside the artwork, text box included, reflects solidly.

So the guide's two statements map to two different technical finishes:

- rarity R and above "foil cards produced with mirror processing" -> `holo` (the Western holo);
- C, U and R "patterned random foil" -> `reverse-holo`; the owner confirmed the photographed
  Poké Ball, Master Ball, star and confetti patterns as reverse holos on contact sheet A.

The eight override rows from #257 are re-keyed by the printed rarity of each card (R -> holo,
U -> reverse-holo), the source's evidence wording is aligned, and SPEC-0669 (CS5aC 093 R, vertical
line foil across artwork and border, previously recorded as `mirror-holo`) is re-read as `holo`.
SPEC-0433 is left alone: its solid silver reflection across the border is the owner's mirror finish.

On the same day the owner decided that a patterned foil outside the artwork is stored as
`reverse-holo` with its pattern, so the pattern-less Cardmarket reverse claim folds into it.
SPEC-0624 (Korean sv4a 145, geometric sparkle foil on illustration and frame; the same seller
listing is tile 11 of contact sheet A, which the owner confirmed as a reverse holo) moves from
`mirror-holo` to that form.

Idempotent; `--check` reports pending changes without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
sys.path.insert(0, str(ROOT / "scripts"))
from atomic_write import atomic_write  # noqa: E402
OVERRIDES = V / "finish_overrides.json"
SPECIMENS = V / "specimens.json"
ROUTES = V / "collector_migration_routes.json"
SOURCE_ID = "pokemon-cn-simplified-finish-rules"
FOLDED_IDS = {  # pattern-less guide row -> the single photographed pattern it folds into
    "cs1ac-110-s-chinese-none-reverse-holo": "cs1ac-110-s-chinese-none-reverse-holo-star",
    "cs5ac-093-s-chinese-none-holo": "cs5ac-093-s-chinese-none-holo-vertical-line",
    "csv5c-115-s-chinese-none-reverse-holo": "csv5c-115-s-chinese-none-reverse-holo-poke-ball",
}
FOLD_REASON = "The guide's class statement folds into the one photographed pattern (#438, 2026-11-03)."
# Printed rarity decides which half of the guide a card falls under.
TARGETS = {
    ("CS5aC", "093"): "holo",          # R
    ("CS6bC", "113"): "holo",          # R
    ("CSM2bC", "124"): "holo",         # R
    ("CSV10C", "175"): "holo",         # R
    ("151C", "143"): "reverse-holo",   # U
    ("CS1aC", "110"): "reverse-holo",  # U
    ("CSV5C", "115"): "reverse-holo",  # U
    ("CSV7C", "158"): "reverse-holo",  # U
}
EVIDENCE = (
    "The official guide states that cards of rarity R and above are foil cards produced with mirror "
    "(镜面) processing, which is the Western holo, and that Simplified Chinese C, U and R cards can "
    "be pulled as the locality-specific patterned random foil treatment, a reverse holo. The "
    "collection owner fixed this terminology on 2026-11-03 (#438). It does not state that these "
    "are the only printings."
)
SPEC_0669_BASIS = (
    "The physical card on fabric reads Simplified Chinese CS5aC 093/127 R. Parallel vertical rainbow "
    "foil is visible across the artwork and silver border: the regular holo of an R card, which the "
    "official guide calls mirror processing (owner terminology correction 2026-11-03, #438)."
)
SPARKLE = "geometric sparkle across artwork and frame"
SPEC_0624_BASIS = (
    "The middle card in the original three-card photograph is Korean 잠만보 sv4a G145/190. "
    "Blue-purple reflective geometric foil on illustration and frame. The collection owner "
    "confirmed this treatment as a reverse holo on 2026-11-03 (#438, contact sheet A tile 11, "
    "same seller listing) and decided that patterned foil is stored as reverse-holo with its pattern."
)


def main() -> int:
    check = "--check" in sys.argv
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    specimens = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    pending = []

    source = overrides["sources"][SOURCE_ID]
    if source["evidence"] != EVIDENCE:
        pending.append(f"source {SOURCE_ID} evidence")
        source["evidence"] = EVIDENCE
    # The guide states rarity classes, never a card's pattern: a product-line description, so
    # finishes.py folds it into the photographed patterned printings instead of keeping a
    # pattern-less duplicate beside them.
    if source.get("coverage") != "product-line-description":
        pending.append(f"source {SOURCE_ID} coverage -> product-line-description")
        source["coverage"] = "product-line-description"

    found = set()
    for row in overrides["overrides"]:
        key = (row.get("setCode"), row.get("number"))
        if key not in TARGETS or row.get("languages") != ["S-Chinese"]:
            continue
        for printing in row.get("printings", []):
            if printing.get("sourceRefs") != [SOURCE_ID]:
                continue
            found.add(key)
            if printing["finish"] != TARGETS[key]:
                pending.append(f"override {key[0]} {key[1]}: {printing['finish']} -> {TARGETS[key]}")
                printing["finish"] = TARGETS[key]
    missing = set(TARGETS) - found
    if missing:
        print(f"ERROR: guide override rows not found: {sorted(missing)}", file=sys.stderr)
        return 2

    spec = next(s for s in specimens["specimens"] if s["specimenId"] == "SPEC-0669")
    observation = spec["physicalObservation"]
    if observation["finish"] != "holo" or observation["basis"] != SPEC_0669_BASIS:
        pending.append("SPEC-0669 mirror-holo -> holo")
        observation["finish"] = "holo"
        observation["basis"] = SPEC_0669_BASIS

    spec = next(s for s in specimens["specimens"] if s["specimenId"] == "SPEC-0624")
    observation = spec["physicalObservation"]
    if (observation["finish"], observation.get("foilPattern")) != ("reverse-holo", SPARKLE):
        pending.append("SPEC-0624 mirror-holo -> reverse-holo")
        observation["finish"] = "reverse-holo"
        observation["foilPattern"] = SPARKLE
        observation["basis"] = SPEC_0624_BASIS

    # The guide row folds into its single photographed pattern; collector state follows, and the
    # routes this pass's earlier run pointed at the pattern-less id are chained onward.
    routes_text = ROUTES.read_text(encoding="utf-8")
    known = {row["from"] for row in json.loads(routes_text)["cumulativeChecklistRekeys"]}
    new_routes = [(old, new) for old, new in FOLDED_IDS.items() if old not in known]
    chained = [old for old in FOLDED_IDS if f'"to": "{old}"' in routes_text]
    pending += [f"route {old} -> {FOLDED_IDS[old]}" for old, _ in new_routes]
    pending += [f"chain routes into {old}" for old in chained]

    if not pending:
        print("no pending changes; CN mirror terminology already corrected")
        return 0
    print(f"pending {len(pending)} change(s):", *pending, sep="\n  ")
    if check:
        return 1
    for path, document in ((OVERRIDES, overrides), (SPECIMENS, specimens)):
        atomic_write(path, json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    for old in chained:
        routes_text = routes_text.replace(f'"to": "{old}"', f'"to": "{FOLDED_IDS[old]}"')
    if new_routes:
        # The routes file keeps one route per line; append inside the rekey array.
        anchor = '\n  ],\n  "cardReleaseRekeys"'
        index = routes_text.index(anchor)
        routes_text = routes_text[:index] + "".join(
            ",\n    " + json.dumps({"from": old, "to": new, "reason": FOLD_REASON}, ensure_ascii=False)
            for old, new in new_routes
        ) + routes_text[index:]
    json.loads(routes_text)
    atomic_write(ROUTES, routes_text)
    print(f"wrote {OVERRIDES.name}, {SPECIMENS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
