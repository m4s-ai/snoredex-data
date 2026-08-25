#!/usr/bin/env python3
"""Discover and reconcile provider-native card records without a legacy seed (#136).

The reviewed contract is ``verification/card_discovery_adapters.json``. Network access occurs
only with ``--refresh``. Normal generation and CI checks replay committed immutable responses,
then match the resulting positive card records against ADR-0001 identities without mutating any
verdict store.

    python scripts/card_discovery.py --refresh --run-id 20260809T180000Z
    python scripts/card_discovery.py --refresh --run-id 20260809T180000Z --resume
    python scripts/card_discovery.py --refresh --run-id 20260809T180000Z --resume \
        --reuse-unfinished-from-run 20260808T180000Z
    python scripts/card_discovery.py
    python scripts/card_discovery.py --check
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

from bulbapedia_historical import HistoricalIndexError, parse_historical_index
from source_capabilities import schema_errors

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "verification" / "card_discovery_adapters.json"
SCHEMA_PATH = ROOT / "verification" / "card_discovery_schema.json"
CAPABILITY_PATH = ROOT / "verification" / "source_capability_graph.json"
GRAPH_PATH = ROOT / "verification" / "authoritative_graph.json"
CONFIRMED_SOURCES_PATH = ROOT / "verification" / "confirmed_sources.json"
SOURCE_FIRST_PRINTS_PATH = ROOT / "verification" / "source_first_prints.json"
ISSUE84_52POKE_PATH = (
    ROOT / "verification" / "evidence" / "issue-84-snorlax-alle-zh.json"
)
RUNS_DIR = ROOT / "verification" / "runs" / "card-discovery"
OUTPUT_PATH = ROOT / "verification" / "card_discovery_staging.json"
RECORDS_PATH = ROOT / "verification" / "card_discovery_records.jsonl"
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z$")
REQUEST_ACQUISITION_FIELDS = {
    "adapterId", "adapterVersion", "sliceId", "providerId", "surfaceId",
    "coverageEdgeId", "rawLocale", "endpoint", "queryParameters",
}
DETAIL_PATH_PATTERN = re.compile(r"/card-search/detail/([0-9]+)/?")
SET_SYMBOL_PATTERN = re.compile(r"_exp_([^./]+)\.(?:png|jpe?g|webp)$", re.IGNORECASE)
OFFICIAL_ARCHIVE_PATH_PATTERN = re.compile(
    r"^/(?P<locale>[a-z]{2})/gcc/archivio-carte/series/"
    r"(?P<set>[^/]+)/(?P<number>[^/]+)/?$",
    re.IGNORECASE,
)


class DiscoveryError(ValueError):
    """The card discovery contract or a retained run violates #136."""


class AsiaListParser(HTMLParser):
    """Extract the bounded result count, page count and official detail ids."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.detail_ids: list[str] = []
        self.result_count: int | None = None
        self.total_pages: int | None = None
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            match = DETAIL_PATH_PATTERN.search(values["href"] or "")
            if match:
                self.detail_ids.append(match.group(1))
        if tag == "p":
            classes = set((values.get("class") or "").split())
            if "resultNumber" in classes:
                self._capture = "count"
            elif "resultTotalPages" in classes:
                self._capture = "pages"

    def handle_endtag(self, tag: str) -> None:
        if tag == "p":
            self._capture = None

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text or self._capture is None:
            return
        numbers = re.findall(r"[0-9]+", text)
        if not numbers:
            return
        if self._capture == "count" and self.result_count is None:
            self.result_count = int(numbers[0])
        elif self._capture == "pages" and self.total_pages is None:
            self.total_pages = int(numbers[-1])


class AsiaDetailParser(HTMLParser):
    """Extract only source-native identity fields from one official detail page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.local_name: str | None = None
        self.collector_number: str | None = None
        self.card_image_url: str | None = None
        self.set_symbol_url: str | None = None
        self.expansion_code: str | None = None
        self._capture: str | None = None
        self._buffer: list[str] = []
        self._inside_evolve_marker = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "h1" and {"pageHeader", "cardDetail"}.issubset(classes):
            self._capture = "name"
            self._buffer = []
        elif tag == "span" and self._capture == "name" and "evolveMarker" in classes:
            self._inside_evolve_marker = True
        elif tag == "span" and "collectorNumber" in classes:
            self._capture = "number"
            self._buffer = []
        elif tag == "a" and values.get("href"):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(values["href"] or "").query)
            expansion_codes = query.get("expansionCodes", [])
            if len(expansion_codes) == 1 and expansion_codes[0]:
                self.expansion_code = expansion_codes[0]
        elif tag == "img" and values.get("src"):
            source = values["src"] or ""
            if "/card-img/mark/" in source:
                self.set_symbol_url = source
            elif "/card-img/" in source and self.card_image_url is None:
                self.card_image_url = source

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._inside_evolve_marker:
            self._inside_evolve_marker = False
            return
        if (tag == "h1" and self._capture == "name") or (
            tag == "span" and self._capture == "number"
        ):
            value = " ".join(part for part in self._buffer if part).strip()
            if self._capture == "name":
                self.local_name = value or None
            else:
                self.collector_number = value or None
            self._capture = None
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture is not None and not self._inside_evolve_marker and data.strip():
            self._buffer.append(data.strip())


class OfficialLocalizedListParser(HTMLParser):
    """Retain provider-native Italian archive result entries without claiming archive closure."""

    def __init__(self, raw_locale: str = "it") -> None:
        super().__init__(convert_charrefs=True)
        self.raw_locale = raw_locale
        self.query_echo: str | None = None
        self.entries: list[dict[str, Any]] = []
        self.has_results_container = False
        self.current_page: int | None = None
        self.total_pages: int | None = None
        self._inside_results = False
        self._current: dict[str, Any] | None = None
        self._pagination_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "input" and values.get("id") == "cardName":
            self.query_echo = values.get("value")
        if tag == "div" and values.get("id") == "cards-load-more":
            self._pagination_depth = 1
        elif tag == "div" and self._pagination_depth:
            self._pagination_depth += 1
        if tag == "ul" and values.get("id") == "cardResults":
            self.has_results_container = True
            self._inside_results = True
            return
        if not self._inside_results:
            return
        if tag == "a" and values.get("href"):
            href = values["href"] or ""
            path = urllib.parse.urlparse(href).path
            match = OFFICIAL_ARCHIVE_PATH_PATTERN.fullmatch(path)
            if match and match.group("locale").lower() == self.raw_locale.lower():
                raw_set_code = match.group("set")
                collector_number = match.group("number")
                self._current = {
                    "detailId": f"{raw_set_code}/{collector_number}",
                    "localName": None,
                    "rawSetCode": raw_set_code,
                    "localCollectorNumber": collector_number,
                    "cardImageUrl": None,
                    "setSymbolUrl": None,
                    "productScope": "physical-tcg",
                    "detailPath": path,
                    "recordSource": "localized-archive-list-entry",
                }
        elif tag == "img" and self._current is not None:
            self._current["cardImageUrl"] = values.get("src")
            self._current["localName"] = values.get("alt")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current is not None:
            self.entries.append(self._current)
            self._current = None
        elif tag == "ul" and self._inside_results:
            self._inside_results = False
        if tag == "div" and self._pagination_depth:
            self._pagination_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._pagination_depth:
            return
        match = re.fullmatch(r"\s*([0-9]+)\s+di\s+([0-9]+)\s*", data)
        if match:
            self.current_page = int(match.group(1))
            self.total_pages = int(match.group(2))


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def content_hash(value: bytes | Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def pagination_complete(pages: list[dict[str, Any]]) -> bool:
    if not pages:
        return False
    ordered = sorted(pages, key=lambda row: row["pageNo"])
    total_pages = ordered[0]["totalPages"]
    detail_ids = [
        detail_id for page in ordered for detail_id in page.get("detailIds", [])
    ]
    return (
        [row["pageNo"] for row in ordered] == list(range(1, total_pages + 1))
        and all(row["totalPages"] == total_pages for row in ordered)
        and len(detail_ids) == len(set(detail_ids))
    )


def capability_pin(capability: Any, surface_ids: Iterable[str] | None = None) -> str:
    """Hash the capability graph's *capabilities*, not the day it was written.

    The pin used the whole document, and the document carries `meta.generated`. So a retained run
    stopped validating the moment anyone regenerated the graph on a later date — no capability
    changed, only the calendar. Because a change to `units.json` flows into the source registry and
    from there into the graph, this fired on any ordinary write pass made the day after the graph
    was last written, and the documented command order regenerates the graph every time.

    Two things are dropped, and both are dropped for the same reason: they are not capabilities.

    `meta.generated` is the day the file was written. `sourceResolution` is the routing of whatever
    evidence rows the source registry happens to hold right now — one row per URL — so adding a
    single citation to any unit rewrote it and expired every retained run. A run was captured under
    a set of capabilities; which URLs exist today is not part of that set, and pinning it made
    ordinary evidence work impossible rather than making provenance stronger.

    What remains pinned is the contract itself: providers, surfaces, coverage edges, observations,
    and `meta.schemaVersion`. A surface, edge, boundary or absence scope that moves still changes
    this hash, which is the whole point of having one.
    """
    document = capability_slice(capability, surface_ids)
    return content_hash(document)


def capability_slice(capability: Any, surface_ids: Iterable[str] | None) -> dict[str, Any]:
    """The part of the capability graph a run depends on.

    `surface_ids` of `None` means the whole graph, which is what the pin meant before it was
    scoped. It is kept so a manifest written under the old rule can still be read and explained,
    never so a new run can be written that way.
    """
    document = {key: value for key, value in capability.items() if key != "sourceResolution"}
    document["meta"] = {
        key: value for key, value in document.get("meta", {}).items() if key != "generated"
    }
    if surface_ids is None:
        return document

    # `meta` carries global tallies — `counts`, `surfaceStates` — that move whenever any provider
    # gains a surface. Keeping them would have re-introduced the very coupling this scoping removes,
    # by a quieter route: the slice's own rows would be identical and the hash would still change.
    # Only the contract's identity survives into a scoped pin.
    document["meta"] = {
        key: value for key, value in document.get("meta", {}).items()
        if key in ("schema", "schemaVersion")
    }

    wanted = set(surface_ids)
    surfaces = [row for row in document.get("surfaces", []) if row["surfaceId"] in wanted]
    missing = wanted - {row["surfaceId"] for row in surfaces}
    if missing:
        raise DiscoveryError(
            f"run cites surfaces the capability graph does not declare: {sorted(missing)}"
        )
    providers = {row["providerId"] for row in surfaces}
    document["surfaces"] = surfaces
    document["providers"] = [
        row for row in document.get("providers", []) if row["providerId"] in providers
    ]
    document["coverageEdges"] = [
        row for row in document.get("coverageEdges", []) if row["surfaceId"] in wanted
    ]
    document["observations"] = [
        row for row in document.get("observations", []) if row["surfaceId"] in wanted
    ]
    return document


def manifest_surfaces(manifest: dict[str, Any]) -> list[str] | None:
    """Which surfaces a manifest was pinned against.

    Recorded explicitly since the pin was scoped. A manifest without the field predates the change
    and was pinned against the whole graph; `None` preserves that reading rather than silently
    re-scoping a hash somebody else computed.
    """
    recorded = manifest.get("capabilityGraphSurfaces")
    if recorded is None:
        return None
    return sorted(recorded)


def surfaces_used(requests: Iterable[dict[str, Any]]) -> list[str]:
    return sorted({row["surfaceId"] for row in requests if row.get("surfaceId")})



def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def render_projection(projection: dict[str, Any]) -> tuple[str, str]:
    records_text = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in projection["records"]
    )
    summary = {key: value for key, value in projection.items() if key != "records"}
    summary["recordsPath"] = "verification/card_discovery_records.jsonl"
    summary["recordsHash"] = content_hash(records_text.encode("utf-8"))
    return json.dumps(summary, ensure_ascii=False, indent=2) + "\n", records_text


def raw_key(provider_id: str, surface_id: str, raw_locale: str, raw_provider_id: str) -> str:
    return "|".join((provider_id, surface_id, raw_locale, raw_provider_id))


def parse_official_localized_entries(
    raw: bytes, raw_locale: str = "it"
) -> tuple[str | None, list[dict[str, Any]]]:
    text = raw.decode("utf-8-sig")
    if "Pardon Our Interruption" in text:
        raise DiscoveryError("official localized archive returned an access challenge")
    parser = OfficialLocalizedListParser(raw_locale)
    parser.feed(text)
    if not parser.has_results_container:
        raise DiscoveryError("official localized archive lacks its card result container")
    keys = [row["detailId"] for row in parser.entries]
    if len(keys) != len(set(keys)):
        raise DiscoveryError("official localized archive returned duplicate detail paths")
    return parser.query_echo, parser.entries


def parse_official_localized_page(
    raw: bytes, raw_locale: str = "it"
) -> tuple[str | None, list[dict[str, Any]], int, int]:
    text = raw.decode("utf-8-sig")
    if "Pardon Our Interruption" in text:
        raise DiscoveryError("official localized archive returned an access challenge")
    parser = OfficialLocalizedListParser(raw_locale)
    parser.feed(text)
    if not parser.has_results_container:
        raise DiscoveryError("official localized archive lacks its card result container")
    keys = [row["detailId"] for row in parser.entries]
    if len(keys) != len(set(keys)):
        raise DiscoveryError("official localized archive returned duplicate detail paths")
    if parser.current_page is None or parser.total_pages is None:
        raise DiscoveryError("official localized archive lacks pagination metadata")
    return parser.query_echo, parser.entries, parser.current_page, parser.total_pages


def parse_list(
    raw: bytes, response_format: str = "pokemon-asia-html", raw_locale: str = "it",
    adapter_version: str | None = None,
) -> dict[str, Any]:
    if response_format in {
        "52poke-scan-json", "confirmed-source-json", "source-first-print-json"
    }:
        value = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(value, list):
            raise DiscoveryError("confirmed-source card list did not return an array")
        detail_ids = []
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("detailId"), str):
                raise DiscoveryError("confirmed-source card row lacks a string detailId")
            detail_ids.append(item["detailId"])
        return {
            "resultCount": len(value),
            "totalPages": 1,
            "detailIds": list(dict.fromkeys(detail_ids)),
        }
    if response_format == "tcgdex-json":
        value = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(value, list):
            raise DiscoveryError("TCGdex card search did not return an array")
        detail_ids = []
        for item in value:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise DiscoveryError("TCGdex card search row lacks a string id")
            detail_ids.append(item["id"])
        return {
            "resultCount": len(value),
            "totalPages": 1,
            "detailIds": list(dict.fromkeys(detail_ids)),
        }
    if response_format == "pokemon-official-localized-html":
        _, entries, _, total_pages = parse_official_localized_page(raw, raw_locale)
        return {
            "resultCount": len(entries),
            "totalPages": 1 if adapter_version == "1.0.0" else total_pages,
            "detailIds": [row["detailId"] for row in entries],
        }
    if response_format != "pokemon-asia-html":
        raise DiscoveryError(f"unsupported card response format: {response_format}")
    parser = AsiaListParser()
    parser.feed(raw.decode("utf-8-sig"))
    detail_ids = list(dict.fromkeys(parser.detail_ids))
    if parser.result_count is None or parser.total_pages is None:
        raise DiscoveryError("official list page lacks result or pagination metadata")
    return {
        "resultCount": parser.result_count,
        "totalPages": parser.total_pages,
        "detailIds": detail_ids,
    }


def parse_detail(
    raw: bytes,
    raw_provider_id: str,
    response_format: str = "pokemon-asia-html",
    set_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if response_format in {
        "52poke-scan-json", "bulbapedia-historical-json", "confirmed-source-json",
        "source-first-print-json",
    }:
        value = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(value, dict) or value.get("detailId") != raw_provider_id:
            raise DiscoveryError(f"confirmed-source detail id differs: {raw_provider_id}")
        return value
    if response_format == "tcgdex-json":
        value = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(value, dict) or value.get("id") != raw_provider_id:
            raise DiscoveryError(f"TCGdex detail id differs: {raw_provider_id}")
        set_brief = value.get("set")
        if not isinstance(set_brief, dict) or not isinstance(set_brief.get("id"), str):
            raise DiscoveryError(f"TCGdex detail lacks a set id: {raw_provider_id}")
        if not isinstance(set_record, dict) or set_record.get("id") != set_brief["id"]:
            raise DiscoveryError(f"TCGdex detail lacks its retained set record: {raw_provider_id}")
        series = set_record.get("serie")
        if not isinstance(series, dict) or not isinstance(series.get("id"), str):
            raise DiscoveryError(f"TCGdex set lacks a series identity: {set_brief['id']}")
        product_scope = (
            "digital-pocket" if series["id"] == "tcgp" else "physical-tcg"
        )
        return {
            "detailId": raw_provider_id,
            "localName": value.get("name"),
            "rawSetCode": set_brief["id"],
            "localCollectorNumber": value.get("localId"),
            "cardImageUrl": value.get("image"),
            "setSymbolUrl": set_brief.get("symbol"),
            "productScope": product_scope,
            "setName": set_brief.get("name"),
            "setSeries": {"id": series["id"], "name": series.get("name")},
            "providerRecord": value,
            "providerSetIdentity": {
                "id": set_record["id"],
                "name": set_record.get("name"),
                "serie": {"id": series["id"], "name": series.get("name")},
                "releaseDate": set_record.get("releaseDate"),
            },
        }
    if response_format == "pokemon-official-localized-html":
        _, entries = parse_official_localized_entries(raw)
        matches = [row for row in entries if row["detailId"] == raw_provider_id]
        if len(matches) != 1:
            raise DiscoveryError(
                f"official localized list does not contain one {raw_provider_id} entry"
            )
        return matches[0]
    if response_format != "pokemon-asia-html":
        raise DiscoveryError(f"unsupported card response format: {response_format}")
    parser = AsiaDetailParser()
    parser.feed(raw.decode("utf-8-sig"))
    raw_set_code = parser.expansion_code
    if parser.set_symbol_url:
        match = SET_SYMBOL_PATTERN.search(parser.set_symbol_url)
        if raw_set_code is None and match:
            raw_set_code = match.group(1)
    return {
        "detailId": raw_provider_id,
        "localName": parser.local_name,
        "rawSetCode": raw_set_code,
        "localCollectorNumber": parser.collector_number,
        "cardImageUrl": parser.card_image_url,
        "setSymbolUrl": parser.set_symbol_url,
        "productScope": "physical-tcg",
    }


def issue84_52poke_records() -> dict[str, dict[str, Any]]:
    """Parse the reviewed positive T-Chinese rows retained from issue #84."""
    document = read_json(ISSUE84_52POKE_PATH)
    records: dict[str, dict[str, Any]] = {}
    for page_key, page in document.items():
        if not isinstance(page, dict) or not isinstance(page.get("url"), str):
            raise DiscoveryError(f"invalid 52poke scan page: {page_key}")
        for row in page.get("tchn", []):
            if not isinstance(row, dict):
                raise DiscoveryError(f"invalid 52poke T-Chinese row: {page_key}")
            set_code = row.get("setcode")
            number = row.get("num")
            if (
                not isinstance(set_code, str)
                or not set_code.strip()
                or not isinstance(number, str)
                or not re.fullmatch(r"\d+/\d+", number)
            ):
                continue
            detail_id = "|".join((page_key, set_code, number))
            if detail_id in records:
                raise DiscoveryError(f"duplicate 52poke scan identity: {detail_id}")
            records[detail_id] = {
                "detailId": detail_id,
                "localName": "卡比獸",
                "rawSetCode": set_code,
                "localCollectorNumber": number,
                "cardImageUrl": None,
                "setSymbolUrl": None,
                "productScope": "physical-tcg",
                "sourceUrl": page["url"],
                "sourcePageKey": page_key,
                "releaseDate": row.get("date") or None,
                "rarity": row.get("rarity") or None,
                "providerRecord": row,
            }
    return records


def validate_contract(
    contract: dict[str, Any], capability: dict[str, Any], identity: dict[str, Any]
) -> None:
    schema = read_json(SCHEMA_PATH)
    errors = schema_errors(contract, schema, schema)
    if errors:
        raise DiscoveryError(
            "contract violates card_discovery_schema.json:\n  - " + "\n  - ".join(errors[:30])
        )

    providers = {row["providerId"] for row in capability["providers"]}
    surfaces = {row["surfaceId"]: row for row in capability["surfaces"]}
    edges = {row["edgeId"]: row for row in capability["coverageEdges"]}
    releases = {row["cardReleaseId"] for row in identity["cardReleases"]}
    seen_adapters: set[str] = set()
    seen_slices: set[str] = set()
    seen_retained_units: set[str] = set()
    seen_retained_prints: set[str] = set()
    seen_retained_records: set[str] = set()
    active_surfaces: set[str] = set()

    for adapter in contract["adapters"]:
        adapter_id = adapter["adapterId"]
        if adapter_id in seen_adapters:
            raise DiscoveryError(f"duplicate adapterId {adapter_id}")
        seen_adapters.add(adapter_id)
        response_format = adapter.get("responseFormat", "pokemon-asia-html")
        if response_format not in {
            "52poke-scan-json", "bulbapedia-historical-json", "confirmed-source-json",
            "pokemon-asia-html", "pokemon-official-localized-html",
            "source-first-print-json", "tcgdex-json",
        }:
            raise DiscoveryError(f"adapter {adapter_id} has an unsupported response format")
        if response_format == "tcgdex-json" and not adapter.get("setEndpointTemplate"):
            raise DiscoveryError(f"adapter {adapter_id} requires a set detail endpoint")
        if response_format == "bulbapedia-historical-json" and (
            not isinstance(adapter.get("revisionId"), int)
            or not isinstance(adapter.get("pageTitle"), str)
        ):
            raise DiscoveryError(f"adapter {adapter_id} lacks its page title or revision id")
        if adapter["providerId"] not in providers:
            raise DiscoveryError(f"adapter {adapter_id} names unknown provider")
        surface = surfaces.get(adapter["surfaceId"])
        if not surface or surface["providerId"] != adapter["providerId"]:
            raise DiscoveryError(f"adapter {adapter_id} does not resolve to its provider surface")
        blocked_replay = (
            response_format == "confirmed-source-json"
            and surface["state"] == "blocked-by-browser"
        )
        if surface["state"] not in {"active", "incomplete"} and not (
            blocked_replay
        ):
            raise DiscoveryError(
                f"adapter {adapter_id} requires a usable registered surface {adapter['surfaceId']}"
            )
        active_surfaces.add(adapter["surfaceId"])
        for slice_row in adapter["slices"]:
            slice_id = slice_row["sliceId"]
            if slice_id in seen_slices:
                raise DiscoveryError(f"duplicate sliceId {slice_id}")
            seen_slices.add(slice_id)
            retained_unit_ids = slice_row.get("retainedUnitIds", [])
            retained_print_ids = slice_row.get("retainedPrintIds", [])
            retained_record_ids = slice_row.get("retainedRecordIds", [])
            if response_format in {"bulbapedia-historical-json", "confirmed-source-json"}:
                if len(slice_row["nameQueries"]) != 1 or not retained_unit_ids:
                    raise DiscoveryError(
                        f"slice {slice_id} needs one name query and retained unit ids"
                    )
                duplicates = seen_retained_units.intersection(retained_unit_ids)
                if duplicates:
                    raise DiscoveryError(
                        f"retained units occur in more than one slice: {sorted(duplicates)}"
                    )
                seen_retained_units.update(retained_unit_ids)
                confirmed_ids = {
                    row["unitId"] for row in read_json(CONFIRMED_SOURCES_PATH)
                }
                missing_units = set(retained_unit_ids) - confirmed_ids
                if missing_units:
                    raise DiscoveryError(
                        f"slice {slice_id} names unknown confirmed units: {sorted(missing_units)}"
                    )
                if response_format == "bulbapedia-historical-json":
                    set_names = slice_row.get("retainedSetNames", {})
                    if set(set_names) != set(retained_unit_ids):
                        raise DiscoveryError(
                            f"slice {slice_id} must map every retained unit to an index set name"
                        )
            elif response_format == "source-first-print-json":
                if len(slice_row["nameQueries"]) != 1 or not retained_print_ids:
                    raise DiscoveryError(
                        f"slice {slice_id} needs one name query and retained print ids"
                    )
                duplicates = seen_retained_prints.intersection(retained_print_ids)
                if duplicates:
                    raise DiscoveryError(
                        f"retained prints occur in more than one slice: {sorted(duplicates)}"
                    )
                seen_retained_prints.update(retained_print_ids)
                known_prints = {
                    row["printId"] for row in read_json(SOURCE_FIRST_PRINTS_PATH)["prints"]
                }
                missing_prints = set(retained_print_ids) - known_prints
                if missing_prints:
                    raise DiscoveryError(
                        f"slice {slice_id} names unknown source-first prints: "
                        f"{sorted(missing_prints)}"
                    )
            elif response_format == "52poke-scan-json":
                if len(slice_row["nameQueries"]) != 1 or not retained_record_ids:
                    raise DiscoveryError(
                        f"slice {slice_id} needs one name query and retained record ids"
                    )
                duplicates = seen_retained_records.intersection(retained_record_ids)
                if duplicates:
                    raise DiscoveryError(
                        f"retained records occur in more than one slice: {sorted(duplicates)}"
                    )
                seen_retained_records.update(retained_record_ids)
                missing_records = set(retained_record_ids) - set(issue84_52poke_records())
                if missing_records:
                    raise DiscoveryError(
                        f"slice {slice_id} names unknown 52poke records: "
                        f"{sorted(missing_records)}"
                    )
            elif retained_unit_ids or retained_print_ids or retained_record_ids:
                raise DiscoveryError(
                    f"slice {slice_id} uses retained ids with a live-response adapter"
                )
            edge = edges.get(slice_row["coverageEdgeId"])
            if not edge or edge["surfaceId"] != adapter["surfaceId"]:
                raise DiscoveryError(f"slice {slice_id} does not resolve to its surface edge")
            coverage = edge["coverage"]
            for field, value in (
                ("localities", slice_row["locality"]),
                ("languages", slice_row["language"]),
                ("scripts", slice_row["script"]),
            ):
                if value not in coverage[field] and "MULTIPLE" not in coverage[field]:
                    raise DiscoveryError(f"slice {slice_id} exceeds edge {field}: {value}")
            if response_format == "bulbapedia-historical-json":
                if "set" not in coverage["productCategories"]:
                    raise DiscoveryError(
                        f"historical replay slice {slice_id} lacks bounded set coverage"
                    )
                if "set-existence" not in edge["positiveEvidenceCapabilities"]:
                    raise DiscoveryError(
                        f"historical replay slice {slice_id} lacks positive set capability"
                    )
            else:
                if "card" not in coverage["productCategories"]:
                    raise DiscoveryError(f"slice {slice_id} does not resolve to card coverage")
                if "card-existence" not in edge["positiveEvidenceCapabilities"]:
                    raise DiscoveryError(f"slice {slice_id} lacks positive card capability")

    assertion_keys: set[str] = set()
    for assertion in contract["setCodeAssertions"]:
        key = raw_key(
            assertion["providerId"], assertion["surfaceId"],
            assertion["rawLocale"], assertion["rawSetCode"],
        )
        if key in assertion_keys:
            raise DiscoveryError(f"duplicate set-code assertion {key}")
        assertion_keys.add(key)
        if assertion["surfaceId"] not in active_surfaces:
            raise DiscoveryError(f"set-code assertion {key} is outside active adapters")

    mapping_keys: set[str] = set()
    for mapping in contract["explicitMappings"]:
        key = raw_key(
            mapping["providerId"], mapping["surfaceId"],
            mapping["rawLocale"], mapping["rawProviderId"],
        )
        if key in mapping_keys:
            raise DiscoveryError(f"duplicate explicit mapping {key}")
        mapping_keys.add(key)
        if mapping["surfaceId"] not in active_surfaces:
            raise DiscoveryError(f"mapping {key} is outside active adapters")
        if mapping["targetCardReleaseId"] not in releases:
            raise DiscoveryError(f"mapping {key} names unknown card release")

    seen_gaps: set[str] = set()
    for gap in contract["gaps"]:
        if gap["gapId"] in seen_gaps:
            raise DiscoveryError(f"duplicate gapId {gap['gapId']}")
        seen_gaps.add(gap["gapId"])
        if gap["providerId"] not in providers:
            raise DiscoveryError(f"gap {gap['gapId']} names unknown provider")
        if gap["surfaceId"] is not None:
            surface = surfaces.get(gap["surfaceId"])
            if not surface or surface["providerId"] != gap["providerId"]:
                raise DiscoveryError(f"gap {gap['gapId']} does not resolve to its provider surface")


def load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from authoritative_graph import identity_view

    contract = read_json(CONTRACT_PATH)
    capability = read_json(CAPABILITY_PATH)
    identity = identity_view(read_json(GRAPH_PATH))
    validate_contract(contract, capability, identity)
    return contract, capability, identity


def acquisition_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Return only the contract fields that can change retained provider bytes."""
    value = json.loads(json.dumps(contract))
    value["meta"].pop("coverageVersion")
    value["meta"].pop("reviewedAt")
    value["explicitMappings"] = []
    value["gaps"] = []
    return value


def normalize_record(
    adapter: dict[str, Any],
    slice_row: dict[str, Any],
    request: dict[str, Any],
    source_record: dict[str, Any],
    identity_releases: list[dict[str, Any]],
    mappings: dict[str, dict[str, Any]],
    assertions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    raw_provider_id = str(source_record.get("detailId") or "")
    stable_key = raw_key(
        adapter["providerId"], adapter["surfaceId"], slice_row["rawLocale"], raw_provider_id
    )
    record_id = "raw-card:" + hashlib.sha256(stable_key.encode("utf-8")).hexdigest()[:24]
    local_name = source_record.get("localName")
    raw_set_code = source_record.get("rawSetCode")
    local_number = source_record.get("localCollectorNumber")
    assertion = assertions.get(raw_key(
        adapter["providerId"], adapter["surfaceId"], slice_row["rawLocale"],
        str(raw_set_code or ""),
    ))
    proposed_set_code = (
        assertion["assertedLocalSetCode"] if assertion is not None else raw_set_code
    )
    mapping = mappings.get(stable_key)
    source_url = source_record.get("sourceUrl")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        source_url = adapter["detailEndpointTemplate"].format(
            rawLocale=slice_row["rawLocale"], rawProviderId=raw_provider_id
        )
    locality_evidence_mode = slice_row.get(
        "localityEvidenceMode", "physical-locality"
    )
    exclusions = [
        row for row in slice_row["positiveNameExclusions"]
        if isinstance(local_name, str) and local_name.startswith(row["prefix"])
    ]
    exact_matches = [
        row for row in identity_releases
        if row.get("locality") == slice_row["locality"]
        and row.get("language") == slice_row["language"]
        and row.get("localSetCode") == proposed_set_code
        and row.get("localNumber") == local_number
    ]
    source_matches = [
        row for row in identity_releases
        if source_url in row.get("sourceRecords", [])
    ]
    missing = [
        field for field, value in (
            ("detailId", raw_provider_id), ("localName", local_name),
            ("rawSetCode", raw_set_code), ("localCollectorNumber", local_number),
        ) if not isinstance(value, str) or not value.strip()
    ]

    equivalence_proposals: list[dict[str, Any]] = []
    target = None
    if source_record.get("productScope") == "digital-pocket":
        bucket = "positively-excluded"
        bucket_basis = "source record explicitly identifies the digital-only Pokémon TCG Pocket product"
    elif exclusions:
        bucket = "positively-excluded"
        bucket_basis = exclusions[0]["reason"]
    elif missing:
        bucket = "needs-evidence"
        bucket_basis = "required source-native identity field is missing: " + ", ".join(missing)
    elif locality_evidence_mode == "unqualified-language":
        bucket = "needs-evidence"
        bucket_basis = (
            f"the provider locale establishes {slice_row['language']} language only; physical "
            "locality remains unresolved"
        )
    elif locality_evidence_mode == "market-only":
        bucket = "needs-evidence"
        bucket_basis = (
            "the retained Brazilian market record establishes a positive listing, not a "
            "distinct printed Brazilian physical locality"
        )
    elif mapping and mapping["mode"] == "equivalence-proposal":
        bucket = "ambiguous"
        bucket_basis = mapping["evidence"]
        equivalence_proposals.append({
            "targetCardReleaseId": mapping["targetCardReleaseId"],
            "evidence": mapping["evidence"],
            "destructiveMergeAllowed": False,
        })
    elif mapping and mapping["mode"] == "exact-match":
        bucket = "matched"
        bucket_basis = mapping["evidence"]
        target = mapping["targetCardReleaseId"]
    elif len(source_matches) == 1:
        bucket = "matched"
        bucket_basis = "exact provider detail URL already establishes one ADR-0001 card release"
        target = source_matches[0]["cardReleaseId"]
    elif len(source_matches) > 1:
        bucket = "ambiguous"
        bucket_basis = "one provider detail URL establishes more than one ADR-0001 card release"
        equivalence_proposals.extend({
            "targetCardReleaseId": row["cardReleaseId"],
            "evidence": bucket_basis,
            "destructiveMergeAllowed": False,
        } for row in source_matches)
    elif len(exact_matches) == 1:
        bucket = "matched"
        bucket_basis = "exact locality, language, asserted local set code, and collector number tuple"
        target = exact_matches[0]["cardReleaseId"]
    elif len(exact_matches) > 1:
        bucket = "ambiguous"
        bucket_basis = "more than one ADR-0001 card release has the exact local identity tuple"
        equivalence_proposals.extend({
            "targetCardReleaseId": row["cardReleaseId"],
            "evidence": bucket_basis,
            "destructiveMergeAllowed": False,
        } for row in exact_matches)
    else:
        bucket = "new-candidate"
        bucket_basis = "positive provider-native card detail; no existing exact local identity tuple"

    list_hashes = sorted({page["responseHash"] for page in request["pages"]})
    detail = next(
        row for row in request["details"] if row["rawProviderId"] == raw_provider_id
    )
    retained_set = next(
        (row for row in request.get("sets", []) if row["rawSetCode"] == raw_set_code),
        None,
    )
    return {
        "recordId": record_id,
        "stableKey": stable_key,
        "identityHintHash": content_hash({
            "locality": slice_row["locality"], "language": slice_row["language"],
            "localSetCode": proposed_set_code, "localCollectorNumber": local_number,
            "localName": local_name,
        }),
        "providerId": adapter["providerId"],
        "surfaceId": adapter["surfaceId"],
        "coverageEdgeId": slice_row["coverageEdgeId"],
        "sourceUrl": source_url,
        "queryParameters": request["queryParameters"],
        "rawProviderId": raw_provider_id,
        "rawLocale": slice_row["rawLocale"],
        "locality": slice_row["locality"],
        "localityEvidenceMode": locality_evidence_mode,
        "retrievedAt": request["retrievedAt"],
        "listResponseHashes": list_hashes,
        "detailResponseHash": detail["responseHash"],
        "setResponseHash": None if retained_set is None else retained_set["responseHash"],
        "recordHash": content_hash(source_record),
        "runId": request["runId"],
        "raw": {
            "localName": local_name,
            "rawSetCode": raw_set_code,
            "localCollectorNumber": local_number,
            "cardImageUrl": source_record.get("cardImageUrl"),
            "setSymbolUrl": source_record.get("setSymbolUrl"),
        },
        "sourceRecord": source_record,
        "bucket": bucket,
        "bucketBasis": bucket_basis,
        "normalizationProposal": {
            "entityType": "card-release",
            "locality": slice_row["locality"],
            "localityEvidenceMode": locality_evidence_mode,
            "language": slice_row["language"],
            "script": slice_row["script"],
            "localName": local_name,
            "rawSetCode": raw_set_code,
            "assertedLocalSetCode": proposed_set_code,
            "setCodeAssertion": None if assertion is None else {
                "assetUrl": assertion["assetUrl"],
                "evidence": assertion["evidence"],
            },
            "localCollectorNumber": local_number,
            "targetCardReleaseId": target,
            "equivalenceProposals": equivalence_proposals,
            "destructiveMergeAllowed": False,
            "verdictMutationAllowed": False,
        },
    }


def diff_records(current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> dict[str, Any]:
    current_by_key = {row["stableKey"]: row for row in current}
    previous_by_key = {row["stableKey"]: row for row in previous}
    added = set(current_by_key) - set(previous_by_key)
    disappeared = set(previous_by_key) - set(current_by_key)
    changed = sorted(
        key for key in set(current_by_key) & set(previous_by_key)
        if current_by_key[key]["recordHash"] != previous_by_key[key]["recordHash"]
    )
    old_hints: dict[str, list[str]] = defaultdict(list)
    new_hints: dict[str, list[str]] = defaultdict(list)
    for key in disappeared:
        old_hints[previous_by_key[key]["identityHintHash"]].append(key)
    for key in added:
        new_hints[current_by_key[key]["identityHintHash"]].append(key)
    rekeyed = []
    for hint in sorted(set(old_hints) & set(new_hints)):
        old_keys = sorted(old_hints[hint])
        new_keys = sorted(new_hints[hint])
        pairs = (
            [(old_key, new_keys[0]) for old_key in old_keys]
            if len(new_keys) == 1 else zip(old_keys, new_keys)
        )
        used_new_keys = set()
        for old_key, new_key in pairs:
            rekeyed.append({"from": old_key, "to": new_key, "identityHintHash": hint})
            disappeared.remove(old_key)
            used_new_keys.add(new_key)
        added.difference_update(used_new_keys)
    locality_deltas = [
        {
            "stableKey": key,
            "from": previous_by_key[key].get("locality"),
            "to": current_by_key[key].get("locality"),
            "fromEvidenceMode": previous_by_key[key].get(
                "localityEvidenceMode", "physical-locality"
            ),
            "toEvidenceMode": current_by_key[key].get(
                "localityEvidenceMode", "physical-locality"
            ),
        }
        for key in sorted(set(current_by_key) & set(previous_by_key))
        if (
            previous_by_key[key].get("locality") != current_by_key[key].get("locality")
            or previous_by_key[key].get(
                "localityEvidenceMode", "physical-locality"
            ) != current_by_key[key].get(
                "localityEvidenceMode", "physical-locality"
            )
        )
    ]
    return {
        "added": sorted(added),
        "changed": changed,
        "disappeared": sorted(disappeared),
        "rekeyedCandidates": rekeyed,
        "localityDeltas": locality_deltas,
        "counts": {
            "added": len(added), "changed": len(changed),
            "disappeared": len(disappeared), "rekeyedCandidates": len(rekeyed),
            "localityDeltas": len(locality_deltas),
        },
    }


def checked_raw_path(run_dir: Path, relative: str) -> Path:
    path = (run_dir / relative).resolve()
    if (run_dir / "raw").resolve() not in path.parents:
        raise DiscoveryError(f"raw response escapes run raw directory: {relative}")
    return path


def build_projection(
    contract: dict[str, Any], capability: dict[str, Any], identity: dict[str, Any],
    manifest: dict[str, Any], run_dir: Path, previous: dict[str, Any] | None,
) -> dict[str, Any]:
    adapters = {row["adapterId"]: row for row in contract["adapters"]}
    slices = {
        row["sliceId"]: (adapter, row)
        for adapter in contract["adapters"] for row in adapter["slices"]
    }
    mappings = {
        raw_key(row["providerId"], row["surfaceId"], row["rawLocale"], row["rawProviderId"]): row
        for row in contract["explicitMappings"]
    }
    assertions = {
        raw_key(row["providerId"], row["surfaceId"], row["rawLocale"], row["rawSetCode"]): row
        for row in contract["setCodeAssertions"]
    }
    if manifest.get("contractHash") != content_hash(contract):
        raise DiscoveryError(f"run {manifest.get('runId')} was captured under another contract")
    if manifest.get("capabilityGraphHash") != capability_pin(
            capability, manifest_surfaces(manifest)):
        raise DiscoveryError(f"run {manifest.get('runId')} was captured under another capability graph")
    if manifest.get("coverageVersion") != contract["meta"]["coverageVersion"]:
        raise DiscoveryError(f"run {manifest.get('runId')} has another coverage version")
    expected_slice_ids = set(slices)
    request_slice_ids = [row.get("sliceId") for row in manifest["requests"]]
    if set(request_slice_ids) != expected_slice_ids or len(request_slice_ids) != len(
        expected_slice_ids
    ):
        raise DiscoveryError("run requests do not exactly cover adapter slices")

    records: list[dict[str, Any]] = []
    run_errors: list[dict[str, Any]] = list(manifest.get("failures", []))
    slice_rows = []
    seen_keys: set[str] = set()
    for request in sorted(manifest["requests"], key=lambda row: row["sliceId"]):
        pair = slices.get(request["sliceId"])
        adapter = adapters.get(request["adapterId"])
        if not pair or not adapter or pair[0]["adapterId"] != request["adapterId"]:
            raise DiscoveryError(f"run request has unknown slice {request['sliceId']}")
        slice_row = pair[1]
        response_format = adapter.get("responseFormat", "pokemon-asia-html")
        expected_list = adapter["listEndpointTemplate"].format(rawLocale=slice_row["rawLocale"])
        if request.get("endpoint") != expected_list:
            raise DiscoveryError(f"run request endpoint differs for {request['sliceId']}")

        slice_records: list[dict[str, Any]] = []
        terminal_state = "blocked-by-source"
        source_failure_state = "source-failed" if request.get("error") else None
        if request.get("error") is None:
            discovered_ids: list[str] = []
            list_hashes: set[str] = set()
            pages_by_query: dict[str, list[dict[str, Any]]] = defaultdict(list)
            pagination_failed = False
            for page in request["pages"]:
                raw = checked_raw_path(run_dir, page["rawPath"]).read_bytes()
                if content_hash(raw) != page["responseHash"]:
                    raise DiscoveryError(f"list response hash mismatch: {page['rawPath']}")
                if response_format == "bulbapedia-historical-json":
                    try:
                        positive_sets = parse_historical_index(
                            raw,
                            slice_row["language"],
                            expected_revision=adapter["revisionId"],
                            expected_title=adapter["pageTitle"],
                        )
                    except HistoricalIndexError as error:
                        raise DiscoveryError(str(error)) from error
                    parsed = {
                        "resultCount": len(slice_row["retainedUnitIds"]),
                        "totalPages": 1,
                        "detailIds": slice_row["retainedUnitIds"],
                    }
                    if page.get("parsedPositiveSetCount") != len(positive_sets):
                        raise DiscoveryError(
                            f"historical set accounting drift: {page['rawPath']}"
                        )
                else:
                    parsed = parse_list(
                        raw, response_format, slice_row["rawLocale"],
                        adapter.get("adapterVersion"),
                    )
                if parsed != {
                    "resultCount": page["resultCount"],
                    "totalPages": page["totalPages"],
                    "detailIds": page["detailIds"],
                }:
                    raise DiscoveryError(f"list parse drift: {page['rawPath']}")
                list_hashes.add(page["responseHash"])
                discovered_ids.extend(page["detailIds"])
                pages_by_query[page["query"]].append(page)
            for query in slice_row["nameQueries"]:
                pages = pages_by_query.get(query, [])
                if not pagination_complete(pages):
                    pagination_failed = True
                    run_errors.append({
                        "code": "incomplete-pagination", "sliceId": request["sliceId"],
                        "query": query, "meaning": "needs-evidence; never a closed catalogue",
                    })
            discovered_unique = sorted(
                set(discovered_ids),
                key=(lambda value: int(value))
                if response_format == "pokemon-asia-html" else None,
            )
            details = {row["rawProviderId"]: row for row in request["details"]}
            if set(details) != set(discovered_unique):
                raise DiscoveryError(f"detail accounting differs for {request['sliceId']}")
            retained_sets: dict[str, dict[str, Any]] = {}
            for retained_set in request.get("sets", []):
                raw = checked_raw_path(run_dir, retained_set["rawPath"]).read_bytes()
                if content_hash(raw) != retained_set["responseHash"]:
                    raise DiscoveryError(f"set response hash mismatch: {retained_set['rawPath']}")
                value = json.loads(raw.decode("utf-8-sig"))
                if not isinstance(value, dict) or value.get("id") != retained_set["rawSetCode"]:
                    raise DiscoveryError(f"set parse drift: {retained_set['rawPath']}")
                retained_sets[retained_set["rawSetCode"]] = value
            discovered_set_codes: set[str] = set()
            for raw_provider_id in discovered_unique:
                detail = details[raw_provider_id]
                raw = checked_raw_path(run_dir, detail["rawPath"]).read_bytes()
                if content_hash(raw) != detail["responseHash"]:
                    raise DiscoveryError(f"detail response hash mismatch: {detail['rawPath']}")
                set_record = None
                if response_format == "tcgdex-json":
                    value = json.loads(raw.decode("utf-8-sig"))
                    set_brief = value.get("set") if isinstance(value, dict) else None
                    raw_set_code = set_brief.get("id") if isinstance(set_brief, dict) else None
                    if not isinstance(raw_set_code, str):
                        raise DiscoveryError(f"TCGdex detail lacks a set id: {raw_provider_id}")
                    discovered_set_codes.add(raw_set_code)
                    set_record = retained_sets.get(raw_set_code)
                source_record = parse_detail(
                    raw, raw_provider_id, response_format, set_record
                )
                record = normalize_record(
                    adapter, slice_row, request, source_record, identity["cardReleases"],
                    mappings, assertions,
                )
                if record["stableKey"] in seen_keys:
                    raise DiscoveryError(f"internal stable-key collision: {record['stableKey']}")
                seen_keys.add(record["stableKey"])
                slice_records.append(record)
                records.append(record)

            if response_format == "tcgdex-json" and set(retained_sets) != discovered_set_codes:
                raise DiscoveryError(f"set accounting differs for {request['sliceId']}")

            used_assertions = {
                row["normalizationProposal"]["rawSetCode"]
                for row in slice_records if row["normalizationProposal"]["setCodeAssertion"]
            }
            assets = {row["rawSetCode"]: row for row in request.get("assets", [])}
            if set(assets) != used_assertions:
                raise DiscoveryError(f"set-symbol asset accounting differs for {request['sliceId']}")
            for asset in assets.values():
                raw = checked_raw_path(run_dir, asset["rawPath"]).read_bytes()
                if content_hash(raw) != asset["responseHash"]:
                    raise DiscoveryError(f"set-symbol response hash mismatch: {asset['rawPath']}")
                assertion = assertions[raw_key(
                    adapter["providerId"], adapter["surfaceId"], slice_row["rawLocale"],
                    asset["rawSetCode"],
                )]
                if asset["url"] != assertion["assetUrl"]:
                    raise DiscoveryError(f"set-symbol URL differs for {asset['rawSetCode']}")

            if pagination_failed:
                terminal_state = "needs-evidence"
                source_failure_state = "source-failed"
            elif not slice_records:
                run_errors.append({
                    "code": "zero-result", "sliceId": request["sliceId"],
                    "meaning": "source-failed/needs-evidence; never negative evidence",
                })
                terminal_state = "needs-evidence"
                source_failure_state = "source-failed"
            elif request["checkpoint"].get("complete") is not True:
                run_errors.append({
                    "code": "incomplete-checkpoint", "sliceId": request["sliceId"],
                    "meaning": "needs-evidence; never a closed catalogue",
                })
                terminal_state = "needs-evidence"
            else:
                terminal_state = "complete"

        accounting = Counter(row["bucket"] for row in slice_records)
        fetched = len(slice_records)
        accounted = sum(accounting.values())
        if fetched != accounted:
            raise DiscoveryError(f"slice {request['sliceId']} failed accounting")
        slice_rows.append({
            "sliceId": request["sliceId"],
            "adapterId": request["adapterId"],
            "terminalState": terminal_state,
            "sourceFailureState": source_failure_state,
            "terminalMeaning": (
                (
                    "every reviewed retained positive record in this browser-blocked frontier "
                    "was replayed and accounted; marketplace or provider-universe completeness "
                    "is not claimed"
                    if response_format == "confirmed-source-json" else
                    "every card frontier backed by the pinned historical language index was "
                    "replayed and accounted; non-expansion products and absence are not claimed"
                    if response_format == "bulbapedia-historical-json" else
                    "every reviewed retained positive source-first print was replayed and "
                    "accounted; neighbouring cards, variants, products and era completeness "
                    "are not claimed"
                    if response_format == "source-first-print-json" else
                    "every reviewed numbered T-Chinese row in the retained issue #84 scan "
                    "was replayed and accounted; omitted or ambiguous rows carry no absence claim"
                    if response_format == "52poke-scan-json" else
                    "every positive detail returned by the bounded provider-native name query "
                    "was retained and accounted; historical or provider-universe completeness "
                    "is not claimed"
                )
                if terminal_state == "complete" else
                "source access, pagination, parsing, or positive content needs evidence; no absence is inferred"
            ),
            "checkpoint": request["checkpoint"],
            "accounting": {
                "fetched": fetched,
                "matched": accounting["matched"],
                "ambiguous": accounting["ambiguous"],
                "newCandidate": accounting["new-candidate"],
                "positivelyExcluded": accounting["positively-excluded"],
                "needsEvidence": accounting["needs-evidence"],
                "accounted": accounted,
            },
        })

    records.sort(key=lambda row: row["stableKey"])
    totals = Counter(row["bucket"] for row in records)
    previous_records = [] if previous is None else previous["records"]
    return {
        "meta": {
            "schema": "snoredex-card-discovery-staging",
            "schemaVersion": "1.0.0",
            "coverageVersion": contract["meta"]["coverageVersion"],
            "generatedFromRun": manifest["runId"],
            "previousRun": None if previous is None else previous["meta"]["generatedFromRun"],
            "contract": "verification/card_discovery_adapters.json",
            "capabilityGraph": "verification/source_capability_graph.json",
            "authoritativeGraph": "verification/authoritative_graph.json",
            "contractHash": manifest["contractHash"],
            "capabilityGraphHash": manifest["capabilityGraphHash"],
            "authoritativeGraphHash": identity.get("authoritativeGraphHash", content_hash(identity)),
            "sourceFirst": True,
            "verdictMutationAllowed": False,
            "counts": {
                "slices": len(slice_rows), "records": len(records),
                "matched": totals["matched"], "ambiguous": totals["ambiguous"],
                "newCandidate": totals["new-candidate"],
                "positivelyExcluded": totals["positively-excluded"],
                "needsEvidence": totals["needs-evidence"],
                "runErrors": len(run_errors), "gaps": len(contract["gaps"]),
            },
        },
        "slices": slice_rows,
        "runErrors": run_errors,
        "diff": diff_records(records, previous_records),
        "gaps": contract["gaps"],
        "records": records,
    }


def run_directories() -> list[Path]:
    if not RUNS_DIR.exists():
        return []
    return sorted(
        path for path in RUNS_DIR.iterdir()
        if path.is_dir() and RUN_ID_PATTERN.fullmatch(path.name)
    )


def newest_compatible_complete_run(contract: dict[str, Any]) -> str | None:
    """Return the newest complete run with the same acquisition contract."""
    compatible = []
    for run_dir in run_directories():
        manifest = read_json(run_dir / "manifest.json")
        if manifest.get("status") != "complete":
            continue
        snapshot_path = run_dir / "contract.json"
        if not snapshot_path.is_file():
            raise DiscoveryError(
                f"complete run lacks its immutable contract snapshot: {run_dir.name}"
            )
        run_contract = read_json(snapshot_path)
        if manifest.get("contractHash") != content_hash(run_contract):
            raise DiscoveryError(f"contract snapshot hash mismatch: {run_dir.name}")
        if acquisition_contract(run_contract) == acquisition_contract(contract):
            compatible.append(run_dir.name)
    return max(compatible, default=None)


def build_latest(
    contract: dict[str, Any], capability: dict[str, Any], identity: dict[str, Any]
) -> tuple[dict[str, Any], Path]:
    directories = run_directories()
    if not directories:
        raise DiscoveryError("no retained card-discovery run exists")
    previous = None
    for run_dir in directories:
        manifest = read_json(run_dir / "manifest.json")
        if manifest.get("runId") != run_dir.name:
            raise DiscoveryError(f"run directory and manifest id differ: {run_dir.name}")
        run_contract = contract
        if manifest.get("contractHash") != content_hash(contract):
            snapshot_path = run_dir / "contract.json"
            if not snapshot_path.is_file():
                raise DiscoveryError(
                    f"historical run {run_dir.name} needs its immutable contract snapshot"
                )
            run_contract = read_json(snapshot_path)
            if manifest.get("contractHash") != content_hash(run_contract):
                raise DiscoveryError(f"contract snapshot hash mismatch: {run_dir.name}")
            validate_contract(run_contract, capability, identity)
        previous = build_projection(
            run_contract, capability, identity, manifest, run_dir, previous
        )
    return previous, directories[-1]


def fetch_bytes(url: str, headers: dict[str, str] | None = None) -> bytes:
    request_headers = {
        "User-Agent": "Snoredex-Data/1.0 source-first card discovery"
    }
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        if response.status != 200:
            raise DiscoveryError(f"HTTP {response.status}: {url}")
        raw = response.read()
        encoding = response.headers.get("Content-Encoding")
        if encoding == "gzip":
            return gzip.decompress(raw)
        if encoding == "deflate":
            return zlib.decompress(raw)
        return raw


def save_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    write_json(run_dir / "manifest.json", manifest)


def retain_response(run_dir: Path, relative: str, raw: bytes) -> str:
    path = checked_raw_path(run_dir, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if existing != raw:
            raise DiscoveryError(f"resume would overwrite retained response: {relative}")
    else:
        path.write_bytes(raw)
    return content_hash(raw)


def new_manifest(
    contract: dict[str, Any], capability: dict[str, Any], run_id: str, timestamp: str
) -> dict[str, Any]:
    requests = []
    for adapter in contract["adapters"]:
        for slice_row in adapter["slices"]:
            query_parameters = {"nameQueries": slice_row["nameQueries"]}
            response_format = adapter.get("responseFormat", "pokemon-asia-html")
            if response_format == "pokemon-asia-html":
                query_parameters.update({
                    "cardType": "all", "regulation": "all",
                    "pageParameter": adapter["pageParameter"],
                })
            elif response_format == "tcgdex-json":
                query_parameters.update({
                    "nameFilter": slice_row.get("nameFilter", "strict-equality"),
                    "pagination": "disabled-provider-default",
                })
            elif response_format == "confirmed-source-json":
                query_parameters.update({
                    "retainedUnitIds": slice_row["retainedUnitIds"],
                    "providerIdentity": "canonical-card-ed-num-query",
                    "sourceRecord": "verification/confirmed_sources.json",
                    "pagination": "exact-reviewed-positive-frontier",
                })
            elif response_format == "bulbapedia-historical-json":
                query_parameters.update({
                    "retainedUnitIds": slice_row["retainedUnitIds"],
                    "retainedSetNames": slice_row["retainedSetNames"],
                    "sourceRecord": "verification/confirmed_sources.json",
                    "pageTitle": adapter["pageTitle"],
                    "revisionId": adapter["revisionId"],
                    "languageColumn": slice_row["language"],
                    "pagination": "single-revision-positive-frontier",
                })
            elif response_format == "source-first-print-json":
                query_parameters.update({
                    "retainedPrintIds": slice_row["retainedPrintIds"],
                    "sourceRecord": "verification/source_first_prints.json",
                    "pagination": "exact-reviewed-positive-frontier",
                })
            elif response_format == "52poke-scan-json":
                query_parameters.update({
                    "retainedRecordIds": slice_row["retainedRecordIds"],
                    "sourceRecord": "verification/evidence/issue-84-snorlax-alle-zh.json",
                    "pagination": "exact-reviewed-positive-frontier",
                })
            elif response_format == "pokemon-official-localized-html":
                query_parameters.update({
                    "nameFilter": "provider-name-search",
                    "format": "unlimited",
                    "pageParameter": adapter["pageParameter"],
                    "pagination": "all-declared-result-pages",
                    "cacheKeyParameter": "snoredexRun",
                })
            else:
                query_parameters.update({
                    "nameFilter": "provider-name-search",
                    "format": "unlimited",
                    "pagination": "single-retained-response-no-archive-closure",
                    "cacheKeyParameter": "snoredexRun",
                })
            requests.append({
                "runId": run_id,
                "adapterId": adapter["adapterId"],
                "adapterVersion": adapter["adapterVersion"],
                "sliceId": slice_row["sliceId"],
                "providerId": adapter["providerId"],
                "surfaceId": adapter["surfaceId"],
                "coverageEdgeId": slice_row["coverageEdgeId"],
                "rawLocale": slice_row["rawLocale"],
                "endpoint": adapter["listEndpointTemplate"].format(
                    rawLocale=slice_row["rawLocale"]
                ),
                "queryParameters": query_parameters,
                "retrievedAt": timestamp,
                "pages": [], "details": [], "sets": [], "assets": [],
                "checkpoint": {
                    "completedPages": [], "completedDetailIds": [],
                    "nextPage": 1, "complete": False,
                },
                "error": None,
            })
    return {
        "schema": "snoredex-card-discovery-run",
        "schemaVersion": "1.0.0",
        "runId": run_id,
        "coverageVersion": contract["meta"]["coverageVersion"],
        "startedAt": timestamp,
        "completedAt": None,
        "status": "incomplete",
        "contract": "verification/card_discovery_adapters.json",
        "contractHash": content_hash(contract),
        "capabilityGraph": "verification/source_capability_graph.json",
        "capabilityGraphHash": capability_pin(capability, surfaces_used(requests)),
        "capabilityGraphSurfaces": surfaces_used(requests),
        "requests": requests,
        "failures": [],
    }


def refresh_asia_request(
    run_dir: Path, manifest: dict[str, Any], request: dict[str, Any],
    adapter: dict[str, Any], slice_row: dict[str, Any],
    assertion_by_code: dict[tuple[str, str, str, str], dict[str, Any]],
) -> None:
    pages_by_pair = {(row["query"], row["pageNo"]): row for row in request["pages"]}
    for query_index, query in enumerate(slice_row["nameQueries"], start=1):
        page_no = 1
        total_pages = None
        while total_pages is None or page_no <= total_pages:
            pair = (query, page_no)
            page = pages_by_pair.get(pair)
            if page is None:
                parameters = {
                    "pageNo": page_no, "keyword": query,
                    "cardType": "all", "regulation": "all",
                }
                url = request["endpoint"] + "?" + urllib.parse.urlencode(parameters)
                raw = fetch_bytes(url)
                parsed = parse_list(raw, "pokemon-asia-html")
                relative = f"raw/{request['sliceId']}/query-{query_index}/page-{page_no}.html"
                page = {
                    "query": query, "pageNo": page_no, "url": url,
                    "rawPath": relative, "responseHash": retain_response(run_dir, relative, raw),
                    **parsed,
                }
                request["pages"].append(page)
                pages_by_pair[pair] = page
                request["checkpoint"]["completedPages"] = sorted(
                    f"{row['query']}:{row['pageNo']}" for row in request["pages"]
                )
                request["checkpoint"]["nextPage"] = page_no + 1
                save_manifest(run_dir, manifest)
            total_pages = page["totalPages"]
            page_no += 1

    discovered_ids = sorted({
        raw_id for page in request["pages"] for raw_id in page["detailIds"]
    }, key=lambda value: int(value))
    details = {row["rawProviderId"]: row for row in request["details"]}
    for raw_provider_id in discovered_ids:
        if raw_provider_id not in details:
            url = adapter["detailEndpointTemplate"].format(
                rawLocale=slice_row["rawLocale"], rawProviderId=raw_provider_id
            )
            raw = fetch_bytes(url)
            parsed = parse_detail(raw, raw_provider_id, "pokemon-asia-html")
            relative = f"raw/{request['sliceId']}/details/{raw_provider_id}.html"
            detail = {
                "rawProviderId": raw_provider_id, "url": url,
                "rawPath": relative, "responseHash": retain_response(run_dir, relative, raw),
                "parsedRecordHash": content_hash(parsed),
            }
            request["details"].append(detail)
            details[raw_provider_id] = detail
            request["checkpoint"]["completedDetailIds"] = sorted(
                details, key=lambda value: int(value)
            )
            save_manifest(run_dir, manifest)

    assets = {row["rawSetCode"]: row for row in request["assets"]}
    for raw_provider_id in discovered_ids:
        detail = details[raw_provider_id]
        raw = checked_raw_path(run_dir, detail["rawPath"]).read_bytes()
        source_record = parse_detail(raw, raw_provider_id, "pokemon-asia-html")
        assertion = assertion_by_code.get((
            adapter["providerId"], adapter["surfaceId"], slice_row["rawLocale"],
            source_record.get("rawSetCode"),
        ))
        if assertion is not None and assertion["rawSetCode"] not in assets:
            asset_raw = fetch_bytes(assertion["assetUrl"])
            extension = Path(urllib.parse.urlparse(assertion["assetUrl"]).path).suffix or ".bin"
            relative = f"raw/{request['sliceId']}/assets/{assertion['rawSetCode']}{extension}"
            asset = {
                "rawSetCode": assertion["rawSetCode"], "url": assertion["assetUrl"],
                "rawPath": relative,
                "responseHash": retain_response(run_dir, relative, asset_raw),
            }
            request["assets"].append(asset)
            assets[assertion["rawSetCode"]] = asset
            save_manifest(run_dir, manifest)


def refresh_tcgdex_request(
    run_dir: Path, manifest: dict[str, Any], request: dict[str, Any],
    adapter: dict[str, Any], slice_row: dict[str, Any],
) -> None:
    name_filter = slice_row.get("nameFilter", "strict-equality")
    filter_operator = {
        "strict-equality": "eq",
        "substring": "like",
    }.get(name_filter)
    if filter_operator is None:
        raise DiscoveryError(f"unsupported TCGdex name filter: {name_filter}")
    pages_by_query = {row["query"]: row for row in request["pages"]}
    for query_index, query in enumerate(slice_row["nameQueries"], start=1):
        if query not in pages_by_query:
            url = request["endpoint"] + "?" + urllib.parse.urlencode({
                "name": f"{filter_operator}:{query}"
            })
            raw = fetch_bytes(url)
            parsed = parse_list(raw, "tcgdex-json")
            relative = f"raw/{request['sliceId']}/query-{query_index}.json"
            page = {
                "query": query, "pageNo": 1, "url": url,
                "rawPath": relative, "responseHash": retain_response(run_dir, relative, raw),
                **parsed,
            }
            request["pages"].append(page)
            pages_by_query[query] = page
            request["checkpoint"]["completedPages"] = sorted(
                f"{row['query']}:{row['pageNo']}" for row in request["pages"]
            )
            save_manifest(run_dir, manifest)

    discovered_ids = sorted({
        raw_id for page in request["pages"] for raw_id in page["detailIds"]
    })
    details = {row["rawProviderId"]: row for row in request["details"]}
    for raw_provider_id in discovered_ids:
        if raw_provider_id not in details:
            url = adapter["detailEndpointTemplate"].format(
                rawLocale=slice_row["rawLocale"], rawProviderId=raw_provider_id
            )
            raw = fetch_bytes(url)
            value = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(value, dict) or value.get("id") != raw_provider_id:
                raise DiscoveryError(f"TCGdex detail id differs: {raw_provider_id}")
            relative = f"raw/{request['sliceId']}/details/{raw_provider_id}.json"
            detail = {
                "rawProviderId": raw_provider_id, "url": url,
                "rawPath": relative, "responseHash": retain_response(run_dir, relative, raw),
                "parsedRecordHash": content_hash(value),
            }
            request["details"].append(detail)
            details[raw_provider_id] = detail
            request["checkpoint"]["completedDetailIds"] = sorted(details)
            save_manifest(run_dir, manifest)

    sets = {row["rawSetCode"]: row for row in request["sets"]}
    for raw_provider_id in discovered_ids:
        detail = details[raw_provider_id]
        value = json.loads(checked_raw_path(run_dir, detail["rawPath"]).read_text(
            encoding="utf-8-sig"
        ))
        set_brief = value.get("set") if isinstance(value, dict) else None
        raw_set_code = set_brief.get("id") if isinstance(set_brief, dict) else None
        if not isinstance(raw_set_code, str):
            raise DiscoveryError(f"TCGdex detail lacks a set id: {raw_provider_id}")
        if raw_set_code not in sets:
            url = adapter["setEndpointTemplate"].format(
                rawLocale=slice_row["rawLocale"], rawSetCode=raw_set_code
            )
            raw = fetch_bytes(url)
            set_value = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(set_value, dict) or set_value.get("id") != raw_set_code:
                raise DiscoveryError(f"TCGdex set id differs: {raw_set_code}")
            relative = f"raw/{request['sliceId']}/sets/{raw_set_code}.json"
            retained_set = {
                "rawSetCode": raw_set_code, "url": url,
                "rawPath": relative, "responseHash": retain_response(run_dir, relative, raw),
            }
            request["sets"].append(retained_set)
            sets[raw_set_code] = retained_set
            save_manifest(run_dir, manifest)


def refresh_confirmed_source_request(
    run_dir: Path, manifest: dict[str, Any], request: dict[str, Any],
    slice_row: dict[str, Any],
) -> None:
    """Replay only exact reviewed positive records from a browser-blocked source frontier."""
    source_records = confirmed_source_records(read_json(CONFIRMED_SOURCES_PATH), slice_row)

    query = slice_row["nameQueries"][0]
    if not request["pages"]:
        raw = canonical_bytes(source_records)
        relative = f"raw/{request['sliceId']}/query-1.json"
        separator = "&" if "?" in request["endpoint"] else "?"
        url = request["endpoint"] + separator + urllib.parse.urlencode({
            "snoredexRetained": ",".join(slice_row["retainedUnitIds"])
        })
        parsed = parse_list(raw, "confirmed-source-json")
        request["pages"].append({
            "query": query, "pageNo": 1, "url": url,
            "rawPath": relative,
            "responseHash": retain_response(run_dir, relative, raw),
            **parsed,
        })
        request["checkpoint"]["completedPages"] = [f"{query}:1"]
        save_manifest(run_dir, manifest)

    details = {row["rawProviderId"]: row for row in request["details"]}
    for source_record in source_records:
        listing_key = source_record["detailId"]
        if listing_key in details:
            continue
        raw = canonical_bytes(source_record)
        relative = f"raw/{request['sliceId']}/details/{listing_key}.json"
        detail = {
            "rawProviderId": listing_key,
            "url": source_record["sourceUrl"],
            "rawPath": relative,
            "responseHash": retain_response(run_dir, relative, raw),
            "recordSource": "confirmed-positive-frontier",
            "parsedRecordHash": content_hash(source_record),
        }
        request["details"].append(detail)
        details[listing_key] = detail
        request["checkpoint"]["completedDetailIds"] = sorted(details)
        save_manifest(run_dir, manifest)


def confirmed_source_records(
    confirmed_sources: list[dict[str, Any]], slice_row: dict[str, Any]
) -> list[dict[str, Any]]:
    """Group repository observations by the provider-native LigaPokemon listing identity."""
    confirmed_by_id: dict[str, dict[str, Any]] = {}
    for row in confirmed_sources:
        unit_id = row["unitId"]
        if unit_id in confirmed_by_id:
            raise DiscoveryError(f"duplicate confirmed unit {unit_id}")
        confirmed_by_id[unit_id] = row
    records_by_listing: dict[str, dict[str, Any]] = {}
    for unit_id in slice_row["retainedUnitIds"]:
        retained = confirmed_by_id[unit_id]
        source_url = retained.get("sourceUrl")
        if not isinstance(source_url, str) or not source_url.startswith("https://"):
            raise DiscoveryError(f"confirmed unit {unit_id} lacks an HTTPS source URL")
        parsed_url = urllib.parse.urlparse(source_url)
        parameters = urllib.parse.parse_qs(parsed_url.query)
        card = parameters.get("card", [None])[0]
        raw_set_code = parameters.get("ed", [None])[0]
        local_number = parameters.get("num", [None])[0]
        if (
            parsed_url.netloc.lower() != "www.ligapokemon.com.br"
            or parameters.get("view") != ["cards/card"]
            or not all(isinstance(value, str) and value for value in (
                card, raw_set_code, local_number
            ))
        ):
            raise DiscoveryError(
                f"confirmed unit {unit_id} lacks a LigaPokemon card/edition/number identity"
            )
        listing_key = urllib.parse.urlencode(
            (("card", card), ("ed", raw_set_code), ("num", local_number)),
            quote_via=urllib.parse.quote,
        )
        identity = {
            "localName": slice_row["nameQueries"][0],
            "rawSetCode": raw_set_code,
            "localCollectorNumber": local_number,
        }
        source_record = records_by_listing.get(listing_key)
        if source_record is None:
            source_record = {
                "detailId": listing_key,
                "providerListingKey": listing_key,
                **identity,
                "sourceUrl": source_url,
                "cardImageUrl": None,
                "setSymbolUrl": None,
                "productScope": "physical-tcg",
                "observations": [],
            }
            records_by_listing[listing_key] = source_record
        elif any(source_record[field] != value for field, value in identity.items()):
            raise DiscoveryError(f"LigaPokemon listing identity drift for {unit_id}")
        source_record["observations"].append({
            "unitId": unit_id,
            "variant": retained.get("variant"),
            "sourceType": retained.get("sourceType"),
            "checkedAt": retained.get("checkedAt"),
            "providerRecord": retained,
        })

    return list(records_by_listing.values())


def refresh_official_localized_request(
    run_dir: Path, manifest: dict[str, Any], request: dict[str, Any],
    adapter: dict[str, Any], slice_row: dict[str, Any],
) -> None:
    """Retain every declared publisher filter page and its exact positive result entries.

    The archive itself exposes each result's localized name, exact detail path and locale-specific
    CMS image. Individual detail pages are not walked here: the known-positive ``pl2/111`` page is
    absent from this filter response, so following result pagination still does not make the
    filter a historical manifest.
    """
    pages_by_pair = {(row["query"], row["pageNo"]): row for row in request["pages"]}
    for query_index, query in enumerate(slice_row["nameQueries"], start=1):
        page_no = 1
        total_pages = None
        while total_pages is None or page_no <= total_pages:
            pair = (query, page_no)
            page = pages_by_pair.get(pair)
            if page is not None:
                total_pages = page["totalPages"]
                page_no += 1
                continue
            parameters = {
                "cardName": query,
                "cardText": "",
                "evolvesFrom": "",
                "simpleSubmit": "",
                "format": "unlimited",
                "hitPointsMin": 0,
                "hitPointsMax": 400,
                "retreatCostMin": 0,
                "retreatCostMax": 5,
                "snoredexRun": manifest["runId"],
            }
            if page_no > 1:
                parameters[adapter["pageParameter"]] = page_no
            url = request["endpoint"] + "?" + urllib.parse.urlencode(parameters)
            relative = (
                f"raw/{request['sliceId']}/query-{query_index}/page-{page_no}.html"
            )
            retained_path = checked_raw_path(run_dir, relative)
            if retained_path.exists():
                raw = retained_path.read_bytes()
            else:
                headers = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/139.0.0.0 Safari/537.36 Snoredex-Data/1.0"
                    ),
                    "Accept-Language": (
                        f"{slice_row['rawLocale']}-{slice_row['rawLocale'].upper()},"
                        f"{slice_row['rawLocale']};q=0.9,en;q=0.8"
                    ),
                    "Accept-Encoding": "gzip, deflate",
                }
                if page_no > 1:
                    headers["Referer"] = pages_by_pair[(query, page_no - 1)]["url"]
                raw = fetch_bytes(url, headers=headers)
            query_echo, entries, parsed_page, parsed_total_pages = parse_official_localized_page(
                raw, slice_row["rawLocale"]
            )
            if query_echo != query:
                raise DiscoveryError(
                    f"official localized archive did not echo the requested name {query!r}"
                )
            if parsed_page != page_no:
                raise DiscoveryError(
                    f"official localized archive returned page {parsed_page} for requested page {page_no}"
                )
            page = {
                "query": query, "pageNo": page_no, "url": url,
                "rawPath": relative, "responseHash": retain_response(run_dir, relative, raw),
                "resultCount": len(entries), "totalPages": parsed_total_pages,
                "detailIds": [row["detailId"] for row in entries],
            }
            request["pages"].append(page)
            pages_by_pair[pair] = page
            request["checkpoint"]["completedPages"] = sorted(
                f"{row['query']}:{row['pageNo']}" for row in request["pages"]
            )
            request["checkpoint"]["nextPage"] = page_no + 1
            save_manifest(run_dir, manifest)
            total_pages = parsed_total_pages
            page_no += 1

    for query in slice_row["nameQueries"]:
        pages = [row for row in request["pages"] if row["query"] == query]
        if not pagination_complete(pages):
            raise DiscoveryError(
                f"official localized pagination is incomplete or duplicates a detail path for {query!r}"
            )

    details = {row["rawProviderId"]: row for row in request["details"]}
    for page in request["pages"]:
        raw = checked_raw_path(run_dir, page["rawPath"]).read_bytes()
        _, entries, parsed_page, parsed_total_pages = parse_official_localized_page(
            raw, slice_row["rawLocale"]
        )
        if parsed_page != page["pageNo"] or parsed_total_pages != page["totalPages"]:
            raise DiscoveryError(f"official localized pagination drift: {page['rawPath']}")
        for source_record in entries:
            raw_provider_id = source_record["detailId"]
            if raw_provider_id in details:
                continue
            detail = {
                "rawProviderId": raw_provider_id,
                "url": adapter["detailEndpointTemplate"].format(
                    rawLocale=slice_row["rawLocale"], rawProviderId=raw_provider_id
                ),
                "rawPath": page["rawPath"],
                "responseHash": page["responseHash"],
                "recordSource": "localized-archive-list-entry",
                "parsedRecordHash": content_hash(source_record),
            }
            request["details"].append(detail)
            details[raw_provider_id] = detail
            request["checkpoint"]["completedDetailIds"] = sorted(details)
            save_manifest(run_dir, manifest)


def refresh_source_first_print_request(
    run_dir: Path, manifest: dict[str, Any], request: dict[str, Any],
    slice_row: dict[str, Any],
) -> None:
    """Replay exact source-first print records without re-fetching their evidence assets."""
    prints_by_id = {
        row["printId"]: row for row in read_json(SOURCE_FIRST_PRINTS_PATH)["prints"]
    }
    source_records = []
    for print_id in slice_row["retainedPrintIds"]:
        retained = prints_by_id[print_id]
        source_records.append({
            "detailId": print_id,
            "localName": retained["name"],
            "rawSetCode": retained["localSetCode"],
            "localCollectorNumber": retained["localNumber"],
            "cardImageUrl": retained.get("cardImageUrl") or retained.get("sourceUrl"),
            "setSymbolUrl": None,
            "productScope": "physical-tcg",
            "sourceUrl": retained["sourceUrl"],
            "providerRecord": retained,
        })

    query = slice_row["nameQueries"][0]
    if not request["pages"]:
        raw = canonical_bytes(source_records)
        relative = f"raw/{request['sliceId']}/query-1.json"
        url = request["endpoint"] + "?" + urllib.parse.urlencode({
            "snoredexRetained": ",".join(slice_row["retainedPrintIds"])
        })
        request["pages"].append({
            "query": query, "pageNo": 1, "url": url,
            "rawPath": relative,
            "responseHash": retain_response(run_dir, relative, raw),
            **parse_list(raw, "source-first-print-json"),
        })
        request["checkpoint"]["completedPages"] = [f"{query}:1"]
        save_manifest(run_dir, manifest)

    details = {row["rawProviderId"]: row for row in request["details"]}
    for source_record in source_records:
        print_id = source_record["detailId"]
        if print_id in details:
            continue
        raw = canonical_bytes(source_record)
        safe_print_id = re.sub(r"[^A-Za-z0-9._-]+", "_", print_id)
        relative = f"raw/{request['sliceId']}/details/{safe_print_id}.json"
        detail = {
            "rawProviderId": print_id,
            "url": source_record["sourceUrl"],
            "rawPath": relative,
            "responseHash": retain_response(run_dir, relative, raw),
            "recordSource": "source-first-positive-frontier",
            "parsedRecordHash": content_hash(source_record),
        }
        request["details"].append(detail)
        details[print_id] = detail
        request["checkpoint"]["completedDetailIds"] = sorted(details)
        save_manifest(run_dir, manifest)


def refresh_52poke_scan_request(
    run_dir: Path, manifest: dict[str, Any], request: dict[str, Any],
    slice_row: dict[str, Any],
) -> None:
    """Replay only the numbered T-Chinese rows reviewed in issue #84."""
    available = issue84_52poke_records()
    source_records = [available[record_id] for record_id in slice_row["retainedRecordIds"]]
    query = slice_row["nameQueries"][0]
    if not request["pages"]:
        raw = canonical_bytes(source_records)
        relative = f"raw/{request['sliceId']}/query-1.json"
        request["pages"].append({
            "query": query,
            "pageNo": 1,
            "url": "https://github.com/m4s-ai/snoredex-data/issues/84",
            "rawPath": relative,
            "responseHash": retain_response(run_dir, relative, raw),
            **parse_list(raw, "52poke-scan-json"),
        })
        request["checkpoint"]["completedPages"] = [f"{query}:1"]
        save_manifest(run_dir, manifest)

    details = {row["rawProviderId"]: row for row in request["details"]}
    for source_record in source_records:
        record_id = source_record["detailId"]
        if record_id in details:
            continue
        raw = canonical_bytes(source_record)
        safe_record_id = re.sub(r"[^A-Za-z0-9._-]+", "_", record_id)
        relative = f"raw/{request['sliceId']}/details/{safe_record_id}.json"
        detail = {
            "rawProviderId": record_id,
            "url": source_record["sourceUrl"],
            "rawPath": relative,
            "responseHash": retain_response(run_dir, relative, raw),
            "recordSource": "issue-84-reviewed-52poke-frontier",
            "parsedRecordHash": content_hash(source_record),
        }
        request["details"].append(detail)
        details[record_id] = detail
        request["checkpoint"]["completedDetailIds"] = sorted(details)
        save_manifest(run_dir, manifest)


def refresh_bulbapedia_historical_request(
    run_dir: Path, manifest: dict[str, Any], request: dict[str, Any],
    adapter: dict[str, Any], slice_row: dict[str, Any],
) -> None:
    """Retain one pinned index revision, then replay its reviewed card frontiers."""
    confirmed_by_id = {
        row["unitId"]: row for row in read_json(CONFIRMED_SOURCES_PATH)
    }
    if request["pages"]:
        if len(request["pages"]) != 1:
            raise DiscoveryError(
                f"historical slice {request['sliceId']} retained more than one index page"
            )
        retained_page = request["pages"][0]
        raw = checked_raw_path(run_dir, retained_page["rawPath"]).read_bytes()
        if content_hash(raw) != retained_page["responseHash"]:
            raise DiscoveryError(
                f"historical index response hash mismatch: {retained_page['rawPath']}"
            )
    else:
        raw = fetch_bytes(request["endpoint"])
    try:
        set_rows = parse_historical_index(
            raw,
            slice_row["language"],
            expected_revision=adapter["revisionId"],
            expected_title=adapter["pageTitle"],
        )
    except HistoricalIndexError as error:
        raise DiscoveryError(str(error)) from error
    sets_by_name = {row["englishSetName"]: row for row in set_rows}
    source_records = []
    for unit_id in slice_row["retainedUnitIds"]:
        retained = confirmed_by_id[unit_id]
        index_name = slice_row["retainedSetNames"][unit_id]
        if index_name not in sets_by_name:
            raise DiscoveryError(
                f"pinned index lacks {slice_row['language']} {index_name} for {unit_id}"
            )
        source_records.append({
            "detailId": unit_id,
            "localName": retained["cardName"],
            "rawSetCode": retained["setCode"],
            "localCollectorNumber": retained["number"],
            "cardImageUrl": None,
            "setSymbolUrl": None,
            "productScope": "physical-tcg",
            "sourceUrl": (
                "https://bulbapedia.bulbagarden.net/w/index.php?title="
                "List_of_Pok%C3%A9mon_Trading_Card_Game_expansions_in_other_languages"
                f"&oldid={adapter['revisionId']}"
            ),
            "sourceType": retained.get("sourceType"),
            "variant": retained.get("variant"),
            "checkedAt": retained.get("checkedAt"),
            "historicalCatalogueRecord": sets_by_name[index_name],
            "providerRecord": retained,
        })

    query = slice_row["nameQueries"][0]
    relative = f"raw/{request['sliceId']}/index-revision-{adapter['revisionId']}.json"
    page = {
        "query": query,
        "pageNo": 1,
        "url": request["endpoint"],
        "rawPath": relative,
        "responseHash": retain_response(run_dir, relative, raw),
        "resultCount": len(source_records),
        "totalPages": 1,
        "detailIds": [row["detailId"] for row in source_records],
        "parsedPositiveSetCount": len(set_rows),
    }
    if request["pages"]:
        if request["pages"][0] != page:
            raise DiscoveryError(
                f"historical index accounting drift: {request['sliceId']}"
            )
    else:
        request["pages"].append(page)
    request["checkpoint"]["completedPages"] = [f"{query}:1"]
    existing_details = {
        row["rawProviderId"]: row for row in request["details"]
    }
    for source_record in source_records:
        unit_id = source_record["detailId"]
        detail_raw = canonical_bytes(source_record)
        detail_relative = f"raw/{request['sliceId']}/details/{unit_id}.json"
        detail = {
            "rawProviderId": unit_id,
            "url": source_record["sourceUrl"],
            "rawPath": detail_relative,
            "responseHash": content_hash(detail_raw),
            "recordSource": "revision-pinned-historical-positive-frontier",
            "parsedRecordHash": content_hash(source_record),
        }
        if unit_id in existing_details:
            if existing_details[unit_id] != detail:
                raise DiscoveryError(f"historical detail accounting drift: {unit_id}")
            retained_raw = checked_raw_path(run_dir, detail_relative).read_bytes()
            if content_hash(retained_raw) != detail["responseHash"]:
                raise DiscoveryError(f"historical detail response hash mismatch: {unit_id}")
        else:
            retain_response(run_dir, detail_relative, detail_raw)
            request["details"].append(detail)
    request["checkpoint"]["completedDetailIds"] = sorted(page["detailIds"])
    save_manifest(run_dir, manifest)


def reuse_unfinished_requests(
    run_dir: Path, manifest: dict[str, Any], source_run_id: str
) -> None:
    """Carry forward exact unchanged requests when another provider blocks a refresh."""
    if not RUN_ID_PATTERN.fullmatch(source_run_id):
        raise DiscoveryError("--reuse-unfinished-from-run must use YYYYMMDDTHHMMSSZ")
    source_dir = RUNS_DIR / source_run_id
    if not source_dir.is_dir():
        raise DiscoveryError(f"reuse source run does not exist: {source_run_id}")
    source_manifest = read_json(source_dir / "manifest.json")
    source_contract_path = source_dir / "contract.json"
    if source_manifest.get("runId") != source_run_id:
        raise DiscoveryError(f"reuse source run id differs: {source_run_id}")
    if source_manifest.get("status") != "complete":
        raise DiscoveryError(f"reuse source run is not complete: {source_run_id}")
    if not source_contract_path.is_file() or source_manifest.get(
        "contractHash"
    ) != content_hash(read_json(source_contract_path)):
        raise DiscoveryError(f"reuse source contract hash differs: {source_run_id}")

    source_requests = {row["sliceId"]: row for row in source_manifest["requests"]}
    reusable: list[tuple[int, dict[str, Any], dict[str, Any], Path]] = []
    for index, request in enumerate(manifest["requests"]):
        if request["checkpoint"].get("complete"):
            continue
        source_request = source_requests.get(request["sliceId"])
        if source_request is None or any(
            request[field] != source_request[field]
            for field in REQUEST_ACQUISITION_FIELDS
        ):
            continue
        newer_source_run_ids = []
        for candidate_dir in run_directories():
            if candidate_dir.name <= source_run_id:
                continue
            candidate_manifest = read_json(candidate_dir / "manifest.json")
            if candidate_manifest.get("status") != "complete":
                continue
            candidate_contract_path = candidate_dir / "contract.json"
            if not candidate_contract_path.is_file() or candidate_manifest.get(
                "contractHash"
            ) != content_hash(read_json(candidate_contract_path)):
                raise DiscoveryError(
                    f"reuse candidate contract hash differs: {candidate_dir.name}"
                )
            candidate_request = next(
                (
                    row for row in candidate_manifest["requests"]
                    if row["sliceId"] == request["sliceId"]
                ),
                None,
            )
            if (
                candidate_request is not None
                and candidate_request["checkpoint"].get("complete")
                and all(
                    request[field] == candidate_request[field]
                    for field in REQUEST_ACQUISITION_FIELDS
                )
            ):
                newer_source_run_ids.append(candidate_dir.name)
        if newer_source_run_ids:
            raise DiscoveryError(
                "reuse source is not the newest compatible complete request for "
                f"{request['sliceId']}: {max(newer_source_run_ids)}"
            )
        target_raw = run_dir / "raw" / request["sliceId"]
        if target_raw.exists():
            raise DiscoveryError(
                f"reuse target already contains raw responses: {request['sliceId']}"
            )
        reusable.append((index, request, source_request, target_raw))

    if not reusable:
        raise DiscoveryError(
            f"reuse source has no exact unfinished request match: {source_run_id}"
        )

    reused: list[str] = []
    for index, request, source_request, target_raw in reusable:
        shutil.copytree(source_dir / "raw" / request["sliceId"], target_raw)
        carried = json.loads(json.dumps(source_request))
        carried["runId"] = manifest["runId"]
        carried["replayedFromRun"] = source_run_id
        manifest["requests"][index] = carried
        reused.append(request["sliceId"])
    manifest["failures"] = [
        row for row in manifest["failures"] if row.get("sliceId") not in reused
    ]
    save_manifest(run_dir, manifest)


def refresh(
    run_id: str, retrieved_at: str | None, resume: bool,
    reuse_unfinished_from_run: str | None = None,
) -> None:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise DiscoveryError("--run-id must use YYYYMMDDTHHMMSSZ")
    contract, capability, identity = load_inputs()
    run_dir = RUNS_DIR / run_id
    timestamp = retrieved_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    if run_dir.exists():
        if not resume:
            raise DiscoveryError(f"run already exists; use --resume only for incomplete runs: {run_id}")
        manifest = read_json(run_dir / "manifest.json")
        if manifest.get("status") != "incomplete":
            raise DiscoveryError(f"immutable completed run cannot be resumed: {run_id}")
        if manifest.get("contractHash") != content_hash(contract) or manifest.get(
            "capabilityGraphHash"
        ) != capability_pin(capability, manifest_surfaces(manifest)):
            raise DiscoveryError("resume inputs differ from the retained run")
        if content_hash(read_json(run_dir / "contract.json")) != content_hash(contract):
            raise DiscoveryError("resume contract snapshot differs from the retained run")
    else:
        if resume:
            raise DiscoveryError(f"cannot resume missing run: {run_id}")
        run_dir.mkdir(parents=True)
        write_json(run_dir / "contract.json", contract)
        manifest = new_manifest(contract, capability, run_id, timestamp)
        save_manifest(run_dir, manifest)

    if reuse_unfinished_from_run is not None:
        if not resume:
            raise DiscoveryError("--reuse-unfinished-from-run requires --resume")
        reuse_unfinished_requests(run_dir, manifest, reuse_unfinished_from_run)

    adapters = {row["adapterId"]: row for row in contract["adapters"]}
    slices = {
        row["sliceId"]: row
        for adapter in contract["adapters"] for row in adapter["slices"]
    }
    assertion_by_code = {
        (row["providerId"], row["surfaceId"], row["rawLocale"], row["rawSetCode"]): row
        for row in contract["setCodeAssertions"]
    }
    manifest["failures"] = []
    try:
        for request in manifest["requests"]:
            adapter = adapters[request["adapterId"]]
            slice_row = slices[request["sliceId"]]
            request["error"] = None
            response_format = adapter.get("responseFormat", "pokemon-asia-html")
            if response_format == "pokemon-asia-html":
                refresh_asia_request(
                    run_dir, manifest, request, adapter, slice_row, assertion_by_code
                )
            elif response_format == "pokemon-official-localized-html":
                refresh_official_localized_request(
                    run_dir, manifest, request, adapter, slice_row
                )
            elif response_format == "tcgdex-json":
                refresh_tcgdex_request(run_dir, manifest, request, adapter, slice_row)
            elif response_format == "confirmed-source-json":
                refresh_confirmed_source_request(
                    run_dir, manifest, request, slice_row
                )
            elif response_format == "source-first-print-json":
                refresh_source_first_print_request(
                    run_dir, manifest, request, slice_row
                )
            elif response_format == "52poke-scan-json":
                refresh_52poke_scan_request(
                    run_dir, manifest, request, slice_row
                )
            elif response_format == "bulbapedia-historical-json":
                refresh_bulbapedia_historical_request(
                    run_dir, manifest, request, adapter, slice_row
                )
            else:
                raise DiscoveryError(f"unsupported card response format: {response_format}")

            request["pages"].sort(key=lambda row: (row["query"], row["pageNo"]))
            request["details"].sort(key=lambda row: row["rawProviderId"])
            request["sets"].sort(key=lambda row: row["rawSetCode"])
            request["assets"].sort(key=lambda row: row["rawSetCode"])
            request["checkpoint"] = {
                "completedPages": [
                    f"{row['query']}:{row['pageNo']}" for row in request["pages"]
                ],
                "completedDetailIds": [row["rawProviderId"] for row in request["details"]],
                "nextPage": None,
                "complete": True,
            }
            save_manifest(run_dir, manifest)
    except (DiscoveryError, urllib.error.URLError, TimeoutError, UnicodeError,
            json.JSONDecodeError) as error:
        request["error"] = {"code": "fetch-or-parse-failure", "message": str(error)}
        manifest["failures"] = [{
            "code": "request-failure", "sliceId": request["sliceId"],
            "error": request["error"], "meaning": "source-failed; never negative evidence",
        }]
        save_manifest(run_dir, manifest)
        raise DiscoveryError(f"run retained incomplete for --resume: {error}") from error

    manifest["status"] = "complete"
    manifest["completedAt"] = timestamp
    save_manifest(run_dir, manifest)
    projection, _ = build_latest(contract, capability, identity)
    summary_text, records_text = render_projection(projection)
    OUTPUT_PATH.write_bytes(summary_text.encode("utf-8"))
    RECORDS_PATH.write_bytes(records_text.encode("utf-8"))
    counts = projection["meta"]["counts"]
    print(
        f"retained {run_id}: {counts['records']} card records, "
        f"{counts['newCandidate']} new candidates, {counts['runErrors']} run errors"
    )


def replay_run(source_run_id: str, run_id: str, replayed_at: str | None) -> None:
    """Reproject immutable responses when only mappings or contract metadata changed."""
    if not RUN_ID_PATTERN.fullmatch(source_run_id) or not RUN_ID_PATTERN.fullmatch(run_id):
        raise DiscoveryError("replay run ids must use YYYYMMDDTHHMMSSZ form")
    source_dir = RUNS_DIR / source_run_id
    run_dir = RUNS_DIR / run_id
    if not source_dir.is_dir():
        raise DiscoveryError(f"replay source run does not exist: {source_run_id}")
    if run_dir.exists():
        raise DiscoveryError(f"replay destination run already exists: {run_id}")
    retained_run_ids = [
        path.name for path in RUNS_DIR.iterdir()
        if path.is_dir() and RUN_ID_PATTERN.fullmatch(path.name)
    ]
    if retained_run_ids and run_id <= max(retained_run_ids):
        raise DiscoveryError(
            "replay destination run must sort after every retained run: "
            f"{run_id} <= {max(retained_run_ids)}"
        )

    contract, capability, identity = load_inputs()
    source_manifest = read_json(source_dir / "manifest.json")
    source_contract = read_json(source_dir / "contract.json")
    if source_manifest.get("status") != "complete":
        raise DiscoveryError(f"replay source run is not complete: {source_run_id}")
    if source_manifest.get("contractHash") != content_hash(source_contract):
        raise DiscoveryError(f"replay source contract hash differs: {source_run_id}")
    validate_contract(source_contract, capability, identity)
    if acquisition_contract(source_contract) != acquisition_contract(contract):
        raise DiscoveryError("replay source differs in its provider acquisition contract")
    newest_source_run_id = newest_compatible_complete_run(contract)
    if source_run_id != newest_source_run_id:
        raise DiscoveryError(
            "replay source must be the newest compatible complete run: "
            f"{source_run_id} != {newest_source_run_id}"
        )

    timestamp = replayed_at or datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")
    expected = new_manifest(contract, capability, run_id, timestamp)
    expected_requests = {
        row["sliceId"]: {key: row[key] for key in REQUEST_ACQUISITION_FIELDS}
        for row in expected["requests"]
    }
    source_requests = {
        row["sliceId"]: {key: row[key] for key in REQUEST_ACQUISITION_FIELDS}
        for row in source_manifest["requests"]
    }
    if source_requests != expected_requests:
        raise DiscoveryError("replay request acquisition inputs differ")

    manifest = json.loads(json.dumps(source_manifest))
    manifest.update({
        "runId": run_id,
        "coverageVersion": contract["meta"]["coverageVersion"],
        "startedAt": timestamp,
        "completedAt": None,
        "status": "incomplete",
        "contractHash": content_hash(contract),
        "replayedFromRun": source_run_id,
    })
    for request in manifest["requests"]:
        request["runId"] = run_id
        request["replayedFromRun"] = source_run_id

    run_dir.mkdir(parents=True)
    write_json(run_dir / "contract.json", contract)
    shutil.copytree(source_dir / "raw", run_dir / "raw")
    save_manifest(run_dir, manifest)
    build_projection(contract, capability, identity, manifest, run_dir, None)
    manifest["status"] = "complete"
    manifest["completedAt"] = timestamp
    save_manifest(run_dir, manifest)

    projection, _ = build_latest(contract, capability, identity)
    summary_text, records_text = render_projection(projection)
    OUTPUT_PATH.write_bytes(summary_text.encode("utf-8"))
    RECORDS_PATH.write_bytes(records_text.encode("utf-8"))
    counts = projection["meta"]["counts"]
    print(
        f"replayed {source_run_id} as {run_id}: {counts['records']} card records, "
        f"{counts['newCandidate']} new candidates, {counts['runErrors']} run errors"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate immutable runs and projections")
    parser.add_argument(
        "--refresh", "--refresh-asia", dest="refresh", action="store_true",
        help="create or resume one immutable run across all active card adapters",
    )
    parser.add_argument("--resume", action="store_true", help="resume the named incomplete run")
    parser.add_argument(
        "--reuse-unfinished-from-run",
        help="on resume, carry forward exact unchanged unfinished requests from a complete run",
    )
    parser.add_argument(
        "--replay-from-run",
        help="reuse a complete immutable run when provider acquisition inputs are unchanged",
    )
    parser.add_argument("--run-id", help="immutable run id in YYYYMMDDTHHMMSSZ form")
    parser.add_argument("--retrieved-at", help="explicit ISO-8601 retrieval timestamp for a run")
    args = parser.parse_args()
    try:
        if args.replay_from_run:
            if (
                args.refresh or args.resume or args.reuse_unfinished_from_run
                or not args.run_id
            ):
                raise DiscoveryError("--replay-from-run requires only --run-id")
            replay_run(args.replay_from_run, args.run_id, args.retrieved_at)
            return 0
        if args.refresh:
            if not args.run_id:
                raise DiscoveryError("--refresh requires --run-id")
            refresh(
                args.run_id, args.retrieved_at, args.resume,
                args.reuse_unfinished_from_run,
            )
            return 0
        if args.reuse_unfinished_from_run:
            raise DiscoveryError("--reuse-unfinished-from-run requires --refresh --resume")
        if args.resume:
            raise DiscoveryError("--resume requires --refresh")
        contract, capability, identity = load_inputs()
        projection, run_dir = build_latest(contract, capability, identity)
        rendered, records_rendered = render_projection(projection)
        if args.check:
            stale = []
            if not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
                stale.append(str(OUTPUT_PATH.relative_to(ROOT)))
            if not RECORDS_PATH.exists() or RECORDS_PATH.read_bytes() != records_rendered.encode(
                "utf-8"
            ):
                stale.append(str(RECORDS_PATH.relative_to(ROOT)))
            if stale:
                raise DiscoveryError("stale projection: " + ", ".join(stale))
            counts = projection["meta"]["counts"]
            if counts["runErrors"]:
                raise DiscoveryError(f"latest run has {counts['runErrors']} run error(s)")
            print(
                f"[ ok ] card discovery: {counts['records']} records across "
                f"{counts['slices']} accounted slices; {counts['gaps']} explicit gaps"
            )
            return 0
        OUTPUT_PATH.write_bytes(rendered.encode("utf-8"))
        RECORDS_PATH.write_bytes(records_rendered.encode("utf-8"))
        print(f"wrote {OUTPUT_PATH.relative_to(ROOT)} from immutable run {run_dir.name}")
        return 0
    except (DiscoveryError, KeyError, TypeError, OSError, json.JSONDecodeError) as error:
        print(f"[FAIL] card discovery: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
