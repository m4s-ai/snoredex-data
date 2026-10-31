"""Settle the four disputed Traditional Chinese Sun & Moon units by owner decision (#440).

Cardmarket claims Traditional Chinese for the Japanese products sm10 076 (U0265), sm9 066 V1
(U0414), sm9 106 V2 (U0634) and sm9 115 V3 (U0558). Asked whether those printings exist, the
collection owner answered on 2026-10-31: "sie existieren aber in den catch up sets/decks die
rausgekommen sind, deswegen gibt es doch die artowrk zuordnung. Also unter anderem set code etc."

That is the same ruling as U0288, U0509 and U0533 (2026-08-03). The Traditional Chinese card exists
under its catch-up identity, which the catalogue already carries as its own positive releases.
Against the Japanese product slot that Cardmarket names, the Traditional Chinese claim is wrong.

* Snorlax (Lazy Eating / Big Counter) is AS5a 142/184.
* Eevee & Snorlax-GX is AS5a 117/184 RR, 203/184 and 204/184 SR, 222/184 HR, and AS5D 118/169.

The decision concerns the legacy product slot only. It asserts nothing about the catch-up
printings, which keep their own evidence.

Idempotent; `--check` reports pending decisions without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADJUDICATIONS = ROOT / "verification" / "owner_adjudications.json"
QUOTE = ("sie existieren aber in den catch up sets/decks die rausgekommen sind, deswegen gibt es doch "
         "die artowrk zuordnung. Also unter anderem set code etc.")
CATCH_UP = {
    "U0265": ("sm10 076", "AS5a 142/184 (Snorlax, Lazy Eating / Big Counter)"),
    "U0414": ("sm9 066 V1", "AS5a 117/184 RR and AS5D 118/169 (Eevee & Snorlax-GX)"),
    "U0634": ("sm9 106 V2", "AS5a 203/184 and 204/184 SR (Eevee & Snorlax-GX)"),
    "U0558": ("sm9 115 V3", "AS5a 222/184 HR (Eevee & Snorlax-GX)"),
}


def decision(unit_id: str) -> dict:
    product, catch_up = CATCH_UP[unit_id]
    return {
        "adjudicationId": f"OA-20261031-{unit_id}",
        "unitId": unit_id,
        "decision": "not-printed",
        "authority": "collection-owner",
        "basis": "multi-source-adjudication",
        "decidedAt": "2026-10-31",
        "rationale": (
            f"The Traditional Chinese card exists, but under its catch-up identity rather than as the "
            f"Japanese product {product}: \"{QUOTE}\" The catalogue carries it as {catch_up}. "
            "Cardmarket claims Traditional Chinese against the Japanese product, and against that "
            "product the claim is wrong. Same ruling as U0288, U0509 and U0533."),
        "evidenceRefs": ["https://github.com/m4s-ai/snoredex-data/issues/440", f"unit:{unit_id}"],
    }


def main(argv) -> int:
    document = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    present = {row["unitId"] for row in document["decisions"]}
    pending = [decision(unit_id) for unit_id in CATCH_UP if unit_id not in present]
    if "--check" in argv:
        for row in pending:
            print("pending:", row["adjudicationId"])
        return 1 if pending else 0
    if pending:
        document["decisions"] += pending
        ADJUDICATIONS.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
