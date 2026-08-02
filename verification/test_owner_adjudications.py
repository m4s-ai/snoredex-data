#!/usr/bin/env python3
"""Regression checks for owner-level application decisions.

These checks deliberately inspect both the raw verdict and the clean handoff projection. The
owner's final decision may make an application row ``not-printed`` without pretending that the
provider itself supplied an exhaustive absence manifest.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "snoredex.sqlite"
EXPECTED_UNIT_IDS = {
    "U0296", "U0298", "U0377", "U0435", "U0437", "U0497", "U0498", "U0499",
    "U0500", "U0501", "U0539", "U0598",
}
SOURCE_SCOPED_UNIT_IDS = {"U0497", "U0498", "U0499", "U0500", "U0501"}


def main() -> int:
    owner_doc = json.loads(
        (ROOT / "verification" / "owner_adjudications.json").read_text(encoding="utf-8")
    )
    raw_units = {
        unit["unitId"]: unit
        for unit in json.loads((ROOT / "verification" / "units.json").read_text(encoding="utf-8"))
    }
    decisions = owner_doc["decisions"]
    decision_ids = {item["unitId"] for item in decisions}
    if decision_ids != EXPECTED_UNIT_IDS:
        raise AssertionError(f"owner decision unit ids changed unexpectedly: {sorted(decision_ids)}")
    if len(decisions) != len(EXPECTED_UNIT_IDS):
        raise AssertionError("owner adjudication ids are not one-per-unit")
    for decision in decisions:
        raw = raw_units.get(decision["unitId"])
        if not raw or raw["status"] != "contradicted":
            raise AssertionError(f"owner decision does not target a contradicted raw unit: {decision}")
        if decision["decision"] != "not-printed":
            raise AssertionError(f"unexpected owner decision: {decision}")
        if decision["authority"] != "collection-owner":
            raise AssertionError(f"unexpected decision authority: {decision}")
        if decision["basis"] != "multi-source-adjudication":
            raise AssertionError(f"unexpected decision basis: {decision}")
        if not decision["rationale"] or not decision["evidenceRefs"]:
            raise AssertionError(f"owner decision lacks rationale or evidence refs: {decision}")

    connection = sqlite3.connect(DATABASE)
    try:
        rows = connection.execute(
            "SELECT unit_id, repository_verdict, application_status, absence_supported, "
            "decision_authority, decision_basis, decision_rationale, decision_evidence_refs_json "
            "FROM app_language_availability WHERE adjudication_id IS NOT NULL"
        ).fetchall()
        if {row[0] for row in rows} != EXPECTED_UNIT_IDS:
            raise AssertionError("database owner-adjudication coverage differs from canonical store")
        for unit_id, verdict, status, absence_supported, authority, basis, rationale, refs_json in rows:
            expected_absence_supported = int(unit_id in SOURCE_SCOPED_UNIT_IDS)
            if (verdict, status, absence_supported, authority, basis) != (
                "contradicted", "not-printed", expected_absence_supported,
                "collection-owner", "multi-source-adjudication"
            ):
                raise AssertionError(f"invalid owner projection for {unit_id}: {verdict, status, absence_supported, authority, basis}")
            if not rationale or not json.loads(refs_json):
                raise AssertionError(f"owner projection lost provenance for {unit_id}")

        ordinary_disputed = connection.execute(
            "SELECT COUNT(*) FROM app_language_availability "
            "WHERE application_status='disputed' AND adjudication_id IS NULL"
        ).fetchone()[0]
        if ordinary_disputed != 73:
            raise AssertionError(f"expected 73 non-adjudicated disputed rows, found {ordinary_disputed}")
        elitefourum_capability = connection.execute(
            "SELECT supports_absence FROM providers WHERE provider_id='elitefourum'"
        ).fetchone()[0]
        if elitefourum_capability != 1:
            raise AssertionError("Elite Fourum must retain scoped absence capability")
    finally:
        connection.close()

    print(f"owner adjudication regressions passed: {len(rows)} owner decisions, {ordinary_disputed} disputed rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
