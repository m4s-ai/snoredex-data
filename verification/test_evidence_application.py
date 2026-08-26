#!/usr/bin/env python3
"""Regression checks for #137's raw-verdict/application-status boundary."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def key(row: dict, variant_field: str) -> tuple[str, str, str]:
    return (
        str(row.get("setCode") or ""),
        str(row.get("number") or ""),
        str(row.get(variant_field) or "base"),
    )


def main() -> int:
    units = load("verification/units.json")
    semantics_doc = load("verification/evidence_semantics.json")
    semantics = {row["unitId"]: row for row in semantics_doc["units"]}
    if set(semantics) != {unit["unitId"] for unit in units}:
        raise AssertionError("semantic application policy does not cover every raw unit")

    expected = {
        "exists": set(),
        "needs-evidence": set(),
        "not-printed": set(),
        "disputed": set(),
        "unresolved": set(),
    }
    by_id = {unit["unitId"]: unit for unit in units}
    bounded_scopes = {
        (row["providerId"], row["url"].rstrip("/"))
        for row in semantics_doc["meta"]["boundedLanguageAbsenceScopes"]
    }
    for unit_id, semantic in semantics.items():
        status = semantic["applicationStatus"]
        if status not in expected:
            raise AssertionError(f"unexpected application status for {unit_id}: {status}")
        expected[status].add(unit_id)
        if unit_id in expected["exists"] and (
            by_id[unit_id]["status"] != "confirmed"
            or not semantic["verdictWithinGranularity"]
        ):
            raise AssertionError(f"unsupported confirmation materialized as exists: {unit_id}")
        if unit_id in expected["needs-evidence"] and (
            by_id[unit_id]["status"] != "confirmed"
            or semantic["verdictWithinGranularity"]
        ):
            raise AssertionError(f"needs-evidence is not an unsupported confirmation: {unit_id}")
        if status == "not-printed" and semantic["inference"] != "owner-adjudicated":
            raise AssertionError(f"hard absence lacks owner adjudication: {unit_id}")
        if semantic["inference"] == "provider-holds-an-absence-edge" and (
            by_id[unit_id]["providerId"],
            str(by_id[unit_id].get("sourceUrl") or "").rstrip("/"),
        ) not in bounded_scopes:
            raise AssertionError(f"provider-wide absence leaked past an exact scope: {unit_id}")

    cards = {
        key(card, "variantToken"): card
        for card in load("snorlax_cards.json")["cards"]
        if not card.get("isCodeCard")
    }
    unit_groups: dict[tuple[str, str, str], dict[str, set[str]]] = {}
    for unit in units:
        group = unit_groups.setdefault(key(unit, "variant"), {
            "repository-confirmed": set(), "exists": set(), "contradicted": set(),
            "not-printed": set(), "disputed": set(), "needs-evidence": set(),
            "unresolved": set(),
        })
        app_status = semantics[unit["unitId"]]["applicationStatus"]
        if unit["status"] == "confirmed":
            group["repository-confirmed"].add(unit["language"])
        if unit["status"] == "contradicted":
            group["contradicted"].add(unit["language"])
        group[app_status].add(unit["language"])
        if app_status == "needs-evidence":
            group["unresolved"].add(unit["language"])

    fields = {
        "languagesRepositoryConfirmed": "repository-confirmed",
        "languagesConfirmed": "exists",
        "languagesContradicted": "contradicted",
        "languagesNotPrinted": "not-printed",
        "languagesDisputed": "disputed",
        "languagesNeedsEvidence": "needs-evidence",
        "languagesUnresolved": "unresolved",
    }
    for identity, group in unit_groups.items():
        card = cards.get(identity)
        if card is None:
            raise AssertionError(f"language group has no card: {identity}")
        for field, status in fields.items():
            if set(card.get(field) or []) != group[status]:
                raise AssertionError(f"{identity} {field} does not match {status}")

    release_pairs = {
        (row["setCode"], str(row.get("number") or ""), row["variant"], language)
        for row in load("analysis_confirmed_releases.json")["variants"]
        if row["edition"] != "1st Edition"
        for language in row["confirmedLanguages"]
    }
    expected_release_pairs = {
        (*key(by_id[unit_id], "variant"), by_id[unit_id]["language"])
        for unit_id in expected["exists"]
    }
    if release_pairs != expected_release_pairs:
        raise AssertionError("chronological release projection differs from established units")

    unsupported_pairs = {
        (*key(by_id[unit_id], "variant"), by_id[unit_id]["language"])
        for unit_id in expected["needs-evidence"]
    }
    leaked_checklist = [
        item["checklistId"]
        for item in load("analysis_checklist.json")["items"]
        if any(
            (
                item["setCode"], str(item.get("number") or ""), variant, item["language"]
            ) in unsupported_pairs
            for variant in item.get("mappedVariants") or ["base"]
        )
    ]
    if leaked_checklist:
        raise AssertionError(f"needs-evidence claims leaked into checklist: {leaked_checklist[:5]}")

    connection = sqlite3.connect(ROOT / "snoredex.sqlite")
    try:
        database_statuses = dict(connection.execute(
            "SELECT unit_id, application_status FROM product_languages "
            "WHERE verification_status<>'out-of-scope'"
        ))
    finally:
        connection.close()
    expected_statuses = {
        unit_id: semantic["applicationStatus"] for unit_id, semantic in semantics.items()
    }
    if database_statuses != expected_statuses:
        raise AssertionError("database application statuses differ from evidence semantics")

    source_first = load("verification/source_first_prints.json")["prints"]
    known_alternates = {
        (row["localSetCode"], str(row["localNumber"]), row["language"])
        for row in source_first
    }
    if {("AS5a", "142", "T-Chinese"), ("SV-P", "215", "T-Chinese")} - known_alternates:
        raise AssertionError("known Traditional-Chinese alternate local identities disappeared")
    legacy_regressions = {
        (unit["setCode"], str(unit["number"]), unit["language"]):
        semantics[unit["unitId"]]["applicationStatus"]
        for unit in units
        if (unit["setCode"], str(unit["number"]), unit["language"])
        in {("sm10", "076", "T-Chinese"), ("svLN", "010", "T-Chinese")}
    }
    if set(legacy_regressions.values()) - {"disputed", "not-printed"}:
        raise AssertionError(f"alternate-local-identity regression was presented as absence: {legacy_regressions}")

    issue84_correction = by_id["U0467"]
    if (
        issue84_correction["status"] != "confirmed"
        or issue84_correction.get("providerId") != "52poke"
        or semantics["U0467"]["applicationStatus"] != "exists"
    ):
        raise AssertionError("#84 positive SVG 021/049 evidence no longer corrects U0467")

    counts = {status: len(unit_ids) for status, unit_ids in expected.items()}
    if semantics_doc["counts"]["applicationStatuses"] != {
        status: count for status, count in sorted(counts.items(), key=lambda item: -item[1]) if count
    }:
        raise AssertionError("reported application-status counts are stale")

    # #210 — a direct owner attestation stays card-level. Do not pin this regression to one
    # product: stronger official evidence may legitimately replace those rows over time.
    prize_pack_regression = [
        unit for unit in units
        if unit.get("providerId") == "owner-attestation"
        and (unit.get("sourceType") or "").startswith("Owner attestation")
    ]
    for unit in prize_pack_regression:
        semantic = semantics[unit["unitId"]]
        if semantic["granularity"] != "specimen-or-card":
            raise AssertionError(
                f"direct owner attestation demoted by trailing corroboration: {unit['unitId']}"
            )
        if semantic["applicationStatus"] != "exists":
            raise AssertionError(
                f"direct owner attestation lost its supported confirmation: {unit['unitId']}"
            )
    if not prize_pack_regression:
        raise AssertionError("#210 regression fixture lost — no direct owner-attestation rows found")

    # #306 review — localized Prize Pack manifests and English-market evidence must not be
    # projected onto neighboring languages merely because they share one finish override.
    finish_overrides = load("verification/finish_overrides.json")
    english_only_refs = {
        "tcgcsv-docs", "tcgcsv-prize-pack-snorlax", "cardmarket-stock-image",
        "owner-scan-review",
    }
    for override in finish_overrides["overrides"]:
        if not str(override.get("setCode") or "").startswith("PPS"):
            continue
        languages = override.get("languages") or []
        if len(languages) != 1:
            raise AssertionError(f"Prize Pack override is not language-scoped: {override['setCode']}")
        language = languages[0]
        for printing in override.get("printings") or []:
            refs = printing.get("sourceRefs") or []
            checklist_languages = {
                tuple(finish_overrides["sources"][ref].get("languages") or [])
                for ref in refs if ref.startswith("prize-pack-series-")
            }
            if checklist_languages != {(language,)}:
                raise AssertionError(
                    f"{override['setCode']} {language} cites another locale's checklist"
                )
            if language != "English" and english_only_refs.intersection(refs):
                raise AssertionError(
                    f"{override['setCode']} {language} inherits English-market evidence"
                )

    print(f"evidence application regressions passed: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
