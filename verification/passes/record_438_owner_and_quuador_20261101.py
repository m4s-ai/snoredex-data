"""Settle #438 candidates with owner decisions and Quuador's sets-and-languages list (2026-11-01).

Owner decisions (finishDecisions; each closes the list at the confirmed non-holo and rejects the
reverse holo that rested on the Cardmarket reverse axis alone):

* Portuguese BCR 109, BKT 118, DP 37, FCO 77, GEN 58 and PLS 101. The owner: "Bulbapedia sagt doch
  eindeutig das Boundaries Crossed auf protugiesich keine reverse holos hat"; every Portuguese
  candidate was then read on its full Bulbapedia set page. These six pages say the Portuguese set
  had no reverse holos, and Quuador's list says the same for each ("no Reverse Holos for this
  Portuguese set"). Hidden Fates and Kalos Starter Set do not.
* Kalos Starter Set 26 in English, French, German, Italian and Portuguese. The owner: "kalos starter
  war es auch nie nur im gespräch das es reverse holos gibt, das ist ein fixed produkt".

Positive evidence from Quuador's "Sets and Languages: Compilation overview list" (Elite Fourum
thread 16565, post 1, updated 2026-10-02), which the owner rates as a highly reliable source.
Excerpts and the full-text hash are retained in
`verification/evidence/issue-438-quuador-overview-20261101/excerpts.json`.

* Hidden Fates: "Portuguese Reverse Holo" (PT HIF 50 reverse).
* EX FireRed & LeafGreen: "German 'Reverse' Holofoil" (DE FL 15 reverse) and the Italian regular
  set (IT FL 15, a holo rare, holo).
* Skyridge: the Italian regular set (IT SK 100, a non-holo rare, non-holo).
* Jungle: "Spanish 1st edition", "Portuguese 1st edition" (ES/PT JU 11 holo and PT JU 27 non-holo
  in 1st Edition; the finish follows the owner's Jungle number rule of 2026-09-10).

Idempotent; `--check` reports pending records without writing.
"""
import json
import sys
from pathlib import Path

V = Path(__file__).resolve().parents[2] / "verification"
CAPABILITIES = V / "source_capabilities.json"
ADJUDICATIONS = V / "owner_adjudications.json"
DATES = V / "confirmed_release_overrides.json"
# The reviewed date of ES Jungle 11 1st Edition named the research slot, which had no physical
# printing; the Quuador evidence makes it a verified printing with its own physical id.
DATE_ROW = ("item-bffdd1fe-0a91-5c0f-936f-54388d38c0b8", "PHYSICAL:PRINTING:7004eaf981593c05c7a6934d")
OVERRIDES = V / "finish_overrides.json"
DATE = "2026-11-01"
PT_QUOTE = "Bulbapedia sagt doch eindeutig das Boundaries Crossed auf protugiesich keine reverse holos hat"
KSS_QUOTE = "kalos starter war es auch nie nur im gespräch das es reverse holos gibt, das ist ein fixed produkt"
QUUADOR = "https://www.elitefourum.com/t/sets-and-languages-compilation-overview-list/16565"
SOURCE_REF = "elitefourum-quuador-sets-languages-20261101"
PT_SETS = {
    ("BCR", "109"): ("Boundaries Crossed", 4284656),
    ("BKT", "118"): ("BREAKthrough", 4387404),
    ("DP", "37"): ("Diamond & Pearl", 4590179),
    ("FCO", "77"): ("Fates Collide", 4378164),
    ("GEN", "58"): ("Generations", 4587656),
    ("PLS", "101"): ("Plasma Storm", 4322565),
}
KSS_LANGUAGES = {"English": "en", "French": "fr", "German": "de", "Italian": "it", "Portuguese": "pt"}
SOURCE = {
    "url": QUUADOR,
    "sourceType": "Elite Fourum collector-community post",
    "authorityTier": "specialist-reference",
    "coverage": "positive-only",
    "supportsAbsence": False,
    "languages": ["German", "Italian", "Portuguese", "Spanish"],
    "claimFields": ["finish"],
    "retrievedAt": DATE,
    "evidence": (
        "Quuador's sets-and-languages compilation (post 1, updated 2026-10-02) lists per set the "
        "variants printed in each language: Hidden Fates \"Portuguese Reverse Holo\"; EX FireRed & "
        "LeafGreen \"German 'Reverse' Holofoil\" and the Italian regular set; Skyridge the Italian "
        "regular set; Jungle \"Spanish 1st edition\" and \"Portuguese 1st edition\". Applied only to "
        "the named, already established releases; the finish of a regular print follows the card's "
        "set rarity. Excerpts: verification/evidence/issue-438-quuador-overview-20261101/excerpts.json."),
}


SURFACE_ID = "elitefourum-quuador-sets-languages"
SURFACE = {
    "surfaceId": SURFACE_ID,
    "providerId": "elitefourum",
    "label": "Quuador's sets-and-languages compilation",
    "match": {"urlPrefixes": [QUUADOR], "nonUrlEvidenceIds": []},
    "state": "active",
    "failureState": None,
    "accessMode": "scriptable",
    "adapterState": "planned",
    "lastCheckedAt": DATE,
    "freshnessPolicy": "Retain the exact topic URL, the post-1 update date and the excerpted set sections; "
                       "re-check the post before using a new set entry.",
    "query": {"method": "GET", "endpoint": QUUADOR + ".json", "parameters": [],
              "pagination": "topic post stream; the list is post 1",
              "expectedIdentifiers": ["topic/16565", "post/1", "Quuador"]},
    "finishCapability": {
        "mode": "named-variety",
        "vocabulary": ["Reverse Holo", "'Reverse' Holofoil", "1st edition", "UED"],
        "publicationForm": "per-set list of the variants printed in each language",
        "closedWithinScope": False,
    },
    "coverageEdges": [{
        "edgeId": "elitefourum-quuador-sets-languages-positive",
        "coverage": {"localities": ["WEST"], "languages": ["German", "Italian", "Portuguese", "Spanish"],
                     "scripts": ["Latn"], "productCategories": ["set"],
                     "timeRange": {"start": "1999-01-01", "end": "2020-12-31",
                                   "basis": "the list runs from Base Set to Vivid Voltage"}},
        "positiveEvidenceCapabilities": ["finish"],
        "exhaustive": False,
        "absenceCapability": {
            "enabled": False, "dimensions": [], "exactScopes": [],
            "rationale": "Only listed variants are used as positive evidence; an unlisted variant stays unknown."},
        "knownPositiveObservationId": "obs-elitefourum-quuador-sets-languages",
        "boundary": {
            "outsideScope": ["sets after Vivid Voltage", "promos and special releases", "unlisted variants"],
            "zeroResultMeans": "unknown",
            "challenge": "A set entry supports the listed variants only; absence decisions stay with the owner."},
    }],
}
OBSERVATION = {
    "observationId": "obs-elitefourum-quuador-sets-languages",
    "surfaceId": SURFACE_ID,
    "kind": "known-positive",
    "queryUrl": QUUADOR,
    "queryParameters": {},
    "retrievedAt": DATE,
    "fixtureRef": {"kind": "source-registry-evidence", "providerId": "elitefourum", "recordKey": QUUADOR},
    "expectedIdentifiers": ["topic/16565", "post/1", "Quuador"],
    "validatesEdges": ["elitefourum-quuador-sets-languages-positive"],
    "outcome": "Post 1 lists Hidden Fates \"Portuguese Reverse Holo\", EX FireRed & LeafGreen \"German 'Reverse' "
               "Holofoil\" and Jungle \"Spanish/Portuguese 1st edition\" among the printed variants.",
}


def pt_decision(set_code: str, number: str) -> dict:
    name, oldid = PT_SETS[(set_code, number)]
    return closing_decision(set_code, number, "Portuguese", "pt", (
        f"The collection owner ruled that the Portuguese {name} had no reverse holos: \"{PT_QUOTE}\", "
        f"applied to every Portuguese set whose full Bulbapedia page says so (revision {oldid}); "
        "Quuador's sets-and-languages list agrees (\"no Reverse Holos for this Portuguese set\")."),
        [f"https://bulbapedia.bulbagarden.net/w/index.php?oldid={oldid}", QUUADOR])


def kss_decision(language: str) -> dict:
    return closing_decision("KSS", "26", language, KSS_LANGUAGES[language], (
        f"The collection owner ruled that the Kalos Starter Set, a fixed product, never had reverse "
        f"holos: \"{KSS_QUOTE}\". Quuador's sets-and-languages list names no Kalos Starter Set reverse "
        "holo in any language."), [QUUADOR])


def closing_decision(set_code, number, language, suffix, rationale, refs) -> dict:
    return {
        "adjudicationId": f"OAF-20261101-{set_code}-{number}-{suffix}",
        "setCode": set_code,
        "number": number,
        "language": language,
        "decision": "finish-complete",
        "availableFinishes": ["non-holo"],
        "rejectedFinishes": ["reverse-holo"],
        "authority": "collection-owner",
        "basis": "owner-adjudication",
        "decidedAt": DATE,
        "rationale": rationale + (" The reverse-holo row rested on the Cardmarket reverse axis alone; the "
                                  "confirmed non-holo stands. Recorded as an owner decision, never "
                                  "attributed to a provider."),
        "evidenceRefs": refs + ["https://github.com/m4s-ai/snoredex-data/issues/438"],
    }


def evidence_row(set_code, number, language, finish, variant) -> dict:
    return {"setCode": set_code, "number": number, "languages": [language], "printings": [{
        "finish": finish, "mappedVariants": [variant], "verificationStatus": "confirmed",
        "sourceRefs": [SOURCE_REF], "evidenceOnlyForExistingPrintings": True}]}


def first_edition_row(number, language, finish, variant) -> dict:
    return {"setCode": "JU", "number": number, "languages": [language], "printings": [{
        "finish": finish, "edition": "1st Edition", "foilPattern": None, "markings": None,
        "distribution": None, "cardSize": "standard", "mappedVariants": [variant],
        "verificationStatus": "confirmed", "sourceRefs": [SOURCE_REF]}]}


ROWS = [
    evidence_row("HIF", "50", "Portuguese", "reverse-holo", "V1"),
    evidence_row("FL", "15", "German", "reverse-holo", "base"),
    evidence_row("FL", "15", "Italian", "holo", "base"),
    evidence_row("SK", "100", "Italian", "non-holo", "base"),
    first_edition_row("11", "Spanish", "holo", "V1"),
    first_edition_row("11", "Portuguese", "holo", "V1"),
    first_edition_row("27", "Portuguese", "non-holo", "V2"),
]


def write(path: Path, document: dict, compact_dates: bool = False) -> None:
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if compact_dates:
        # The overrides store keeps one hand-written compact list; preserve it byte for byte.
        text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
    path.write_text(text, encoding="utf-8", newline="\n")


def main(argv) -> int:
    adjudications = json.loads(ADJUDICATIONS.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    present = {row["adjudicationId"] for row in adjudications["finishDecisions"]}
    decisions = [pt_decision(*key) for key in PT_SETS] + [kss_decision(lang) for lang in KSS_LANGUAGES]
    decisions = [row for row in decisions if row["adjudicationId"] not in present]
    rows = [row for row in ROWS if row not in overrides["overrides"]]
    source = SOURCE_REF not in overrides["sources"]
    dates = json.loads(DATES.read_text(encoding="utf-8"))
    date_row = next(row for row in dates["releaseDates"]["reviewedItems"] if row["itemId"] == DATE_ROW[0])
    date_pending = date_row.get("physicalPrintingId") != DATE_ROW[1]
    capabilities = json.loads(CAPABILITIES.read_text(encoding="utf-8"))
    surface = SURFACE_ID not in {row["surfaceId"] for row in capabilities["surfaces"]}
    if "--check" in argv:
        if surface:
            print("pending: capability surface", SURFACE_ID)
        if date_pending:
            print("pending: reviewed date identity of", DATE_ROW[0])
        for row in decisions:
            print("pending:", row["adjudicationId"])
        for row in rows:
            print("pending: Quuador evidence", row["setCode"], row["number"], row["languages"][0])
        return 1 if decisions or rows or source or surface or date_pending else 0
    if date_pending:
        date_row["physicalPrintingId"] = DATE_ROW[1]
        write(DATES, dates)
    if surface:
        capabilities["surfaces"].append(SURFACE)
        capabilities["observations"].append(OBSERVATION)
        write(CAPABILITIES, capabilities)
    if decisions:
        adjudications["finishDecisions"] += decisions
        write(ADJUDICATIONS, adjudications)
    if rows or source:
        overrides["sources"].setdefault(SOURCE_REF, SOURCE)
        overrides["overrides"] += rows
        write(OVERRIDES, overrides, compact_dates=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
