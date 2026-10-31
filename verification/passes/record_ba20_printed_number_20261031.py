"""Record the printed collector number 50/68 for Battle Academy 2020 Snorlax (#435).

Cardmarket files the card as `BA20 MWT` (the Mewtwo deck), and `MWT` became the release's
`localNumber`. That value stays: it is the join key to the legacy units and finish units. The card
itself prints the Hidden Fates number 50/68 with the purple Mewtwo deck mark:

* SPEC-0121 (German), SPEC-0145 (French) and SPEC-0466 (Italian) show `50/68` on the card face;
* the Bulbapedia Battle Academy 2020 Mewtwo Deck half-deck list names the card `50/68` and is the
  source for the English release, which has no photograph of its own.

As for DP1's `DPBP#174`, the printed number is recorded as the release's `numberingBasis`, which
the collector catalogue reads before the join key. Idempotent; `--check` reports pending releases.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "verification" / "authoritative_graph.json"
LIST = "https://bulbapedia.bulbagarden.net/wiki/Battle_Academy_2020_(TCG)"
EVIDENCE = {
    "English": ([], [LIST]),
    "French": (["SPEC-0145"], [LIST, "https://www.pokecardex.com/series/ADC-M"]),
    "German": (["SPEC-0121"], [LIST, "https://www.ebay.de/itm/366600950681"]),
    "Italian": (["SPEC-0466"], [LIST, "https://www.ebay.it/itm/174939387384"]),
}


def basis(language: str) -> dict:
    specimens, urls = EVIDENCE[language]
    seen = (f"{', '.join(specimens)} show{'s' if len(specimens) == 1 else ''} 50/68 on the {language} card face; "
            if specimens else "")
    return {
        "kind": "printed-collector-number",
        "collectorNumber": "50/68",
        "note": (f"{seen}the Bulbapedia Mewtwo Deck half-deck list names the card 50/68. The marketplace "
                 "deck code MWT stays the release's join key."),
        "specimenIds": specimens,
        "sourceUrls": urls,
        "recordedAt": "2026-10-31",
    }


def main(argv) -> int:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    pending = []
    for row in graph["entities"]:
        payload = row["payload"]
        if row["entityType"] == "card-release" and ":BA20:MWT:" in row["entityId"]:
            expected = basis(payload["language"])
            if payload.get("numberingBasis") != expected:
                pending.append((row["entityId"], payload, expected))
    if "--check" in argv:
        for release_id, *_ in pending:
            print("pending:", release_id)
        return 1 if pending else 0
    for _, payload, expected in pending:
        payload["numberingBasis"] = expected
    if pending:
        GRAPH.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
