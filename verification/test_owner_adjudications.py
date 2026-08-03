#!/usr/bin/env python3
"""Regression checks for owner-level application decisions.

These checks deliberately inspect both the raw verdict and the clean handoff projection. The
owner's final decision may make an application row ``not-printed`` without pretending that the
provider itself supplied an exhaustive absence manifest.

Nothing here freezes *which* units the owner has decided, or how many. That list grows every time
the owner adjudicates, and a test that had to be edited on each such occasion would be a test
people learn to edit rather than read. What is asserted instead is that the canonical store and
the database projection say the same thing, and that each decision is well-formed.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from absence_model import absence_scope_urls  # noqa: E402

DATABASE = ROOT / "snoredex.sqlite"


def main() -> int:
    owner_doc = json.loads(
        (ROOT / "verification" / "owner_adjudications.json").read_text(encoding="utf-8")
    )
    raw_units = {
        unit["unitId"]: unit
        for unit in json.loads((ROOT / "verification" / "units.json").read_text(encoding="utf-8"))
    }
    registry = json.loads(
        (ROOT / "verification" / "source_registry.json").read_text(encoding="utf-8")
    )
    scope_urls = absence_scope_urls(registry["providers"])

    decisions = owner_doc["decisions"]
    decision_ids = {item["unitId"] for item in decisions}
    if not decision_ids:
        raise AssertionError("owner adjudication store is empty")
    if len(decisions) != len(decision_ids):
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

    # A unit's source only "supports absence" when it is one of the declared complete manifests.
    # The owner's decision never confers that property, so the projection must not invent it.
    source_scoped = {
        unit_id
        for unit_id in decision_ids
        if (raw_units[unit_id].get("sourceUrl") or "").rstrip("/") in scope_urls
    }
    contradicted_ids = {
        unit_id for unit_id, unit in raw_units.items() if unit["status"] == "contradicted"
    }
    expected_disputed = len(contradicted_ids - decision_ids)

    connection = sqlite3.connect(DATABASE)
    try:
        rows = connection.execute(
            "SELECT unit_id, repository_verdict, application_status, absence_supported, "
            "decision_authority, decision_basis, decision_rationale, decision_evidence_refs_json "
            "FROM app_language_availability WHERE adjudication_id IS NOT NULL"
        ).fetchall()
        if {row[0] for row in rows} != decision_ids:
            raise AssertionError("database owner-adjudication coverage differs from canonical store")
        for unit_id, verdict, status, absence_supported, authority, basis, rationale, refs_json in rows:
            expected_absence_supported = int(unit_id in source_scoped)
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
        if ordinary_disputed != expected_disputed:
            raise AssertionError(
                f"expected {expected_disputed} non-adjudicated disputed rows "
                f"(contradicted units without an owner decision), found {ordinary_disputed}"
            )
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
