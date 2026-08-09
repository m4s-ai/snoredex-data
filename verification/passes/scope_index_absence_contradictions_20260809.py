#!/usr/bin/env python3
"""Stop five contradictions claiming a card does not exist in a language it demonstrably does (#137).

#137 names the pattern: a pass "contradicts a card because a cross-language expansion index has no
entry", and separately warns to "separate 'this local print does not exist' from 'the same card
exists under a different local identity'". Five units are that pattern, and each is now falsifiable
from evidence already in this repository.

Each reads, verbatim:

    expansion <X> has NO T-Chinese entry in the cross-language expansion index, so no T-Chinese
    printing of this card should exist

The index's silence is real and the narrow reading is fine — there is no Traditional Chinese
edition of the Japanese `s1H`/`s2` sets. The sentence does not say that. It says **this card** has
no Traditional Chinese printing, and that is false: every one of the five has a corroborated
Traditional Chinese printing under its own catch-up set code, admitted under ADR-0001 decision D1.

    U0288  s1H 46  ->  TW:sc1b F:120/153   SPEC-0007
    U0509  s1H 70  ->  TW:sc1b F:177/153   SPEC-0008
    U0512  s1H 45  ->  TW:sc1b F:119/153   SPEC-0009
    U0533  s2  77  ->  TW:sc1a F:127/154   SPEC-0011
    U0549  s1H 66  ->  TW:sc1b F:165/153   SPEC-0010

WHAT THIS DOES NOT DO

It does not change a verdict. The units stay `contradicted`, because the claim they answer is
Cardmarket's — that the *Japanese product* is available in Traditional Chinese — and that claim is
still refuted. What changes is the inference the sentence licenses. #137 puts it exactly: historical
evidence remains queryable, only its permitted inference changes.

It does not delete the original observation either. The correction is appended, so a reader can see
what was concluded, what it rested on, and why the conclusion was narrowed. A correction that erases
what it corrects leaves nobody able to check it.

THE ONE THAT WAS ALREADY RIGHT

`U0265` (sm10 076, Traditional Chinese) reaches the same verdict from the market-history argument
and is deliberately left alone. Its own text already carries the scope: "Note: the card itself may
exist in Traditional Chinese via a later catch-up set, but not as a printing of this set." That is
the distinction #137 asks for, written before the catch-up print was admitted. It needs no repair
and receives none.

    python verification/passes/scope_index_absence_contradictions_20260809.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"
PRINTS = ROOT / "verification" / "source_first_prints.json"

MARKER = "SCOPE CORRECTION 2026-08-09"

# unitId -> the admitted printing that falsifies the card-level reading
FALSIFIED_BY = {
    "U0288": "TW:sc1b F:120/153:base",
    "U0509": "TW:sc1b F:177/153:base",
    "U0512": "TW:sc1b F:119/153:base",
    "U0533": "TW:sc1a F:127/154:base",
    "U0549": "TW:sc1b F:165/153:base",
}


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    by_id = {u["unitId"]: u for u in units}
    prints = {p["printId"]: p for p in json.loads(PRINTS.read_text(encoding="utf-8"))["prints"]}

    corrected = 0
    for unit_id, print_id in FALSIFIED_BY.items():
        unit = by_id.get(unit_id)
        record = prints.get(print_id)
        if unit is None or record is None:
            print(f"missing {unit_id} or {print_id}", file=sys.stderr)
            return 1
        if unit["status"] != "contradicted":
            print(f"{unit_id} is {unit['status']}, expected contradicted", file=sys.stderr)
            return 1
        if MARKER in unit["evidence"]:
            continue
        unit["evidence"] = unit["evidence"].rstrip().rstrip(".") + (
            f". {MARKER}: the index's silence supports only the narrow claim — the Japanese "
            f"{unit['setCode']} set has no Traditional Chinese edition. It does not support the "
            f"sentence above about this *card*, which does exist in Traditional Chinese as "
            f"{record['localSetCode']} {record['localNumber']} ({print_id}), admitted under "
            f"ADR-0001 D1 from {record['specimenId']} and corroborated by "
            f"{record['providerId']}. The verdict is unchanged and still answers Cardmarket's "
            f"claim about the Japanese product; only the absence inference is narrowed. A missing "
            f"row in a cross-language expansion index is silence about a catch-up release, never "
            f"evidence against one."
        )
        corrected += 1

    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"narrowed {corrected} card-level absence inference(s) to the set slot they can support")
    for unit_id, print_id in sorted(FALSIFIED_BY.items()):
        unit = by_id[unit_id]
        print(f"  {unit_id}  {unit['setCode']:4} {unit['number']:4} {unit['language']:10} "
              f"still contradicted, falsified card-level reading -> {print_id}")
    print("  U0265 left unchanged: its own text already scopes the claim to the set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
