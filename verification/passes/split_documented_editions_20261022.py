"""Split edition-documented finish units into one printing per edition (owner decision 2026-10-22).

The collection owner decided on 2026-10-22 that a card positively documented in both 1st
Edition and Unlimited is catalogued as one item per edition. Jungle 11/64 (Holo) and 27/64
(Non-Holo) exist in both editions in all seven Western languages; this rests on the reviewed
edition rule (`edition_rules.json`, owner-confirmed for Jungle) and the owner's number-to-finish
rule. Where TCGdex's `variants_detailed` lists the unstamped and the 1st-edition-stamped
variant for the exact language, that retained record is cited as well. Gym Heroes 33 (English)
and the Japanese PCG1 074, PCG3 062, PCG9 001 and e-Card 5 062 rest on those TCGdex records.

A printing is added only where no edition-specific printing for that edition exists yet, so
specimen-backed printings (with their observed stamp text) are never duplicated. The stamp
text is not asserted: TCGdex labels are database translations, not the printed wording.

A reviewed launch date that named the editionless printing moves to each edition printing of
the same release and finish once the graph is reprojected; it states the set's language debut,
which covers both editions, and never a production date. Run the pass, project finishes, graph
and checklist, run it again for the dates, then project the catalogue.

Idempotent; `--check` reports pending printings and dates without writing.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
OVERRIDES = V / "finish_overrides.json"
DATES = V / "confirmed_release_overrides.json"
sys.path.insert(0, str(ROOT / "scripts"))
from collector_catalogue import item_id  # noqa: E402
BUNDLE = "verification/evidence/data-gaps-20261022/edition/raw"
OWNER_REF = "owner-edition-split-20261022"
FIRST, UNLIMITED = "1st Edition", "Unlimited"
LANG_CODE = {"English": "en", "French": "fr", "German": "de", "Italian": "it", "Japanese": "ja"}
# (setCode, number, language, finish, TCGdex card id or None, editions)
TARGETS = [
    *[("JU", "11", lang, "holo", "base2-11" if lang in {"English", "French", "German"} else None,
       (FIRST, UNLIMITED)) for lang in ("English", "French", "German", "Spanish")],
    ("JU", "11", "Portuguese", "holo", None, (FIRST,)),
    *[("JU", "27", lang, "non-holo", "base2-27", (FIRST, UNLIMITED)) for lang in ("English", "French", "German")],
    ("JU", "27", "Italian", "non-holo", "base2-27", (FIRST,)),
    ("JU", "27", "Portuguese", "non-holo", None, (FIRST, UNLIMITED)),
    ("GH", "33", "English", "non-holo", "gym1-33", (UNLIMITED,)),
    ("EC5", "062", "Japanese", "non-holo", "E5-062", (FIRST, UNLIMITED)),
    ("PCG1", "074", "Japanese", "non-holo", "PCG1-074", (FIRST, UNLIMITED)),
    ("PCG3", "062", "Japanese", "non-holo", "PCG3-062", (FIRST, UNLIMITED)),
    ("PCG9", "001", "Japanese", "holo", "PCG9-001", (FIRST, UNLIMITED)),
]
OWNER_SOURCE = {
    "url": None,
    "sourceType": "Owner attestation (domain expert)",
    "authorityTier": "owner-attestation",
    "coverage": "positive-only",
    "supportsAbsence": False,
    "retrievedAt": "2026-10-22",
    "evidence": (
        "The collection owner decided on 2026-10-22 that a card positively documented in both 1st "
        "Edition and Unlimited is catalogued as one item per edition, and that Jungle 11/64 and "
        "27/64 exist in both editions in all seven Western languages (edition_rules.json, "
        "owner-confirmed for Jungle). Finish follows the owner's Jungle number-to-finish rule. "
        "No edition-stamp wording is asserted."
    ),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def tcgdex_ref(language, card_id):
    return f"tcgdex-edition-{LANG_CODE[language]}-{card_id}-20261022"


def tcgdex_source(language, card_id):
    path = ROOT / BUNDLE / f"tcgdex-{LANG_CODE[language]}-{card_id}.json"
    payload = read(path)
    variants = [(v.get("type"), v.get("stamp"), v.get("subtype")) for v in payload.get("variants_detailed") or []]
    return {
        "url": f"https://api.tcgdex.net/v2/{LANG_CODE[language]}/cards/{card_id}",
        "sourceType": "TCGdex API card variant detail",
        "authorityTier": "specialist-reference",
        "coverage": "positive-only",
        "supportsAbsence": False,
        # No `languages`: a localized source is merged into same-language specimens as curated
        # identity, which would stamp this edition onto a photograph that does not show it.
        "retrievedAt": "2026-10-22",
        "evidence": (
            f"TCGdex {card_id} ({language}) variants_detailed lists an edition-stamped variant and an "
            f"unstamped or 'unlimited' variant: {json.dumps(variants, ensure_ascii=False)}. Retained as "
            f"{BUNDLE}/tcgdex-{LANG_CODE[language]}-{card_id}.json "
            f"(sha256 {hashlib.sha256(path.read_bytes()).hexdigest()})."
        ),
    }


def finish_units():
    return {(u["setCode"], u["number"], u["language"]): u for u in read(V / "finish_units.json")["units"]}


def pending(overrides, units):
    """Yield (override key, printing) pairs not yet present in the overrides or the finish store."""
    present = {
        (o["setCode"], o["number"], lang, p.get("finish"), p.get("edition"))
        for o in overrides["overrides"] for lang in o.get("languages") or []
        for p in o.get("printings") or [] if p.get("edition")
    }
    for set_code, number, language, finish, card_id, editions in TARGETS:
        unit = units[(set_code, number, language)]
        variants = sorted({p["variant"] for p in unit["products"]})
        for edition in editions:
            if (set_code, number, language, finish, edition) in present:
                continue
            if any(p["finish"] == finish and p.get("edition") == edition and p.get("specimenIds")
                   for p in unit["printings"]):
                continue  # Specimen-backed printing already carries this edition.
            refs = [OWNER_REF] + ([tcgdex_ref(language, card_id)] if card_id else [])
            yield (set_code, number, language, card_id), {
                "finish": finish, "edition": edition, "foilPattern": None, "markings": None,
                "distribution": None, "cardSize": "standard", "mappedVariants": variants,
                "verificationStatus": "confirmed" if card_id else "owner-attested", "sourceRefs": refs,
            }


def write(overrides):
    text = json.dumps(overrides, ensure_ascii=False, indent=2) + "\n"
    # The store keeps one hand-written compact list; preserve it byte for byte.
    text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
    OVERRIDES.write_text(text, encoding="utf-8", newline="\n")


def retargeted_dates(document):
    """Replace date rows whose editionless printing was folded into an edition pair."""
    graph = read(V / "authoritative_graph.json")
    physical = {e["entityId"]: e["payload"] for e in graph["entities"] if e["entityType"] == "physical-printing"}
    checklist = {row["printingId"]: row["checklistId"] for row in read(ROOT / "analysis_checklist.json")["items"]
                 if row.get("printingId")}
    targets = {(t[0], t[1], t[2]) for t in TARGETS}
    finishes = {(t[0], t[1], t[2]): t[3] for t in TARGETS}
    rows, changed = [], False
    for row in document["releaseDates"]["reviewedItems"]:
        release = row["cardReleaseId"].split(":")
        key = (release[3], release[4].split("/")[0], release[2])
        if row["physicalPrintingId"] in physical or key not in targets:
            rows.append(row)
            continue
        editions = [p for pid, p in sorted(physical.items()) if p["cardReleaseId"] == row["cardReleaseId"]
                    and p["finish"] == finishes[key] and p.get("edition") in (FIRST, UNLIMITED)]
        if {p["edition"] for p in editions} != {FIRST, UNLIMITED}:
            raise ValueError(f"no complete edition pair for reviewed date {row['itemId']}")
        for printing in editions:
            rows.append({**row, "itemId": item_id("claim:" + printing["establishingClaimId"]),
                         "physicalPrintingId": printing["physicalPrintingId"],
                         "sourcePrintingId": printing["sourcePrintingId"],
                         "legacyChecklistIds": [checklist[printing["sourcePrintingId"]]],
                         "basis": row["basis"] + f"; applies to the {printing['edition']} printing of that launch"})
        changed = True
    return rows if changed else None


def main(argv):
    overrides = read(OVERRIDES)
    rows = list(pending(overrides, finish_units()))
    dates_document = read(DATES)
    date_rows = retargeted_dates(dates_document)
    if "--check" in argv:
        for key, printing in rows:
            print("pending:", *key[:3], printing["finish"], printing["edition"])
        if date_rows is not None:
            print("pending: reviewed launch dates on folded editionless printings")
        return 1 if rows or date_rows is not None else 0
    if date_rows is not None:
        dates_document["releaseDates"]["reviewedItems"] = date_rows
        DATES.write_text(json.dumps(dates_document, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8", newline="\n")
        print("retargeted reviewed launch dates")
    if not rows:
        return 0
    overrides["sources"].setdefault(OWNER_REF, OWNER_SOURCE)
    for (set_code, number, language, card_id), printing in rows:
        if card_id:
            overrides["sources"].setdefault(tcgdex_ref(language, card_id), tcgdex_source(language, card_id))
        overrides["overrides"].append({"setCode": set_code, "number": number, "languages": [language],
                                       "printings": [printing]})
        print(set_code, number, language, printing["finish"], printing["edition"])
    write(overrides)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
