#!/usr/bin/env python3
"""Admit owner adjudications into the finish layer, and record the first one (#119).

WHY THE MODEL HAD TO CHANGE

`mP1 012` Japanese is documented non-holo from SPEC-0025, and the owner ruled that non-holo is the
only finish. There was nowhere to put that ruling. `completenessStatus=complete-manifest` is derived
from a source that explicitly covers the unit's language, and `FINISH_SOURCES.md` puts owner
attestation in the row that cannot establish absence — deliberately, because a collector's memory is
not a manifest.

Probing confirmed no manifest exists for this product: `/ex/mP1/` is a 404, the official card page
carries no finish vocabulary at all, and the CoroCiao page is an event page. The control `/ex/m2a/`
returns ミラー仕様 and レアリティ, so the technique works and the page simply is not published for a
magazine-bonus deck. The owner's conclusion: "Es gibt keine offizielle Quelle die das explizit nennt,
hier müssen wir auch auf owner adjudikation setzen."

That is the same argument rule 4 already accepts for languages, where 58 units rest on it. The
finish layer was the half that never got the mechanism.

THE SHAPE, WHICH MIRRORS THE LANGUAGE LAYER

The decision does not overwrite the evidence. `owner_adjudications.json` gains a second array,
`finishDecisions`, and `scripts/finishes.py` projects it into a *distinct* completeness value:

    complete-manifest      a source explicitly covers this unit's language   (unchanged, 4 units)
    owner-adjudicated      the collection owner ruled, with no such source   (new)
    positive-evidence-only finishes found; others unevidenced, not excluded  (unchanged)

Keeping them apart is the point. A consumer that trusts only manufacturer manifests can still tell
the two apart, exactly as `repository_verdict` and `application_status` stay separable for languages,
and the adjudication is never attributed to a provider.

Decisions are keyed by (setCode, number, language) rather than by `finishUnitId`: the F-numbers are
positional and would silently retarget if the corpus grew.

WHAT IT DOES NOT DO

It does not touch `availableFinishes` or any printing. Non-holo was already confirmed from the
specimen; this records only that the list is closed. And it stays inapplicable to a unit with no
positive evidence at all: adjudicating a finish set for a unit nothing is known about would be an
absence argument wearing the owner's name.

Idempotent: re-running changes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADJUDICATIONS = ROOT / "verification" / "owner_adjudications.json"

DECIDED_AT = "2026-08-08"

DECISION = {
    "adjudicationId": f"OAF-{DECIDED_AT.replace('-', '')}-mP1-012-ja",
    "setCode": "mP1",
    "number": "012",
    "language": "Japanese",
    "decision": "finish-complete",
    "availableFinishes": ["non-holo"],
    "authority": "collection-owner",
    "basis": "owner-adjudication",
    "decidedAt": DECIDED_AT,
    "rationale": (
        "The collection owner ruled that this printing exists in non-holo only: \"Es gibt keine "
        "offizielle Quelle die das explizit nennt, hier müssen wir auch auf owner adjudikation "
        "setzen.\" Non-holo itself is documented from SPEC-0025, a SNKRDUNK listing photograph "
        "showing a uniformly matte card face. No official manifest exists to close the list: "
        "pokemon-card.com publishes no /ex/ page for this magazine-bonus fixed deck, its card page "
        "carries no finish vocabulary, and the CoroCiao page is an event page — probed 2026-08-08 "
        "with /ex/m2a/ as a working control. Recorded as an owner decision rather than as a "
        "manifest, and never attributed to a provider."
    ),
    "evidenceRefs": [
        "specimen:SPEC-0025",
        "https://github.com/m4s-ai/snoredex-data/issues/119",
    ],
}

POLICY_ADDITION = (
    "A finish decision closes the finish list for one set-number-language unit. It never asserts a "
    "finish: every finish it names must already rest on positive evidence, and the decision only "
    "states that no others exist. It projects to completenessStatus=owner-adjudicated, which is "
    "deliberately distinct from complete-manifest so a consumer can tell a collector's ruling from "
    "a manufacturer's."
)


def main() -> int:
    document = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    decisions = document.setdefault("finishDecisions", [])

    key = (DECISION["setCode"], DECISION["number"], DECISION["language"])
    if any((d["setCode"], d["number"], d["language"]) == key for d in decisions):
        print(f"{key} already adjudicated; nothing to do")
        return 0

    decisions.append(DECISION)
    decisions.sort(key=lambda d: d["adjudicationId"])

    policy = document["meta"].setdefault("policy", [])
    if POLICY_ADDITION not in policy:
        policy.append(POLICY_ADDITION)
    document["meta"]["schemaVersion"] = "1.1.0"

    ADJUDICATIONS.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{DECISION['adjudicationId']}: mP1 012 Japanese -> finish-complete "
          f"{DECISION['availableFinishes']} ({len(decisions)} finish decisions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
