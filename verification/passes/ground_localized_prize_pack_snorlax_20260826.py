#!/usr/bin/env python3
"""Ground localized Snorlax Prize Pack units on official checklists.

The official lists positively name the localized card and use the legend's standard/foil
checkboxes to identify its finish. Portuguese Series One and Three remain untouched: their
existing owner-adjudicated contradictions are not changed by the absence of localized lists.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
UNITS = ROOT / "verification" / "units.json"
JOURNAL = ROOT / "verification" / "evidence.jsonl"
FINISH_OVERRIDES = ROOT / "verification" / "finish_overrides.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
CHECKED_AT = "2026-08-26T00:00:00Z"

OLD_LOCALES = {
    "English": ("cms2", "en"),
    "French": ("cms2-fr-fr", "fr"),
    "German": ("cms2-de-de", "de"),
    "Italian": ("cms2-it-it", "it"),
    "Spanish": ("cms2-es-es", "es"),
}
NEW_LOCALES = {
    "English": ("en-us", "EN"),
    "French": ("fr-fr", "FR"),
    "German": ("de-de", "DE"),
    "Italian": ("it-it", "IT"),
    "Spanish": ("es-es", "ES"),
    "Portuguese": ("pt-br", "PTBR"),
}


def checklist_url(series: int, language: str) -> str:
    if series <= 6:
        cms, tag = OLD_LOCALES[language]
        return (
            f"https://www.pokemon.com/static-assets/content-assets/{cms}/pdf/"
            f"trading-card-game/checklist/prize_pack_series_{series}_web_cardlist_{tag}.pdf"
        )
    locale, tag = NEW_LOCALES[language]
    filename = {
        7: f"P11076_USOP_OP_Prize_Packs_Series7_Card_List_{tag}.pdf",
        8: f"OP_Prize_Packs_Series8_Card_List_{tag}.pdf",
    }[series]
    return f"https://d1wx537rtdixyy.cloudfront.net/expansions/series{series}/{locale}/{filename}"


SERIES = {
    1: {
        "setCode": "PPS1 VIV", "number": "VIV 131",
        "variants": {"V1": "standard/non-holo", "V2": "foil/holo"},
        "units": {
            "V1": {"English": "U0534", "French": "U0535", "German": "U0536", "Spanish": "U0537", "Italian": "U0538"},
            "V2": {"English": "U0593", "French": "U0594", "German": "U0595", "Spanish": "U0596", "Italian": "U0597"},
        },
    },
    3: {
        "setCode": "PPS3 LOR", "number": "LOR 143",
        "variants": {"base": "standard/non-holo"},
        "units": {"base": {"English": "U0372", "French": "U0373", "German": "U0374", "Spanish": "U0375", "Italian": "U0376"}},
    },
    7: {
        "setCode": "PPS7 JTG", "number": "JTG 117",
        "variants": {"base": "standard/non-holo"},
        "units": {"base": {"English": "U0324", "French": "U0325", "German": "U0326", "Spanish": "U0327", "Italian": "U0328", "Portuguese": "U0329"}},
    },
    8: {
        "setCode": "PPS8 JTG", "number": "JTG 117",
        "variants": {"V1": "standard/non-holo", "V2": "foil/holo"},
        "units": {
            "V1": {"English": "U0214", "French": "U0215", "German": "U0216", "Spanish": "U0217", "Italian": "U0218", "Portuguese": "U0219"},
            "V2": {"English": "U0187", "French": "U0188", "German": "U0189", "Spanish": "U0190", "Italian": "U0191", "Portuguese": "U0192"},
        },
    },
}

SOURCE_SUFFIX = {
    "English": "", "French": "-fr", "German": "-de", "Italian": "-it",
    "Spanish": "-es", "Portuguese": "-pt-br",
}

# These records describe English-market products or an English scan. They remain useful for the
# English override, but a localized checklist is the positive finish evidence for every other
# language and must not inherit them.
ENGLISH_ONLY_PRINTING_REFS = {
    "tcgcsv-docs",
    "tcgcsv-prize-pack-snorlax",
    "cardmarket-stock-image",
    "owner-scan-review",
}

# These earlier observations identify the exact card, language and Prize Pack printing. The
# localized Series One/Three name-list rows are deliberately absent: they establish only product
# names, not a Snorlax card or V1/V2 finish.
EXACT_PRIOR_CORROBORATION_UNITS = {
    "U0372", "U0534", "U0593",
    "U0187", "U0188", "U0189", "U0190", "U0191", "U0192",
    "U0214", "U0215", "U0216", "U0217", "U0218", "U0219",
    "U0324", "U0325", "U0326", "U0327", "U0328", "U0329",
}

# These Brazilian-market observations are source-capability fixtures and remain the current
# language evidence. Their official checklists are still appended below and drive finish truth.
CURRENT_EXCEPTIONS = {
    "U0329": {
        "sourceUrl": "https://www.ligapokemon.com.br/?view=cards/card&card=Hop%27s%20Snorlax%20(117%2F096)&ed=PPPS7&num=117",
        "sourceType": "Marketplace listing, LigaPokemon (Brazilian/Portuguese market)",
        "providerId": "ligapokemon", "sourceRef": None, "corroborated": False,
        "evidence": "LigaPokemon (Brazilian marketplace) lists this card as \"Snorlax do Lupo / Hop's Snorlax (117/096)\", edition \"Play! Pokemon Prize Pack Series Seven (2025) PPPS7\", with 15 sellers, every one under the language filter \"Idiomas: Portugues\". Portuguese distribution of this Prize Pack card is thereby confirmed. Source: https://www.ligapokemon.com.br/?view=cards/card&card=Hop%27s%20Snorlax%20(117%2F096)&ed=PPPS7&num=117",
        "checkedAt": "2026-07-23T00:39:10",
    },
    "U0219": {
        "sourceUrl": "https://www.ligapokemon.com.br/?view=cards/card&card=Hop%27s%20Snorlax%20(117b%2F90)&ed=PPPS8&num=117b",
        "sourceType": "Marketplace listing (LigaPokemon, Normal/non-foil)",
        "providerId": "ligapokemon", "sourceRef": None, "corroborated": False,
        "evidence": "Portuguese NON-HOLO printing: LigaPokemon (Brazilian marketplace) lists \"Snorlax do Lupo / Hop's Snorlax (117b/90)\", Play! Pokemon Prize Pack Series Eight, with \"Normal\" (non-foil) copies under \"Idiomas: Portugues\". Note: this non-holo print is physically identical to the PPS7 non-holo but is catalogued separately.",
        "checkedAt": "2026-07-23T00:58:46",
    },
    "U0192": {
        "sourceUrl": "https://www.ligapokemon.com.br/?view=cards/card&card=Hop%27s%20Snorlax%20(117b%2F90)&ed=PPPS8&num=117b",
        "sourceType": "Marketplace listing (LigaPokemon, Foil) + photographed holo specimen",
        "providerId": "ligapokemon", "sourceRef": "specimen:SPEC-0006", "corroborated": True,
        "evidence": "Portuguese HOLO printing: LigaPokemon lists this Prize Pack card with \"Foil\" copies under \"Idiomas: Portugues\", and a physical Portuguese holo specimen was inspected from a photograph (\"Snorlax do Lupo\", Habilidade \"Boca-livre\", \"Compressao Dinamica\" 140, \"JTG PT 117/159\", Play! stamp, (c)2025).",
        "checkedAt": "2026-07-23T00:58:46",
    },
}


def source_id(series: int, language: str) -> str:
    return f"prize-pack-series-{series}-checklist{SOURCE_SUFFIX[language]}"


def main() -> int:
    units = json.loads(UNITS.read_text(encoding="utf-8"))
    finish_overrides = json.loads(FINISH_OVERRIDES.read_text(encoding="utf-8"))
    specimens = json.loads(SPECIMENS.read_text(encoding="utf-8"))
    by_id = {unit["unitId"]: unit for unit in units}
    journal = [json.loads(line) for line in JOURNAL.read_text(encoding="utf-8").splitlines() if line]
    changed = 0
    additions = []

    for series, record in SERIES.items():
        for variant, languages in record["units"].items():
            finish = record["variants"][variant]
            for language, unit_id in languages.items():
                unit = by_id.get(unit_id)
                expected = (record["setCode"], record["number"], variant, language, "confirmed")
                actual = None if unit is None else (
                    unit["setCode"], str(unit["number"]), unit.get("variant") or "base",
                    unit["language"], unit["status"],
                )
                if actual != expected:
                    print(f"{unit_id} is {actual}, expected {expected}", file=sys.stderr)
                    return 1

                url = checklist_url(series, language)
                evidence = (
                    f"The official localized Prize Pack Series {series} checklist names the exact "
                    f"{record['number']} card and its colored legend checkbox positively marks the "
                    f"{finish} printing. This establishes the {language} unit and its stated finish "
                    "only; it does not establish another language or an unmarked printing."
                )
                desired = deepcopy(CURRENT_EXCEPTIONS.get(unit_id, {
                        "sourceUrl": url,
                        "sourceType": f"The Pokémon Company official localized Prize Pack Series {series} card list",
                        "providerId": "pokemon-official",
                        "sourceRef": None,
                        "evidence": evidence,
                        "checkedAt": CHECKED_AT,
                    }))
                desired["corroborated"] = unit_id in EXACT_PRIOR_CORROBORATION_UNITS
                if any(unit.get(key) != value for key, value in desired.items()):
                    unit.update(desired)
                    changed += 1
                if not any(row.get("unitId") == unit_id and row.get("source") == url for row in journal):
                    additions.append({
                        "unitId": unit_id, "lang": language, "status": "confirmed",
                        "source": url, "evidence": evidence, "at": CHECKED_AT,
                    })

    all_overrides = finish_overrides["overrides"]
    for series, record in SERIES.items():
        languages = list(next(iter(record["units"].values())))
        for language in languages:
            ref = source_id(series, language)
            finish_overrides["sources"][ref] = {
                "url": checklist_url(series, language),
                "sourceType": f"Official Pokemon localized Prize Pack Series {series} checklist",
                "authorityTier": "official-primary",
                "coverage": "complete-manifest",
                "supportsAbsence": True,
                "languages": [language],
                "retrievedAt": "2026-08-26",
                "evidence": (
                    f"The complete {language} checklist positively names the exact Snorlax row; "
                    "the colored legend checkboxes distinguish Standard Set from Standard Set Foil."
                ),
            }
        matches = [row for row in all_overrides if row["setCode"] == record["setCode"]]
        if not matches or str(matches[0].get("number")) != record["number"]:
            print(f"missing finish override for {record['setCode']} {record['number']}", file=sys.stderr)
            return 1

        if series == 8:
            continue
        insert_at = all_overrides.index(matches[0])
        template = deepcopy(matches[0])
        all_overrides[:] = [row for row in all_overrides if row["setCode"] != record["setCode"]]
        localized_overrides = []
        prefix = f"prize-pack-series-{series}-checklist"
        for language in languages:
            localized = deepcopy(template)
            localized["languages"] = [language]
            for printing in localized["printings"]:
                other_refs = [
                    ref for ref in printing["sourceRefs"]
                    if not ref.startswith(prefix)
                    and (language == "English" or ref not in ENGLISH_ONLY_PRINTING_REFS)
                ]
                printing["sourceRefs"] = [source_id(series, language)] + other_refs
            localized_overrides.append(localized)
        all_overrides[insert_at:insert_at] = localized_overrides

    # The localized lists establish "foil", not its pattern. Keep Cosmos only where separately
    # established (English and the owner's German adjudication); do not project it to PT/FR/IT/ES.
    pps8_indices = [i for i, row in enumerate(all_overrides) if row["setCode"] == "PPS8 JTG"]
    if not pps8_indices:
        print("missing PPS8 finish override", file=sys.stderr)
        return 1
    insert_at = pps8_indices[0]
    pps8 = deepcopy(all_overrides[insert_at])
    del all_overrides[insert_at:pps8_indices[-1] + 1]
    split_overrides = []
    groups = (
        ("English", True, True),
        ("German", False, True),
        ("Portuguese", False, False),
        ("French", True, False),
        ("Italian", True, False),
        ("Spanish", True, False),
    )
    for language, include_manual_holo, keep_cosmos in groups:
        localized = deepcopy(pps8)
        localized["languages"] = [language]
        if not include_manual_holo:
            for printing in localized["printings"]:
                if printing["finish"] == "holo":
                    printing["evidenceOnlyForSpecimen"] = True
        for printing in localized["printings"]:
            other_refs = [
                ref for ref in printing["sourceRefs"]
                if not ref.startswith("prize-pack-series-8-checklist")
                and (language == "English" or ref not in ENGLISH_ONLY_PRINTING_REFS)
            ]
            printing["sourceRefs"] = [source_id(8, language)] + other_refs
            if printing["finish"] == "holo" and not keep_cosmos:
                printing["foilPattern"] = None
        split_overrides.append(localized)
    all_overrides[insert_at:insert_at] = split_overrides

    german = next((row for row in specimens["specimens"] if row.get("specimenId") == "SPEC-0001"), None)
    if german is None or (german.get("physicalObservation") or {}).get("finish") != "holo":
        print("missing German PPS8 holo specimen SPEC-0001", file=sys.stderr)
        return 1
    german["physicalObservation"]["foilPattern"] = "cosmos"
    german["physicalObservation"]["basis"] = (
        "Physical German holo specimen plus the collection owner's 2026-08-25 identification "
        "of the foil treatment as Cosmos, matching the English Series Eight product."
    )

    finish_overrides["meta"]["lastUpdated"] = "2026-08-26"
    UNITS.write_text(json.dumps(units, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    FINISH_OVERRIDES.write_text(
        json.dumps(finish_overrides, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    SPECIMENS.write_text(json.dumps(specimens, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if additions:
        with JOURNAL.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"grounded {changed} localized Prize Pack confirmation(s); appended {len(additions)} observation(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
