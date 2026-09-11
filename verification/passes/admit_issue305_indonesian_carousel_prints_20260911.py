#!/usr/bin/env python3
"""Admit physical-printing evidence for 13 Indonesian Snorlax releases.

Issue #258 established these card releases from official Indonesian renders and
recorded a third-party Instagram collector carousel photograph for each in
``specimens.json`` (SPEC-0326..SPEC-0388).  The carousel photographs positively
establish that a physical Indonesian card exists; the observed text explicitly
states that **no finish, edition, size or alternative is inferred**.  This pass
therefore materialises one ``physical-printing`` entity per release (the graph
never admitted one, so ``collector_catalogue.py`` emitted them as
``research-placeholder``) while deliberately carrying ``finish=None``,
``edition=None``, ``foilPattern=None`` and ``distribution=None``.  It follows
the reviewed-positive-evidence pattern of
``admit_issue261_latam_svp_prerelease_20260825.py``: for each release a
set-source-record (holding the ``physicalPrintingEvidence``), a positive
candidate-claim, the physical-printing node, the edges
(``established-by`` -> claim, ``realizes`` -> card-release,
``materializes`` from claim) and the migration disposition.

Only the 13 released card identities below are admitted; nothing adversarial is
inferred, and no specimen or unit file is touched (their carousel rows already
carry ``citedBy`` pointing at the ``ID:<code>:<num>:base`` print).

    python verification/passes/admit_issue305_indonesian_carousel_prints_20260911.py
    python verification/passes/admit_issue305_indonesian_carousel_prints_20260911.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "verification"
GRAPH_PATH = VERIFY / "authoritative_graph.json"
SOURCES_PATH = VERIFY / "set_catalogue_sources.json"
SPECIMENS_PATH = VERIFY / "specimens.json"
sys.path.insert(0, str(ROOT / "scripts"))

import authoritative_graph as graph_projection  # noqa: E402

REVIEWED_AT = "2026-09-11"
INSTAGRAM_URL = "https://www.instagram.com/p/DLKJu7Mvpap/"
# locality every physical-printing must map into
LOCALITY = "ID"

# One entry per release: set code + collector number (used to resolve the
# existing card-release node), the carousel specimen id(s) already cited to
# ``ID:<code>:<num>:base``, and the work key carried by that release.
RELEASES = (
    {"code": "sc1a I", "number": "127/154", "specimenIds": ["SPEC-0355"]},
    {"code": "sc1b I", "number": "119/153", "specimenIds": ["SPEC-0350"]},
    {"code": "sc1b I", "number": "120/153", "specimenIds": ["SPEC-0352"]},
    {"code": "sc1D I", "number": "132/164", "specimenIds": ["SPEC-0342"]},
    {"code": "sc1D I", "number": "133/164", "specimenIds": ["SPEC-0345"]},
    {"code": "S10a I", "number": "058/071", "specimenIds": ["SPEC-0369"]},
    {"code": "S10b I", "number": "056/071", "specimenIds": ["SPEC-0367"]},
    {"code": "AS1b", "number": "112/150", "specimenIds": ["SPEC-0326"]},
    {"code": "AS1D", "number": "108/140", "specimenIds": ["SPEC-0328"]},
    {"code": "AC3D", "number": "120/172", "specimenIds": ["SPEC-0337"]},
    {"code": "SV4a I", "number": "145/190", "specimenIds": ["SPEC-0381", "SPEC-0382"]},
    {"code": "SV4a I", "number": "310/190", "specimenIds": ["SPEC-0384"]},
    {"code": "SV6s I", "number": "136/167", "specimenIds": ["SPEC-0388"]},
)


def stable_id(prefix: str, *parts: str) -> str:
    body = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(body).hexdigest()[:16]}"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encoded(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def upsert_entity(
    graph: dict[str, Any], entity_type: str, entity_id: str, payload: dict[str, Any],
) -> None:
    expected = {
        "entityType": entity_type,
        "entityId": entity_id,
        "origin": "reviewed-evidence-issue-258b-carousel",
        "payload": payload,
    }
    matches = [
        row for row in graph["entities"]
        if row.get("entityType") == entity_type and row.get("entityId") == entity_id
    ]
    if not matches:
        graph["entities"].append(expected)
    elif len(matches) != 1 or matches[0] != expected:
        raise ValueError(f"drift in {entity_type} {entity_id}")


def upsert_edge(
    graph: dict[str, Any], from_type: str, from_id: str, relation: str,
    to_type: str, to_id: str, provenance: dict[str, Any] | None = None,
) -> None:
    expected = {
        "fromType": from_type,
        "fromId": from_id,
        "relation": relation,
        "toType": to_type,
        "toId": to_id,
        "provenance": provenance or {},
    }
    key = (from_type, from_id, relation, to_type, to_id)
    matches = [
        row for row in graph["edges"]
        if (
            row.get("fromType"), row.get("fromId"), row.get("relation"),
            row.get("toType"), row.get("toId"),
        ) == key
    ]
    if not matches:
        graph["edges"].append(expected)
    elif len(matches) != 1 or matches[0] != expected:
        raise ValueError(f"drift in edge {key}")


def upsert_migration(graph: dict[str, Any], expected: dict[str, Any]) -> None:
    key = (expected["sourceKind"], expected["sourceId"])
    matches = [
        row for row in graph["migrationDispositions"]
        if (row.get("sourceKind"), row.get("sourceId")) == key
    ]
    if not matches:
        graph["migrationDispositions"].append(expected)
    elif len(matches) != 1 or matches[0] != expected:
        raise ValueError(f"drift in migration disposition {key}")


def resolve_release_ids(graph: dict[str, Any]) -> dict[tuple[str, str], str]:
    resolved: dict[tuple[str, str], str] = {}
    for row in graph["entities"]:
        if row.get("entityType") != "card-release":
            continue
        payload = row.get("payload") or {}
        if payload.get("locality") != LOCALITY:
            continue
        resolved.setdefault(
            (str(payload.get("localSetCode")), str(payload.get("localNumber"))), row["entityId"]
        )
    for facts in RELEASES:
        key = (facts["code"], facts["number"])
        if key not in resolved:
            raise ValueError(f"no single ID card-release for {key}: {resolved.get(key)}")
    return resolved


def evidence_payload(facts: dict[str, Any], release_id: str) -> dict[str, Any]:
    specimens = ", ".join(facts["specimenIds"])
    return {
        "cardReleaseId": release_id,
        "sourceUrl": INSTAGRAM_URL,
        "finish": None,
        "edition": None,
        "foilPattern": None,
        "markings": [],
        "distribution": None,
        "cardSize": "unknown",
        "specimenIds": sorted(facts["specimenIds"]),
        "positiveOnly": True,
        "completenessClaim": False,
        "basis": (
            f"The public Instagram collector carousel photograph{'' if len(facts['specimenIds']) == 1 else 's'} "
            f"{specimens} show the physical Indonesian {facts['code']} {facts['number']} card and establish "
            f"its exact release identity and existence; no finish, edition, size or unpictured alternative is inferred."
        ),
    }


def apply_release(graph: dict[str, Any], sources: dict[str, Any],
                  facts: dict[str, Any], release_id: str) -> None:
    source_id = stable_id("SET-SRC-INSTAGRAM-CAROUSEL", release_id)
    evidence = evidence_payload(facts, release_id)
    raw = {
        "locality": LOCALITY,
        "languageScope": "Indonesian",
        "localCode": facts["code"],
        "physicalPrintingEvidence": evidence,
    }
    record = {
        "sourceRecordId": source_id,
        "sourceKind": "source-first-local-set-profile",
        "provider": "mixed-positive-evidence",
        "providerRecordKey": f"ID\x1f{facts['code']}\x1f{facts['number']}\x1fcarousel",
        "retrieved": REVIEWED_AT,
        "sourceUrl": INSTAGRAM_URL,
        "raw": raw,
    }
    reconcile_source(sources, record)

    physical_id = stable_id("PHYSICAL", release_id, "instagram-carousel-evidence")
    claim_id = stable_id("CLAIM:positive", source_id, physical_id)

    upsert_entity(graph, "set-source-record", source_id, record)
    upsert_entity(graph, "set-source-disposition", source_id, {
        "sourceRecordId": source_id,
        "disposition": "established-and-mapped",
        "targetRef": physical_id,
        "reason": evidence["basis"],
    })
    upsert_edge(graph, "set-source-disposition", source_id, "disposes",
                "set-source-record", source_id)
    upsert_migration(graph, {
        "sourceKind": "set-catalogue-source",
        "sourceId": source_id,
        "disposition": "established-and-mapped",
        "targetRef": physical_id,
        "reason": evidence["basis"],
    })

    claim = {
        "claimId": claim_id,
        "claimKind": "physical-printing",
        "sourceKind": "reviewed-positive-evidence",
        "sourceId": source_id,
        "sourceRecord": INSTAGRAM_URL,
        "evidenceStatus": "confirmed",
        "disposition": "established-and-mapped",
        "proposedTargetId": physical_id,
        "materializedTargetId": physical_id,
        "specimenIds": sorted(facts["specimenIds"]),
        "reason": evidence["basis"],
    }
    upsert_entity(graph, "candidate-claim", claim_id, claim)
    upsert_edge(graph, "candidate-claim", claim_id, "materializes",
                "physical-printing", physical_id,
                {"disposition": "established-and-mapped"})
    upsert_migration(graph, {
        "sourceKind": "reviewed-positive-evidence",
        "sourceId": source_id,
        "disposition": claim["disposition"],
        "targetRef": physical_id,
        "reason": evidence["basis"],
    })

    physical = {
        "physicalPrintingId": physical_id,
        "cardReleaseId": release_id,
        "finish": evidence["finish"],
        "edition": evidence["edition"],
        "foilPattern": evidence["foilPattern"],
        "markings": evidence["markings"],
        "distribution": evidence["distribution"],
        "cardSize": evidence["cardSize"],
        "errorClass": None,
        "classificationState": "classified-from-positive-evidence",
        "sourceFinishUnitId": None,
        "sourcePrintingId": None,
        "sourceRecordIds": [source_id],
        "establishingClaimId": claim_id,
        "specimenIds": sorted(facts["specimenIds"]),
    }
    upsert_entity(graph, "physical-printing", physical_id, physical)
    upsert_edge(graph, "physical-printing", physical_id, "established-by",
                "candidate-claim", claim_id)
    upsert_edge(graph, "physical-printing", physical_id, "realizes",
                "card-release", release_id)


def reconcile_source(sources: dict[str, Any], record: dict[str, Any]) -> None:
    rows = sources["sourceRecords"]
    matches = [row for row in rows if row.get("sourceRecordId") == record["sourceRecordId"]]
    if not matches:
        rows.append(record)
    elif len(matches) != 1 or matches[0] != record:
        raise ValueError(f"drift in set source {record['sourceRecordId']}")
    counts = sources["meta"]["counts"]
    counts["sourceRecords"] = len(rows)


def apply_sources(sources: dict[str, Any], release_by_key: dict[tuple[str, str], str]) -> None:
    for facts in RELEASES:
        release_id = release_by_key[(facts["code"], facts["number"])]
        reconcile_source(sources, {
            "sourceRecordId": stable_id("SET-SRC-INSTAGRAM-CAROUSEL", release_id),
            "sourceKind": "source-first-local-set-profile",
            "provider": "mixed-positive-evidence",
            "providerRecordKey": f"ID\x1f{facts['code']}\x1f{facts['number']}\x1fcarousel",
            "retrieved": REVIEWED_AT,
            "sourceUrl": INSTAGRAM_URL,
            "raw": {
                "locality": LOCALITY,
                "languageScope": "Indonesian",
                "localCode": facts["code"],
                "physicalPrintingEvidence": evidence_payload(facts, release_id),
            },
        })


def apply_graph(graph: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    release_by_key = resolve_release_ids(graph)
    for facts in RELEASES:
        release_id = release_by_key[(facts["code"], facts["number"])]
        apply_release(graph, sources, facts, release_id)
    return graph_projection.project_physical_evidence(graph)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    original_sources = SOURCES_PATH.read_text(encoding="utf-8")
    original_graph = GRAPH_PATH.read_text(encoding="utf-8")
    sources = json.loads(original_sources)
    graph = json.loads(original_graph)

    apply_sources(sources, resolve_release_ids(graph))
    graph = apply_graph(graph, sources)

    wanted_sources = encoded(sources)
    wanted_graph = encoded(graph)

    if args.check:
        if wanted_sources != original_sources or wanted_graph != original_graph:
            raise SystemExit("Indonesian carousel physical-printing pass is not applied")
        print("validated Indonesian carousel physical-printing evidence")
        return 0

    SOURCES_PATH.write_text(wanted_sources, encoding="utf-8", newline="\n")
    GRAPH_PATH.write_text(wanted_graph, encoding="utf-8", newline="\n")
    print("admitted 13 Indonesian carousel physical-printing releases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())