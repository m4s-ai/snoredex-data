#!/usr/bin/env python3
"""Validate the canonical model in data/: format, schema, references and domain rules.

Observational: reads data/ and, in place, the owner adjudications and the specimen register;
writes nothing. It never compares against the old pipeline's outputs.

    python scripts/check.py              # exit 0 when every rule holds, 1 otherwise
    python scripts/check.py --selftest   # each rule fires on exactly its own mutation
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FILES = ("printings", "sets", "images", "evidence", "claims")
OWNER = ROOT / "verification" / "owner_adjudications.json"
SPECIMENS = ROOT / "verification" / "specimens.json"

NONE = type(None)
S, OS, I, B, OB, L, D, OD = (str,), (str, NONE), (int,), (bool,), (bool, NONE), (list,), (dict,), (dict, NONE)
RESOLVED = ("confirmed", "contradicted")  # the verdicts that resolve a claim
GRANULARITIES = frozenset(("specimen-or-card", "product-or-set", "market-or-era", "sibling-derived",
                           "unclassified"))  # how far a claim's evidence reaches
FINISHES = frozenset(("non-holo", "holo", "reverse-holo", "mirror-holo", "unknown"))  # technical finishes
COMPLETENESS = frozenset(("owner-adjudicated", "positive-evidence-only", "pending", "not-applicable"))
MARKING_ROLES = frozenset(("print-identity", "reverse-holo-treatment", "distribution-promo"))
MAPPED, UNMAPPED = ("mapped", "mapped-by-explicit-equivalence"), ("needs-explicit-equivalence", "unmapped")
SPECIMEN_PROVIDERS = ("inspected-specimen", "cardmarket-listing-photo", "seller-listing-photo")  # was S14


def enum(*values) -> frozenset:
    return frozenset(values)


PRECISION = enum("day", "month", "year", None)
# collection -> (id field, sort field, fields); a field ending in "?" may be absent.
COLLECTIONS = {
    "printings.printings": ("itemId", "itemId", {
        "itemId": S, "identityAnchor": S, "legacyChecklistIds": L, "active": B,
        "itemKind": enum("verified-printing", "finish-candidate", "research-placeholder"),
        "progressClass": enum("current-known", "research"), "workId": OS,
        "workMappingState": enum(*MAPPED, *UNMAPPED), "setEditionId": S, "cardReleaseId": S,
        "physicalPrintingId": OS, "sourcePrintingId": OS, "finishUnitId": OS, "sourceClaimRefs": L,
        "cardName": S, "localCardName": OS, "collectorNumber": OS, "collectorNumberDenominator": OS,
        "edition": enum("1st Edition", "Unlimited", None),
        "editionAssignmentStatus": enum("assigned", "not-applicable", "unresolved"),
        # the finish-status vocabulary the table ranks (build.py STATUS_RANK)
        "finishVerificationStatus": enum("pending", "other-product", "unmapped", "marketplace-claimed",
                                         "owner-attested", "observed", "confirmed"),
        "finish": FINISHES | {None}, "finishGroupId": S, "foilPattern": OS, "markings": L, "distribution": OD,
        "cardSize": S, "errorClass": OS, "rarity": D, "completenessStatus": COMPLETENESS,
        "completenessEvidence?": D, "imageAssetId": OS, "releaseDate?": OS, "releaseDatePrecision?": PRECISION,
        "releaseApproximate?": B, "artist?": S}),
    "printings.meta": (None, None, {"dataAsOf": S, "siteGenerated": S, "previousFingerprint": OS,
                                    "legacyQuality": D}),
    "sets.localizations": ("localizationId", "localizationId", {
        "localizationId": S, "locality": S, "languageId": S, "language": S, "languageTag": S, "script": OS,
        "displayName": S, "displayOrder": I}),
    "sets.languages": ("languageCode", "displayOrder", {
        "languageCode": S, "sourceName": S, "displayName": S, "region": S, "displayOrder": I}),
    "sets.localSets": ("localSetId", "localSetId", {
        "localSetId": S, "locality": S, "localSetCode": OS, "localSetName": OS, "productKind": S,
        "identityState": S, "sourceRefs": L}),
    "sets.setEditions": ("setEditionId", "setEditionId", {
        "setEditionId": S, "localSetId": S, "localizationId": S, "identityState": S, "releaseDate": OS,
        "releaseDatePrecision": PRECISION, "releaseApproximate": B, "releaseEventId": OS}),
    "sets.works": ("workId", "workId", {"workId": S, "cardKey": S}),
    "images.assets": ("assetId", "assetId", {
        "assetId": S, "path": S, "sha256": S, "imageScope": enum("exact-printing", "card-release", "legacy-product"),
        "altTextBasis": S, "preview?": S}),
    "images.galleryImages": ("itemId", "itemId", {
        "itemId": S, "recipe": S, "mediaKind": enum("photo", "render"),
        "scope": enum("exact-printing", "representative"), "source": S, "images": L}),
    "images.artworkGroups": ("cardReleaseId", "cardReleaseId", {"cardReleaseId": S, "group": S}),
    "images.placeholders": ("id", "id", {
        "id": S, "baseItemId": S, "finish": FINISHES, "foilPattern": OS, "distribution": OS, "status": S,
        "note": OS, "sources": L}),
    "evidence.providers": ("providerId", "providerId", {
        "providerId": S, "displayName": S, "organization": OS, "homepage": OS, "category": S, "authorityTier": I,
        "coverage": S, "usedFor": L, "attribution": S, "notes": S, "hosts": L,
        "supportsAbsence?": B, "absenceScopes?": L}),  # declared so that E9, not the schema, owns them
    "evidence.printings": ("itemId", "itemId", {
        "itemId": S, "sourceLinks": L, "languageEvidence?": D, "dateSource?": OD}),
    "claims.meta": (None, None, {"legacyDatabase": D}),
    "claims.legacyProducts": ("productId", "productId", {
        "productId": I, "cardName": S, "setCode": S, "collectorNumber": OS, "setName": S, "rarity": OS,
        "variantToken": S, "variantName": OS, "variantNameSource": OS, "cardKey": OS, "market": S,
        "isCodeCard": B, "artist": OS, "artistSource": OS, "artistSourceUrl": OS, "imagePath": S,
        "imageUrl": S, "cardmarketUrl": S, "axes": L}),
    "claims.languageClaims": ("unitId", "unitId", {
        "unitId": S, "productId": I, "languageCode": S,
        "repositoryVerdict": enum("confirmed", "contradicted", "needs-manual-review", "pending", "out-of-scope"),
        "applicationStatus": enum("exists", "needs-evidence", "not-printed", "disputed", "unresolved",
                                  "out-of-scope"),
        "adjudicationId": OS, "providerId": OS, "corroborated": OB, "sourceUrl": OS, "sourceRef": OS,
        "sourceType": OS, "evidence": OS, "evidenceGranularity": GRANULARITIES | {None},
        "evidenceInference": OS, "checkedAt": OS, "editions": L}),
    "claims.releaseRows": ("rowId", "rowId", {
        "rowId": S, "productId": I, "edition": S, "releaseDate": S, "datePrecision": PRECISION - {None},
        "dateApproximate": B, "sourceProviderId": OS, "sourceUrl": OS, "sourcePage": OS, "sourceField": OS}),
    "claims.finishUnits": ("finishUnitId", "finishUnitId", {
        "finishUnitId": S, "cardName": S, "setCode": S, "collectorNumber": OS, "languageCode": S,
        "applicabilityStatus": enum("applicable", "not-applicable"),  # the finish-unit state vocabularies
        "availabilityStatus": enum("confirmed", "owner-attested", "marketplace-claimed", "pending", "not-applicable"),
        "completenessStatus": COMPLETENESS,
        "productMappingStatus": enum("confirmed", "partial", "pending", "not-applicable"),
        "patternStatus": enum("confirmed", "partial", "pending", "not-applicable"),
        "availableFinishes": L, "finishStatus": D, "unresolved": L, "products": L}),
    "claims.finishPrintings": ("printingId", "printingId", {
        "printingId": S, "productId?": I, "releaseDate?": S, "image?": OS, "sources": L, "finishUnitId?": S,
        "finish?": FINISHES, "foilPattern?": OS, "cardSize?": S,
        "verificationStatus?": enum("confirmed", "owner-attested", "marketplace-claimed", "pending"),
        "distribution?": OD, "markings?": L, "physicalPrintingId?": S}),
}


def dump(document: dict) -> str:
    """The data/ format: top-level keys in order, one record (or header object) per line."""
    line = lambda value: json.dumps(value, ensure_ascii=False)
    parts = []
    for key, value in document.items():
        if isinstance(value, list) and value:
            parts.append(f"{line(key)}: [\n" + ",\n".join(map(line, value)) + "\n]")
        else:
            parts.append(f"{line(key)}: {line(value)}")
    return "{\n" + ",\n".join(parts) + "\n}\n"


def load() -> dict:
    raw = {name: (DATA / f"{name}.json").read_bytes() for name in FILES}
    model = {}
    for name in FILES:  # a BOM is tolerated here and reported by the format rule
        try:
            model[name] = json.loads(raw[name].decode("utf-8-sig"))
        except ValueError as error:  # UnicodeDecodeError and JSONDecodeError
            raise SystemExit(f"check: data/{name}.json is not UTF-8 JSON: {error}")
    owner = json.loads(OWNER.read_text(encoding="utf-8"))
    specimens = json.loads(SPECIMENS.read_text(encoding="utf-8"))["specimens"]
    return dict(model, raw=raw, owner=owner, specimens={row["specimenId"] for row in specimens})


def rows(model: dict, name: str) -> list:
    file, collection = name.split(".")
    value = model[file].get(collection, [])
    return [value] if collection == "meta" else value


def ids(model: dict, name: str, key: str | None = None) -> set:
    return {row[key or COLLECTIONS[name][0]] for row in rows(model, name)}


def missing(pairs, targets: set) -> tuple[int, list]:
    """References that do not resolve; None means "no reference"."""
    pairs = list(pairs)
    return len(pairs), [f"{label} -> {value}" for label, value in pairs if value is not None and value not in targets]


def failing(records, test, label) -> tuple[int, list]:
    records = list(records)
    return len(records), [label(row) for row in records if test(row)]


# --- format and schema ---

def file_format(model: dict) -> tuple[int, list]:
    errors = [f"{name}.json is not in canonical form (UTF-8, LF, no BOM, one record per line)"
              for name in FILES if model["raw"][name] != dump(model[name]).encode("utf-8")]
    return len(FILES), errors


def id_order(model: dict) -> tuple[int, list]:
    errors, total = [], 0
    for name, (key, sort, _) in COLLECTIONS.items():
        if key is None:
            continue
        records = rows(model, name)
        total += len(records)
        dupes = [value for value, n in Counter(row.get(key) for row in records).items() if n > 1]
        order = [row.get(sort) for row in records]
        errors += [f"{name}: duplicate {key} {value}" for value in dupes]
        if order != sorted(order, key=lambda value: (type(value).__name__, value)):
            errors.append(f"{name}: records are not sorted by {sort}")
    return total, errors


def bad_value(value, spec) -> bool:
    if isinstance(spec, frozenset):  # a bool is not the integer it compares equal to
        return isinstance(value, bool) or not isinstance(value, (str, int, NONE)) or value not in spec
    return type(value) not in spec


def record_errors(name: str, record: dict, fields: dict) -> list:
    declared = {field.rstrip("?"): spec for field, spec in fields.items()}
    label = f"{name}:{record.get(COLLECTIONS[name][0]) if COLLECTIONS[name][0] else 'meta'}"
    errors = [f"{label}: unknown field {field}" for field in record if field not in declared]
    errors += [f"{label}: missing {field}" for field in fields if not field.endswith("?") and field not in record]
    errors += [f"{label}: {field}={record[field]!r} has the wrong type or value"
               for field, spec in declared.items() if field in record and bad_value(record[field], spec)]
    return errors


def schema(model: dict) -> tuple[int, list]:
    errors, total = [], 0
    for file in FILES:
        known = {name.split(".")[1] for name in COLLECTIONS if name.startswith(file + ".")}
        errors += [f"{file}.json: unknown collection {key}" for key in set(model[file]) - known]
        errors += [f"{file}.json: missing collection {key}" for key in known - set(model[file])]
    for name, (_, _, fields) in COLLECTIONS.items():
        for record in rows(model, name):
            total += 1
            errors += record_errors(name, record, fields)
    return total, errors


# --- mutations for --selftest (copy-on-write, so the loaded base model stays intact) ---

P, C, FP, FU = "printings.printings", "claims.languageClaims", "claims.finishPrintings", "claims.finishUnits"
RESOLVED_CLAIM = lambda c: c["repositoryVerdict"] in RESOLVED
SPECIMEN = lambda c: RESOLVED_CLAIM(c) and c["providerId"] in SPECIMEN_PROVIDERS


def edit(model: dict, name: str, pick=lambda row: True) -> dict:
    """The first record matching `pick`, copied into `model` so it can be changed."""
    file, collection = name.split(".")
    model[file] = dict(model[file])
    records = model[file][collection] = list(model[file][collection])
    index = next(i for i, row in enumerate(records) if pick(row))
    records[index] = copy.deepcopy(records[index])
    return records[index]


def change(name: str, pick=lambda row: True, **values):
    return lambda m: edit(m, name, pick).update(values)


def break_ref(source: str, field: str, pick=None):
    def mutate(m: dict) -> None:
        record = edit(m, source, pick(m) if pick else lambda row: row.get(field) is not None)
        record[field] = -1 if isinstance(record[field], int) else record[field] + "-none"  # keeps the id order
    return mutate


def add_claim(**values):
    """Append a copy of an unadjudicated claim: no finish unit or owner decision is disturbed."""
    def mutate(m: dict) -> None:
        claims = list(m["claims"][C.split(".")[1]])
        claims.append(dict(next(c for c in claims if not c["adjudicationId"]), unitId="U~", **values))
        m["claims"] = dict(m["claims"], languageClaims=claims)
    return mutate


def lone_release(m: dict):
    counts = Counter(r["cardReleaseId"] for r in rows(m, P))
    return lambda r: counts[r["cardReleaseId"]] == 1


def foreign_language(m: dict) -> None:
    unit = edit(m, FU, lambda u: u["products"] and u["completenessStatus"] != "owner-adjudicated")
    spoken = {c["languageCode"] for c in rows(m, C) if c["productId"] == unit["products"][0]["productId"]}
    unit["languageCode"] = min(ids(m, "sets.languages") - spoken)


def unverifiable_claim(m: dict) -> None:
    tier3 = next(p["providerId"] for p in rows(m, "evidence.providers") if p["authorityTier"] == 3)
    edit(m, C, lambda c: RESOLVED_CLAIM(c) and not c["corroborated"] and not SPECIMEN(c)).update(
        providerId=tier3, sourceUrl=None)


def owner_unit(m: dict) -> None:
    m["owner"] = copy.deepcopy(m["owner"])
    m["owner"]["decisions"][0]["unitId"] = "U9999"


def replace(file: str, **collections):
    return lambda m: m.update({file: dict(m[file], **{k: v(m[file][k]) for k, v in collections.items()})})


# --- references: (check, negative case); an unresolved id is reported by its own reference only ---

def pairs(model: dict, name: str, field: str):
    return ((row[COLLECTIONS[name][0]], row.get(field)) for row in rows(model, name))


# (source collection, field, target collection, target field or None for its id, negative case or None)
SIMPLE_REFS = (
    (P, "workId", "sets.works", None, lambda: break_ref(P, "workId", lone_release)),
    (P, "setEditionId", "sets.setEditions", None, None),
    (P, "imageAssetId", "images.assets", None, None),
    (P, "finishUnitId", FU, None, None),
    (P, "sourcePrintingId", FP, None, None),
    ("sets.setEditions", "localSetId", "sets.localSets", None, None),
    ("sets.setEditions", "localizationId", "sets.localizations", None, None),
    (C, "productId", "claims.legacyProducts", None, lambda: add_claim(productId=-1)),
    (C, "languageCode", "sets.languages", None, lambda: add_claim(languageCode="xx")),
    (FU, "languageCode", "sets.languages", None, None),
    (FP, "productId", "claims.legacyProducts", None, None),
    (FP, "finishUnitId", FU, None, None),
    (FP, "physicalPrintingId", P, "physicalPrintingId", None),
    ("claims.releaseRows", "productId", "claims.legacyProducts", None, None),
    ("images.galleryImages", "itemId", P, None, None),
    ("images.artworkGroups", "cardReleaseId", P, "cardReleaseId", None),
    ("images.placeholders", "baseItemId", P, None, None),
)


def simple_ref(source: str, field: str, target: str, key: str | None):
    return lambda m: missing(pairs(m, source, field), ids(m, target, key))


def provider_refs(model: dict) -> tuple[int, list]:
    found = [(r["itemId"], r["languageEvidence"]["providerId"])
             for r in rows(model, "evidence.printings") if "languageEvidence" in r]
    found += [*pairs(model, C, "providerId"), *pairs(model, "claims.releaseRows", "sourceProviderId")]
    found += [(r["printingId"], s["providerId"]) for r in rows(model, FP) for s in r["sources"]]
    return missing(found, ids(model, "evidence.providers"))


def unit_products(model: dict):
    return ((f"{u['finishUnitId']}/{p['productId']}", p["productId"], u["languageCode"])
            for u in rows(model, FU) for p in u["products"])


def product_claims(model: dict) -> tuple[int, list]:
    claims = {(c["productId"], c["languageCode"]) for c in rows(model, C)}
    known = ids(model, "claims.legacyProducts"), ids(model, "sets.languages")
    return missing(((label, (pid, code)) for label, pid, code in unit_products(model)
                    if pid in known[0] and code in known[1]), claims)


def printing_units(model: dict) -> tuple[int, list]:
    units = ids(model, FU)
    found = [(r["itemId"], r["sourcePrintingId"], r["finishUnitId"]) for r in rows(model, P)
             if r["sourcePrintingId"] and r["finishUnitId"] in units]
    found += [(r["printingId"], r["printingId"], r["finishUnitId"]) for r in rows(model, FP)
              if r.get("finishUnitId") in units]
    return len(found), [label for label, printing, unit in found if not printing.startswith(unit + "-")]


def repository_files(model: dict) -> tuple[int, list]:
    assets = rows(model, "images.assets")
    paths = [a["path"] for a in assets] + [a["preview"] for a in assets if "preview" in a]
    paths += [p for r in rows(model, "images.galleryImages") for p in [r["source"], *(i["path"] for i in r["images"])]]
    paths += [r["image"] for r in rows(model, FP) if r.get("image")]
    return len(paths), [path for path in paths if not (ROOT / path).is_file()]


def owner_links(model: dict) -> tuple[int, list]:
    """Each cited adjudication is an owner decision about the citing unit (rule 4)."""
    decisions = {d["adjudicationId"]: d["unitId"] for d in model["owner"]["decisions"]}
    cited = [(c["unitId"], c["adjudicationId"]) for c in rows(model, C) if c["adjudicationId"]]
    return len(cited), [unit for unit, adjudication in cited if decisions.get(adjudication) != unit]


def uncited_decisions(model: dict) -> tuple[int, list]:
    """Every owner decision is cited by a claim: an owner decision data/ does not carry is not applied."""
    cited = {c["adjudicationId"] for c in rows(model, C)}
    decisions = model["owner"]["decisions"]
    return len(decisions), [d["adjudicationId"] for d in decisions if d["adjudicationId"] not in cited]


def add_decision(m: dict) -> None:
    m["owner"] = copy.deepcopy(m["owner"])
    m["owner"]["decisions"].append(dict(m["owner"]["decisions"][0], adjudicationId="OA-uncited", unitId="U9999"))


def specimen_refs(model: dict) -> tuple[int, list]:
    text = "".join(model["raw"][name].decode("utf-8") for name in FILES)
    found = re.findall(r'(?:specimen:|"specimenId": ")(SPEC-\d+)', text)
    return len(found), sorted({spec for spec in found if spec not in model["specimens"]})


def unique(values) -> tuple[int, list]:
    values = list(values)
    return len(values), sorted(str(v) for v, n in Counter(values).items() if n > 1)


REFERENCES = {
    **{f"{s}.{f} -> {t}" + (f".{k}" if k else ""): (simple_ref(s, f, t, k), (case or (lambda: break_ref(s, f)))())
       for s, f, t, k, case in SIMPLE_REFS},
    "evidence.printings 1:1 printings.printings": (
        lambda m: (len(rows(m, "evidence.printings")), sorted(ids(m, P) ^ ids(m, "evidence.printings"))),
        replace("evidence", printings=lambda records: records[1:])),
    "every providerId -> evidence.providers": (provider_refs, break_ref("claims.releaseRows", "sourceProviderId")),
    "finishUnits.products.productId -> claims.legacyProducts": (
        lambda m: missing(((label, pid) for label, pid, _ in unit_products(m)), ids(m, "claims.legacyProducts")),
        lambda m: edit(m, FU, lambda u: u["products"])["products"][0].update(productId=-1)),
    "finish-unit product has a claim in the unit's language": (product_claims, foreign_language),
    "finish printing id belongs to its finish unit": (printing_units, change(
        FP, lambda r: "finishUnitId" in r, finishUnitId="F0000")),
    "image files exist in the repository": (repository_files, change(
        "images.assets", lambda a: "preview" not in a, path="images/none.png")),
    "adjudicationId -> a verification/owner_adjudications.json decision on that unit": (owner_links, owner_unit),
    "every owner decision is cited by its claim": (uncited_decisions, add_decision),
    "completenessEvidence.adjudicationId -> owner finishDecisions": (
        lambda m: missing(((r["itemId"], r["completenessEvidence"].get("adjudicationId"))
                           for r in rows(m, P) if "completenessEvidence" in r),
                          {d["adjudicationId"] for d in m["owner"]["finishDecisions"]}),
        lambda m: edit(m, P, lambda r: "completenessEvidence" in r)["completenessEvidence"].update(
            adjudicationId="OAF-none")),
    "specimen:SPEC-nnnn -> verification/specimens.json": (specimen_refs, change(
        C, SPECIMEN, sourceRef="specimen:SPEC-9999")),
    "legacyChecklistIds unique across printings": (
        lambda m: unique(legacy for r in rows(m, P) for legacy in r["legacyChecklistIds"]),
        lambda m: (lambda r: r.update(legacyChecklistIds=r["legacyChecklistIds"][:1] * 2))(
            edit(m, P, lambda r: r["legacyChecklistIds"]))),
    "one claim per product and language": (
        lambda m: unique((c["productId"], c["languageCode"]) for c in rows(m, C)), add_claim()),
}


# --- domain rules: (check, negative case) ---

def resolved(model: dict) -> list:
    return [c for c in rows(model, C) if RESOLVED_CLAIM(c)]


def expected_status(claim: dict, code_cards: set) -> str:
    """A confirmation counts only where its evidence reaches the card; code cards are out of scope."""
    if claim["productId"] in code_cards:
        return "out-of-scope"
    grain, inference = claim["evidenceGranularity"], claim["evidenceInference"]
    if claim["repositoryVerdict"] == "confirmed":
        carries = grain == "specimen-or-card" or (grain == "product-or-set" and inference == "carries")
        return "exists" if carries else "needs-evidence"
    if claim["repositoryVerdict"] == "contradicted":
        return "not-printed" if inference == "owner-adjudicated" else "disputed"
    return "unresolved"


def application_status(model: dict) -> tuple[int, list]:
    code_cards = {p["productId"] for p in rows(model, "claims.legacyProducts") if p["isCodeCard"]}
    return failing(rows(model, C), lambda c: c["applicationStatus"] != expected_status(c, code_cards),
                   lambda c: c["unitId"])


def incomplete_claim(claim: dict) -> bool:
    """A resolved claim has a provider (E2), evidence of 20+ characters, a sourceType and a granularity."""
    evidence, source_type = claim["evidence"], claim["sourceType"]
    return (not claim["providerId"] or not isinstance(evidence, str) or len(evidence) < 20
            or not isinstance(source_type, str) or not source_type.strip()
            or claim["evidenceGranularity"] not in GRANULARITIES)


def unverifiable(model: dict) -> tuple[int, list]:
    # E3: fails only with no URL AND uncorroborated AND a declared provider below tier 2
    tiers = {p["providerId"]: p["authorityTier"] for p in rows(model, "evidence.providers")}
    return failing(resolved(model), lambda c: not c["sourceUrl"] and not c["corroborated"]
                   and tiers.get(c["providerId"], 0) > 2, lambda c: c["unitId"])


def absence_authority(provider: dict) -> bool:
    # was E9; the model drops supportsAbsence (always false), so only a present non-false value fails
    return (provider.get("supportsAbsence", False) is not False or bool(provider.get("absenceScopes"))
            or provider["authorityTier"] not in (1, 2, 3, 5))


def item_kind_error(item: dict) -> bool:
    """What an item carries matches its kind (verified printing, finish candidate, research placeholder)."""
    kind, physical, progress = item["itemKind"], item["physicalPrintingId"], item["progressClass"]
    if kind == "verified-printing":
        return not physical or progress != "current-known"
    if kind == "finish-candidate":
        return physical is not None or progress != "research"
    return physical is not None or progress != "research" or item["finish"] is not None


def item_kinds(model: dict) -> tuple[int, list]:
    items = rows(model, P)
    physical = Counter(i["physicalPrintingId"] for i in items if i["itemKind"] == "verified-printing")
    count, errors = failing(items, item_kind_error, lambda i: i["itemId"])
    return count, errors + [f"physical printing projected twice: {p}" for p, n in physical.items() if n > 1]


def work_mapping(model: dict) -> tuple[int, list]:
    """The catalogue schema allOf: mapped -> workId, unmapped -> none, one mapping per card release."""
    items, by_release, errors = rows(model, P), {}, []
    for item in items:
        state = (item["workMappingState"], item["workId"])
        mapped_wrong = state[0] in MAPPED and not isinstance(state[1], str)
        if mapped_wrong or (state[0] in UNMAPPED and state[1] is not None):
            errors.append(item["itemId"])
        if by_release.setdefault(item["cardReleaseId"], state) != state:
            errors.append(f"mapping differs within {item['cardReleaseId']}")
    return len(items), errors


def marking_error(marks: list, finish: str | None) -> bool:
    """A marking has non-empty kind, role and text; a reverse-holo treatment sits only on a reverse holo."""
    return any(not isinstance(m, dict) or any(not isinstance(m.get(k), str) or not m[k] for k in ("kind", "text"))
               or m.get("role") not in MARKING_ROLES
               or (m["role"] == "reverse-holo-treatment" and finish != "reverse-holo") for m in marks)


def markings(model: dict) -> tuple[int, list]:
    marked = [(r["itemId"], r["markings"], r["finish"]) for r in rows(model, P)]
    marked += [(r["printingId"], r["markings"], r["finish"]) for r in rows(model, FP) if "markings" in r]
    return len(marked), [label for label, marks, finish in marked if marking_error(marks, finish)]


def not_applicable_units(model: dict) -> tuple[int, list]:
    """A not-applicable finish unit has no printings, nothing unresolved and only contradicted products."""
    printed = {r["finishUnitId"] for r in rows(model, P)} | {r.get("finishUnitId") for r in rows(model, FP)}
    units = [u for u in rows(model, FU) if u["applicabilityStatus"] == "not-applicable"]
    return failing(units, lambda u: u["availabilityStatus"] != "not-applicable" or u["unresolved"]
                   or u["finishUnitId"] in printed or any(p["claimStatus"] != "contradicted" for p in u["products"]),
                   lambda u: u["finishUnitId"])


def source_error(printing: dict) -> bool:
    """A finish printing cites sources, none claims absence authority, and every evidence scope is known."""
    sources = [s["source"] for s in printing["sources"]]
    return not sources or any(s.get("supportsAbsence") is True
                              or s.get("evidenceScope") not in (None, "finish-unit", "standard-set") for s in sources)


def unknown_finishes(model: dict) -> tuple[int, list]:
    """An unknown finish keeps its finish unit unresolved."""
    open_units = {u["finishUnitId"] for u in rows(model, FU) if u["unresolved"]}
    unknown = [(r["itemId"], r["finishUnitId"]) for r in rows(model, P) if r["finish"] == "unknown"]
    unknown += [(r["printingId"], r["finishUnitId"]) for r in rows(model, FP) if r.get("finish") == "unknown"]
    return len(unknown), [label for label, unit in unknown if unit not in open_units]


def decision_problem(unit: dict, decision: dict | None, printed: set) -> str | None:
    """E13: an owner finish decision names exactly the list the evidence established, rejects nothing
    still available, and never applies to a finish unit with no printing at all."""
    label, available = unit["finishUnitId"], sorted(unit["availableFinishes"])
    named = sorted((decision or {}).get("availableFinishes") or [])
    if unit["completenessStatus"] == "owner-adjudicated" and (not decision or named != available):
        return f"{label}: owner-adjudicated, decision names {named if decision else 'nothing'}, unit has {available}"
    return rejection_problem(label, decision, set(named) | set(available), printed) if decision else None


def rejection_problem(label: str, decision: dict, available: set, printed: set) -> str | None:
    rejected = set(decision.get("rejectedFinishes") or [])
    if rejected & available:
        return f"{label}: rejected finish {sorted(rejected)} is still available"
    return None if label in printed else f"{label}: adjudicated with no printing evidence at all"


def finish_decisions(model: dict) -> tuple[int, list]:
    """Owner finishDecisions, keyed by set code, number and language name, against the finish units."""
    names = {row["languageCode"]: row["sourceName"] for row in rows(model, "sets.languages")}
    decisions = {(d["setCode"], d["number"], d["language"]): d for d in model["owner"]["finishDecisions"]}
    printed = {r["finishUnitId"] for r in rows(model, P)} | {r.get("finishUnitId") for r in rows(model, FP)}
    pairs = [(u, decisions.get((u["setCode"], u["collectorNumber"], names[u["languageCode"]])))
             for u in rows(model, FU) if u["languageCode"] in names]  # an unresolved language: its reference
    problems = [decision_problem(unit, decision, printed) for unit, decision in pairs]
    return sum(decision is not None for _, decision in pairs), [p for p in problems if p]


def records(name: str, test, subset=None):
    """A rule failing every record of `name` (or `subset(model)`) that `test` rejects."""
    key = COLLECTIONS[name][0]
    return lambda m: failing(subset(m) if subset else rows(m, name), test, lambda row: row[key])


DOMAIN = {
    "rule 4: not-printed if and only if an owner adjudication is cited": (
        records(C, lambda c: (c["applicationStatus"] == "not-printed") != (c["adjudicationId"] is not None)),
        change(C, lambda c: c["adjudicationId"], applicationStatus="disputed", evidenceInference="disagreement")),
    "application status follows verdict, granularity and inference": (application_status, change(
        C, lambda c: c["applicationStatus"] == "exists", evidenceGranularity="market-or-era")),
    "resolved claims carry provider, evidence, sourceType, granularity": (
        records(C, incomplete_claim, resolved), change(C, RESOLVED_CLAIM, evidence="short")),
    "E1: sourceUrl holds a URL or nothing": (
        records(C, lambda c: c["sourceUrl"] is not None and not c["sourceUrl"].startswith("http"), resolved),
        change(C, lambda c: RESOLVED_CLAIM(c) and c["sourceUrl"], sourceUrl="see notes")),
    "E3: an uncorroborated claim without URL rests on tier 1-2": (unverifiable, unverifiable_claim),
    "E9: no external absence authority; tiers 1, 2, 3, 5": (
        records("evidence.providers", absence_authority), change("evidence.providers", absenceScopes=["regional"])),
    "S13: sourceRef holds a reference or nothing": (
        records(C, lambda c: bool(c["sourceRef"]) and not c["sourceRef"].startswith("specimen:"), resolved),
        change(C, lambda c: RESOLVED_CLAIM(c) and not SPECIMEN(c), sourceRef="a sentence")),
    "S14: specimen authority cites a specimen": (records(
        C, lambda c: c["providerId"] in SPECIMEN_PROVIDERS and not str(c["sourceRef"] or "").startswith("specimen:"),
        resolved), change(C, SPECIMEN, sourceRef=None)),
    "item kind matches what the item carries": (item_kinds, change(
        P, lambda r: r["itemKind"] == "finish-candidate", physicalPrintingId="PHYSICAL:invented")),
    "work mapping state matches workId": (work_mapping, change(P, workMappingState="unmapped")),
    "owner-adjudicated completeness carries completenessEvidence": (
        records(P, lambda r: r["completenessStatus"] == "owner-adjudicated" and "completenessEvidence" not in r),
        lambda m: edit(m, P, lambda r: "completenessEvidence" in r).pop("completenessEvidence")),
    "markings are role-structured and finish-safe": (markings, change(
        P, markings=[{"kind": "stamp", "role": "invented", "text": "x"}])),
    "not-applicable finish units carry nothing": (not_applicable_units, change(
        FU, lambda u: u["applicabilityStatus"] == "not-applicable", unresolved=["x"])),
    "finish printings cite sources, none with absence authority": (records(FP, source_error), change(FP, sources=[])),
    "an unknown finish keeps its finish unit unresolved": (unknown_finishes, change(
        FP, lambda r: "finish" in r, finish="unknown")),
    "E13: an owner finish decision closes only the list the evidence established": (finish_decisions, change(
        FU, lambda u: u["completenessStatus"] == "owner-adjudicated",
        availableFinishes=["holo", "mirror-holo", "non-holo", "reverse-holo"])),
}
RULES = {
    "format: canonical serialization": (file_format, lambda m: m.update(
        raw=dict(m["raw"], sets=m["raw"]["sets"] + b" "))),
    "format: unique ids in sorted order": (id_order, replace("sets", works=lambda works: works[::-1])),
    "schema": (schema, change("sets.works", colour="blue")),
    **REFERENCES, **DOMAIN,
}


def run(model: dict) -> dict:
    return {name: check(model) for name, (check, _) in RULES.items()}


def fired(model: dict) -> set:
    return {name for name, (_, errors) in run(model).items() if errors}


def selftest(base: dict) -> int:
    assert not fired(base), fired(base)
    for name, (_, mutate) in RULES.items():
        model = dict(base)
        mutate(model)
        if model["raw"] is base["raw"]:  # the documents changed: re-serialize them
            model["raw"] = {f: base["raw"][f] if model[f] is base[f] else dump(model[f]).encode("utf-8")
                            for f in FILES}
        assert fired(model) == {name}, (name, fired(model))
    bom = dict(base, raw=dict(base["raw"], sets=b"\xef\xbb\xbf" + base["raw"]["sets"]))  # load() tolerates it
    assert fired(bom) == {"format: canonical serialization"}, fired(bom)
    print(f"selftest ok: each of {len(RULES)} rules fires on exactly its own mutation")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true", help="mutate the loaded model, expect each rule to fire")
    args = parser.parse_args()
    model = load()
    if args.selftest:
        return selftest(model)
    results = run(model)
    for name, (count, errors) in results.items():
        print(f"{'FAIL' if errors else 'ok  '} {name}: {count} checked"
              + (f", {len(errors)} failing: {errors[:5]}" if errors else ""))
    failed = sum(bool(errors) for _, errors in results.values())
    print(f"check: {len(results) - failed} of {len(results)} rules hold")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
