"""Apply the positive Korean research collected for issue #260.

This is an active correction pass, not a historical note.  It admits only exact
local set/number/rarity evidence and leaves finish, appearance and unresolved
taxonomy questions open.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import admit_issue260_korean_20260828 as base  # noqa: E402


PRINTS = ROOT / "verification" / "source_first_prints.json"
REKEYS = ROOT / "verification" / "legacy_issue_rekeys.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
CAPABILITIES = ROOT / "verification" / "source_capabilities.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
UNITS = ROOT / "verification" / "units.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def research(
    unit_id: str,
    set_code: str,
    number: str,
    rarity: tuple[str, str],
    source_url: str,
    provider: str,
    *,
    specimen_id: str | None = None,
    card_name: str | None = None,
    corroborating: list[str] | None = None,
    legacy: list[str] | None = None,
) -> dict[str, Any]:
    unit = UNITS_BY_ID[unit_id]
    legacy_ids = legacy if legacy is not None else [unit_id]
    return {
        "printId": f"KR:{set_code}:{number}:base",
        "localSetCode": set_code,
        "localNumber": number,
        "work": unit["cardKey"],
        "legacy": legacy_ids,
        "rarity": rarity,
        "specimenId": specimen_id,
        "cardName": card_name or unit["cardName"],
        "providerId": provider,
        "sourceUrl": source_url,
        "corroborated": bool(corroborating),
        "corroboratingSourceUrls": corroborating or [],
        "legacyVariants": sorted({str(UNITS_BY_ID[item].get("variant") or "base") for item in legacy_ids}),
    }


UNITS_BY_ID = {row["unitId"]: row for row in read(UNITS)}


# Positive source observations from the current Korean research.  Namu-only
# rows are represented by their corresponding Bulbapedia KTCG set/promo pages
# in the active registry; no finish is inferred from any of these records.
RESEARCH_ROWS = [
    research("U0049", "sv2a", "181/165", ("AR", "art-rare"), "https://pokemoncard.co.kr/cards/detail/BS2023014181", "pokemon-card-korea"),
    research("U0103", "sv2a", "143/165", ("U", "uncommon"), "https://pokemoncard.co.kr/cards/detail/BS2023014143", "pokemon-card-korea"),
    research("U0127", "m2a", "136/193", ("not stated", "unknown"), "https://globalbunjang.com/product/423487583", "seller-listing-photo", specimen_id="SPEC-0436"),
    research("U0233", "sv5a", "051/066", ("U", "uncommon"), "https://pokemoncard.co.kr/cards/detail/BS2024007051", "pokemon-card-korea", specimen_id="SPEC-0441"),
    research("U0257", "m3", "062/080", ("C", "common"), "https://collectory.cc/cards/b6401ed6-1c9a-4703-9b55-762ac6e6d33e", "collectory", specimen_id="SPEC-0443"),
    research("U0260", "sv4K", "060/066", ("U", "uncommon"), "https://globalbunjang.com/product/407721760", "seller-listing-photo", specimen_id="SPEC-0445", corroborating=["https://www.pokepolio.com/cards/8ae3d25e-9838-4724-bcf3-cf5ed897d22b"]),
    research("U0306", "sv4a", "145/190", ("N", "normal"), "https://collectory.cc/cards/cba4c986-3c69-4a8c-b065-30efbaac86ed", "collectory"),
    research("U0379", "SM-P", "017/SM-P", ("PROMO", "promo"), "https://bulbapedia.bulbagarden.net/wiki/SM-P_Promotional_cards_(KTCG)", "bulbapedia", specimen_id="SPEC-0439", corroborating=["https://tcgbox.co.kr/product/%EC%9E%A0%EB%A7%8C%EB%B3%B4gx/3966/"]),
    research("U0402", "svM", "094/175", ("U", "uncommon"), "https://collectory.cc/cards/6ff1ddb5-e091-42e4-8581-90cebe2d3b5f", "collectory", specimen_id="SPEC-0464"),
    research("U0413", "sm9", "066/095", ("RR", "double-rare"), "https://collectory.cc/cards/46ece022-2213-48b9-bb7d-6504f5e3a4eb", "collectory", specimen_id="SPEC-0449"),
    research("U0440", "CLF", "016/034", ("fixed product", "fixed"), "https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_Trading_Card_Game_Classic_(TCG)", "bulbapedia"),
    research("U0508", "s1H", "070/060", ("HR", "hyper-rare"), "https://bulbapedia.bulbagarden.net/wiki/Shield_(TCG)", "bulbapedia"),
    research("U0541", "XY10", "057/078", ("C", "common"), "https://bulbapedia.bulbagarden.net/wiki/Awakening_Psychic_King_(TCG)", "bulbapedia", specimen_id="SPEC-0457"),
    research("U0557", "sm9", "115/095", ("HR", "hyper-rare"), "https://bulbapedia.bulbagarden.net/wiki/Eevee_%26_Snorlax-GX_(Team_Up_120)", "bulbapedia", corroborating=["https://collectory.cc/cards/d3bcbd09-e544-468a-a596-7745da852bba"]),
    research("U0561", "XY2", "066/080", ("U", "uncommon"), "https://pokemoncard.co.kr/cards/detail/BS2014002066", "pokemon-card-korea", specimen_id="SPEC-0411"),
    research("U0579", "BW7", "055/070", ("U", "uncommon"), "https://pokemoncard.co.kr/cards/detail/BS2013001055", "pokemon-card-korea", specimen_id="SPEC-0442"),
    research("U0590", "mC", "568/742", ("N", "normal"), "https://collectory.cc/cards/f7c4636f-8030-40a7-86d6-994a0bc3283c", "collectory", specimen_id="SPEC-0459"),
    research("U0601", "s5a", "093/070", ("UR", "ultra-rare"), "https://bulbapedia.bulbagarden.net/wiki/Matchless_Fighters_(TCG)", "bulbapedia"),
    research("U0610", "sA", "010/023", ("fixed product", "fixed"), "https://collectory.cc/cards/481d9b00-6a36-4954-bb67-c5b411d5fe39", "collectory", specimen_id="SPEC-0462"),
    research("U0641", "sH", "038/053", ("fixed product", "fixed"), "https://bulbapedia.bulbagarden.net/wiki/Sword_%26_Shield_Family_Pok%C3%A9mon_Card_Game_(TCG)", "bulbapedia"),
    research("U0648", "svI", "046/066", ("fixed product", "fixed"), "https://bulbapedia.bulbagarden.net/wiki/Scarlet_%26_Violet_Battle_Academy_(TCG)", "bulbapedia", specimen_id="SPEC-0463", corroborating=["https://collectory.cc/cards/73c55006-427b-45ae-9a58-f7facd855820"]),
    research("U0677", "svLN", "010/022", ("fixed product", "fixed"), "https://bulbapedia.bulbagarden.net/wiki/Scarlet_%26_Violet_Stellar_Tera_Type_Starter_Set_(TCG)", "bulbapedia", specimen_id="SPEC-0438"),
    research("U0680", "20th", "047/072", ("fixed product", "fixed"), "https://bulbapedia.bulbagarden.net/wiki/Generations_(TCG)", "bulbapedia"),
    research("U0683", "mC", "567/742", ("N", "normal"), "https://collectory.cc/cards/a504064b-e9ee-44ee-9e6e-329a3b81974d", "collectory", specimen_id="SPEC-0458"),
    research("U0763", "mC", "569/742", ("N", "normal"), "https://collectory.cc/cards/5c9ad620-27b1-4a36-a7fb-1d50394b1fec", "collectory", specimen_id="SPEC-0460"),
    research("U0775", "xsv2a", "143/165", ("not stated", "unknown"), "https://bulbapedia.bulbagarden.net/wiki/151_(TCG)", "bulbapedia", specimen_id="SPEC-0061", legacy=["U0775", "U0780"]),
    research("U0785", "xm2a", "136/193", ("not stated", "unknown"), "https://www.cardmarket.com/en/Pokemon/Products/Singles/MEGA-Dream-ex-Additionals/Hops-Snorlax-V2-xm2a136", "cardmarket-listing-photo", specimen_id="SPEC-0410", corroborating=["https://globalbunjang.com/product/420832203"], legacy=["U0785", "U0790"]),
]


def source_first_row(row: dict[str, Any]) -> dict[str, Any]:
    if row in base.OFFICIAL + base.PROMOS:
        return base.source_first_row(row)
    specimen_clause = (
        f" Retained {row['specimenId']} is the positive physical/card-face observation."
        if row.get("specimenId") else
        " This is catalogue/set-list evidence only; no physical finish or appearance is inferred."
    )
    result = {
        "printId": row["printId"], "locality": "KR", "localSetCode": row["localSetCode"],
        "localNumber": row["localNumber"], "variant": "base", "language": "Korean",
        "script": "Hang", "name": "이브이&잠만보 GX" if row["cardName"].startswith("Eevee") else "잠만보",
        "cardName": row["cardName"],
        "catchUpOf": "positive Korean research applied to the issue #260 legacy queue",
        "specimenId": row.get("specimenId"), "providerId": row["providerId"],
        "sourceUrl": row["sourceUrl"], "corroborated": row["corroborated"],
        "markAssetUrl": None, "cardImageUrl": None,
        "evidence": (
            f"The retained positive {row['providerId']} record identifies Korean {row['localSetCode']} "
            f"{row['localNumber']} for {row['cardName']} and states rarity {row['rarity'][0] or 'not printed in the retained record'}."
            " This establishes local identity and the explicit Work mapping while keeping the Korean release distinct."
            + specimen_clause
        ),
    }
    if row.get("corroboratingSourceUrls"):
        result["corroboratingSourceUrls"] = row["corroboratingSourceUrls"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows = base.OFFICIAL + base.PROMOS + RESEARCH_ROWS
    for row in rows:
        row.setdefault("legacyVariants", sorted({str(UNITS_BY_ID[item].get("variant") or "base") for item in row["legacy"]}))
    source_rows = [source_first_row(row) for row in rows]

    prints = read(PRINTS)
    before = base.encoded(prints)
    by_print = {row["printId"]: row for row in prints["prints"]}
    by_print.update({row["printId"]: row for row in source_rows})
    prints["prints"] = sorted(by_print.values(), key=lambda row: row["printId"])
    prints["meta"]["generated"] = "2026-08-31"
    prints["meta"]["counts"]["admitted"] = len(prints["prints"])

    sources = read(SET_SOURCES)
    before_sources = base.encoded(sources)
    profiles = base.apply_profiles(sources, rows)
    capabilities = read(CAPABILITIES)
    before_capabilities = base.encoded(capabilities)
    base.apply_capabilities(capabilities)
    rekeys = read(REKEYS)
    before_rekeys = base.encoded(rekeys)
    graph = read(GRAPH)
    before_graph = base.encoded(graph)

    if not args.check:
        base.write(PRINTS, prints)
        base.write(SET_SOURCES, sources)
        base.write(CAPABILITIES, capabilities)
    graph, mappings = base.apply_graph(graph, profiles, rows)
    question = {"issueNumber": 260, "locality": "KR", "language": "Korean", "legacyUnitIds": base.ISSUE_UNITS, "defaultDisposition": "needs-positive-local-identity", "mappings": mappings}
    by_issue = {row["issueNumber"]: row for row in rekeys["questionSets"]}
    by_issue[260] = question
    rekeys["questionSets"] = sorted(by_issue.values(), key=lambda row: row["issueNumber"])

    stale = [label for label, old, new in (
        ("prints", before, base.encoded(prints)),
        ("set sources", before_sources, base.encoded(sources)),
        ("capabilities", before_capabilities, base.encoded(capabilities)),
        ("rekeys", before_rekeys, base.encoded(rekeys)),
        ("graph", before_graph, base.encoded(graph)),
    ) if old != new]
    if args.check:
        if stale:
            raise SystemExit("issue #260 Korean applied inputs are stale: " + ", ".join(stale))
        print("issue #260 Korean applied inputs are current")
        return 0
    base.write(REKEYS, rekeys)
    base.write(GRAPH, graph)
    print(f"applied {len(RESEARCH_ROWS)} Korean research rows, {len(mappings)} total positive re-keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
