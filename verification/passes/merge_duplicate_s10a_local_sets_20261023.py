"""Merge the duplicate Indonesian and Thai Dark Phantasma local sets (#431, owner-approved).

Two intake routes recorded the same product under two codes per locality: issue #258/#262
admitted Snorlax 058/071 under `S10a I` (ID) and `s10a` (TH), while the PR #375 photo route
admitted 077/071 under `s10a I` and `s10a T`. The cards themselves print `s10a I` and `s10a T`
(SPEC-0522, SPEC-0550, SPEC-0174 for ID; SPEC-0520, SPEC-0264 for TH), so those are the
canonical codes. The collection owner approved the merge in #431 on 2026-10-22.

The 058/071 print, release, edition and local set are re-keyed to the printed code; each
duplicate derived profile and set-name record folds into the canonical one; Bulbapedia's
locality index keeps its own source-native code and only its mapping target changes. Card
releases stay distinct (058 and 077 are different cards). Collector checklist state follows
through reviewed card-release routes.

Idempotent; `--check` reports pending work without writing.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
APPROVAL = "https://github.com/m4s-ai/snoredex-data/issues/431"
WORK = "Snorlax-Unfazed-Fat-Thumping-Snore"
# (locality, language, losing code, printed code, losing profile, canonical profile,
#  kept name record, dropped name record)
MERGES = [
    ("ID", "Indonesian", "S10a I", "s10a I", "SET-SRC-SF-FED4F4C57464", "SET-SRC-SF-C2E5F40A73F0",
     "SET-SRC-NAME-07374799D127", "SET-SRC-NAME-AD2883514C9B"),
    ("TH", "Thai", "s10a", "s10a T", "SET-SRC-SF-74E1378DF787", "SET-SRC-SF-9CBF36A23C34",
     "SET-SRC-NAME-EC00FB858813", "SET-SRC-NAME-81DDC5B16641"),
]


# Finish units stay keyed by the legacy Cardmarket code s10a; the printed code joins them through a
# reviewed releaseSetCode bridge naming the legacy V-token (V1 = 058, V2 = 077 in s10a).
FINISH_BRIDGES = [("058", "Indonesian", "s10a I", "V1"), ("077", "Indonesian", "s10a I", "V2"),
                  ("058", "Thai", "s10a T", "V1"), ("077", "Thai", "s10a T", "V2")]


def pending_bridges(overrides):
    present = {(o["number"], tuple(o.get("languages") or []), o.get("releaseSetCode"))
               for o in overrides["overrides"] if o["setCode"] == "s10a"}
    return [b for b in FINISH_BRIDGES if (b[0], (b[1],), b[2]) not in present]


def write_bridges(path, overrides, bridges):
    for number, language, code, variant in bridges:
        overrides["overrides"].append({"setCode": "s10a", "releaseSetCode": code, "number": number,
                                       "variant": variant, "languages": [language], "printings": []})
    text = json.dumps(overrides, ensure_ascii=False, indent=2) + "\n"
    text = text.replace('"claimFields": [\n        "date"\n      ],', '"claimFields": ["date"],')
    path.write_text(text, encoding="utf-8", newline="\n")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def id_map(locality, language, old, new):
    """Exact identifier renames for one locality; composite ids are rewritten by their parts."""
    enc_old, enc_new = old.replace(" ", "%20"), new.replace(" ", "%20")
    return [
        (f"RELEASE:{locality}:{language}:{old}:058/071:{WORK}", f"RELEASE:{locality}:{language}:{new}:058/071:{WORK}"),
        (f"{locality}:{old}:058/071:base", f"{locality}:{new}:058/071:base"),
        (f"EDITION:{locality}:{language}:{old}", f"EDITION:{locality}:{language}:{new}"),
        (f"LOCALSET:{locality}:{enc_old}", f"LOCALSET:{locality}:{enc_new}"),
    ]


def rename(value, pairs):
    """Rewrite identifiers that equal, or are delimited inside, a composite id; never free text."""
    if isinstance(value, dict):
        return {key: rename(item, pairs) for key, item in value.items()}
    if isinstance(value, list):
        return [rename(item, pairs) for item in value]
    if not isinstance(value, str):
        return value
    for old, new in pairs:
        if value == old:
            return new
        value = re.sub(rf"(?:(?<=^)|(?<=[:\x1f]))({re.escape(old)})(?=$|[:\x1f])", new, value)
    return value


def union(*lists):
    out = []
    for values in lists:
        for value in values or []:
            if value not in out:
                out.append(value)
    return out


def fold_profile(sources, losing_id, canonical_id):
    records = sources["sourceRecords"]
    losing = next((r for r in records if r["sourceRecordId"] == losing_id), None)
    if losing is None:
        return False
    canonical = next(r for r in records if r["sourceRecordId"] == canonical_id)
    raw, extra = canonical["raw"], losing["raw"]
    for field in ("printIds", "providers", "sourceUrls", "observedCollectorNumbers", "markAssetUrls", "cardImageUrls"):
        raw[field] = sorted(union(raw.get(field), extra.get(field)))
    raw["observedCoverage"] = (
        f"{raw['observedCoverage']}; merged with {losing_id} ({extra['observedCoverage']}) after the "
        f"owner-approved local-set merge {APPROVAL}"
    )
    sources["sourceRecords"] = [r for r in records if r["sourceRecordId"] != losing_id]
    return True


def keep_name_record(sources, kept_id, dropped_id, locality, new):
    records = sources["sourceRecords"]
    if not any(r["sourceRecordId"] == dropped_id for r in records):
        return False
    kept = next(r for r in records if r["sourceRecordId"] == kept_id)
    kept["raw"]["localCode"] = new
    kept["providerRecordKey"] = f"{locality}\x1f{new}\x1fname"
    sources["sourceRecords"] = [r for r in records if r["sourceRecordId"] != dropped_id]
    return True


def contextual_codes(value, locality, old, new):
    """Local code fields of this locality only; the legacy `viaLegacySetCode` stays as harvested."""
    if isinstance(value, list):
        return [contextual_codes(item, locality, old, new) for item in value]
    if not isinstance(value, dict):
        return value
    out = {key: contextual_codes(item, locality, old, new) for key, item in value.items()}
    if out.get("locality") == locality or out.get("language") == {"ID": "Indonesian", "TH": "Thai"}[locality]:
        for field in ("localCode", "localSetCode", "setCode"):
            if out.get(field) == old:
                out[field] = new
    return out


def dedupe_graph(graph):
    merged = {}
    for entity in graph["entities"]:
        key = (entity["entityType"], entity["entityId"])
        if key not in merged:
            merged[key] = entity
            continue
        kept, other = merged[key]["payload"], entity["payload"]
        for field in ("sourceRecordIds", "observedNames"):
            if field in kept or field in other:
                kept[field] = union(kept.get(field), other.get(field))
        for part, field in (("identity", "establishingClaimIds"), ("catalogue", "establishingEvidenceIds")):
            if isinstance(kept.get(part), dict) and isinstance(other.get(part), dict):
                kept[part][field] = sorted(union(kept[part].get(field), other[part].get(field)))
    graph["entities"] = list(merged.values())
    graph["edges"] = list({
        (e["fromType"], e["fromId"], e["relation"], e["toType"], e["toId"]): e for e in graph["edges"]
    }.values())
    graph["migrationDispositions"] = list({
        (row.get("sourceKind"), row.get("sourceId")): row for row in graph["migrationDispositions"]
    }.values())


def mirror_sources(graph, sources):
    """The graph mirrors each set-source record byte for byte; drop mirrors of folded records."""
    by_id = {r["sourceRecordId"]: r for r in sources["sourceRecords"]}
    kept = []
    for entity in graph["entities"]:
        if entity["entityType"] in {"set-source-record", "set-source-disposition"}:
            if entity["entityId"] not in by_id:
                continue
            if entity["entityType"] == "set-source-record":
                entity["payload"] = by_id[entity["entityId"]]
        kept.append(entity)
    graph["entities"] = kept
    ids = {e["entityId"] for e in kept}
    graph["edges"] = [e for e in graph["edges"]
                      if not (e["fromType"].startswith("set-source") and e["fromId"] not in ids)
                      and not (e["toType"].startswith("set-source") and e["toId"] not in ids)]


def normalize_stores(sources, prints):
    """Order and counts as the admission replays (e.g. integrate_rarity_finish_research_20261007) rebuild them."""
    prints["prints"].sort(key=lambda row: row["printId"])
    counts = sources["meta"]["counts"]
    kinds = [row.get("sourceKind") for row in sources["sourceRecords"]]
    counts["sourceRecords"] = len(kinds)
    counts["sourceFirstLocalSets"] = kinds.count("source-first-local-set-profile")
    counts["localSetNameRecords"] = kinds.count("local-set-name-record")


def stores_normalized(sources, prints):
    before = json.dumps([sources["meta"], [row["printId"] for row in prints["prints"]]])
    normalize_stores(sources, prints)
    return before == json.dumps([sources["meta"], [row["printId"] for row in prints["prints"]]])


def refresh_summary(graph):
    summary = graph["summary"]
    summary["entities"], summary["edges"] = len(graph["entities"]), len(graph["edges"])
    summary["cardReleases"] = sum(e["entityType"] == "card-release" for e in graph["entities"])
    summary["setSourceRecords"] = sum(e["entityType"] == "set-source-record" for e in graph["entities"])
    summary["setSourceDispositions"] = sum(e["entityType"] == "set-source-disposition" for e in graph["entities"])
    summary["migrationInputs"] = len(graph["migrationDispositions"])


def add_routes(pairs_by_locality):
    path = V / "collector_migration_routes.json"
    text = path.read_text(encoding="utf-8")
    routes = json.loads(text)
    new_rows = []
    for (old, new) in pairs_by_locality:
        if not any(row["from"] == old for row in routes["cardReleaseRekeys"]):
            new_rows.append({"from": old, "to": new, "reason": f"Owner-approved local-set merge {APPROVAL}: the card prints the canonical code."})
    stale = "retain it separately from S10a I 058/071."
    text = text.replace(stale, "the 058/071 card was later merged into the same printed s10a I set (#431).")
    if new_rows:
        head, rest = text.split('  "cardReleaseRekeys": [\n', 1)
        block, tail = rest.split("\n  ],", 1)
        rows = block.split(",\n") + ["    " + json.dumps(r, ensure_ascii=False) for r in new_rows]
        text = head + '  "cardReleaseRekeys": [\n' + ",\n".join(rows) + "\n  ]," + tail
    path.write_text(text, encoding="utf-8", newline="\n")


def main(argv):
    names = {
        "graph": V / "authoritative_graph.json", "sources": V / "set_catalogue_sources.json",
        "prints": V / "source_first_prints.json", "rekeys": V / "legacy_issue_rekeys.json",
        "specimens": V / "specimens.json", "discovery": V / "card_discovery_adapters.json",
        "names": V / "local_card_names.json",
    }
    # pairs[:2] are the release and print ids; local-set and edition ids are graph-only.
    docs = {key: read(path) for key, path in names.items()}
    pending = [m for m in MERGES if any(r["sourceRecordId"] == m[4] for r in docs["sources"]["sourceRecords"])]
    overrides_path = V / "finish_overrides.json"
    overrides = read(overrides_path)
    bridges = pending_bridges(overrides)
    normalized = stores_normalized(docs["sources"], docs["prints"])
    if "--check" in argv:
        if not normalized:
            print("pending: source store order or counts")
        for merge in pending:
            print("pending local-set merge:", merge[0], merge[2], "->", merge[3])
        for bridge in bridges:
            print("pending finish bridge:", *bridge)
        return 1 if pending or bridges or not normalized else 0
    if bridges:
        write_bridges(overrides_path, overrides, bridges)
    if not pending:
        if not normalized:
            write(names["sources"], docs["sources"])
            write(names["prints"], docs["prints"])
        return 0
    routes = []
    for locality, language, old, new, losing, canonical, kept_name, dropped_name in pending:
        pairs = id_map(locality, language, old, new) + [(losing, canonical), (dropped_name, kept_name)]
        routes.append(pairs[0])
        fold_profile(docs["sources"], losing, canonical)
        keep_name_record(docs["sources"], kept_name, dropped_name, locality, new)
        # Derived profiles name prints by id; source-native index codes stay as harvested.
        docs["sources"] = rename(docs["sources"], pairs[:2])
        for key in ("graph", "prints", "rekeys", "specimens", "discovery"):
            docs[key] = contextual_codes(rename(docs[key], pairs), locality, old, new)
        docs["names"]["releases"] = {rename(k, pairs): v for k, v in docs["names"]["releases"].items()}
    normalize_stores(docs["sources"], docs["prints"])
    dedupe_graph(docs["graph"])
    mirror_sources(docs["graph"], docs["sources"])
    refresh_summary(docs["graph"])
    for key, path in names.items():
        write(path, docs[key])
    add_routes(routes)
    for locality, _, old, new, *_ in pending:
        print(f"merged {locality} {old} -> {new}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
