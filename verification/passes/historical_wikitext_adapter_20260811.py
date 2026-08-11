#!/usr/bin/env python3
"""Activate the revision-pinned Dutch, Polish and Russian historical adapter (#193)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "verification"
REVISION = 4567865
PAGE_TITLE = "List of Pokémon Trading Card Game expansions in other languages"
API_URL = (
    "https://bulbapedia.bulbagarden.net/w/api.php?action=parse&oldid=4567865"
    "&prop=wikitext&format=json&formatversion=2"
)


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def replace_by_id(rows: list[dict[str, Any]], key: str, row: dict[str, Any]) -> None:
    rows[:] = [item for item in rows if item[key] != row[key]]
    rows.append(row)


def update_capabilities() -> None:
    path = VERIFY / "source_capabilities.json"
    document = read(path)
    surface = next(
        row for row in document["surfaces"]
        if row["surfaceId"] == "bulbapedia-mediawiki"
    )
    surface.update({
        "state": "active",
        "failureState": None,
        "accessMode": "scriptable",
        "adapterState": "active",
        "lastCheckedAt": "2026-08-11",
        "freshnessPolicy": (
            "Retain page title, exact revision id and wikitext section; a newer revision is a "
            "new comparison run, never an in-place replacement."
        ),
    })
    surface["query"] = {
        "method": "GET",
        "endpoint": "https://bulbapedia.bulbagarden.net/w/api.php",
        "parameters": [
            "action=parse", "prop=wikitext", "redirects=1", "oldid",
            "format=json", "formatversion=2",
        ],
        "pagination": (
            "The pinned parse response is one page; list modules still require continuation."
        ),
        "expectedIdentifiers": [
            "page title", "revision id", "section", "source-native table cells",
        ],
    }
    edge = {
        "edgeId": "bulbapedia-historical-index-positive",
        "coverage": {
            "localities": ["WEST"],
            "languages": ["Dutch", "Polish", "Russian"],
            "scripts": ["Latn", "Cyrl"],
            "productCategories": ["set"],
            "timeRange": {
                "start": "Original Series",
                "end": "XY Series",
                "basis": "positive cells in revision 4567865 only",
            },
        },
        "positiveEvidenceCapabilities": ["language", "edition", "set-existence"],
        "exhaustive": False,
        "absenceCapability": {
            "enabled": False,
            "dimensions": [],
            "exactScopes": [],
            "rationale": (
                "Only non-dash cells are positive evidence; dashes, omitted columns and "
                "non-expansion products remain unknown."
            ),
        },
        "knownPositiveObservationId": "obs-bulbapedia-historical-index",
        "boundary": {
            "outsideScope": [
                "promos and decks not enumerated by the English-set tables",
                "blank or dash cells",
                "cards not already reached by their own positive card-list or unit evidence",
                "newer page revisions",
            ],
            "zeroResultMeans": "unknown",
            "challenge": (
                "Kalos Starter Set is explicitly a partial theme-deck release, and the Russian "
                "FLF promotional variant is not independently enumerated by this set index."
            ),
        },
    }
    replace_by_id(surface["coverageEdges"], "edgeId", edge)
    observation = {
        "observationId": "obs-bulbapedia-historical-index",
        "surfaceId": "bulbapedia-mediawiki",
        "kind": "known-positive",
        "queryUrl": API_URL,
        "queryParameters": {
            "action": "parse", "prop": "wikitext", "oldid": REVISION,
            "format": "json", "formatversion": 2,
        },
        "retrievedAt": "2026-08-11",
        "fixtureRef": {
            "kind": "inline-record",
            "record": {
                "pageTitle": PAGE_TITLE,
                "revisionId": REVISION,
                "section": "English sets",
                "positiveRows": {"Dutch": 3, "Polish": 2, "Russian": 9},
                "absenceCapability": False,
            },
        },
        "expectedIdentifiers": [
            "revisionId=4567865", "Dutch=3", "Polish=2", "Russian=9",
        ],
        "validatesEdges": ["bulbapedia-historical-index-positive"],
        "outcome": (
            "The retained revision exposes three Dutch, two Polish and nine Russian positive "
            "physical-set cells; every one is staged without interpreting dashes as absence."
        ),
    }
    replace_by_id(document["observations"], "observationId", observation)
    write(path, document)


def update_source_adapter() -> None:
    path = VERIFY / "source_adapters.json"
    document = read(path)
    old_run_snapshot = (
        VERIFY / "runs" / "source-adapters" / "20260809T155355Z" / "contract.json"
    )
    if not old_run_snapshot.exists():
        write(old_run_snapshot, document)
    document["meta"]["coverageVersion"] = "1.1.0"
    document["meta"]["reviewedAt"] = "2026-08-11"
    source_policy = (
        "Revision-pinned historical indexes may enumerate every positive language cell in "
        "their bounded table section; dash cells and unlisted product categories remain unknown."
    )
    if source_policy not in document["meta"]["policies"]:
        document["meta"]["policies"].append(source_policy)
    adapter = {
        "adapterId": "bulbapedia-historical-language-index",
        "adapterVersion": "1.0.0",
        "responseFormat": "bulbapedia-historical-wikitext",
        "providerId": "bulbapedia",
        "surfaceId": "bulbapedia-mediawiki",
        "state": "active",
        "endpointTemplate": API_URL,
        "pageTitle": PAGE_TITLE,
        "revisionId": REVISION,
        "category": "set",
        "sourceFirst": True,
        "slices": [
            {
                "sliceId": "bulbapedia-historical-nl-sets",
                "coverageEdgeId": "bulbapedia-historical-index-positive",
                "rawLocale": "nl", "locality": "WEST",
                "language": "Dutch", "script": "Latn",
            },
            {
                "sliceId": "bulbapedia-historical-pl-sets",
                "coverageEdgeId": "bulbapedia-historical-index-positive",
                "rawLocale": "pl", "locality": "WEST",
                "language": "Polish", "script": "Latn",
            },
            {
                "sliceId": "bulbapedia-historical-ru-sets",
                "coverageEdgeId": "bulbapedia-historical-index-positive",
                "rawLocale": "ru", "locality": "WEST",
                "language": "Russian", "script": "Cyrl",
            },
        ],
    }
    replace_by_id(document["adapters"], "adapterId", adapter)
    mappings = [
        ("nl", "Jungle", "EDITION:WEST:Dutch:JU"),
        ("pl", "Diamond & Pearl", "EDITION:WEST:Polish:DP"),
        ("ru", "Kalos Starter Set", "EDITION:WEST:Russian:KSS"),
        ("ru", "Flashfire", "EDITION:WEST:Russian:FLF"),
        ("ru", "BREAKthrough", "EDITION:WEST:Russian:BKT"),
    ]
    document["explicitMappings"] = [
        row for row in document["explicitMappings"]
        if row["providerId"] != "bulbapedia"
    ] + [{
        "providerId": "bulbapedia",
        "surfaceId": "bulbapedia-mediawiki",
        "rawLocale": locale,
        "rawProviderId": source_id,
        "targetType": "set-edition",
        "targetId": target,
        "evidence": (
            "Revision 4567865 positively names this physical language edition; the existing "
            "set-edition target preserves the local Snorlax identity without merging languages."
        ),
    } for locale, source_id, target in mappings]
    document["gaps"] = [
        row for row in document["gaps"]
        if row["gapId"] not in {
            "bulbapedia-wikitext-catalogue",
            "bulbapedia-non-expansion-catalogue",
        }
    ]
    document["gaps"].append({
        "gapId": "bulbapedia-non-expansion-catalogue",
        "track": "historical promos, decks and other non-expansion products",
        "providerId": "bulbapedia",
        "surfaceId": "bulbapedia-mediawiki",
        "terminalState": "needs-evidence",
        "reason": (
            "The activated revision is a bounded English-set language table; it does not "
            "enumerate promo series, deck-only cards or every historical product."
        ),
        "retryCondition": (
            "Add separately revision-pinned product-category indexes and account every row; "
            "never extend expansion coverage to promos or decks."
        ),
    })
    write(path, document)


def update_card_adapter() -> None:
    path = VERIFY / "card_discovery_adapters.json"
    document = read(path)
    document["meta"]["coverageVersion"] = "1.6.0"
    document["meta"]["reviewedAt"] = "2026-08-11"
    card_policy = (
        "A revision-pinned historical card frontier may replay exact confirmed units only "
        "after its shared empty-start set adapter accounts every positive language row; "
        "the replay cannot create or change a verdict."
    )
    if card_policy not in document["meta"]["policies"]:
        document["meta"]["policies"].append(card_policy)
    adapter = {
        "adapterId": "bulbapedia-historical-card-frontiers",
        "adapterVersion": "1.0.0",
        "responseFormat": "bulbapedia-historical-json",
        "providerId": "bulbapedia",
        "surfaceId": "bulbapedia-mediawiki",
        "state": "active",
        "listEndpointTemplate": API_URL,
        "detailEndpointTemplate": (
            "https://bulbapedia.bulbagarden.net/w/index.php?title="
            "List_of_Pok%C3%A9mon_Trading_Card_Game_expansions_in_other_languages"
            "&oldid=4567865#{rawProviderId}"
        ),
        "pageTitle": PAGE_TITLE,
        "revisionId": REVISION,
        "category": "card",
        "sourceFirst": True,
        "pageParameter": "oldid",
        "pageSize": 14,
        "slices": [
            {
                "sliceId": "bulbapedia-historical-nl-snorlax",
                "coverageEdgeId": "bulbapedia-historical-index-positive",
                "rawLocale": "nl", "locality": "WEST",
                "language": "Dutch", "script": "Latn",
                "nameQueries": ["Snorlax"],
                "retainedUnitIds": ["U0095", "U0125"],
                "retainedSetNames": {"U0095": "Jungle", "U0125": "Jungle"},
                "positiveNameExclusions": [],
            },
            {
                "sliceId": "bulbapedia-historical-pl-snorlax",
                "coverageEdgeId": "bulbapedia-historical-index-positive",
                "rawLocale": "pl", "locality": "WEST",
                "language": "Polish", "script": "Latn",
                "nameQueries": ["Snorlax"],
                "retainedUnitIds": ["U0364"],
                "retainedSetNames": {"U0364": "Diamond & Pearl"},
                "positiveNameExclusions": [],
            },
            {
                "sliceId": "bulbapedia-historical-ru-snorlax",
                "coverageEdgeId": "bulbapedia-historical-index-positive",
                "rawLocale": "ru", "locality": "WEST",
                "language": "Russian", "script": "Cyrl",
                "nameQueries": ["Snorlax"],
                "retainedUnitIds": ["U0212", "U0336", "U0487", "U0621"],
                "retainedSetNames": {
                    "U0212": "BREAKthrough", "U0336": "Flashfire",
                    "U0487": "Kalos Starter Set", "U0621": "Flashfire",
                },
                "positiveNameExclusions": [],
            },
        ],
    }
    replace_by_id(document["adapters"], "adapterId", adapter)
    targets = {
        "U0095": "RELEASE:WEST:Dutch:JU:27:Snorlax-Thick-Skinned-Body-Slam",
        "U0125": "RELEASE:WEST:Dutch:JU:11:Snorlax-Thick-Skinned-Body-Slam",
        "U0212": "RELEASE:WEST:Russian:BKT:118:Snorlax-Plump-Body-Knock-Away",
        "U0336": "RELEASE:WEST:Russian:FLF:80:Snorlax-Stir-and-Snooze-Sleepy-Press",
        "U0364": "RELEASE:WEST:Polish:DP:37:Snorlax-Lv35-Block-Ease-Up",
        "U0487": "RELEASE:WEST:Russian:KSS:26:Snorlax-Rock-Smash-Strength",
        "U0621": "RELEASE:WEST:Russian:FLF:80:Snorlax-Stir-and-Snooze-Sleepy-Press",
    }
    unit_locale = {
        "U0095": "nl", "U0125": "nl", "U0364": "pl",
        "U0212": "ru", "U0336": "ru", "U0487": "ru", "U0621": "ru",
    }
    document["explicitMappings"] = [
        row for row in document["explicitMappings"]
        if row["providerId"] != "bulbapedia"
    ] + [{
        "providerId": "bulbapedia",
        "surfaceId": "bulbapedia-mediawiki",
        "rawLocale": unit_locale[unit_id],
        "rawProviderId": unit_id,
        "mode": "exact-match",
        "targetCardReleaseId": target,
        "evidence": (
            "The pinned language-index row and retained positive unit preserve this exact "
            "local set, collector number and variant without creating a new verdict."
        ),
    } for unit_id, target in targets.items()]
    document["gaps"] = [
        row for row in document["gaps"]
        if row["gapId"] not in {
            "specialist-historical-card-discovery",
            "historical-non-expansion-card-discovery",
        }
    ]
    document["gaps"].append({
        "gapId": "historical-non-expansion-card-discovery",
        "track": (
            "specialist historical promos, decks and category-specific card discovery"
        ),
        "providerId": "bulbapedia",
        "surfaceId": "bulbapedia-mediawiki",
        "terminalState": "needs-evidence",
        "reason": (
            "The shared index positively scopes expansion language rows. KSS deck identity and "
            "the Russian FLF V2 legacy promo survive replay, but the index does not enumerate "
            "all decks or promo printings."
        ),
        "retryCondition": (
            "Activate category-specific revision-pinned lists or positive specimens; do not "
            "inherit expansion coverage into promos and decks."
        ),
    })
    write(path, document)


def update_matrix() -> None:
    path = VERIFY / "locality_era_matrix.json"
    document = read(path)
    tracks = {row["trackId"]: row for row in document["tracks"]}
    definitions = {
        "west-nl": {
            "basis": (
                "Revision 4567865 accounts for three positive Dutch expansion rows (Base Set, "
                "Jungle, Fossil); the card frontier matches both Jungle Snorlax numbers."
            ),
            "source": "bulbapedia-historical-nl-sets",
            "card": "bulbapedia-historical-nl-snorlax",
            "units": ["unit:U0095", "unit:U0125"],
            "open": "Which Dutch promos, decks and products sit outside the three indexed expansions?",
        },
        "west-pl": {
            "basis": (
                "Revision 4567865 accounts for two positive Polish expansion rows (Diamond & "
                "Pearl, Mysterious Treasures); the card frontier matches DP 37."
            ),
            "source": "bulbapedia-historical-pl-sets",
            "card": "bulbapedia-historical-pl-snorlax",
            "units": ["unit:U0364"],
            "open": "Which Polish promos, decks and products sit outside the two indexed expansions?",
        },
        "west-ru": {
            "basis": (
                "Revision 4567865 accounts for nine positive Russian rows from Kalos Starter "
                "Set/XY through BREAKthrough; the card frontier preserves KSS 26, FLF 80 V1/V2 "
                "and BKT 118. The later dash cells are not absence evidence."
            ),
            "source": "bulbapedia-historical-ru-sets",
            "card": "bulbapedia-historical-ru-snorlax",
            "units": ["unit:U0212", "unit:U0336", "unit:U0487", "unit:U0621"],
            "open": "Which Russian promos and decks lie outside the nine indexed set rows?",
        },
    }
    for track_id, definition in definitions.items():
        track = tracks[track_id]
        refs = [
            f"slice:{definition['source']}",
            f"card-slice:{definition['card']}",
            "edge:bulbapedia-historical-index-positive",
            "observation:obs-bulbapedia-historical-index",
            *definition["units"],
        ]
        track["eraSegments"] = [
            {
                "eraId": "revision-4567865-positive-frontier",
                "start": None,
                "end": None,
                "state": "positive-observations-only",
                "basis": definition["basis"],
                "evidenceRefs": refs,
                "absenceAllowed": False,
            },
            {
                "eraId": "non-expansion-and-unlisted-history",
                "start": None,
                "end": None,
                "state": "needs-evidence",
                "basis": (
                    "The pinned expansion table does not enumerate historical promos, decks or "
                    "other product categories, and its dash cells remain unknown."
                ),
                "evidenceRefs": [
                    "source-gap:bulbapedia-non-expansion-catalogue",
                    "card-gap:historical-non-expansion-card-discovery",
                ],
                "absenceAllowed": False,
            },
        ]
        track["discovery"] = {
            "state": "complete-positive-slice",
            "sourceRefs": refs,
            "gapRefs": [
                "source-gap:bulbapedia-non-expansion-catalogue",
                "card-gap:historical-non-expansion-card-discovery",
            ],
            "retryCondition": (
                "Rerun only as a new pinned revision comparison; add promos and decks through "
                "their own bounded category sources."
            ),
        }
        track["evidenceRefs"] = refs
        track["openQuestions"] = [definition["open"]]
    write(path, document)


def main() -> None:
    update_capabilities()
    update_source_adapter()
    update_card_adapter()
    update_matrix()
    print("activated revision 4567865 historical Dutch/Polish/Russian adapters")


if __name__ == "__main__":
    main()
