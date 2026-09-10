"""Reconcile retained photo identities without losing legacy collection references."""
import json
from copy import deepcopy
from pathlib import Path
from urllib.parse import quote, urlsplit

from admit_issue257_simplified_chinese_20260827 import (
    append_unique, source_profile, upsert_edge, upsert_entity, upsert_migration,
)

ROOT = Path(__file__).resolve().parents[2]
ORIGIN = "reviewed-photo-identities-pr375"
DATE = "2026-09-10"
TARGETS = [
    ("U0170", "SPEC-0522", "s10a I", "077/071", "CHR", None, 258),
    ("U0604", "SPEC-0523", "s5a T", "093/070", "UR", None, 262),
    ("U0051", "SPEC-0518", "SV2a I", "181/165", "AR", None, 258),
    ("U0603", "SPEC-0519", "s5a I", "093/070", "UR", None, 258),
    ("U0171", "SPEC-0520", "s10a T", "077/071", "CHR", None, 262),
]


def read(name):
    return json.loads((ROOT / "verification" / name).read_text(encoding="utf-8"))


def write(name, value):
    (ROOT / "verification" / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def replace_refs(value, old, new):
    if isinstance(value, dict):
        return {k: replace_refs(v, old, new) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_refs(v, old, new) for v in value]
    return new if value == old else value


def specimen_evidence_url(specimen):
    for field in ("photographSource", "listingUrl"):
        value = specimen.get(field) or ""
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return value
    raise ValueError("specimen equivalence requires a navigable evidence URL")


def main():
    graph, prints, sources, rekeys = [read(n) for n in (
        "authoritative_graph.json", "source_first_prints.json", "set_catalogue_sources.json", "legacy_issue_rekeys.json")]
    units = {r["unitId"]: r for r in read("units.json")}
    specs = {r["specimenId"]: r for r in read("specimens.json")["specimens"]}
    for uid, sid, code, number, rarity, normalized, issue in TARGETS:
        unit, spec = units[uid], specs[sid]
        assert uid in spec["citedBy"] and unit["language"] == spec["language"]
        assert code in spec["observed"] and number in spec["observed"]
        claim = next(e["payload"] for e in graph["entities"]
                     if e["entityType"] == "candidate-claim" and e["payload"].get("sourceId") == uid)
        old_id = claim["materializedTargetId"]
        old = next(e["payload"] for e in graph["entities"] if e["entityType"] == "card-release" and e["entityId"] == old_id)
        locality, language, script = old["locality"], old["language"], old["script"]
        pid = f"{locality}:{code}:{number}:base"
        rid = f"RELEASE:{locality}:{language}:{code}:{number}:{old['work']}"
        if old_id == rid:
            upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": uid, "disposition": "linked-local-counterpart", "targetRef": rid, "targetRefs": [rid], "reason": f"issue #{issue} re-key"})
            if uid in {"U0603", "U0171"}:
                row = next(r for r in prints["prints"] if r["printId"] == pid)
                row["sourceUrl"] = spec["listingUrl"]
                if uid == "U0171":
                    row["cardImageUrl"] = None  # The supplied original has page provenance, not a remote image URL.
                profile = next(s for s in sources["sourceRecords"] if s.get("raw", {}).get("localCode") == code and s.get("raw", {}).get("locality") == locality)
                profile["raw"]["sourceUrls"] = [spec["listingUrl"]]
                profile["raw"]["cardImageUrls"] = [row["cardImageUrl"]] if row.get("cardImageUrl") else []
                upsert_entity(graph, "set-source-record", profile["sourceRecordId"], profile, origin=ORIGIN)
                next(e["payload"] for e in graph["entities"] if e["entityId"] == f"CLAIM:source-first:{pid}")["sourceRecord"] = spec["listingUrl"]
                append_unique(old["sourceRecords"], spec["listingUrl"])
            for entity in graph["entities"]:
                if entity["entityType"] == "rarity-claim" and entity["entityId"] == f"RARITYCLAIM:pr375:{pid}":
                    profile = next(s for s in sources["sourceRecords"] if s["sourceRecordId"] == entity["payload"]["sourceRecordId"])
                    entity["payload"]["sourceProvider"] = profile["provider"]
            continue
        row = next((r for r in prints["prints"] if r["printId"] == pid), None)
        if row is None:
            row = {"printId": pid, "localSetCode": code, "localNumber": number,
                   "variant": "base", "locality": locality, "language": language, "script": script,
                   "cardName": unit["cardName"], "name": unit["cardName"], "specimenId": sid,
                   "providerId": "seller-listing-photo" if spec["heldBy"] == "third-party seller" else "inspected-specimen", "sourceUrl": spec["listingUrl"],
                   "cardImageUrl": spec["photographSource"] if spec["photographSource"].startswith("https://") and spec["photographSource"] != spec["listingUrl"] else None, "markAssetUrl": None, "corroborated": False,
                   "retrievedAt": DATE, "releaseDate": None, "releaseDatePrecision": None,
                   "releaseApproximate": False,
                   "evidence": f"specimen:{sid} visibly establishes {code} {number}, {language}, and printed rarity {rarity}. Release date remains unknown."}
            prints["prints"].append(row)
        profile = next((r for r in sources["sourceRecords"] if r.get("sourceKind") == "source-first-local-set-profile"
                        and r.get("raw", {}).get("locality") == locality and r.get("raw", {}).get("localCode") == code), None)
        if profile is None:
            profile = source_profile([row])
            profile["retrieved"] = DATE
            profile["raw"]["observedCoverage"] = f"Exact card identity retained as {sid}; not an enumeration of the set"
            sources["sourceRecords"].append(profile)
        srid = profile["sourceRecordId"]
        lsid = f"LOCALSET:{locality}:{quote(code, safe='')}"
        eid = f"EDITION:{locality}:{language}:{code}"
        lid = f"LOCALIZATION:{locality}:" + ("id" if locality == "ID" else "th")
        scid = f"CLAIM:source-first:{pid}"
        upsert_entity(graph, "set-source-record", srid, profile, origin=ORIGIN)
        disp = {"sourceRecordId": srid, "disposition": "mapped", "targetRef": lsid, "reason": "retained exact card identifies its local set"}
        upsert_entity(graph, "set-source-disposition", srid, disp, origin=ORIGIN)
        upsert_edge(graph, "set-source-disposition", srid, "disposes", "set-source-record", srid)
        upsert_migration(graph, {"sourceKind": "set-catalogue-source", "sourceId": srid, "disposition": "mapped", "targetRef": lsid, "reason": disp["reason"]})
        if not any(e["entityId"] == lsid for e in graph["entities"]):
            upsert_entity(graph, "local-set", lsid, {"localSetId": lsid, "locality": locality, "localCode": code,
                          "observedNames": [], "productKind": "physical-card-set-or-product", "sourceRecordIds": [srid]}, origin=ORIGIN)
        upsert_edge(graph, "local-set", lsid, "observed-by", "set-source-record", srid)
        if not any(e["entityType"] == "set-edition" and e["entityId"] == eid for e in graph["entities"]):
            upsert_entity(graph, "set-edition", eid, {"setEditionId": eid,
                "identity": {"setEditionId": eid, "locality": locality, "language": language, "script": script,
                             "localSetCode": code, "localIdentifierKnown": True, "state": "identified", "viaLegacySetCodes": [],
                             "establishingClaimIds": [scid], "localizationId": lid},
                "catalogue": {"setEditionId": eid, "localSetId": lsid, "locality": locality, "language": language,
                              "script": script, "localCode": code, "state": "identified", "establishingEvidenceIds": [srid], "localizationId": lid}}, origin=ORIGIN)
        upsert_edge(graph, "set-edition", eid, "belongs-to", "local-set", lsid)
        upsert_edge(graph, "set-edition", eid, "localized-as", "localization", lid)
        existing = next((e["payload"] for e in graph["entities"] if e["entityType"] == "card-release" and e["entityId"] == rid), None)
        release = deepcopy(existing or old)
        for field in ("claimIds", "establishingClaimIds", "nonEstablishingClaimIds", "legacyVariants", "legacyProducts", "sourceRecords"):
            append_unique(release.setdefault(field, []), *old.get(field, []))
        append_unique(release.setdefault("claimIds", []), scid)
        append_unique(release.setdefault("establishingClaimIds", []), scid)
        append_unique(release.setdefault("sourceFirstRecordIds", []), pid)
        append_unique(release.setdefault("legacyCounterpartUnitIds", []), uid)
        append_unique(release.setdefault("sourceRecords", []), row["sourceUrl"], spec["photographSource"])
        alias = [unit["setCode"], unit["number"]]
        if alias not in release.setdefault("legacyIdentityAliases", []): release["legacyIdentityAliases"].append(alias)
        release.update(cardReleaseId=rid, setEditionId=eid, localSetCode=code, localNumber=number,
                       localIdentifierKnown=True, state="identified", viaLegacySetCode=None, viaLegacyNumber=None,
                       workMappingState="mapped-by-explicit-equivalence")
        graph["entities"] = [e for e in graph["entities"] if not (e["entityType"] in {"card-release", "catalogue-card-release-ref"} and e["entityId"] == old_id)]
        graph = replace_refs(graph, old_id, rid)
        graph["edges"] = [e for e in graph["edges"] if not (e["fromType"] == "card-release" and e["fromId"] == rid and e["relation"] in {"belongs-to", "implements"})]
        upsert_entity(graph, "card-release", rid, release, origin=ORIGIN)
        upsert_edge(graph, "card-release", rid, "belongs-to", "set-edition", eid)
        upsert_edge(graph, "card-release", rid, "implements", "work", "WORK:" + release["work"], {"state": "mapped-by-explicit-equivalence", "basis": f"exact printed identity and attacks retained in {sid}"})
        upsert_entity(graph, "candidate-claim", scid, {"claimId": scid, "claimKind": "card-release", "sourceKind": "source-first-record",
                      "sourceId": pid, "sourceRecord": row["sourceUrl"], "evidenceStatus": "confirmed", "disposition": "established-and-mapped",
                      "proposedTargetId": rid, "materializedTargetId": rid, "reason": "retained exact card identity"}, origin=ORIGIN)
        upsert_edge(graph, "candidate-claim", scid, "materializes", "card-release", rid, {"disposition": "established-and-mapped"})
        upsert_migration(graph, {"sourceKind": "source-first-record", "sourceId": pid, "disposition": "established-and-mapped", "targetRef": rid, "reason": "retained exact card identity"})
        upsert_entity(graph, "catalogue-card-release-ref", rid, {"cardReleaseId": rid, "setEditionId": eid, "collectorNumber": number, "origin": ORIGIN}, origin=ORIGIN)
        upsert_edge(graph, "catalogue-card-release-ref", rid, "belongs-to", "set-edition", eid)
        upsert_edge(graph, "catalogue-card-release-ref", rid, "references", "card-release", rid)
        question = next(q for q in rekeys["questionSets"] if q["issueNumber"] == issue)
        mapping = next((m for m in question["mappings"] if m["legacyUnitId"] == uid and m["sourceFirstRecordId"] == pid), None)
        if mapping is None:
            mapping = {"legacyUnitId": uid, "sourceFirstRecordId": pid, "assertionType": "same-work-decision", "assertedBy": "repository verification pass",
                       "assertedAt": DATE, "evidenceUrl": specimen_evidence_url(spec), "evidence": f"{sid} identifies the printed local code, number and matching attacks."}
            question["mappings"].append(mapping)
        aid = f"ASSERT:same-work:{uid}:{pid}"
        assertion = {**mapping, "assertionId": aid, "fromId": rid, "toId": "WORK:" + release["work"], "destructiveMergeAllowed": False}
        upsert_entity(graph, "equivalence-assertion", aid, assertion, origin=ORIGIN)
        for typ, target in [("card-release", rid), ("work", assertion["toId"])]: upsert_edge(graph, "equivalence-assertion", aid, "relates", typ, target, assertion)
        upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": uid, "disposition": "linked-local-counterpart", "targetRef": rid, "targetRefs": [rid], "reason": f"issue #{issue} re-key"})
        if existing is None:
            rarity_id = f"RARITYCLAIM:pr375:{pid}"
            upsert_entity(graph, "rarity-claim", rarity_id, {"rarityClaimId": rarity_id, "cardReleaseId": rid, "sourceRecordId": srid,
                          "sourceProvider": profile["provider"], "sourceVocabulary": "printed-card", "sourceNativeValue": rarity,
                          "normalizedRarityId": normalized, "sourceProductKey": spec["photographSource"], "retrievedAt": DATE}, origin=ORIGIN)
            upsert_edge(graph, "rarity-claim", rarity_id, "asserts-rarity-for", "card-release", rid)
            upsert_edge(graph, "rarity-claim", rarity_id, "observed-by", "set-source-record", srid)
        # Coalescing release references can make equivalent edges meet.
        graph["edges"] = list({(e["fromType"], e["fromId"], e["relation"], e["toType"], e["toId"]): e for e in graph["edges"]}.values())
        print(uid, "->", rid)
    prints["meta"]["counts"]["admitted"] = len(prints["prints"])
    for name, value in [("authoritative_graph.json", graph), ("source_first_prints.json", prints),
                        ("set_catalogue_sources.json", sources), ("legacy_issue_rekeys.json", rekeys)]: write(name, value)


if __name__ == "__main__": main()
