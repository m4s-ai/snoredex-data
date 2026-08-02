#!/usr/bin/env python3
"""Close the final language/product review queue with the researched findings.

This pass is intentionally small and idempotent.  It updates only the 15 units whose
status changed during the final review sweep; all other unit fields remain untouched.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "verification"

ELITEFOURUM_EEVEE = (
    "https://www.elitefourum.com/t/collectors-guide-to-eevee-cards-in-all-languages/62616"
)
BA20_ARTICLE = "https://bulbapedia.bulbagarden.net/wiki/Battle_Academy_2020_%28TCG%29"

BA20_EVIDENCE = (
    "The Elite Fourum language matrix lists ordinary Hidden Fates Eevee 49/68 in English, "
    "French, German, Italian, Spanish and Portuguese, but the Battle Academy 2020 Mewtwo Deck "
    "stamped Eevee 49/68 only in English, French, German and Italian. The same four-language "
    "scope is shown for the Charizard Deck stamp. Bulbapedia's Battle Academy 2020 article "
    "lists French, German and Italian product releases and includes Snorlax 50/68 in the Mewtwo "
    "Deck: " + BA20_ARTICLE + ". Spanish records point to later or inconsistent products: "
    "BoardGameGeek (https://boardgamegeek.com/boardgameversion/614262/spanish-edition) and "
    "Raccoon Games (https://www.raccoongames.es/es/producto/pokemon-tcg-academia-de-combate) "
    "describe Cinderace V/Pikachu V/Eevee V, while SafariZone describes Battle Academy 2024. "
    "Portuguese records likewise identify Copag's later Cinderace/Pikachu/Eevee product "
    "(https://copag.com.br/pokemon/blog/detalhes/box-academia-de-batalha-novos-decks-para-iniciantes), "
    "Copag reference 31495/EAN 7896192314949, and a Portuguese-market listing that warns the "
    "article may be Castilian, English or Catalan rather than Portuguese. No Spanish or Portuguese "
    "BA20 MWT Snorlax card image, product code/EAN, manufacturer record, or localized listing was "
    "found. The ordinary Spanish Hidden Fates Snorlax 50/68 is unstamped and does not establish a "
    "BA20 MWT printing. Cardmarket's language filter is marketplace metadata, not a print manifest. "
    "The Spanish and Portuguese claims are therefore contradicted."
)

UPDATES = {
    "U0101": {
        "status": "contradicted",
        "sourceUrl": "https://www.copagloja.com.br/pokemon",
        "sourceType": "Retail listings and Copag official catalog/store checks + Portuguese marketplace research (user-directed closure)",
        "providerId": "retailer-listing",
        "corroborated": True,
        "evidence": (
            "No Brazilian Portuguese xPRE 076 V1 evidence was found. Copag's catalog/store and "
            "Portuguese marketplace listings show ordinary Portuguese PRE 076/131, while localized "
            "Special Collection evidence exists in English, French, German, Italian and European "
            "Spanish. At the user's direction, Cardmarket's Portuguese xPRE 076 V1 claim is "
            "contradicted. Ordinary Portuguese listing: https://mypcards.com/pokemon/produto/260382/snorlax-ex"
        ),
    },
    "U0315": {
        "status": "contradicted",
        "sourceUrl": "https://www.copagloja.com.br/pokemon",
        "sourceType": "Retail listings and Copag official catalog/store checks + Portuguese marketplace research (user-directed closure)",
        "providerId": "retailer-listing",
        "corroborated": True,
        "evidence": (
            "No Brazilian Portuguese xPRE 076 V2 jumbo evidence was found. Copag's catalog/store "
            "and Portuguese marketplace listings show ordinary Portuguese PRE 076/131, while "
            "localized Special Collection evidence exists in English, French, German, Italian and "
            "European Spanish. At the user's direction, Cardmarket's Portuguese xPRE 076 V2 claim "
            "is contradicted. Ordinary Portuguese listing: https://mypcards.com/pokemon/produto/260382/snorlax-ex"
        ),
    },
    "U0296": {
        "status": "contradicted",
        "sourceUrl": ELITEFOURUM_EEVEE,
        "sourceType": "Elite Fourum collector guide + Bulbapedia + manufacturer/regional catalog cross-check",
        "providerId": "elitefourum",
        "corroborated": True,
        "evidence": BA20_EVIDENCE + " Language-specific conclusion: no Spanish BA20 MWT Snorlax printing was found.",
    },
    "U0298": {
        "status": "contradicted",
        "sourceUrl": ELITEFOURUM_EEVEE,
        "sourceType": "Elite Fourum collector guide + Bulbapedia + manufacturer/regional catalog cross-check",
        "providerId": "elitefourum",
        "corroborated": True,
        "evidence": BA20_EVIDENCE + " Language-specific conclusion: no Portuguese BA20 MWT Snorlax printing was found.",
    },
    "U0377": {
        "status": "contradicted",
        "sourceUrl": "https://www.facebook.com/groups/389018291429685/posts/2416439302020897/",
        "sourceType": "Elite Fourum collector-group confirmation corroborated by archived official Copag announcements and owner attestation",
        "providerId": "elitefourum",
        "corroborated": True,
        "evidence": (
            "The linked collector discussion confirms no Portuguese Snorlax LOR 143 Prize Pack Series Three "
            "printing. Copag's announcement states Series Three packs sent to Brazilian Leagues contained "
            "English cards and that localization began with Series Four. Copag research: "
            "https://www.elitefourum.com/t/how-to-research-copag-portuguese-cards/60133; original post: "
            "https://x.com/CopagPokemon/status/1760012631660748847."
        ),
    },
    "U0435": {
        "status": "contradicted",
        "sourceUrl": "https://www.elitefourum.com/t/modern-world-championships-decks-languages/55804",
        "sourceType": "Elite Fourum collector community + localized retail listings",
        "providerId": "elitefourum",
        "corroborated": True,
        "evidence": (
            "The World Championships language discussion identifies English, French, German and Italian "
            "Colorless Lugia 2023 decks, calls Spanish less likely, and reports no Spanish localized listing. "
            "Retail references include https://www.miraicards.com/en/products/pokemon-2023-world-championships-deck-colorless-lugia "
            "and https://mycomics.it/shop/pokemon-mazzo-colorless-lugia-dei-campionati-mondiali-world-championship-2023-gabriel-fernandez/. "
            "Cardmarket's Spanish WCD23 Snorlax claim is contradicted."
        ),
    },
    "U0437": {
        "status": "contradicted",
        "sourceUrl": "https://www.elitefourum.com/t/modern-world-championships-decks-languages/55804",
        "sourceType": "Elite Fourum collector community + localized retail listings",
        "providerId": "elitefourum",
        "corroborated": True,
        "evidence": (
            "The World Championships language discussion identifies English, French, German and Italian "
            "Colorless Lugia 2023 decks, calls Portuguese less likely, and reports no Portuguese localized listing. "
            "Retail references include https://www.miraicards.com/en/products/pokemon-2023-world-championships-deck-colorless-lugia "
            "and https://mycomics.it/shop/pokemon-mazzo-colorless-lugia-dei-campionati-mondiali-world-championship-2023-gabriel-fernandez/. "
            "Cardmarket's Portuguese WCD23 Snorlax claim is contradicted."
        ),
    },
    "U0467": {
        "status": "contradicted",
        "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/Venusaur_%26_Charizard_%26_Blastoise_Special_Deck_Set_ex_(TCG)",
        "sourceType": "Bulbapedia product release field and set list",
        "providerId": "bulbapedia",
        "corroborated": False,
        "evidence": "The product article lists only Japanese and Korean releases and includes Snorlax as card 021/049; no Traditional Chinese edition is documented. Cardmarket's Traditional Chinese svG 021 claim is contradicted.",
    },
    "U0539": {
        "status": "contradicted",
        "sourceUrl": "https://www.facebook.com/groups/389018291429685/posts/2416439302020897/",
        "sourceType": "Elite Fourum collector-group confirmation corroborated by archived official Copag announcements and owner attestation",
        "providerId": "elitefourum",
        "corroborated": True,
        "evidence": (
            "The linked collector discussion confirms no Portuguese Snorlax VIV 131 Prize Pack Series One printing. "
            "Copag's 2023 announcement documents only a limited Portuguese Series One/Two selection that excludes "
            "Snorlax, and localized Prize Pack support began with Series Four. Copag research: "
            "https://www.elitefourum.com/t/how-to-research-copag-portuguese-cards/60133."
        ),
    },
    "U0598": {
        "status": "contradicted",
        "sourceUrl": "https://www.facebook.com/groups/389018291429685/posts/2416439302020897/",
        "sourceType": "Elite Fourum collector-group confirmation corroborated by archived official Copag announcements and owner attestation",
        "providerId": "elitefourum",
        "corroborated": True,
        "evidence": (
            "The linked collector discussion confirms no Portuguese Snorlax VIV 131 Prize Pack Series One printing. "
            "Copag's 2023 announcement documents only a limited Portuguese Series One/Two selection that excludes "
            "Snorlax, and localized Prize Pack support began with Series Four. Copag research: "
            "https://www.elitefourum.com/t/how-to-research-copag-portuguese-cards/60133."
        ),
    },
    "U0610": {
        "status": "confirmed",
        "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/V_Starter_Sets_(TCG)",
        "sourceType": "Bulbapedia V Starter Sets product article and deck list",
        "providerId": "bulbapedia",
        "corroborated": False,
        "evidence": "The V Starter Sets article describes the products as Japanese and Korean Standard Decks and the Grass deck contains Snorlax 010/023. This confirms the Korean sA 10 printing.",
    },
    "U0611": {
        "status": "contradicted",
        "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/V_Starter_Sets_(TCG)",
        "sourceType": "Bulbapedia V Starter Sets product article and deck list",
        "providerId": "bulbapedia",
        "corroborated": False,
        "evidence": "The V Starter Sets article exhaustively describes the products as Japanese and Korean and includes Snorlax 010/023 in the Grass deck; no Traditional Chinese edition is documented. Traditional Chinese S-P 145 is a separate promo, not an sA 10 printing.",
    },
    "U0649": {
        "status": "contradicted",
        "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_Card_Game_Battle_Academy_(TCG)",
        "sourceType": "Bulbapedia Battle Academy release field and Simplified Chinese set-code note",
        "providerId": "bulbapedia",
        "corroborated": False,
        "evidence": "The Battle Academy article lists Japan, South Korea and mainland China releases; mainland China is Simplified Chinese and uses the separate CSV S code. No Traditional Chinese svIba 046 release is documented.",
    },
    "U0673": {
        "status": "contradicted",
        "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/Start_Deck_100_Battle_Collection_CoroCiao_Version_(TCG)",
        "sourceType": "Bulbapedia exhaustive product release field and card list; official CoroCiao product page",
        "providerId": "bulbapedia",
        "corroborated": True,
        "evidence": "The product article lists exactly one Japanese release on December 19, 2025 and includes Snorlax 012/023; the official CoroCiao page identifies it as a Japanese magazine bonus. No Korean mP1 012 printing is documented. Official page: https://www.corocoro.jp/corociao",
    },
    "U0674": {
        "status": "contradicted",
        "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/Start_Deck_100_Battle_Collection_CoroCiao_Version_(TCG)",
        "sourceType": "Bulbapedia exhaustive product release field and card list; official CoroCiao product page",
        "providerId": "bulbapedia",
        "corroborated": True,
        "evidence": "The product article lists exactly one Japanese release on December 19, 2025 and includes Snorlax 012/023; the official CoroCiao page identifies it as a Japanese magazine bonus. No Traditional Chinese mP1 012 printing is documented; Traditional Chinese SV-P 215 is a separate Taiwan promo. Official page: https://www.corocoro.jp/corociao",
    },
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    units_path = VERIFICATION / "units.json"
    units = read_json(units_path)
    now = datetime.now().isoformat(timespec="seconds")
    seen = set()
    log_rows = []
    journal_path = VERIFICATION / "evidence.jsonl"
    journal_keys = set()
    if journal_path.exists():
        for line in journal_path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            evidence = row.get("evidence")
            if isinstance(evidence, (dict, list)):
                evidence = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
            journal_keys.add((row.get("unitId"), row.get("status"), evidence))

    for unit in units:
        update = UPDATES.get(unit.get("unitId"))
        if not update:
            continue
        seen.add(unit["unitId"])
        changed = any(unit.get(key) != value for key, value in update.items())
        changed = changed or unit.get("sourceRef") is not None
        changed = changed or bool(unit.get("manualReason"))
        if changed:
            for key, value in update.items():
                unit[key] = value
            unit["sourceRef"] = None
            unit["checkedAt"] = now
            if "manualReason" in unit:
                unit["manualReason"] = None
        log_row = {
            "unitId": unit["unitId"],
            "status": unit["status"],
            "source": unit["sourceUrl"],
            "evidence": unit["evidence"],
            "at": now,
        }
        journal_key = (log_row["unitId"], log_row["status"], log_row["evidence"])
        if journal_key not in journal_keys:
            log_rows.append(log_row)
            journal_keys.add(journal_key)

    missing = sorted(set(UPDATES) - seen)
    if missing:
        raise SystemExit(f"Missing expected units: {', '.join(missing)}")

    units_path.write_text(json.dumps(units, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with journal_path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in log_rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    state = {"phase": "language-review-closure", "completedAt": now}
    (VERIFICATION / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    dataset_path = ROOT / "snorlax_cards.json"
    dataset = read_json(dataset_path)
    dataset["meta"]["verification"].update({
        "confirmed": 634,
        "contradicted": 85,
        "needsManualReview": 0,
        "open": 0,
        "totalUnits": 719,
        "lastUpdated": now[:10],
    })
    dataset_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(seen)} language-review units; state={state['phase']}")


if __name__ == "__main__":
    main()
