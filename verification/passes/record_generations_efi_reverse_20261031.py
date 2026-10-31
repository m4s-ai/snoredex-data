"""Extend the retained Generations reverse-holo statement to English, French and Italian (#438).

The Bulbapedia revision retained under issue #266
(`verification/evidence/issue-266-generations-reverse-20260908.json`, oldid 4587656, response
hash recorded there) states: "Cards in the English, German, French, Italian, and Spanish sets were
also available as Reverse Holos." Only the Spanish row was applied then. The same statement names
English, French and Italian, whose GEN 58/83 releases are already established, so each gets the
same positive reverse-holo source. German has no GEN 58 finish candidate; Portuguese is not named
and is left untouched (no absence is inferred).

Idempotent; `--check` reports pending records without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OVERRIDES = ROOT / "verification" / "finish_overrides.json"
LANGUAGES = ["English", "French", "Italian"]
SOURCE_REF = "bulbapedia-generations-efi-reverse-20261031"
SOURCE = {
    "url": "https://bulbapedia.bulbagarden.net/w/index.php?title=Generations_(TCG)&oldid=4587656",
    "sourceType": "Bulbapedia localized Generations finish description",
    "authorityTier": "specialist-reference",
    "coverage": "positive-only",
    "supportsAbsence": False,
    "languages": LANGUAGES,
    "claimFields": ["finish"],
    "retrievedAt": "2026-09-08",
    "evidence": (
        "The retained revision (verification/evidence/issue-266-generations-reverse-20260908.json) "
        "names Snorlax 58/83 as Rare and states that cards in the English, German, French, Italian "
        "and Spanish sets were also available as Reverse Holos. Applied only to the already "
        "established English, French and Italian GEN 58 releases. No ordinary finish, stamp, "
        "edition or absence is inferred."),
    "evidenceScope": "standard-set",
}


def override(language: str) -> dict:
    return {"setCode": "GEN", "number": "58", "languages": [language], "printings": [{
        "finish": "reverse-holo", "foilPattern": None, "markings": None, "distribution": None,
        "cardSize": "standard", "mappedVariants": ["base"], "verificationStatus": "confirmed",
        "sourceRefs": [SOURCE_REF]}]}


def main(argv) -> int:
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    rows = [override(language) for language in LANGUAGES]
    rows = [row for row in rows if row not in overrides["overrides"]]
    source = SOURCE_REF not in overrides["sources"]
    if "--check" in argv:
        for row in rows:
            print("pending: GEN 58 reverse-holo", row["languages"][0])
        return 1 if rows or source else 0
    if rows or source:
        overrides["sources"].setdefault(SOURCE_REF, SOURCE)
        overrides["overrides"] += rows
        text = json.dumps(overrides, ensure_ascii=False, indent=2) + "\n"
        # The store keeps one hand-written compact list; preserve it byte for byte.
        text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
        OVERRIDES.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
