"""Close Spanish Diamond & Pearl 37 at non-holo and correct the Spanish DP checklist reading (2026-11-02).

The Spanish reverse holo of DP 37 had been recorded from the official Spanish Diamond & Pearl
checklist (`dp-official-checklist-es`) with the English checklist's "Parallel Set" reading. The
Spanish PDF has no such legend. It reads "Cartas 18-119: aparecen en una versión no foil.", while
the English checklist says "Cards 18-119: come in foil versions and non-foil versions." The German,
French and Italian checklists match the English one. A re-read of all 82 localized checklists
behind finish rows found no other mismatch.

* The checklist now supports only the non-holo of Spanish DP 37; its reverse-holo row is removed
  and the source text records what the PDF actually says.
* Owner decision: the owner asked for further research and, if nothing confirmed a Spanish
  reverse holo, to record it as not printed ("wenn nicht setzen wir es auf grund dieser
  informationen auf not printed als reverse holo"). Nothing confirmed one; Bulbapedia's
  Diamond & Pearl page (revision 4590179), Quuador's sets-and-languages list and dromanyte on
  Elite Fourum (thread 48558, post 9: "The sets that lacked RH variants in Spanish/Portuguese
  are: DP Base Set ...") say the Spanish set had none.

Evidence: `verification/evidence/issue-438-es-dp-checklist-20261102/`. Idempotent; `--check`
reports pending records without writing.
"""
import json
import sys
from pathlib import Path

V = Path(__file__).resolve().parents[2] / "verification"
ADJUDICATIONS = V / "owner_adjudications.json"
OVERRIDES = V / "finish_overrides.json"
DATE = "2026-11-02"
SOURCE_ID = "dp-official-checklist-es"
QUOTE = "wenn nicht setzen wir es auf grund dieser informationen auf not printed als reverse holo"
EVIDENCE = (
    "The complete localized Diamond & Pearl checklist lists 37 Snorlax; its legend reads \"Cartas "
    "18-119: aparecen en una versión no foil.\" and has no Parallel Set entry (the English checklist: "
    "\"Cards 18-119: come in foil versions and non-foil versions.\"). It supports the non-holo only. "
    "Re-read 2026-11-02 (PDF SHA-256 d79480876287ccd76033c086e50c8459fd2376dd8c44051a77e5ad4562858908); "
    "the earlier reading had carried over the English Parallel Set legend.")
DECISION = {
    "adjudicationId": "OAF-20261102-DP-37-es",
    "setCode": "DP",
    "number": "37",
    "language": "Spanish",
    "decision": "finish-complete",
    "availableFinishes": ["non-holo"],
    "rejectedFinishes": ["reverse-holo"],
    "authority": "collection-owner",
    "basis": "owner-adjudication",
    "decidedAt": DATE,
    "rationale": (
        f"The collection owner ruled that, unless a Spanish reverse holo was confirmed, it is recorded as "
        f"not printed: \"{QUOTE}\". No confirmation was found. The official Spanish checklist prints "
        "cards 18-119 in a non-foil version only; Bulbapedia's Diamond & Pearl page, Quuador's "
        "sets-and-languages list and an Elite Fourum post on the Panini-era Spanish sets say the Spanish "
        "set had no reverse holos. Recorded as an owner decision, never attributed to a provider."),
    "evidenceRefs": [
        "https://assets.pokemon.com/assets/cms2-es-es/pdf/trading-card-game/checklist/dp1_web_cardlist_es.pdf",
        "https://bulbapedia.bulbagarden.net/w/index.php?oldid=4590179",
        "https://www.elitefourum.com/t/sets-and-languages-compilation-overview-list/16565",
        "https://www.elitefourum.com/t/48558/9",
        "https://github.com/m4s-ai/snoredex-data/issues/438",
    ],
}


def spanish_row(overrides: dict) -> dict:
    return next(row for row in overrides["overrides"]
                if (row.get("setCode"), row.get("number"), row.get("languages")) == ("DP", "37", ["Spanish"]))


def write(path: Path, document: dict, compact_dates: bool = False) -> None:
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if compact_dates:
        # The overrides store keeps one hand-written compact list; preserve it byte for byte.
        text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
    path.write_text(text, encoding="utf-8", newline="\n")


def main(argv) -> int:
    adjudications = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    row = spanish_row(overrides)
    reverse = [p for p in row["printings"] if p["finish"] == "reverse-holo"]
    source = overrides["sources"][SOURCE_ID]
    text_pending = source["evidence"] != EVIDENCE or source.get("retrievedAt") != DATE
    decision = DECISION["adjudicationId"] not in {r["adjudicationId"] for r in adjudications["finishDecisions"]}
    if "--check" in argv:
        for label, pending in (("Spanish DP 37 reverse-holo row", reverse),
                               ("checklist reading", text_pending), (DECISION["adjudicationId"], decision)):
            if pending:
                print("pending:", label)
        return 1 if reverse or text_pending or decision else 0
    if reverse or text_pending:
        row["printings"] = [p for p in row["printings"] if p["finish"] != "reverse-holo"]
        source["evidence"] = EVIDENCE
        source["retrievedAt"] = DATE
        write(OVERRIDES, overrides, compact_dates=True)
    if decision:
        adjudications["finishDecisions"].append(DECISION)
        write(ADJUDICATIONS, adjudications)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
