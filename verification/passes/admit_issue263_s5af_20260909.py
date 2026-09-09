"""Admit the owner-supplied 52Poke s5a F 093/070 identity without inferring finish."""
import json
from copy import deepcopy
from pathlib import Path
import admit_issue263_traditional_chinese_20260828 as tw

ROOT = Path(__file__).resolve().parents[2]
DATE = "2026-09-09"
SOURCE = "https://wiki.52poke.com/index.php?title=卡比兽（S4）&oldid=2150661"
ROW = {
    "printId": "TW:s5a F:093/070:base", "localSetCode": "s5a F", "localNumber": "093/070",
    "localSetName": "雙璧戰士", "variant": "base", "locality": "TW", "language": "T-Chinese", "script": "Hant",
    "cardName": "Snorlax", "name": "卡比獸", "work": "Snorlax-Gormandize-Body-Slam",
    "rarity": ["UR", None], "legacy": ["U0602"], "specimenId": "SPEC-0489",
    "providerId": "52poke", "sourceUrl": SOURCE, "corroborated": False,
    "cardImageUrl": "https://s1.52poke.com/wiki/1/17/S5aF093.jpg", "markAssetUrl": None,
    "releaseDate": "2021-04-02", "releaseDatePrecision": "day", "releaseApproximate": False,
    "retrievedAt": DATE,
    "catchUpOf": "Exact s5a 093 Snorlax: Gormandize, Body Slam 100, HP130, Saki Hayashiro and gold illustration.",
    "evidence": "52Poke revision 2150661 explicitly lists Traditional Chinese 雙璧戰士 093/070 UR, 2021-04-02, Saki Hayashiro. Owner-supplied SPEC-0489 visibly reads s5a F, 093/070 UR, 卡比獸, 積食 and 泰山壓頂 100. No physical finish is inferred.",
}

def reproject_prior_products(graph):
    """Replay reviewed TW rekeys without replacing later claim/finish evidence."""
    existing = {r["printId"]: r for r in tw.read(tw.PRINTS)["prints"]}
    rows = tw.official_rows() + tw.enrich_photo_rows() + tw.supplemental_rows(existing)
    profiles = tw.apply_profiles(tw.read(tw.SET_SOURCES), rows)
    units = {r["unitId"]: r for r in tw.read(tw.UNITS)}
    replay, _ = tw.apply_graph(deepcopy(graph), profiles, rows, units)
    products = {e["entityId"]: e["payload"]["cardReleaseIds"] for e in replay["entities"]
                if e["entityType"] == "legacy-cardmarket-product"}
    for entity in graph["entities"]:
        if entity["entityType"] == "legacy-cardmarket-product":
            entity["payload"]["cardReleaseIds"] = products[entity["entityId"]]


def main():
    prints = tw.read(tw.PRINTS)
    by_id = {r["printId"]: r for r in prints["prints"]}
    by_id[ROW["printId"]] = tw.persisted_source_row(ROW)
    prints["prints"] = sorted(by_id.values(), key=lambda r: r["printId"])
    prints["meta"]["generated"] = DATE
    prints["meta"]["counts"]["admitted"] = len(by_id)
    sources = tw.read(tw.SET_SOURCES)
    profiles = tw.apply_profiles(sources, [ROW])
    profile = profiles[ROW["localSetCode"]]
    profile["retrieved"] = DATE
    profile["raw"]["localName"] = "雙璧戰士"
    graph = tw.read(tw.GRAPH)
    units = {r["unitId"]: r for r in tw.read(tw.UNITS)}
    claim = "CLAIM:source-first:" + ROW["printId"]
    tw.apply_set_graph(graph, profile, ROW["localSetCode"], [claim])
    tw.apply_release_group(graph, profile, [ROW], units)
    reproject_prior_products(graph)
    rid = tw.release_id(ROW)
    mapping = {"legacyUnitId": "U0602", "sourceFirstRecordId": ROW["printId"],
               "assertionType": "same-work-decision", "assertedBy": "repository verification pass",
               "assertedAt": DATE, "evidenceUrl": SOURCE, "evidence": "The exact Traditional Chinese card identity and printed attacks establish this local counterpart without merging release identities."}
    aid = "ASSERT:same-work:U0602:" + ROW["printId"]
    assertion = {**mapping, "assertionId": aid, "fromId": rid, "toId": "WORK:" + ROW["work"], "destructiveMergeAllowed": False}
    tw.upsert_entity(graph, "equivalence-assertion", aid, assertion, origin=tw.ORIGIN)
    tw.upsert_edge(graph, "equivalence-assertion", aid, "relates", "card-release", rid, assertion)
    tw.upsert_edge(graph, "equivalence-assertion", aid, "relates", "work", assertion["toId"], assertion)
    tw.upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": "U0602", "disposition": "linked-local-counterpart", "targetRef": rid, "targetRefs": [rid], "reason": "issue #263 re-key"})
    rekeys = tw.read(tw.REKEYS)
    question = next(q for q in rekeys["questionSets"] if q["issueNumber"] == 263)
    question["mappings"] = sorted([r for r in question["mappings"] if r["legacyUnitId"] != "U0602"] + [mapping], key=lambda r: r["legacyUnitId"])
    for path, data in [(tw.PRINTS, prints), (tw.SET_SOURCES, sources), (tw.REKEYS, rekeys), (tw.GRAPH, graph)]:
        tw.write(path, data)
    print("Admitted s5a F 093/070 and retained U0602 provenance; finish remains unasserted.")

if __name__ == "__main__":
    main()
