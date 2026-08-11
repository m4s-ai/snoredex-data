#!/usr/bin/env python3
"""Parse the revision-pinned Bulbapedia other-language expansion index."""

from __future__ import annotations

import json
import re
from typing import Any


class HistoricalIndexError(ValueError):
    """The retained MediaWiki response does not match the reviewed index contract."""


def _header_value(line: str) -> str:
    value = line[1:].strip()
    return value.rsplit("|", 1)[-1].strip()


def _cell_value(line: str) -> tuple[int, str]:
    value = line[1:].strip()
    match = re.match(r'^colspan\s*=\s*"?(\d+)"?\s*\|\s*(.*)$', value)
    return (int(match.group(1)), match.group(2)) if match else (1, value)


def _clean_wikitext(value: str) -> str:
    value = re.sub(r"<!--.*?-->", "", value)
    value = re.sub(r"\{\{tt\|([^|}]+)\|.*?\}\}", r"\1", value)
    value = re.sub(r"\[\[[^]|]+\|([^]]+)\]\]", r"\1", value)
    value = re.sub(r"\[\[([^]]+)\]\]", r"\1", value)
    return re.sub(r"''+", "", value).strip()


def _english_identity(value: str) -> tuple[str, str]:
    match = re.fullmatch(r"\{\{TCG\|([^}|]+)(?:\|([^}]+))?\}\}", value.strip())
    if not match:
        raise HistoricalIndexError(f"English set cell is not a TCG template: {value!r}")
    page = match.group(1).strip()
    return page, (match.group(2) or page).strip()


def parse_historical_index(
    raw: bytes,
    language: str,
    *,
    expected_revision: int,
    expected_title: str,
) -> list[dict[str, Any]]:
    """Return every positive cell in one language column of the pinned English-set index."""
    try:
        document = json.loads(raw.decode("utf-8-sig"))
        parsed = document["parse"]
        revision = parsed["revid"]
        title = parsed["title"]
        wikitext = parsed["wikitext"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise HistoricalIndexError("MediaWiki response lacks parse title/revid/wikitext") from error
    if revision != expected_revision:
        raise HistoricalIndexError(
            f"MediaWiki revision differs: expected {expected_revision}, got {revision}"
        )
    if title != expected_title:
        raise HistoricalIndexError(
            f"MediaWiki title differs: expected {expected_title!r}, got {title!r}"
        )
    if not isinstance(wikitext, str):
        raise HistoricalIndexError("MediaWiki wikitext is not text")
    try:
        wikitext = wikitext[
            wikitext.index("==English sets=="):wikitext.index("==Japanese sets==")
        ]
    except ValueError as error:
        raise HistoricalIndexError("reviewed English-set section boundaries are missing") from error

    records: list[dict[str, Any]] = []
    headers: list[str] = []
    header_cells: list[str] = []
    cells: list[str] = []
    series: str | None = None
    in_table = False

    def flush_row() -> None:
        nonlocal headers, header_cells, cells
        if header_cells:
            headers = header_cells
        elif cells and headers and language in headers:
            if len(cells) != len(headers):
                raise HistoricalIndexError(
                    f"table row width differs in {series}: {len(cells)} != {len(headers)}"
                )
            row = dict(zip(headers, cells))
            local_raw = row.get(language)
            english_raw = row.get("English")
            if local_raw is not None and english_raw is not None:
                local_name = _clean_wikitext(local_raw)
                if local_name and local_name != "—":
                    source_page, english_name = _english_identity(english_raw)
                    records.append({
                        "id": source_page,
                        "name": local_name,
                        "englishSetName": english_name,
                        "sourceSetPage": source_page,
                        "languageColumn": language,
                        "series": series,
                        "sourcePageTitle": title,
                        "sourceRevisionId": revision,
                        "sourceSection": "English sets",
                        "rawEnglishCell": english_raw,
                        "rawLocalCell": local_raw,
                        "sourceClause": (
                            f"English sets / {series}: {english_name} | "
                            f"{language}: {local_raw}"
                        ),
                        "releaseStatus": "physical-positive",
                        "releaseDate": None,
                        "cardCount": None,
                    })
        header_cells = []
        cells = []

    for line in wikitext.splitlines():
        heading = re.match(r"^===([^=]+)===$", line)
        if heading:
            series = heading.group(1).strip()
        if line.startswith("{|"):
            in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("|-"):
            flush_row()
            continue
        if line.startswith("|}"):
            flush_row()
            in_table = False
            continue
        if line.startswith("!"):
            header_cells.append(_header_value(line))
            continue
        if line.startswith("|"):
            span, value = _cell_value(line)
            cells.extend([value] * span)
    flush_row()

    ids = [record["id"] for record in records]
    if len(ids) != len(set(ids)):
        raise HistoricalIndexError(f"duplicate positive {language} set identity")
    if not records:
        raise HistoricalIndexError(f"reviewed revision has no positive {language} rows")
    return records
