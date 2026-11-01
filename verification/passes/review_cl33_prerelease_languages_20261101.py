#!/usr/bin/env python3
"""Correct two over-broad CL 33 V2 confirmations to unconfirmed application claims."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "verification"
BUNDLE = VERIFY / "evidence/issue-440-cl-prerelease-unconfirmed-20261101"
SOURCE = "https://www.elitefourum.com/t/list-of-all-tcg-cards-that-exist-for-a-specific-pokemon/16709/584"
DATE = "2026-11-01"


def main():
    review = json.loads((BUNDLE / "review.json").read_text(encoding="utf-8"))
    assert hashlib.sha256((BUNDLE / "discussion.json").read_bytes()).hexdigest() == review["discussionSha256"]
    units_path = VERIFY / "units.json"
    units = json.loads(units_path.read_text(encoding="utf-8"))
    targets = {"U0469": ("French", "sibling-derived"), "U0471": ("Italian", "product-or-set")}
    assert set(targets) == set(review["unitIds"])
    before = copy.deepcopy(units)
    journal = VERIFY / "evidence.jsonl"
    observations = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]
    additions = []
    for unit in units:
        if unit["unitId"] not in targets:
            continue
        language, grain = targets[unit["unitId"]]
        assert (unit["setCode"], unit["number"], unit["variant"], unit["language"], unit["status"]) == ("CL", "33", "V2", language, "confirmed")
        prior = copy.deepcopy(unit)
        evidence = (
            f"Unconfirmed {language} CL 33/95 V2 prerelease (owner-directed review, {DATE}). "
            + ("The retained TCGdex record identifies the regular French card, not this prerelease printing. " if language == "French" else "The retained expansion-language source does not establish this distribution promo. ")
            + "Elite Fourum posts 583-584 (2024-10-10) question both French and Italian prerelease entries; "
            "the list author acknowledges that these entries were assumptions and retracts them. "
            "This is research context, not a positive printing record or proof of non-printing. "
            "The historical raw verdict is retained; its reviewed scope projects to needs-evidence. "
            + SOURCE
        )
        unit.update(evidenceGranularity=grain, evidenceIncludesCardList=False, evidence=evidence, checkedAt=DATE)
        key = f"CL33-V2-unconfirmed-{DATE}-{unit['unitId']}"
        if not any(row.get("reviewId") == key for row in observations):
            additions.append({"reviewId": key, "unitId": unit["unitId"], "at": DATE,
                              "status": "confirmed", "applicationStatus": "needs-evidence",
                              "source": SOURCE, "evidence": evidence, "supersededObservation": prior})
    assert all(a == b for a, b in zip(before, units) if a["unitId"] not in targets)
    assert {r["unitId"] for r in units if r["unitId"] in targets} == set(targets)
    # Preserve earlier observations before replacing their reviewed evidence scope.
    with journal.open("a", encoding="utf-8", newline="\n") as handle:
        for observation in additions:
            handle.write(json.dumps(observation, ensure_ascii=False) + "\n")
    units_path.write_text(json.dumps(units,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(f"CL 33 V2 French/Italian reviewed as unconfirmed; {len(additions)} journal observations added")


if __name__ == "__main__":
    main()
