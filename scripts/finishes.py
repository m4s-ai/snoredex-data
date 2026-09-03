# -*- coding: utf-8 -*-
"""Build the finish-verification layer and attach product summaries to the main data.

The authoritative finish unit is (set code, collector number, language), because
TCGdex normal/holo/reverse flags describe the card rather than Cardmarket's opaque
V1/V2/V3 product split. Curated overrides map special printings to those products.

Only positive availability is asserted. A false or missing upstream flag becomes
``pending`` here, never proof that a printing does not exist.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CARDS_PATH = ROOT / "snorlax_cards.json"
UNITS_PATH = ROOT / "verification" / "units.json"
OVERRIDES_PATH = ROOT / "verification" / "finish_overrides.json"
SPECIMENS_PATH = ROOT / "verification" / "specimens.json"
ADJUDICATIONS_PATH = ROOT / "verification" / "owner_adjudications.json"
OUTPUT_PATH = ROOT / "verification" / "finish_units.json"
REVIEW_JSON_PATH = ROOT / "verification" / "FINISH_REVIEW.json"
REVIEW_CSV_PATH = ROOT / "verification" / "FINISH_REVIEW.csv"
ANALYSIS_PATH = ROOT / "analysis_finishes.json"
CACHE_DIR = ROOT / "verification" / "cache" / "finish-tcgdex"
SNAPSHOT_PATH = ROOT / "verification" / "finish_tcgdex_snapshot.json"
REFRESH_CANDIDATE_PATH = CACHE_DIR / "refresh-candidate.json"
REFRESH_CANDIDATE_SCHEMA = "snoredex-tcgdex-refresh/1"

FINISHES = ("non-holo", "holo", "reverse-holo", "mirror-holo")
FOIL_PATTERN_ALIASES = {
    "poke ball mirror": "poke-ball",
    "poké ball mirror": "poke-ball",
    "master ball mirror": "master-ball",
}
STATUS_RANK = {"pending": 0, "marketplace-claimed": 1, "owner-attested": 2, "confirmed": 3}
LANG_ORDER = (
    "English",
    "French",
    "German",
    "Italian",
    "Spanish",
    "Portuguese",
    "Dutch",
    "Polish",
    "Russian",
    "Japanese",
    "Korean",
    "T-Chinese",
    "S-Chinese",
    "Indonesian",
    "Thai",
    "Czech",
    "Hungarian",
)
LANG_RANK = {language: index for index, language in enumerate(LANG_ORDER)}


def read_json(path: Path) -> Any:
    # Tolerate historical PowerShell 5.1 BOM output; all active writers now emit UTF-8 no-BOM.
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def rendered_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def latest_input_date(*documents: Any) -> str:
    keys = {"checkedAt", "decidedAt", "generated", "lastUpdated", "recordedAt", "retrievedAt"}
    dates: list[str] = []
    stack = list(documents)
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            for key, item in value.items():
                if key in keys and isinstance(item, str) and re.match(r"^\d{4}-\d{2}-\d{2}", item):
                    dates.append(item[:10])
                elif isinstance(item, (dict, list)):
                    stack.append(item)
        elif isinstance(value, list):
            stack.extend(value)
    if not dates:
        raise ValueError("finish inputs contain no dated evidence")
    return max(dates)


def variant_token(value: dict[str, Any]) -> str:
    return str(value.get("variantToken") or value.get("variant") or "base")


def group_key(value: dict[str, Any]) -> tuple[str, str, str]:
    return (str(value.get("setCode") or ""), str(value.get("number") or ""), str(value["language"]))


def group_sort_key(key: tuple[str, str, str]) -> tuple[Any, ...]:
    set_code, number, language = key
    number_parts = tuple(int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", number))
    return (set_code.casefold(), number_parts, LANG_RANK.get(language, 999), language.casefold())


# --- fetch cache (#35) ----------------------------------------------------------------------- #
# Entries used to be the bare payload under a hash of the URL. That is unattributable: given a
# cached file there was no way to say which URL produced it, when, or whether the response was
# plausible — and the cache directory is gitignored, so none of it appears in a diff either. A
# stale or thin entry was not wrong so much as invisible.
#
# Each entry is now an envelope recording the URL, the fetch time, the HTTP status, the content
# hash and the item count. Entries in the old bare format are treated as stale and refetched:
# accepting them would mean keeping exactly the unattributable state this replaces.

CACHE_SCHEMA = "snoredex-fetch-cache/1"
CACHE_MAX_AGE_DAYS = 30
FETCH_ATTEMPTS = 3
FETCH_BACKOFF_SECONDS = 1.5
# Transient by nature: worth retrying. A 404 is an answer, and retrying it just costs time.
RETRY_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


def cache_path(url: str) -> Path:
    return CACHE_DIR / f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"


def implausible(payload: Any) -> str | None:
    """Why this response cannot be a TCGdex card, or None if it looks like one.

    Checked before the response is cached, because a cache entry is trusted on every later run and
    an empty or wrongly-shaped body is indistinguishable from a real answer once stored.
    """
    if not isinstance(payload, dict):
        return f"expected a JSON object, got {type(payload).__name__}"
    if not payload:
        return "empty object"
    if "id" not in payload:
        return "no 'id' field, so this is not a card record"
    return None


def cache_entry_age_days(entry: dict[str, Any]) -> float | None:
    stamp = entry.get("fetchedAt")
    if not isinstance(stamp, str):
        return None
    try:
        fetched = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - fetched).total_seconds() / 86400


def read_cache(url: str, refresh: bool, max_age_days: float) -> tuple[dict[str, Any] | None, str]:
    """Return the cached payload and why it was or was not used."""
    path = cache_path(url)
    if refresh:
        return None, "refresh requested"
    if not path.exists():
        return None, "not cached"
    try:
        entry = read_json(path)
    except (OSError, json.JSONDecodeError):
        return None, "cache entry unreadable"
    if not isinstance(entry, dict) or entry.get("schema") != CACHE_SCHEMA:
        return None, "cache entry predates the metadata envelope"
    payload = entry.get("payload")
    if json_hash(payload) != entry.get("contentHash"):
        return None, "cache entry failed its own content hash"
    age = cache_entry_age_days(entry)
    if age is None:
        return None, "cache entry has no usable timestamp"
    if age > max_age_days:
        return None, f"cache entry is {age:.0f} days old"
    return payload, "cached"


def json_hash(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def write_cache(url: str, payload: Any, status: int, content_type: str | None) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(cache_path(url), {
        "schema": CACHE_SCHEMA,
        "url": url,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "httpStatus": status,
        "contentType": content_type,
        "contentHash": json_hash(payload),
        "itemCount": len(payload) if isinstance(payload, (list, dict)) else None,
        "payload": payload,
    })


def snapshot_records() -> dict[str, Any]:
    if not SNAPSHOT_PATH.is_file():
        return {}
    document = read_json(SNAPSHOT_PATH)
    records = document.get("records") if isinstance(document, dict) else None
    return records if isinstance(records, dict) else {}


def snapshot_drift(previous: dict[str, Any], current: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """Return changed, added, and removed upstream records by content hash."""
    changed = sorted(
        url for url in set(previous) & set(current)
        if previous[url].get("contentHash") != current[url].get("contentHash")
    )
    added = sorted(set(current) - set(previous))
    removed = sorted(set(previous) - set(current))
    return changed, added, removed


def write_refresh_candidate(records: dict[str, Any]) -> None:
    """Stage the exact payloads produced by a review refresh for later acceptance."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    write_json(REFRESH_CANDIDATE_PATH, {
        "schema": REFRESH_CANDIDATE_SCHEMA,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records": records,
    })


def load_refresh_candidate(expected_urls: set[str]) -> dict[str, dict[str, Any]]:
    """Load and validate the payloads staged by the preceding non-accepting refresh."""
    if not REFRESH_CANDIDATE_PATH.is_file():
        raise ValueError(
            "no staged TCGdex refresh candidate; run `python scripts/finishes.py --refresh` first"
        )
    document = read_json(REFRESH_CANDIDATE_PATH)
    if not isinstance(document, dict):
        raise ValueError("staged TCGdex refresh candidate is not an object")
    if document.get("schema") != REFRESH_CANDIDATE_SCHEMA:
        raise ValueError("staged TCGdex refresh candidate has an unexpected schema")
    records = document.get("records")
    if not isinstance(records, dict) or set(records) != expected_urls:
        raise ValueError("staged TCGdex refresh candidate does not match current source URLs")
    for url, record in records.items():
        payload = record.get("payload") if isinstance(record, dict) else None
        if (not isinstance(record, dict) or json_hash(payload) != record.get("contentHash")
                or implausible(payload)):
            raise ValueError(f"staged TCGdex refresh candidate failed validation: {url}")
    return records


def fetch_tcgdex(url: str, refresh: bool = False, offline: bool = False,
                 max_age_days: float = CACHE_MAX_AGE_DAYS
                 ) -> tuple[str, dict[str, Any] | None, str | None]:
    if offline:
        record = snapshot_records().get(url)
        payload = record.get("payload") if isinstance(record, dict) else None
        if payload is None:
            return url, None, "not present in versioned finish snapshot"
        if json_hash(payload) != record.get("contentHash") or implausible(payload):
            return url, None, "versioned finish snapshot record failed validation"
        return url, payload, None
    payload, _reason = read_cache(url, refresh, max_age_days)
    if payload is not None:
        return url, payload, None

    request = urllib.request.Request(
        url, headers={"User-Agent": "snoredex-data/finish-verification"})
    last_error = "unknown error"
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                status = getattr(response, "status", 200) or 200
                content_type = response.headers.get("Content-Type")
                body = json.load(response)
        except urllib.error.HTTPError as error:
            last_error = f"HTTP {error.code}"
            if error.code not in RETRY_STATUS or attempt == FETCH_ATTEMPTS:
                return url, None, last_error
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
            last_error = str(error)
            if attempt == FETCH_ATTEMPTS:
                return url, None, last_error
        else:
            problem = implausible(body)
            if problem:
                # Not cached. A response that cannot be a card is a failure, and storing it would
                # make it look like a settled answer on every later run.
                return url, None, f"implausible response: {problem}"
            write_cache(url, body, status, content_type)
            return url, body, None
        time.sleep(FETCH_BACKOFF_SECONDS * attempt)
    return url, None, last_error


def reverse_pattern(card_url: str | None) -> str | None:
    """Return a sourced era pattern only where the TCGdex set id is unambiguous."""
    if not card_url or "/cards/" not in card_url:
        return None
    card_id = card_url.rsplit("/cards/", 1)[1]
    if card_id.startswith(("base6-", "lc-")):
        return "fireworks"
    if re.match(r"ecard[123]-", card_id):
        return "flat-foil-card-body"
    match = re.match(r"ex(\d+)-", card_id)
    if match:
        ex_number = int(match.group(1))
        return {
            5: "energy-symbol-artwork",
            6: "energy-symbol-artwork-poke-ball",
            7: "energy-symbol-artwork-poke-ball",
            8: "pinwheel-artwork",
            9: "poke-ball-and-stars-artwork",
            10: "three-dimensional-poke-ball-artwork",
            11: "plain-foil-artwork-background",
            12: "plain-foil-artwork-background",
            13: "plain-foil-artwork-background",
            14: "plain-foil-artwork-background",
            15: "plain-foil-on-pokemon",
            16: "plain-foil-artwork-background",
        }.get(ex_number)
    if re.match(r"(?:dp\d+|pl\d+|hgss\d*|col1|bw1)-", card_id):
        return "plain-foil-background"
    match = re.match(r"bw(\d+)-", card_id)
    if match and int(match.group(1)) >= 2:
        return "type-symbol-background"
    match = re.match(r"xy(\d+)-", card_id)
    if match:
        return "plain-foil-background" if int(match.group(1)) == 12 else "type-symbol-background"
    if card_id.startswith("g1-"):
        return "type-symbol-background"
    if re.match(r"sm\d", card_id):
        return "large-type-symbol-left"
    if card_id.startswith("swsh"):
        return "tiled-type-symbol"
    if re.match(r"sv\d", card_id):
        return "intricate-tiled-type-symbol"
    if card_id.startswith("me"):
        return "plain-foil-background"
    return None


def source_signature(source: dict[str, Any]) -> str:
    return json.dumps(source, ensure_ascii=False, sort_keys=True)


def printing_signature(printing: dict[str, Any]) -> str:
    identity = {
        "finish": printing["finish"],
        "edition": printing.get("edition"),
        "foilPattern": normalize_foil_pattern(printing.get("foilPattern")),
        "markings": printing.get("markings") or None,
        "distribution": printing.get("distribution"),
        "releaseDate": printing.get("releaseDate"),
        "cardSize": printing.get("cardSize"),
    }
    return json.dumps(identity, ensure_ascii=False, sort_keys=True)


def refine_specimen_card_sizes(printings: list[dict[str, Any]]) -> None:
    """Resolve omitted specimen sizes after every printing candidate is known."""
    for specimen in printings:
        if specimen.get("cardSize") != "unknown" or not specimen.get("specimenIds"):
            continue
        matching_sizes = set()
        for candidate in printings:
            resized = dict(specimen)
            resized["cardSize"] = candidate.get("cardSize")
            if printing_signature(resized) == printing_signature(candidate):
                matching_sizes.add(candidate.get("cardSize"))
        if matching_sizes == {"unknown", "standard"}:
            specimen["cardSize"] = "standard"


def add_printing(printings: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
    candidate["foilPattern"] = normalize_foil_pattern(candidate.get("foilPattern"))
    candidate.setdefault("foilPattern", None)
    candidate.setdefault("markings", None)
    candidate.setdefault("distribution", None)
    candidate.setdefault("cardSize", "unknown")
    candidate.setdefault("mappedVariants", [])
    candidate.setdefault("verificationStatus", "pending")
    candidate.setdefault("sources", [])
    conflicts = sorted(set(candidate.get("conflictsWith") or []))
    if conflicts:
        candidate["conflictsWith"] = conflicts
        candidate["verificationStatus"] = "pending"
    else:
        candidate.pop("conflictsWith", None)
    signature = printing_signature(candidate)
    existing = next((item for item in printings if printing_signature(item) == signature), None)
    if existing is None and candidate["foilPattern"] is None and any(
            source.get("evidenceScope") == "standard-set" for source in candidate["sources"]):
        pattern_matches = []
        for item in printings:
            patternless = dict(item)
            patternless["foilPattern"] = None
            if printing_signature(patternless) == signature:
                pattern_matches.append(item)
        if len(pattern_matches) == 1:
            existing = pattern_matches[0]
    if existing is None:
        candidate["mappedVariants"] = sorted(set(candidate["mappedVariants"]))
        if candidate.get("specimenIds"):
            candidate["specimenIds"] = sorted(set(candidate["specimenIds"]))
        else:
            candidate.pop("specimenIds", None)
        candidate["_origin"] = candidate.get("_origin", "auto")
        printings.append(candidate)
        return
    existing["mappedVariants"] = sorted(set(existing["mappedVariants"] + candidate["mappedVariants"]))
    if candidate.get("specimenIds"):
        existing["specimenIds"] = sorted(set(existing.get("specimenIds") or [])
                                          | set(candidate["specimenIds"]))
        existing["_origin"] = "specimen"
    existing_conflicts = sorted(set(existing.get("conflictsWith") or []))
    if existing_conflicts or conflicts:
        existing["verificationStatus"] = "pending"
        existing["conflictsWith"] = sorted(set(existing_conflicts) | set(conflicts))
    elif STATUS_RANK[candidate["verificationStatus"]] > STATUS_RANK[existing["verificationStatus"]]:
        existing["verificationStatus"] = candidate["verificationStatus"]
    seen_sources = {source_signature(source) for source in existing["sources"]}
    for source in candidate["sources"]:
        if source_signature(source) not in seen_sources:
            existing["sources"].append(source)
            seen_sources.add(source_signature(source))
    if "image" not in existing and candidate.get("image"):
        existing["image"] = candidate["image"]


def refine_auto_printing(printings: list[dict[str, Any]], candidate: dict[str, Any]) -> bool:
    """Replace one generic auto identity with a positively established curated identity."""
    if not candidate.pop("_refinesAuto", False):
        return False
    expected_key = (
        "auto",
        candidate.get("finish"),
        tuple(sorted(candidate.get("mappedVariants") or [])),
        "null",
        "null",
    )
    matches = [
        printing for printing in printings
        if (
            printing.get("_origin"),
            printing.get("finish"),
            tuple(sorted(printing.get("mappedVariants") or [])),
            json.dumps(printing.get("markings") or None, sort_keys=True),
            json.dumps(printing.get("distribution"), sort_keys=True),
        ) == expected_key
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one generic auto printing to refine, found {len(matches)}")
    existing = matches[0]
    if candidate.get("cardSize") == "unknown":
        candidate["cardSize"] = existing.get("cardSize", "unknown")
    candidate["sources"] = existing["sources"] + candidate["sources"]
    candidate["verificationStatus"] = max(
        (existing["verificationStatus"], candidate["verificationStatus"]),
        key=STATUS_RANK.__getitem__,
    )
    candidate["_origin"] = "manual"
    printings.remove(existing)
    add_printing(printings, candidate)
    return True


def add_or_refine_printing(printings: list[dict[str, Any]], candidate: dict[str, Any]) -> None:
    if not refine_auto_printing(printings, candidate):
        add_printing(printings, candidate)


def apply_standard_scope_card_size(candidate: dict[str, Any]) -> None:
    if candidate.get("cardSize") == "unknown" and any(
        source.get("evidenceScope") == "standard-set"
        for source in candidate.get("sources") or []
    ):
        candidate["cardSize"] = "standard"


def exact_source(url: str, source_type: str, evidence: str) -> dict[str, Any]:
    return {"url": url, "sourceType": source_type, "evidence": evidence}


def specimen_number(value: object) -> str:
    return str(value or "").split("/", 1)[0]


def normalize_foil_pattern(value: object) -> object:
    if not isinstance(value, str):
        return value
    key = " ".join(value.casefold().replace("é", "e").split())
    return FOIL_PATTERN_ALIASES.get(key, value)


def specimen_markings(observation: dict[str, Any]) -> list[dict[str, Any]]:
    text = observation.get("markings")
    if not text:
        return []
    normalized = str(text).strip()
    if normalized.casefold() in {"editie 1", "edizione 1"}:
        kind = "edition-stamp"
    elif normalized.casefold() == "staff":
        kind, normalized = "staff", "Staff"
    elif normalized.casefold().endswith(" deck silhouette"):
        kind, normalized = "deck-logo", normalized[:-16].strip()
    elif normalized.casefold().endswith(" replica signature"):
        kind, normalized = "championship-signature", normalized[:-18].strip()
    else:
        kind = "observed-marking"
    return [{"kind": kind, "role": observation.get("markingRole"), "text": normalized}]


def specimen_source(specimen: dict[str, Any]) -> dict[str, Any]:
    holder = str(specimen.get("heldBy", "")).casefold()
    if "third-party seller" in holder:
        source_type = "Seller listing photograph"
    elif "third-party retailer" in holder:
        source_type = "Retail listing"
    elif "third-party scan archive" in holder:
        source_type = "Third-party scan archive"
    elif "owner" in holder:
        source_type = "Owner-supplied physical card photograph"
    else:
        source_type = "Inspected physical specimen photograph"
    return exact_source(
        str(specimen.get("photographSource") or f"specimen:{specimen['specimenId']}"),
        source_type,
        f"{specimen.get('observed', '').strip()} Retained as {specimen['specimenId']}.",
    )


def specimen_sources(specimen: dict[str, Any], observation: dict[str, Any]) -> list[dict[str, Any]]:
    photograph_source = specimen_source(specimen)
    if specimen.get("recordedAt"):
        photograph_source["retrievedAt"] = specimen["recordedAt"]
    sources = [photograph_source]
    owner_fields = observation.get("ownerAttestedFields") or []
    if owner_fields:
        photograph_label = str(photograph_source["sourceType"]).casefold()
        photograph_source["claimFields"] = [
            "identity",
            *[
                field for field in ("finish", "edition")
                if observation.get(field) is not None and field not in owner_fields
            ],
        ]
        labels = {"finish": "finish", "edition": "edition"}
        established = ", ".join(labels[field] for field in owner_fields)
        sources.append({
            "sourceType": "Owner attestation (domain expert)",
            "claimFields": owner_fields,
            "retrievedAt": specimen.get("recordedAt"),
            "evidence": (
                f"The collection owner's explicit {specimen.get('recordedAt', '')} confirmation "
                f"establishes the specimen's {established}; the retained {photograph_label} "
                "supports card identity and any independently visible properties."
            ),
        })
    return sources


def specimen_printing(specimen: dict[str, Any]) -> dict[str, Any] | None:
    observation = specimen.get("physicalObservation")
    if not isinstance(observation, dict) or not observation.get("finish"):
        return None
    marking_values = specimen_markings(observation)
    candidate = {
        "finish": observation["finish"],
        "foilPattern": normalize_foil_pattern(observation.get("foilPattern")),
        "markings": marking_values,
        "distribution": observation.get("distribution"),
        "cardSize": observation.get("cardSize") or "unknown",
        "mappedVariants": [str(specimen.get("variant"))],
        "verificationStatus": "confirmed",
        "sources": specimen_sources(specimen, observation),
        "_origin": "specimen",
        "specimenIds": [specimen["specimenId"]],
    }
    conflicts = observation.get("conflictsWith") or []
    if conflicts:
        candidate["conflictsWith"] = sorted(set(str(ref) for ref in conflicts))
    if observation.get("edition") is not None:
        candidate["edition"] = observation["edition"]
    photograph = specimen.get("photograph")
    if photograph:
        candidate["image"] = f"verification/specimens/{photograph}"
    return candidate


def merge_curated_specimen_identity(
    candidate: dict[str, Any], manual: dict[str, Any], source_registry: dict[str, dict[str, Any]]
) -> bool:
    """Carry curated optional identity onto a specimen with the same cited provenance."""
    if candidate.get("finish") != manual.get("finish"):
        return False
    candidate_variants = set(candidate.get("mappedVariants") or [])
    manual_variants = set(manual.get("mappedVariants") or [])
    if manual_variants and not candidate_variants & manual_variants:
        return False
    candidate_urls = {
        str(source.get("url")) for source in candidate.get("sources") or [] if source.get("url")
    }
    manual_urls = {
        str(source_registry[ref].get("url"))
        for ref in manual.get("sourceRefs") or []
        if ref in source_registry and source_registry[ref].get("url")
    }
    if not candidate_urls & manual_urls:
        return False
    for field in ("edition", "foilPattern", "markings", "distribution", "releaseDate"):
        candidate_value = candidate.get(field)
        manual_value = manual.get(field)
        if candidate_value in (None, [], "unknown") and manual_value not in (None, [], "unknown"):
            candidate[field] = manual_value
    return True


def add_reverse_specimen_conflicts(
    candidate: dict[str, Any], specimen_id: str, reverse_conflicts: dict[str, set[str]]
) -> dict[str, Any]:
    conflicts = set(candidate.get("conflictsWith") or []) | reverse_conflicts.get(specimen_id, set())
    if conflicts:
        candidate["conflictsWith"] = sorted(conflicts)
    return candidate


def validate_specimen_conflicts(specimens_document: dict[str, Any]) -> None:
    """Validate explicit conflict references without inferring conflicts from omissions."""
    specimens = specimens_document.get("specimens", [])
    specimen_ids = {str(row.get("specimenId")) for row in specimens}
    for specimen in specimens:
        conflicts = (specimen.get("physicalObservation") or {}).get("conflictsWith") or []
        if not isinstance(conflicts, list) or any(
            not isinstance(ref, str) or ref == specimen.get("specimenId") or ref not in specimen_ids
            for ref in conflicts
        ):
            raise ValueError(f"invalid physicalObservation.conflictsWith: {specimen.get('specimenId')}")


def resolve_override_sources(
    source_refs: list[str],
    registry: dict[str, dict[str, Any]],
    products: list[dict[str, Any]],
    mapped_variants: list[str],
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for source_ref in source_refs:
        source = dict(registry[source_ref])
        if source_ref == "cardmarket-stock-image":
            product = next((item for item in products if item["variant"] in mapped_variants), None)
            if product:
                source["url"] = product["cardmarketUrl"]
                source["image"] = product["image"]
        if source.get("url") is None:
            source.pop("url", None)
        resolved.append(source)
    return resolved


def strongest_status(printings: list[dict[str, Any]], finish: str | None = None) -> str:
    statuses = [item["verificationStatus"] for item in printings if finish is None or item["finish"] == finish]
    return max(statuses, key=lambda status: STATUS_RANK[status]) if statuses else "pending"


def evidence_scopes(printings: list[dict[str, Any]]) -> set[str]:
    return {
        source["evidenceScope"]
        for printing in printings
        for source in printing.get("sources") or []
        if source.get("evidenceScope")
    }


def source_scope_needs_owner(
    printings: list[dict[str, Any]],
    scopes: set[str],
    unit_key: tuple[str, str, str],
    decisions: dict[tuple[str, str, str], dict[str, Any]],
) -> bool:
    return bool(printings) and "finish-unit" in scopes and unit_key not in decisions


def compact_printing(printing: dict[str, Any], product_mapping: str = "mapped") -> dict[str, Any]:
    compact = {
        "printingId": printing["printingId"],
        "finish": printing["finish"],
        "foilPattern": printing.get("foilPattern"),
        "markings": printing.get("markings"),
        "distribution": printing.get("distribution"),
        "cardSize": printing.get("cardSize"),
        "verificationStatus": printing["verificationStatus"],
        "productMapping": product_mapping,
    }
    if printing.get("edition"):
        compact["edition"] = printing["edition"]
    if "releaseDate" in printing:
        compact["releaseDate"] = printing.get("releaseDate")
    # An explicit null suppresses a Cardmarket product image for a physical printing whose
    # pictured version is different. Preserve the key as well as a concrete image path so the
    # public projection can make that distinction.
    if "image" in printing:
        compact["image"] = printing["image"]
    if printing.get("specimenIds"):
        compact["specimenIds"] = list(printing["specimenIds"])
    if printing.get("conflictsWith"):
        compact["conflictsWith"] = list(printing["conflictsWith"])
    return compact


def project_unit_onto_product(unit: dict[str, Any], token: str) -> dict[str, Any]:
    """Project one finish unit onto one Cardmarket product without losing evidence.

    A finish unit is keyed on (set, number, language); a Cardmarket product is one V-token
    within it. Printings are therefore in one of three relationships to a given product:

    * mapped here      - attributed to this token by evidence;
    * unresolved       - attributed to no product yet, so it may belong to this one;
    * another product  - attributed to a different token of the same unit.

    Earlier revisions kept only the first group, so confirmed printings attributed to no
    product reached no consumer at all and cells rendered blank where the store held
    evidence. All three groups are now represented, and each finish carries a status that
    says which relationship it rests on, so `pending` keeps its single documented meaning
    of "no positive evidence anywhere in this unit".
    """
    product = next((item for item in unit["products"] if item["variant"] == token), None)
    not_applicable = bool(product and product["claimStatus"] == "contradicted")

    mapped_here = [p for p in unit["printings"] if token in p["mappedVariants"]]
    unresolved = [p for p in unit["printings"] if not p["mappedVariants"]]
    other_product = [
        p for p in unit["printings"] if p["mappedVariants"] and token not in p["mappedVariants"]
    ]

    def status_for(finish: str) -> str:
        if not_applicable:
            return "not-applicable"
        attributed = [p for p in mapped_here if p["finish"] == finish]
        if attributed:
            return strongest_status(attributed, finish)
        if any(p["finish"] == finish for p in unresolved):
            return "unmapped"
        if any(p["finish"] == finish for p in other_product):
            return "other-product"
        return "pending"

    finish_status = {finish: status_for(finish) for finish in FINISHES}
    attributed_known = [p for p in mapped_here if p["finish"] in FINISHES]

    return {
        "language": unit["language"],
        "claimStatus": product["claimStatus"] if product else "pending",
        # Finishes evidence attributes to this specific Cardmarket product.
        "availableFinishes": [
            finish for finish in FINISHES if any(p["finish"] == finish for p in mapped_here)
        ],
        # Finishes known for this set number and language regardless of which product carries
        # them. Always populated when the store holds evidence, so a consumer never sees an
        # empty cell for a card whose finishes are in fact documented.
        "unitAvailableFinishes": list(unit["availableFinishes"]),
        "finishStatus": finish_status,
        # The store's own status, carried verbatim. Product attribution can only ever be weaker
        # than the unit's knowledge, so this guarantees the projection loses no evidence.
        "unitFinishStatus": dict(unit["finishStatus"]),
        "status": "not-applicable" if not_applicable else strongest_status(attributed_known),
        "finishUnitId": unit["finishUnitId"],
        # Propagated so `pending` and `unmapped` can be told apart without loading the store.
        "productMappingStatus": unit["productMappingStatus"],
        "printings": [compact_printing(p, "mapped") for p in mapped_here]
        + [compact_printing(p, "unresolved") for p in unresolved],
    }


def _load_finish_context() -> dict[str, Any]:
    cards_document = read_json(CARDS_PATH)
    cards = cards_document["cards"]
    units = read_json(UNITS_PATH)
    overrides_document = read_json(OVERRIDES_PATH)
    specimens_document = read_json(SPECIMENS_PATH)
    validate_specimen_conflicts(specimens_document)
    specimens_by_group: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    reverse_conflicts: dict[str, set[str]] = defaultdict(set)
    for specimen in specimens_document.get("specimens", []):
        specimen_id = str(specimen.get("specimenId"))
        for reference in (specimen.get("physicalObservation") or {}).get("conflictsWith") or []:
            reverse_conflicts[str(reference)].add(specimen_id)
        # A frame that explicitly covers multiple cards is context evidence only.  It must not
        # become a synthetic ``base`` printing; the per-card crops/records are the canonical
        # observations that carry the variant mapping.
        observation = specimen.get("physicalObservation")
        if observation and not observation.get("coversMultipleCards"):
            specimens_by_group[
                (str(specimen.get("setCode") or ""), specimen_number(specimen.get("number")),
                 str(specimen.get("language") or ""))
            ].append(specimen)
    # Rule 4 owner decisions, finish half (#119). Keyed by (setCode, number, language) rather
    # than by finishUnitId, because the F-numbers are positional and would silently retarget.
    adjudications_document = read_json(ADJUDICATIONS_PATH)
    owner_finish_decisions = {
        (d["setCode"], d["number"], d["language"]): d
        for d in adjudications_document.get("finishDecisions", [])
    }
    source_registry = overrides_document["sources"]

    cards_by_product: dict[tuple[str, str, str], dict[str, Any]] = {}
    for card in cards:
        if card.get("isCodeCard"):
            continue
        key = (str(card.get("setCode") or ""), str(card.get("number") or ""), variant_token(card))
        if key in cards_by_product:
            raise ValueError(f"Duplicate non-code product key: {key}")
        cards_by_product[key] = card

    grouped_units: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        grouped_units[group_key(unit)].append(unit)

    tcgdex_urls = sorted(
        {
            unit["sourceUrl"]
            for unit in units
            if unit.get("status") == "confirmed"
            and str(unit.get("sourceUrl") or "").startswith("https://api.tcgdex.net/")
        }
    )

    return {
        "cards_document": cards_document,
        "cards": cards,
        "units": units,
        "overrides_document": overrides_document,
        "specimens_document": specimens_document,
        "specimens_by_group": specimens_by_group,
        "reverse_conflicts": reverse_conflicts,
        "owner_finish_decisions": owner_finish_decisions,
        "adjudications_document": adjudications_document,
        "snapshot_document": read_json(SNAPSHOT_PATH),
        "source_registry": source_registry,
        "cards_by_product": cards_by_product,
        "grouped_units": grouped_units,
        "tcgdex_urls": tcgdex_urls,
    }


def _resolve_tcgdex(context: dict[str, Any]) -> int | None:
    """Resolve offline, refresh, and refresh-accept modes before projection starts."""
    tcgdex_urls = context["tcgdex_urls"]
    tcgdex_data: dict[str, dict[str, Any]] = {}
    fetch_errors: dict[str, str] = {}
    refresh = "--refresh" in sys.argv or "--refresh-cache" in sys.argv
    # Network access is opt-in.  A bare finishes.py invocation is the same deterministic
    # versioned build as regen.py; only --refresh (or its legacy alias) may consult TCGdex.
    offline = "--offline" in sys.argv or not refresh
    accept_refresh = "--accept-refresh" in sys.argv
    if offline and refresh:
        raise ValueError("--offline and --refresh are mutually exclusive")
    if accept_refresh and not refresh:
        raise ValueError("--accept-refresh requires --refresh")
    accepted_refresh = False
    if accept_refresh:
        try:
            current_snapshot = load_refresh_candidate(set(tcgdex_urls))
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            print(f"cannot accept TCGdex refresh candidate: {error}", file=sys.stderr)
            return 2
        tcgdex_data = {
            url: record["payload"] for url, record in current_snapshot.items()
        }
        accepted_refresh = True
    else:
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = {
                executor.submit(fetch_tcgdex, url, refresh, offline): url for url in tcgdex_urls
            }
            for future in as_completed(futures):
                url, payload, error = future.result()
                if payload is not None:
                    tcgdex_data[url] = payload
                else:
                    fetch_errors[url] = error or "unknown error"

    if refresh and not fetch_errors and not accept_refresh:
        current_snapshot = {
            url: {"contentHash": json_hash(payload), "payload": payload}
            for url, payload in sorted(tcgdex_data.items())
        }
        changed, added, removed = snapshot_drift(snapshot_records(), current_snapshot)
        print(
            "TCGdex refresh: "
            f"changed={len(changed)} added={len(added)} removed={len(removed)}"
        )
        for url in changed + added + removed:
            print(f"  drift: {url}")
        write_refresh_candidate(current_snapshot)
        print("Refresh candidate staged. Review it, then rerun with --refresh --accept-refresh.")
        return 0

    if accepted_refresh:
        changed, added, removed = snapshot_drift(snapshot_records(), current_snapshot)
        print(
            "TCGdex refresh accepted: "
            f"changed={len(changed)} added={len(added)} removed={len(removed)}"
        )
        for url in changed + added + removed:
            print(f"  drift: {url}")
        snapshot_document = {
            "schema": "snoredex-tcgdex-snapshot/1",
            "generated": datetime.now(timezone.utc).date().isoformat(),
            "records": current_snapshot,
        }
        write_json(SNAPSHOT_PATH, snapshot_document)
        context["snapshot_document"] = snapshot_document
    if fetch_errors and (offline or refresh):
        for url, reason in sorted(fetch_errors.items()):
            print(f"unreachable: {url} — {reason}", file=sys.stderr)
        return 2
    context.update({
        "tcgdex_data": tcgdex_data,
        "fetch_errors": fetch_errors,
        "accepted_refresh": accepted_refresh,
        "refresh": refresh,
    })
    return None


def _prepare_finish_indexes(context: dict[str, Any]) -> None:
    """Build local lookup indexes and reject duplicate evidence references."""
    units = context["units"]
    overrides_document = context["overrides_document"]
    specimens_document = context["specimens_document"]
    tcgdex_sibling_url: dict[tuple[str, str], str] = {}
    for unit in units:
        url = str(unit.get("sourceUrl") or "")
        if url.startswith("https://api.tcgdex.net/"):
            sibling_key = (str(unit.get("setCode") or ""), str(unit.get("number") or ""))
            if unit.get("language") == "English" or sibling_key not in tcgdex_sibling_url:
                tcgdex_sibling_url[sibling_key] = url

    overrides_by_group: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for override in overrides_document["overrides"]:
        overrides_by_group[(str(override["setCode"]), str(override.get("number") or ""))].append(override)

    specimens_by_id = {
        str(row.get("specimenId")): row for row in specimens_document.get("specimens", [])
    }
    specimen_ids = set(specimens_by_id)
    for override in overrides_document["overrides"]:
        for manual in override.get("printings") or []:
            refs = {str(ref) for ref in manual.get("sourceRefs") or []}
            duplicate_refs = refs & specimen_ids
            if duplicate_refs or any(ref.startswith("SPEC-") for ref in refs):
                raise ValueError(
                    "finish_overrides duplicates specimen evidence: "
                    + ", ".join(sorted(duplicate_refs or refs))
                )
    context.update({
        "tcgdex_sibling_url": tcgdex_sibling_url,
        "overrides_by_group": overrides_by_group,
        "specimens_by_id": specimens_by_id,
    })


def _build_finish_unit(
    context: dict[str, Any], finish_index: int, key: tuple[str, str, str]
) -> dict[str, Any]:
    cards_by_product = context["cards_by_product"]
    grouped_units = context["grouped_units"]
    tcgdex_data = context["tcgdex_data"]
    tcgdex_sibling_url = context["tcgdex_sibling_url"]
    source_registry = context["source_registry"]
    overrides_by_group = context["overrides_by_group"]
    specimens_by_group = context["specimens_by_group"]
    specimens_by_id = context["specimens_by_id"]
    reverse_conflicts = context["reverse_conflicts"]
    owner_finish_decisions = context["owner_finish_decisions"]
    set_code, number, language = key
    member_units = grouped_units[key]
    products: list[dict[str, Any]] = []
    active_variants = None
    all_claims_contradicted = None
    applicable_overrides = None
    auto_card_size = None
    auto_mapping = None
    available_finishes = None
    candidate = None
    card_name = None
    completeness_status = None
    exact_urls = None
    field = None
    finish = None
    finish_status = None
    finish_unit_id = None
    inferred_reverse_pattern = None
    known_printings = None
    manual = None
    mapped_variants = None
    override = None
    pattern_status = None
    present_variants = None
    printing = None
    printings = None
    product = None
    product_mapping_status = None
    required_variants = None
    set_name = None
    source = None
    sources = None
    unit = None
    unknown_finish_printings = None
    unresolved = None
    source_scopes = None
    def _build_finish_unit_part1():
        nonlocal active_variants, all_claims_contradicted, card_name, present_variants, printings, product, set_name, unit
        for unit in sorted(member_units, key=lambda item: variant_token(item)):
            product_key = (set_code, number, variant_token(unit))
            card = cards_by_product.get(product_key)
            if card is None:
                raise ValueError(f"Finish unit has no card product: {product_key}")
            products.append(
                {
                    "variant": variant_token(unit),
                    "claimStatus": unit["status"],
                    "rarity": card.get("rarity"),
                    "variantName": card.get("variantName"),
                    "variantNameSource": card.get("variantNameSource"),
                    "cardmarketHints": {
                        "reverseHoloAxis": "Reverse Holo" in (card.get("variantAxes") or []),
                        "firstEditionAxis": "First Edition?" in (card.get("variantAxes") or []),
                    },
                    "cardmarketUrl": card["productUrl"],
                    "image": card.get("imageFile"),
                }
            )
        present_variants = {product["variant"] for product in products}
        active_variants = {
            product["variant"] for product in products if product["claimStatus"] != "contradicted"
        }
        all_claims_contradicted = bool(products) and not active_variants
        card_name = member_units[0]["cardName"]
        set_name = member_units[0]["setName"]
        printings = []

    def _build_finish_unit_part2():
        nonlocal auto_card_size, auto_mapping, exact_urls, inferred_reverse_pattern, product, unit
        exact_urls = sorted(
            {
                str(unit.get("sourceUrl") or "")
                for unit in member_units
                if unit.get("status") == "confirmed"
                and str(unit.get("sourceUrl") or "").startswith("https://api.tcgdex.net/")
            }
        )
        pattern_url = exact_urls[0] if exact_urls else tcgdex_sibling_url.get((set_code, number))
        inferred_reverse_pattern = reverse_pattern(pattern_url)
        auto_mapping = sorted(active_variants) if len(active_variants) == 1 else []
        auto_product = (
            next((product for product in products if product["variant"] in active_variants), None)
            if len(active_variants) == 1
            else None
        )
        auto_card_size = (
            "jumbo" if auto_product and auto_product.get("rarity") == "Oversized" else "standard"
        ) if auto_product else "unknown"

    def _build_finish_unit_part3():
        nonlocal field, finish, sources
        for url in exact_urls:
            payload = tcgdex_data.get(url)
            if payload is None:
                continue
            upstream_variants = payload.get("variants") or {}
            upstream_source = exact_source(
                url,
                "TCGdex API card variants",
                f"{payload.get('id')} variants=true is positive evidence that the printing exists; false values are not used as contradiction.",
            )
            for field, finish in (("normal", "non-holo"), ("holo", "holo"), ("reverse", "reverse-holo")):
                if upstream_variants.get(field) is not True:
                    continue
                sources = [upstream_source]
                pattern = inferred_reverse_pattern if finish == "reverse-holo" else None
                if pattern:
                    sources.append(dict(source_registry["holofoil-patterns"]))
                add_printing(
                    printings,
                    {
                        "finish": finish,
                        "foilPattern": pattern,
                        "markings": None,
                        "distribution": None,
                        "cardSize": auto_card_size,
                        "mappedVariants": auto_mapping,
                        "verificationStatus": "confirmed",
                        "sources": sources,
                        "_origin": "auto",
                    },
                )

    def _build_finish_unit_part4():
        nonlocal product, sources
        for product in products:
            if product["claimStatus"] == "contradicted":
                continue
            product_source = exact_source(
                product["cardmarketUrl"],
                "Cardmarket catalogue hint (not external verification)",
                "This is a positive marketplace catalogue claim only; it is not treated as proof or as a complete finish manifest.",
            )
            rarity = str(product.get("rarity") or "")
            product_card_size = "jumbo" if rarity == "Oversized" else "standard"
            if product["cardmarketHints"]["reverseHoloAxis"]:
                sources = [product_source]
                if inferred_reverse_pattern:
                    sources.append(dict(source_registry["holofoil-patterns"]))
                add_printing(
                    printings,
                    {
                        "finish": "reverse-holo",
                        "foilPattern": inferred_reverse_pattern,
                        "markings": None,
                        "distribution": None,
                        "cardSize": product_card_size,
                        "mappedVariants": [product["variant"]],
                        "verificationStatus": "marketplace-claimed",
                        "sources": sources,
                        "_origin": "auto",
                    },
                )
            if rarity in {"Common", "Uncommon", "Rare"}:
                add_printing(
                    printings,
                        {
                            "finish": "non-holo",
                            "cardSize": product_card_size,
                        "mappedVariants": [product["variant"]],
                        "verificationStatus": "marketplace-claimed",
                        "sources": [product_source],
                        "_origin": "auto",
                    },
                )
            elif "Holo" in rarity:
                add_printing(
                    printings,
                        {
                            "finish": "holo",
                            "cardSize": product_card_size,
                        "mappedVariants": [product["variant"]],
                        "verificationStatus": "marketplace-claimed",
                        "sources": [product_source],
                        "_origin": "auto",
                    },
                )

            variant_name = str(product.get("variantName") or "")
            if variant_name:
                normalized_name = variant_name.casefold()
                named_finish = None
                named_pattern = None
                if "non-holo" in normalized_name:
                    named_finish = "non-holo"
                elif "mirror holo" in normalized_name:
                    named_finish = "mirror-holo"
                elif "holo" in normalized_name:
                    named_finish = "holo"
                if "master ball" in normalized_name:
                    named_pattern = "master-ball"
                elif "poké ball" in normalized_name or "poke ball" in normalized_name:
                    named_pattern = "poke-ball"
                elif "cosmos" in normalized_name:
                    named_pattern = "cosmos"
                elif "colourless-energy star" in normalized_name:
                    named_pattern = "colorless-energy-star"
                if named_finish:
                    add_printing(
                        printings,
                        {
                            "finish": named_finish,
                            "foilPattern": named_pattern,
                            "markings": None,
                            "distribution": None,
                            "cardSize": product_card_size,
                            "mappedVariants": [product["variant"]],
                            "verificationStatus": "confirmed",
                            "sources": [
                                exact_source(
                                    product["cardmarketUrl"],
                                    product.get("variantNameSource") or "Curated variant identification",
                                    f"Curated variant name: {variant_name}",
                                )
                            ],
                            "_origin": "auto",
                        },
                    )

    def _build_finish_unit_part5():
        nonlocal applicable_overrides, override
        applicable_overrides = [
            override
            for override in overrides_by_group.get((set_code, number), [])
            if not override.get("languages") or language in override["languages"]
        ]

    def _build_finish_unit_part6():
        nonlocal candidate, field, manual, override
        for specimen in specimens_by_group.get((set_code, number, language), []):
            candidate = specimen_printing(specimen)
            if candidate is not None:
                add_reverse_specimen_conflicts(candidate, str(specimen["specimenId"]), reverse_conflicts)
                for override in applicable_overrides:
                    for manual in override.get("printings") or []:
                        manual_variants = set(manual.get("mappedVariants") or [])
                        if manual.get("finish") != candidate["finish"] or (
                            manual_variants
                            and not manual_variants.intersection(candidate["mappedVariants"])
                        ):
                            continue
                        photograph_claim_fields = manual.get("specimenPhotographClaimFields")
                        if photograph_claim_fields is not None:
                            if (
                                not isinstance(photograph_claim_fields, list)
                                or not photograph_claim_fields
                                or any(
                                    field not in {"identity", "finish", "edition"}
                                    for field in photograph_claim_fields
                                )
                            ):
                                raise ValueError(
                                    "invalid specimenPhotographClaimFields for "
                                    f"{set_code} {number} {language}"
                                )
                            candidate["sources"][0]["claimFields"] = list(
                                photograph_claim_fields
                            )
                        localized_refs = [
                            ref for ref in manual.get("sourceRefs") or []
                            if language in (source_registry[ref].get("languages") or [])
                        ]
                        candidate["sources"].extend(resolve_override_sources(
                            localized_refs,
                            source_registry,
                            products,
                            candidate["mappedVariants"],
                        ))
                    if any(
                        merge_curated_specimen_identity(candidate, manual, source_registry)
                        for manual in override.get("printings") or []
                    ):
                        break
                apply_standard_scope_card_size(candidate)
                add_printing(printings, candidate)

    def _build_finish_unit_part7():
        nonlocal candidate, finish, manual, mapped_variants, override, printing, printings, product, source
        def _build_finish_unit_part7_suppression():
            nonlocal override, printing, printings, product, source
            for override in applicable_overrides:
                suppressed = set(override.get("suppressAutoFinishes") or [])
                if suppressed:
                    # Suppression corrects catalogue-derived guesses; only a positive TCGdex
                    # variants=true response is immune.
                    printings = [
                        printing
                        for printing in printings
                        if not (
                            printing.get("_origin") == "auto"
                            and printing["finish"] in suppressed
                            and not any(
                                str(source.get("url") or "").startswith("https://api.tcgdex.net/")
                                for source in printing.get("sources") or []
                            )
                        )
                    ]
                for finish, mapped_variants in (override.get("mapAutoFinishes") or {}).items():
                    usable = sorted(set(mapped_variants) & present_variants)
                    mapped_sizes = {
                        "jumbo" if product.get("rarity") == "Oversized" else "standard"
                        for product in products
                        if product["variant"] in usable
                    }
                    for printing in printings:
                        observed_variants = {
                            str(specimens_by_id[specimen_id].get("variant"))
                            for specimen_id in printing.get("specimenIds") or []
                            if specimen_id in specimens_by_id
                        }
                        if printing["finish"] == finish and (
                            printing.get("_origin") == "auto" or observed_variants
                        ):
                            printing["mappedVariants"] = sorted(set(usable) | observed_variants)
                            if printing.get("cardSize") == "unknown" and len(mapped_sizes) == 1:
                                printing["cardSize"] = next(iter(mapped_sizes))

        def _build_finish_unit_part7_manual():
            nonlocal candidate, mapped_variants, override
            for override in applicable_overrides:
                for manual in override.get("printings") or []:
                    if manual.get("evidenceOnlyForSpecimen"):
                        continue
                    requested_variants = list(manual.get("mappedVariants") or [])
                    mapped_variants = sorted(set(requested_variants) & present_variants)
                    if requested_variants and not mapped_variants:
                        continue
                    candidate = {
                        "finish": manual["finish"],
                        "foilPattern": manual.get("foilPattern"),
                        "markings": manual.get("markings"),
                        "distribution": manual.get("distribution"),
                        "cardSize": manual.get("cardSize", "unknown"),
                        "mappedVariants": mapped_variants,
                        "verificationStatus": manual["verificationStatus"],
                        "sources": resolve_override_sources(
                            manual.get("sourceRefs") or [], source_registry, products, mapped_variants
                        ),
                        "_origin": "manual",
                        "_refinesAuto": manual.get("refinesAuto", False),
                    }
                    if "edition" in manual:
                        candidate["edition"] = manual["edition"]
                    if "releaseDate" in manual:
                        candidate["releaseDate"] = manual["releaseDate"]
                    if "image" in manual:
                        candidate["image"] = manual["image"]
                    add_or_refine_printing(printings, candidate)

        _build_finish_unit_part7_suppression()
        _build_finish_unit_part7_manual()

    def _build_finish_unit_part8():
        nonlocal available_finishes, finish, finish_status, finish_unit_id, printing, printings
        refine_specimen_card_sizes(printings)
        deduplicated_printings: list[dict[str, Any]] = []
        for printing in printings:
            add_printing(deduplicated_printings, printing)
        printings = [] if all_claims_contradicted else deduplicated_printings
        printings.sort(
            key=lambda item: (
                FINISHES.index(item["finish"]) if item["finish"] in FINISHES else 99,
                str(item.get("edition") or ""),
                str(item.get("releaseDate") or ""),
                str(item.get("foilPattern") or ""),
                json.dumps(item.get("markings"), ensure_ascii=False, sort_keys=True),
                item.get("cardSize") or "",
            )
        )
        finish_unit_id = f"F{finish_index:04d}"
        for printing_index, printing in enumerate(printings, 1):
            printing["printingId"] = f"{finish_unit_id}-P{printing_index:02d}"
            printing.pop("_origin", None)
        available_finishes = [finish for finish in FINISHES if any(p["finish"] == finish for p in printings)]
        finish_status = {
            finish: "not-applicable" if all_claims_contradicted else strongest_status(printings, finish)
            for finish in FINISHES
        }

    def _build_finish_unit_part9():
        nonlocal known_printings, mapped_variants, printing, product_mapping_status, required_variants, source, source_scopes, unknown_finish_printings
        mapped_variants = {variant for printing in printings for variant in printing["mappedVariants"]}
        required_variants = active_variants
        if not required_variants:
            product_mapping_status = "not-applicable"
        elif required_variants <= mapped_variants:
            product_mapping_status = "confirmed"
        elif required_variants & mapped_variants:
            product_mapping_status = "partial"
        else:
            product_mapping_status = "pending"
        known_printings = [printing for printing in printings if printing["finish"] in FINISHES]
        unknown_finish_printings = [printing for printing in printings if printing["finish"] == "unknown"]
        source_scopes = evidence_scopes(known_printings)

    def _build_finish_unit_part10():
        nonlocal pattern_status, printing, unresolved
        pattern_target_printings = [
            printing for printing in printings if printing["finish"] in {"reverse-holo", "mirror-holo"}
        ]
        patterned = [printing for printing in pattern_target_printings if printing.get("foilPattern")]
        if not pattern_target_printings:
            pattern_status = "not-applicable"
        elif len(patterned) == len(pattern_target_printings):
            pattern_status = "confirmed"
        elif patterned:
            pattern_status = "partial"
        else:
            pattern_status = "pending"
        unresolved = []
        if not all_claims_contradicted and not known_printings:
            unresolved.append("No positive finish evidence has been recorded for this set-number-language unit.")
        if unknown_finish_printings:
            unresolved.append(
                "One or more known physical printings still have unresolved finishes: "
                + ", ".join(printing["printingId"] for printing in unknown_finish_printings)
            )
        if source_scope_needs_owner(
            known_printings,
            source_scopes,
            (set_code, number, language),
            owner_finish_decisions,
        ):
            unresolved.append(
                "The source lists known finishes only. Unlisted alternatives remain unknown."
            )

    def _build_finish_unit_part11():
        nonlocal completeness_status, product
        if product_mapping_status in {"partial", "pending"}:
            unresolved.append(
                "One or more Cardmarket product variants are not mapped to a logical printing: "
                + ", ".join(sorted(required_variants - mapped_variants))
            )
        if pattern_status in {"partial", "pending"}:
            unresolved.append("The exact reverse- or mirror-holo pattern is not identified for every known printing of those types.")
        # A contradicted language-product claim is already resolved and cannot create a finish TODO.
        if all_claims_contradicted:
            completeness_status = "not-applicable"
        elif known_printings and (set_code, number, language) in owner_finish_decisions:
            completeness_status = "owner-adjudicated"
        elif known_printings:
            completeness_status = "positive-evidence-only"
        else:
            completeness_status = "pending"

    _build_finish_unit_part1()
    _build_finish_unit_part2()
    _build_finish_unit_part3()
    _build_finish_unit_part4()
    _build_finish_unit_part5()
    _build_finish_unit_part6()
    _build_finish_unit_part7()
    _build_finish_unit_part8()
    _build_finish_unit_part9()
    _build_finish_unit_part10()
    _build_finish_unit_part11()
    release_set_codes = {
        str(override["releaseSetCode"])
        for override in applicable_overrides
        if override.get("releaseSetCode")
    }
    if len(release_set_codes) > 1:
        raise ValueError(f"conflicting releaseSetCode overrides for {set_code} {number} {language}")
    return {
            "finishUnitId": finish_unit_id,
            "cardName": card_name,
            "setCode": set_code,
            "releaseSetCode": next(iter(release_set_codes), None),
            "setName": set_name,
            "number": number,
            "language": language,
            "products": products,
            "availableFinishes": available_finishes,
            "finishStatus": finish_status,
            "applicabilityStatus": "not-applicable" if all_claims_contradicted else "applicable",
            "availabilityStatus": (
                "not-applicable" if all_claims_contradicted else strongest_status(known_printings)
            ),
            "completenessStatus": completeness_status,
            "productMappingStatus": product_mapping_status,
            "patternStatus": pattern_status,
            "printings": printings,
            "unresolved": unresolved,
        }


def _build_finish_units(context: dict[str, Any]) -> list[dict[str, Any]]:
    grouped_units = context["grouped_units"]
    finish_units: list[dict[str, Any]] = []
    for finish_index, key in enumerate(sorted(grouped_units, key=group_sort_key)):
        finish_units.append(_build_finish_unit(context, finish_index, key))
    return finish_units




def _project_cards(cards: list[dict[str, Any]], finish_units: list[dict[str, Any]]) -> None:
    finish_lookup = {
        (unit["setCode"], unit["number"], unit["language"]): unit for unit in finish_units
    }
    for card in cards:
        if card.get("isCodeCard"):
            card["finishAvailability"] = {
                "scope": "not-applicable",
                "status": "not-applicable",
                "reason": "Online/live code cards do not have physical card finishes.",
            }
            continue
        token = variant_token(card)
        by_language: list[dict[str, Any]] = []
        for language in card.get("languages") or []:
            unit = finish_lookup[(str(card.get("setCode") or ""), str(card.get("number") or ""), language)]
            by_language.append(project_unit_onto_product(unit, token))
        union_finishes = [
            finish
            for finish in FINISHES
            if any(finish in row["availableFinishes"] for row in by_language)
        ]
        language_statuses = [row["status"] for row in by_language]
        applicable_statuses = [status for status in language_statuses if status != "not-applicable"]
        if language_statuses and not applicable_statuses:
            overall_status = "not-applicable"
        elif applicable_statuses and all(status == "confirmed" for status in applicable_statuses):
            overall_status = "confirmed"
        elif any(status != "pending" for status in applicable_statuses):
            overall_status = "partial"
        else:
            overall_status = "pending"
        card["finishAvailability"] = {
            "scope": (
                "this Cardmarket product variant, by listed language; full evidence is in "
                "verification/finish_units.json"
            ),
            "statusMeanings": {
                "confirmed/owner-attested/marketplace-claimed": "evidence attributes this finish to this product",
                "unmapped": "the card and language have this finish, but no product is attributed yet; it may be this one",
                "other-product": "the card and language have this finish, attributed to a different Cardmarket product",
                "pending": "no positive evidence for this finish anywhere in this set-number-language unit",
                "not-applicable": "this product-language claim is contradicted",
            },
            "status": overall_status,
            "availableFinishes": union_finishes,
            "unitAvailableFinishes": sorted(
                {finish for row in by_language for finish in row["unitAvailableFinishes"]},
                key=FINISHES.index,
            ),
            "byLanguage": by_language,
        }


def _build_finish_counts(
    cards_document: dict[str, Any],
    finish_units: list[dict[str, Any]],
    tcgdex_urls: list[str],
    fetch_errors: dict[str, str],
    generated_date: str,
) -> dict[str, int]:
    counts = {
        "totalFinishUnits": len(finish_units),
        "withConfirmedFinish": sum(unit["availabilityStatus"] == "confirmed" for unit in finish_units),
        "withOnlyMarketplaceClaim": sum(unit["availabilityStatus"] == "marketplace-claimed" for unit in finish_units),
        "pendingFinish": sum(unit["availabilityStatus"] == "pending" for unit in finish_units),
        "notApplicableFinish": sum(unit["availabilityStatus"] == "not-applicable" for unit in finish_units),
        "withOwnerAdjudication": sum(
            unit["completenessStatus"] == "owner-adjudicated" for unit in finish_units
        ),
        "withNonHolo": sum("non-holo" in unit["availableFinishes"] for unit in finish_units),
        "withHolo": sum("holo" in unit["availableFinishes"] for unit in finish_units),
        "withReverseHolo": sum("reverse-holo" in unit["availableFinishes"] for unit in finish_units),
        "withMirrorHolo": sum("mirror-holo" in unit["availableFinishes"] for unit in finish_units),
        "withBothNonHoloAndHolo": sum(
            {"non-holo", "holo"} <= set(unit["availableFinishes"]) for unit in finish_units
        ),
        "withUnresolvedProductMapping": sum(
            unit["productMappingStatus"] in {"partial", "pending"} for unit in finish_units
        ),
        "withAnyUnresolvedDetail": sum(bool(unit["unresolved"]) for unit in finish_units),
        "tcgdexUrlsRequested": len(tcgdex_urls),
        "tcgdexFetchErrors": len(fetch_errors),
    }
    cards_document["meta"]["finishVerification"] = {
        "description": "Positive finish availability by set number, language, and mapped Cardmarket product. See verification/finish_units.json.",
        "lastUpdated": generated_date,
        **counts,
    }
    notes = cards_document["meta"].setdefault("notes", [])
    generated_note_prefixes = (
        "variantAxes =",
        "variantAxes and hasReverseHolo are",
        "markings.role distinguishes",
    )
    language_notes = extract_language_notes(notes)
    notes = retained_finish_notes(notes, generated_note_prefixes, language_notes)
    notes.append(
        "variantAxes and hasReverseHolo are Cardmarket catalogue hints only. finishAvailability is the positive-evidence finish layer; pending never means a finish is proven not to exist."
    )
    notes.append(
        "markings.role distinguishes print-identity features, EX-era reverse-holo-treatment set logos, and later distribution-promo stamps such as prerelease, Staff, retailer, and Pokemon Center marks."
    )
    notes.extend(language_notes)
    cards_document["meta"]["notes"] = notes

    return counts


def extract_language_notes(notes: list[Any]) -> list[Any]:
    return [
        note for note in notes
        if str(note).startswith(("languagesConfirmed", "languagesRepositoryConfirmed"))
    ]


def retained_finish_notes(
    notes: list[Any], prefixes: tuple[str, ...], language_notes: list[Any]
) -> list[Any]:
    return [
        note for note in notes
        if not any(str(note).startswith(prefix) for prefix in prefixes)
        and note not in language_notes
    ]


def _build_finish_documents(
    finish_units: list[dict[str, Any]],
    counts: dict[str, int],
    fetch_errors: dict[str, str],
    generated_date: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    finish_document = {
        "meta": {
            "description": "One row per set code x collector number x language, with logical physical printings, their identifying metadata and release dates, and Cardmarket product mappings.",
            "generated": generated_date,
            "scope": "Physical cards only; online/live code cards are excluded.",
            "sourcePolicy": [
                "Only positive availability is asserted. pending means not yet established, never proven absent.",
                "A unit whose underlying product-language claims are all contradicted is not-applicable and is excluded from the finish-review queue.",
                "Every external source confirms named finishes only. Missing alternatives remain unknown.",
                "A collection-owner finish adjudication can close a finish list after every named finish has positive evidence.",
                "TCGdex variants=true is confirmation; false is ignored because upstream variant coverage is incomplete.",
                "TCGdex finish flags are set-number-language level and are not mapped to a Cardmarket V token without independent evidence or an unambiguous single product.",
                "Cardmarket Reverse Holo axes and rarity labels are retained as marketplace-claimed hints, not external confirmation.",
                "Printed identity features use markings.role=print-identity; EX-era set-logo stamps intrinsic to reverse holo use markings.role=reverse-holo-treatment; later promotional stamps use markings.role=distribution-promo.",
            ],
            "taxonomy": {
                "finish": list(FINISHES) + ["unknown"],
                "edition": ["1st Edition", "Unlimited"],
                "verificationStatus": ["confirmed", "owner-attested", "marketplace-claimed", "pending"],
                "availabilityStatus": ["confirmed", "owner-attested", "marketplace-claimed", "pending", "not-applicable"],
                "cardSize": ["standard", "jumbo", "unknown"],
                "markingRoles": ["print-identity", "reverse-holo-treatment", "distribution-promo"],
                "completenessStatus": ["owner-adjudicated", "positive-evidence-only", "pending", "not-applicable"],
            },
            "counts": counts,
            "fetchErrors": fetch_errors,
        },
        "units": finish_units,
    }

    review_rows = [
        {
            "finishUnitId": unit["finishUnitId"],
            "cardName": unit["cardName"],
            "setCode": unit["setCode"],
            "number": unit["number"],
            "language": unit["language"],
            "availabilityStatus": unit["availabilityStatus"],
            "availableFinishes": unit["availableFinishes"],
            "productMappingStatus": unit["productMappingStatus"],
            "patternStatus": unit["patternStatus"],
            "unmappedVariants": sorted(
                {
                    product["variant"]
                    for product in unit["products"]
                    if product["claimStatus"] != "contradicted"
                }
                - {
                    variant
                    for printing in unit["printings"]
                    for variant in printing["mappedVariants"]
                }
            ),
            "unresolved": unit["unresolved"],
        }
        for unit in finish_units
        if unit["unresolved"]
    ]
    # The queue's shape by language, generated rather than written down (#71). Working
    # FINISH_REVIEW.csv top to bottom re-derives the same source decision on every row, because
    # what can answer "which finishes exist" depends almost entirely on the language: TCGdex has no
    # Simplified Chinese at all and one Korean URL in the whole store, so a third of this queue is
    # not waiting to be asked, it is waiting for a different kind of source. See FINISH_SOURCES.md.
    pending_by_language = Counter(
        unit["language"] for unit in finish_units
        if unit["applicabilityStatus"] == "applicable"
        and unit["availabilityStatus"] == "pending"
    )
    review_document = {
        "meta": {
            "description": "Finish units that still need finish, pattern, marking, size, or Cardmarket-product mapping evidence.",
            "generated": generated_date,
            "count": len(review_rows),
            "pendingByLanguage": dict(sorted(pending_by_language.items(),
                                             key=lambda kv: (-kv[1], kv[0]))),
        },
        "units": review_rows,
    }

    combination_counts = Counter(" + ".join(unit["availableFinishes"]) or "pending" for unit in finish_units)
    pattern_counts = Counter(
        printing["foilPattern"] or "unidentified"
        for unit in finish_units
        for printing in unit["printings"]
        if printing["finish"] in {"holo", "reverse-holo", "mirror-holo"}
    )
    marking_role_counts = Counter(
        marking["role"]
        for unit in finish_units
        for printing in unit["printings"]
        for marking in (printing.get("markings") or [])
    )
    analysis = {
        "generated": generated_date,
        "note": "Counts are set-number-language finish units. Availability is positive-evidence-only and is not a proof of completeness.",
        "counts": counts,
        "finishCombinations": dict(sorted(combination_counts.items())),
        "foilPatterns": dict(sorted(pattern_counts.items())),
        "markingRoles": dict(sorted(marking_role_counts.items())),
        "bothNonHoloAndHolo": [
            {
                "finishUnitId": unit["finishUnitId"],
                "card": f"{unit['cardName']} ({unit['setCode']} {unit['number']})",
                "language": unit["language"],
            }
            for unit in finish_units
            if {"non-holo", "holo"} <= set(unit["availableFinishes"])
        ],
    }

    return finish_document, review_document, analysis, review_rows


def _render_finish_outputs(
    cards_document: dict[str, Any],
    finish_document: dict[str, Any],
    review_document: dict[str, Any],
    analysis: dict[str, Any],
    review_rows: list[dict[str, Any]],
) -> dict[Path, str]:
    csv_buffer = io.StringIO(newline="")
    writer = csv.writer(csv_buffer, lineterminator="\n")
    writer.writerow(
        [
            "finishUnitId",
            "cardName",
            "setCode",
            "number",
            "language",
            "availabilityStatus",
            "availableFinishes",
            "productMappingStatus",
            "patternStatus",
            "unmappedVariants",
            "unresolved",
        ]
    )
    for row in review_rows:
        writer.writerow(
            [
                row["finishUnitId"],
                row["cardName"],
                row["setCode"],
                row["number"],
                row["language"],
                row["availabilityStatus"],
                "; ".join(row["availableFinishes"]),
                row["productMappingStatus"],
                row["patternStatus"],
                "; ".join(row["unmappedVariants"]),
                " | ".join(row["unresolved"]),
            ]
        )
    return {
        OUTPUT_PATH: rendered_json(finish_document),
        REVIEW_JSON_PATH: rendered_json(review_document),
        REVIEW_CSV_PATH: csv_buffer.getvalue(),
        ANALYSIS_PATH: rendered_json(analysis),
        CARDS_PATH: rendered_json(cards_document),
    }


def _write_finish_outputs(outputs: dict[Path, str]) -> None:
    for path, body in outputs.items():
        path.write_text(body, encoding="utf-8", newline="\n")

def _finish_summary(
    counts: dict[str, int],
    review_rows: list[dict[str, Any]],
    tcgdex_data: dict[str, dict[str, Any]],
    tcgdex_urls: list[str],
    fetch_errors: dict[str, str],
    accepted_refresh: bool,
) -> int:
    print(f"finish units: {counts['totalFinishUnits']}")
    print(
        "availability: "
        f"confirmed={counts['withConfirmedFinish']} "
        f"marketplace-only={counts['withOnlyMarketplaceClaim']} "
        f"pending={counts['pendingFinish']} "
        f"not-applicable={counts['notApplicableFinish']}"
    )
    print(
        "finishes: "
        f"non-holo={counts['withNonHolo']} holo={counts['withHolo']} "
        f"reverse={counts['withReverseHolo']} mirror={counts['withMirrorHolo']} "
        f"both-base+holo={counts['withBothNonHoloAndHolo']}"
    )
    print(
        f"review units: {len(review_rows)}; unresolved product mappings: "
        f"{counts['withUnresolvedProductMapping']}"
    )
    print(f"TCGdex: {len(tcgdex_data)}/{len(tcgdex_urls)} fetched; errors={len(fetch_errors)}")
    if fetch_errors:
        for url, reason in sorted(fetch_errors.items())[:10]:
            print(f"  unreachable: {url} — {reason}", file=sys.stderr)
        # The artifacts written above are still internally consistent; what is missing is upstream
        # evidence nobody could reach. Exit 2 says "try again later" rather than "this is wrong".
        return 2
    if accepted_refresh:
        REFRESH_CANDIDATE_PATH.unlink(missing_ok=True)
    return 0

def main() -> int:
    if "--check" in sys.argv and ("--refresh" in sys.argv or "--accept-refresh" in sys.argv):
        raise ValueError("--check cannot be combined with refresh modes")
    context = _load_finish_context()
    cards_document = context["cards_document"]
    cards = context["cards"]
    tcgdex_urls = context["tcgdex_urls"]
    status = _resolve_tcgdex(context)
    if status is not None:
        return status
    tcgdex_data = context["tcgdex_data"]
    fetch_errors = context["fetch_errors"]
    accepted_refresh = context["accepted_refresh"]
    generated_date = latest_input_date(
        context["units"],
        context["overrides_document"],
        context["specimens_document"],
        context["adjudications_document"],
        context["snapshot_document"],
    )
    _prepare_finish_indexes(context)

    finish_units = _build_finish_units(context)
    _project_cards(cards, finish_units)
    counts = _build_finish_counts(
        cards_document, finish_units, tcgdex_urls, fetch_errors, generated_date
    )
    finish_document, review_document, analysis, review_rows = _build_finish_documents(
        finish_units, counts, fetch_errors, generated_date
    )
    outputs = _render_finish_outputs(
        cards_document, finish_document, review_document, analysis, review_rows
    )
    if "--check" in sys.argv:
        stale = [
            str(path.relative_to(ROOT))
            for path, body in outputs.items()
            if not path.exists() or path.read_text(encoding="utf-8") != body
        ]
        if stale:
            print(f"stale: {', '.join(stale)}")
            return 1
        print("finish artifacts are current")
    else:
        _write_finish_outputs(outputs)
    return _finish_summary(counts, review_rows, tcgdex_data, tcgdex_urls, fetch_errors, accepted_refresh)



def reproject() -> None:
    """Re-apply the card projection from the committed finish store, without network access.

    `main()` needs TCGdex to rebuild `finish_units.json`. The projection step does not: it is a
    pure function of the committed store. Exposing it separately lets the release gate assert
    that the published card summaries are reproducible from the store, and lets a projection
    fix be applied without a full re-fetch.
    """
    cards_document = read_json(CARDS_PATH)
    finish_units = read_json(OUTPUT_PATH)["units"]
    finish_lookup = {
        (unit["setCode"], unit["number"], unit["language"]): unit for unit in finish_units
    }

    for card in cards_document["cards"]:
        if card.get("isCodeCard"):
            card["finishAvailability"] = {
                "scope": "not-applicable",
                "status": "not-applicable",
                "reason": "Online/live code cards do not have physical card finishes.",
            }
            continue
        token = variant_token(card)
        by_language = [
            project_unit_onto_product(
                finish_lookup[
                    (str(card.get("setCode") or ""), str(card.get("number") or ""), language)
                ],
                token,
            )
            for language in card.get("languages") or []
        ]
        union_finishes = [
            finish for finish in FINISHES if any(finish in row["availableFinishes"] for row in by_language)
        ]
        language_statuses = [row["status"] for row in by_language]
        applicable = [status for status in language_statuses if status != "not-applicable"]
        if language_statuses and not applicable:
            overall_status = "not-applicable"
        elif applicable and all(status == "confirmed" for status in applicable):
            overall_status = "confirmed"
        elif any(status != "pending" for status in applicable):
            overall_status = "partial"
        else:
            overall_status = "pending"
        card["finishAvailability"] = {
            "scope": (
                "this Cardmarket product variant, by listed language; full evidence is in "
                "verification/finish_units.json"
            ),
            "statusMeanings": {
                "confirmed/owner-attested/marketplace-claimed": "evidence attributes this finish to this product",
                "unmapped": "the card and language have this finish, but no product is attributed yet; it may be this one",
                "other-product": "the card and language have this finish, attributed to a different Cardmarket product",
                "pending": "no positive evidence for this finish anywhere in this set-number-language unit",
                "not-applicable": "this product-language claim is contradicted",
            },
            "status": overall_status,
            "availableFinishes": union_finishes,
            "unitAvailableFinishes": sorted(
                {finish for row in by_language for finish in row["unitAvailableFinishes"]},
                key=FINISHES.index,
            ),
            "byLanguage": by_language,
        }

    write_json(CARDS_PATH, cards_document)
    reachable = {
        printing["printingId"]
        for card in cards_document["cards"]
        for row in (card.get("finishAvailability") or {}).get("byLanguage", [])
        for printing in row["printings"]
    }
    confirmed = {
        printing["printingId"]
        for unit in finish_units
        for printing in unit["printings"]
        if printing["verificationStatus"] == "confirmed"
    }
    print(f"reprojected {len(cards_document['cards'])} cards from {len(finish_units)} finish units")
    print(f"confirmed printings reachable from a product view: {len(confirmed & reachable)}/{len(confirmed)}")


if __name__ == "__main__":
    if "--reproject" in sys.argv:
        reproject()
        sys.exit(0)
    # Same contract as verification/verify_finish_sources.py, for the same reason: a caller has to
    # be able to tell "the source said something unexpected" from "the source could not be
    # reached". 2 means unreachable — retry later; the committed artifacts are not at fault (#35).
    sys.exit(main() or 0)
