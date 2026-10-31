"""Join seven research placeholders to the specimen printings of the same card (#439).

Each placeholder is a legacy Cardmarket finish unit with no printing, while a specimen of the same
card release already established a printing under its printed local code. The two never met, so
the catalogue showed the card twice: once photographed, once as an open research slot.

| Placeholder (Cardmarket) | Printed card | Specimen |
|---|---|---|
| KR DP-P 127 | DP 006 Snorlax LV.X, holo | SPEC-0440 |
| KR SM-P 1 | 017/SM-P Snorlax-GX, holo | SPEC-0625 |
| KR SM-P 297 | 140/SM-P Eevee & Snorlax-GX, holo ripple | SPEC-0028 |
| TW PKMTCH S-P 145 | 145/S-P Snorlax, mirror holo | SPEC-0030 |
| KR sA 10 | sA 010/023 Snorlax, non-holo | SPEC-0462 |
| KR svIba 046 | svI 046/066 Snorlax, non-holo | SPEC-0463 |
| ID svM 094 | SVM I 094/175 Snorlax ex, holo | SPEC-0609 |

A `releaseSetCode`/`releaseNumber` bridge lets each specimen join its legacy unit, as for the
Kisstick (167/XY-P -> XY-P 149) and Korean s2/sv4K bridges. For the four promos, pokumon.com's
per-card records (Cosmos, Ripple, Ripple, Mirror/Reverse) agree with the specimens.

Each retired `-unresolved` checklist id gets a reviewed route to the joined printing's id, so state
recorded on the research slot moves with it. The reviewed release date of the KR SM-P 140 slot is
dropped: the photographed holo row of the same release carries the same 2019-03-20 date.

Idempotent; `--check` reports pending changes.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = ROOT / "verification" / "finish_overrides.json"
ROUTES = ROOT / "verification" / "collector_migration_routes.json"
DATES = ROOT / "verification" / "confirmed_release_overrides.json"
REASON = "Research placeholder joined to the specimen printing of the same card release (#439)."
REKEYS = {
    "dp-p-127-korean-none-unresolved": "dp-p-127-korean-none-holo",
    "sm-p-1-korean-none-unresolved": "sm-p-1-korean-none-holo",
    "sm-p-297-korean-none-unresolved": "sm-p-297-korean-none-holo-ripple",
    "pkmtch-s-p-s-p-145-t-chinese-none-unresolved": "pkmtch-s-p-s-p-145-t-chinese-none-mirror-holo",
    "sa-10-korean-none-unresolved": "sa-10-korean-none-non-holo",
    "sviba-046-korean-none-unresolved": "sviba-046-korean-none-non-holo",
    "svm-094-indonesian-none-unresolved": "svm-094-indonesian-none-holo",
}
RETIRED_DATE_ITEM = "item-21227d52-c2c4-5c5c-a73f-b29329cb58e4"
# The photographed SM-P 140 holo row keeps its date; the joined printing has a new identity.
RETARGET_DATE = ("item-f9a028a1-6b5a-5816-a3d5-1a28fc1b21bc", {
    "itemId": "item-55db1b6d-db98-5e03-8465-46bdf1ee63c2",
    "physicalPrintingId": "PHYSICAL:PRINTING:1ace46fc14262589b4bcb2bc",
    "sourcePrintingId": "F0401-P01",
    "legacyChecklistIds": ["sm-p-297-korean-none-holo-ripple"],
})
BRIDGES = [
    {"setCode": "DP-P", "releaseSetCode": "DP", "releaseNumber": "006", "number": "127",
     "languages": ["Korean"], "printings": []},
    {"setCode": "SM-P", "releaseSetCode": "SM-P", "releaseNumber": "017", "number": "1",
     "languages": ["Korean"], "printings": []},
    {"setCode": "SM-P", "releaseSetCode": "SM-P", "releaseNumber": "140", "number": "297",
     "languages": ["Korean"], "printings": []},
    {"setCode": "sA", "releaseSetCode": "sA", "releaseNumber": "010", "number": "10",
     "languages": ["Korean"], "printings": []},
    {"setCode": "svIba", "releaseSetCode": "svI", "releaseNumber": "046", "number": "046",
     "languages": ["Korean"], "printings": []},
    {"setCode": "svM", "releaseSetCode": "SVM I", "releaseNumber": "094", "number": "094",
     "languages": ["Indonesian"], "printings": []},
]
# The Traditional-Chinese unit already carries a releaseSetCode bridge; it lacked the printed number.
TW_ROW = {"setCode": "PKMTCH S-P", "releaseSetCode": "S-P", "number": "S-P 145",
          "languages": ["T-Chinese"], "printings": []}


def collapse_chains(text: str) -> str:
    """Point earlier routes that ended at a retired placeholder id straight at its new id.

    The #445 size routes took `X-unresolved-unknown` to `X-unresolved` and kept the item id; that
    placeholder item is now the photographed printing, so the route ends at the printing's id.
    """
    for old, new in REKEYS.items():
        for row in json.loads(text)["cumulativeChecklistRekeys"]:
            if row["to"] == old:
                text = text.replace(json.dumps(row, ensure_ascii=False),
                                    json.dumps({"from": row["from"], "to": new, "reason": row["reason"]},
                                               ensure_ascii=False))
    return text


def main(argv) -> int:
    document = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    rows = document["overrides"]
    pending = [row for row in BRIDGES if row not in rows]
    tw = next((row for row in rows if row.get("setCode") == "PKMTCH S-P"), None)
    tw_pending = tw is not None and tw.get("releaseNumber") != "145"
    routes_text = collapse_chains(ROUTES.read_text(encoding="utf-8"))
    present = {row["from"] for row in json.loads(routes_text)["cumulativeChecklistRekeys"]}
    chained = routes_text != ROUTES.read_text(encoding="utf-8")
    routes = [{"from": old, "to": new, "reason": REASON} for old, new in REKEYS.items() if old not in present]
    dates = json.loads(DATES.read_text(encoding="utf-8"))
    stale_date = any(row["itemId"] in (RETIRED_DATE_ITEM, RETARGET_DATE[0])
                     for row in dates["releaseDates"]["reviewedItems"])
    if "--check" in argv:
        for row in routes:
            print("pending: route", row["from"])
        if stale_date:
            print("pending: retire or retarget the KR SM-P 140 dates")
        for row in pending:
            print("pending: bridge", row["setCode"], row["number"], "<-", row["releaseSetCode"], row["releaseNumber"])
        if tw_pending:
            print("pending: PKMTCH S-P 145 releaseNumber")
        if chained:
            print("pending: collapse routes that ended at a retired placeholder id")
        return 1 if pending or tw_pending or routes or stale_date or chained else 0
    if chained and not routes:
        ROUTES.write_text(routes_text, encoding="utf-8", newline="\n")
    if routes:
        lines = ",\n".join("    " + json.dumps(row, ensure_ascii=False) for row in routes)
        marker = "\n  ],\n  \"cardReleaseRekeys\""
        ROUTES.write_text(routes_text.replace(marker, ",\n" + lines + marker, 1), encoding="utf-8", newline="\n")
    if stale_date:
        dates["releaseDates"]["reviewedItems"] = [row for row in dates["releaseDates"]["reviewedItems"]
                                                  if row["itemId"] != RETIRED_DATE_ITEM]
        for row in dates["releaseDates"]["reviewedItems"]:
            if row["itemId"] == RETARGET_DATE[0]:
                row.update(RETARGET_DATE[1])
        DATES.write_text(json.dumps(dates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    if tw is None:
        raise SystemExit(f"expected the reviewed row {TW_ROW}")
    if tw_pending:
        tw["releaseNumber"] = "145"
    rows += pending
    if pending or tw_pending:
        text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        # The store keeps one hand-written compact list; preserve it byte for byte.
        text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
        OVERRIDES.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
