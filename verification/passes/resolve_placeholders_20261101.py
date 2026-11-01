"""Resolve the last three research placeholders of #439 (2026-11-01).

* JP XY2 066 Unlimited: SPEC-0670, the Elite Fourum image with an empty 1st Edition mark position
  captioned "non-Holo UED", establishes the Unlimited non-holo printing.
* TH MA3 136 Hop's Snorlax: SPEC-0671, an eBay seller photograph, shows the regular card in holo.
* TW M2a F 136 Hop's Snorlax: SPEC-0672, a Shopee photograph, shows the regular card in holo.

The Thai specimen is filed under the printed code MA3, while the legacy Cardmarket finish unit is
m2a 136. A `releaseSetCode` bridge joins them, as for the Indonesian MA3 I and the Traditional
Chinese M2a F rows. Each retired `-unresolved` checklist id gets a reviewed route to its printing,
and the #445 size routes that ended at those ids now point straight at the printing, so no route
chains.

Idempotent; `--check` reports pending changes.
"""
import json
import sys
from pathlib import Path

V = Path(__file__).resolve().parents[2] / "verification"
ROUTES = V / "collector_migration_routes.json"
OVERRIDES = V / "finish_overrides.json"
REASON = "Research placeholder resolved by the printing evidenced on 2026-11-01 (#439)."
REKEYS = {
    "xy2-066-japanese-unl-unresolved": "xy2-066-japanese-unl-non-holo",
    "m2a-136-thai-none-unresolved": "m2a-136-thai-none-holo",
    "m2a-136-t-chinese-none-unresolved": "m2a-136-t-chinese-none-holo",
}
TH_BRIDGE = {"setCode": "m2a", "releaseSetCode": "MA3", "number": "136", "languages": ["Thai"], "printings": []}


def collapse_chains(text: str) -> str:
    for old, new in REKEYS.items():
        for row in json.loads(text)["cumulativeChecklistRekeys"]:
            if row["to"] == old:
                text = text.replace(json.dumps(row, ensure_ascii=False),
                                    json.dumps({"from": row["from"], "to": new, "reason": row["reason"]},
                                               ensure_ascii=False))
    return text


def write_routes(original: str, text: str, routes: list) -> None:
    if routes:
        lines = ",\n".join("    " + json.dumps(row, ensure_ascii=False) for row in routes)
        marker = "\n  ],\n  \"cardReleaseRekeys\""
        text = text.replace(marker, ",\n" + lines + marker, 1)
    if text != original:
        ROUTES.write_text(text, encoding="utf-8", newline="\n")


def main(argv) -> int:
    original = ROUTES.read_text(encoding="utf-8")
    text = collapse_chains(original)
    present = {row["from"] for row in json.loads(text)["cumulativeChecklistRekeys"]}
    routes = [{"from": old, "to": new, "reason": REASON} for old, new in REKEYS.items() if old not in present]
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    bridge = TH_BRIDGE not in overrides["overrides"]
    if "--check" in argv:
        for row in routes:
            print("pending: route", row["from"])
        if text != original:
            print("pending: collapse routes that ended at a retired placeholder id")
        if bridge:
            print("pending: Thai m2a 136 -> MA3 bridge")
        return 1 if routes or text != original or bridge else 0
    write_routes(original, text, routes)
    if bridge:
        overrides["overrides"].append(TH_BRIDGE)
        out = json.dumps(overrides, ensure_ascii=False, indent=2) + "\n"
        # The store keeps one hand-written compact list; preserve it byte for byte.
        out = out.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
        OVERRIDES.write_text(out, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
