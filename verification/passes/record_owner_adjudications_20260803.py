#!/usr/bin/env python3
"""Record the collection owner's decisions on the adjudication queue (#84-#93).

Thirty-five disputed claims settled as `not-printed`, and one contradiction overturned. The owner
answered issue by issue on 2026-08-03; each rationale below quotes what they wrote and cites the
thread it came from, so the reasoning survives with the decision rather than in a comment thread.

Four patterns run through the answers, and three of them are the same shape:

  * **The card exists, but not as this product.** `KSS 26` in Japanese and Korean is `HXY` and
    `FXY`; the Sword & Shield-era `s1H`/`s2` Traditional Chinese cards are the `sc1a`/`sc1b`
    catch-up sets; `S-P 156` exists in Korean and Traditional Chinese under different promo
    numbers; the Indonesian 151 mirror holos were released as `SV-P` promos. Cardmarket claims the
    language against *this* set code, and against that product the claim is wrong — so the decision
    is `not-printed` and the equivalent is named, which is what `RESUME.md` means by checking
    whether a card exists in that language under another set.
  * **Japan-only distribution channels.** The CoroCiao deck, `XY-P 261`, `BW-P 207`, `DP-P 126`.
  * **Market or era out of scope.** `UNP` predates both Asian markets; `WP 49` is English only;
    Fates Collide and Generations have no Russian run; the stamped store promos had no European
    localisation beyond the one below.

The fourth is the exception, and it is why asking was worth it.

`U0452` — French `xJTG 117` V2 — is **overturned to confirmed**. V2 is the GameStop stamp, and the
owner points out that GameStop is not only the USA: it is Canada too, which is bilingual, so a
French run exists. The contradiction had reasoned from "every documented printing was distributed
in an English-language retail market", which was the weakest evidence in the store and is now shown
to be wrong. That is the argument shape `RESUME.md` already warns about after the false `XY-P 149`
contradiction.

The owner attached an image to that comment. This session could not retrieve it — GitHub
attachment URLs are outside the repository-scoped proxy — so the claim is recorded on the
attestation alone and is *not* filed as a specimen. Writing a `SPEC-nnnn` record describing a
photograph nobody here has examined would be the #64 mistake again: grading a claim by the
strongest thing beside it rather than by what it rests on. If the image is added to
`verification/specimens/`, the unit can cite it and move to tier 1.

Idempotent: re-running adds nothing and re-decides nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "verification"
DECIDED_AT = "2026-08-03"
ISSUE = "https://github.com/m4s-ai/snoredex-data/issues"

# unitIds -> (issue number, rationale). One entry per decision the owner actually made; the
# clusters they have not answered yet are deliberately absent.
NOT_PRINTED: list[tuple[list[str], int, str]] = [
    (["U0453", "U0454", "U0455", "U0456", "U0460", "U0461", "U0462", "U0463", "U0464"], 85,
     "The collection owner ruled that the stamped Journey Together store promos had no European "
     "localisation beyond French: \"All other Euro Languages were not released for stamped store "
     "promos.\" The single exception is the French GameStop printing (V2), which is confirmed "
     "rather than contradicted — see U0452. V1 is the Malaysia/Philippines/Singapore stamp, so "
     "French does not apply to it either."),
    (["U0485", "U0488"], 86,
     "The card exists in Japanese and Korean, but not as the Kalos Starter Set: \"japanese and "
     "korean are released in their own version with code HXY for japanese and FXY for korean.\" "
     "Cardmarket claims these languages against KSS 26, and against that product the claim is "
     "wrong. Korean reference: "
     "https://bulbapedia.bulbagarden.net/wiki/Evolution_of_Chespin_(KTCG)"),
    (["U0200", "U0248"], 87,
     "The collection owner confirmed the Russian gap directly: \"yes these do not exist in "
     "russian.\" The Russian XY run ended with BREAKthrough, so Fates Collide and Generations have "
     "no Russian printing."),
    (["U0502"], 87,
     "The collection owner ruled \"WP 49 is only english.\" Wizards Black Star Promos is a promo "
     "series rather than a main expansion, so the cross-language expansion index does not cover "
     "it; this decision rests on the owner's knowledge, not on that index's silence."),
    (["U0288", "U0509", "U0512", "U0549"], 87,
     "The Traditional Chinese cards exist, but as the era's catch-up set rather than as s1H: "
     "\"T-Chinese Snorlax vMax in 2 versions, sc1b is the catch-up set for this era, the F at the "
     "end signifies it's t-Chinese.\" Cardmarket claims Traditional Chinese against s1H, and "
     "against that product the claim is wrong. Reference: "
     "https://bulbapedia.bulbagarden.net/wiki/Sword_%26_Shield_(ATCG)"),
    (["U0533"], 87,
     "As for the s1H rows, the Traditional Chinese equivalent is a catch-up set rather than s2: "
     "\"sc1a is the other sword and shield catch-up set that was released with sc1b and it has the "
     "s2 equivalent snorlax.\" Reference: "
     "https://bulbapedia.bulbagarden.net/wiki/Sword_%26_Shield_(ATCG)"),
    (["U0777", "U0782"], 89,
     "The Indonesian mirror holos exist, but as promos rather than as the 151 special set: "
     "\"Indonesian 151 Masterball/Pokeball was released as Promos.\" Cardmarket claims Indonesian "
     "against xsv2a 143, and against that product the claim is wrong. Reference: "
     "https://bulbapedia.bulbagarden.net/wiki/SV-P_Promotional_cards_(ITCG)"),
    (["U0101", "U0315"], 90,
     "The collection owner searched and found nothing: \"Can not find any evidence that this box "
     "set with stamp was released in Portuguese on manufacturer (Copaq) and leading Marketplaces "
     "(LigaPokemon) or anywhere else in the world.\" This confirms the user-directed closure "
     "already recorded in the unit evidence."),
    (["U0523", "U0524"], 91,
     "The card exists in Korean and Traditional Chinese, but under different promo numbers: "
     "\"especially for promos the numbering differs between countries/release regions and not all "
     "promos are released in all languages at all.\" Cardmarket claims these languages against "
     "S-P 156, and against that number the claim is wrong."),
    (["U0664"], 91,
     "Japan-only distribution: \"XY 261 is again a japanese magazine release that has not gotten "
     "an international release as it's stamp is japan specific.\""),
    (["U0673", "U0674"], 92,
     "\"The CoroCiao Deck Variant was only released in japanese, all similar cards (same art, "
     "differing languages) are other versions of this card. No direct 1to1 release in korean and "
     "t-chinese for mP1 CoroCiao Deck.\""),
    (["U0505", "U0506"], 93,
     "\"UNP Hungry Snorlax — Korean (U0505) and T-Chinese (U0506) not printed.\" The card is a "
     "1997 Japanese Nintendo 64 campaign promo; the Korean TCG began in 2000 and the Traditional "
     "Chinese market later still, so it predates both."),
    (["U0467"], 93, "\"svG 021 — T-Chinese (U0467) not printed.\""),
    (["U0611"], 93,
     "\"V Starter Sets — T-Chinese (U0611) correct seperate printing.\" The Traditional Chinese "
     "card is the separate S-P 145 promo, not an sA 10 printing."),
    (["U0649"], 93, "\"svIba 046 Battle Academy — T-Chinese (U0649) correct not in t-chinese.\""),
    (["U0576"], 93,
     "\"BW-P 207 — Korean (U0576) correct not printed.\" A CoroCoro Ichiban! magazine insert, a "
     "Japanese channel with no Korean equivalent."),
    (["U0637"], 93,
     "\"DP-P 126 Snorlax Lv.37 — Korean (U0637) correct not printed.\" The owner's own knowledge "
     "settles this one; the Domino's Pizza channel argument alone would not, since Korea ran its "
     "own food tie-ins — the mistake that produced the false XY-P 149 contradiction."),
]

# The one overturn. V2 is the GameStop stamp and GameStop is USA *and* Canada.
OVERTURN_UNIT = "U0452"
OVERTURN = {
    "status": "confirmed",
    "providerId": "owner-attestation",
    # Must not contain "photograph": scripts/source_registry.py resolves the provider from this
    # text, and no photograph was examined here.
    "sourceType": "Owner attestation (domain expert); GameStop bilingual Canadian distribution",
    "corroborated": False,
    "sourceUrl": None,
    "sourceRef": None,
    "evidence": (
        "Owner (domain expert) confirms a French printing of the GameStop-stamped Hop's Snorlax: "
        "\"The Gamestop Promo was also released in french as GameStop is not only US, but also "
        "Canada which has two languages.\" The V2 variant is the GameStop stamp, distributed in "
        "the USA and Canada, and Canada is bilingual. This overturns a contradiction that had "
        "reasoned from the absence of a recorded localized run — the weakest evidence in the "
        "store, and the same argument shape that produced the false XY-P 149 contradiction. The "
        "owner attached an image to " + ISSUE + "/85#issuecomment-5163165868; it could not be "
        "retrieved from this environment, so this claim rests on the attestation alone and is not "
        "filed as a specimen. Adding the image to verification/specimens/ would let this unit cite "
        "it and move to tier 1."
    ),
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    units_path = VERIFICATION / "units.json"
    units = read(units_path)
    by_id = {u["unitId"]: u for u in units}

    adj_path = VERIFICATION / "owner_adjudications.json"
    document = read(adj_path)
    known = {d["unitId"] for d in document["decisions"]}

    added = 0
    for unit_ids, issue, rationale in NOT_PRINTED:
        for unit_id in unit_ids:
            unit = by_id.get(unit_id)
            if unit is None:
                raise SystemExit(f"unknown unit {unit_id}")
            if unit["status"] != "contradicted":
                raise SystemExit(
                    f"{unit_id} is {unit['status']}, not contradicted; an adjudication may only "
                    "settle a contradiction")
            if unit_id in known:
                continue
            document["decisions"].append({
                "adjudicationId": f"OA-{DECIDED_AT.replace('-', '')}-{unit_id}",
                "unitId": unit_id,
                "decision": "not-printed",
                "authority": "collection-owner",
                "basis": "multi-source-adjudication",
                "decidedAt": DECIDED_AT,
                "rationale": rationale,
                "evidenceRefs": [f"{ISSUE}/{issue}", f"unit:{unit_id}"],
            })
            known.add(unit_id)
            added += 1

    if added:
        document["decisions"].sort(key=lambda d: d["unitId"])
        document["meta"]["generated"] = DECIDED_AT
        write(adj_path, document)

    overturned = 0
    unit = by_id[OVERTURN_UNIT]
    if unit["status"] != OVERTURN["status"]:
        if unit["status"] != "contradicted":
            raise SystemExit(f"{OVERTURN_UNIT} is {unit['status']}; expected contradicted")
        unit.update(OVERTURN)
        overturned = 1
        write(units_path, units)

    # snorlax_cards.json echoes the store's own tallies and check R6 holds them to it. Computed
    # here rather than typed: close_language_review.py hard-coded these, which is why they went
    # stale the moment a single verdict moved.
    dataset_path = ROOT / "snorlax_cards.json"
    dataset = read(dataset_path)
    tally = {
        "confirmed": sum(1 for u in units if u["status"] == "confirmed"),
        "contradicted": sum(1 for u in units if u["status"] == "contradicted"),
        "needsManualReview": sum(1 for u in units if u["status"] == "needs-manual-review"),
        "open": sum(1 for u in units if u["status"] == "pending"),
        "totalUnits": len(units),
        "lastUpdated": DECIDED_AT,
    }
    if {k: dataset["meta"]["verification"].get(k) for k in tally} != tally:
        dataset["meta"]["verification"].update(tally)
        write(dataset_path, dataset)

    print(f"Recorded {added} owner adjudication(s); overturned {overturned} contradiction(s). "
          f"{len(document['decisions'])} decisions total; "
          f"meta.verification = {tally['confirmed']} confirmed / {tally['contradicted']} "
          f"contradicted.")


if __name__ == "__main__":
    main()
