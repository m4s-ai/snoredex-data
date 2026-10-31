"""Record the owner-supplied names that #436 was missing (2026-10-31).

Local set names, from the collection owner's statements of 2026-10-31. The three promo series carry
an English series name only; there is no localized name:

* ID SM-P (Eevee & Snorlax-GX 166/SM-P): "Sun & Moon Indonesian Promos gibt halt nur den
  englsichen set namen".
* TH SM-P (Eevee & Snorlax-GX 083/SM-P): "das ist genauso Sun & moon thai Promos".
* KR S-P (Snorlax 101/S-P): "das ist Sword & Shield Era Promo in korean".

Each becomes a `local-set-name-record` from `owner-attestation`, the same record kind as the
researched names of #430, and the local set's `observedNames` gains it.

Local card name: SPEC-0662, a photograph supplied by the owner, shows the Italian DF 10/101 face
with the name bar "Snorlax" and "δ SPECIE DELTA". Following the δ convention of the other DF 10
releases ("Snorlax δ", "Ronflex δ", "Relaxo δ"), the Italian release gets "Snorlax δ".

Idempotent; `--check` reports pending records without writing.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from admit_issue257_simplified_chinese_20260827 import upsert_edge, upsert_entity, upsert_migration  # noqa: E402

GRAPH = ROOT / "verification" / "authoritative_graph.json"
SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
NAMES = ROOT / "verification" / "local_card_names.json"
ORIGIN = "reviewed-evidence-issue-436"
RETRIEVED = "2026-10-31"
BUNDLE = "verification/evidence/issue-436-owner-input-20261031"
SET_NAMES = [
    ("LOCALSET:ID:SM-P", "Sun & Moon Indonesian Promos",
     "Sun & Moon Indonesian Promos gibt halt nur den englsichen set namen"),
    ("LOCALSET:TH:SM-P", "Sun & Moon Thai Promos", "das ist genauso Sun & moon thai Promos"),
    ("LOCALSET:KR:S-P", "Sword & Shield Era Promo", "das ist Sword & Shield Era Promo in korean"),
]
IT_DF_10 = "RELEASE:WEST:Italian:DF:10:Snorlax-Delta-Species-Bedhead-Dozing"
SPEC = "verification/specimens/SPEC-0662.png"
REASON = "Owner-stated local set name for this exact local set; name only, no membership (#436)."


def name_record(local_set: dict, value: str, quote: str) -> dict:
    digest = hashlib.sha256(f"{local_set['localSetId']}\x1f{value}".encode()).hexdigest()[:12].upper()
    return {
        "sourceRecordId": f"SET-SRC-NAME-{digest}",
        "sourceKind": "local-set-name-record",
        "provider": "owner-attestation",
        "providerRecordKey": f"{local_set['locality']}\x1f{local_set['localCode']}\x1fname",
        "retrieved": RETRIEVED,
        "raw": {"localCode": local_set["localCode"], "locality": local_set["locality"], "localName": value,
                "excerpt": f"Collection owner, {RETRIEVED}: \"{quote}\"", "confidence": "high",
                "evidenceBundle": BUNDLE,
                "note": "The series carries an English name only; no localized set name exists."},
    }


def card_name(sha256: str) -> dict:
    return {"value": "Snorlax δ", "evidence": [{
        "sourceRef": SPEC, "providerId": "inspected-specimen", "retrievedAt": RETRIEVED,
        "excerpt": "Visual transcription of the card name bar: \"Snorlax\" with \"δ SPECIE DELTA\" "
                   "(Italian DF 10/101 face, SPEC-0662). Written \"Snorlax δ\" as for the other DF 10 releases.",
        "evidencePath": SPEC, "sha256": sha256, "confidence": "high", "evidenceBundle": BUNDLE}]}


def apply_set_name(graph: dict, sources: dict, local_set: dict, record: dict) -> None:
    sid = record["sourceRecordId"]
    sources["sourceRecords"] = [row for row in sources["sourceRecords"] if row["sourceRecordId"] != sid] + [record]
    upsert_entity(graph, "set-source-record", sid, record, origin=ORIGIN)
    upsert_entity(graph, "set-source-disposition", sid, {"sourceRecordId": sid, "disposition": "mapped",
                                                         "targetRef": local_set["localSetId"], "reason": REASON},
                  origin=ORIGIN)
    upsert_edge(graph, "set-source-disposition", sid, "disposes", "set-source-record", sid)
    upsert_edge(graph, "local-set", local_set["localSetId"], "observed-by", "set-source-record", sid)
    upsert_migration(graph, {"sourceKind": "set-catalogue-source", "sourceId": sid, "disposition": "mapped",
                             "targetRef": local_set["localSetId"], "reason": REASON})
    local_set["sourceRecordIds"] = sorted(set(local_set["sourceRecordIds"]) | {sid})
    value = record["raw"]["localName"]
    local_set["observedNames"] = [value, *[name for name in local_set.get("observedNames") or [] if name != value]]


def refresh_counts(graph: dict, sources: dict) -> None:
    summary = graph["summary"]
    summary["entities"], summary["edges"] = len(graph["entities"]), len(graph["edges"])
    summary["migrationInputs"] = len(graph["migrationDispositions"])
    summary["setSourceRecords"] = sum(row["entityType"] == "set-source-record" for row in graph["entities"])
    summary["setSourceDispositions"] = sum(row["sourceKind"] == "set-catalogue-source"
                                           for row in graph["migrationDispositions"])
    counts = sources["meta"]["counts"]
    counts["sourceRecords"] = len(sources["sourceRecords"])
    counts["localSetNameRecords"] = sum(row["sourceKind"] == "local-set-name-record" for row in sources["sourceRecords"])


def write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv) -> int:
    graph, sources, names = (json.loads(path.read_text(encoding="utf-8")) for path in (GRAPH, SOURCES, NAMES))
    local_sets = {row["entityId"]: row["payload"] for row in graph["entities"] if row["entityType"] == "local-set"}
    stored = {row["sourceRecordId"]: row for row in sources["sourceRecords"]}
    todo = [(local_sets[set_id], name_record(local_sets[set_id], value, quote))
            for set_id, value, quote in SET_NAMES]
    todo = [(local_set, record) for local_set, record in todo
            if stored.get(record["sourceRecordId"]) != record or local_set.get("observedNames", [None])[:1] != [record["raw"]["localName"]]]
    sha256 = hashlib.sha256((ROOT / SPEC).read_bytes()).hexdigest()
    name_pending = names["releases"].get(IT_DF_10) != card_name(sha256)
    if "--check" in argv:
        for local_set, record in todo:
            print("pending: local set name", local_set["localSetId"], record["raw"]["localName"])
        if name_pending:
            print("pending: Italian DF 10 local card name")
        return 1 if todo or name_pending else 0
    for local_set, record in todo:
        apply_set_name(graph, sources, local_set, record)
    if todo:
        refresh_counts(graph, sources)
        write(GRAPH, graph)
        write(SOURCES, sources)
    if name_pending:
        names["releases"][IT_DF_10] = card_name(sha256)
        write(NAMES, names)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
