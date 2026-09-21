#!/usr/bin/env python3
"""Check the finite Malie contract against existing identities, without writes."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def check_profile(profile: dict, catalogue: dict) -> None:
    assert profile["profileId"] == "snoredex-malie-sv-pilot/1"
    upstream = profile["upstream"]
    assert upstream["url"] == "https://malie.io/static/draft/html/pkproto_sv.html"
    assert upstream["declaredVersion"] == "2024-05-20"
    for name in ("responseSha256", "normalizedHtmlSha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", upstream[name]), name
    items = {item["itemId"]: item for item in catalogue["items"]}
    selected = profile["pilot"]
    assert len({row["itemId"] for row in selected}) == len(selected), "duplicate selection"
    positives = []
    for row in selected:
        assert row["itemId"] in items, f"unknown selected ID: {row['itemId']}"
        actual = items[row["itemId"]]
        for key in ("cardReleaseId", "physicalPrintingId", "localizationId"):
            assert row[key] == actual[key], f"selection identity drift: {row['itemId']} {key}"
        if row["purpose"] == "mandatory-positive":
            assert actual["itemKind"] == "verified-printing"
            assert actual["physicalPrintingId"] is not None
            assert actual["finish"] == "non-holo"
            assert actual["localizationId"] in profile["languages"]
            positives.append(actual)
    assert len(positives) >= profile["minimumRealExportedPrintings"] >= 2
    assert len({r["localizationId"] for r in positives}) >= profile["minimumRealExportedLanguages"] >= 2
    assert profile["statusPrecedence"] == [
        "outside-profile", "blocked-by-source", "needs-evidence", "needs-mapping", "exported"
    ]


def main() -> None:
    profile = read("verification/malie_profile.json")
    catalogue = read("collector_catalogue.json")
    check_profile(profile, catalogue)
    # A plausible but mismatched printing must not silently change the selected target.
    altered = json.loads(json.dumps(profile))
    altered["pilot"][0]["physicalPrintingId"] = "PHYSICAL:unrelated"
    try:
        check_profile(altered, catalogue)
    except AssertionError:
        pass
    else:
        raise AssertionError("profile identity guard did not reject a changed printing")
    fixture = read("verification/fixtures/malie_contract.json")
    assert fixture["fixtureKind"] == "synthetic-contract-only"
    assert fixture["profileId"] == profile["profileId"]
    payload = fixture["validPayload"]
    assert payload["collector_number"]["numerator"] == "001"
    assert payload["retreat"] == 0 and type(payload["retreat"]) is int
    assert payload["text"][1]["damage"]["amount"] == 0
    assert [block["kind"] for block in payload["text"]] == ["ABILITY", "ATTACK"]
    assert payload["text"][1]["cost"] == ["FREE"]
    comparison = read("verification/evidence/issue-385-malie-reference.json")
    assert {entry["language"] for entry in comparison["exports"]} == {"en-US", "de-DE"}
    for entry in comparison["exports"]:
        encoded = json.dumps(entry["records"], ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
        assert hashlib.sha256(encoded).hexdigest() == entry["excerptSha256"]
        records = [row["record"] for row in entry["records"]]
        assert len(records) == entry["selectionCount"] == 2
        assert all(row["collector_number"]["full"] == "143/165" for row in records)
        assert all(row["lang"] == entry["language"] for row in records)
        assert {row["name"] for row in records} == {
            "Relaxo" if entry["language"] == "de-DE" else "Snorlax"
        }
        assert [row.get("foil") for row in records] == [None, {"type": "FLAT_SILVER", "mask": "REVERSE"}]
        assert all("stage_text" not in row for row in records), "revisit documented draft/reference discrepancy"
    print(f"Malie profile: {len(profile['pilot'])} existing targets; identity guard and reference digests passed.")
    print("Contract-only check: does not prove field evidence, payload conformance or an implemented export.")


if __name__ == "__main__":
    main()
