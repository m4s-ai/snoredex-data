"""Record the owner's SM05 Snorlax-GX decision: the card exists only as holo (owner, 2026-10-26).

Every non-holo SM05 row rests on TCGdex `normal: true` alone, the same wrong flag as PCG3 062.
Asked whether the unknown-size non-holo rows were jumbo cards, the collection owner ruled:
"es gibt die jumbo nur in einer variante wenn die holo bestätigt ist müssen wir doch keine
non-holo erfinden" - the card, standard or jumbo, is holo only.

* Six owner finish decisions (EN, FR, DE, IT, ES, PT) close the list at holo and reject non-holo.
* In FR, DE, IT, ES and PT the TCGdex row was the only printing, so the owner's holo
  determination is recorded as an owner-attested standard-size holo printing on the regular
  promo product. No localized jumbo is asserted; English keeps its retained holo jumbo.

Idempotent; `--check` reports pending records without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
ADJUDICATIONS = V / "owner_adjudications.json"
OVERRIDES = V / "finish_overrides.json"
QUOTE = "es gibt die jumbo nur in einer variante wenn die holo bestätigt ist müssen wir doch keine non-holo erfinden"
LANGUAGES = {"English": "en", "French": "fr", "German": "de", "Italian": "it", "Spanish": "es",
             "Portuguese": "pt"}
SOURCE_REF = "owner-sm05-holo-20261026"
SOURCE = {
    "url": None,
    "sourceType": "Owner attestation (domain expert)",
    "authorityTier": "owner-attestation",
    "coverage": "positive-only",
    "supportsAbsence": False,
    "retrievedAt": "2026-10-26",
    "evidence": (f"The collection owner ruled on 2026-10-26 that SM05 Snorlax-GX exists only as holo: "
                 f"\"{QUOTE}\". Recorded for the regular promo in each European language; no "
                 "localized jumbo is asserted."),
}


def decision(language: str) -> dict:
    return {
        "adjudicationId": f"OAF-20261026-SM-05-{LANGUAGES[language]}",
        "setCode": "SM",
        "number": "05",
        "language": language,
        "decision": "finish-complete",
        "availableFinishes": ["holo"],
        "rejectedFinishes": ["non-holo"],
        "authority": "collection-owner",
        "basis": "owner-adjudication",
        "decidedAt": "2026-10-26",
        "rationale": (
            f"The collection owner ruled on 2026-10-26 that {language} SM05 Snorlax-GX exists only as "
            f"holo: \"{QUOTE}\". The non-holo row rested on TCGdex variants normal=true alone. "
            "Recorded as an owner decision, never attributed to a provider."),
        "evidenceRefs": ["https://github.com/m4s-ai/snoredex-data/pull/433"],
    }


def holo_override(language: str) -> dict:
    return {"setCode": "SM", "number": "05", "languages": [language], "printings": [{
        "finish": "holo", "foilPattern": None, "markings": None, "distribution": None,
        "cardSize": "standard", "mappedVariants": ["base"], "verificationStatus": "owner-attested",
        "sourceRefs": [SOURCE_REF]}]}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv) -> int:
    adjudications, overrides = read(ADJUDICATIONS), read(OVERRIDES)
    present = {row["adjudicationId"] for row in adjudications["finishDecisions"]}
    decisions = [decision(language) for language in LANGUAGES if decision(language)["adjudicationId"] not in present]
    rows = [holo_override(language) for language in LANGUAGES if language != "English"]
    rows = [row for row in rows if row not in overrides["overrides"]]
    source = SOURCE_REF not in overrides["sources"]
    if "--check" in argv:
        for row in decisions:
            print("pending:", row["adjudicationId"])
        for row in rows:
            print("pending: owner-attested holo", row["languages"][0])
        return 1 if decisions or rows or source else 0
    if decisions:
        adjudications["finishDecisions"] += decisions
        ADJUDICATIONS.write_text(json.dumps(adjudications, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8", newline="\n")
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
