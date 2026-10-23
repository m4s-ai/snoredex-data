#!/usr/bin/env python3
"""Record the printed set size of every numbered set the collector catalogue carries (owner, 2026-10-23).

The catalogue showed no collector-number denominator for 789 items because the set database held
only 14 printed sizes, all recorded for run membership (#146). A set's printed size is a set fact
and belongs to every item of that set, whatever source created the item. This pass records it for
each remaining numbered set, in the format of `extend_printed_set_sizes_20260810.py`:

* TCGdex `cardCount.official` is the printed denominator. The retained set lists sit beside the
  findings in `verification/evidence/printed-set-sizes-20261023/`. Wherever a printed card in the
  repository also shows a denominator for the same set and numbering, the two agree (24 of 24).
* Sets TCGdex does not list take the denominator printed on inspected specimens, or on retained
  source-first prints, of that set and numbering.

Numbering is regional: the Japanese 20th set prints /072 where Korean prints /071, and HXY /039
where Korean prints /036. Each record names its numbering, and the catalogue applies a size only
to the matching region. Promo, prize-pack, championship-deck and reprint sets have no printed run
size and are not recorded; sets with no source stay without a size.

Idempotent; `--check` reports pending records without writing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
BUNDLE = "verification/evidence/printed-set-sizes-20261023"
RETRIEVED = "2026-10-23"
ORIGIN = "reviewed-printed-set-sizes-20261023"
NUMBERING = {"WEST": ("western", "en"), "JP": ("japanese", "ja"), "CN": ("simplified-chinese", "zh-cn"),
             "TW": ("traditional-chinese", None)}
# (legacy set code, printed size, region, TCGdex set id or None, agreeing printed evidence)
SIZES = [
    ("CS5aC", 127, "CN", "CS5aC", []),
    ("CS6bC", 131, "CN", "CS6bC", []),
    ("CSM1cC", 151, "CN", "CSM1cC", []),
    ("CSM2DC", 342, "CN", None, ["SPEC-0435"]),
    ("CSM2bC", 150, "CN", "CSM2bC", ["SPEC-0433", "SPEC-0434"]),
    ("CSV5C", 129, "CN", "CSV5C", []),
    ("CSV7C", 204, "CN", "CSV7C", []),
    ("20th", 72, "JP", None, ["SPEC-0588"]),
    ("BW7", 70, "JP", None, ["SPEC-0572", "SPEC-0583", "SPEC-0637", "SPEC-0638"]),
    ("EC5", 88, "JP", "E5", ["SPEC-0576", "SPEC-0584", "SPEC-0632", "SPEC-0633"]),
    ("HSZ", 34, "JP", None, ["SPEC-0062", "SPEC-0481"]),
    ("HXY", 39, "JP", None, ["SPEC-0482"]),
    ("LL", 40, "JP", "LL", []),
    ("PCG1", 82, "JP", "PCG1", []),
    ("PCG3", 84, "JP", "PCG3", ["SPEC-0095", "SPEC-0096", "SPEC-0097", "SPEC-0639"]),
    ("PCG9", 68, "JP", "PCG9", []),
    ("XY10", 78, "JP", "XY10", ["SPEC-0104", "SPEC-0589", "SPEC-0642"]),
    ("XY2", 80, "JP", "XY2", ["SPEC-0573", "SPEC-0586"]),
    ("m3", 80, "JP", "M3", []),
    ("mC", 742, "JP", "MC", []),
    ("s10b", 71, "JP", "S10b", []),
    ("s2", 96, "JP", "S2", []),
    ("s4", 100, "JP", "S4", []),
    ("sH", 53, "JP", None, ["SPEC-0484"]),
    ("sm10", 95, "JP", "SM10", ["SPEC-0414"]),
    ("smL", 51, "JP", None, ["SPEC-0485"]),
    ("sv4K", 66, "JP", "SV4K", []),
    ("sv5a", 66, "JP", "SV5a", []),
    ("sv9", 100, "JP", "SV9", []),
    ("svG", 49, "JP", None, ["SPEC-0486"]),
    ("svIba", 66, "JP", None, ["SPEC-0487"]),
    ("svLN", 22, "JP", "SVLN", []),
    ("AS5a", 184, "TW", None, ["SPEC-0038", "SPEC-0039", "SPEC-0287", "SPEC-0429"]),
    ("B2", 130, "WEST", "base4", []),
    ("BCR", 149, "WEST", "bw7", ["SPEC-0068"]),
    ("BKT", 162, "WEST", "xy8", []),
    ("CRE", 198, "WEST", "swsh6", []),
    ("CRZ", 159, "WEST", "swsh12.5", []),
    ("DF", 101, "WEST", "ex15", []),
    ("DP", 130, "WEST", "dp1", ["SPEC-0056"]),
    ("FCO", 124, "WEST", "xy10", []),
    ("FL", 112, "WEST", "ex6", ["SPEC-0107", "SPEC-0140", "SPEC-0141", "SPEC-0142"]),
    ("FST", 264, "WEST", "swsh8", []),
    ("GEN", 83, "WEST", "g1", ["SPEC-0053", "SPEC-0123", "SPEC-0124", "SPEC-0131"]),
    ("GH", 132, "WEST", "gym1", ["SPEC-0585"]),
    ("HIF", 68, "WEST", "sm115", ["SPEC-0054", "SPEC-0108", "SPEC-0109"]),
    ("JTG", 159, "WEST", "sv09", []),
    ("JU", 64, "WEST", "base2", ["SPEC-0055", "SPEC-0110", "SPEC-0111", "SPEC-0112"]),
    ("KSS", 39, "WEST", "xy0", ["SPEC-0132"]),
    ("LC", 110, "WEST", "lc", ["SPEC-0101", "SPEC-0102"]),
    ("LOR", 196, "WEST", "swsh11", ["SPEC-0089", "SPEC-0090"]),
    ("MEW", 165, "WEST", "sv03.5", ["SPEC-0528", "SPEC-0529"]),
    ("PAF", 91, "WEST", "sv04.5", []),
    ("PAR", 182, "WEST", "sv04", []),
    ("PGO", 78, "WEST", "swsh10.5", []),
    ("PLS", 135, "WEST", "bw8", []),
    ("POR", 88, "WEST", "me03", []),
    ("PRE", 131, "WEST", "sv08.5", []),
    ("RCL", 192, "WEST", "swsh2", []),
    ("SK", 144, "WEST", "ecard3", ["SPEC-0113"]),
    ("SSH", 202, "WEST", "swsh1", ["SPEC-0070"]),
    ("SSP", 191, "WEST", "sv08", []),
    ("TEU", 181, "WEST", "sm9", []),
    ("TWM", 167, "WEST", "sv06", []),
    ("UNB", 214, "WEST", "sm10", ["SPEC-0412", "SPEC-0413", "SPEC-0416", "SPEC-0417"]),
    ("VIV", 185, "WEST", "swsh4", ["SPEC-0087", "SPEC-0088"]),
]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def tcgdex_count(language: str, set_id: str) -> int:
    rows = read(ROOT / BUNDLE / f"sets-{language}.json")
    return next(row["cardCount"]["official"] for row in rows if row["id"] == set_id)


def record(code: str, size: int, region: str, set_id: str | None, printed: list[str]) -> dict:
    numbering, language = NUMBERING[region]
    agreeing = f" Printed evidence of the same set and numbering agrees: {', '.join(printed)}." if printed else ""
    if set_id:
        path = f"{BUNDLE}/sets-{language}.json"
        if tcgdex_count(language, set_id) != size:
            raise ValueError(f"{code}: retained TCGdex count differs from {size}")
        sha = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        provider, url = "tcgdex", f"https://api.tcgdex.net/v2/{language}/sets/{set_id}"
        basis = (f"TCGdex {language} set {set_id} cardCount.official {size}, the denominator printed "
                 f"beside the collector number; retained set list {path} (sha256 {sha}).{agreeing}")
    else:
        provider, url = "inspected-specimen", None
        basis = (f"The denominator {size} printed beside the collector number on retained cards of this "
                 f"set and numbering: {', '.join(printed)}. TCGdex does not list the set.")
    return {
        "sourceRecordId": stable_id("SET-SRC-SIZE", code),
        "sourceKind": "printed-set-size-record",
        "provider": provider,
        "providerRecordKey": code,
        "retrieved": RETRIEVED,
        **({"sourceUrl": url} if url else {}),
        "raw": {"legacySetCode": code, "printedSetSize": size, "numbering": numbering,
                "basis": basis + " Not inferred from a rarity, a name or a card count."},
    }


def mirror(graph: dict, row: dict) -> bool:
    sid = row["sourceRecordId"]
    present = {(e["entityType"], e["entityId"]) for e in graph["entities"]}
    if ("set-source-record", sid) in present:
        return False
    reason = "printed set size; a set fact applied by numbering to every item of the set"
    graph["entities"] += [
        {"entityType": "set-source-record", "entityId": sid, "origin": ORIGIN, "payload": row},
        {"entityType": "set-source-disposition", "entityId": sid, "origin": ORIGIN,
         "payload": {"sourceRecordId": sid, "disposition": "needs-evidence", "targetRef": None, "reason": reason}},
    ]
    graph["edges"].append({"fromType": "set-source-disposition", "fromId": sid, "relation": "disposes",
                           "toType": "set-source-record", "toId": sid, "provenance": {}})
    graph["migrationDispositions"].append({"sourceKind": "set-catalogue-source", "sourceId": sid,
                                           "disposition": "needs-evidence", "targetRef": None, "reason": reason})
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report only; write nothing")
    args = parser.parse_args(argv)
    document, graph = read(SOURCES), read(GRAPH)
    records = document["sourceRecords"]
    existing = {row["providerRecordKey"] for row in records if row["sourceKind"] == "printed-set-size-record"}
    added = [record(*entry) for entry in SIZES if entry[0] not in existing]
    mirrored = [row for row in [*added, *(r for r in records if r["sourceRecordId"].startswith("SET-SRC-SIZE"))]
                if mirror(graph, row)]
    for row in added:
        print(("pending: " if args.check else "") + f"{row['providerRecordKey']} {row['raw']['printedSetSize']}")
    if args.check:
        return 1 if added or mirrored else 0
    if not added:
        return 0
    records += added  # appended in table order; the store keeps its historical order
    counts = document["meta"]["counts"]
    counts["sourceRecords"] = len(records)
    counts["printedSetSizeRecords"] = sum(row["sourceKind"] == "printed-set-size-record" for row in records)
    graph["summary"]["entities"], graph["summary"]["edges"] = len(graph["entities"]), len(graph["edges"])
    SOURCES.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    GRAPH.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"added {len(added)} printed-set-size records; {counts['printedSetSizeRecords']} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
