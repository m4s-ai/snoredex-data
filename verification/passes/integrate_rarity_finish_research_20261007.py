"""Apply the retained #256 research through existing graph/catalogue owners.

Bulk correction only; photographs are imported separately by fetch_attachment.py.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from admit_issue257_simplified_chinese_20260827 import upsert_entity, upsert_edge, upsert_migration
from admit_issue262_thai_as1b_release_date_20260928 import write_json

BUNDLE = ROOT / "verification/evidence/rarity-finish-research-20261006"
ORIGIN = "reviewed-evidence-issue-256-20261007"


def read(name):
    return json.loads((ROOT / "verification" / name).read_text(encoding="utf-8"))


def replace_identity(value, replacements):
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [replace_identity(row, replacements) for row in value]
    if isinstance(value, dict):
        return {replace_identity(key, replacements): replace_identity(row, replacements)
                for key, row in value.items()}
    return value


def source_record(graph, catalogue, record, target, target_type):
    sid = record["sourceRecordId"]
    rows = catalogue["sourceRecords"]
    index = next((i for i, row in enumerate(rows) if row["sourceRecordId"] == sid), None)
    if index is None:
        rows.append(record)
    else:
        rows[index] = record
    upsert_entity(graph, "set-source-record", sid, record, origin=ORIGIN)
    reason = "Positive retained evidence scoped to the exact localized product/card; no absence or finish inference."
    upsert_entity(graph, "set-source-disposition", sid,
                  {"sourceRecordId": sid, "disposition": "mapped", "targetRef": target, "reason": reason}, origin=ORIGIN)
    upsert_edge(graph, "set-source-disposition", sid, "disposes", "set-source-record", sid)
    upsert_migration(graph, {"sourceKind": "set-catalogue-source", "sourceId": sid,
                            "disposition": "mapped", "targetRef": target, "reason": reason})
    upsert_edge(graph, "set-source-record", sid,
                "asserts-release-event" if target_type == "release-event" else "observed-by",
                target_type, target)


def admit_date(graph, catalogue, releases, prints, release_id, value, url, retrieved, *, card_only=False):
    release = releases[release_id]
    code, locality = release["localSetCode"], release["locality"]
    edition = release["setEditionId"]
    edition_row = next(row["payload"] for row in graph["entities"]
                       if row["entityType"] == "set-edition" and row["entityId"] == edition)
    local_set = edition_row["catalogue"]["localSetId"]
    suffix = release["localNumber"].replace("/", "-") if card_only else "launch"
    sid = f"SET-SRC-RESEARCH-DATE-{locality}-{code}-{suffix}-20261007"
    target = release_id if card_only else f"EVENT:{locality}:{code}:launch-{value}"
    record = {"sourceRecordId": sid, "sourceKind": "release-date-record",
              "provider": "pokemon-card-korea" if locality == "KR" else "pokemon-cn-official",
              "providerRecordKey": url + "#" + suffix + ":" + locality + ":" + code,
              "retrieved": retrieved, "sourceUrl": url,
              "raw": {"localCode": code, "locality": locality, "languageScope": release["language"],
                      "marketScopes": [locality], "date": value, "datePrecision": "day",
                      "approximate": False, "status": "released",
                      "marketScopeBasis": "Exact localized publisher product matched to retained card identity.",
                      "note": "Exact named promo only; not the whole promo sequence." if card_only
                              else "Localized product launch; prerelease and later reprints not asserted."}}
    source_record(graph, catalogue, record, target, "card-release" if card_only else "release-event")
    if not card_only:
        event = {"releaseEventId": target, "localSetId": local_set, "setEditionIds": [edition],
                 "eventKind": "launch", "dateValue": value, "datePrecision": "day",
                 "approximate": False, "status": "released", "timezone": None,
                 "marketScopes": [locality], "marketScopeBasis": record["raw"]["marketScopeBasis"],
                 "sourceRecordId": sid, "linkBasis": "Exact established local set and publisher product."}
        upsert_entity(graph, "release-event", target, event, origin=ORIGIN)
        upsert_edge(graph, "release-event", target, "belongs-to", "local-set", local_set)
        upsert_edge(graph, "release-event", target, "supports", "set-edition", edition)
    for print_id in release.get("sourceFirstRecordIds", []):
        row = next(row for row in prints["prints"] if row["printId"] == print_id)
        row.update(releaseDate=value, releaseDatePrecision="day", releaseApproximate=False,
                   releaseDateSourceUrl=url, releaseDateProviderId=record["provider"],
                   releaseDateRetrievedAt=retrieved, releaseDateSourceRecordId=sid)
    release.update(releaseDate=value, releaseDatePrecision="day", releaseApproximate=False)


def apply(documents):
    graph, catalogue, prints, rekeys, overrides = documents
    # The old denominator came from a shared foreign-language set list. Rekey the
    # coordinated identity graph, never unrelated localities or historical captures.
    replacements = [("KR:CLF:016/034", "KR:CLF:016/032"),
                    ("KR:Korean:CLF:016/034", "KR:Korean:CLF:016/032"),
                    ("RARITYCLAIM:issue260:CLF:016/034", "RARITYCLAIM:issue260:CLF:016/032")]
    for document in (graph, catalogue, prints, rekeys):
        corrected = replace_identity(document, replacements)
        document.clear()
        document.update(corrected)
    classic = next(row for row in prints["prints"] if row["printId"] == "KR:CLF:016/032:base")
    classic.update(localNumber="016/032", specimenId="SPEC-0616", providerId="seller-listing-photo",
                   sourceUrl="https://www.ebay.com/itm/197250301809", retrievedAt="2026-10-07",
                   evidence="SPEC-0616 positively shows Korean CLF 016/032 and Holo. The old /034 "
                            "shared-list inference is corrected; Korean and foreign releases remain distinct.")
    for row in graph["entities"]:
        payload = row["payload"]
        if row["entityType"] == "card-release" and payload.get("locality") == "KR" and payload.get("localSetCode") == "CLF":
            payload["localNumber"] = "016/032"
            payload["sourceRecords"] = sorted(set(payload.get("sourceRecords", []) + [classic["sourceUrl"]]))
        if row["entityType"] == "catalogue-card-release-ref" and row["entityId"].startswith("RELEASE:KR:Korean:CLF:"):
            payload["collectorNumber"] = "016/032"
        if payload.get("sourceKind") == "source-first-record" and payload.get("sourceId") == classic["printId"]:
            payload.update(sourceRecord=classic["sourceUrl"], retrievedAt="2026-10-07")
    profile = next(row for row in catalogue["sourceRecords"] if row["sourceRecordId"] == "SET-SRC-SF-23CB693E14E9")
    profile["raw"].update(printedSetSize=32, observedCollectorNumbers=["016/032"],
                          printedSetSizeBasis="Korean original photograph SPEC-0616; earlier foreign /034 inference superseded.")
    profile["raw"]["sourceUrls"] = sorted(set(profile["raw"]["sourceUrls"] + [classic["sourceUrl"]]))
    profile["raw"]["retrievedByPrintId"][classic["printId"]] = "2026-10-07"
    upsert_entity(graph, "set-source-record", profile["sourceRecordId"], profile, origin=ORIGIN)
    releases = {row["entityId"]: row["payload"] for row in graph["entities"] if row["entityType"] == "card-release"}

    rarity_catalogue = read("rarity_catalogue.json")
    from authoritative_graph import _rarity_native_mappings
    mappings = _rarity_native_mappings(rarity_catalogue)
    for row in graph["entities"]:
        if row["entityType"] == "rarity-claim" and row["payload"].get("sourceNativeValue") == "no printed rarity symbol":
            claim = row["payload"]
            release = releases[claim["cardReleaseId"]]
            key = (release["locality"], claim["sourceVocabulary"], claim["sourceNativeValue"])
            claim["normalizedRarityId"] = mappings.get((*key, claim["cardReleaseId"]), mappings.get((*key, None)))
    bs2 = next(row for row in prints["prints"] if row["printId"] == "KR:BS2:30/40:base")
    bs2.update(rarity=["U", "uncommon"], rarityProviderId="pokemon-card-korea",
               raritySourceUrl="https://pokemoncard.co.kr/cards/detail/BS2010002030", rarityRetrievedAt="2026-10-06")
    rid = "RELEASE:KR:Korean:BS2:30/40:Snorlax-Lv35-Block-Ease-Up"
    rarity_id = "RARITYCLAIM:issue256:BS2:30/40:Snorlax-Lv35-Block-Ease-Up"
    claim = {"rarityClaimId": rarity_id, "cardReleaseId": rid,
             "sourceRecordId": "SET-SRC-SF-5398FFDCABCD", "sourceProvider": "mixed-positive-evidence",
             "sourceVocabulary": "printed-Korean-card", "sourceNativeValue": "U",
             "normalizedRarityId": "uncommon", "sourceProductKey": bs2["raritySourceUrl"], "retrievedAt": "2026-10-06"}
    upsert_entity(graph, "rarity-claim", rarity_id, claim, origin=ORIGIN)
    upsert_edge(graph, "rarity-claim", rarity_id, "asserts-rarity-for", "card-release", rid)
    upsert_edge(graph, "rarity-claim", rarity_id, "observed-by", "set-source-record", claim["sourceRecordId"])

    research = json.loads((BUNDLE / "korean-results.json").read_text(encoding="utf-8"))
    for row in research["results"]:
        for field in row.get("supportedFields", []):
            if field["field"] == "release-date":
                admit_date(graph, catalogue, releases, prints, row["cardReleaseId"], field["value"],
                           field["sourceUrl"], "2026-10-06", card_only=":SM-P:" in row["cardReleaseId"])
    rid = next(key for key, row in releases.items() if row.get("locality") == "KR" and row.get("localSetCode") == "CLF")
    admit_date(graph, catalogue, releases, prints, rid, "2023-12-16", "https://pokemoncard.co.kr/card/590", "2026-10-07")
    # Source-first releases without legacy finish groups use the established
    # reviewed-positive-evidence graph lane (also used by Indonesian deck intake).
    from authoritative_graph import printing_semantic_key, stable_printing_id
    rid = next(key for key, row in releases.items()
               if row.get("locality") == "KR" and row.get("localSetCode") == "SM30A")
    sid = "SET-SRC-KR-SM30A-060-080-FINISH-20261007"
    url = "https://pokemoncard.co.kr/card/277"
    basis = "The exact Korean Random 30-card Deck explicitly has no Holo cards; retained official SM30A 060/080 detail establishes product membership. Positive Non-Holo only; no complete finish list."
    facts = dict(cardReleaseId=rid, sourceUrl=url, finish="non-holo", edition=None,
                 foilPattern=None, markings=[], distribution=None, cardSize="unknown",
                 specimenIds=[], positiveOnly=True, completenessClaim=False, basis=basis)
    record = dict(sourceRecordId=sid, sourceKind="edition-availability-record",
                  provider="pokemon-card-korea", providerRecordKey=url + "#SM30A:060/080:finish",
                  retrieved="2026-10-06", sourceUrl=url,
                  raw=dict(localCode="SM30A", locality="KR", languages=["Korean"],
                           physicalPrintingEvidence=facts, evidenceBundle=str(BUNDLE.relative_to(ROOT)).replace("\\", "/")))
    source_record(graph, catalogue, record, rid, "card-release")
    pid = stable_printing_id(printing_semantic_key(rid, facts))
    cid = "CLAIM:reviewed-positive-evidence:" + sid
    upsert_entity(graph, "candidate-claim", cid,
                  dict(claimId=cid, claimKind="physical-printing", sourceKind="reviewed-positive-evidence",
                       sourceId=sid, sourceRecord=url, evidenceStatus="confirmed", disposition="established-and-mapped",
                       proposedTargetId=pid, materializedTargetId=pid, specimenIds=[], reason=basis), origin=ORIGIN)
    payload = {key: facts[key] for key in ("cardReleaseId", "finish", "edition", "foilPattern", "markings", "distribution", "cardSize", "specimenIds")}
    payload.update(physicalPrintingId=pid, errorClass=None, classificationState="classified-from-positive-evidence",
                   sourceFinishUnitId=None, sourcePrintingId=None, sourceRecordIds=[sid], establishingClaimId=cid)
    upsert_entity(graph, "physical-printing", pid, payload, origin=ORIGIN)
    for ftype, fid, relation, ttype, tid in [("candidate-claim", cid, "materializes", "physical-printing", pid),
                                           ("physical-printing", pid, "established-by", "candidate-claim", cid),
                                           ("physical-printing", pid, "realizes", "card-release", rid)]:
        upsert_edge(graph, ftype, fid, relation, ttype, tid)
    upsert_migration(graph, dict(sourceKind="reviewed-positive-evidence", sourceId=sid,
                                disposition="established-and-mapped", targetRef=pid, reason=basis))
    chinese_dates = json.loads((BUNDLE / "chinese-release-dates-20261005.json").read_text(encoding="utf-8"))
    for observation in chinese_dates["observations"]:
        for rid, release in list(releases.items()):
            if release["setEditionId"] == observation["setEditionId"] and release.get("localNumber") in observation["numbers"]:
                admit_date(graph, catalogue, releases, prints, rid, observation["date"], observation["sourceUrl"], "2026-10-05")
    from admit_issue257_simplified_chinese_20260827 import correct_happy_set_pack_scopes
    correct_happy_set_pack_scopes(overrides)
    catalogue["meta"]["counts"]["sourceRecords"] = len(catalogue["sourceRecords"])
    catalogue["meta"]["counts"]["editionAvailabilityRecords"] = sum(row["sourceKind"] == "edition-availability-record" for row in catalogue["sourceRecords"])
    catalogue["meta"]["counts"]["releaseDateRecords"] = sum(row["sourceKind"] == "release-date-record" for row in catalogue["sourceRecords"])
    graph["entities"].sort(key=lambda row: (row["entityType"], row["entityId"]))
    graph["edges"].sort(key=lambda row: (row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"]))
    graph["migrationDispositions"].sort(key=lambda row: (row["sourceKind"], row["sourceId"]))
    graph["summary"].update(entities=len(graph["entities"]), edges=len(graph["edges"]), migrationInputs=len(graph["migrationDispositions"]))
    for kind, name in (("set-source-record", "setSourceRecords"), ("set-source-disposition", "setSourceDispositions")):
        graph["summary"][name] = sum(row["entityType"] == kind for row in graph["entities"])
    graph["summary"]["migrationDispositions"] = dict(sorted(Counter(row["disposition"] for row in graph["migrationDispositions"]).items()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    names = ["authoritative_graph.json", "set_catalogue_sources.json", "source_first_prints.json", "legacy_issue_rekeys.json", "finish_overrides.json"]
    documents = [read(name) for name in names]
    before = deepcopy(documents)
    apply(documents)
    if args.check:
        if documents != before:
            raise SystemExit("Research correction is not completely applied.")
    else:
        for name, document in zip(names, documents):
            write_json(ROOT / "verification" / name, document)
    print("Retained research integrated into canonical owners; replay is idempotent.")


if __name__ == "__main__":
    main()
