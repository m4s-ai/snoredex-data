#!/usr/bin/env python3
"""Regression checks for the versioned, offline TCGdex finish input."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "verification" / "finish_tcgdex_snapshot.json"
UNITS = ROOT / "verification" / "units.json"


def load_finishes():
    spec = importlib.util.spec_from_file_location("finishes", ROOT / "scripts" / "finishes.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_finish_source_verifier():
    spec = importlib.util.spec_from_file_location(
        "verify_finish_sources", ROOT / "verification" / "verify_finish_sources.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    finishes = load_finishes()
    document = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    records = document.get("records", {})
    expected = {
        row["sourceUrl"] for row in json.loads(UNITS.read_text(encoding="utf-8"))
        if row.get("status") == "confirmed"
        and str(row.get("sourceUrl") or "").startswith("https://api.tcgdex.net/")
    }
    assert document.get("schema") == "snoredex-tcgdex-snapshot/1"
    assert set(records) == expected
    assert all(finishes.json_hash(row["payload"]) == row["contentHash"]
               and finishes.implausible(row["payload"]) is None
               for row in records.values())
    url = sorted(records)[0]
    fetched_url, payload, error = finishes.fetch_tcgdex(url, offline=True)
    assert (fetched_url, error) == (url, None)
    assert payload == records[url]["payload"]
    assert finishes.snapshot_drift(
        {"same": {"contentHash": "sha256:a"}, "removed": {"contentHash": "sha256:b"}},
        {"same": {"contentHash": "sha256:c"}, "added": {"contentHash": "sha256:d"}},
    ) == (["same"], ["added"], ["removed"])
    with tempfile.TemporaryDirectory() as temporary:
        candidate_path = Path(temporary) / "candidate.json"
        original_candidate_path = finishes.REFRESH_CANDIDATE_PATH
        original_cache_dir = finishes.CACHE_DIR
        finishes.REFRESH_CANDIDATE_PATH = candidate_path
        # Keep the refresh-candidate regression out of the production fetch cache.  The release
        # gate deliberately rejects cache directories left behind by any test or generator.
        finishes.CACHE_DIR = candidate_path.parent
        try:
            staged = {"https://api.tcgdex.net/test": {
                "contentHash": finishes.json_hash({"id": "test-card"}),
                "payload": {"id": "test-card"},
            }}
            finishes.write_refresh_candidate(staged)
            assert finishes.load_refresh_candidate(set(staged)) == staged
            candidate_path.write_text(candidate_path.read_text(encoding="utf-8")
                                      .replace("test-card", "tampered"), encoding="utf-8")
            try:
                finishes.load_refresh_candidate(set(staged))
            except ValueError:
                pass
            else:
                raise AssertionError("tampered refresh candidate must fail closed")
        finally:
            finishes.REFRESH_CANDIDATE_PATH = original_candidate_path
            finishes.CACHE_DIR = original_cache_dir
    with tempfile.TemporaryDirectory() as temporary:
        temporary_root = Path(temporary)
        snapshot_path = temporary_root / "snapshot.json"
        candidate_path = temporary_root / "candidate.json"
        old_snapshot = {
            "schema": "snoredex-tcgdex-snapshot/1",
            "generated": "2026-08-01",
            "records": staged,
        }
        snapshot_path.write_text(json.dumps(old_snapshot), encoding="utf-8")
        original_snapshot_path = finishes.SNAPSHOT_PATH
        original_candidate_path = finishes.REFRESH_CANDIDATE_PATH
        original_cache_dir = finishes.CACHE_DIR
        original_arguments = sys.argv
        finishes.SNAPSHOT_PATH = snapshot_path
        finishes.REFRESH_CANDIDATE_PATH = candidate_path
        finishes.CACHE_DIR = temporary_root / "cache"
        try:
            finishes.write_refresh_candidate(staged)
            sys.argv = ["finishes.py", "--refresh", "--accept-refresh"]
            context = {"tcgdex_urls": sorted(staged), "snapshot_document": old_snapshot}
            assert finishes._resolve_tcgdex(context) is None
            accepted = json.loads(snapshot_path.read_text(encoding="utf-8"))
            assert context["snapshot_document"] == accepted
        finally:
            finishes.SNAPSHOT_PATH = original_snapshot_path
            finishes.REFRESH_CANDIDATE_PATH = original_candidate_path
            finishes.CACHE_DIR = original_cache_dir
            sys.argv = original_arguments

    verifier = load_finish_source_verifier()
    with tempfile.TemporaryDirectory() as temporary:
        temporary_root = Path(temporary)
        verification = temporary_root / "verification"
        fixture = verification / "fixtures" / "tcgcsv_finish_sources.json"
        fixture.parent.mkdir(parents=True)
        old_fixture = b'{"responses":{"old":true}}\n'
        fixture.write_bytes(old_fixture)
        (verification / "finish_overrides.json").write_text(
            json.dumps({
                "sources": {
                    "test": {
                        "expectedSubtypes": {"1": ["Normal"]},
                        "identityUrl": "https://example.test/identity",
                        "url": "https://example.test/prices",
                    }
                }
            }),
            encoding="utf-8",
        )
        original_verification = verifier.VERIFICATION
        original_fixture = verifier.FIXTURE
        original_urlopen = verifier.urllib.request.urlopen
        original_arguments = sys.argv

        def unavailable(*_args, **_kwargs):
            raise OSError("simulated total network failure")

        verifier.VERIFICATION = verification
        verifier.FIXTURE = fixture
        verifier.urllib.request.urlopen = unavailable
        try:
            sys.argv = ["verify_finish_sources.py", "--record"]
            assert verifier.main() == 2
        finally:
            sys.argv = original_arguments
            verifier.urllib.request.urlopen = original_urlopen
            verifier.VERIFICATION = original_verification
            verifier.FIXTURE = original_fixture
        assert fixture.read_bytes() == old_fixture
        assert not fixture.with_name(fixture.name + ".tmp").exists()

        # A product with no current price row is the export's silence, not a mismatch; a price
        # row without the expected subtype, or a vanished product, still fails.
        identity = {"success": True, "error": None,
                    "results": [{"productId": 1, "name": "Snorlax"}]}
        cases = (
            ([], True, 0),
            ([{"productId": 1, "subTypeName": "Holofoil"}], True, 1),
            ([], False, 1),
        )
        for price_rows, product_listed, expected_exit in cases:
            products = identity if product_listed else {**identity, "results": []}
            fixture.write_text(json.dumps({"responses": {
                "https://example.test/identity": products,
                "https://example.test/prices": {"success": True, "error": None,
                                                "results": price_rows},
            }}), encoding="utf-8")
            verifier.VERIFICATION = verification
            verifier.FIXTURE = fixture
            try:
                sys.argv = ["verify_finish_sources.py", "--replay"]
                assert verifier.main() == expected_exit, (price_rows, product_listed)
            finally:
                sys.argv = original_arguments
                verifier.VERIFICATION = original_verification
                verifier.FIXTURE = original_fixture

        # A price gap must never overwrite the fixture's positive rows through --record.
        live_payloads = {
            "https://example.test/identity": {"results": identity["results"]},
            "https://example.test/prices": {"results": []},
        }

        def gap_only(request, **_kwargs):
            return io.BytesIO(json.dumps(live_payloads[request.full_url]).encode("utf-8"))

        recorded_fixture = fixture.read_bytes()
        verifier.VERIFICATION = verification
        verifier.FIXTURE = fixture
        verifier.urllib.request.urlopen = gap_only
        try:
            sys.argv = ["verify_finish_sources.py", "--record"]
            assert verifier.main() == 2
        finally:
            sys.argv = original_arguments
            verifier.urllib.request.urlopen = original_urlopen
            verifier.VERIFICATION = original_verification
            verifier.FIXTURE = original_fixture
        assert fixture.read_bytes() == recorded_fixture

    # Card-level finish evidence folds into a complete edition pair; a specimen-backed or
    # half-covered editionless printing stays a separate, edition-unknown observation.
    def printing(edition, **extra):
        return {"finish": "holo", "edition": edition, "foilPattern": None, "distribution": None,
                "markings": None, "mappedVariants": ["V1"], "verificationStatus": "owner-attested",
                "sources": [{"url": f"https://example.test/{edition}", "sourceType": "x", "evidence": "e"}],
                **extra}
    generic = printing(None, verificationStatus="confirmed")
    pair = [printing("1st Edition"), printing("Unlimited")]
    folded = finishes.absorb_editionless_finish_evidence([generic, *pair])
    assert [row["edition"] for row in folded] == ["1st Edition", "Unlimited"]
    assert all(row["verificationStatus"] == "confirmed" and len(row["sources"]) == 2 for row in folded)
    observed = printing(None, specimenIds=["SPEC-9999"])
    assert observed in finishes.absorb_editionless_finish_evidence([observed, *pair])
    jumbo = printing(None, cardSize="jumbo")
    assert jumbo in finishes.absorb_editionless_finish_evidence(
        [jumbo, *[{**row, "cardSize": "standard"} for row in pair]])
    decision = {"adjudicationId": "OAF-test", "rejectedFinishes": ["non-holo"]}
    normal = {**printing(None), "finish": "non-holo"}
    assert finishes.drop_owner_rejected_finishes([normal, *pair], decision) == pair
    try:
        finishes.drop_owner_rejected_finishes([{**normal, "specimenIds": ["SPEC-9999"]}], decision)
    except ValueError:
        pass
    else:
        raise AssertionError("a photographed rejected finish must stop the build")
    half = [printing(None), printing("Unlimited")]
    assert len(finishes.absorb_editionless_finish_evidence(half)) == 2

    original_arguments = sys.argv
    try:
        sys.argv = ["finishes.py", "--offline", "--check", "--reproject"]
        try:
            finishes.main()
        except ValueError as error:
            assert "reproject" in str(error)
        else:
            raise AssertionError("--check --reproject must fail")
    finally:
        sys.argv = original_arguments
    print(f"tcgdex snapshot regression passed: {len(records)} hashed records, offline")


if __name__ == "__main__":
    main()
