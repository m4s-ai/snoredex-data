#!/usr/bin/env python3
"""Materialize the reviewed locality graph used by the application database.

The identity and set-catalogue passes are intentionally kept as reviewable, generated
artifacts.  This pass is the migration boundary from those artifacts to one canonical,
machine-readable graph snapshot.  It does not re-derive evidence or manufacture identities;
it only joins the already validated nodes, edges and dispositions and fails closed when an
input is incomplete.

    python scripts/authoritative_graph.py
    python scripts/authoritative_graph.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "verification" / "authoritative_graph.json"
INPUTS = (
    "verification/print_identity_dryrun.json",
    "verification/set_catalogue_dryrun.json",
)


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(relative: str) -> str:
    payload = (ROOT / relative).read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def entity(entity_type: str, entity_id: str, payload: dict, origin: str) -> dict:
    return {
        "entityType": entity_type,
        "entityId": entity_id,
        "origin": origin,
        "payload": payload,
    }


def add_entity(entities: dict[tuple[str, str], dict], entity_type: str, entity_id: str,
               payload: dict, origin: str) -> None:
    key = (entity_type, entity_id)
    previous = entities.get(key)
    candidate = entity(entity_type, entity_id, payload, origin)
    if previous is not None and previous["payload"] != payload:
        if entity_type == "set-edition":
            # The identity pass and the set-catalogue pass describe the same edition from
            # different angles.  Keep both raw records under one graph node instead of
            # accidentally creating two identities with the same stable id.
            identity_payload = previous["payload"].get("identity", previous["payload"])
            catalogue_payload = previous["payload"].get("catalogue", payload)
            previous["payload"] = {
                "setEditionId": entity_id,
                "identity": identity_payload,
                "catalogue": catalogue_payload,
            }
            previous["origin"] = "verification/print_identity_dryrun.json+verification/set_catalogue_dryrun.json"
            return
        raise ValueError(f"conflicting graph entity {entity_type}:{entity_id}")
    entities[key] = candidate


def edge(edges: dict[tuple[str, str, str, str, str], dict], from_type: str, from_id: str,
         relation: str, to_type: str, to_id: str, provenance: dict | None = None) -> None:
    key = (from_type, from_id, relation, to_type, to_id)
    edges[key] = {
        "fromType": from_type,
        "fromId": from_id,
        "relation": relation,
        "toType": to_type,
        "toId": to_id,
        "provenance": provenance or {},
    }


def build() -> dict:
    identity = load(INPUTS[0])
    catalogue = load(INPUTS[1])
    entities: dict[tuple[str, str], dict] = {}
    edges: dict[tuple[str, str, str, str, str], dict] = {}

    for row in identity["candidateClaims"]:
        add_entity(entities, "candidate-claim", row["claimId"], row, INPUTS[0])
        if row.get("materializedTargetId"):
            target = row["materializedTargetId"]
            target_type = "physical-printing" if row["claimKind"] == "physical-printing" else "card-release"
            edge(edges, "candidate-claim", row["claimId"], "materializes", target_type, target,
                 {"disposition": row["disposition"]})

    for row in identity["setEditions"]:
        add_entity(entities, "set-edition", row["setEditionId"], row, INPUTS[0])
    for row in identity["cardReleases"]:
        add_entity(entities, "card-release", row["cardReleaseId"], row, INPUTS[0])
        edge(edges, "card-release", row["cardReleaseId"], "belongs-to",
             "set-edition", row["setEditionId"])
        if row.get("work"):
            work_id = row["work"] if str(row["work"]).startswith("WORK:") else f"WORK:{row['work']}"
            add_entity(entities, "work", work_id, {"workId": work_id, "cardKey": row["work"]}, INPUTS[0])
            edge(edges, "card-release", row["cardReleaseId"], "implements", "work", work_id,
                 {"state": row.get("workMappingState")})
    for row in identity["physicalPrintings"]:
        add_entity(entities, "physical-printing", row["physicalPrintingId"], row, INPUTS[0])
        edge(edges, "physical-printing", row["physicalPrintingId"], "realizes",
             "card-release", row["cardReleaseId"])
        edge(edges, "physical-printing", row["physicalPrintingId"], "established-by",
             "candidate-claim", row["establishingClaimId"])
    for row in identity["equivalenceAssertions"]:
        add_entity(entities, "equivalence-assertion", row["assertionId"], row, INPUTS[0])
        for target_id in (row["fromId"], row["toId"]):
            target_types = [entity_type for entity_type, entity_id in entities if entity_id == target_id]
            if len(target_types) != 1:
                raise ValueError(
                    f"equivalence target {target_id!r} resolves to {target_types}, expected one graph entity"
                )
            edge(edges, "equivalence-assertion", row["assertionId"], "relates",
                 target_types[0], target_id, row)

    for row in catalogue["sourceRecords"]:
        add_entity(entities, "set-source-record", row["sourceRecordId"], row, INPUTS[1])
    for row in catalogue["sourceDispositions"]:
        add_entity(entities, "set-source-disposition", row["sourceRecordId"], row, INPUTS[1])
        edge(edges, "set-source-disposition", row["sourceRecordId"], "disposes",
             "set-source-record", row["sourceRecordId"])
    for row in catalogue["localSets"]:
        add_entity(entities, "local-set", row["localSetId"], row, INPUTS[1])
        for source_id in row.get("sourceRecordIds", []):
            edge(edges, "local-set", row["localSetId"], "observed-by", "set-source-record", source_id)
    for row in catalogue["setEditions"]:
        add_entity(entities, "set-edition", row["setEditionId"], row, INPUTS[1])
        edge(edges, "set-edition", row["setEditionId"], "belongs-to", "local-set", row["localSetId"])
    for row in catalogue["editionCandidates"]:
        add_entity(entities, "edition-candidate", row["setEditionId"], row, INPUTS[1])
    for row in catalogue["editionRelations"]:
        relation_id = row.get("editionRelationId") or compact(row)
        add_entity(entities, "edition-relation", relation_id, row, INPUTS[1])
    for row in catalogue["releaseEvents"]:
        add_entity(entities, "release-event", row["releaseEventId"], row, INPUTS[1])
        edge(edges, "release-event", row["releaseEventId"], "belongs-to", "local-set", row["localSetId"])
        for edition_id in row.get("setEditionIds", []):
            edge(edges, "release-event", row["releaseEventId"], "supports", "set-edition", edition_id)
    for row in catalogue["finishProfiles"]:
        profile_id = row["finishProfileId"]
        add_entity(entities, "finish-profile", profile_id, row, INPUTS[1])
        edge(edges, "finish-profile", profile_id, "scoped-to", "local-set", row["localSetId"],
             {"scopePrecision": row.get("scopePrecision")})
        for edition_id in row.get("setEditionIds", []):
            edge(edges, "finish-profile", profile_id, "scoped-to", "set-edition", edition_id,
                 {"scopePrecision": row.get("scopePrecision")})
        edge(edges, "finish-profile", profile_id, "supported-by", "set-source-record",
             row["sourceRecordId"])
    for row in catalogue["cardReleaseRefs"]:
        ref_id = row["cardReleaseId"]
        add_entity(entities, "catalogue-card-release-ref", ref_id, row, INPUTS[1])
        edge(edges, "catalogue-card-release-ref", ref_id, "references",
             "card-release", row["cardReleaseId"])
        edge(edges, "catalogue-card-release-ref", ref_id, "belongs-to",
             "set-edition", row["setEditionId"])
    for row in catalogue["rarityClaims"]:
        claim_id = row["rarityClaimId"]
        add_entity(entities, "rarity-claim", claim_id, row, INPUTS[1])
        edge(edges, "rarity-claim", claim_id, "asserts-rarity-for",
             "card-release", row["cardReleaseId"])
        edge(edges, "rarity-claim", claim_id, "observed-by",
             "set-source-record", row["sourceRecordId"])
    for row in catalogue["profileFinishClaims"]:
        claim_id = row["profileFinishClaimId"]
        add_entity(entities, "profile-finish-claim", claim_id, row, INPUTS[1])
        edge(edges, "profile-finish-claim", claim_id, "uses-profile",
             "finish-profile", row["finishProfileId"])
        edge(edges, "profile-finish-claim", claim_id, "asserts-finish-for",
             "card-release", row["cardReleaseId"])
    for row in catalogue["aliasAssertions"]:
        assertion_id = row["aliasAssertionId"]
        add_entity(entities, "catalogue-alias-assertion", assertion_id, row, INPUTS[1])
        edge(edges, "catalogue-alias-assertion", assertion_id, "asserted-by",
             "set-source-record", row["sourceRecordId"])
        if row.get("localSetId"):
            edge(edges, "catalogue-alias-assertion", assertion_id, row["relationship"],
                 "local-set", row["localSetId"])
        if row.get("setEditionId"):
            edge(edges, "catalogue-alias-assertion", assertion_id, row["relationship"],
                 "set-edition", row["setEditionId"])
    source_targets = (
        ("rarityClaimId", "rarity-claim"),
        ("localSetId", "local-set"),
        ("releaseEventId", "release-event"),
        ("setEditionId", "set-edition"),
        ("finishProfileId", "finish-profile"),
    )
    for row in catalogue["sourceAssertions"]:
        assertion_id = row["sourceAssertionId"]
        add_entity(entities, "source-assertion", assertion_id, row, INPUTS[1])
        edge(edges, "source-assertion", assertion_id, "asserted-by",
             "set-source-record", row["sourceRecordId"])
        for field, target_type in source_targets:
            if row.get(field):
                edge(edges, "source-assertion", assertion_id, row["assertionKind"],
                     target_type, row[field])
                break

    for source_id, record in sorted(identity["legacyProductDispositions"].items()):
        product_id = f"LEGACYPRODUCT:{source_id}"
        targets = list(record.get("cardReleaseIds") or [])
        add_entity(
            entities, "legacy-cardmarket-product", product_id,
            {**record, "sourceId": source_id, "cardReleaseIds": targets}, INPUTS[0],
        )
        for target in targets:
            edge(edges, "legacy-cardmarket-product", product_id, "maps-to",
                 "card-release", target, {"disposition": record["disposition"]})

    migration: list[dict] = []
    for row in identity["candidateClaims"]:
        migration.append({
            "sourceKind": row["sourceKind"], "sourceId": row["sourceId"],
            "disposition": row["disposition"], "targetRef": row.get("materializedTargetId"),
            "reason": row.get("reason") or "identity claim disposition",
        })
    for row in catalogue["sourceDispositions"]:
        migration.append({
            "sourceKind": "set-catalogue-source", "sourceId": row["sourceRecordId"],
            "disposition": row["disposition"], "targetRef": row.get("targetRef"),
            "reason": row["reason"],
        })
    for source_id, record in sorted(identity["legacyProductDispositions"].items()):
        targets = list(record.get("cardReleaseIds") or [])
        migration.append({
            "sourceKind": "legacy-cardmarket-product", "sourceId": source_id,
            "disposition": record["disposition"],
            "targetRef": targets[0] if targets else None,
            "targetRefs": targets,
            "reason": record.get("reason") or "legacy product migration disposition",
        })
    for report in identity["reports"].get("legacyIssueRekeys", []):
        for row in report.get("rows", []):
            migration.append({
                "sourceKind": "legacy-issue-rekey", "sourceId": row["legacyUnitId"],
                "disposition": row["disposition"],
                "targetRef": (row.get("localCardReleaseIds") or [None])[0],
                "targetRefs": list(row.get("localCardReleaseIds") or []),
                "reason": row.get("reason") or f"issue #{report['issueNumber']} re-key",
            })
    migration_keys = [(row["sourceKind"], row["sourceId"]) for row in migration]
    if len(migration_keys) != len(set(migration_keys)):
        raise ValueError("migration inputs contain duplicate source kind/id pairs")

    entity_rows = sorted(entities.values(), key=lambda row: (row["entityType"], row["entityId"]))
    edge_rows = sorted(edges.values(), key=lambda row: (
        row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"]
    ))
    entity_keys = {(row["entityType"], row["entityId"]) for row in entity_rows}
    missing_targets = [
        row for row in edge_rows
        if row["toType"] != "node"
        and (row["toType"], row["toId"]) not in entity_keys
    ]
    if missing_targets:
        raise ValueError(f"graph has {len(missing_targets)} dangling typed edge(s): {missing_targets[:3]}")

    dispositions = Counter(row["disposition"] for row in migration)
    generated = max(identity["meta"]["generated"], catalogue["meta"]["generated"])
    return {
        "meta": {
            "schema": "snoredex-authoritative-locality-graph",
            "schemaVersion": "1.0.0",
            "status": "authoritative-migrated",
            "generated": generated,
            "inputs": {path: digest(path) for path in INPUTS},
            "identitySource": identity["meta"].get("schema"),
            "catalogueSource": catalogue["meta"].get("schema"),
            "description": (
                "Canonical locality graph after the reviewed #140 migration boundary. "
                "Raw source records, claims and dispositions remain reversible."
            ),
        },
        "entities": entity_rows,
        "edges": edge_rows,
        "migrationDispositions": migration,
        "summary": {
            "entities": len(entity_rows),
            "edges": len(edge_rows),
            "migrationInputs": len(migration),
            "migrationDispositions": dict(sorted(dispositions.items())),
            "candidateClaims": len(identity["candidateClaims"]),
            "cardReleases": len(identity["cardReleases"]),
            "physicalPrintings": len(identity["physicalPrintings"]),
            "setSourceRecords": len(catalogue["sourceRecords"]),
            "setSourceDispositions": len(catalogue["sourceDispositions"]),
        },
    }


def write() -> None:
    document = build()
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    temporary = OUTPUT.with_name(OUTPUT.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, OUTPUT)
    print(
        f"authoritative_graph.py: {document['summary']['entities']} entities, "
        f"{document['summary']['edges']} edges, "
        f"{document['summary']['migrationInputs']} migration inputs"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the committed graph is current")
    args = parser.parse_args()
    document = build()
    expected = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("authoritative_graph.py: stale or missing verification/authoritative_graph.json")
            return 1
        print(
            f"authoritative_graph.py: OK ({document['summary']['entities']} entities, "
            f"{document['summary']['edges']} edges)"
        )
        return 0
    write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
