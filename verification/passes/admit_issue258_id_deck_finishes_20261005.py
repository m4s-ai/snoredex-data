"""Accept the six exact Indonesian deck finishes retained on 2026-10-02."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
BUNDLE = V / "evidence/id-targeted-research-20261002"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from admit_issue257_simplified_chinese_20260827 import upsert_entity, upsert_edge, upsert_migration
sys.path.insert(0, str(ROOT / "scripts"))
from authoritative_graph import printing_semantic_key, stable_printing_id


def main():
    sources = json.loads((V / "set_catalogue_sources.json").read_text(encoding="utf-8"))
    graph = json.loads((V / "authoritative_graph.json").read_text(encoding="utf-8"))
    observations = []
    for filename in ("deck-finish-proposals.json", "additional-deck-proposals.json"):
        observations.extend(json.loads((BUNDLE / filename).read_text(encoding="utf-8")))
    origin = "reviewed-id-deck-finish-20261005"
    accepted = []

    def ent(kind, identifier, payload):
        upsert_entity(graph, kind, identifier, payload, origin=origin)

    def edge(kind, identifier, relation, target_kind, target):
        upsert_edge(graph, kind, identifier, relation, target_kind, target)

    for observation in observations:
        code, url, excerpt = (observation[k] for k in ("localCode", "sourceUrl", "excerpt"))
        assert hashlib.sha256(excerpt.encode()).hexdigest() == observation["excerptSha256"]
        assert observation["finish"] == "non-holo" and observation["retrievedAt"] == "2026-10-02"
        numbers = observation.get("numbers", [observation.get("number")])
        releases = [e for e in graph["entities"] if e["entityType"] == "card-release"
                    and e["payload"].get("language") == "Indonesian"
                    and e["payload"].get("localSetCode") == code
                    and e["payload"].get("localNumber") in numbers]
        assert len(releases) == len(numbers)
        edition_ids = sorted({r["payload"]["setEditionId"] for r in releases})
        local_sets = {e["payload"]["catalogue"]["localSetId"] for e in graph["entities"]
                      if e["entityType"] == "set-edition" and e["entityId"] in edition_ids}
        assert len(local_sets) == 1
        lid = local_sets.pop()
        fid = f"FINISHPROFILE:{code}:ID:non-holo"
        profile_source = None
        for release in releases:
            rid, number = release["entityId"], release["payload"]["localNumber"]
            sid = f"SET-SRC-BP-{code}-{number.replace('/', '-')}-FINISH-ID-20261005"
            profile_source = profile_source or sid
            basis = (f"The retained article explicitly names the Indonesian deck and {number}, "
                     f"and states its cards lack Holofoil treatment. Existing official identity "
                     f"specimens establish the printed {code} code. Positive finish only.")
            facts = dict(cardReleaseId=rid, sourceUrl=url, finish="non-holo", edition=None,
                         foilPattern=None, markings=[], distribution=None, cardSize="unknown",
                         specimenIds=[], positiveOnly=True, completenessClaim=False, basis=basis)
            raw = dict(localCode=code, locality="ID", languages=["Indonesian"],
                       finishProfileText=excerpt, finishProfileSection="Information",
                       finishProfileClauses=[dict(verbatim=excerpt, disposition="mapped",
                                                 finish="non-holo", scope="named Indonesian deck")],
                       finishProfileUnparsedText="", evidenceBundle=str(BUNDLE.relative_to(ROOT)).replace("\\", "/"),
                       scopeObservation=observation.get("scopeExcerpt", observation.get("scope")),
                       identitySpecimens=observation["identitySpecimens"],
                       scopeBoundary="Positive exact-target finish only; no inventory closure, absence or rarity change.",
                       physicalPrintingEvidence=facts)
            source = dict(sourceRecordId=sid, sourceKind="edition-availability-record", provider="bulbapedia",
                          providerRecordKey=f"{url.rsplit('/', 1)[-1]}#Information:ID:{code}:{number}",
                          retrieved=observation["retrievedAt"], sourceUrl=url, raw=raw)
            existing = next((i for i, s in enumerate(sources["sourceRecords"]) if s["sourceRecordId"] == sid), None)
            if existing is None:
                sources["sourceRecords"].append(source)
            else:
                sources["sourceRecords"][existing] = source
            ent("set-source-record", sid, source)
            ent("set-source-disposition", sid, dict(sourceRecordId=sid, disposition="mapped", targetRef=lid, reason=basis))
            upsert_migration(graph, dict(sourceKind="set-catalogue-source", sourceId=sid,
                                        disposition="mapped", targetRef=lid, reason=basis))
            pid = stable_printing_id(printing_semantic_key(rid, facts))
            cid = f"CLAIM:reviewed-positive-evidence:{sid}"
            ent("candidate-claim", cid, dict(claimId=cid, claimKind="physical-printing", sourceKind="reviewed-positive-evidence",
                sourceId=sid, sourceRecord=url, evidenceStatus="confirmed", disposition="established-and-mapped",
                proposedTargetId=pid, materializedTargetId=pid, specimenIds=[], reason=basis))
            ent("physical-printing", pid, {k: facts[k] for k in ("cardReleaseId", "finish", "edition", "foilPattern", "markings", "distribution", "cardSize", "specimenIds")} |
                dict(physicalPrintingId=pid, errorClass=None, classificationState="classified-from-positive-evidence",
                     sourceFinishUnitId=None, sourcePrintingId=None, sourceRecordIds=[sid], establishingClaimId=cid))
            edge("candidate-claim", cid, "materializes", "physical-printing", pid)
            edge("physical-printing", pid, "established-by", "candidate-claim", cid)
            edge("physical-printing", pid, "realizes", "card-release", rid)
            upsert_migration(graph, dict(sourceKind="reviewed-positive-evidence", sourceId=sid,
                                        disposition="established-and-mapped", targetRef=pid, reason=basis))
            qid = f"PROFILEFINISHCLAIM:{code}:ID:{number}:non-holo"
            ent("profile-finish-claim", qid, dict(profileFinishClaimId=qid, finishProfileId=fid,
                cardReleaseId=rid, finish="non-holo", state="established-by-profile", closesCompleteFinishList=False))
            edge("profile-finish-claim", qid, "uses-profile", "finish-profile", fid)
            edge("profile-finish-claim", qid, "asserts-finish-for", "card-release", rid)
            if url not in release["payload"]["sourceRecords"]:
                release["payload"]["sourceRecords"].append(url)
            accepted.append(dict(localCode=code, number=number, sourceRecordId=sid, physicalPrintingId=pid))
        ent("finish-profile", fid, dict(finishProfileId=fid, localSetId=lid, setEditionIds=edition_ids,
            languageScope=["Indonesian"], scopePrecision="scoped", closedWithinScope=False,
            evidenceScope="ordinary cards in the named Indonesian deck", sourceRecordId=profile_source,
            sourceStatement=excerpt, rules=[dict(finishProfileRuleId=fid + ":all", priority=10,
                effect="include", finish="non-holo", condition=dict(localSetCode=code), sourceRecordId=profile_source)]))
        edge("finish-profile", fid, "supported-by", "set-source-record", profile_source)
        for edition in edition_ids:
            edge("finish-profile", fid, "scoped-to", "set-edition", edition)
    assert len(accepted) == 6
    sources["meta"]["counts"]["sourceRecords"] = len(sources["sourceRecords"])
    sources["meta"]["counts"]["editionAvailabilityRecords"] = sum(s["sourceKind"] == "edition-availability-record" for s in sources["sourceRecords"])
    for filename, data in (("set_catalogue_sources.json", sources), ("authoritative_graph.json", graph)):
        (V / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    journal = V / "evidence.jsonl"
    if not any(json.loads(line).get("batchId") == origin for line in journal.read_text(encoding="utf-8").splitlines()):
        with journal.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(dict(at="2026-10-05", batchId=origin, source="bulbapedia",
                retrievedAt="2026-10-02", evidenceBundle=str(BUNDLE.relative_to(ROOT)).replace("\\", "/"),
                language="Indonesian", finish="non-holo", positiveOnly=True, completenessClaim=False,
                accepted=accepted), ensure_ascii=False) + "\n")
    print(json.dumps(accepted, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
