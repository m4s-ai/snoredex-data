"""Apply the bounded 2026-09-01 official Pokémon Korea Snorlax catalogue pass."""

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
import admit_issue260_korean_research_20260831 as research  # noqa: E402


EVIDENCE = ROOT / "verification" / "evidence" / "pokemon-korea-snorlax-catalogue-20260901.json"
PRINTS = ROOT / "verification" / "source_first_prints.json"
REKEYS = ROOT / "verification" / "legacy_issue_rekeys.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
CAPABILITIES = ROOT / "verification" / "source_capabilities.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
UNITS = ROOT / "verification" / "units.json"
ADAPTERS = ROOT / "verification" / "card_discovery_adapters.json"
ASIA_MATRIX = ROOT / "verification" / "asia_locality_matrix.json"
FINISH_SNAPSHOT = ROOT / "verification" / "finish_tcgdex_snapshot.json"
SNAPSHOT = "verification/evidence/pokemon-korea-snorlax-catalogue-20260901.json"
REVIEWED_AT = "2026-09-01"


ALIASES = {
    "KR:FXY:026/036:base": [("HXY", "026")],
    "KR:SM-P:017/SM-P:base": [("SM-P", "1")],
    "KR:SM-P:140:base": [("SM-P", "297")],
    "KR:XY-P:167:base": [("XY-P", "149")],
    "KR:sI:341/414:base": [("sI100", "341")],
    "KR:sI:342/414:base": [("sI100", "342")],
    "KR:sv4K:060/066:base": [("sv4K", "059")],
    "KR:svI:046/066:base": [("svIba", "046")],
}

U0523_ORIGINAL_EVIDENCE = (
    "Validated absence. A collector-database search for S-P Snorlax promos returns "
    "printings in six languages - S-P 061 (Simplified Chinese), S-P 101 (Korean), "
    "S-P 145 (Chinese), S-P 052 / S-P 100 / S-P 356 (Indonesian) - so the source "
    "demonstrably covers Korean and Chinese S-P Snorlax promos. For S-P 156 it lists "
    "only \"Snorlax (156/S-P Japanese Promo)\", distributed as a CoroCoro Ichiban! "
    "March 2021 issue insert. The absence of a Korean or Traditional Chinese 156 is "
    "therefore evidence, not a coverage gap. Note S-P 101 is a different card and "
    "does not cover 156. Search: https://pokumon.com/?s=snorlax+s-p"
)


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def official_url(record_id: str) -> str:
    return f"https://pokemoncard.co.kr/cards/detail/{record_id}"


def independent_url(url: str) -> bool:
    return not (
        url.startswith("https://pokemoncard.co.kr/")
        or url.startswith("https://cards.image.pokemonkorea.co.kr/")
    )


def new_rows() -> list[dict[str, Any]]:
    fxy = research.research(
        "U0586", "FXY", "026/036", ("fixed product", "fixed"),
        official_url("ST2014001026"), "pokemon-card-korea",
        corroborating=["https://bulbapedia.bulbagarden.net/wiki/Kalos_Starter_Set_(TCG)"],
        legacy_aliases=ALIASES["KR:FXY:026/036:base"],
    )
    fxy["retrievedAt"] = REVIEWED_AT
    sm30a = {
        "printId": "KR:SM30A:060/080:base",
        "localSetCode": "SM30A",
        "localNumber": "060/080",
        "work": "Snorlax-Incredible-Snore",
        "legacy": [],
        "rarity": ("B", None),
        "specimenId": None,
        "cardName": "Snorlax",
        "providerId": "pokemon-card-korea",
        "providerRecordId": "BS2019018060",
        "retrievedAt": REVIEWED_AT,
        "sourceUrl": official_url("BS2019018060"),
        "cardImageUrl": "https://cards.image.pokemonkorea.co.kr/data/wmimages/SM/SM30A/SM30A_060.png?w=512",
        "corroborated": False,
        "corroboratingSourceUrls": [],
        "legacyVariants": [],
        "legacyIdentityAliases": [],
    }
    return [fxy, sm30a]


def apply_official_rows(
    rows: list[dict[str, Any]], identities: dict[str, dict[str, Any]]
) -> None:
    for row in rows:
        identity = identities.get(row["printId"])
        if identity is None:
            continue
        record_ids = identity["providerRecordIds"]
        source_url = official_url(record_ids[0])
        # The official detail becomes the identity source, but it does not
        # restate every source-native rarity captured by earlier research.
        # Keep that field's evidence attached to the record that supplied it.
        row.setdefault("raritySourceUrl", row.get("sourceUrl"))
        row.setdefault("rarityProviderId", row.get("providerId"))
        row.setdefault("rarityRetrievedAt", row.get("retrievedAt"))
        prior_urls = {
            *(row.get("corroboratingSourceUrls") or []),
            *([row["sourceUrl"]] if row.get("sourceUrl") else []),
        }
        row.update({
            "providerId": "pokemon-card-korea",
            "providerRecordId": record_ids[0],
            "providerRecordIds": record_ids,
            "retrievedAt": REVIEWED_AT,
            "sourceUrl": source_url,
            "cardImageUrl": identity["imageUrls"][0],
            "alternateCardImageUrls": identity["imageUrls"][1:],
            "evidenceSnapshot": SNAPSHOT,
            "illustrator": identity["illustrator"],
            "hp": identity["hp"],
            "localProductName": identity["product"],
            "catalogueCollectorNumber": identity["collectorNumber"],
        })
        row["corroboratingSourceUrls"] = sorted(
            url for url in prior_urls - {source_url} if independent_url(url)
        )
        row["corroborated"] = bool(row["corroboratingSourceUrls"])
        row["legacyIdentityAliases"] = sorted({
            *(tuple(item) for item in row.get("legacyIdentityAliases") or []),
            *ALIASES.get(row["printId"], []),
        })


def apply_prints(
    document: dict[str, Any], rows: list[dict[str, Any]], identities: dict[str, dict[str, Any]]
) -> None:
    by_print = {row["printId"]: row for row in document["prints"]}
    by_print.update({row["printId"]: research.source_first_row(row) for row in rows})
    for print_id, identity in identities.items():
        row = by_print[print_id]
        source_url = official_url(identity["providerRecordIds"][0])
        prior_urls = {
            *(row.get("corroboratingSourceUrls") or []),
            *([row["sourceUrl"]] if row.get("sourceUrl") else []),
        }
        row.update({
            "name": identity["name"],
            "providerId": "pokemon-card-korea",
            "providerRecordId": identity["providerRecordIds"][0],
            "providerRecordIds": identity["providerRecordIds"],
            "retrievedAt": REVIEWED_AT,
            "sourceUrl": source_url,
            "cardImageUrl": identity["imageUrls"][0],
            "alternateCardImageUrls": identity["imageUrls"][1:],
            "evidenceSnapshot": SNAPSHOT,
            "catalogueCollectorNumber": identity["collectorNumber"],
            "illustrator": identity["illustrator"],
            "hp": identity["hp"],
            "localProductName": identity["product"],
            "corroboratingSourceUrls": sorted(
                url for url in prior_urls - {source_url} if independent_url(url)
            ),
            "evidence": (
                f"The retained official Pokémon Korea exact-name catalogue detail identifies "
                f"{identity['name']} {identity['localSetCode']} {identity['collectorNumber']} in "
                f"{identity['product']}, with illustrator {identity['illustrator']}"
                f"{(' and ' + identity['hp']) if identity['hp'] else ''}. The page establishes "
                "this Korean card release and its local identity. Alternate publisher renders "
                "remain identity evidence only; no physical finish or catalogue absence is inferred."
            ),
        })
        row["corroborated"] = bool(row["corroboratingSourceUrls"])
    document["prints"] = sorted(by_print.values(), key=lambda row: row["printId"])
    document["meta"]["generated"] = REVIEWED_AT
    document["meta"]["counts"]["admitted"] = len(document["prints"])


def apply_units(
    document: list[dict[str, Any]], rows: list[dict[str, Any]], identities: dict[str, dict[str, Any]]
) -> None:
    by_id = {row["unitId"]: row for row in document}
    # S-P 101 is a separate Korean counterpart, not evidence for the contradicted
    # S-P 156 claim that happens to share this legacy Work mapping.
    by_id["U0523"].update({
        "artist": None,
        "sourceUrl": "https://pokumon.com/?s=snorlax+s-p",
        "sourceType": "pokumon.com (collector card database), promo search",
        "providerId": "pokumon",
        "sourceRef": None,
        "corroborated": False,
        "evidence": U0523_ORIGINAL_EVIDENCE,
        "checkedAt": "2026-07-22T16:34:50",
    })
    for row in rows:
        identity = identities.get(row["printId"])
        if identity is None:
            continue
        source_url = official_url(identity["providerRecordIds"][0])
        for unit_id in row["legacy"]:
            unit = by_id[unit_id]
            if unit.get("status") != "confirmed":
                continue
            marker = " OFFICIAL KOREAN CATALOGUE 2026-09-01:"
            evidence = unit.get("evidence", "").split(marker, 1)[0].rstrip()
            unit.update({
                "sourceUrl": source_url,
                "sourceType": "Pokémon Korea official card catalogue detail",
                "providerId": "pokemon-card-korea",
                "sourceRef": None,
                "artist": identity["illustrator"],
                "corroborated": bool(row["corroborated"]),
                "checkedAt": REVIEWED_AT,
                "evidence": (
                    evidence + marker + f" {source_url} positively identifies {identity['name']} "
                    f"{identity['collectorNumber']} in {identity['product']} and credits "
                    f"{identity['illustrator']}. This supports identity and Work mapping only; "
                    "no finish or absence is inferred."
                ),
            })


def apply_capabilities(document: dict[str, Any], evidence: dict[str, Any]) -> None:
    base.apply_capabilities(document)
    document["meta"]["reviewedAt"] = REVIEWED_AT
    historical = next(
        row for row in document["surfaces"]
        if row["surfaceId"] == "pokemon-card-korea-historical-detail"
    )
    historical.update({
        "failureState": "Reachability is region/session dependent: these detail routes returned HTTP 200 with the user-provided VPN active on 2026-09-01; the earlier HTTP 410 observation remains an access-route result, never absence evidence.",
        "lastCheckedAt": REVIEWED_AT,
        "freshnessPolicy": "Retain exact publisher fields and re-check region/session reachability before refresh; neither HTTP 410 nor an unavailable route is absence evidence.",
    })
    retailer = next(
        row for row in document["surfaces"]
        if row["surfaceId"] == "retailer-listings"
    )
    retailer_edge = retailer["coverageEdges"][0]
    for value in ("KR",):
        if value not in retailer_edge["coverage"]["localities"]:
            retailer_edge["coverage"]["localities"].append(value)
    for value in ("Hang",):
        if value not in retailer_edge["coverage"]["scripts"]:
            retailer_edge["coverage"]["scripts"].append(value)
    if "identity" not in retailer_edge["positiveEvidenceCapabilities"]:
        retailer_edge["positiveEvidenceCapabilities"].append("identity")
    surface = {
        "surfaceId": "pokemon-card-korea-card-search",
        "providerId": "pokemon-card-korea",
        "label": "Pokémon Korea bounded exact Korean card-name catalogue",
        "match": {
            "urlPrefixes": ["https://pokemoncard.co.kr/cards"],
            "nonUrlEvidenceIds": [SNAPSHOT],
        },
        "state": "incomplete",
        "failureState": "The search POST requires a primed browser session and region-dependent access; only the retained bounded positive response is replayable.",
        "accessMode": "browser",
        "adapterState": "active",
        "lastCheckedAt": REVIEWED_AT,
        "freshnessPolicy": "Rerun the exact 잠만보 card-name query through a primed browser session, retain every returned endpoint and detail, and treat missing or failed responses as unknown.",
        "query": {
            "method": "POST",
            "endpoint": "https://pokemoncard.co.kr/v2/ajax2_dev2",
            "parameters": ["search_params=cardname", "search_text=잠만보", "browser session from GET /cards"],
            "pagination": "30, 17 and 0 endpoint records were observed in consecutive batches; 47 endpoints normalized to 45 unique displayed set/number identities",
            "expectedIdentifiers": ["opaque provider record id", "Korean card name", "printed collector number", "product membership", "illustrator", "publisher render"],
        },
        "finishCapability": {
            "mode": "none", "vocabulary": [],
            "publicationForm": "publisher catalogue detail and render, not a physical card photograph",
            "closedWithinScope": False,
        },
        "coverageEdges": [{
            "edgeId": "pokemon-card-korea-card-search-positive",
            "coverage": {
                "localities": ["KR"], "languages": ["Korean"], "scripts": ["Hang"],
                "productCategories": ["card"],
                "timeRange": {"start": None, "end": None, "basis": "the retained 2026-09-01 exact 잠만보 response only"},
            },
            "positiveEvidenceCapabilities": ["identity", "image", "language", "card-existence", "card-release", "local-set-identifier", "collector-number", "rarity", "set-membership", "product-membership", "illustrator"],
            "exhaustive": False,
            "absenceCapability": {"enabled": False, "dimensions": [], "exactScopes": [], "rationale": "The response is a positive exact-name frontier; omissions, route failures and zero results are unknown."},
            "knownPositiveObservationId": "obs-pokemon-card-korea-snorlax-search-20260901",
            "boundary": {
                "outsideScope": ["other Korean names", "provider-wide historical completeness", "physical finish", "unreturned products"],
                "zeroResultMeans": "unknown",
                "challenge": "Region/session dependence and alternate positive routes prevent any missing result from supporting absence.",
            },
        }],
    }
    observation = {
        "observationId": "obs-pokemon-card-korea-snorlax-search-20260901",
        "surfaceId": surface["surfaceId"], "kind": "known-positive",
        "queryUrl": surface["query"]["endpoint"],
        "queryParameters": evidence["query"]["parameters"], "retrievedAt": REVIEWED_AT,
        "fixtureRef": {"kind": "inline-record", "record": {
            "evidenceSnapshot": SNAPSHOT, "endpointRecordCount": 47,
            "uniqueIdentityCount": 45, "newPositivePrintIds": [
                "KR:FXY:026/036:base", "KR:SM30A:060/080:base"
            ], "absenceCapability": False, "finishCapability": False,
        }},
        "expectedIdentifiers": ["잠만보", "47 endpoint records", "45 unique identities", "FXY 026/036", "SM30A 060/080"],
        "validatesEdges": ["pokemon-card-korea-card-search-positive"],
        "outcome": "The bounded exact-name response retained 47 official endpoint records representing 45 unique Korean identities, including FXY 026/036 and SM30A 060/080; no absence or finish conclusion is attached.",
    }
    surfaces = {row["surfaceId"]: row for row in document["surfaces"]}
    surfaces[surface["surfaceId"]] = surface
    document["surfaces"] = list(surfaces.values())
    observations = {row["observationId"]: row for row in document["observations"]}
    observations[observation["observationId"]] = observation
    document["observations"] = list(observations.values())


def apply_discovery_contract(document: dict[str, Any], print_ids: list[str]) -> None:
    document["meta"].update({"coverageVersion": "1.19.0", "reviewedAt": REVIEWED_AT})
    adapter = {
        "adapterId": "pokemon-korea-reviewed-name-search",
        "adapterVersion": "1.0.0", "responseFormat": "source-first-print-json",
        "providerId": "pokemon-card-korea", "surfaceId": "pokemon-card-korea-card-search",
        "state": "active", "listEndpointTemplate": "https://pokemoncard.co.kr/cards",
        "detailEndpointTemplate": "https://pokemoncard.co.kr/cards/detail/{rawProviderId}",
        "category": "card", "sourceFirst": True,
        "pageParameter": "retained-print-id", "pageSize": len(print_ids),
        "slices": [{
            "sliceId": "pokemon-korea-snorlax-positive",
            "coverageEdgeId": "pokemon-card-korea-card-search-positive",
            "rawLocale": "ko", "locality": "KR", "language": "Korean", "script": "Hang",
            "nameQueries": ["잠만보"], "retainedPrintIds": print_ids,
            "positiveNameExclusions": [],
        }],
    }
    adapters = {row["adapterId"]: row for row in document["adapters"]}
    adapters[adapter["adapterId"]] = adapter
    document["adapters"] = list(adapters.values())
    gaps = []
    for gap in document["gaps"]:
        if gap["gapId"] == "official-asia-kr-cn":
            gap = {
                "gapId": "official-asia-cn",
                "track": "Simplified-Chinese card discovery",
                "providerId": "pokemon-card-asia", "surfaceId": "asia-card-search",
                "terminalState": "blocked-by-source",
                "reason": "The official Asia card-search capability does not cover mainland China.",
                "retryCondition": "Activate only after a provider-native official or bounded specialist Simplified-Chinese surface is registered in the capability graph.",
            }
        gaps.append(gap)
    document["gaps"] = gaps
    korean_gap = {
        "gapId": "official-korean-historical-positive-frontier",
        "track": "Korean historical card discovery beyond the retained exact-name slice",
        "providerId": "pokemon-card-korea",
        "surfaceId": "pokemon-card-korea-card-search",
        "terminalState": "needs-evidence",
        "reason": "The retained official Korean 잠만보 response accounts for 45 positive identities within that bounded response, while additional independently retained Korean releases and the region-dependent route prevent any provider-wide historical-completeness claim.",
        "retryCondition": "Rerun the exact Korean name slice for positive deltas and retain any alternate positive routes; missing rows, failed routes and zero results remain unknown.",
    }
    by_gap = {row["gapId"]: row for row in document["gaps"]}
    by_gap[korean_gap["gapId"]] = korean_gap
    document["gaps"] = list(by_gap.values())


def apply_asia_matrix(document: dict[str, Any]) -> None:
    document["meta"]["reviewedAt"] = REVIEWED_AT
    for track in document["tracks"]:
        if track["trackId"] == "asia-cn":
            track["gapIds"] = ["official-asia-cn"]
        elif track["trackId"] == "asia-kr":
            track.update({
                "terminalState": "complete",
                "scope": "The bounded official Korean 잠만보 exact-name slice and all 45 retained positive local identities.",
                "cardSliceIds": ["pokemon-korea-snorlax-positive"],
                "gapIds": ["official-korean-historical-positive-frontier"],
                "evidenceRefs": ["source-first:KR:FXY:026/036:base", "source-first:KR:SM30A:060/080:base"],
                "retryCondition": "Rerun the exact Korean name slice for deltas; preserve new positives as candidates and never treat a missing row as absence.",
            })


def add_graph_corroboration(graph: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    by_id = {
        row["entityId"]: row for row in graph["entities"]
        if row.get("entityType") == "card-release"
    }
    for row in rows:
        release = by_id.get(base.release_id(row))
        if release is None:
            continue
        urls = {
            *release["payload"].get("sourceRecords", []), row["sourceUrl"],
            *(row.get("corroboratingSourceUrls") or []),
        }
        release["payload"]["sourceRecords"] = sorted(urls)


def normalize_graph_semantics(graph: dict[str, Any]) -> None:
    sm30a_release_id = "RELEASE:KR:Korean:SM30A:060/080:Snorlax-Incredible-Snore"
    for entity in graph["entities"]:
        payload = entity.get("payload", {})
        if entity.get("entityType") == "card-release" \
                and entity.get("entityId") == sm30a_release_id:
            # This new source-native release needs no legacy equivalence assertion:
            # the retained official detail carries the matching attack directly.
            payload["workMappingState"] = "mapped"
        elif entity.get("entityType") == "rarity-claim" \
                and payload.get("sourceVocabulary") == "printed-Korean-card" \
                and payload.get("sourceNativeValue") in {"HR", "UR"}:
            # rarity_catalogue.json deliberately leaves historical Korean HR and
            # unqualified UR unmapped because their meaning varies by era.
            payload["normalizedRarityId"] = None
    for edge in graph["edges"]:
        if edge.get("fromType") == "card-release" \
                and edge.get("fromId") == sm30a_release_id \
                and edge.get("relation") == "implements":
            edge["provenance"] = {
                "state": "mapped",
                "basis": "the official Korean detail carries 굉장한코골기 100",
            }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    evidence = read(EVIDENCE)
    identities = {row["printId"]: row for row in evidence["identities"]}
    if len(identities) != 45 or sum(len(row["providerRecordIds"]) for row in identities.values()) != 47:
        raise SystemExit("Pokémon Korea snapshot must retain 45 identities / 47 endpoints")

    rows = base.OFFICIAL + base.PROMOS + research.RESEARCH_ROWS + new_rows()
    for row in rows:
        row.setdefault("legacyVariants", sorted({
            str(research.UNITS_BY_ID[item].get("variant") or "base") for item in row["legacy"]
        }))
    apply_official_rows(rows, identities)

    documents = {
        "prints": read(PRINTS), "sources": read(SET_SOURCES),
        "capabilities": read(CAPABILITIES), "rekeys": read(REKEYS),
        "graph": read(GRAPH), "units": read(UNITS),
        "adapters": read(ADAPTERS), "asia matrix": read(ASIA_MATRIX),
        "finish snapshot": read(FINISH_SNAPSHOT),
    }
    before = {label: base.encoded(value) for label, value in documents.items()}

    apply_prints(documents["prints"], rows, identities)
    profiles = base.apply_profiles(documents["sources"], rows, retrieved_at=REVIEWED_AT)
    apply_capabilities(documents["capabilities"], evidence)
    apply_units(documents["units"], rows, identities)
    if not args.check:
        # project_physical_evidence reads units.json to refresh legacy claim sources.
        base.write(UNITS, documents["units"])
    apply_discovery_contract(documents["adapters"], sorted(identities))
    apply_asia_matrix(documents["asia matrix"])
    documents["finish snapshot"]["records"].pop(
        "https://api.tcgdex.net/v2/ko/cards/SV4K-059", None
    )
    documents["finish snapshot"]["generated"] = REVIEWED_AT
    research.ensure_researched_works(documents["graph"], rows)
    # The first projection rekeys legacy finish links; the second stabilizes their semantic IDs.
    for _ in range(2):
        documents["graph"], mappings = base.apply_graph(
            documents["graph"], profiles, rows, asserted_at=REVIEWED_AT
        )
    normalize_graph_semantics(documents["graph"])
    add_graph_corroboration(documents["graph"], rows)
    legacy_ids = sorted(set(base.ISSUE_UNITS) | {"U0586"})
    question = {
        "issueNumber": 260, "locality": "KR", "language": "Korean",
        "legacyUnitIds": legacy_ids, "defaultDisposition": "needs-positive-local-identity",
        "mappings": mappings,
    }
    by_issue = {row["issueNumber"]: row for row in documents["rekeys"]["questionSets"]}
    by_issue[260] = question
    documents["rekeys"]["questionSets"] = sorted(by_issue.values(), key=lambda row: row["issueNumber"])

    stale = [
        label for label, value in documents.items()
        if before[label] != base.encoded(value)
    ]
    if args.check:
        if stale:
            raise SystemExit("Pokémon Korea catalogue inputs are stale: " + ", ".join(stale))
        print("Pokémon Korea catalogue inputs are current: 47 endpoints / 45 identities")
        return 0

    for label, path in (
        ("prints", PRINTS), ("sources", SET_SOURCES), ("capabilities", CAPABILITIES),
        ("rekeys", REKEYS), ("graph", GRAPH), ("units", UNITS),
        ("adapters", ADAPTERS), ("asia matrix", ASIA_MATRIX),
        ("finish snapshot", FINISH_SNAPSHOT),
    ):
        base.write(path, documents[label])
    print("applied official Pokémon Korea catalogue: 47 endpoints, 45 identities, 2 additions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
