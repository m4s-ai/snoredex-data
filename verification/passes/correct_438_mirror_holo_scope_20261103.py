"""Re-key every reviewed `mirror-holo` record to the owner's finish vocabulary (#438, 2026-11-03).

The collection owner fixed the vocabulary on 2026-11-03: `mirror-holo` is a reverse holo with a
mirror finish, where everything outside the artwork reflects solidly, and a pattern on reverse
foil outside the artwork (Poké Ball, Master Ball, energy star) is stored as `reverse-holo` with
its pattern. The owner then reviewed every remaining `mirror-holo` record on contact sheet D:

- holo: TW CLF 016 (foil across the full face, artwork included; override row and SPEC-0319..0322)
  and CN CSM2bC 124 (SPEC-0433; the Chinese "mirror" of an R card is the Western holo);
- reverse-holo with pattern: the xm2a and xsv2a override rows, SV-P 117 (ID), SV-P/CS 277 (CN),
  xm2a 136 and xsv2a 143 (KR) specimens — "Der Rest auch";
- mirror-holo stays: TW S-P 145 (SPEC-0030), confirmed as "Reverse Holo mit Mirror Finish".

SPEC-0617 was filed under sv2a 143 and created a duplicate KR mirror row. The owner explained that
sv2a is the printed number and Cardmarket's xsv2a only separates the mirror cards, so it is the
same card; its balls lack the Master Ball's bump, so it is the Poké Ball mirror (xsv2a V1, U0780).

Owner decisions that named `mirror-holo` for these units are re-keyed to `reverse-holo`.
JP sA 10 (Elite Fourum, no photograph) is outside this review and unchanged. Idempotent;
`--check` reports pending changes without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
OVERRIDES = V / "finish_overrides.json"
SPECIMENS = V / "specimens.json"
ADJUDICATIONS = V / "owner_adjudications.json"
RELEASE_DATES = V / "confirmed_release_overrides.json"
CHECKLIST_RENAMES = {
    "clf-016-t-chinese-none-mirror-holo": "clf-016-t-chinese-none-holo",
    "sv-p-cs-277-s-chinese-none-mirror-holo-master-ball": "sv-p-cs-277-s-chinese-none-reverse-holo-master-ball",
    "sv-p-cs-277-s-chinese-none-mirror-holo-poke-ball": "sv-p-cs-277-s-chinese-none-reverse-holo-poke-ball",
}
RELEASE_ITEM_REKEYS = {  # old item id -> (new item id, new physical printing id)
    "item-6754a89d-5fe0-5779-a495-378b2b19a5e0": (
        "item-c3abe9fe-4f69-53ed-85d9-269bfd4bef10", "PHYSICAL:PRINTING:877b297c24bace029db6bc37"),
    "item-9e12f0a7-cf6b-58ac-bb90-0d82a72559e8": (
        "item-d86f64e9-f28a-5b74-bcee-9a370c46bed7", "PHYSICAL:PRINTING:358015d25d89708bb3fa8eff"),
    "item-c7eec9be-fb9a-5be1-a093-39b147541339": (
        "item-05066956-63df-5919-8027-5ee0e52e4e98", "PHYSICAL:PRINTING:51fb343ff99b4828b6c23675"),
}
ROUTES = V / "collector_migration_routes.json"
ROUTE_REASON = "Owner finish vocabulary review of the mirror-holo records (2026-11-03, #438)."
sys.path.insert(0, str(ROOT / "scripts"))
from atomic_write import atomic_write  # noqa: E402


def collector_routes() -> list[tuple[str, str]]:
    """Retired checklist id -> current id for every re-keyed mirror-holo printing."""
    routes = [
        ("clf-016-t-chinese-none-mirror-holo", "clf-016-t-chinese-none-holo"),
        ("csm2bc-124-s-chinese-none-mirror-holo", "csm2bc-124-s-chinese-none-holo"),
        ("sv2a-143-korean-none-mirror-holo", "xsv2a-143-korean-none-reverse-holo-poke-ball"),
        ("sv-p-cs-277-s-chinese-none-mirror-holo-master-ball", "sv-p-cs-277-s-chinese-none-reverse-holo-master-ball"),
        ("sv-p-cs-277-s-chinese-none-mirror-holo-poke-ball", "sv-p-cs-277-s-chinese-none-reverse-holo-poke-ball"),
    ]
    for language in ("indonesian", "japanese", "korean", "t-chinese", "thai"):
        for pattern in ("colorless-energy-star", "poke-ball"):
            routes.append((f"xm2a-136-{language}-none-mirror-holo-{pattern}",
                           f"xm2a-136-{language}-none-reverse-holo-{pattern}"))
    for language in ("japanese", "korean", "t-chinese"):
        for pattern in ("master-ball", "poke-ball"):
            routes.append((f"xsv2a-143-{language}-none-mirror-holo-{pattern}",
                           f"xsv2a-143-{language}-none-reverse-holo-{pattern}"))
    return routes

DATE = "2026-11-03"
OVERRIDE_FINISH = {("xm2a", "136"): "reverse-holo", ("xsv2a", "143"): "reverse-holo", ("CLF", "016"): "holo"}
SPECIMEN_FINISH = {
    **{sid: "holo" for sid in ("SPEC-0319", "SPEC-0320", "SPEC-0321", "SPEC-0322", "SPEC-0433")},
    **{sid: "reverse-holo" for sid in (
        "SPEC-0013", "SPEC-0019", "SPEC-0020", "SPEC-0061", "SPEC-0410", "SPEC-0437",
        "SPEC-0471", "SPEC-0472", "SPEC-0612", "SPEC-0659", "SPEC-0660",
    )},
}
NOTE = {
    "holo": " Re-keyed to holo after the collection owner's review on 2026-11-03 (#438, contact sheet D).",
    "reverse-holo": (" Re-keyed to reverse-holo with its pattern after the collection owner's review on "
                     "2026-11-03 (#438, contact sheet D)."),
}
DECISIONS = ("OAF-20260901-SV-P-CS-277-zh-Hans", "OAF-20261103-XSV2A-143-ja", "OAF-20261103-XSV2A-143-ko")
SPEC_0617 = {
    "setCode": "xsv2a",
    "variant": "V1",
    "citedBy": ["U0780"],
    "physicalObservation": {
        "finish": "reverse-holo",
        "foilPattern": "poke-ball",
        # The ball type is what tells the two mirror printings apart, so it is a finish statement.
        "ownerAttestedFields": ["finish"],
        "ownerAttestedAt": DATE,
        "cardSize": "standard",
        "basis": ("Korean sv2a 143/165 with reflective repeating ball outlines across the card body outside "
                  "the artwork. The collection owner identified them on 2026-11-03 as Poké Balls: they lack "
                  "the bump of the Master Ball in this foil design. sv2a is the printed number; Cardmarket's "
                  "xsv2a only separates the mirror cards, so this is the Korean xsv2a V1 Poké Ball mirror."),
    },
}


def main() -> int:
    check = "--check" in sys.argv
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    specimens = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    adjudications = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    release_dates = json.loads(RELEASE_DATES.read_text(encoding="utf-8"))
    pending = []

    for row in overrides["overrides"]:
        target = OVERRIDE_FINISH.get((row.get("setCode"), row.get("number")))
        for printing in row.get("printings", []) if target else []:
            if printing["finish"] == "mirror-holo":
                pending.append(f"override {row['setCode']} {row['number']} {printing.get('foilPattern')} -> {target}")
                printing["finish"] = target

    for spec in specimens["specimens"]:
        sid = spec["specimenId"]
        observation = spec.get("physicalObservation") or {}
        target = SPECIMEN_FINISH.get(sid)
        if target and observation.get("finish") == "mirror-holo":
            pending.append(f"{sid} mirror-holo -> {target}")
            observation["finish"] = target
            observation["basis"] = observation["basis"].rstrip() + NOTE[target]
        if sid == "SPEC-0617" and any(spec.get(key) != value for key, value in SPEC_0617.items()):
            pending.append("SPEC-0617 sv2a mirror -> xsv2a V1 Poké Ball reverse-holo")
            spec.update({key: value for key, value in SPEC_0617.items()})

    for decision in adjudications["finishDecisions"]:
        if decision["adjudicationId"] in DECISIONS and "mirror-holo" in decision["availableFinishes"]:
            pending.append(f"decision {decision['adjudicationId']} mirror-holo -> reverse-holo")
            decision["availableFinishes"] = [
                "reverse-holo" if finish == "mirror-holo" else finish for finish in decision["availableFinishes"]
            ]
            decision["rationale"] += (
                " The collection owner re-keyed the patterned mirror to reverse-holo with its pattern on "
                "2026-11-03 (#438)."
            )

    # Reviewed release dates are keyed by the checklist ids the re-keyed printings retire, and by
    # the item and physical-printing ids that the finish change re-derives.
    for row in release_dates["releaseDates"]["reviewedItems"]:
        if row["itemId"] in RELEASE_ITEM_REKEYS:
            new_item, new_physical = RELEASE_ITEM_REKEYS[row["itemId"]]
            pending.append(f"release date item {row['itemId']} -> {new_item}")
            row["itemId"], row["physicalPrintingId"] = new_item, new_physical
        renamed = [CHECKLIST_RENAMES.get(cid, cid) for cid in row.get("legacyChecklistIds", [])]
        if renamed != row.get("legacyChecklistIds", []):
            pending.append(f"release date {row['itemId']}: {row['legacyChecklistIds']} -> {renamed}")
            row["legacyChecklistIds"] = renamed

    # Collector state follows each retired checklist id; older routes into a retired id are chained.
    routes_text = ROUTES.read_text(encoding="utf-8")
    known = {row["from"] for row in json.loads(routes_text)["cumulativeChecklistRekeys"]}
    new_routes = [(old, new) for old, new in collector_routes() if old not in known]
    stale_targets = [old for old, _ in collector_routes() if f'"to": "{old}"' in routes_text]
    splits_at = routes_text.index('"itemSplits"')
    stale_splits = [old for old, _ in collector_routes() if f'"{old}"' in routes_text[splits_at:]]
    pending += [f"item split target {old}" for old in stale_splits]
    pending += [f"route {old} -> {new}" for old, new in new_routes]
    pending += [f"chain routes into {old}" for old in stale_targets]

    if not pending:
        print("no pending changes; mirror-holo scope already corrected")
        return 0
    print(f"pending {len(pending)} change(s):", *pending, sep="\n  ")
    if check:
        return 1
    for path, document in ((OVERRIDES, overrides), (SPECIMENS, specimens), (ADJUDICATIONS, adjudications),
                           (RELEASE_DATES, release_dates)):
        atomic_write(path, json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    targets = dict(collector_routes())
    for old in stale_targets:
        routes_text = routes_text.replace(f'"to": "{old}"', f'"to": "{targets[old]}"')
    head, splits = routes_text[:splits_at], routes_text[splits_at:]
    for old in stale_splits:
        splits = splits.replace(f'"{old}"', f'"{targets[old]}"')
    routes_text = head + splits
    if new_routes:
        # The routes file keeps one route per line; append inside the rekey array.
        anchor = '\n  ],\n  "cardReleaseRekeys"'
        index = routes_text.index(anchor)
        routes_text = routes_text[:index] + "".join(
            ",\n    " + json.dumps({"from": old, "to": new, "reason": ROUTE_REASON}, ensure_ascii=False)
            for old, new in new_routes
        ) + routes_text[index:]
    json.loads(routes_text)
    atomic_write(ROUTES, routes_text)
    print("wrote", OVERRIDES.name, SPECIMENS.name, ADJUDICATIONS.name, RELEASE_DATES.name, ROUTES.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
