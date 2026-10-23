"""Apply the 2026-10-23 day-precision release-date research to the reviewed-date owner.

Fifty catalogue items carried only a month or a year. The research bundle
`verification/evidence/release-dates-20261023/findings.json` accounts for every one of them:
ten carry a market-specific date with a retained source, forty stay unresolved with their
attempts and next lead. This pass appends the ten as item-scoped rows to
`confirmed_release_overrides.json` and declares one date-only capability surface per provider,
so each new source routes to exactly one reviewed surface.

A date is applied only for the market its source names, as the availability or debut date
that source states; it is never borrowed from another language or channel. Unresolved items
keep their current value: an unsuccessful search establishes nothing.

Idempotent; `--check` reports pending rows and surfaces without writing.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
BUNDLE = "verification/evidence/release-dates-20261023"
sys.path.insert(0, str(ROOT / "scripts"))
from source_registry import PROVIDERS, canonical_url  # noqa: E402

LOCALITY = {"KR": ("KR", "Korean", "Hang"), "WEST:es-ES": ("WEST", "Spanish", "Latn"),
            "WEST:de": ("WEST", "German", "Latn"), "WEST:it": ("WEST", "Italian", "Latn"),
            "WEST:fr": ("WEST", "French", "Latn")}
SURFACE = "{}-reviewed-dates-20261023"
RAW_RETENTION = ("Retain the exact source-native date excerpt, acquisition URL, retrieval date, the "
                 "retained file's SHA-256 and the as-fetched SHA-256. Only individually reviewed "
                 "date fields are covered; no acquisition adapter is asserted.")
OUTSIDE_SCOPE = ["other pages, products or campaigns", "other markets or languages",
                 "unsupported finer precision or other shipment/reprint waves",
                 "card existence, identity or membership", "rarity or physical finish",
                 "absence or completeness"]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def render(document):
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def found(findings):
    return [row for row in findings["findings"] if row["status"] == "found"]


def reviewed_row(finding, item):
    return {
        "itemId": item["itemId"],
        "cardReleaseId": item["cardReleaseId"],
        "physicalPrintingId": item["physicalPrintingId"],
        "localizationId": item["localizationId"],
        "sourcePrintingId": item["sourcePrintingId"],
        "legacyChecklistIds": item["legacyChecklistIds"],
        "releaseDate": finding["value"],
        "releaseDatePrecision": finding["precision"],
        "releaseApproximate": False,
        "basis": finding["identityMatch"],
        "sources": [{
            "providerId": source["providerId"],
            "url": source["url"],
            "retrievedAt": source["retrievedAt"],
            "evidencePath": f"{BUNDLE}/findings.json",
            "sourceRef": f"{BUNDLE}/{source['retainedPath']}",
        } for source in finding["sources"]],
    }


def apply_dates(overrides, catalogue, findings):
    items = {row["itemId"]: row for row in catalogue["items"]}
    rows = overrides["releaseDates"]["reviewedItems"]
    index = {row["itemId"]: n for n, row in enumerate(rows)}
    changed = []
    for finding in found(findings):
        row = reviewed_row(finding, items[finding["itemId"]])
        if finding["itemId"] in index:
            if rows[index[finding["itemId"]]] != row:
                raise ValueError(f"reviewed date already differs: {finding['itemId']}")
            continue
        rows.append(row)
        changed.append(finding["itemId"])
    return changed


def observation_pair(surface_id, finding, source, edge_id):
    slug = finding["itemId"][5:13]
    record = {
        "sourceId": f"{surface_id}-{slug}",
        "sourceUrl": source["url"],
        "retrievedAt": source["retrievedAt"],
        "captureMethod": source["captureForm"],
        "responseSha256": source["originalSha256"],
        "responseHashScope": "file as fetched, before line-ending normalization",
        "retainedSha256": source["sha256"],
        "retainedPath": f"{BUNDLE}/{source['retainedPath']}",
        "excerpt": source["excerpt"],
        "excerptSha256": hashlib.sha256(source["excerpt"].encode("utf-8")).hexdigest(),
        "excerptHashScope": "UTF-8 bytes of the excerpt",
        "nativeQualifier": source["nativeQualifier"],
        "date": finding["value"], "precision": finding["precision"], "approximate": False,
        "field": "source-native availability date",
        "scope": finding["identityMatch"],
        "limits": "Date only, for the named market and product; other markets, channels, finishes and card identity are outside scope.",
    }
    base = {"surfaceId": surface_id, "queryUrl": source["url"], "retrievedAt": source["retrievedAt"],
            "fixtureRef": {"kind": "inline-record", "record": record}}
    challenge = (f"The source dates {source['nativeQualifier']} only; it transfers to no other "
                 "market, language, channel, finish or finer precision.")
    return [
        {"observationId": f"obs-{surface_id}-{slug}", **base, "kind": "known-positive",
         "queryParameters": {"field": "source-native availability date",
                             "nativeQualifier": source["nativeQualifier"]},
         "expectedIdentifiers": [finding["value"]], "validatesEdges": [edge_id],
         "outcome": finding["identityMatch"]},
        {"observationId": f"obs-{surface_id}-{slug}-boundary", **base, "kind": "out-of-scope-challenge",
         "queryParameters": {"challenge": "unsupported date/precision/locality transfer"},
         "expectedIdentifiers": [finding["value"]], "validatesEdges": [edge_id], "outcome": challenge},
    ], challenge


def edge(surface_id, finding, item, challenge):
    slug = finding["itemId"][5:13]
    locality = item["localizationId"].split(":", 1)[1]
    region, language, script = LOCALITY["KR" if locality.startswith("KR:") else locality]
    return {
        "edgeId": f"{surface_id}-{slug}-positive",
        "coverage": {"localities": [region], "languages": [language], "scripts": [script],
                     "productCategories": ["product"],
                     "timeRange": {"start": finding["value"], "end": finding["value"],
                                   "basis": "Only the exact retained source-native date at its stated precision: "
                                            + finding["identityMatch"]}},
        "positiveEvidenceCapabilities": ["date", "release-date"],
        "exhaustive": False,
        "absenceCapability": {"enabled": False, "dimensions": [], "exactScopes": [],
                              "rationale": "An explicit retained native date establishes only its matching already-known release scope. Missing rows, fields, markets and finer precision remain unknown."},
        "knownPositiveObservationId": f"obs-{surface_id}-{slug}",
        "outOfScopeChallengeObservationId": f"obs-{surface_id}-{slug}-boundary",
        "boundary": {"outsideScope": OUTSIDE_SCOPE, "zeroResultMeans": "unknown", "challenge": challenge},
    }


def surfaces(catalogue, findings):
    items = {row["itemId"]: row for row in catalogue["items"]}
    by_provider = {}
    for finding in found(findings):
        for source in finding["sources"]:
            surface_id = SURFACE.format(source["providerId"])
            entry = by_provider.setdefault(source["providerId"], {"edges": [], "observations": [], "urls": set()})
            edge_id = f"{surface_id}-{finding['itemId'][5:13]}-positive"
            pair, challenge = observation_pair(surface_id, finding, source, edge_id)
            entry["observations"] += pair
            entry["edges"].append(edge(surface_id, finding, items[finding["itemId"]], challenge))
            entry["urls"].add(canonical_url(source["url"]))
    result = []
    for provider_id, entry in sorted(by_provider.items()):
        endpoint = sorted(entry["urls"])[0]
        result.append(({
            "surfaceId": SURFACE.format(provider_id), "providerId": provider_id,
            "label": f"Reviewed day/month release dates of 2026-10-23 ({provider_id})",
            "match": {"urlPrefixes": sorted(entry["urls"]), "nonUrlEvidenceIds": []},
            "state": "active", "failureState": None, "accessMode": "manual", "adapterState": "not-applicable",
            "lastCheckedAt": "2026-10-23",
            "freshnessPolicy": "Only individually retained native date fields, acquisition metadata and separate file/excerpt hashes. Re-review changed sources or expanded scope. No automatic acquisition adapter, completeness or finer precision is inferred.",
            "query": {"method": "MANUAL", "endpoint": endpoint, "parameters": [],
                      "pagination": "not paginated; individually reviewed source fields only",
                      "expectedIdentifiers": ["exact named product or campaign",
                                              "source-native locality/language qualifier",
                                              "source-native availability field"]},
            "finishCapability": {"mode": "none", "vocabulary": [],
                                 "publicationForm": "date excerpt only; adjacent card or finish vocabulary confers no capability",
                                 "closedWithinScope": False},
            "coverageEdges": entry["edges"],
        }, entry["observations"]))
    return result


def apply_capabilities(capabilities, catalogue, findings):
    registry = {provider["providerId"]: provider for provider in PROVIDERS}
    known = {provider["providerId"] for provider in capabilities["providers"]}
    changed = []
    for surface, observations in surfaces(catalogue, findings):
        provider_id = surface["providerId"]
        if provider_id not in known:
            registered = registry[provider_id]
            capabilities["providers"].append({
                "providerId": provider_id, "operator": registered["organization"],
                "authorityTier": registered["authorityTier"],
                "licenseOrTerms": registered["licenseOrTerms"], "rawRetention": RAW_RETENTION,
            })
            known.add(provider_id)
            changed.append(f"provider {provider_id}")
        if not any(row["surfaceId"] == surface["surfaceId"] for row in capabilities["surfaces"]):
            capabilities["surfaces"].append(surface)
            changed.append(f"surface {surface['surfaceId']}")
        present = {row["observationId"] for row in capabilities["observations"]}
        capabilities["observations"] += [row for row in observations if row["observationId"] not in present]
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="report only; write nothing")
    args = parser.parse_args(argv)
    findings = read(ROOT / BUNDLE / "findings.json")
    catalogue = read(ROOT / "collector_catalogue.json")
    overrides_path, capabilities_path = V / "confirmed_release_overrides.json", V / "source_capabilities.json"
    overrides, capabilities = read(overrides_path), read(capabilities_path)
    dates = apply_dates(overrides, catalogue, findings)
    declared = apply_capabilities(capabilities, catalogue, findings)
    for line in [f"date {item}" for item in dates] + declared:
        print(("pending: " if args.check else "") + line)
    if args.check:
        return 1 if dates or declared else 0
    if dates:
        overrides_path.write_text(render(overrides), encoding="utf-8", newline="\n")
    if declared:
        capabilities_path.write_text(render(capabilities), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
