"""Admit reviewed positive Traditional Chinese card evidence from issue #263."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import authoritative_graph as graph_projection  # noqa: E402
from admit_issue257_simplified_chinese_20260827 import (  # noqa: E402
    append_unique,
    encoded,
    stable_profile_id,
    upsert_edge,
    upsert_entity,
    upsert_migration,
)


PRINTS = ROOT / "verification" / "source_first_prints.json"
REKEYS = ROOT / "verification" / "legacy_issue_rekeys.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
FINISHES = ROOT / "verification" / "finish_overrides.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
DISCOVERY = ROOT / "verification" / "card_discovery_records.jsonl"
DISCOVERY_ADAPTERS = ROOT / "verification" / "card_discovery_adapters.json"
SPECIMEN_DIR = ROOT / "verification" / "specimens"
UNITS = ROOT / "verification" / "units.json"

ORIGIN = "reviewed-evidence-issue-263"
LOCALITY = "TW"
LANGUAGE = "T-Chinese"
SCRIPT = "Hant"
SUPERSEDED_PRINT_IDS = {"TW:AS5a:142/184:base"}
PRIOR_CONTRADICTED_LEGACY_IDS = {"U0265", "U0414", "U0558", "U0634"}
LEGACY_RELEASE_REWRITES = {
    "RELEASE:TW:T-Chinese:PKMTCH S-P:S-P 145:Snorlax-Rolling-Tackle-Heavy-Impact":
        "RELEASE:TW:T-Chinese:S-P:145:Snorlax-Rolling-Tackle-Heavy-Impact",
}


def card(
    detail: str,
    specimen: str,
    code: str,
    number: str,
    work: str,
    rarity: tuple[str, str | None],
    *legacy: str,
    variant: str = "base",
    card_name: str = "Snorlax",
    date: tuple[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "detail": detail,
        "specimenId": specimen,
        "printId": f"TW:{code}:{number}:{variant}",
        "localSetCode": code,
        "localNumber": number,
        "variant": variant,
        "work": work,
        "rarity": rarity,
        "legacy": list(legacy),
        "cardName": card_name,
        "date": date,
    }


SET_DATES = {
    "S4 F": ("2020-10-09", "day"),
    "SCA F": ("2021", "year"),
    "sH F": ("2021-10-01", "day"),
    "scD F": ("2021-10-01", "day"),
    "sc1a F": ("2020-06-19", "day"),
    "sc1b F": ("2020-06-19", "day"),
    "sc1D F": ("2020-06-19", "day"),
    "AS5a": ("2019-10-09", "day"),
    "AS5D": ("2019", "year"),
    "AC1b": ("2019", "year"),
    "S8b F": ("2021-12-17", "day"),
    "S-P": ("2022-12-15", "day"),
    "SI F": ("2022-02-18", "day"),
    "S10a F": ("2022-07-29", "day"),
    "S10b F": ("2022", "year"),
    "SN F": ("2022", "year"),
    "sv2a F": ("2023-06-30", "day"),
    "sv4K F": ("2023", "year"),
    "sv4a F": ("2023-12-22", "day"),
    "sv5a F": ("2024-04-03", "day"),
    "SVI F": ("2024-08-22", "day"),
    "SVM F": ("2024-12-20", "day"),
    "SV-P": ("2025", "year"),
    "SV9 F": ("2025-02-07", "day"),
    "svQP F": ("2025", "year"),
    "M2a F": ("2025-12-05", "day"),
    "MC F": ("2026-01-16", "day"),
    "M3 F": ("2026-02-06", "day"),
    "CLF": ("2023", "year"),
    "SM-P": ("2020", "year"),
}


OFFICIAL = [
    card("375", "SPEC-0278", "S4 F", "084/100", "Snorlax-Gormandize-Body-Slam", ("R", "rare"), "U0292"),
    card("1474", "SPEC-0279", "SCA F", "084/135", "Snorlax-Gormandize-Body-Slam", ("no printed rarity symbol", None)),
    card("2051", "SPEC-0280", "sH F", "038/053", "Snorlax-Heavy-Impact", ("no printed rarity symbol", None), "U0642"),
    card("2220", "SPEC-0281", "scD F", "111/159", "Snorlax-Slap-Push-Single-Strike-Tackle", ("no printed rarity symbol", None)),
    card("2395", "SPEC-0282", "sc1a F", "127/154", "Snorlax-Collect-Collapse", ("U", "uncommon")),
    card("2541", "SPEC-0283", "sc1b F", "119/153", "Snorlax-V-Swallow-Falling-Down", ("RR", "double-rare"), card_name="Snorlax V"),
    card("2542", "SPEC-0284", "sc1b F", "120/153", "Snorlax-VMAX-G-Max-Fall", ("RRR", "triple-rare"), card_name="Snorlax VMAX"),
    card("2707", "SPEC-0285", "sc1D F", "132/164", "Snorlax-Rolling-Tackle-Heavy-Impact", ("no printed rarity symbol", None)),
    card("2708", "SPEC-0286", "sc1D F", "133/164", "Snorlax-V-Swallow-Falling-Down", ("no printed rarity symbol", None), card_name="Snorlax V"),
    card("2856", "SPEC-0287", "AS5a", "117/184", "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX", ("RR", "double-rare"), "U0414", card_name="Eevee & Snorlax-GX"),
    card("2881", "SPEC-0288", "AS5a", "142", "Snorlax-Lazy-Eating-Big-Counter", ("U", "uncommon"), "U0265"),
    card("3553", "SPEC-0289", "AS5D", "118/169", "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX", ("RR", "double-rare"), card_name="Eevee & Snorlax-GX"),
    card("4244", "SPEC-0290", "AC1b", "118/158", "Snorlax-GX-Collapse-Thunderous-Snore-Pulverizing-Pancake-GX", ("no printed rarity symbol", None), card_name="Snorlax-GX"),
    card("5314", "SPEC-0291", "S8b F", "126/184", "Snorlax-Gormandize-Body-Slam", ("R", "rare"), "U0174"),
    card("5618", "SPEC-0292", "S-P", "145", "Snorlax-Rolling-Tackle-Heavy-Impact", ("PROMO", "promo"), "U0625"),
    card("5968", "SPEC-0293", "SI F", "341/414", "Snorlax-Heavy-Impact", ("no printed rarity symbol", None), "U0654"),
    card("5969", "SPEC-0294", "SI F", "342/414", "Snorlax-Heavy-Impact", ("no printed rarity symbol", None), "U0658"),
    card("6424", "SPEC-0295", "S10a F", "058/071", "Snorlax-Unfazed-Fat-Thumping-Snore", ("R", "rare"), "U0345"),
    card("6589", "SPEC-0296", "S10b F", "056/071", "Snorlax-Block-Collapse", ("R", "rare"), "U0203"),
    card("7016", "SPEC-0297", "SN F", "008/024", "Snorlax-Heavy-Impact", ("no printed rarity symbol", None), "U0771"),
    card("7426", "SPEC-0298", "sc1b F", "165/153", "Snorlax-V-Swallow-Falling-Down", ("SR", "super-rare"), card_name="Snorlax V"),
    card("8266", "SPEC-0299", "sv2a F", "143/165", "Snorlax-Voraciousness-Thudding-Press", ("U", "uncommon"), "U0104"),
    card("8304", "SPEC-0300", "sv2a F", "181/165", "Snorlax-Voraciousness-Thudding-Press", ("AR", "illustration-rare"), "U0050"),
    card("8943", "SPEC-0301", "sv4K F", "059/066", "Snorlax-Doll", ("U", "uncommon"), "U0261", card_name="Snorlax Doll"),
    card("9173", "SPEC-0302", "sv4a F", "145/190", "Snorlax-Voraciousness-Thudding-Press", ("no printed rarity symbol", None), "U0307"),
    card("9339", "SPEC-0303", "sv4a F", "310/190", "Snorlax-Voraciousness-Thudding-Press", ("S", "shiny-rare"), "U0385"),
    card("10298", "SPEC-0304", "sv5a F", "051/066", "Snorlax-But-First-Food-Heavy-Impact", ("U", "uncommon"), "U0234"),
    card("11337", "SPEC-0305", "SVI F", "046/066", "Snorlax-Lazy-Press", ("no printed rarity symbol", None)),
    card("12164", "SPEC-0306", "SVM F", "094/175", "Snorlax-ex-Strength-Toss-and-Turn-Press", ("no printed rarity symbol", None), "U0403", card_name="Snorlax ex"),
    card("12268", "SPEC-0307", "SV-P", "215", "Snorlax-Spike-Draw-Mega-Punch", ("PROMO", "promo")),
    card("12537", "SPEC-0308", "SV9 F", "075/100", "Hops-Snorlax-Extra-Helpings-Dynamic-Press", ("R", "rare"), "U0371", card_name="Hop's Snorlax"),
    card("13148", "SPEC-0309", "svQP F", "012/023", "Snorlax-Spike-Draw-Mega-Punch", ("no printed rarity symbol", None)),
    card("14796", "SPEC-0310", "M2a F", "136/193", "Hops-Snorlax-Extra-Helpings-Dynamic-Press", ("U", "uncommon"), "U0128", card_name="Hop's Snorlax"),
    card("14986", "SPEC-0311", "sv2a F", "143/165", "Snorlax-Voraciousness-Thudding-Press", ("U", "uncommon"), "U0776", "U0781", variant="poke-ball-pattern"),
    card("16453", "SPEC-0312", "M2a F", "136/193", "Hops-Snorlax-Extra-Helpings-Dynamic-Press", ("U", "uncommon"), "U0786", variant="poke-ball-pattern", card_name="Hop's Snorlax"),
    card("16454", "SPEC-0313", "M2a F", "136/193", "Hops-Snorlax-Extra-Helpings-Dynamic-Press", ("U", "uncommon"), "U0791", variant="colorless-energy-star-pattern", card_name="Hop's Snorlax"),
    card("17038", "SPEC-0314", "MC F", "567/742", "Snorlax-But-First-Food-Heavy-Impact", ("no printed rarity symbol", None), "U0684"),
    card("17039", "SPEC-0315", "MC F", "568/742", "Snorlax-Lazy-Press", ("no printed rarity symbol", None), "U0591"),
    card("17040", "SPEC-0316", "MC F", "569/742", "Hops-Snorlax-Extra-Helpings-Dynamic-Press", ("U", "uncommon"), "U0764", card_name="Hop's Snorlax"),
    card("18039", "SPEC-0317", "M3 F", "062/080", "Snorlax-Gormandizer-Collapse", ("C", "common"), "U0258"),
    card("18292", "SPEC-0318", "MC F", "568/742", "Snorlax-Lazy-Press", ("no printed rarity symbol", None), "U0591"),
]


PHOTO_ROWS = [
    {
        **card("clf-a", "SPEC-0319", "CLF", "016/032", "Snorlax-Collect-Collapse", ("no printed rarity symbol", None), "U0441"),
        "providerId": "shopee-tw",
        "sourceUrl": "https://shopee.tw/product/9736187/25206242683",
        "cardImageUrl": "https://cf.shopee.tw/file/tw-11134207-7r98p-lq0zta37yupu9a",
        "photograph": "SPEC-0319.jpg",
    },
    {
        **card("clf-b", "SPEC-0320", "CLF", "016/032", "Snorlax-Collect-Collapse", ("no printed rarity symbol", None), "U0441"),
        "providerId": "shopee-tw",
        "sourceUrl": "https://shopee.tw/product/4914178/22786197647",
        "cardImageUrl": "https://cf.shopee.tw/file/tw-11134207-7r991-lny2yl0igo4d9b",
        "photograph": "SPEC-0320.jpg",
    },
    {
        **card("clf-c", "SPEC-0321", "CLF", "016/032", "Snorlax-Collect-Collapse", ("no printed rarity symbol", None), "U0441"),
        "providerId": "shopee-tw",
        "sourceUrl": "https://shopee.tw/product/6777510/50602680694",
        "cardImageUrl": "https://cf.shopee.tw/file/tw-11134207-81ztc-mhx0q1fnelmuc0",
        "photograph": "SPEC-0321.jpg",
    },
    {
        **card("clf-d", "SPEC-0322", "CLF", "016/032", "Snorlax-Collect-Collapse", ("no printed rarity symbol", None), "U0441"),
        "providerId": "shopee-tw",
        "sourceUrl": "https://shopee.tw/product/16896213/51412187955",
        "cardImageUrl": "https://cf.shopee.tw/file/tw-11134207-820lg-mpg97q4m34lof2",
        "photograph": "SPEC-0322.jpg",
    },
    {
        **card("s10a077-nacg", "SPEC-0323", "S10a F", "077/071", "Snorlax-Unfazed-Fat-Thumping-Snore", ("CHR", "character-rare"), "U0169"),
        "providerId": "nacg",
        "sourceUrl": "https://www.nacg.tw/product-details.php?id=149595",
        "cardImageUrl": "https://www.nacg.tw/files/item/149595.jpg?v=1748956270",
        "photograph": "SPEC-0323.jpg",
    },
    {
        **card("s10a077-ruten", "SPEC-0324", "S10a F", "077/071", "Snorlax-Unfazed-Fat-Thumping-Snore", ("CHR", "character-rare"), "U0169"),
        "providerId": "ruten",
        "sourceUrl": "https://www.ruten.com.tw/item/22223353127192/",
        "cardImageUrl": "https://a.rimg.com.tw/s6/76c/3b0/akb5566/9/18/22223353127192_302.jpeg",
        "photograph": "SPEC-0324.jpeg",
    },
]


SUPPLEMENTAL = [
    card("existing-as5a203", "SPEC-0039", "AS5a", "203/184", "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX", ("SR", "super-rare"), "U0634", card_name="Eevee & Snorlax-GX"),
    card("existing-as5a222", "SPEC-0038", "AS5a", "222/184", "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX", ("HR", "hyper-rare"), "U0558", card_name="Eevee & Snorlax-GX"),
    card("existing-smp053", "SPEC-0029", "SM-P", "053", "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX", ("PROMO", "promo"), "U0414", card_name="Eevee & Snorlax-GX"),
    card("existing-sc1b177", "SPEC-0008", "sc1b F", "177/153", "Snorlax-VMAX-G-Max-Fall", ("HR", "hyper-rare"), card_name="Snorlax VMAX"),
    card(
        "svg021", "", "SVG", "021/049", "Snorlax-Unfazed-Fat-Thumping-Snore",
        ("no printed rarity symbol", None), "U0467", date=("2023-11-10", "day"),
    ),
]

ISSUE_UNITS = sorted({
    "U0050", "U0104", "U0128", "U0169", "U0174", "U0203", "U0234", "U0258",
    "U0261", "U0292", "U0307", "U0345", "U0371", "U0385", "U0403", "U0441",
    "U0467", "U0591", "U0602", "U0625", "U0642", "U0654", "U0658", "U0684",
    "U0764", "U0771", "U0776", "U0781", "U0786", "U0791",
})


def read(path: Path) -> dict[str, Any] | list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(encoded(payload), encoding="utf-8", newline="\n")


def discovery_rows() -> dict[str, dict[str, Any]]:
    wanted = {item["detail"] for item in OFFICIAL}
    rows = {}
    for line in DISCOVERY.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        detail = str(row.get("rawProviderId") or "")
        if row.get("locality") == LOCALITY and detail in wanted:
            rows[detail] = row
    if len(rows) != len(OFFICIAL):
        raise ValueError("retained Traditional Chinese discovery frontier differs from reviewed detail ids")
    return rows


def official_rows() -> list[dict[str, Any]]:
    discovered = discovery_rows()
    result = []
    for facts in OFFICIAL:
        raw = discovered[facts["detail"]]
        date, precision = facts["date"] or SET_DATES[facts["localSetCode"]]
        result.append({
            **facts,
            "locality": LOCALITY,
            "language": LANGUAGE,
            "script": SCRIPT,
            "name": raw["raw"]["localName"],
            "catchUpOf": "the exact Traditional Chinese counterpart established by its printed attacks and card traits",
            "providerId": "pokemon-card-asia",
            "sourceUrl": raw["sourceUrl"],
            "corroborated": False,
            "markAssetUrl": raw["raw"].get("setSymbolUrl"),
            "cardImageUrl": raw["raw"]["cardImageUrl"],
            "releaseDate": date,
            "releaseDatePrecision": precision,
            "releaseApproximate": False,
            "photograph": f"{facts['specimenId']}.png",
            "evidence": (
                f"The retained official Taiwan detail {facts['detail']} and {facts['specimenId']} show "
                f"{raw['raw']['localName']} {facts['localSetCode']} {facts['localNumber']}, including "
                f"the printed attacks used for the explicit Work mapping and rarity {facts['rarity'][0]}. "
                "The publisher render is identity and rarity evidence only; no physical finish is inferred."
            ),
        })
    return result


def enrich_photo_rows() -> list[dict[str, Any]]:
    result = []
    for row in PHOTO_ROWS:
        date, precision = row["date"] or SET_DATES[row["localSetCode"]]
        is_clf = row["localSetCode"] == "CLF"
        result.append({
            **row,
            "locality": LOCALITY,
            "language": LANGUAGE,
            "script": SCRIPT,
            "name": "卡比獸",
            "catchUpOf": "the exact Traditional Chinese counterpart established by the photographed card",
            "corroborated": not is_clf,
            "markAssetUrl": None,
            "releaseDate": date,
            "releaseDatePrecision": precision,
            "releaseApproximate": False,
            "evidence": (
                f"The retained listing photograph {row['specimenId']} positively shows Traditional Chinese "
                f"Snorlax {row['localSetCode']} {row['localNumber']}. "
                + ("Four retained Shopee seller listings show the same full-card mirror-holo CLF printing."
                   if is_clf else "NACG and Ruten independently identify the exact CHR card as Foil.")
            ),
            "physicalObservation": {
                "finish": "mirror-holo" if is_clf else "holo",
                "foilPattern": None,
                "markings": None,
                "markingRole": None,
                "cardSize": "standard",
                "basis": (
                    "The photograph visibly shows dense foil across the full card face, including the artwork window."
                    if is_clf else
                    "The exact specialist listing identifies the card as Foil and the physical listing photograph shows the same exact card."
                ),
            },
        })
    return result


def supplemental_rows(existing: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    urls = {
        "TW:SM-P:053:base": "https://pokumon.com/card/eevee-snorlax-gx-053-sm-p-chinese-promo",
        "TW:S-P:145:base": "https://pokumon.com/card/snorlax-145-s-p-chinese-promo",
        "TW:SV-P:215:base": "https://pokumon.com/card/snorlax-215-sv-p-chinese-promo",
    }
    result = []
    for facts in SUPPLEMENTAL:
        if facts["detail"] == "svg021":
            base = {
                "printId": facts["printId"], "locality": LOCALITY,
                "localSetCode": "SVG", "localNumber": "021/049", "variant": "base",
                "language": LANGUAGE, "script": SCRIPT, "name": "卡比獸", "cardName": "Snorlax",
                "catchUpOf": "the exact Traditional Chinese S10a Snorlax counterpart",
                "specimenId": None, "providerId": "52poke",
                "sourceUrl": "https://wiki.52poke.com/wiki/%E5%8D%A1%E6%AF%94%E5%85%BD%EF%BC%88S10a%EF%BC%89",
                "corroborated": False, "markAssetUrl": None, "cardImageUrl": None,
                "evidence": "The retained 52poke card record positively lists Traditional Chinese SVG 021/049 Snorlax with the exact S10a attack text.",
            }
        else:
            base = dict(existing[facts["printId"]])
            if facts["printId"] in urls:
                base["sourceUrl"] = urls[facts["printId"]]
        date, precision = facts["date"] or SET_DATES[facts["localSetCode"]]
        result.append({
            **facts, **base,
            "work": facts["work"], "rarity": facts["rarity"], "legacy": facts["legacy"],
            "releaseDate": date, "releaseDatePrecision": precision, "releaseApproximate": False,
        })
    return result


def persisted_source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in {
        "detail", "work", "rarity", "legacy", "date", "photograph", "physicalObservation",
    }}


def specimen_row(row: dict[str, Any]) -> dict[str, Any]:
    photograph = SPECIMEN_DIR / row["photograph"]
    observed = (
        f"Complete retained image for Traditional Chinese {row['cardName']} {row['localSetCode']} "
        f"{row['localNumber']} ({row['variant']}). The printed name, collector identity and attacks "
        "establish this card release and Work equivalence."
    )
    if row["providerId"] == "pokemon-card-asia":
        observed += " Publisher render: identity and rarity evidence only; no physical finish is inferred."
    else:
        observed += " The physical finish is recorded separately from identity."
    result = {
        "specimenId": row["specimenId"], "setCode": row["localSetCode"],
        "number": row["localNumber"], "variant": row["variant"], "language": LANGUAGE,
        "heldBy": (
            "publisher or marketplace seller"
            if row["providerId"] == "pokemon-card-asia" else "third-party seller"
        ),
        "inspectedFrom": "retained positive card image",
        "photograph": photograph.name, "photographSource": row["cardImageUrl"],
        "photographSha256": "sha256:" + hashlib.sha256(photograph.read_bytes()).hexdigest(),
        "observed": observed, "recordedAt": "2026-08-28",
        "citedBy": sorted({*row["legacy"], row["printId"]}), "listingUrl": row["sourceUrl"],
    }
    if row.get("physicalObservation"):
        result["physicalObservation"] = row["physicalObservation"]
    return result


def build_profile(code: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    numbers = sorted({row["localNumber"] for row in rows})
    denominators = {number.partition("/")[2] for number in numbers if number.partition("/")[2].isdigit()}
    return {
        "sourceRecordId": stable_profile_id(LOCALITY, code),
        "sourceKind": "source-first-local-set-profile", "provider": "mixed-positive-evidence",
        "providerRecordKey": f"{LOCALITY}\x1f{code}", "retrieved": "2026-08-28",
        "raw": {
            "localCode": code, "localName": None, "locality": LOCALITY,
            "languages": [LANGUAGE], "scripts": [SCRIPT],
            "printIds": sorted({row["printId"] for row in rows}),
            "providers": sorted({row["providerId"] for row in rows}),
            "sourceUrls": sorted({row["sourceUrl"] for row in rows if row.get("sourceUrl")}),
            "printedSetSize": int(next(iter(denominators))) if len(denominators) == 1 else None,
            "printedSetSizeBasis": "the denominator printed on every observed card" if len(denominators) == 1 else "no common printed denominator is inferred",
            "localeSuffix": "F" if code.endswith(" F") else None,
            "observedCollectorNumbers": numbers,
            "observedCoverage": "exact positive Traditional Chinese cards reviewed for issue #263, not a set enumeration",
            "markAssetUrls": sorted({row["markAssetUrl"] for row in rows if row.get("markAssetUrl")}),
            "cardImageUrls": sorted({row["cardImageUrl"] for row in rows if row.get("cardImageUrl")}),
        },
    }


def apply_profiles(document: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["localSetCode"]].append(row)
    profiles = {code: build_profile(code, group) for code, group in grouped.items()}
    by_id = {row["sourceRecordId"]: row for row in document["sourceRecords"]}
    by_id.update({profile["sourceRecordId"]: profile for profile in profiles.values()})
    document["sourceRecords"] = sorted(by_id.values(), key=lambda row: row["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(document["sourceRecords"])
    document["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        row["sourceKind"] == "source-first-local-set-profile" for row in document["sourceRecords"]
    )
    return profiles


def release_id(row: dict[str, Any]) -> str:
    return f"RELEASE:{LOCALITY}:{LANGUAGE}:{row['localSetCode']}:{row['localNumber']}:{row['work']}"


def apply_set_graph(graph: dict[str, Any], profile: dict[str, Any], code: str, claim_ids: list[str]) -> None:
    source_id = profile["sourceRecordId"]
    local_set_id = f"LOCALSET:{LOCALITY}:{quote(code, safe='')}"
    edition_id = f"EDITION:{LOCALITY}:{LANGUAGE}:{code}"
    localization_id = "LOCALIZATION:TW:zh-Hant"
    upsert_entity(graph, "set-source-record", source_id, profile, origin=ORIGIN)
    disposition = {"sourceRecordId": source_id, "disposition": "mapped", "targetRef": local_set_id, "reason": "positive Traditional Chinese source-first records establish this local set"}
    upsert_entity(graph, "set-source-disposition", source_id, disposition, origin=ORIGIN)
    upsert_edge(graph, "set-source-disposition", source_id, "disposes", "set-source-record", source_id)
    upsert_migration(graph, {"sourceKind": "set-catalogue-source", "sourceId": source_id, "disposition": "mapped", "targetRef": local_set_id, "reason": disposition["reason"]})
    matches = [item for item in graph["entities"] if item.get("entityType") == "local-set" and item.get("entityId") == local_set_id]
    if matches:
        append_unique(matches[0]["payload"].setdefault("sourceRecordIds", []), source_id)
    else:
        upsert_entity(graph, "local-set", local_set_id, {"localSetId": local_set_id, "locality": LOCALITY, "localCode": code, "observedNames": [], "productKind": "physical-card-set-or-product", "sourceRecordIds": [source_id]}, origin=ORIGIN)
    upsert_edge(graph, "local-set", local_set_id, "observed-by", "set-source-record", source_id)
    editions = [item for item in graph["entities"] if item.get("entityType") == "set-edition" and item.get("entityId") == edition_id]
    if editions:
        payload = editions[0]["payload"]
        append_unique(payload["identity"].setdefault("establishingClaimIds", []), *claim_ids)
        append_unique(payload["catalogue"].setdefault("establishingEvidenceIds", []), source_id)
        payload["catalogue"]["localSetId"] = local_set_id
    else:
        upsert_entity(graph, "set-edition", edition_id, {
            "setEditionId": edition_id,
            "identity": {"setEditionId": edition_id, "locality": LOCALITY, "language": LANGUAGE, "script": SCRIPT, "localSetCode": code, "localIdentifierKnown": True, "state": "identified", "viaLegacySetCodes": [], "establishingClaimIds": claim_ids, "localizationId": localization_id},
            "catalogue": {"setEditionId": edition_id, "localSetId": local_set_id, "locality": LOCALITY, "language": LANGUAGE, "script": SCRIPT, "localCode": code, "state": "identified", "establishingEvidenceIds": [source_id], "localizationId": localization_id},
        }, origin=ORIGIN)
    upsert_edge(graph, "set-edition", edition_id, "belongs-to", "local-set", local_set_id)
    upsert_edge(graph, "set-edition", edition_id, "localized-as", "localization", localization_id, {"decisionRef": "https://github.com/m4s-ai/snoredex-data/issues/254", "reviewedAt": "2026-08-24"})


def remove_old_releases(
    graph: dict[str, Any], group: list[dict[str, Any]], target: str, units: dict[str, dict[str, Any]],
) -> tuple[list[tuple[str, str | None]], list[str], dict[str, list[str]]]:
    first = group[0]
    legacy_ids = {unit_id for row in group for unit_id in row["legacy"]}
    active_legacy_ids = legacy_ids & set(ISSUE_UNITS)
    patterns = {(str(units[unit_id]["setCode"]), str(units[unit_id]["number"]).lstrip("0")) for unit_id in legacy_ids}

    def matches_old_ref(value: Any) -> bool:
        text = str(value or "")
        return text.startswith(f"RELEASE:{LOCALITY}:{LANGUAGE}:") and any(
            f":via-{code}:unknown-local-set:via-{number}:" in text for code, number in patterns
        )

    obsolete = {
        item["entityId"] for item in graph["entities"]
        if item.get("entityType") == "card-release" and item.get("entityId") != target
        and item.get("payload", {}).get("language") == LANGUAGE
        and ((item.get("payload", {}).get("localSetCode") == first["localSetCode"]
              and str(item.get("payload", {}).get("localNumber") or "").partition("/")[0].lstrip("0")
              == first["localNumber"].partition("/")[0].lstrip("0")) or matches_old_ref(item.get("entityId")))
    }
    for item in graph["entities"]:
        payload = item.get("payload", {})
        if item.get("entityType") == "candidate-claim" and payload.get("sourceKind") == "legacy-language-unit" and payload.get("sourceId") in active_legacy_ids:
            old_target = payload.get("materializedTargetId")
            if old_target and old_target != target:
                obsolete.add(old_target)
    old_payloads = [item.get("payload", {}) for item in graph["entities"] if item.get("entityType") == "card-release" and item.get("entityId") in {*obsolete, target}]
    legacy_claims: list[tuple[str, str | None]] = []
    recovered_legacy_ids: set[str] = set()
    finish_claims: list[str] = []
    rarity_claims: list[str] = []
    for item in graph["entities"]:
        payload = item.get("payload", {})
        if item.get("entityType") != "candidate-claim":
            continue
        if payload.get("sourceKind") == "legacy-language-unit" and payload.get("sourceId") in active_legacy_ids:
            payload["proposedTargetId"] = target
            payload["materializedTargetId"] = target
            legacy_claims.append((item["entityId"], payload.get("sourceRecord")))
            recovered_legacy_ids.add(payload["sourceId"])
            upsert_migration(graph, {"sourceKind": "legacy-language-unit", "sourceId": payload["sourceId"], "disposition": "established-and-mapped", "targetRef": target, "reason": payload["reason"]})
        proposed = payload.get("proposedCardReleaseId")
        if payload.get("sourceKind") == "finish-printing-record" and (proposed in obsolete or matches_old_ref(proposed)):
            payload["proposedCardReleaseId"] = target
            finish_claims.append(item["entityId"])
        if item.get("entityType") == "rarity-claim" and payload.get("cardReleaseId") in obsolete:
            payload["cardReleaseId"] = target
            rarity_claims.append(item["entityId"])
    for disposition in graph["migrationDispositions"]:
        if disposition.get("targetRef") in obsolete or matches_old_ref(disposition.get("targetRef")):
            disposition["targetRef"] = target
        if "targetRefs" in disposition:
            disposition["targetRefs"] = [target if value in obsolete or matches_old_ref(value) else value for value in disposition["targetRefs"]]
    catalogue = {item["entityId"] for item in graph["entities"] if item.get("entityType") == "catalogue-card-release-ref" and item.get("payload", {}).get("cardReleaseId") in obsolete}
    graph["entities"] = [item for item in graph["entities"] if not ((item.get("entityType") == "card-release" and item.get("entityId") in obsolete) or (item.get("entityType") == "catalogue-card-release-ref" and item.get("entityId") in catalogue))]
    graph["edges"] = [edge for edge in graph["edges"] if not ((edge.get("fromType") == "card-release" and edge.get("fromId") in obsolete) or (edge.get("toType") == "card-release" and edge.get("toId") in obsolete) or (edge.get("fromType") == "catalogue-card-release-ref" and edge.get("fromId") in catalogue) or (edge.get("toType") == "catalogue-card-release-ref" and edge.get("toId") in catalogue))]
    graph["edges"] = [edge for edge in graph["edges"] if not (edge.get("fromId") in finish_claims and edge.get("relation") == "proposes-for" and edge.get("toId") != target)]
    for rarity_id in rarity_claims:
        upsert_edge(graph, "rarity-claim", rarity_id, "asserts-rarity-for", "card-release", target)
    return legacy_claims, finish_claims, {
        "legacyProducts": sorted({item for payload in old_payloads for item in payload.get("legacyProducts", [])}),
        "legacyVariants": sorted({item for payload in old_payloads for item in payload.get("legacyVariants", [])}),
        "legacyCounterpartUnitIds": sorted({item for payload in old_payloads for item in payload.get("legacyCounterpartUnitIds", [])}),
        "recoveredLegacyIds": sorted(recovered_legacy_ids),
        "claimIds": sorted({item for payload in old_payloads for item in payload.get("claimIds", []) if not item.startswith("CLAIM:legacy:")}),
        "establishingClaimIds": sorted({item for payload in old_payloads for item in payload.get("establishingClaimIds", []) if not item.startswith("CLAIM:legacy:")}),
        "nonEstablishingClaimIds": sorted({item for payload in old_payloads for item in payload.get("nonEstablishingClaimIds", [])}),
        "sourceRecords": sorted({item for payload in old_payloads for item in payload.get("sourceRecords", [])}),
        "sourceFirstRecordIds": sorted({item for payload in old_payloads for item in payload.get("sourceFirstRecordIds", [])}),
        "legacyIdentityAliases": sorted({tuple(item) for payload in old_payloads for item in payload.get("legacyIdentityAliases", [])}),
    }


def apply_release_group(
    graph: dict[str, Any], profile: dict[str, Any], group: list[dict[str, Any]], units: dict[str, dict[str, Any]],
) -> None:
    first = group[0]
    rid = release_id(first)
    legacy_claims, finish_claims, heritage = remove_old_releases(graph, group, rid, units)
    unique_rows = {row["printId"]: row for row in group}.values()
    source_claim_ids = []
    for row in unique_rows:
        claim_id = f"CLAIM:source-first:{row['printId']}"
        source_claim_ids.append(claim_id)
        claim = {"claimId": claim_id, "claimKind": "card-release", "sourceKind": "source-first-record", "sourceId": row["printId"], "sourceRecord": row["sourceUrl"], "evidenceStatus": "confirmed", "disposition": "established-and-mapped", "proposedTargetId": rid, "materializedTargetId": rid, "reason": "positive exact Traditional Chinese card record and retained image"}
        upsert_entity(graph, "candidate-claim", claim_id, claim, origin=ORIGIN)
        upsert_edge(graph, "candidate-claim", claim_id, "materializes", "card-release", rid, {"disposition": "established-and-mapped"})
        upsert_migration(graph, {"sourceKind": "source-first-record", "sourceId": row["printId"], "disposition": "established-and-mapped", "targetRef": rid, "reason": claim["reason"]})
    legacy_ids = sorted(
        {unit_id for row in group for unit_id in row["legacy"]}
        | set(heritage["legacyCounterpartUnitIds"])
        | set(heritage["recoveredLegacyIds"])
    )
    claim_ids = sorted({*source_claim_ids, *(item[0] for item in legacy_claims)})
    mapping_state = "mapped-by-explicit-equivalence" if legacy_ids else "mapped"
    payload = {
        "cardReleaseId": rid, "setEditionId": f"EDITION:{LOCALITY}:{LANGUAGE}:{first['localSetCode']}",
        "locality": LOCALITY, "language": LANGUAGE, "script": SCRIPT,
        "localSetCode": first["localSetCode"], "localNumber": first["localNumber"],
        "localIdentifierKnown": True, "state": "identified", "work": first["work"],
        "workMappingState": mapping_state, "viaLegacySetCode": None, "viaLegacyNumber": None,
        "claimIds": claim_ids, "establishingClaimIds": claim_ids, "nonEstablishingClaimIds": heritage["nonEstablishingClaimIds"],
        "legacyVariants": sorted(set(heritage["legacyVariants"]) | {row["variant"] for row in group}),
        "legacyProducts": heritage["legacyProducts"],
        "sourceRecords": sorted({row["sourceUrl"] for row in group if row.get("sourceUrl")} | {value for _, value in legacy_claims if value}),
        "sourceFirstRecordIds": sorted({row["printId"] for row in group}),
        "legacyCounterpartUnitIds": legacy_ids,
        "legacyIdentityAliases": sorted({(str(units[unit_id]["setCode"]), str(units[unit_id]["number"])) for unit_id in legacy_ids} | set(heritage["legacyIdentityAliases"])),
        "releaseDate": first["releaseDate"], "releaseDatePrecision": first["releaseDatePrecision"], "releaseApproximate": False,
    }
    upsert_entity(graph, "card-release", rid, payload, origin=ORIGIN)
    work_id = f"WORK:{first['work']}"
    if not any(item.get("entityType") == "work" and item.get("entityId") == work_id for item in graph["entities"]):
        upsert_entity(graph, "work", work_id, {"workId": work_id, "cardKey": first["work"]}, origin=ORIGIN)
    for claim_id, _ in legacy_claims:
        upsert_edge(graph, "candidate-claim", claim_id, "materializes", "card-release", rid, {"disposition": "established-and-mapped"})
    for claim_id in finish_claims:
        upsert_edge(graph, "candidate-claim", claim_id, "proposes-for", "card-release", rid)
    upsert_edge(graph, "card-release", rid, "belongs-to", "set-edition", payload["setEditionId"])
    upsert_edge(graph, "card-release", rid, "implements", "work", work_id, {"state": mapping_state, "basis": "exact Traditional Chinese printed attacks and card traits"})
    upsert_entity(graph, "catalogue-card-release-ref", rid, {"cardReleaseId": rid, "setEditionId": payload["setEditionId"], "collectorNumber": first["localNumber"], "origin": "issue-263-positive-evidence"}, origin=ORIGIN)
    upsert_edge(graph, "catalogue-card-release-ref", rid, "belongs-to", "set-edition", payload["setEditionId"])
    upsert_edge(graph, "catalogue-card-release-ref", rid, "references", "card-release", rid)
    rarity_id = "RARITYCLAIM:issue263:" + rid.removeprefix(f"RELEASE:{LOCALITY}:{LANGUAGE}:")
    rarity = {"rarityClaimId": rarity_id, "cardReleaseId": rid, "sourceRecordId": profile["sourceRecordId"], "sourceProvider": "mixed-positive-evidence", "sourceVocabulary": "printed-Traditional-Chinese-card", "sourceNativeValue": first["rarity"][0], "normalizedRarityId": first["rarity"][1], "sourceProductKey": first["sourceUrl"]}
    upsert_entity(graph, "rarity-claim", rarity_id, rarity, origin=ORIGIN)
    upsert_edge(graph, "rarity-claim", rarity_id, "asserts-rarity-for", "card-release", rid)
    upsert_edge(graph, "rarity-claim", rarity_id, "observed-by", "set-source-record", profile["sourceRecordId"])


def apply_graph(
    graph: dict[str, Any], profiles: dict[str, dict[str, Any]], rows: list[dict[str, Any]], units: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_release: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_code[row["localSetCode"]].append(row)
        by_release[release_id(row)].append(row)
    for code, group in by_code.items():
        apply_set_graph(graph, profiles[code], code, sorted({f"CLAIM:source-first:{row['printId']}" for row in group}))
    for group in by_release.values():
        apply_release_group(graph, profiles[group[0]["localSetCode"]], group, units)
    mappings_by_unit = {}
    for row in rows:
        rid = release_id(row)
        for legacy_id in row["legacy"]:
            if legacy_id not in ISSUE_UNITS:
                continue
            if legacy_id in mappings_by_unit:
                continue
            assertion_id = f"ASSERT:same-work:{legacy_id}:{row['printId']}"
            evidence = "The exact Traditional Chinese card identity and printed attacks establish this local counterpart without merging release identities."
            assertion = {"assertionId": assertion_id, "assertionType": "same-work-decision", "fromId": rid, "toId": f"WORK:{row['work']}", "legacyUnitId": legacy_id, "sourceFirstRecordId": row["printId"], "assertedBy": "repository verification pass", "assertedAt": "2026-08-28", "evidenceUrl": row["sourceUrl"], "evidence": evidence, "destructiveMergeAllowed": False}
            upsert_entity(graph, "equivalence-assertion", assertion_id, assertion, origin=ORIGIN)
            upsert_edge(graph, "equivalence-assertion", assertion_id, "relates", "card-release", rid, assertion)
            upsert_edge(graph, "equivalence-assertion", assertion_id, "relates", "work", f"WORK:{row['work']}", assertion)
            upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": legacy_id, "disposition": "linked-local-counterpart", "targetRef": rid, "targetRefs": [rid], "reason": "issue #263 re-key"})
            mappings_by_unit[legacy_id] = {key: assertion[key] for key in ("legacyUnitId", "sourceFirstRecordId", "assertionType", "assertedBy", "assertedAt", "evidenceUrl", "evidence")}
    for legacy_id in set(ISSUE_UNITS) - set(mappings_by_unit):
        upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": legacy_id, "disposition": "needs-positive-local-identity", "targetRef": None, "targetRefs": [], "reason": "issue #263 re-key"})
    restore_prior_rekey_migrations(graph)
    return graph_projection.project_physical_evidence(graph), sorted(mappings_by_unit.values(), key=lambda row: row["legacyUnitId"])


def restore_prior_rekey_migrations(graph: dict[str, Any]) -> None:
    targets: dict[str, set[str]] = defaultdict(set)
    for item in graph["entities"]:
        payload = item.get("payload", {})
        legacy_id = payload.get("legacyUnitId")
        if item.get("entityType") == "equivalence-assertion" and legacy_id in PRIOR_CONTRADICTED_LEGACY_IDS:
            targets[legacy_id].add(payload["fromId"])
    for legacy_id, release_ids in targets.items():
        ordered = sorted(release_ids)
        upsert_migration(graph, {
            "sourceKind": "legacy-issue-rekey", "sourceId": legacy_id,
            "disposition": "linked-local-counterpart", "targetRef": ordered[0],
            "targetRefs": ordered, "reason": "issue #84 re-key",
        })


def apply_finish_evidence(document: dict[str, Any]) -> None:
    document["sources"].update({
        "tw-clf016-shopee-a": {"url": PHOTO_ROWS[0]["sourceUrl"], "sourceType": "Seller listing photograph", "authorityTier": "seller-listing-photo", "coverage": "positive-only", "supportsAbsence": False, "languages": [LANGUAGE], "retrievedAt": "2026-08-28", "evidence": "Exact CLF 016/032 Traditional Chinese card photographed with full-card mirror holo."},
        "tw-clf016-shopee-b": {"url": PHOTO_ROWS[1]["sourceUrl"], "sourceType": "Seller listing photograph", "authorityTier": "seller-listing-photo", "coverage": "positive-only", "supportsAbsence": False, "languages": [LANGUAGE], "retrievedAt": "2026-08-28", "evidence": "Additional exact CLF 016/032 Traditional Chinese mirror-holo card photograph."},
        "tw-clf016-shopee-c": {"url": PHOTO_ROWS[2]["sourceUrl"], "sourceType": "Seller listing photograph", "authorityTier": "seller-listing-photo", "coverage": "positive-only", "supportsAbsence": False, "languages": [LANGUAGE], "retrievedAt": "2026-08-28", "evidence": "Additional exact CLF 016/032 Traditional Chinese mirror-holo card photograph."},
        "tw-clf016-shopee-d": {"url": PHOTO_ROWS[3]["sourceUrl"], "sourceType": "Seller listing photograph", "authorityTier": "seller-listing-photo", "coverage": "positive-only", "supportsAbsence": False, "languages": [LANGUAGE], "retrievedAt": "2026-08-28", "evidence": "Additional exact CLF 016/032 Traditional Chinese mirror-holo card photograph."},
        "tw-s10a077-nacg": {"url": PHOTO_ROWS[4]["sourceUrl"], "sourceType": "Specialist card listing with exact retained image", "authorityTier": "specialist-reference", "coverage": "positive-only", "supportsAbsence": False, "languages": [LANGUAGE], "retrievedAt": "2026-08-28", "evidence": "Exact S10a F 077/071 CHR listing explicitly identifies the card as Foil."},
        "tw-s10a077-ruten": {"url": PHOTO_ROWS[5]["sourceUrl"], "sourceType": "Seller listing photograph", "authorityTier": "seller-listing-photo", "coverage": "positive-only", "supportsAbsence": False, "languages": [LANGUAGE], "retrievedAt": "2026-08-28", "evidence": "Independent seller photograph of exact Traditional Chinese S10a F 077/071 CHR."},
    })
    rows = [
        {"setCode": "m2a", "releaseSetCode": "M2a F", "number": "136", "languages": [LANGUAGE], "printings": []},
        {"setCode": "xm2a", "releaseSetCode": "M2a F", "number": "136", "languages": [LANGUAGE], "suppressAutoFinishes": ["non-holo"], "printings": []},
    ]
    rows.extend(
        {"setCode": "mC", "releaseSetCode": "MC F", "number": number, "languages": [LANGUAGE], "printings": []}
        for number in ("567", "568", "569")
    )
    rows += [
        {"setCode": "m3", "releaseSetCode": "M3 F", "number": "062", "languages": [LANGUAGE], "printings": []},
        {"setCode": "s10a", "releaseSetCode": "S10a F", "number": "058", "languages": [LANGUAGE], "printings": []},
        {"setCode": "s10a", "releaseSetCode": "S10a F", "number": "077", "languages": [LANGUAGE], "printings": [{"finish": "holo", "foilPattern": None, "markings": [], "distribution": None, "cardSize": "standard", "mappedVariants": ["V2"], "verificationStatus": "confirmed", "sourceRefs": ["tw-s10a077-nacg", "tw-s10a077-ruten"]}]},
        {"setCode": "s10b", "releaseSetCode": "S10b F", "number": "056", "languages": [LANGUAGE], "printings": []},
        {"setCode": "s4", "releaseSetCode": "S4 F", "number": "84", "languages": [LANGUAGE], "printings": []},
        {"setCode": "s8b", "releaseSetCode": "S8b F", "number": "126", "languages": [LANGUAGE], "printings": []},
        {"setCode": "sH", "releaseSetCode": "sH F", "number": "038", "languages": [LANGUAGE], "printings": []},
    ]
    rows.extend(
        {"setCode": "sI100", "releaseSetCode": "SI F", "number": number, "languages": [LANGUAGE], "printings": []}
        for number in ("341", "342")
    )
    rows += [
        {"setCode": "sN", "releaseSetCode": "SN F", "number": "008", "languages": [LANGUAGE], "printings": []},
    ]
    rows.extend(
        {"setCode": "sv2a", "releaseSetCode": "sv2a F", "number": number, "languages": [LANGUAGE], "printings": []}
        for number in ("143", "181")
    )
    rows += [
        {"setCode": "xsv2a", "releaseSetCode": "sv2a F", "number": "143", "languages": [LANGUAGE], "suppressAutoFinishes": ["non-holo"], "printings": []},
    ]
    rows.extend(
        {"setCode": "sv4a", "releaseSetCode": "sv4a F", "number": number, "languages": [LANGUAGE], "printings": []}
        for number in ("145", "310")
    )
    rows += [
        {"setCode": "sv5a", "releaseSetCode": "sv5a F", "number": "051", "languages": [LANGUAGE], "printings": []},
        {"setCode": "sv9", "releaseSetCode": "SV9 F", "number": "075", "languages": [LANGUAGE], "printings": []},
        {"setCode": "sv4K", "releaseSetCode": "sv4K F", "number": "059", "languages": [LANGUAGE], "printings": []},
        {"setCode": "svM", "releaseSetCode": "SVM F", "number": "094", "languages": [LANGUAGE], "printings": []},
        {"setCode": "PKMTCH S-P", "releaseSetCode": "S-P", "number": "S-P 145", "languages": [LANGUAGE], "printings": []},
        {"setCode": "svG", "releaseSetCode": "SVG", "number": "021", "languages": [LANGUAGE], "printings": []},
        {"setCode": "CLF", "releaseSetCode": "CLF", "number": "016", "languages": [LANGUAGE], "printings": [{"finish": "mirror-holo", "foilPattern": None, "markings": [], "distribution": None, "cardSize": "standard", "mappedVariants": ["base"], "verificationStatus": "confirmed", "sourceRefs": [f"tw-clf016-shopee-{letter}" for letter in "abcd"]}]},
    ]
    keys = {(row["setCode"], row["number"], tuple(row.get("languages") or [])) for row in rows}
    document["overrides"] = [row for row in document["overrides"] if (row["setCode"], row["number"], tuple(row.get("languages") or [])) not in keys] + rows
    document["meta"]["lastUpdated"] = "2026-08-28"


def apply_discovery_adapters(document: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    discovered = discovery_rows()
    mappings = {(row["providerId"], row["rawLocale"], str(row["rawProviderId"])): row for row in document["explicitMappings"]}
    by_detail = {row["detail"]: row for row in rows}
    for detail, raw in discovered.items():
        if raw.get("bucket") != "new-candidate":
            continue
        source = by_detail[detail]
        key = (raw["providerId"], raw["rawLocale"], detail)
        mappings[key] = {"providerId": raw["providerId"], "surfaceId": raw["surfaceId"], "rawLocale": raw["rawLocale"], "rawProviderId": detail, "mode": "exact-match", "targetCardReleaseId": release_id(source), "evidence": "The retained official Taiwan detail and exact image establish this Traditional Chinese card release and its printed Work traits."}
    document["explicitMappings"] = sorted(mappings.values(), key=lambda row: (row["providerId"], row["rawLocale"], str(row["rawProviderId"])))


def remove_superseded_graph_records(graph: dict[str, Any]) -> None:
    claim_ids = {f"CLAIM:source-first:{print_id}" for print_id in SUPERSEDED_PRINT_IDS}
    obsolete_entities = {
        item["entityId"] for item in graph["entities"]
        if item.get("entityId") in claim_ids
        or (item.get("entityType") == "rarity-claim" and ":AS5a:142/184:" in item.get("entityId", ""))
    }
    graph["entities"] = [item for item in graph["entities"] if item.get("entityId") not in obsolete_entities]
    graph["edges"] = [
        edge for edge in graph["edges"]
        if edge.get("fromId") not in obsolete_entities and edge.get("toId") not in obsolete_entities
    ]
    graph["migrationDispositions"] = [
        row for row in graph["migrationDispositions"]
        if row.get("sourceId") not in SUPERSEDED_PRINT_IDS
    ]
    rewritten_rarities: list[tuple[str, str]] = []
    for item in graph["entities"]:
        payload = item.get("payload", {})
        target = LEGACY_RELEASE_REWRITES.get(payload.get("cardReleaseId"))
        if item.get("entityType") == "rarity-claim" and target:
            payload["cardReleaseId"] = target
            rewritten_rarities.append((item["entityId"], target))
    graph["edges"] = [
        edge for edge in graph["edges"]
        if not (
            edge.get("fromId") in {rarity_id for rarity_id, _ in rewritten_rarities}
            and edge.get("relation") == "asserts-rarity-for"
        )
    ]
    for rarity_id, target in rewritten_rarities:
        upsert_edge(graph, "rarity-claim", rarity_id, "asserts-rarity-for", "card-release", target)
    contradicted_claim_ids = {
        f"CLAIM:legacy:{legacy_id}" for legacy_id in PRIOR_CONTRADICTED_LEGACY_IDS
    }
    graph["edges"] = [
        edge for edge in graph["edges"]
        if not (
            edge.get("fromId") in contradicted_claim_ids
            and edge.get("relation") == "materializes"
        )
    ]
    graph["migrationDispositions"] = [
        row for row in graph["migrationDispositions"]
        if not (
            row.get("sourceKind") == "legacy-language-unit"
            and row.get("sourceId") in PRIOR_CONTRADICTED_LEGACY_IDS
            and row.get("disposition") == "established-and-mapped"
        )
    ]
    for item in graph["entities"]:
        payload = item.get("payload", {})
        if item.get("entityId") in contradicted_claim_ids:
            payload["materializedTargetId"] = None
            upsert_migration(graph, {
                "sourceKind": "legacy-language-unit",
                "sourceId": payload["sourceId"],
                "disposition": payload["disposition"],
                "targetRef": None,
                "reason": payload["reason"],
            })
        if item.get("entityType") == "card-release":
            for key in ("claimIds", "establishingClaimIds", "nonEstablishingClaimIds"):
                payload[key] = [value for value in payload.get(key, []) if value not in claim_ids]
        if item.get("entityType") != "set-edition":
            continue
        identity = payload.get("identity", {})
        identity["establishingClaimIds"] = [
            value for value in identity.get("establishingClaimIds", []) if value not in claim_ids
        ]
    prior_assertions = {
        item["entityId"]: item["payload"] for item in graph["entities"]
        if item.get("entityType") == "equivalence-assertion"
        and item.get("payload", {}).get("legacyUnitId") in PRIOR_CONTRADICTED_LEGACY_IDS
    }
    graph["edges"] = [
        edge for edge in graph["edges"]
        if not (
            edge.get("fromType") == "equivalence-assertion"
            and edge.get("fromId") in prior_assertions
            and edge.get("relation") == "relates"
        )
    ]
    for assertion_id, assertion in prior_assertions.items():
        upsert_edge(
            graph, "equivalence-assertion", assertion_id, "relates",
            "card-release", assertion["fromId"], assertion,
        )
        upsert_edge(
            graph, "equivalence-assertion", assertion_id, "relates",
            "work", assertion["toId"], assertion,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    prints = read(PRINTS)
    existing_prints = {row["printId"]: row for row in prints["prints"]}
    official = official_rows()
    photos = enrich_photo_rows()
    supplemental = supplemental_rows(existing_prints)
    rows = official + photos + supplemental
    units = {row["unitId"]: row for row in read(UNITS)}

    before_prints = encoded(prints)
    by_print = dict(existing_prints)
    for print_id in SUPERSEDED_PRINT_IDS:
        by_print.pop(print_id, None)
    for row in rows:
        persisted = persisted_source_row(row)
        if (
            row["corroborated"]
            and row["printId"] in by_print
            and row["printId"] in {item["printId"] for item in photos}
        ):
            persisted["corroboratingSourceUrls"] = sorted({item["sourceUrl"] for item in photos if item["printId"] == row["printId"]})
        by_print[row["printId"]] = persisted
    prints["prints"] = sorted(by_print.values(), key=lambda row: row["printId"])
    prints["meta"]["generated"] = "2026-08-28"
    prints["meta"]["counts"]["admitted"] = len(prints["prints"])

    specimens = read(SPECIMENS)
    before_specimens = encoded(specimens)
    by_specimen = {row["specimenId"]: row for row in specimens["specimens"]}
    by_specimen.update({row["specimenId"]: specimen_row(row) for row in official + photos})
    for row in rows:
        specimen_id = row.get("specimenId")
        if specimen_id and specimen_id in by_specimen:
            append_unique(by_specimen[specimen_id].setdefault("citedBy", []), row["printId"])
            by_specimen[specimen_id]["citedBy"] = sorted(set(by_specimen[specimen_id]["citedBy"]))
            if row.get("sourceUrl"):
                by_specimen[specimen_id]["listingUrl"] = row["sourceUrl"]
    specimens["specimens"] = sorted(by_specimen.values(), key=lambda row: int(row["specimenId"].split("-")[1]))
    specimens["count"] = len(specimens["specimens"])
    if not args.check:
        write(SPECIMENS, specimens)

    sources = read(SET_SOURCES)
    before_sources = encoded(sources)
    profiles = apply_profiles(sources, rows)

    finishes = read(FINISHES)
    before_finishes = encoded(finishes)
    apply_finish_evidence(finishes)
    if not args.check:
        write(FINISHES, finishes)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "finishes.py"), "--offline"], cwd=ROOT, check=True)

    adapters = read(DISCOVERY_ADAPTERS)
    before_adapters = encoded(adapters)
    apply_discovery_adapters(adapters, official)

    rekeys = read(REKEYS)
    before_rekeys = encoded(rekeys)
    graph = read(GRAPH)
    before_graph = encoded(graph)
    remove_superseded_graph_records(graph)
    graph, mappings = apply_graph(graph, profiles, rows, units)
    question = {"issueNumber": 263, "locality": LOCALITY, "language": LANGUAGE, "legacyUnitIds": ISSUE_UNITS, "defaultDisposition": "needs-positive-local-identity", "mappings": mappings}
    by_issue = {row["issueNumber"]: row for row in rekeys["questionSets"]}
    by_issue[263] = question
    rekeys["questionSets"] = sorted(by_issue.values(), key=lambda row: row["issueNumber"])

    stale = [label for label, before, after in (
        ("prints", before_prints, encoded(prints)), ("specimens", before_specimens, encoded(specimens)),
        ("set sources", before_sources, encoded(sources)), ("finishes", before_finishes, encoded(finishes)),
        ("discovery adapters", before_adapters, encoded(adapters)), ("rekeys", before_rekeys, encoded(rekeys)),
        ("graph", before_graph, encoded(graph)),
    ) if before != after]
    if args.check:
        if stale:
            raise SystemExit("issue #263 Traditional Chinese reviewed inputs are stale: " + ", ".join(stale))
        print("issue #263 Traditional Chinese reviewed inputs are current")
        return 0

    for path, document in (
        (PRINTS, prints), (SPECIMENS, specimens), (SET_SOURCES, sources), (FINISHES, finishes),
        (DISCOVERY_ADAPTERS, adapters), (REKEYS, rekeys), (GRAPH, graph),
    ):
        write(path, document)
    print(f"admitted {len({row['printId'] for row in rows})} Traditional Chinese source-first records, {len(mappings)} positive re-keys and {len(official) + len(photos)} new image specs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
