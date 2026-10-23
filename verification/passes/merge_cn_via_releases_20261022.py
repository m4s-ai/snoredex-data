"""Merge Simplified-Chinese via-releases into their reviewed CN counterparts (owner decision 2026-10-22).

Issue #257 already maps each legacy unit below to an exact CN source-first release, but the
legacy Cardmarket claim still materialized a separate `via-…:unknown-local-set` release that
carried the Japanese harvest date. The collection owner decided on 2026-10-22 that these are
the same physical CN prints: the legacy claim, its finish printings and its Cardmarket product
now attach to the identified release, following the PR #375 reconciliation path. The release
date then comes from the CN source-first row, never from the Japanese product.

Idempotent: a second run finds no via-release and changes nothing. `--check` reports pending
work without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
ISSUE = 257
DECISION = "owner decision 2026-10-22: merge the S-Chinese via-release into the identified CN print"
ROUTES = V / "collector_migration_routes.json"
OVERRIDES = V / "finish_overrides.json"
# Finish units stay keyed by the legacy Cardmarket code. The reviewed releaseSetCode bridge lets
# a specimen of the identified CN print join that unit instead of projecting a second printing.
# s4 84 needs none: its counterpart CS2aC 086 is a finish unit of its own.
FINISH_BRIDGES = [("sH", "038", "CS2DaC", None), ("sI100", "341", "CS4DaC", "V1"),
                  ("sI100", "342", "CS4DaC", "V2"), ("svIba", "046", "CSVSC", None)]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def append_unique(values, *items):
    for item in items:
        if item not in values:
            values.append(item)


def replace_refs(value, old, new):
    if isinstance(value, dict):
        return {k: replace_refs(v, old, new) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_refs(v, old, new) for v in value]
    return new if value == old else value


def merge_targets(graph, rekeys):
    """Yield (legacy unit, via release id, identified release id) still awaiting the merge."""
    entities = {(e["entityType"], e["entityId"]): e["payload"] for e in graph["entities"]}
    question = next(q for q in rekeys["questionSets"] if q["issueNumber"] == ISSUE)
    for mapping in question["mappings"]:
        uid = mapping["legacyUnitId"]
        legacy = entities.get(("candidate-claim", f"CLAIM:legacy:{uid}"))
        source = entities.get(("candidate-claim", f"CLAIM:source-first:{mapping['sourceFirstRecordId']}"))
        old_id = (legacy or {}).get("materializedTargetId") or ""
        rid = (source or {}).get("materializedTargetId")
        if ":unknown-local-set:" in old_id and rid and rid != old_id:
            yield uid, old_id, rid


def merge(graph, uid, old_id, rid):
    payloads = {e["entityId"]: e["payload"] for e in graph["entities"] if e["entityType"] == "card-release"}
    old, release = payloads[old_id], payloads[rid]
    for field in ("claimIds", "establishingClaimIds", "nonEstablishingClaimIds",
                  "legacyVariants", "legacyProducts", "sourceRecords"):
        append_unique(release.setdefault(field, []), *old.get(field, []))
    for field in ("claimIds", "establishingClaimIds", "sourceRecords"):
        # Admission replays (e.g. integrate_rarity_finish_research_20261007) rebuild these sorted.
        release[field] = sorted(release[field])
    append_unique(release.setdefault("legacyCounterpartUnitIds", []), uid)
    alias = [old["viaLegacySetCode"], old["viaLegacyNumber"]]
    if alias not in release.setdefault("legacyIdentityAliases", []):
        release["legacyIdentityAliases"].append(alias)
    old_edition = old["setEditionId"]
    graph["entities"] = [
        e for e in graph["entities"]
        if not (e["entityType"] in {"card-release", "catalogue-card-release-ref"} and e["entityId"] == old_id)
    ]
    # The identified release keeps its own Work and edition edges; the via-release's are dropped.
    graph["edges"] = [
        e for e in graph["edges"]
        if not (e["fromType"] == "card-release" and e["fromId"] == old_id
                and e["relation"] in {"belongs-to", "implements"})
    ]
    merged = replace_refs({k: v for k, v in graph.items()}, old_id, rid)
    graph.clear()
    graph.update(merged)
    graph["edges"] = list({
        (e["fromType"], e["fromId"], e["relation"], e["toType"], e["toId"]): e for e in graph["edges"]
    }.values())
    for entity in graph["entities"]:
        if entity["entityType"] == "candidate-claim" and entity["entityId"] == f"CLAIM:legacy:{uid}":
            entity["payload"]["reason"] = DECISION
    for row in graph["migrationDispositions"]:
        if row.get("sourceKind") == "legacy-language-unit" and row.get("sourceId") == uid:
            row["reason"] = DECISION
    return old_edition


def write_routes(new_rows):
    """Append rows to cardReleaseRekeys in place, keeping the file's hand-reviewed layout."""
    text = ROUTES.read_text(encoding="utf-8")
    head, rest = text.split('  "cardReleaseRekeys": [\n', 1)
    block, tail = rest.split("\n  ],", 1)
    rows = block.split(",\n") + ["    " + json.dumps(r, ensure_ascii=False) for r in new_rows]
    ROUTES.write_text(head + '  "cardReleaseRekeys": [\n' + ",\n".join(rows) + "\n  ]," + tail,
                      encoding="utf-8", newline="\n")


def refresh_summary(graph):
    summary = graph["summary"]
    summary["entities"], summary["edges"] = len(graph["entities"]), len(graph["edges"])
    summary["cardReleases"] = sum(e["entityType"] == "card-release" for e in graph["entities"])


def pending_bridges(overrides):
    present = {(o["setCode"], o["number"], o.get("releaseSetCode"), o.get("variant"))
               for o in overrides["overrides"] if o.get("languages") == ["S-Chinese"]}
    return [b for b in FINISH_BRIDGES if b not in present]


def write_bridges(overrides, bridges):
    for set_code, number, release_code, variant in bridges:
        bridge = {"setCode": set_code, "releaseSetCode": release_code, "number": number}
        if variant:
            bridge["variant"] = variant
        overrides["overrides"].append({**bridge, "languages": ["S-Chinese"], "printings": []})
    text = json.dumps(overrides, ensure_ascii=False, indent=2) + "\n"
    # The store keeps one hand-written compact list; preserve it byte for byte.
    text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
    OVERRIDES.write_text(text, encoding="utf-8", newline="\n")


def sort_merged_lists(graph, rekeys):
    """Release ids already merged by this pass whose claim/source lists are not yet sorted."""
    question = next(q for q in rekeys["questionSets"] if q["issueNumber"] == ISSUE)
    sources = {f"CLAIM:source-first:{m['sourceFirstRecordId']}" for m in question["mappings"]}
    claims = {e["entityId"]: e["payload"] for e in graph["entities"] if e["entityId"] in sources}
    ids = {c.get("materializedTargetId") for c in claims.values()}
    pending = []
    for entity in graph["entities"]:
        payload = entity["payload"]
        merged = entity["entityType"] == "card-release" and entity["entityId"] in ids \
            and payload.get("legacyIdentityAliases")
        if merged and any(payload.get(f, []) != sorted(payload.get(f, []))
                          for f in ("claimIds", "establishingClaimIds", "sourceRecords")):
            pending.append(payload)
    return pending


def route(old_id, rid):
    return {"from": old_id, "to": rid, "reason": f"Issue #{ISSUE} re-key; {DECISION}."}


def main(argv):
    check = "--check" in argv
    graph, rekeys, routes = read(V / "authoritative_graph.json"), read(V / "legacy_issue_rekeys.json"), read(ROUTES)
    overrides = read(OVERRIDES)
    bridges = pending_bridges(overrides)
    targets = list(merge_targets(graph, rekeys))
    unsorted = sort_merged_lists(graph, rekeys)
    pending_routes = [(o, r) for _, o, r in targets if not any(x["from"] == o for x in routes["cardReleaseRekeys"])]
    if check:
        for uid, old_id, rid in targets:
            print(f"pending: {uid} {old_id} -> {rid}")
        for bridge in bridges:
            print("pending finish bridge:", *bridge)
        if unsorted:
            print("pending: unsorted merged release lists")
        return 1 if targets or pending_routes or bridges or unsorted else 0
    for uid, old_id, rid in targets:
        merge(graph, uid, old_id, rid)
        print(uid, old_id, "->", rid)
    for payload in unsorted:
        for field in ("claimIds", "establishingClaimIds", "sourceRecords"):
            payload[field] = sorted(payload.get(field, []))
    if targets or unsorted:
        refresh_summary(graph)
        write(V / "authoritative_graph.json", graph)
    if pending_routes:
        write_routes([route(o, r) for o, r in pending_routes])
    if bridges:
        write_bridges(overrides, bridges)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
