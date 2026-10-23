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
size and are not recorded; sets with no source stay without a size. The unnumbered Japanese
releases (DP1, EXS, G2, PJU, UNP; their card-release ids say `unnumbered`) print no denominator
and take none.

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
    ("Pt2", 90, "JP", None, ["SPEC-0571", "SPEC-0582", "SPEC-0635", "SPEC-0636"]),
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
# Gallery subsets ship inside their main set and print their own run (TG10/TG30). They are a
# separate record kind so the main set's size, which decides run membership, stays untouched.
# (legacy set code, subset prefix, printed subset size, region, TCGdex subset id)
SUBSETS = [
    ("LOR", "TG", 30, "WEST", "swsh11tg"),
]
# Read from the printed face of the catalogue's own retained card images (owner request,
# 2026-10-23: check the cards of the sets still without a denominator). A product image attests
# the printed text, like an illustrator credit; no physical-printing claim is made.
# (legacy set code, printed size, region, printed evidence)
PRINTED = [
    ("sI100", 414, "JP", ["images/sI100_341_Snorlax_V1_588051.jpg", "images/sI100_342_Snorlax_V2_588052.jpg"]),
    ("sA", 23, "JP", ["SPEC-0462"]),
    ("sN", 24, "JP", ["SPEC-0058", "SPEC-0059", "SPEC-0060", "SPEC-0063"]),
    ("CLF", 32, "JP", ["SPEC-0319", "SPEC-0320", "SPEC-0321"]),
    ("svM", 175, "JP", ["SPEC-0272", "SPEC-0389", "SPEC-0464"]),
    ("mP1", 23, "JP", ["SPEC-0025"]),
    ("xsv2a", 165, "JP", ["SPEC-0061", "SPEC-0612"]),
    ("xm2a", 193, "JP", ["SPEC-0410", "SPEC-0437"]),
    ("CLV", 34, "WEST", ["images/CLV_016_Snorlax_745674.jpg"]),
    ("CS1DC", 207, "CN", ["images/CS1DC_152_Snorlax_887087.png"]),
    ("CSAC", 24, "CN", ["images/CSAC_009_Snorlax_V_882263.png"]),
    ("CSM2.1C", 45, "CN", ["SPEC-0147"]),
    ("CS3DC", 170, "CN", ["images/CS3DC_117_Snorlax_882597.png"]),
    ("CS5DC", 153, "CN", ["images/CS5DC_097_Snorlax_V1_882375.png", "images/CS5DC_098_Snorlax_V2_882376.png"]),
    ("CSUC", 12, "CN", ["SPEC-0153"]),
    ("CSZC", 66, "CN", ["images/CSZC_018_Snorlax_854381.png"]),
    ("151C", 151, "CN", ["images/151C_143_Snorlax_V1_819209.jpg", "images/151C_169_Snorlax_V2_819235.jpg"]),
    ("CSVE1C", 177, "CN", ["images/CSVE1C_093_Snorlax_877905.png"]),
    ("CSVL1C", 49, "CN", ["SPEC-0154"]),
    ("CSVE2C", 207, "CN", ["images/CSVE2C_122_Snorlax_887279.png"]),
    ("CSV10C", 222, "CN", ["images/CSV10C_175_Hop_s_Snorlax_897733.png"]),
]
# Database-prefixed numbers whose card prints the bare number: a001 prints 001/023.
# (legacy set code, catalogue prefix, printed size, region, printed evidence)
PRINTED_SUBSETS = [
    ("CSMPC", "h", 24, "CN", ["SPEC-0431", "SPEC-0432"]),
    ("CSVH1C", "a", 23, "CN", ["SPEC-0619"]),
    ("CSVH4C", "a", 23, "CN", ["SPEC-0630"]),
    ("CSVH4C", "p", 6, "CN", ["images/CSVH4C_p006_Snorlax_ex_888095.png"]),
]


def printed_basis(refs: list[str]) -> tuple[str, str]:
    """Provider and basis for a size read from retained card faces."""
    cited = [ref if ref.startswith("SPEC-") else
             f"{ref} (sha256 {hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()})" for ref in refs]
    provider = "inspected-specimen" if any(ref.startswith("SPEC-") for ref in refs) else "cardmarket-product-image"
    return provider, f"Read from the printed face of retained card images: {', '.join(cited)}."


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def tcgdex_count(language: str, set_id: str) -> int:
    rows = read(ROOT / BUNDLE / f"sets-{language}.json")
    return next(row["cardCount"]["official"] for row in rows if row["id"] == set_id)


def printed_record(code: str, size: int, region: str, refs: list[str]) -> dict:
    provider, basis = printed_basis(refs)
    return {
        "sourceRecordId": stable_id("SET-SRC-SIZE", code),
        "sourceKind": "printed-set-size-record",
        "provider": provider,
        "providerRecordKey": code,
        "retrieved": RETRIEVED,
        "raw": {"legacySetCode": code, "printedSetSize": size, "numbering": NUMBERING[region][0],
                "basis": f"The denominator {size} printed beside the collector number. {basis}"},
    }


def printed_subset_record(code: str, prefix: str, size: int, region: str, refs: list[str]) -> dict:
    provider, basis = printed_basis(refs)
    return {
        "sourceRecordId": stable_id("SET-SRC-SUBSET", code, prefix),
        "sourceKind": "printed-subset-size-record",
        "provider": provider,
        "providerRecordKey": f"{code}\x1f{prefix}",
        "retrieved": RETRIEVED,
        "raw": {"legacySetCode": code, "subsetPrefix": prefix, "printedSubsetSize": size,
                "denominatorPrefix": "", "numbering": NUMBERING[region][0],
                "basis": (f"The catalogue number carries the database prefix {prefix!r}; the card prints "
                          f"the bare number over {size:03d}. {basis}")},
    }


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


def subset_record(code: str, prefix: str, size: int, region: str, set_id: str) -> dict:
    numbering, language = NUMBERING[region]
    path = f"{BUNDLE}/sets-{language}.json"
    if tcgdex_count(language, set_id) != size:
        raise ValueError(f"{code} {prefix}: retained TCGdex count differs from {size}")
    sha = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    return {
        "sourceRecordId": stable_id("SET-SRC-SUBSET", code, prefix),
        "sourceKind": "printed-subset-size-record",
        "provider": "tcgdex",
        "providerRecordKey": f"{code}\x1f{prefix}",
        "retrieved": RETRIEVED,
        "sourceUrl": f"https://api.tcgdex.net/v2/{language}/sets/{set_id}",
        "raw": {"legacySetCode": code, "subsetPrefix": prefix, "printedSubsetSize": size,
                "numbering": numbering,
                "basis": (f"TCGdex {language} subset {set_id} cardCount.official {size}: the gallery subset "
                          f"ships inside {code} and prints {prefix}nn/{prefix}{size}; retained set list "
                          f"{path} (sha256 {sha}). The owner confirmed on 2026-10-23 that galleries are "
                          f"subsets delivered with their main set.")},
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
    present = {row["sourceRecordId"] for row in records}
    added = [record(*entry) for entry in SIZES if entry[0] not in existing]
    added += [printed_record(*entry) for entry in PRINTED if entry[0] not in existing]
    added += [row for row in [*(subset_record(*entry) for entry in SUBSETS),
                              *(printed_subset_record(*entry) for entry in PRINTED_SUBSETS)]
              if row["sourceRecordId"] not in present]
    mirrored = [row for row in [*added, *(r for r in records if r["sourceRecordId"].startswith(("SET-SRC-SIZE", "SET-SRC-SUBSET")))]
                if mirror(graph, row)]
    for row in added:
        size = row["raw"].get("printedSetSize") or row["raw"]["printedSubsetSize"]
        print(("pending: " if args.check else "") + f"{row['providerRecordKey']} {size}")
    if args.check:
        return 1 if added or mirrored else 0
    if not added:
        return 0
    records += added  # appended in table order; the store keeps its historical order
    counts = document["meta"]["counts"]
    counts["sourceRecords"] = len(records)
    counts["printedSetSizeRecords"] = sum(row["sourceKind"] == "printed-set-size-record" for row in records)
    counts["printedSubsetSizeRecords"] = sum(row["sourceKind"] == "printed-subset-size-record" for row in records)
    graph["summary"]["entities"], graph["summary"]["edges"] = len(graph["entities"]), len(graph["edges"])
    SOURCES.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    GRAPH.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"added {len(added)} printed-set-size records; {counts['printedSetSizeRecords']} total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
