#!/usr/bin/env python3
"""Regression checks for the versioned, offline TCGdex finish input."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
from pathlib import Path
from copy import deepcopy

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


def assert_product_scoped_holo(unit, case):
    holos = [printing for printing in unit['printings'] if printing['finish'] == 'holo']
    assert not any(not p.get('distribution') and not p.get('markings') and not p.get('foilPattern')
                   for p in holos), 'generic Holo must not duplicate existing product-backed identities'
    base = [p for p in holos if p['mappedVariants'] == [case['variant']]
            and (p.get('distribution') or {}).get('kind') == case['expectedDistributionKind']]
    assert len(base) == 1, 'positive field evidence must attach to exactly one existing base identity'
    assert case['sourceUrl'] in {source.get('url') for source in base[0]['sources']}
    assert all(case['sourceUrl'] not in {source.get('url') for source in p['sources']}
               for p in holos if p['mappedVariants'] == ['V2']), 'V1 evidence cannot corroborate V2'


def verify_product_scoped_refinement(finishes):
    fixture = json.loads((ROOT / 'verification/evidence/issue-438-finish-review-20261102/product-refinement-regression.json').read_text(encoding='utf-8'))
    context = finishes._load_finish_context()
    context.update(tcgdex_data={url: record['payload'] for url, record in context['snapshot_document']['records'].items()}, fetch_errors={})
    for case in fixture['cases']:
        record = case['record']
        assert finishes.json_hash(record['payload']) == record['contentHash']
        assert record['payload']['variants']['holo'] is True
        assert any((row.get('thirdParty') or {}).get('cardmarket') == case['cardmarketProductId']
                   for row in finishes.tcgdex_regular_details(record['payload'], 'holo'))
        card = context['cards_by_product'][(case['setCode'], case['number'], case['variant'])]
        product_id = case['cardmarketProductId']
        assert card['imageUrl'].endswith(f'/{product_id}/{product_id}.jpg')
        context['tcgdex_data'][case['sourceUrl']] = record['payload']
    finishes._prepare_finish_indexes(context)
    for case in fixture['cases']:
        key = (case['setCode'], case['number'], case['language'])
        result = finishes._build_finish_unit(context, 1, key)
        assert_product_scoped_holo(result, case)
        assert finishes._build_finish_unit(context, 1, key) == result, 'replay must not accumulate evidence'
        reordered = deepcopy(context)
        overrides = reordered['overrides_by_group'][(case['setCode'], case['number'])]
        overrides.reverse()
        for override in overrides:
            if 'printings' in override:
                override['printings'].reverse()
        other = finishes._build_finish_unit(reordered, 1, key)
        assert_product_scoped_holo(other, case)
        def identities(unit):
            return {finishes.printing_signature(p): {source.get('url') for source in p['sources']}
                    for p in unit['printings']}
        assert identities(result) == identities(other), 'source ordering must preserve identity/provenance'
        seeded = deepcopy(result)
        seeded['printings'].append({'finish': 'holo', 'distribution': None, 'markings': None,
                                   'foilPattern': None, 'mappedVariants': [case['variant']],
                                   'sources': [{'url': case['sourceUrl']}]})
        try:
            assert_product_scoped_holo(seeded, case)
        except AssertionError as error:
            assert 'generic Holo' in str(error)
        else:
            raise AssertionError('seeded duplicate verified printing escaped the regression')


def main() -> None:
    finishes = load_finishes()
    verify_product_scoped_refinement(finishes)
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
    # Aggregate availability across distributions must not regularize stamped cards.
    for field, native in (("normal", "normal"), ("holo", "holo"), ("reverse", "reverse")):
        aggregate = {"variants": {field: True}}
        assert finishes.tcgdex_regular_variant(aggregate, field)
        qualified = {**aggregate, "variants_detailed": [
            {"type": native, "size": "standard", "stamp": ["player-rewards-program"]}]}
        assert not finishes.tcgdex_regular_variant(qualified, field)
        for qualifier in ({"foil": "unreviewed"}, {"subtype": "error"}, {"size": "jumbo"}):
            assert not finishes.tcgdex_regular_variant({**aggregate, "variants_detailed": [
                {"type": native, "size": "standard", **qualifier}]}, field)
        qualified["variants_detailed"].append({"type": native, "size": "standard"})
        assert finishes.tcgdex_regular_variant(qualified, field)
        qualified["variants"][field] = False
        assert not finishes.tcgdex_regular_variant(qualified, field)
    for field, native, size in (("normal", "Normale", "Standard"),
                                ("normal", "básico", "estándar"),
                                ("holo", "Olografica", "Standard"),
                                ("reverse", "Reverse", "Padrão")):
        assert finishes.tcgdex_regular_variant({"variants": {field: True},
            "variants_detailed": [{"type": native, "size": size}]}, field)
    for field, native, foil in (("holo", "holo", "Cosmos"), ("holo", "Holo", "Ouro"),
                               ("reverse", "Reverse", "Énergie")):
        assert finishes.tcgdex_regular_variant({"variants": {field: True},
            "variants_detailed": [{"type": native, "size": "standard", "foil": foil}]}, field)
    for foil in ("pokeball", "masterball", "league"):
        assert not finishes.tcgdex_regular_variant({"variants": {"reverse": True},
            "variants_detailed": [{"type": "reverse", "size": "standard", "foil": foil}]}, "reverse")
    assert not finishes.tcgdex_regular_variant({"variants": {"holo": True},
        "variants_detailed": [{"type": "holo"}]}, "holo")
    assert not finishes.tcgdex_regular_variant({"variants": {"holo": True},
        "variants_detailed": [{"type": "unreviewed", "size": "standard"}]}, "holo")

    # Qualified API evidence attaches to one compatible physical identity, never another copy.
    def cosmos_evidence():
        return {"finish": "holo", "foilPattern": None, "cardSize": "standard",
                "mappedVariants": ["base"], "verificationStatus": "confirmed", "_origin": "auto",
                "_tcgdexFoilPattern": "cosmos", "sources": [{"url": "https://example.test/api"}]}
    def observed_cosmos(**extra):
        return {"finish": "holo", "foilPattern": "cosmos", "cardSize": "standard",
                "mappedVariants": ["base"], "verificationStatus": "confirmed", "_origin": "specimen",
                "markings": [{"kind": "observed-marking", "role": "print-identity", "text": "promo"}],
                "sources": [{"url": "https://example.test/photo"}], **extra}
    target = observed_cosmos()
    assert finishes.absorb_qualified_tcgdex_evidence([cosmos_evidence(), target]) == [target]
    assert len(target["sources"]) == 2 and target["markings"]
    assert finishes.absorb_qualified_tcgdex_evidence([target, cosmos_evidence()]) == [target]
    assert len(target["sources"]) == 2, "replay must not duplicate provenance"
    for extra in ({"cardSize": "jumbo"}, {"edition": "1st Edition"},
                  {"foilPattern": "unreviewed"}, {"distribution": {"kind": "prerelease"}},
                  {"markings": [{"kind": "staff", "role": "distribution-promo", "text": "Staff"}]}):
        assert len(finishes.absorb_qualified_tcgdex_evidence([cosmos_evidence(), observed_cosmos(**extra)])) == 2
    one, two = observed_cosmos(), observed_cosmos(markings=[{
        "kind": "observed-marking", "role": "print-identity", "text": "other"}])
    assert len(finishes.absorb_qualified_tcgdex_evidence([cosmos_evidence(), one, two])) == 3
    for extra in ({"verificationStatus": "pending"}, {"conflictsWith": ["SPEC-conflict"]}):
        conflict = observed_cosmos(**extra)
        for items in ([cosmos_evidence(), conflict], [conflict, cosmos_evidence()]):
            assert len(finishes.absorb_qualified_tcgdex_evidence(items)) == 2
            assert conflict["verificationStatus"] == extra.get("verificationStatus", "confirmed")
    unknown = cosmos_evidence()
    unknown.pop("_tcgdexFoilPattern")
    assert len(finishes.absorb_qualified_tcgdex_evidence([unknown, one, observed_cosmos(foilPattern="star")])) == 3
    pin = observed_cosmos(foilPattern=None, markings=[], distribution={"kind": "collection-promo"})
    assert finishes.absorb_qualified_tcgdex_evidence([cosmos_evidence(), pin]) == [pin]

    import review_integrity
    probe_url = "https://api.tcgdex.net/test-qualified"
    probe_unit = {"setCode": "TEST", "number": "1", "language": "English", "status": "confirmed",
                  "sourceUrl": probe_url}
    def preservation_check(details, printings):
        suite = review_integrity.Suite()
        review_integrity._check_tcgdex_positives(suite, [probe_unit], [{**probe_unit, "printings": printings}],
            {probe_url: {"payload": {"variants": {"normal": True}, "variants_detailed": details}}})
        return suite.checks[0].ok
    stamped = [{"type": "normal", "size": "standard", "stamp": ["player-rewards-program"]}]
    regular = [{"type": "normal", "size": "standard"}]
    assert preservation_check(stamped, [])
    assert not preservation_check(regular, []), "a seeded missing regular positive must still fail"
    assert preservation_check(regular, [{"finish": "non-holo", "sources": [{"url": probe_url}]}])

    retained = {"setCode": "TEST", "number": "1", "language": "English", "printings": [{
        "printingId": "FTEST-P01", "finish": "non-holo", "cardSize": "standard",
        "mappedVariants": ["base"], "verificationStatus": "confirmed"}]}
    assert finishes.refresh_printing_losses([retained], [retained]) == []
    assert finishes.refresh_printing_losses([retained], [])
    downgraded = {**retained, "printings": [{**retained["printings"][0],
                                           "verificationStatus": "marketplace-claimed"}]}
    assert finishes.refresh_printing_losses([retained], [downgraded])
    wrong_stamp = {**retained, "printings": [{**retained["printings"][0],
        "markings": [{"kind": "staff", "text": "Staff", "role": "distribution-promo"}]}]}
    assert finishes.refresh_printing_losses([retained], [wrong_stamp])
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
        original_prepare = finishes._prepare_finish_indexes
        original_build = finishes._build_finish_units
        original_output = finishes.OUTPUT_PATH
        finishes._prepare_finish_indexes = lambda _context: None
        finishes._build_finish_units = lambda _context: [retained]
        finishes.OUTPUT_PATH = temporary_root / "finish_units.json"
        finishes.OUTPUT_PATH.write_text(json.dumps({"units": [retained]}), encoding="utf-8")
        finishes.SNAPSHOT_PATH = snapshot_path
        finishes.REFRESH_CANDIDATE_PATH = candidate_path
        finishes.CACHE_DIR = temporary_root / "cache"
        try:
            finishes.write_refresh_candidate(staged)
            sys.argv = ["finishes.py", "--refresh", "--accept-refresh"]
            previous_bytes = snapshot_path.read_bytes()
            finishes._build_finish_units = lambda _context: []
            context = {"tcgdex_urls": sorted(staged), "snapshot_document": old_snapshot}
            assert finishes._resolve_tcgdex(context) == 2
            assert snapshot_path.read_bytes() == previous_bytes
            assert candidate_path.exists()
            finishes._build_finish_units = lambda _context: [retained]
            context = {"tcgdex_urls": sorted(staged), "snapshot_document": old_snapshot}
            assert finishes._resolve_tcgdex(context) is None
            accepted = json.loads(snapshot_path.read_text(encoding="utf-8"))
            assert context["snapshot_document"] == accepted
        finally:
            finishes.SNAPSHOT_PATH = original_snapshot_path
            finishes._prepare_finish_indexes = original_prepare
            finishes._build_finish_units = original_build
            finishes.OUTPUT_PATH = original_output
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

    # A pattern-less marketplace claim folds into its one photographed patterned printing (JP mC
    # 568); with two patterned candidates, or when the claim is stronger evidence, nothing folds.
    claim = {**printing(None), "finish": "reverse-holo", "verificationStatus": "marketplace-claimed"}
    star = {**claim, "foilPattern": "star", "verificationStatus": "confirmed", "specimenIds": ["SPEC-9999"],
            "sources": [{"url": "https://example.test/photo", "sourceType": "x", "evidence": "e"}]}
    folded = finishes.absorb_patternless_marketplace_claims([claim, star])
    assert folded == [star] and len(star["sources"]) == 2 and star["verificationStatus"] == "confirmed"
    ball = {**star, "foilPattern": "poke-ball", "sources": list(star["sources"])}
    assert len(finishes.absorb_patternless_marketplace_claims([claim, star, ball])) == 3
    tcgdex = {**claim, "verificationStatus": "confirmed"}
    assert tcgdex in finishes.absorb_patternless_marketplace_claims([tcgdex, star])

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
