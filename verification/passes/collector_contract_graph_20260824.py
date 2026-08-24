#!/usr/bin/env python3
"""Add the reviewed collector-contract boundary to the authoritative graph (#254).

The pass adds three things the producer contract cannot safely infer in a consumer:

* explicit locality + language + script localizations with BCP-47 tags;
* local-set parents for identity-only editions whose printed code/name remain unknown; and
* exact card-release targets for retained, non-materializing finish candidates.

No candidate becomes a physical printing, no unknown identifier is filled, and no
source-first discovery output is promoted.  The pass is idempotent.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH = ROOT / "verification" / "authoritative_graph.json"
FINISH_UNITS = ROOT / "verification" / "finish_units.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
ISSUE = "https://github.com/m4s-ai/snoredex-data/issues/254"
REVIEWED_AT = "2026-08-24"

# One reviewed display vocabulary for the 16 locality-bearing language/script
# combinations that the current graph actually contains.  Portuguese deliberately
# remains the producer value ``pt`` rather than being reinterpreted as pt-BR.
LOCALIZATIONS = {
    ("WEST", "English", "Latn"): ("LANG:English", "en", "English", 10),
    ("WEST", "German", "Latn"): ("LANG:German", "de", "German", 20),
    ("WEST", "French", "Latn"): ("LANG:French", "fr", "French", 30),
    ("WEST", "Italian", "Latn"): ("LANG:Italian", "it", "Italian", 40),
    ("WEST", "Spanish", "Latn"): ("LANG:Spanish", "es-ES", "Spanish (Europe)", 50),
    ("LATAM", "Spanish", "Latn"): ("LANG:Spanish", "es-419", "Spanish (Latin America)", 60),
    ("WEST", "Portuguese", "Latn"): ("LANG:Portuguese", "pt", "Portuguese", 70),
    ("WEST", "Dutch", "Latn"): ("LANG:Dutch", "nl", "Dutch", 80),
    ("WEST", "Polish", "Latn"): ("LANG:Polish", "pl", "Polish", 90),
    ("WEST", "Russian", "Cyrl"): ("LANG:Russian", "ru", "Russian", 100),
    ("JP", "Japanese", "Jpan"): ("LANG:Japanese", "ja", "Japanese", 110),
    ("KR", "Korean", "Hang"): ("LANG:Korean", "ko", "Korean", 120),
    ("CN", "S-Chinese", "Hans"): ("LANG:S-Chinese", "zh-Hans", "Chinese (Simplified)", 130),
    ("TW", "T-Chinese", "Hant"): ("LANG:T-Chinese", "zh-Hant", "Chinese (Traditional)", 140),
    ("ID", "Indonesian", "Latn"): ("LANG:Indonesian", "id", "Indonesian", 150),
    ("TH", "Thai", "Thai"): ("LANG:Thai", "th", "Thai", 160),
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def localization_id(locality: str, tag: str) -> str:
    return f"LOCALIZATION:{locality}:{tag}"


def unresolved_local_set_id(edition_id: str) -> str:
    digest = hashlib.sha256(edition_id.encode("utf-8")).hexdigest()[:20]
    return f"LOCALSET:UNRESOLVED:{digest}"


def identity_of(payload: dict) -> dict:
    identity = payload.get("identity")
    return identity if isinstance(identity, dict) else payload


def specimen_markings(observation: dict) -> list[dict]:
    text = observation.get("markings")
    if not text:
        return []
    role = observation.get("markingRole")
    if not role:
        raise ValueError("specimen marking has no reviewed role")
    return [{"kind": "observed-marking", "role": role, "text": text}]


def main() -> int:
    graph = read(GRAPH)
    specimen_by_id = {
        row["specimenId"]: row for row in read(SPECIMENS)["specimens"]
    }
    normalized_markings = 0
    for row in graph["entities"]:
        if row["entityType"] != "physical-printing":
            continue
        payload = row["payload"]
        specimen_id = payload.get("establishingSpecimenId")
        if not specimen_id:
            continue
        observation = specimen_by_id[specimen_id].get("physicalObservation") or {}
        expected = specimen_markings(observation)
        if isinstance(payload.get("markings"), str):
            payload["markings"] = expected
            normalized_markings += 1
        elif (payload.get("markings") or []) != expected:
            raise ValueError(f"specimen marking projection is stale: {specimen_id}")

    if graph["meta"].get("schemaVersion") == "1.1.0":
        if normalized_markings:
            write(GRAPH, graph)
            print(f"collector contract graph: normalized {normalized_markings} specimen markings")
        else:
            print("collector contract graph pass already applied")
        return 0
    if graph["meta"].get("schemaVersion") != "1.0.0":
        raise ValueError("collector contract pass expects graph schema 1.0.0")

    entities = graph["entities"]
    edges = graph["edges"]
    entity_keys = {(row["entityType"], row["entityId"]) for row in entities}
    edge_keys = {
        (row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
        for row in edges
    }

    editions = [row for row in entities if row["entityType"] == "set-edition"]
    observed = {
        (identity_of(row["payload"])["locality"], identity_of(row["payload"])["language"],
         identity_of(row["payload"])["script"])
        for row in editions
    }
    if observed != set(LOCALIZATIONS):
        raise ValueError(f"localization review is stale: {sorted(observed ^ set(LOCALIZATIONS))}")

    additions: list[dict] = []
    new_edges: list[dict] = []
    for key, (language_id, tag, display_name, display_order) in LOCALIZATIONS.items():
        locality, language, script = key
        loc_id = localization_id(locality, tag)
        additions.append({
            "entityType": "localization",
            "entityId": loc_id,
            "origin": "reviewed-collector-contract-254",
            "payload": {
                "localizationId": loc_id,
                "locality": locality,
                "languageId": language_id,
                "language": language,
                "languageTag": tag,
                "script": script,
                "displayName": display_name,
                "displayOrder": display_order,
                "reviewedAt": REVIEWED_AT,
                "decisionRef": ISSUE,
            },
        })

    for row in editions:
        payload = row["payload"]
        edition_id = row["entityId"]
        identity = dict(identity_of(payload))
        spec = LOCALIZATIONS[(identity["locality"], identity["language"], identity["script"])]
        loc_id = localization_id(identity["locality"], spec[1])
        identity["localizationId"] = loc_id

        catalogue = payload.get("catalogue")
        if isinstance(catalogue, dict):
            catalogue = dict(catalogue)
            catalogue["localizationId"] = loc_id
        else:
            local_set_id = unresolved_local_set_id(edition_id)
            evidence_refs = sorted(identity.get("establishingClaimIds") or [])
            additions.append({
                "entityType": "local-set",
                "entityId": local_set_id,
                "origin": "reviewed-collector-contract-254",
                "payload": {
                    "localSetId": local_set_id,
                    "locality": identity["locality"],
                    "localCode": None,
                    "observedNames": [],
                    "productKind": "unknown-physical-card-set-or-product",
                    "state": "needs-local-identifier",
                    "sourceRecordIds": [],
                    "evidenceRefs": evidence_refs,
                    "reviewedAt": REVIEWED_AT,
                    "decisionRef": ISSUE,
                },
            })
            catalogue = {
                "setEditionId": edition_id,
                "localSetId": local_set_id,
                "locality": identity["locality"],
                "language": identity["language"],
                "script": identity["script"],
                "localCode": None,
                "state": "needs-local-identifier",
                "establishingEvidenceIds": evidence_refs,
                "localizationId": loc_id,
            }
            new_edges.append({
                "fromType": "set-edition",
                "fromId": edition_id,
                "relation": "belongs-to",
                "toType": "local-set",
                "toId": local_set_id,
                "provenance": {"decisionRef": ISSUE, "reviewedAt": REVIEWED_AT},
            })

        row["payload"] = {
            "setEditionId": edition_id,
            "identity": identity,
            "catalogue": catalogue,
        }
        new_edges.append({
            "fromType": "set-edition",
            "fromId": edition_id,
            "relation": "localized-as",
            "toType": "localization",
            "toId": loc_id,
            "provenance": {"decisionRef": ISSUE, "reviewedAt": REVIEWED_AT},
        })

    finish_units = read(FINISH_UNITS)["units"]
    unit_by_printing = {
        printing["printingId"]: unit
        for unit in finish_units
        for printing in unit.get("printings", [])
    }
    releases = [row["payload"] for row in entities if row["entityType"] == "card-release"]
    release_index: defaultdict[tuple[str, str, str], list[str]] = defaultdict(list)
    for release in releases:
        set_codes = {release.get("localSetCode"), release.get("viaLegacySetCode")} - {None}
        numbers = {
            str(value or "") for value in (release.get("localNumber"), release.get("viaLegacyNumber"))
        }
        for set_code in set_codes:
            for number in numbers:
                release_index[(str(set_code), number, release["language"])].append(
                    release["cardReleaseId"]
                )

    linked_candidates = 0
    for row in entities:
        if row["entityType"] != "candidate-claim":
            continue
        claim = row["payload"]
        if claim.get("sourceKind") != "finish-printing-record" \
                or claim.get("disposition") != "candidate-needs-evidence":
            continue
        unit = unit_by_printing.get(claim.get("sourceId"))
        if not unit:
            raise ValueError(f"finish candidate has no source unit: {claim.get('claimId')}")
        key = (str(unit.get("setCode") or ""), str(unit.get("number") or ""), unit["language"])
        targets = sorted(set(release_index[key]))
        if len(targets) != 1:
            raise ValueError(f"finish candidate does not resolve exactly once: {claim['claimId']} -> {targets}")
        claim["proposedCardReleaseId"] = targets[0]
        linked_candidates += 1
        new_edges.append({
            "fromType": "candidate-claim",
            "fromId": claim["claimId"],
            "relation": "proposes-for",
            "toType": "card-release",
            "toId": targets[0],
            "provenance": {"decisionRef": ISSUE, "reviewedAt": REVIEWED_AT},
        })

    for row in additions:
        key = (row["entityType"], row["entityId"])
        if key in entity_keys:
            raise ValueError(f"collector graph entity already exists: {key}")
        entity_keys.add(key)
    entities.extend(sorted(additions, key=lambda row: (row["entityType"], row["entityId"])))

    for row in sorted(
        new_edges,
        key=lambda edge: (
            edge["fromType"], edge["fromId"], edge["relation"], edge["toType"], edge["toId"]
        ),
    ):
        key = (row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
        if key in edge_keys:
            continue
        edge_keys.add(key)
        edges.append(row)

    graph["meta"]["schemaVersion"] = "1.1.0"
    graph["meta"]["generated"] = REVIEWED_AT
    graph["meta"]["collectorContractIssue"] = ISSUE
    graph["summary"]["entities"] = len(entities)
    graph["summary"]["edges"] = len(edges)
    graph["summary"]["localizations"] = len(LOCALIZATIONS)
    write(GRAPH, graph)
    print(
        f"collector contract graph: {len(LOCALIZATIONS)} localizations, "
        f"{len([row for row in additions if row['entityType'] == 'local-set'])} unresolved local sets, "
        f"{linked_candidates} finish-candidate release links, "
        f"{normalized_markings} normalized specimen markings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
