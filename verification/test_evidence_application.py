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
    if "boundedLanguageAbsenceScopes" in semantics_doc["meta"]:
        raise AssertionError("evidence semantics still exposes provider absence scopes")
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
        if semantic["inference"] == "provider-holds-an-absence-edge":
            raise AssertionError(f"provider absence inference remains active: {unit_id}")

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

    # A direct owner attestation stays card-level. Do not pin this regression to one
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
        raise AssertionError("owner-attestation regression fixture is missing")

    # Localized Prize Pack checklists and English-market evidence must not be
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

    exact_prior_support = {
        "U0372", "U0534", "U0593",
        "U0187", "U0188", "U0189", "U0190", "U0191", "U0192",
        "U0214", "U0215", "U0216", "U0217", "U0218", "U0219",
        "U0324", "U0325", "U0326", "U0327", "U0328", "U0329",
    }
    localized_name_only = {
        "U0373", "U0374", "U0375", "U0376",
        "U0535", "U0536", "U0537", "U0538",
        "U0594", "U0595", "U0596", "U0597",
    }
    if {unit_id for unit_id in exact_prior_support if not by_id[unit_id].get("corroborated")}:
        raise AssertionError("exact Prize Pack corroboration was demoted")
    false_corroboration = {
        unit_id for unit_id in localized_name_only if by_id[unit_id].get("corroborated")
    }
    if false_corroboration:
        raise AssertionError(
            f"localized product names were counted as exact corroboration: {false_corroboration}"
        )

    exact_cardmarket_specimen_support = {"U0246", "U0561", "U0785"}
    missing_cardmarket_corroboration = {
        unit_id for unit_id in exact_cardmarket_specimen_support
        if not by_id[unit_id].get("corroborated")
    }
    if missing_cardmarket_corroboration:
        raise AssertionError(
            "exact Cardmarket seller-photo corroboration was not applied: "
            f"{missing_cardmarket_corroboration}"
        )

    finish_units = load("verification/finish_units.json")["units"]
    for language in ("German", "Portuguese"):
        unit = next(
            row for row in finish_units
            if row["setCode"] == "PPS8 JTG"
            and row["number"] == "JTG 117"
            and row["language"] == language
        )
        holo = next(printing for printing in unit["printings"] if printing["finish"] == "holo")
        if not any(source.get("languages") == [language] for source in holo["sources"]):
            raise AssertionError(f"{language} specimen-backed holo lost its localized checklist")

    russian_issue_272 = {
        unit["finishUnitId"]: unit
        for unit in finish_units
        if unit["finishUnitId"] in {"F0024", "F0125", "F0183"}
    }
    expected_reverse_specimens = {"F0024": "SPEC-0050", "F0125": "SPEC-0051"}
    for finish_unit_id, specimen_id in expected_reverse_specimens.items():
        reverse = next(
            printing for printing in russian_issue_272[finish_unit_id]["printings"]
            if printing["finish"] == "reverse-holo"
        )
        if (
            reverse["verificationStatus"] != "confirmed"
            or reverse.get("foilPattern") != "type-symbol-background"
            or specimen_id not in (reverse.get("specimenIds") or [])
        ):
            raise AssertionError(f"#272 reverse evidence was lost for {finish_unit_id}")
    russian_kss = russian_issue_272["F0183"]
    if (
        russian_kss["availableFinishes"] != ["non-holo"]
        or russian_kss["completenessStatus"] != "owner-adjudicated"
        or {printing["finish"] for printing in russian_kss["printings"]} != {"non-holo"}
    ):
        raise AssertionError("#272 Russian KSS finish adjudication no longer suppresses the false reverse claim")

    specimens = load("verification/specimens.json")["specimens"]
    polish_non_holo = next(row for row in specimens if row["specimenId"] == "SPEC-0045")
    finish_basis = str((polish_non_holo.get("physicalObservation") or {}).get("basis") or "")
    if (
        (polish_non_holo.get("physicalObservation") or {}).get("finish") != "non-holo"
        or "collection owner" not in finish_basis.casefold()
        or "scan lighting alone is not treated as finish evidence" not in finish_basis.casefold()
    ):
        raise AssertionError("Polish non-holo scan lacks its explicit owner identification boundary")

    print(f"evidence application regressions passed: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
