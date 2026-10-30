"""Record printed and owner-attested rarities that rested on the marketplace alone (#437).

Each claim rests on an image of the exact card whose collector line is legible, or on an explicit
collection-owner statement recorded under its own `owner-attestation` source record:

* KR m2a 136/193: the official Pokémon Korea render shows no rarity symbol (retained in
  `verification/evidence/kr-hop-snorlax-rarity-20261030/`). The claim concerns the release.
* KR xm2a 136/193 V2 (Poké Ball mirror): SPEC-0410 shows no rarity symbol.
* KR xm2a 136/193 V1 (Colorless Energy mirror): the owner attested on 2026-10-30 that it equals V2
  apart from the reverse pattern, so it prints no symbol either.
* KR xsv2a 143/165 V1 and V2 (Poké Ball / Master Ball mirror): owner-supplied photographs SPEC-0660
  and SPEC-0659 show the printed mark U. Nothing is carried over from the regular sv2a release
  (the owner's rule for `x…` Additionals).
* EN CL 33 prerelease and prerelease Staff promos: the owner ruled on 2026-10-30 that both are
  Promo. The Staff promo has no marketplace product, so the claim names its distribution kinds.

Marketplace-product claims carry the product URL as `sourceProductKey`, so the collector catalogue
applies each only to the printing mapped to that product. No-symbol values stay source-native
(`no printed rarity symbol`, no normalized id): `fixed` is reserved for fixed-deck contents.
Idempotent; `--check` reports pending records without writing.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from admit_issue257_simplified_chinese_20260827 import upsert_edge, upsert_entity, upsert_migration  # noqa: E402

GRAPH = ROOT / "verification" / "authoritative_graph.json"
PRINTS = ROOT / "verification" / "source_first_prints.json"
SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
ORIGIN = "reviewed-evidence-issue-437"
BUNDLE = "verification/evidence/kr-hop-snorlax-rarity-20261030"
RETRIEVED = "2026-10-30"
NATIVE = "no printed rarity symbol"
RENDER = "https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M2a/M2a_136.png"
DETAIL = "https://pokemoncard.co.kr/cards/detail/BS2025015136"
XM2A = "https://www.cardmarket.com/en/Pokemon/Products/Singles/MEGA-Dream-ex-Additionals/Hops-Snorlax-{}-xm2a136"
XSV2A = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Pokemon-Card-151-Additionals/Snorlax-{}-xsv2a143"
WORK = "Hops-Snorlax-Extra-Helpings-Dynamic-Press"
SNORLAX = "Snorlax-Voraciousness-Thudding-Press"
XM2A_QUOTE = "m2a 136 v1 ist bis auf die art des reverse holo komplett gleich also auch kein Symbol"
CL_QUOTE = "und ja die CL 33 ist Promo in der Prerelease und Prerelease Staff Variante"
XM2A_OWNER = "SET-SRC-OWNER-XM2A-136-V1-RARITY-20261030"
CL_OWNER = "SET-SRC-OWNER-CL-33-PROMO-RARITY-20261030"

# Owner statements get their own source records, as for the 30th Celebration rarities.
OWNER_RECORDS = [
    {"sourceRecordId": XM2A_OWNER, "localCode": "xm2a", "locality": "KR", "language": "Korean",
     "script": "Hang", "printId": "KR:xm2a:136/193:base", "number": "136/193",
     "localSetId": "LOCALSET:KR:xm2a", "statement": XM2A_QUOTE, "rarity": NATIVE,
     "evidenceRefs": ["specimen:SPEC-0437", "specimen:SPEC-0410"],
     "basis": "Owner attestation for the xm2a 136/193 V1 Colorless Energy mirror only."},
    {"sourceRecordId": CL_OWNER, "localCode": "CL", "locality": "WEST", "language": "English",
     "script": "Latn", "printId": "WEST:CL:33:base", "number": "33",
     "localSetId": "LOCALSET:WEST:CL", "statement": CL_QUOTE, "rarity": "Promo",
     "evidenceRefs": [],
     "basis": "Owner classification of the CL 33 prerelease and prerelease Staff promos only."},
]

CLAIMS = [
    {
        "rarityClaimId": f"RARITYCLAIM:issue437:m2a:136/193:{WORK}",
        "cardReleaseId": f"RELEASE:KR:Korean:m2a:136/193:{WORK}",
        "sourceRecordId": "SET-SRC-SF-EBC661CA979D",
        "sourceProductKey": RENDER,
        "supportingSourceUrls": [DETAIL],
        "evidence": ("The official Pokémon Korea render of 호브의 잠만보 m2a 136/193 shows the complete "
                     "collector line with no rarity symbol after the number. MEGA Dream ex is a "
                     "high-class pack; no fixed-deck normalization applies."),
    },
    {
        "rarityClaimId": f"RARITYCLAIM:issue437:xm2a:136/193-V2:{WORK}",
        "cardReleaseId": f"RELEASE:KR:Korean:xm2a:136/193:{WORK}",
        "sourceRecordId": "SET-SRC-SF-BE4749055DF1",
        "sourceProductKey": XM2A.format("V2"),
        "specimenIds": ["SPEC-0410"],
        "evidence": ("SPEC-0410, a complete seller photograph of the Korean xm2a V2 Poké Ball mirror "
                     "product, shows the legible collector line 136/193 with no rarity symbol after "
                     "it. Scoped to the V2 product."),
    },
    {
        "rarityClaimId": f"RARITYCLAIM:issue437:xm2a:136/193-V1:{WORK}",
        "cardReleaseId": f"RELEASE:KR:Korean:xm2a:136/193:{WORK}",
        "sourceRecordId": XM2A_OWNER,
        "sourceProvider": "owner-attestation",
        "sourceVocabulary": "owner-classification",
        "sourceProductKey": XM2A.format("V1"),
        "specimenIds": ["SPEC-0437"],
        "evidence": (f"The collection owner attested on 2026-10-30: \"{XM2A_QUOTE}\". The V1 Colorless "
                     "Energy mirror equals the V2 Poké Ball mirror (SPEC-0410) apart from the reverse "
                     "pattern, so it prints no rarity symbol. SPEC-0437 identifies the V1 card; at 480 "
                     "px its collector line is too small to read, so the claim rests on the owner."),
    },
    {
        "rarityClaimId": "RARITYCLAIM:issue437:CL:33-prerelease:Snorlax-Layabout-Clomp-Clomp-Clobber",
        "cardReleaseId": "RELEASE:WEST:English:CL:33:Snorlax-Layabout-Clomp-Clomp-Clobber",
        "sourceRecordId": CL_OWNER,
        "sourceProvider": "owner-attestation",
        "sourceVocabulary": "owner-classification",
        "sourceNativeValue": "Promo",
        "sourceProductKey": "RARITYCLAIM:owner:WEST:CL:33:prerelease:20261030",
        "distributionKinds": ["prerelease", "prerelease-staff"],
        "evidence": (f"The collection owner ruled on 2026-10-30: \"{CL_QUOTE}\". Scoped to the "
                     "prerelease and prerelease Staff printings; the regular CL 33 stays Rare."),
    },
] + [
    {
        "rarityClaimId": f"RARITYCLAIM:issue437:xsv2a:143/165-{variant}:{SNORLAX}",
        "cardReleaseId": f"RELEASE:KR:Korean:xsv2a:143/165:{SNORLAX}",
        "sourceRecordId": "SET-SRC-SF-34389B3ACFA7",
        "sourceProductKey": XSV2A.format(variant),
        "specimenIds": [specimen],
        "sourceNativeValue": "U",
        "normalizedRarityId": "uncommon",
        "evidence": (f"{specimen}, an owner-supplied photograph of the Korean sv2a 143/165 {ball} mirror, "
                     "shows the legible collector line 143/165 followed by the printed rarity mark U."),
    }
    for variant, specimen, ball in (("V1", "SPEC-0660", "Poké Ball"), ("V2", "SPEC-0659", "Master Ball"))
]


def claim_payload(row: dict) -> dict:
    defaults = {"sourceProvider": "mixed-positive-evidence", "sourceVocabulary": "printed-Korean-card",
                "sourceNativeValue": NATIVE, "normalizedRarityId": None}
    return {**defaults, **row, "retrievedAt": RETRIEVED, "evidenceBundle": BUNDLE}


def owner_record(row: dict) -> dict:
    return {
        "sourceRecordId": row["sourceRecordId"], "sourceKind": "source-first-local-set-profile",
        "provider": "owner-attestation", "providerRecordKey": row["sourceRecordId"],
        "retrieved": RETRIEVED, "sourceUrl": None,
        "raw": {"localCode": row["localCode"], "locality": row["locality"], "languages": [row["language"]],
                "scripts": [row["script"]], "printIds": [row["printId"]], "providers": ["owner-attestation"],
                "sourceUrls": [], "observedCollectorNumbers": [row["number"]],
                "observedCoverage": "owner rarity determination for one exact card",
                "assertedBy": "collection owner", "assertedAt": RETRIEVED, "statement": row["statement"],
                "rarity": row["rarity"], "basis": row["basis"], "evidenceRefs": row["evidenceRefs"]},
    }


def pending(graph: dict, sources: dict, prints: dict) -> dict:
    entities = {(row["entityType"], row["entityId"]): row["payload"] for row in graph["entities"]}
    stored = {row["sourceRecordId"]: row for row in sources["sourceRecords"]}
    migrated = {row["sourceId"] for row in graph["migrationDispositions"] if row["sourceKind"] == "set-catalogue-source"}
    m2a = next(row for row in prints["prints"] if row["printId"] == "KR:m2a:136/193:base")
    provenance = {"raritySourceUrl": RENDER, "rarityProviderId": "pokemon-card-korea", "rarityRetrievedAt": RETRIEVED}
    return {
        "records": [row for row in OWNER_RECORDS if stored.get(row["sourceRecordId"]) != owner_record(row)
                    or entities.get(("set-source-record", row["sourceRecordId"])) != owner_record(row)
                    or row["sourceRecordId"] not in migrated],
        "claims": [row for row in CLAIMS
                   if entities.get(("rarity-claim", row["rarityClaimId"])) != claim_payload(row)],
        "print": None if all(m2a.get(key) == value for key, value in provenance.items()) else (m2a, provenance),
    }


def write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def apply(graph: dict, sources: dict, todo: dict) -> None:
    for row in todo["records"]:
        record = owner_record(row)
        sources["sourceRecords"] = [old for old in sources["sourceRecords"]
                                    if old["sourceRecordId"] != record["sourceRecordId"]] + [record]
        upsert_entity(graph, "set-source-record", record["sourceRecordId"], record, origin=ORIGIN)
        upsert_entity(graph, "set-source-disposition", record["sourceRecordId"], {
            "sourceRecordId": record["sourceRecordId"], "disposition": "mapped",
            "targetRef": row["localSetId"], "reason": row["basis"]}, origin=ORIGIN)
        upsert_migration(graph, {"sourceKind": "set-catalogue-source", "sourceId": record["sourceRecordId"],
                                 "disposition": "mapped", "targetRef": row["localSetId"], "reason": row["basis"]})
        upsert_edge(graph, "set-source-disposition", record["sourceRecordId"], "disposes",
                    "set-source-record", record["sourceRecordId"])
    for row in todo["claims"]:
        upsert_entity(graph, "rarity-claim", row["rarityClaimId"], claim_payload(row), origin=ORIGIN)
        upsert_edge(graph, "rarity-claim", row["rarityClaimId"], "asserts-rarity-for", "card-release",
                    row["cardReleaseId"])
        upsert_edge(graph, "rarity-claim", row["rarityClaimId"], "observed-by", "set-source-record",
                    row["sourceRecordId"])
    # The graph writer recomputes the summary; keep the stored one consistent until it runs.
    summary = graph["summary"]
    summary["entities"], summary["edges"] = len(graph["entities"]), len(graph["edges"])
    summary["migrationInputs"] = len(graph["migrationDispositions"])
    summary["setSourceRecords"] = sum(row["entityType"] == "set-source-record" for row in graph["entities"])
    summary["setSourceDispositions"] = sum(row["sourceKind"] == "set-catalogue-source"
                                           for row in graph["migrationDispositions"])
    sources["meta"]["counts"]["sourceRecords"] = len(sources["sourceRecords"])
    sources["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        row["sourceKind"] == "source-first-local-set-profile" for row in sources["sourceRecords"])


def main(argv) -> int:
    graph, sources, prints = (json.loads(path.read_text(encoding="utf-8")) for path in (GRAPH, SOURCES, PRINTS))
    todo = pending(graph, sources, prints)
    if "--check" in argv:
        for row in todo["records"]:
            print("pending:", row["sourceRecordId"])
        for row in todo["claims"]:
            print("pending:", row["rarityClaimId"])
        if todo["print"]:
            print("pending: rarity provenance on KR:m2a:136/193:base")
        return 1 if any(todo.values()) else 0
    if todo["records"] or todo["claims"]:
        apply(graph, sources, todo)
        write(GRAPH, graph)
        write(SOURCES, sources)
    if todo["print"]:
        todo["print"][0].update(todo["print"][1])
        write(PRINTS, prints)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
