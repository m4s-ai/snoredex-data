#!/usr/bin/env python3
"""Regression checks for the #140 authoritative graph boundary."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "verification" / "passes"))
import authoritative_graph as graph_module  # noqa: E402
import admit_issue263_traditional_chinese_20260828 as issue263_pass  # noqa: E402
import admit_pokemon_korea_catalogue_20260901 as korean_catalogue_pass  # noqa: E402
import map_bs2_space_time_work_20260901 as bs2_work_pass  # noqa: E402
import admit_30th_cn_20261001 as admission_30th  # noqa: E402
import correct_kss_spanish_digital_only_20261001 as kss_correction  # noqa: E402
from authoritative_graph import identity_view, project_physical_evidence, validate  # noqa: E402


def issue263_rebuilt_graph() -> dict:
    prints = issue263_pass.read(issue263_pass.PRINTS)
    existing = {row["printId"]: row for row in prints["prints"]}
    official = issue263_pass.official_rows(existing)
    photos = issue263_pass.enrich_photo_rows()
    rows = official + photos + issue263_pass.supplemental_rows(existing)
    sources = issue263_pass.read(issue263_pass.SET_SOURCES)
    profiles = issue263_pass.apply_profiles(sources, rows)
    units = {row["unitId"]: row for row in issue263_pass.read(issue263_pass.UNITS)}
    graph = issue263_pass.read(issue263_pass.GRAPH)
    issue263_pass.remove_superseded_graph_records(graph)
    rebuilt, _ = issue263_pass.apply_graph(graph, profiles, rows, units)
    return rebuilt


def verify_30th_admission_replay():
    names = ["authoritative_graph.json", "source_first_prints.json",
             "set_catalogue_sources.json", "rarity_catalogue.json", "specimens.json"]
    for mode in ("unchanged", "changed", "missing"):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            verification = root / "verification"
            verification.mkdir()
            for name in names:
                (verification / name).write_bytes((ROOT / "verification" / name).read_bytes())
            path = verification / "set_catalogue_sources.json"
            sources = json.loads(path.read_text(encoding="utf-8"))
            ids = {admission_30th.SID, admission_30th.SID + "-OWNER-RARITY"}
            original_order = [r["sourceRecordId"] for r in sources["sourceRecords"]]
            unrelated = [r for r in sources["sourceRecords"] if r["sourceRecordId"] not in ids]
            if mode == "changed":
                next(r for r in sources["sourceRecords"]
                     if r["sourceRecordId"] == admission_30th.SID)["raw"]["printedRarity"] = "stale"
            if mode == "missing":
                sources["sourceRecords"] = unrelated
            kss_correction.write(path, sources)
            before = {name: (verification / name).read_bytes() for name in names}
            with patch.object(admission_30th, "ROOT", root), patch.object(admission_30th, "V", verification):
                admission_30th.main()
                after = {name: (verification / name).read_bytes() for name in names}
                specimen = next(r for r in json.loads(after['specimens.json'])['specimens']
                                if r['specimenId'] == 'SPEC-0600')
                assert specimen['heldBy'] == 'not established; image supplied by collection owner'
                import source_registry as registry
                assert registry.specimen_provider(specimen['photographSource'],
                    registry.specimen_source_type(specimen)) == 'inspected-specimen'
                admitted = next(r for r in json.loads(after['source_first_prints.json'])['prints']
                                if r['printId'] == admission_30th.PID)
                assert admitted['providerId'] == 'inspected-specimen'
                original = next(r for r in json.loads(before['specimens.json'])['specimens']
                                if r['specimenId'] == 'SPEC-0600')
                for field in ('photographSha256', 'recordedAt', 'physicalObservation', 'citedBy'):
                    assert specimen[field] == original[field]
                if mode == "unchanged":
                    assert after == before, "unchanged admission replay must be byte-idempotent"
                records = json.loads(path.read_text(encoding="utf-8"))["sourceRecords"]
                assert [r for r in records if r["sourceRecordId"] not in ids] == unrelated
                assert len([r for r in records if r["sourceRecordId"] in ids]) == 2
                if mode != "missing":
                    assert [r["sourceRecordId"] for r in records] == original_order
                admission_30th.main()
                assert {name: (verification / name).read_bytes() for name in names} == after


def verify_kss_retirement_replay():
    names = ["verification/units.json", "verification/specimens.json",
             "verification/owner_adjudications.json", "verification/authoritative_graph.json",
             "verification/evidence.jsonl", "verification/evidence/issue-266-spanish-evidence.json",
             "snorlax_cards.json"]
    journal = [json.loads(line) for line in (ROOT / "verification/evidence.jsonl")
               .read_text(encoding="utf-8").splitlines() if line.strip()]
    original_evidence = {r["unitId"]: r["evidence"] for entry in journal
                        for r in entry.get("supersededSiblingObservations", [])
                        if r["setCode"] == "KSS" and kss_correction.OLD_LANGUAGES in r["evidence"]
                        and kss_correction.LIST_CORRECTION not in r["evidence"]}
    assert set(original_evidence) == {"U0484", "U0485", "U0488", "U0489", "U0490", "U0494", "U0495"}
    graph = kss_correction.read(ROOT / "verification/authoritative_graph.json")
    retired = {e["entityId"]: e for row in journal for e in row.get("supersededGraphEntities", [])
               if e["entityId"] in kss_correction.RETIRED_IDS}
    retired.update({e["entityId"]: e for e in graph["entities"]
                    if e["entityId"] in kss_correction.RETIRED_IDS})
    assert set(retired) == kss_correction.RETIRED_IDS
    for mode in ("initial", "partial", "already-retired", "after-units",
                 "after-specimen", "after-adjudication", "stale-adjudication"):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in names:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / name).read_bytes())
            restored = deepcopy(graph)
            if mode != "already-retired":
                restored["entities"] = [e for e in restored["entities"]
                                        if e["entityId"] not in retired] + list(retired.values())
                restored["edges"].append(dict(fromId=kss_correction.EDITION, toId="LOCALSET:WEST:KSS",
                    fromType="set-edition", toType="local-set", relation="belongs-to", provenance={}))
            product = next(e for e in restored["entities"]
                           if e["entityType"] == "legacy-cardmarket-product"
                           and kss_correction.CLAIM in e["payload"]["claimIds"])
            product["payload"]["reason"] = "7 established language-bearing card release(s)"
            if mode == "initial":
                product["payload"]["cardReleaseIds"].append(kss_correction.RELEASE)
                claim = next(e["payload"] for e in restored["entities"]
                             if e["entityId"] == kss_correction.CLAIM)
                claim.update(evidenceStatus="confirmed", disposition="established-and-mapped",
                             proposedTargetId=kss_correction.RELEASE,
                             materializedTargetId=kss_correction.RELEASE)
                restored["edges"].append(dict(fromType="candidate-claim", fromId=kss_correction.CLAIM,
                    relation="materializes", toType="card-release", toId=kss_correction.RELEASE, provenance={}))
                unit_migration = next(r for r in restored["migrationDispositions"]
                                      if r["sourceKind"] == "legacy-language-unit" and r["sourceId"] == "U0482")
                unit_migration.update(disposition="established-and-mapped", targetRef=kss_correction.RELEASE)
                migration = next(r for r in restored["migrationDispositions"]
                                 if r["sourceKind"] == "legacy-cardmarket-product"
                                 and r["sourceId"] == product["payload"]["sourceId"])
                migration["targetRefs"].append(kss_correction.RELEASE)
                migration["reason"] = product["payload"]["reason"]
            kss_correction.write(root / "verification/authoritative_graph.json", restored)
            if mode == "initial":
                units = kss_correction.read(root / "verification/units.json")
                prior = next(row["supersededObservation"] for row in journal
                             if row.get("unitId") == "U0482" and "supersededObservation" in row)
                units = [prior if row["unitId"] == "U0482" else row for row in units]
                kss_correction.write(root / "verification/units.json", units)
                adjudications = kss_correction.read(root / "verification/owner_adjudications.json")
                adjudications["decisions"] = [r for r in adjudications["decisions"] if r["unitId"] != "U0482"]
                kss_correction.write(root / "verification/owner_adjudications.json", adjudications)
            if mode in {"initial", "after-units"}:
                specimens = kss_correction.read(root / "verification/specimens.json")
                prior_spec = next(row["supersededSpecimenObservation"] for row in journal
                                  if "supersededSpecimenObservation" in row)
                specimens["specimens"] = [prior_spec if row["specimenId"] == "SPEC-0132" else row
                                          for row in specimens["specimens"]]
                kss_correction.write(root / "verification/specimens.json", specimens)
            if mode in {"after-units", "after-specimen", "stale-adjudication"}:
                adjudications = kss_correction.read(root / "verification/owner_adjudications.json")
                if mode == "stale-adjudication":
                    next(r for r in adjudications["decisions"] if r["unitId"] == "U0482")["rationale"] = "stale"
                else:
                    adjudications["decisions"] = [r for r in adjudications["decisions"] if r["unitId"] != "U0482"]
                kss_correction.write(root / "verification/owner_adjudications.json", adjudications)
            units = kss_correction.read(root / "verification/units.json")
            for row in units:
                if row["unitId"] in original_evidence and mode in {"initial", "already-retired"}:
                    row["evidence"] = original_evidence[row["unitId"]]
                    if mode == "already-retired":
                        row["evidence"] = row["evidence"].replace(kss_correction.OLD_LANGUAGES,
                            kss_correction.PHYSICAL_LANGUAGES) + " " + kss_correction.LIST_CORRECTION
            hxy = next(r for r in units if r["unitId"] == "U0586")
            hxy["evidence"] = hxy["evidence"].replace(kss_correction.HISTORICAL_QUOTE, "Quote:")
            kss_correction.write(root / "verification/units.json", units)
            adjudications = kss_correction.read(root / "verification/owner_adjudications.json")
            next(r for r in adjudications["decisions"] if r["unitId"] == "U0484")["rationale"] = kss_correction.OLD_RATIONALE
            kss_correction.write(root / "verification/owner_adjudications.json", adjudications)
            with patch.object(kss_correction, "ROOT", root), patch.object(kss_correction, "V", root / "verification"):
                kss_correction.main()
                units = kss_correction.read(root / "verification/units.json")
                for row in units:
                    if row["unitId"] in original_evidence:
                        assert row["evidence"] == (kss_correction.HISTORICAL_EVIDENCE
                            + original_evidence[row["unitId"]] + " " + kss_correction.LIST_CORRECTION)
                assert kss_correction.HISTORICAL_QUOTE in next(r for r in units if r["unitId"] == "U0586")["evidence"]
                adjudications = kss_correction.read(root / "verification/owner_adjudications.json")
                assert len([r for r in adjudications["decisions"] if r["unitId"] == "U0482"]) == 1
                decision = next(r for r in adjudications["decisions"] if r["unitId"] == "U0482")
                assert decision["decision"] == "not-printed" and decision["rationale"] == kss_correction.EVIDENCE
                assert not any(kss_correction.OLD_RATIONALE in r["rationale"] for r in adjudications["decisions"])
                spec = next(r for r in kss_correction.read(root / "verification/specimens.json")["specimens"]
                            if r["specimenId"] == "SPEC-0132")
                assert spec["observed"] == kss_correction.SPECIMEN_OBSERVATION
                assert "physicalObservation" not in spec
                original_spec = next(r for r in kss_correction.read(ROOT / "verification/specimens.json")["specimens"]
                                     if r["specimenId"] == "SPEC-0132")
                assert spec["photographSha256"] == original_spec["photographSha256"]
                assert spec["recordedAt"] == original_spec["recordedAt"]
                manifest = kss_correction.read(root / "verification/evidence/issue-266-spanish-evidence.json")
                assert next(r for r in manifest["observations"] if r["specimenId"] == "SPEC-0132")["observed"] == spec["observed"]
                result = kss_correction.read(root / "verification/authoritative_graph.json")
                untouched = lambda g: [e for e in g["entities"] if e["entityId"] not in retired
                                      and e["entityId"] not in {product["entityId"], kss_correction.CLAIM}]
                assert untouched(result) == untouched(restored)
                corrected = next(e["payload"] for e in result["entities"] if e["entityId"] == product["entityId"])
                assert len(corrected["cardReleaseIds"]) == 6
                assert corrected["reason"] == "6 established language-bearing card release(s)"
                migration = next(r for r in result["migrationDispositions"]
                                 if r["sourceKind"] == "legacy-cardmarket-product"
                                 and r["sourceId"] == corrected["sourceId"])
                assert migration["targetRefs"] == corrected["cardReleaseIds"]
                assert migration["reason"] == corrected["reason"]
                claim = next(e["payload"] for e in result["entities"] if e["entityId"] == kss_correction.CLAIM)
                assert claim["evidenceStatus"] == "contradicted" and claim["materializedTargetId"] is None
                assert not any(ref in json.dumps(result) for ref in retired)
                assert not any("release-count reason mismatch" in error for error in validate(result))
                assert result["edges"] == [e for e in restored["edges"]
                    if e["fromId"] not in retired and e["toId"] not in retired]
                assert not any(row["setEditionId"] == kss_correction.EDITION
                               for row in identity_view(result)["setEditions"])
                before = {name: (root / name).read_bytes() for name in names}
                kss_correction.main()
                assert before == {name: (root / name).read_bytes() for name in names}


def verify_release_count_reason_guard(graph):
    for kind in ("product", "migration"):
        tampered = deepcopy(graph)
        if kind == "product":
            row = next(e["payload"] for e in tampered["entities"]
                       if e["entityType"] == "legacy-cardmarket-product")
        else:
            row = next(r for r in tampered["migrationDispositions"]
                       if r["sourceKind"] == "legacy-cardmarket-product")
        row["reason"] = "999 established language-bearing card release(s)"
        assert any("release-count reason mismatch" in error for error in validate(tampered))


def verify_source_first_specimen_registry():
    import source_registry as registry
    document = json.loads((ROOT / 'verification/source_registry.json').read_text(encoding='utf-8'))
    evidence = document['evidence']
    assert all(row['stableIdCount'] == len(row['stableIds']) for row in evidence)
    prints = {row['printId']: row for row in json.loads(
        (ROOT / 'verification/source_first_prints.json').read_text(encoding='utf-8'))['prints']}
    indexed = {}
    for position, row in enumerate(evidence):
        for stable_id in row['stableIds']:
            indexed.setdefault(stable_id, set()).add(position)
    assert not (prints.keys() - indexed.keys()), "every admitted source-first print must be indexed"
    # A non-URL owner rarity decision must not borrow the publisher's authority.
    m6a = prints['JP:M6a:095/103:base']
    owner = next(row for row in evidence if row['providerId'] == 'owner-attestation')
    assert m6a['printId'] in owner['stableIds'] and 'rarity' in owner['dimensions']
    assert owner['canonicalUrl'] is None and m6a['raritySourceUrl'] is None
    assert m6a['providerId'] == 'pokemon-card-jp'
    publisher = next(row for row in evidence if row['canonicalUrl'] == m6a['sourceUrl'])
    assert 'rarity' not in publisher['dimensions']
    for print_id, row in prints.items():
        if row.get('specimenId'):
            assert indexed.get(row['specimenId'], set()) & indexed[print_id], (print_id, row['specimenId'])
    specimens = json.loads((ROOT / 'verification/specimens.json').read_text(encoding='utf-8'))['specimens']
    units = json.loads((ROOT / 'verification/units.json').read_text(encoding='utf-8'))
    finish_units = json.loads((ROOT / 'verification/finish_units.json').read_text(encoding='utf-8'))['units']
    reviewed_graph = json.loads((ROOT / 'verification/authoritative_graph.json').read_text(encoding='utf-8'))
    known_refs = registry.registry_claim_ids(units, list(prints.values()), finish_units, reviewed_graph)
    assert 'CLAIM:positive:56aee25aabfce91a' in known_refs, 'retained reviewed claims are upstream inputs'
    for specimen in specimens:
        if specimen.get('physicalObservation'):
            assert indexed.get(specimen['specimenId']), ('standalone observation omitted', specimen['specimenId'])
        for ref in set(specimen.get('citedBy') or []) & known_refs:
            assert indexed.get(specimen['specimenId'], set()) & indexed.get(ref, set()), (specimen['specimenId'], ref)
    urls = {row['canonicalUrl']: row for row in evidence if row['canonicalUrl']}
    set_sources = json.loads((ROOT / 'verification/set_catalogue_sources.json').read_text(encoding='utf-8'))
    providers = {row['providerId']: row for row in document['providers']}
    for source in set_sources['sourceRecords']:
        if source['sourceKind'] != 'release-date-record':
            continue
        url = source.get('sourceUrl') or source.get('raw', {}).get('sourceUrl')
        if not url and source['provider'] == 'bulbapedia':
            url = 'https://bulbapedia.bulbagarden.net/wiki/' + source['raw']['page'].replace(' ', '_')
        row = urls[registry.canonical_url(url)]
        assert row['providerId'] == source['provider'], source['sourceRecordId']
        assert 'date' in row['dimensions'], source['sourceRecordId']
        assert source['sourceRecordId'] in row['stableIds'], source['sourceRecordId']
        retrieved = source.get('raw', {}).get('retrievedAt') or source.get('retrieved')
        assert not retrieved or row['retrievedAt'] >= retrieved, source['sourceRecordId']
        assert 'date' in providers[source['provider']]['usedFor']
    for row in prints.values():
        if row['providerId'] == 'pokemon-card-korea':
            for url in registry.source_first_registry_urls(row):
                assert 'card-release' in urls[registry.canonical_url(url)]['dimensions'], row['printId']
    items = json.loads((ROOT / 'collector_catalogue.json').read_text(encoding='utf-8'))['items']
    for specimen in specimens:
        number = int(specimen['specimenId'].split('-')[1])
        if not 494 <= number <= 506:
            continue
        matches = [row for row in evidence if specimen['specimenId'] in row['stableIds']]
        owner_matches = [row for row in matches if row['providerId'] == 'owner-attestation']
        attested = specimen.get('physicalObservation', {}).get('ownerAttestedFields', [])
        if attested:
            assert owner_matches, specimen['specimenId']
            for field in attested:
                assert any(field in row['dimensions'] for row in owner_matches)
            assert all(row['retrievedAt'] >= specimen['physicalObservation']['ownerAttestedAt']
                       for row in owner_matches)
        else:
            assert not owner_matches, specimen['specimenId']
        matches = [row for row in matches if row['providerId'] != 'owner-attestation']
        assert matches, specimen['specimenId']
        assert all('identity' in row['dimensions'] for row in matches)
        assert all(row['retrievedAt'] >= '2026-09-09' for row in matches)
        if number in (495, 496):
            assert all(row['providerId'] == 'seller-listing-photo' for row in matches)
            photo_url = registry.canonical_url(registry.provenance_url(specimen['photographSource']))
            assert any(row['canonicalUrl'] == photo_url and 'finish' in row['dimensions'] for row in matches)
        print_id = specimen['citedBy'][0]
        if number == 505:
            assert specimen['specimenId'] not in prints[print_id].get('corroboratingSpecimenIds', [])
            continue
        assert prints[print_id]['corroborated'] is True
        assert all(row['providerId'] != prints[print_id]['providerId'] for row in matches)
        urls = set(prints[print_id]['corroboratingSourceUrls'])
        assert urls
        assert any(urls <= set(item['evidenceLinks']) for item in items)
        assert all(print_id in row['stableIds'] for row in matches)
    calls = []
    specimen = {'specimenId': 'sample', 'heldBy': 'third-party retailer',
                'citedBy': ['print'], 'photographSource': 'https://example.org/card.jpg',
                'recordedAt': '2026-09-09'}
    record = {'printId': 'print', 'corroborated': False}
    registry.record_linked_specimens([specimen], [], lambda *a, **kw: calls.append(a), [record])
    assert {call[3] for call in calls} == {'sample', 'print'}
    assert all(call[2] == 'identity' for call in calls)
    assert record['corroborated'] is False
    calls.clear()
    specimen['citedBy'] = []
    record['specimenId'] = specimen['specimenId']
    registry.record_linked_specimens([specimen], [], lambda *a, **kw: calls.append(a), [record])
    assert {call[3] for call in calls} == {'sample', 'print'}, "direct references need no reverse citation"
    assert record['corroborated'] is False
    calls.clear()
    unit = {'unitId': 'legacy', 'corroborated': False, 'status': 'pending'}
    specimen['citedBy'] = ['legacy', 'F-test-P01', 'unresolved']
    registry.record_linked_specimens([specimen], [unit], lambda *a, **kw: calls.append(a),
        finish_units=[{'printings': [{'printingId': 'F-test-P01'}]}])
    assert {call[3] for call in calls} == {'sample', 'legacy', 'F-test-P01'}
    assert unit == {'unitId': 'legacy', 'corroborated': False, 'status': 'pending'}
    graph_fixture = {'entities': [
        {'entityType': 'candidate-claim', 'entityId': 'reviewed', 'origin': 'reviewed-evidence'},
        {'entityType': 'candidate-claim', 'entityId': 'projected', 'origin': 'physical-evidence-projection'}]}
    assert registry.registry_claim_ids([], [], [], graph_fixture) == {'reviewed'}, 'ignore downstream physical projection'
    calls.clear()
    korean_url = 'https://pokemoncard.co.kr/cards/detail/BS2010002030'
    registry.record_source_first_identity({'providerId': 'pokemon-card-korea',
        'sourceUrl': korean_url, 'printId': 'release'}, lambda *a, **kw: calls.append(a), registry.specimen_surfaces())
    assert {call[2] for call in calls} == {'card-release'}
    calls.clear()
    specimen.update({'photographSource': korean_url, 'citedBy': ['legacy']})
    registry.record_linked_specimens([specimen], [unit], lambda *a, **kw: calls.append(a))
    assert {call[2] for call in calls} == {'identity'}
    render_rows = [row for row in evidence if 'SPEC-0022' in row['stableIds']]
    assert render_rows and all(row['providerId'] == 'owner-attestation' for row in render_rows)
    assert all('identity' not in row['dimensions'] for row in render_rows), 'marketing render is not an inspected card'
    finish_calls = []
    registry.record_specimen_claim('https://example.org/card.jpg', 'Retail listing',
        'retailer-listing', 'identity', 'sample', '2026-09-09',
        {'finish': 'holo', 'ownerAttestedFields': ['finish']},
        lambda *a, **kw: finish_calls.append((a, kw)), registry.specimen_surfaces())
    assert [(a[0], kw['provider_id']) for a, kw in finish_calls if a[2] == 'finish'] == [
        (None, 'owner-attestation')], "an owner finish assertion must not become retailer-image evidence"
    verify_source_first_asset_authority(prints, evidence, registry)
    verify_retained_image_identity(specimens, evidence, registry)
    verify_observed_finish_attribution(specimens, registry)
    verify_standalone_registry_observations(registry)


def verify_standalone_registry_observations(registry):
    calls = []
    registry.record_set_evidence({'sourceRecords': [
        {'sourceRecordId': 'mixed', 'sourceKind': 'edition-availability-record',
         'provider': 'mixed-positive-evidence', 'retrieved': '2026-10-02',
         'raw': {'physicalPrintingEvidence': {'sourceUrl': 'https://www.pokemon.com/us/news/example',
                                              'finish': 'holo'}}},
        {'sourceRecordId': 'identity-only', 'sourceKind': 'edition-availability-record',
         'provider': 'bulbapedia', 'raw': {}}]},
        lambda *args, **kw: calls.append((args, kw)))
    assert len(calls) == 1 and calls[0][0][2:5] == ('finish', 'mixed', '2026-10-02')
    assert calls[0][1]['provider_id'] == 'pokemon-official'
    indexed = json.loads((ROOT / 'verification/source_registry.json').read_text(encoding='utf-8'))['evidence']
    for source in json.loads((ROOT / 'verification/set_catalogue_sources.json').read_text(encoding='utf-8'))['sourceRecords']:
        physical = (source.get('raw') or {}).get('physicalPrintingEvidence')
        if physical and physical.get('finish'):
            assert any(source['sourceRecordId'] in row['stableIds'] and 'finish' in row['dimensions']
                       for row in indexed), source['sourceRecordId']
    direct = registry.direct_specimen_claims(
        [{'unitId': 'U1', 'sourceRef': 'specimen:S1'}],
        [{'printId': 'SF1', 'specimenId': 'S2', 'corroboratingSpecimenIds': ['S3']}],
        {'entities': [
            {'entityType': 'candidate-claim', 'entityId': 'C1', 'origin': 'reviewed', 'payload': {'specimenIds': ['S4']}},
            {'entityType': 'candidate-claim', 'entityId': 'C2', 'origin': 'physical-evidence-projection', 'payload': {'specimenIds': ['S5']}}]})
    assert direct == {'S1': {'U1'}, 'S2': {'SF1'}, 'S3': {'SF1'}, 'S4': {'C1'}}
    calls = []
    specimen = {'specimenId': 'SPEC-standalone', 'citedBy': ['unresolved'],
                'physicalObservation': {'finish': 'holo'}, 'recordedAt': '2026-09-09',
                'photographSource': 'https://example.org/card.jpg', 'heldBy': 'third-party seller'}
    registry.record_linked_specimens([specimen], [], lambda *a, **kw: calls.append((a, kw)))
    assert {a[3] for a, _ in calls} == {'SPEC-standalone'}, 'no invented printing or unresolved foreign claim'
    assert {a[2] for a, _ in calls} == {'identity', 'finish'}
    assert all(a[4] == '2026-09-09' for a, _ in calls)
    assert specimen['citedBy'] == ['unresolved'], 'reference routing cannot admit a claim'
    calls.clear()
    specimen.pop('photographSource')
    specimen['inspectedFrom'] = 'product image'
    registry.record_linked_specimens([specimen], [], lambda *a, **kw: calls.append((a, kw)))
    assert calls, 'an empty context-reference list cannot swallow a typed physical observation'
    assert all(a[3] == 'SPEC-standalone' for a, _ in calls)
    assert registry.specimen_provider('https://snkrdunk.com/apparels/200/', 'Seller listing photograph') == 'snkrdunk'
    assert registry.specimen_provider('https://example.org/card.jpg', 'Seller listing photograph') == 'seller-listing-photo'
    assert registry.specimen_provider('https://rocketcoll.com/products/example', 'Seller listing photograph') == 'seller-listing-photo'


def verify_source_first_asset_authority(prints, evidence, registry):
    surfaces = registry.specimen_surfaces()
    for row in prints.values():
        calls = []
        registry.record_source_first_identity(row, lambda *a, **kw: calls.append(a), surfaces)
        for field in ('cardImageUrl', 'comparisonAssetUrl'):
            asset = row.get(field)
            if asset and registry.resolve_provider(asset, None) != row['providerId']:
                assert asset not in {call[0] for call in calls}, (row['printId'], field)
    # Photo-backed admissions must use the retained photo path, not count the
    # listing as a second identity source. Cover every current sibling admission.
    for row in prints.values():
        if row['providerId'] != 'seller-listing-photo':
            continue
        calls = []
        registry.record_source_first_identity(row, lambda *a, **kw: calls.append(a), surfaces)
        assert not calls, (row['printId'], 'listing duplicates retained photo identity')
        identities = [source for source in evidence
                      if row['printId'] in source.get('stableIds', [])
                      and row['specimenId'] in source.get('stableIds', [])
                      and source['providerId'] == 'seller-listing-photo'
                      and 'identity' in source['dimensions']]
        assert len(identities) == 1, (row['printId'], identities)
        assert row['specimenId'] in identities[0]['stableIds']
    try:
        registry.record_source_first_identity(
            {'providerId': 'seller-listing-photo', 'printId': 'missing-photo'},
            lambda *a, **kw: None, surfaces)
    except ValueError:
        pass
    else:
        raise AssertionError('photo admission without retained specimen must be rejected')
    # No specimen/earlier registry row exists to mask incorrect ownership in these cases.
    for provider, primary in (
        ('52poke', 'https://wiki.52poke.com/wiki/example'),
        ('bulbapedia', 'https://bulbapedia.bulbagarden.net/wiki/example'),
        ('pokemon-card-korea', 'https://pokemoncard.co.kr/cards/detail/example'),
    ):
        calls = []
        registry.record_source_first_identity({'providerId': provider, 'printId': 'sample',
            'sourceUrl': primary, 'cardImageUrl': 'https://media.pokipair.com/foreign.png',
            'comparisonAssetUrl': 'https://unknown.example/foreign.png'},
            lambda *a, **kw: calls.append((a, kw)), surfaces)
        assert [(a[0], kw['provider_id']) for a, kw in calls] == [(primary, provider)]
    actual = next(row for row in evidence if row.get('canonicalUrl') ==
        prints['CN:CS2aC:142/115:base']['cardImageUrl'])
    assert actual['providerId'] == 'retailer-listing'
    assert actual['dimensions'] == ['identity']
    assert 'SPEC-0475' in actual['stableIds']
    assert 'CN:CS2aC:142/115:base' in actual['stableIds']


def verify_retained_image_identity(specimens, evidence, registry):
    from urllib.parse import urlsplit
    urls = {row['canonicalUrl']: row for row in evidence if row['canonicalUrl']}
    for specimen in specimens:
        url = registry.provenance_url(specimen.get('photographSource'))
        if not url or not urlsplit(url).path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            continue
        row = urls.get(registry.canonical_url(url))
        if row and specimen['specimenId'] in row['stableIds']:
            assert 'identity' in row['dimensions'], (specimen['specimenId'], row['providerId'])
    surfaces = registry.specimen_surfaces()
    for provider in ('52poke', 'pokemon-official', 'pokemon-cn-official'):
        for surface in surfaces[provider]:
            if surface['surfaceId'] not in {'52poke-wiki', 'tpci-latam-spanish-card-assets',
                    'tpci-eu-spanish-card-assets', 'pokemon-cn-card-image'}:
                continue
            assert surface['finishCapability']['mode'] == 'none'
            for edge in surface['coverageEdges']:
                assert 'identity' in edge['positiveEvidenceCapabilities']
                assert edge['absenceCapability']['enabled'] is False
    specimen = next(row for row in specimens if row['specimenId'] == 'SPEC-0189')
    calls = []
    registry.record_specimen_sources(specimen, ['sample'], 'Inspected physical specimen photograph',
        {}, lambda *a, **kw: calls.append((a, kw)), surfaces)
    image_calls = [(a[2], kw['provider_id']) for a, kw in calls if a[0] == specimen['photographSource']]
    assert image_calls and set(image_calls) == {('identity', 'cardmarket-product-image')}
    page_calls = [a[2] for a, kw in calls if a[0] == specimen['listingUrl']]
    assert page_calls and set(page_calls) == {'product'}, 'product pages do not inherit image authority'


def verify_observed_finish_attribution(specimens, registry):
    from source_capabilities import route_evidence
    surfaces = registry.specimen_surfaces()
    for specimen in specimens:
        physical = specimen.get('physicalObservation') or {}
        if not physical.get('finish'):
            continue
        calls = []
        source_type = registry.SPECIMEN_SOURCE_TYPES.get(str(specimen.get('heldBy', '')).casefold(),
            specimen.get('inspectedFrom', 'Inspected physical specimen photograph'))
        registry.record_specimen_sources(specimen, ['sample'], source_type, physical,
            lambda *a, **kw: calls.append((a, kw)), surfaces)
        photo = registry.provenance_url(specimen.get('photographSource'))
        listing = registry.provenance_url(specimen.get('listingUrl'))
        if source_type == "Seller listing photograph" and photo and listing and photo != listing:
            context_claims = [a for a, kw in calls if a[0] == listing]
            assert all(a[2] == 'product' for a in context_claims), specimen['specimenId']
        finish = [(a, kw) for a, kw in calls if a[2] == 'finish']
        assert len(finish) == 2, 'one finish observation per specimen/claim, not one per context URL'
        if 'finish' in physical.get('ownerAttestedFields', []):
            assert all(a[0] is None and kw['provider_id'] == 'owner-attestation'
                       and a[4] == (physical.get('ownerAttestedAt') or specimen.get('recordedAt'))
                       for a, kw in finish)
            continue
        image = registry.provenance_url(specimen.get('photographSource')) or registry.provenance_url(specimen.get('listingUrl'))
        primary = [(a, kw) for a, kw in calls if a[0] == image and a[2] != 'finish']
        if not primary:
            continue
        provider = primary[0][1]['provider_id']
        surface = route_evidence({'canonicalUrl': image, 'providerId': provider}, surfaces)
        if surface['finishCapability']['mode'] == 'specimen-observation':
            assert all(a[0] == image and kw['provider_id'] == provider for a, kw in finish), specimen['specimenId']
    # Capabilities, not a provider-name allowlist, decide whether the URL can carry the observation.
    synthetic = {'new-photo-provider': [{'finishCapability': {'mode': 'specimen-observation'},
        'coverageEdges': [{'positiveEvidenceCapabilities': ['identity', 'finish']}]}]}
    calls = []
    registry.record_specimen_claim('https://example.org/card.jpg', 'Inspected physical specimen photograph',
        'new-photo-provider', 'identity', 'sample', '2026-09-09', {'finish': 'holo'},
        lambda *a, **kw: calls.append((a, kw)), synthetic)
    assert [(a[0], kw['provider_id']) for a, kw in calls if a[2] == 'finish'] == [
        ('https://example.org/card.jpg', 'new-photo-provider')]
    synthetic['new-photo-provider'][0]['finishCapability']['mode'] = 'product-subtype'
    assert not registry.surface_supports_observed_finish('https://example.org/card.jpg', 'new-photo-provider', synthetic)
    synthetic['new-photo-provider'][0]['finishCapability']['mode'] = 'specimen-observation'
    synthetic['new-photo-provider'][0]['coverageEdges'][0]['positiveEvidenceCapabilities'] = ['identity']
    assert not registry.surface_supports_observed_finish('https://example.org/card.jpg', 'new-photo-provider', synthetic)


def verify_standalone_printing_identity() -> None:
    graph = {"meta": {}, "entities": [{"entityType": "card-release", "entityId": "release",
             "payload": {"cardReleaseId": "release", "localSetCode": "TEST",
                         "localNumber": "1", "language": "Japanese"}}],
             "edges": [], "migrationDispositions": []}
    specimens = [{"specimenId": f"SPEC-{index:04d}", "setCode": "TEST", "number": "1",
                  "language": "Japanese", "recordedAt": "2026-09-28",
                  "physicalObservation": {"finish": finish, "basis": f"copy {index}"}}
                 for index, finish in enumerate(("holo", "holo", "non-holo"), 1)]
    inputs = {graph_module.UNITS: [], graph_module.FINISH_UNITS: {"units": []},
              ROOT / "verification/source_first_prints.json": {"prints": []},
              graph_module.SPECIMENS: {"specimens": specimens}}
    with patch.object(graph_module, "_read_json", side_effect=inputs.__getitem__):
        result = project_physical_evidence(deepcopy(graph))
        specimens.reverse()
        assert project_physical_evidence(deepcopy(graph)) == result
        assert project_physical_evidence(deepcopy(result)) == result
    physicals = [row["payload"] for row in result["entities"]
                 if row["entityType"] == "physical-printing"]
    assert len(physicals) == 2, "copies share a printing; different finishes stay separate"
    holo = next(row for row in physicals if row["finish"] == "holo")
    assert holo["specimenIds"] == ["SPEC-0001", "SPEC-0002"]
    assert any(row["fromId"] == "CLAIM:specimen:SPEC-0002" and row["relation"] == "provenance"
               and row["toId"] == holo["physicalPrintingId"] for row in result["edges"])


def verify_research_correction() -> None:
    sys.path.insert(0, str(ROOT / "verification/passes"))
    import integrate_rarity_finish_research_20261007 as correction
    names = ["authoritative_graph.json", "set_catalogue_sources.json", "source_first_prints.json", "legacy_issue_rekeys.json", "finish_overrides.json"]
    documents = [correction.read(name) for name in names]
    before = deepcopy(documents)
    correction.apply(documents)
    assert documents == before, "canonical correction replay must be unchanged"
    csvs = next(r for r in documents[2]["prints"] if r["printId"] == "CN:CSVSC:046/066:base")
    assert csvs["localNumber"] == "046/066" and csvs["specimenId"] == "SPEC-0631"
    assert csvs["releaseDate"] == "2026-01-16" and csvs["rarity"] == ["no printed rarity symbol", "fixed"]
    assert not any(r["printId"] == "CN:CSVS:046/066:base" for r in documents[2]["prints"])
    rarity_catalogue = correction.read("rarity_catalogue.json")
    csvsc_mapping = next(row for row in rarity_catalogue["sourceNativeMappings"]
                         if "RELEASE:CN:S-Chinese:CSVSC:046/066:Snorlax-Lazy-Press" in row.get("cardReleaseIds", []))
    assert csvsc_mapping["cardReleaseIds"] == ["RELEASE:CN:S-Chinese:CSVSC:046/066:Snorlax-Lazy-Press"]
    assert all(source in csvsc_mapping["basis"] for source in
               ("SPEC-0631", "Lucario", "https://www.pokemon.cn/tcg/product/15476.html",
                "verification/evidence/52poke-cn-local-identities-20261008")), "exact normalization needs its own reviewed basis"
    mappings = graph_module._rarity_native_mappings(rarity_catalogue)
    assert all(key[3] is not None for key in mappings
               if key[2] == "no printed rarity symbol"), "no generic symbol-to-Fixed mapping"
    claims = [row["payload"] for row in documents[0]["entities"]
              if row["entityType"] == "rarity-claim"
              and row["payload"].get("sourceNativeValue") == "no printed rarity symbol"]
    fixed = [row for row in claims if row.get("normalizedRarityId") == "fixed"]
    assert len(fixed) == 22, "retain 21 reviewed deck mappings plus the exact CSVSC deck card"
    cn_fixed = {row["cardReleaseId"] for row in fixed if row["cardReleaseId"].startswith("RELEASE:CN:")}
    expected_cn = {f"RELEASE:CN:S-Chinese:{code}:{number}:Snorlax-Heavy-Impact"
                   for code, number, *_ in correction.CN_DECK_RARITIES}
    expected_cn.add("RELEASE:CN:S-Chinese:CSVSC:046/066:Snorlax-Lazy-Press")
    assert cn_fixed == expected_cn, "only positively bound CN deck cards normalize to Fixed"
    assert not any("CSVH" in rid for rid in cn_fixed), "random modification packs are not Fixed"
    unresolved = [row for row in claims if row.get("normalizedRarityId") is None
                  and row["cardReleaseId"].split(":")[1] in ("ID", "KR", "TH")]
    assert len(unresolved) == 5, "five booster rarities remain native, not invented Fixed/Common"
    for row in unresolved:
        row["normalizedRarityId"] = "fixed"
    correction.apply(documents)
    assert documents == before, "repair every sibling booster, preserving unrelated stores"
    graph, catalogue, prints, rekeys, overrides = documents
    sm30a = next(row for row in prints["prints"] if row["printId"] == "KR:SM30A:060/080:base")
    assert sm30a["specimenId"] == "SPEC-0627", "retain the exact publisher image through admission replay"
    for code, number, specimen, *_ in correction.CN_DECK_RARITIES:
        print_row = next(row for row in prints["prints"] if row["printId"] == f"CN:{code}:{number}:base")
        assert print_row["rarity"] == ["no printed rarity symbol", "fixed"]
        assert print_row["specimenId"] == specimen
        assert print_row["rarityRetrievedAt"] == "2026-10-07"
        assert print_row["releaseDate"] == ("2023-11-17" if code == "CS2DaC" else "2024-05-17")
    xy2 = next(row for row in prints["prints"] if row["printId"] == "KR:XY2:066/080:base")
    assert xy2["releaseDate"] == "2014-05-01"
    assert xy2["releaseDateRetrievedAt"] == "2026-10-07"
    assert xy2["releaseDateSourceUrl"] == "https://pokemoncard.co.kr/card/33"
    bs2 = next(row for row in prints["prints"] if row["printId"] == "KR:BS2:30/40:base")
    assert bs2["releaseDate"] == "2010-06-17"
    assert bs2["releaseDateProviderId"] == "bulbapedia"
    assert bs2["releaseDateRetrievedAt"] == "2026-10-08"
    event = next(row["payload"] for row in graph["entities"]
                 if row["entityType"] == "release-event"
                 and row["entityId"] == "EVENT:KR:BS2:launch-2010-06-17")
    source = next(row for row in catalogue["sourceRecords"]
                  if row["sourceRecordId"] == event["sourceRecordId"])
    assert source["provider"] == "bulbapedia"
    assert source["sourceUrl"] == bs2["releaseDateSourceUrl"]
    assert event["marketScopes"] == ["KR"]
    xy10 = next(row for row in prints["prints"] if row["printId"] == "KR:XY10:057/078:base")
    assert xy10["releaseDate"] == "2016-03-24"
    assert xy10["releaseDateProviderId"] == "pokemon-card-korea"
    assert xy10["releaseDateRetrievedAt"] == "2026-10-08"
    assert xy10["releaseDateSourceUrl"] == "https://pokemoncard.co.kr/card/65"
    date_record = next(row for row in catalogue["sourceRecords"]
                       if row["sourceRecordId"] == xy10["releaseDateSourceRecordId"])
    assert date_record["raw"]["conflictingHeaderDate"] == "2016-03-01"
    assert date_record["raw"]["assertionDate"] == "2017-03-29"
    assert date_record["raw"]["corroboratingAnnouncement"]["publishedAt"].startswith("2016-03-11")
    assert date_record["raw"]["corroboratingAnnouncement"]["ownStockArrivalDate"] == "explicitly unknown"
    dp006 = next(row for row in prints["prints"] if row["printId"] == "KR:DP:006:base")
    assert dp006["releaseDate"] == "2010-08-26"
    assert dp006["releaseDateProviderId"] == "52poke"
    dp_source = next(row for row in catalogue["sourceRecords"] if row["sourceRecordId"] == dp006["releaseDateSourceRecordId"])
    assert dp_source["raw"]["note"] == "Exact named promo only; not the whole promo sequence."
    assert not any(row["entityType"] == "release-event" and row["entityId"] == "EVENT:KR:DP:launch-2010-08-26" for row in graph["entities"])
    twenty = next(row for row in prints["prints"] if row["printId"] == "KR:20th:047/071:base")
    assert twenty["localNumber"] == "047/071" and twenty["specimenId"] == "SPEC-0629"
    assert twenty["releaseDate"] == "2016-02-27" and twenty["releaseDateProviderId"] == "pokemon-card-korea"
    date_source = next(row for row in catalogue["sourceRecords"] if row["sourceRecordId"] == twenty["releaseDateSourceRecordId"])
    assert date_source["raw"]["conflictingHeaderDate"] == "2016-02-01"
    assert not any(row["printId"] in {"KR:20th:047/072:base", "KR:20th:047/077:base"} for row in prints["prints"])
    twenty_profile = next(row for row in catalogue["sourceRecords"] if row["sourceRecordId"] == "SET-SRC-SF-443327CEB86E")
    assert twenty_profile["raw"]["printedSetSize"] == 71
    assert twenty_profile["raw"]["observedCollectorNumbers"] == ["047/071"]
    # The bounded CN helper cannot alter finishes, aliases or unrelated source-first rows.
    bounded_before = deepcopy(documents)
    correction.admit_cn_followup(graph, catalogue, prints)
    assert documents == bounded_before
    import admit_issue257_simplified_chinese_20260827 as cn_admission
    replay_prints = deepcopy(prints)
    cn_admission.apply_source_first_prints(replay_prints)
    correction.admit_cn_followup(graph, catalogue, replay_prints)
    assert replay_prints == prints, "CN identity admission preserves SPEC, image followrefs and later fields"
    replay_graph, replay_catalogue = deepcopy(graph), deepcopy(catalogue)
    profiles = cn_admission.apply_set_sources(replay_catalogue)
    replay_graph = cn_admission.apply_graph(replay_graph, profiles)
    correction.admit_cn_followup(replay_graph, replay_catalogue, replay_prints)
    for entity_type in ("rarity-claim", "card-release"):
        scoped = lambda document: {e["entityId"]: e["payload"] for e in document["entities"]
                                    if e["entityType"] == entity_type
                                    and (e["payload"].get("cardReleaseId") in expected_cn)}
        assert scoped(replay_graph) == scoped(graph), "CN graph replay retains follow-up fields"
    for code in ("CS2DaC", "CS4DaC"):
        get_profile = lambda document: next(row for row in document["sourceRecords"]
                         if row["sourceKind"] == "source-first-local-set-profile"
                         and row["raw"]["localCode"] == code)
        assert get_profile(replay_catalogue) == get_profile(catalogue)
    assert overrides == bounded_before[-1], "CN replay cannot infer or alter finishes"
    classic = next(row for row in prints["prints"] if row["printId"] == "KR:CLF:016/032:base")
    assert classic["specimenId"] == "SPEC-0616" and classic["retrievedAt"] == "2026-10-07"
    assert not any("KR:CLF:016/034" in row["printId"] for row in prints["prints"])
    keys = {(row["setCode"], row["number"]): row for row in overrides["overrides"]}
    assert ("CSVH1C", "a001") not in keys and ("CSVH4C", "a003") not in keys
    reward = keys[("CSVH4C", "p006")]["printings"]
    assert len(reward) == 1 and reward[0]["finish"] == "holo"
    assert reward[0]["distribution"]["kind"] == "special-pack"
    assert not any(row["payload"].get("localSetCode") == "SM-P"
                   for row in graph["entities"] if row["entityType"] == "release-event")


def main() -> None:
    verify_research_correction()
    verify_standalone_printing_identity()
    # A retained legacy specimen may follow its reviewed local re-key, but not a neighbour.
    specimen = {"setCode": "s5a", "number": "93/070", "language": "Indonesian", "citedBy": ["U0603"]}
    release = {"localSetCode": "s5a I", "localNumber": "093/070", "language": "Indonesian",
               "legacyIdentityAliases": [["s5a", "93"]], "legacyCounterpartUnitIds": ["U0603"]}
    units_by_id = {"U0603": {**specimen, "number": "93"}}
    assert graph_module._specimen_has_cited_legacy_identity(specimen, release, units_by_id)
    for changed in ({"language": "Thai"}, {"number": "94/070"}, {"citedBy": ["U0602"]}, {"setCode": "s4"}):
        assert not graph_module._specimen_has_cited_legacy_identity({**specimen, **changed}, release, units_by_id)
    assert not graph_module._specimen_has_cited_legacy_identity(specimen, {**release, "legacyIdentityAliases": []}, units_by_id)
    # An alias and a citation on the same coalesced release must belong together.
    merged = {**release, "legacyIdentityAliases": [["s5a", "93"], ["xs5a", "93"]], "legacyCounterpartUnitIds": ["U0603", "neighbour"]}
    units_by_id["neighbour"] = {**specimen, "setCode": "xs5a"}
    assert not graph_module._specimen_has_cited_legacy_identity({**specimen, "citedBy": ["neighbour"]}, merged, units_by_id)
    assert graph_module._specimen_has_cited_legacy_identity({**specimen, "setCode": "xs5a", "citedBy": ["neighbour"]}, merged, units_by_id)
    graph = json.loads((ROOT / "verification/authoritative_graph.json").read_text(encoding="utf-8"))
    assert not validate(graph)
    assert not validate(issue263_rebuilt_graph())
    import admit_issue263_s5af_20260909 as s5af_pass
    repaired = deepcopy(graph)
    s5af_pass.reproject_prior_products(repaired)
    assert repaired == graph, "committed product references must include all reviewed TW rekeys"
    product_refs = lambda g: {e["entityId"]: e["payload"]["cardReleaseIds"] for e in g["entities"]
                              if e["entityType"] == "legacy-cardmarket-product"}
    assert product_refs(graph) == product_refs(issue263_rebuilt_graph())
    s5af_id = "RELEASE:TW:T-Chinese:s5a F:093/070:Snorlax-Gormandize-Body-Slam"
    for current in (graph, issue263_rebuilt_graph()):
        release = next(e["payload"] for e in current["entities"] if e["entityType"] == "card-release" and e["entityId"] == s5af_id)
        assert release["localIdentifierKnown"] and release["localNumber"] == "093/070"
        assert release["releaseDate"] == "2021-04-02"
        rarity = next(e["payload"] for e in current["entities"]
                      if e["entityType"] == "rarity-claim"
                      and e["entityId"] == "RARITYCLAIM:issue263:s5a F:093/070:Snorlax-Gormandize-Body-Slam")
        assert rarity["retrievedAt"] == "2026-09-09"
        assert rarity["sourceNativeValue"] == "UR"
        assert "U0602" in release["legacyCounterpartUnitIds"]
        local_set = next(e["payload"] for e in current["entities"] if e["entityId"] == "LOCALSET:TW:s5a%20F")
        assert "雙璧戰士" in local_set["observedNames"]
        product = next(e["payload"] for e in current["entities"] if e["entityType"] == "legacy-cardmarket-product" and e["payload"]["sourceId"].endswith("/Matchless-Fighter/Snorlax-s5a93"))
        assert s5af_id in product["cardReleaseIds"]
        assert len(product["cardReleaseIds"]) == 5
        assert not any(":TW:T-Chinese:via-s5a:" in ref for ref in product["cardReleaseIds"])
        assert not any(e["entityType"] == "card-release" and ":via-s5a:" in e["entityId"] and e["payload"].get("language") == "T-Chinese" for e in current["entities"])
    specimen = next(r for r in json.loads((ROOT / "verification/specimens.json").read_text(encoding="utf-8"))["specimens"] if r["specimenId"] == "SPEC-0489")
    assert specimen["physicalObservation"]["finish"] == "holo"
    flat_render = next(r for r in json.loads((ROOT / "verification/specimens.json").read_text(encoding="utf-8"))["specimens"] if r["specimenId"] == "SPEC-0294")
    # A publisher render cannot establish finish; an explicit owner determination can.
    physical = flat_render.get("physicalObservation", {})
    assert not physical or (
        physical.get("ownerAttestedFields") == ["finish"]
        and physical.get("ownerAttestedAt")
        and physical.get("basis")
    )
    for uid, code, number in [("U0051", "SV2a I", "181/165"), ("U0603", "s5a I", "093/070"), ("U0171", "s10a T", "077/071")]:
        claim = next(e["payload"] for e in graph["entities"] if e["entityType"] == "candidate-claim" and e["payload"].get("sourceId") == uid)
        release = next(e["payload"] for e in graph["entities"] if e["entityType"] == "card-release" and e["entityId"] == claim["materializedTargetId"])
        assert (release["localSetCode"], release["localNumber"]) == (code, number)
        assert uid in release["legacyCounterpartUnitIds"]

    tampered = deepcopy(graph)
    next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "rarity-claim"
        and row["payload"].get("normalizedRarityId")
    )["normalizedRarityId"] = "unknown"
    assert any(
        "rarity claim normalized id is not in the catalogue" in error
        for error in validate(tampered)
    )
    tampered = deepcopy(graph)
    next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "rarity-claim"
        and row["payload"].get("sourceNativeValue") == "RRR"
    )["normalizedRarityId"] = "common"
    assert any(
        "rarity claim normalized id does not match source-native mapping" in error
        for error in validate(tampered)
    )
    tampered = deepcopy(graph)
    next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "rarity-claim"
        and row["payload"].get("sourceNativeValue") == "HR"
    )["normalizedRarityId"] = "hyper-rare"
    assert any(
        "rarity claim normalized id does not match source-native mapping" in error
        for error in validate(tampered)
    )
    tampered = deepcopy(graph)
    next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "rarity-claim"
        and row["payload"].get("sourceVocabulary") == "printed-Korean-card"
        and row["payload"].get("sourceNativeValue") == "R"
    )["normalizedRarityId"] = None
    assert any(
        "rarity claim normalized id does not match source-native mapping" in error
        for error in validate(tampered)
    )
    tampered = deepcopy(graph)
    next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "rarity-claim"
        and row["payload"].get("sourceVocabulary") == "printed-Korean-card"
        and row["payload"].get("sourceNativeValue") == "UR"
    )["normalizedRarityId"] = "ultra-rare"
    assert any(
        "rarity claim normalized id does not match source-native mapping" in error
        for error in validate(tampered)
    )
    # Updating a Korean release to an official identity page must not rewrite
    # the source that supplied an already-reviewed rarity value.
    korean_rarity = next(
        row["payload"] for row in graph["entities"]
        if row["entityId"]
        == "RARITYCLAIM:issue260:m3:062/080:Snorlax-Gormandizer-Collapse"
    )
    assert korean_rarity["sourceProductKey"] == (
        "https://collectory.cc/cards/b6401ed6-1c9a-4703-9b55-762ac6e6d33e"
    )
    assert korean_rarity["retrievedAt"] == "2026-08-30"
    korean_profile = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "set-source-record"
        and row["entityId"] == korean_rarity["sourceRecordId"]
    )
    assert korean_rarity["sourceProductKey"] in korean_profile["raw"]["sourceUrls"]
    source_first_rows = {
        row["printId"]: row for row in json.loads(
            (ROOT / "verification/source_first_prints.json").read_text(encoding="utf-8")
        )["prints"]
    }
    unmatched_korean = {
        "KR:s1H:070/060:base", "KR:sm9:115/095:base",
        "KR:s5a:093/070:base",
        "KR:xsv2a:143/165:base", "KR:xm2a:136/193:base",
    }
    assert {
        print_id: source_first_rows[print_id]["retrievedAt"]
        for print_id in unmatched_korean
    } == {print_id: "2026-08-30" for print_id in unmatched_korean}
    official_korean = {
        row["printId"] for row in json.loads(
            (
                ROOT
                / "verification/evidence/pokemon-korea-snorlax-catalogue-20260901.json"
            ).read_text(encoding="utf-8")
        )["identities"]
    }
    assert len(official_korean) == 45
    bs2_print_id = "KR:BS2:30/40:base"
    bs2_profile = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "set-source-record"
        and row["payload"].get("raw", {}).get("printIds") == [bs2_print_id]
    )
    assert bs2_profile["retrieved"] == "2026-09-01"
    assert bs2_profile["raw"]["retrievedByPrintId"] == {
        bs2_print_id: "2026-09-01"
    }
    assert bs2_profile["raw"]["evidenceSnapshot"] == korean_catalogue_pass.SNAPSHOT
    assert bs2_profile["raw"]["workEvidenceSnapshot"] == bs2_work_pass.SNAPSHOT
    assert set(source_first_rows[bs2_print_id]["corroboratingSourceUrls"]) < set(
        bs2_profile["raw"]["sourceUrls"]
    )
    assert source_first_rows[bs2_print_id]["cardImageUrl"] in (
        bs2_profile["raw"]["cardImageUrls"]
    )
    bs2_claim = next(
        row["payload"] for row in graph["entities"]
        if row["entityId"] == f"CLAIM:source-first:{bs2_print_id}"
    )
    assert bs2_claim["sourceRecord"] == source_first_rows[bs2_print_id]["sourceUrl"]
    assert bs2_claim["retrievedAt"] == "2026-09-01"
    bs2_release = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "card-release"
        and bs2_print_id in row["payload"].get("sourceFirstRecordIds", [])
    )
    assert bs2_release["work"] == "Snorlax-Lv35-Block-Ease-Up"
    assert bs2_release["workMappingState"] == "mapped"
    assert bs2_release["cardReleaseId"] == (
        "RELEASE:KR:Korean:BS2:30/40:Snorlax-Lv35-Block-Ease-Up"
    )
    catalogue_identities = {
        row["printId"]: row for row in json.loads(
            korean_catalogue_pass.EVIDENCE.read_text(encoding="utf-8")
        )["identities"]
    }
    catalogue_rows = deepcopy(
        korean_catalogue_pass.base.OFFICIAL
        + korean_catalogue_pass.base.PROMOS
        + korean_catalogue_pass.research.RESEARCH_ROWS
        + korean_catalogue_pass.new_rows()
    )
    for row in catalogue_rows:
        row.setdefault("legacyVariants", sorted({
            str(korean_catalogue_pass.research.UNITS_BY_ID[item].get("variant") or "base")
            for item in row["legacy"]
        }))
    korean_catalogue_pass.apply_official_rows(catalogue_rows, catalogue_identities)
    projected_prints = korean_catalogue_pass.read(korean_catalogue_pass.PRINTS)
    korean_catalogue_pass.apply_prints(
        projected_prints, catalogue_rows, catalogue_identities
    )
    catalogue_rows = korean_catalogue_pass.projection_rows(
        catalogue_rows, projected_prints, graph, catalogue_identities
    )
    assert len(catalogue_rows) == 52
    assert {row["printId"] for row in catalogue_rows} == (
        official_korean | unmatched_korean | {"KR:CLF:016/032:base", "KR:20th:047/072:base"}
    )
    assert {
        row["printId"] for row in catalogue_rows if not row.get("work")
    } == set()
    assert all(
        all(row.get(field) for field in (
            "raritySourceUrl", "rarityProviderId", "rarityRetrievedAt"
        ))
        for row in catalogue_rows if row.get("rarity") is not None
    )
    unsupported_rarity_prints = {
        "KR:m2a:136/193:base",
        "KR:xsv2a:143/165:base",
        "KR:xm2a:136/193:base",
    }
    assert all(
        row.get("rarity") is None
        for row in catalogue_rows if row["printId"] in unsupported_rarity_prints
    )
    assert not any(
        entity["entityType"] == "rarity-claim"
        and entity["payload"].get("cardReleaseId")
        == korean_catalogue_pass.base.release_id(row)
        for row in catalogue_rows if row["printId"] in unsupported_rarity_prints
        for entity in graph["entities"]
    )
    fxy_row = next(row for row in catalogue_rows if row["printId"] == "KR:FXY:026/036:base")
    assert fxy_row["corroboratingSourceUrls"] == [
        "https://bulbapedia.bulbagarden.net/wiki/Kalos_Starter_Set_(TCG)"
    ]
    assert fxy_row["corroborated"] is True
    assert fxy_row["rarity"] == ("fixed product", "fixed")
    assert fxy_row["raritySourceUrl"] == (
        "https://bulbapedia.bulbagarden.net/wiki/Kalos_Starter_Set_(TCG)"
    )
    assert fxy_row["rarityRetrievedAt"] == "2026-08-10"
    sm30a_row = next(
        row for row in catalogue_rows if row["printId"] == "KR:SM30A:060/080:base"
    )
    assert sm30a_row["rarity"] == ("fixed product", "fixed")
    assert sm30a_row["raritySourceUrl"] == (
        "https://pokemoncard.co.kr/card/277"
    )
    assert sm30a_row["raritySupportingSourceUrls"] == [
        "https://pokemoncard.co.kr/cards/detail/BS2019018060",
        "https://pokemoncard.co.kr/cards?s=%EB%A6%AC%EC%9E%90%EB%AA%BD%20GX%2030%EC%9E%A5%EB%8D%B1",
    ]
    assert sm30a_row["rarityRetrievedAt"] == "2026-09-01"
    fixed_product_observations = {
        row["printId"]: row for row in json.loads(
            korean_catalogue_pass.EVIDENCE.read_text(encoding="utf-8")
        )["fixedProductObservations"]
    }
    assert fixed_product_observations[sm30a_row["printId"]]["sourceUrl"] == (
        sm30a_row["raritySourceUrl"]
    )
    assert fixed_product_observations[sm30a_row["printId"]]["supportingSourceUrls"] == (
        sm30a_row["raritySupportingSourceUrls"]
    )
    assert source_first_rows[fxy_row["printId"]]["corroboratingSourceUrls"] == (
        fxy_row["corroboratingSourceUrls"]
    )
    units = {
        row["unitId"]: row for row in json.loads(
            (ROOT / "verification/units.json").read_text(encoding="utf-8")
        )
    }
    assert "대지의 그릇" not in units["U0260"]["evidence"]
    assert "잠만보인형 060/066" in units["U0260"]["evidence"]
    assert units["U0586"]["corroborated"] is True
    rarity_provenance = {
        row["printId"]: (
            row.get("raritySourceUrl", row["sourceUrl"]),
            row.get("rarityRetrievedAt", row["retrievedAt"]),
        )
        for row in catalogue_rows
        if row["printId"] in official_korean and row.get("rarity") is not None
    }
    fixed_product_rarities = {
        "KR:FXY:026/036:base",
        "KR:SM30A:060/080:base",
    }
    assert fixed_product_rarities.issubset(rarity_provenance)
    capabilities = korean_catalogue_pass.read(korean_catalogue_pass.CAPABILITIES)
    korean_catalogue_pass.apply_capabilities(
        capabilities, korean_catalogue_pass.read(korean_catalogue_pass.EVIDENCE),
        catalogue_rows,
    )
    korea_edge = next(
        edge for surface in capabilities["surfaces"]
        if surface["surfaceId"] == "pokemon-card-korea-card-search"
        for edge in surface["coverageEdges"]
    )
    assert "rarity" not in korea_edge["positiveEvidenceCapabilities"]
    exact_rarity_surface = next(
        surface for surface in capabilities["surfaces"]
        if surface["surfaceId"] == "pokemon-card-korea-retained-rarity-details"
    )
    assert "rarity" in exact_rarity_surface["coverageEdges"][0][
        "positiveEvidenceCapabilities"
    ]
    assert set(exact_rarity_surface["match"]["urlPrefixes"]) == {
        row["raritySourceUrl"] for row in catalogue_rows
        if row.get("rarityProviderId") == "pokemon-card-korea"
        and row["raritySourceUrl"].startswith(
            "https://pokemoncard.co.kr/cards/detail/"
        )
    }
    for row in catalogue_rows:
        if row.get("rarity") is not None:
            # This historical replay predates the exact Korean /071 scan.
            current_id = {"KR:20th:047/072:base": "KR:20th:047/071:base"}.get(row["printId"], row["printId"])
            persisted = source_first_rows[current_id]
            assert persisted["raritySourceUrl"] == row["raritySourceUrl"]
            assert persisted["rarityProviderId"] == row["rarityProviderId"]
            assert persisted["rarityRetrievedAt"] == row["rarityRetrievedAt"]
        if row["printId"] not in official_korean:
            continue
        if row.get("rarity") is not None:
            source_url, retrieved_at = rarity_provenance[row["printId"]]
            assert row["raritySourceUrl"] == source_url
            assert row["rarityRetrievedAt"] == retrieved_at
            rarity_id = (
                "RARITYCLAIM:issue260:"
                + korean_catalogue_pass.base.release_id(row).removeprefix(
                    "RELEASE:KR:Korean:"
                )
            )
            rarity_claim = next(
                entity["payload"] for entity in graph["entities"]
                if entity["entityId"] == rarity_id
            )
            assert rarity_claim["sourceProductKey"] == source_url
            assert rarity_claim["retrievedAt"] == retrieved_at
            if row.get("raritySupportingSourceUrls"):
                assert rarity_claim["supportingSourceUrls"] == row["raritySupportingSourceUrls"]
                source_profile = next(
                    entity["payload"] for entity in graph["entities"]
                    if entity["entityType"] == "set-source-record"
                    and entity["entityId"] == rarity_claim["sourceRecordId"]
                )
                assert set(row["raritySupportingSourceUrls"]) < set(
                    source_profile["raw"]["sourceUrls"]
                )
        profile = next(
            entity["payload"] for entity in graph["entities"]
            if entity["entityType"] == "set-source-record"
            and row["printId"] in entity["payload"].get("raw", {}).get("printIds", [])
        )
        assert profile["raw"]["retrievedByPrintId"][row["printId"]] == (
            row["retrievedAt"]
        )
        assert row["sourceUrl"] in profile["raw"]["sourceUrls"]
        if row.get("cardImageUrl"):
            assert row["cardImageUrl"] in profile["raw"]["cardImageUrls"]
        candidate = next(
            entity["payload"] for entity in graph["entities"]
            if entity["entityId"] == f"CLAIM:source-first:{row['printId']}"
        )
        assert candidate["sourceRecord"] == row["sourceUrl"]
        assert candidate["retrievedAt"] == row["retrievedAt"]
        release = next(
            entity["payload"] for entity in graph["entities"]
            if entity["entityType"] == "card-release"
            and row["printId"] in entity["payload"].get("sourceFirstRecordIds", [])
        )
        assert row["sourceUrl"] in release["sourceRecords"]
    verify_source_first_specimen_registry()
    verify_30th_admission_replay()
    verify_kss_retirement_replay()
    verify_release_count_reason_guard(graph)
    source_registry = {
        row["canonicalUrl"]: row for row in json.loads(
            (ROOT / "verification/source_registry.json").read_text(encoding="utf-8")
        )["evidence"] if row.get("canonicalUrl")
    }
    fxy_rarity_url = fxy_row["raritySourceUrl"]
    from source_registry import canonical_url
    from urllib.parse import urlsplit
    for row in issue263_pass.read(issue263_pass.PRINTS)["prints"]:
        if row.get("providerId") == "52poke":
            for url in {row.get("sourceUrl"), row.get("cardImageUrl"), row.get("comparisonAssetUrl")} - {None}:
                if not urlsplit(url).hostname.endswith(".52poke.com"):
                    assert source_registry.get(canonical_url(url), {}).get("providerId") != "52poke"
                    continue
                evidence = source_registry[canonical_url(url)]
                assert evidence["providerId"] == "52poke"
                if row.get("retrievedAt"):
                    assert evidence["retrievedAt"] >= row["retrievedAt"]
                assert row["printId"] in evidence["stableIds"]
                assert "card-release" in evidence["dimensions"]
    assert source_registry[fxy_rarity_url]["providerId"] == "bulbapedia"
    assert "rarity" in source_registry[fxy_rarity_url]["dimensions"]
    assert fxy_row["printId"] in source_registry[fxy_rarity_url]["stableIds"]
    product_url = sm30a_row["raritySourceUrl"]
    detail_url, membership_url = sm30a_row["raritySupportingSourceUrls"]
    assert source_registry[product_url]["providerId"] == "pokemon-card-korea"
    assert {"rarity", "date", "finish"} <= set(source_registry[product_url]["dimensions"])
    assert sm30a_row["printId"] in source_registry[product_url]["stableIds"]
    assert "set-membership" in source_registry[detail_url]["dimensions"]
    assert source_registry[membership_url]["dimensions"] == ["set-membership"]
    capability_resolution = {
        row["sourceKey"]: row for row in json.loads(
            (ROOT / "verification/source_capability_graph.json").read_text(encoding="utf-8")
        )["sourceResolution"]
    }
    assert capability_resolution[fxy_rarity_url]["surfaceId"] == (
        "bulbapedia-mediawiki"
    )
    assert "rarity" in capability_resolution[fxy_rarity_url]["dimensions"]
    assert capability_resolution[product_url]["surfaceId"] == (
        "pokemon-card-korea-fixed-product"
    )
    assert capability_resolution[membership_url]["surfaceId"] == (
        "pokemon-card-korea-fixed-product"
    )
    assert capability_resolution[detail_url]["surfaceId"] == (
        "pokemon-card-korea-card-search"
    )
    assert "rarity" not in capability_resolution[detail_url]["dimensions"]
    assert {
        print_id: source_first_rows[print_id]["retrievedAt"]
        for print_id in official_korean
    } == {print_id: "2026-09-01" for print_id in official_korean}
    mixed_profile = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "set-source-record"
        and row["payload"].get("providerRecordKey") == "KR\x1fs1H"
    )
    assert mixed_profile["retrieved"] == "2026-09-01"
    assert mixed_profile["raw"]["retrievedByPrintId"] == {
        "KR:s1H:045/060:base": "2026-09-01",
        "KR:s1H:046/060:base": "2026-09-01",
        "KR:s1H:066/060:base": "2026-09-01",
        "KR:s1H:070/060:base": "2026-08-30",
    }
    unmatched_rarity = next(
        row["payload"] for row in graph["entities"]
        if row["entityId"]
        == "RARITYCLAIM:issue260:s1H:070/060:Snorlax-VMAX-G-Max-Fall"
    )
    assert unmatched_rarity["retrievedAt"] == "2026-08-30"
    same_work_assertions = [
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "equivalence-assertion"
        and row["payload"].get("sourceFirstRecordId") in official_korean | unmatched_korean | {"KR:CLF:016/032:base", "KR:20th:047/071:base"}
    ]
    unmatched_assertions = [
        row for row in same_work_assertions
        if row["sourceFirstRecordId"] in unmatched_korean
    ]
    official_assertions = [
        row for row in same_work_assertions
        if row["sourceFirstRecordId"] in official_korean
    ]
    assert {row["sourceFirstRecordId"] for row in unmatched_assertions} == unmatched_korean
    assert {row["assertedAt"] for row in unmatched_assertions} == {"2026-08-30"}
    assert official_assertions
    assert {row["assertedAt"] for row in official_assertions} == {"2026-09-01"}
    assert graph_module._number("058/071") == graph_module._number("58")
    assert graph_module.specimen_markings({
        "markings": "EDIZIONE 1", "markingRole": "print-identity"
    }) == [{"kind": "edition-stamp", "role": "print-identity", "text": "EDIZIONE 1"}]
    assert graph_module.specimen_observation_field_matches(
        {}, {"cardSize": "standard"}, "cardSize"
    )
    assert not graph_module.specimen_observation_field_matches(
        {"cardSize": "jumbo"}, {"cardSize": "standard"}, "cardSize"
    )
    repaired_releases = [
        row["payload"] for row in graph["entities"] if row["entityType"] == "card-release"
    ]
    assert all(
        row["workMappingState"] in graph_module.WORK_MAPPING_STATES
        and (
            row["workMappingState"] in graph_module.WORK_REQUIRED_STATES
            and isinstance(row.get("work"), str)
            or row["workMappingState"] in graph_module.WORK_EMPTY_STATES
            and row.get("work") is None
        )
        for row in repaired_releases
    )
    tampered = deepcopy(graph)
    mapped_release = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "card-release" and row["payload"]["workMappingState"] == "mapped"
    )
    mapped_release["work"] = None
    assert any("mapped card release has no Work relation" in error for error in validate(tampered))
    tampered = deepcopy(graph)
    mapped_release = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "card-release" and row["payload"]["workMappingState"] == "mapped"
    )
    mapped_release["workMappingState"] = "needs-explicit-equivalence"
    assert any("unmapped card release carries a Work relation" in error for error in validate(tampered))
    tampered = deepcopy(graph)
    next(row["payload"] for row in tampered["entities"] if row["entityType"] == "card-release")[
        "workMappingState"
    ] = "future-state"
    assert any("unknown work mapping state" in error for error in validate(tampered))
    tampered = deepcopy(graph)
    mapped_release_id = next(
        row["entityId"] for row in tampered["entities"]
        if row["entityType"] == "card-release" and row["payload"]["workMappingState"] == "mapped"
    )
    implements_edge = next(
        edge for edge in tampered["edges"]
        if edge["fromType"] == "card-release"
        and edge["fromId"] == mapped_release_id
        and edge["relation"] == "implements"
    )
    other_work_id = next(
        row["entityId"] for row in tampered["entities"]
        if row["entityType"] == "work" and row["entityId"] != implements_edge["toId"]
    )
    implements_edge["toId"] = other_work_id
    assert any("implements edge is missing or inconsistent" in error for error in validate(tampered))
    tampered = deepcopy(graph)
    empty_release = next(
        row for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["payload"]["workMappingState"] == "mapped"
    )
    empty_release["payload"]["workMappingState"] = "unmapped"
    empty_release["payload"]["work"] = None
    assert any("unmapped card release has an implements edge" in error for error in validate(tampered))
    # Work entity IDs are the stable relation targets.  Swapping only the
    # payload workId values (and retargeting release edges to those values)
    # must fail instead of silently changing collector identity grouping.
    tampered = deepcopy(graph)
    work_rows = [row for row in tampered["entities"] if row["entityType"] == "work"][:2]
    first_work_id, second_work_id = (row["entityId"] for row in work_rows)
    first_work, second_work = (row["payload"] for row in work_rows)
    first_work["workId"], second_work["workId"] = second_work_id, first_work_id
    for release_row in tampered["entities"]:
        if release_row["entityType"] != "card-release":
            continue
        work_key = release_row["payload"].get("work")
        target_id = second_work_id if work_key == first_work["cardKey"] else (
            first_work_id if work_key == second_work["cardKey"] else None
        )
        if target_id is None:
            continue
        for edge in tampered["edges"]:
            if (
                edge["fromType"] == "card-release"
                and edge["fromId"] == release_row["entityId"]
                and edge["relation"] == "implements"
            ):
                edge["toId"] = target_id
    assert any("work payload id mismatch" in error for error in validate(tampered))
    # An explicit-equivalence mapping is only promotable with at least one
    # reviewed assertion that names both the exact release and Work relation.
    tampered = deepcopy(graph)
    equivalence_release = next(
        row for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["payload"]["workMappingState"] == "mapped-by-explicit-equivalence"
    )
    assertion_ids = {
        edge["fromId"] for edge in tampered["edges"]
        if edge["fromType"] == "equivalence-assertion"
        and edge["relation"] == "relates"
        and edge["toType"] == "card-release"
        and edge["toId"] == equivalence_release["entityId"]
    }
    tampered["entities"] = [
        row for row in tampered["entities"] if not (
            row["entityType"] == "equivalence-assertion"
            and row["entityId"] in assertion_ids
        )
    ]
    tampered["edges"] = [
        edge for edge in tampered["edges"]
        if not (edge["fromType"] == "equivalence-assertion" and edge["fromId"] in assertion_ids)
    ]
    assert any(
        "mapped-by-explicit-equivalence card release lacks a matching equivalence assertion"
        in error for error in validate(tampered)
    )
    # Retargeting the release, implements edge, assertion payload and
    # assertion relation together must still fail against the legacy unit's
    # independently reviewed cardKey.
    tampered = deepcopy(graph)
    equivalence_release = next(
        row for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["payload"]["workMappingState"] == "mapped-by-explicit-equivalence"
    )
    assertion_id = next(
        edge["fromId"] for edge in tampered["edges"]
        if edge["fromType"] == "equivalence-assertion"
        and edge["relation"] == "relates"
        and edge["toType"] == "card-release"
        and edge["toId"] == equivalence_release["entityId"]
    )
    alternate_work = next(
        row for row in tampered["entities"]
        if row["entityType"] == "work"
        and row["entityId"] != next(
            edge["toId"] for edge in tampered["edges"]
            if edge["fromType"] == "card-release"
            and edge["fromId"] == equivalence_release["entityId"]
            and edge["relation"] == "implements"
        )
    )
    equivalence_release["payload"]["work"] = alternate_work["payload"]["cardKey"]
    for edge in tampered["edges"]:
        if edge["fromType"] == "card-release" and edge["fromId"] == equivalence_release["entityId"] \
                and edge["relation"] == "implements":
            edge["toId"] = alternate_work["entityId"]
        if edge["fromType"] == "equivalence-assertion" and edge["fromId"] == assertion_id:
            if edge["toType"] == "work":
                edge["toId"] = alternate_work["entityId"]
    assertion = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "equivalence-assertion" and row["entityId"] == assertion_id
    )
    assertion["toId"] = alternate_work["entityId"]
    assert any(
        "re-key equivalence assertion is stale" in error
        or "mapped-by-explicit-equivalence release Work is not canonical" in error
        for error in validate(tampered)
    )
    # A canonical re-key cannot silently fall back to the ordinary mapped
    # state while changing the release's Work relation.
    tampered = deepcopy(graph)
    stateful_release = next(
        row for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["payload"]["workMappingState"] == "mapped-by-explicit-equivalence"
    )
    current_work_id = next(
        edge["toId"] for edge in tampered["edges"]
        if edge["fromType"] == "card-release"
        and edge["fromId"] == stateful_release["entityId"]
        and edge["relation"] == "implements"
    )
    alternate_work = next(
        row for row in tampered["entities"]
        if row["entityType"] == "work" and row["entityId"] != current_work_id
    )
    stateful_release["payload"]["workMappingState"] = "mapped"
    stateful_release["payload"]["work"] = alternate_work["payload"]["cardKey"]
    next(
        edge for edge in tampered["edges"]
        if edge["fromType"] == "card-release"
        and edge["fromId"] == stateful_release["entityId"]
        and edge["relation"] == "implements"
    )["toId"] = alternate_work["entityId"]
    assert any(
        "re-keyed release must retain mapped-by-explicit-equivalence state" in error
        for error in validate(tampered)
    )
    rr111_releases = {
        "RELEASE:JP:Japanese:DP-P:127:None",
        "RELEASE:WEST:English:RR:111:None",
        "RELEASE:WEST:French:RR:111:None",
        "RELEASE:WEST:German:RR:111:None",
        "RELEASE:WEST:Italian:RR:111:None",
    }
    rr111_work_id = "WORK:Snorlax-LvX-Big-Appetite-Exercise"
    assert {
        row["entityId"]
        for row in graph["entities"]
        if row["entityType"] == "card-release"
        and row["entityId"] in rr111_releases
        and row["payload"]["workMappingState"] == "mapped"
        and row["payload"]["work"] == "Snorlax-LvX-Big-Appetite-Exercise"
    } == rr111_releases
    assert {
        row["fromId"]
        for row in graph["edges"]
        if row["fromType"] == "card-release"
        and row["fromId"] in rr111_releases
        and row["relation"] == "implements"
        and row["toType"] == "work"
        and row["toId"] == rr111_work_id
    } == rr111_releases
    dpp126_release_id = "RELEASE:JP:Japanese:DP-P:126:None"
    dpp126_work_id = "WORK:Snorlax-Lv37-Pick-and-Collect-Roll-Over"
    dpp126_release = next(
        row for row in graph["entities"]
        if row["entityType"] == "card-release" and row["entityId"] == dpp126_release_id
    )
    assert dpp126_release["payload"]["workMappingState"] == "mapped"
    assert dpp126_release["payload"]["work"] == "Snorlax-Lv37-Pick-and-Collect-Roll-Over"
    assert any(
        row["fromType"] == "card-release"
        and row["fromId"] == dpp126_release_id
        and row["relation"] == "implements"
        and row["toType"] == "work"
        and row["toId"] == dpp126_work_id
        for row in graph["edges"]
    )
    hungry_release_id = "RELEASE:JP:Japanese:UNP:unnumbered:None"
    hungry_work_id = "WORK:Hungry-Snorlax-Lv50-Eat-Rollout"
    hungry_releases = [
        row for row in graph["entities"]
        if row["entityType"] == "card-release"
        and row["payload"].get("localSetCode") == "UNP"
        and row["payload"].get("localNumber") == ""
    ]
    assert len(hungry_releases) == 1
    assert hungry_releases[0]["entityId"] == hungry_release_id
    assert hungry_releases[0]["payload"]["workMappingState"] == "mapped"
    assert hungry_releases[0]["payload"]["work"] == "Hungry-Snorlax-Lv50-Eat-Rollout"
    assert any(
        row["fromType"] == "card-release"
        and row["fromId"] == hungry_release_id
        and row["relation"] == "implements"
        and row["toType"] == "work"
        and row["toId"] == hungry_work_id
        for row in graph["edges"]
    )
    assert project_physical_evidence(deepcopy(graph)) == graph
    # A newer publisher observation survives physical refresh and reaches export metadata.
    dated = deepcopy(graph)
    source = next(row for row in dated["entities"] if row["entityType"] == "set-source-record")
    source["payload"]["retrieved"] = "2030-01-02"
    dated = project_physical_evidence(dated)
    assert dated["meta"]["generated"] == "2030-01-02"
    assert project_physical_evidence(deepcopy(dated))["meta"]["generated"] == "2030-01-02"
    dated["meta"]["generated"] = "2030-01-03"
    assert project_physical_evidence(dated)["meta"]["generated"] == "2030-01-03"
    # A later identity-only photo updates the shared snapshot even without a finish.
    with tempfile.TemporaryDirectory() as directory:
        specimens_path = Path(directory) / "specimens.json"
        specimens = json.loads(graph_module.SPECIMENS.read_text(encoding="utf-8"))
        identity_only = next(row for row in specimens["specimens"]
                             if row["specimenId"] == "SPEC-0551")
        assert not identity_only.get("physicalObservation")
        identity_only["recordedAt"] = "2031-02-03"
        specimens_path.write_text(json.dumps(specimens), encoding="utf-8")
        original_specimens_path = graph_module.SPECIMENS
        graph_module.SPECIMENS = specimens_path
        try:
            unlinked = next(row for row in specimens["specimens"]
                            if not row.get("citedBy") and not row.get("physicalObservation")
                            and not row.get("sameCardAs") and row["specimenId"] == "SPEC-0012")
            unlinked["recordedAt"] = "2040-01-01"
            specimens_path.write_text(json.dumps(specimens), encoding="utf-8")
            dated_identity = project_physical_evidence(deepcopy(graph))
            assert dated_identity["meta"]["generated"] == "2031-02-03"
            assert project_physical_evidence(deepcopy(dated_identity)) == dated_identity
            dated_identity["meta"]["generated"] = "2031-02-04"
            assert project_physical_evidence(dated_identity)["meta"]["generated"] == "2031-02-04"
            # An unknown citation cannot promote the later unadmitted date either.
            unlinked["citedBy"] = ["nonexistent:release"]
            specimens_path.write_text(json.dumps(specimens), encoding="utf-8")
            assert project_physical_evidence(deepcopy(graph))["meta"]["generated"] == "2031-02-03"
            # Direct source-first evidence remains supporting without a reverse citation.
            direct = next(row for row in specimens["specimens"] if row["specimenId"] == "SPEC-0285")
            direct["citedBy"] = []
            direct["recordedAt"] = "2032-01-01"
            specimens_path.write_text(json.dumps(specimens), encoding="utf-8")
            assert project_physical_evidence(deepcopy(graph))["meta"]["generated"] == "2032-01-01"
            physical = next(row for row in specimens["specimens"] if row["specimenId"] == "SPEC-0554")
            physical["recordedAt"] = "2033-01-01"
            specimens_path.write_text(json.dumps(specimens), encoding="utf-8")
            assert project_physical_evidence(deepcopy(graph))["meta"]["generated"] == "2033-01-01"
        finally:
            graph_module.SPECIMENS = original_specimens_path
    # The reviewed base is retained input, not reconstructible physical output (#357).
    retained = deepcopy(graph)
    work = next(row for row in retained["entities"] if row["entityType"] == "work")
    work["payload"]["reviewedBoundaryFixture"] = "retain reviewed metadata"
    expected_work = deepcopy(work)
    projected = project_physical_evidence(retained)
    assert next(row for row in projected["entities"]
                if row["entityId"] == expected_work["entityId"]) == expected_work
    assert project_physical_evidence(deepcopy(projected)) == projected
    # A positional printing id may change when a new printing sorts before it.  The
    # existing physical node and claim must nevertheless follow the same semantics.
    with tempfile.TemporaryDirectory() as directory:
        finish_path = Path(directory) / "finish_units.json"
        finish_copy = json.loads(
            (ROOT / "verification" / "finish_units.json").read_text(encoding="utf-8")
        )
        # Marking permutations must also preserve every existing node, claim and
        # provenance reference when the physical slice is actually rebuilt (#350).
        for unit in finish_copy["units"]:
            for printing in unit.get("printings", []):
                if printing.get("markings"):
                    printing["markings"].reverse()
        finish_path.write_text(json.dumps(finish_copy), encoding="utf-8")
        original_finish_path = graph_module.FINISH_UNITS
        graph_module.FINISH_UNITS = finish_path
        try:
            permuted_projection = project_physical_evidence(deepcopy(graph))
        finally:
            graph_module.FINISH_UNITS = original_finish_path
        assert permuted_projection["edges"] == graph["edges"]
        assert permuted_projection["migrationDispositions"] == graph["migrationDispositions"]
        for before, after in zip(graph["entities"], permuted_projection["entities"], strict=True):
            before, after = deepcopy(before), deepcopy(after)
            for row in (before, after):
                if row["entityType"] == "physical-printing":
                    row["payload"]["markings"] = graph_module._semantic_markings(row["payload"].get("markings"))
            assert before == after
        retained_source_id = next(e["payload"]["sourcePrintingId"] for e in graph["entities"]
                                  if e["entityId"] == "PHYSICAL:F0167-P01")
        shifted = next(
            printing for unit in finish_copy["units"]
            for printing in unit.get("printings", [])
            if printing.get("printingId") == retained_source_id
        )
        shifted["printingId"] = "F0167-P99"
        finish_path.write_text(json.dumps(finish_copy), encoding="utf-8")
        original_finish_path = graph_module.FINISH_UNITS
        graph_module.FINISH_UNITS = finish_path
        try:
            shifted_projection = project_physical_evidence(deepcopy(graph))
        finally:
            graph_module.FINISH_UNITS = original_finish_path
    shifted_physical = next(
        row["payload"] for row in shifted_projection["entities"]
        if row["entityType"] == "physical-printing"
        and row["entityId"] == "PHYSICAL:F0167-P01"
    )
    assert shifted_physical["sourcePrintingId"] == "F0167-P99"
    assert shifted_physical["establishingClaimId"] == "CLAIM:finish:F0167-P01"
    standalone_claim = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceId") == "SPEC-0030"
    )
    assert standalone_claim["disposition"] == "established-and-mapped"
    assert standalone_claim["materializedTargetId"] == "PHYSICAL:specimen:SPEC-0030"
    assert any(
        row["entityType"] == "physical-printing"
        and row["entityId"] == "PHYSICAL:specimen:SPEC-0030"
        for row in graph["entities"]
    )
    specimens_with_denominator = json.loads(
        (ROOT / "verification/specimens.json").read_text(encoding="utf-8")
    )
    next(row for row in specimens_with_denominator["specimens"]
         if row["specimenId"] == "SPEC-0030")["number"] = "145/999"
    assert not validate(graph, identity_inputs={"specimens": specimens_with_denominator})
    meta = graph["meta"]
    assert meta["schema"] == "snoredex-authoritative-locality-graph"
    assert meta["schemaVersion"] == "1.1.0"
    assert meta["status"] == "authoritative-migrated"
    assert "inputs" not in meta

    entities = {(row["entityType"], row["entityId"]): row for row in graph["entities"]}
    edges = graph["edges"]
    edge_keys = {
        (row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
        for row in edges
    }
    assert len(entities) == graph["summary"]["entities"]
    assert len(edge_keys) == len(edges)
    assert graph["summary"]["candidateClaims"] > 0
    assert graph["summary"]["cardReleases"] > 0
    assert graph["summary"]["physicalPrintings"] > 0
    assert graph["summary"]["localizations"] == 16
    assert graph["summary"]["setSourceRecords"] == graph["summary"]["setSourceDispositions"]

    dutch_printings = {
        row["entityId"]: row["payload"]
        for row in graph["entities"]
        if row["entityType"] == "physical-printing"
        and row["entityId"] in {
            "PHYSICAL:F0167-P01", "PHYSICAL:F0167-P02",
            "PHYSICAL:F0174-P01", "PHYSICAL:F0174-P02",
        }
    }
    assert {
        printing_id: (row["finish"], row["edition"])
        for printing_id, row in dutch_printings.items()
    } == {
        "PHYSICAL:F0167-P01": ("holo", "1st Edition"),
        "PHYSICAL:F0167-P02": ("holo", "Unlimited"),
        "PHYSICAL:F0174-P01": ("non-holo", "1st Edition"),
        "PHYSICAL:F0174-P02": ("non-holo", "Unlimited"),
    }
    assert all(
        row["markings"] == ([{
            "kind": "edition-stamp", "text": "EDITIE 1", "role": "print-identity",
        }] if row["edition"] == "1st Edition" else [])
        for row in dutch_printings.values()
    )
    for specimen_id in ("SPEC-0040", "SPEC-0041", "SPEC-0042", "SPEC-0043", "SPEC-0044"):
        claim = entities[("candidate-claim", f"CLAIM:specimen:{specimen_id}")]["payload"]
        assert claim["evidenceStatus"] == "observed"
        assert claim["materializedTargetId"] is None
        assert claim["reason"].startswith("provides provenance for PHYSICAL:F")
        assert claim["provenanceTargetId"].startswith("PHYSICAL:F")
        assert "corroboratedTargetId" not in claim

    localizations = {
        row["payload"]["languageTag"]: row["payload"]
        for row in graph["entities"] if row["entityType"] == "localization"
    }
    assert localizations["es-ES"]["locality"] == "WEST"
    assert localizations["es-419"]["locality"] == "LATAM"
    assert localizations["pt"]["language"] == "Portuguese"

    unresolved_editions = [
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "set-edition"
        and row["payload"]["identity"]["state"] == "needs-local-identifier"
    ]
    assert unresolved_editions
    assert all(row["catalogue"]["localSetId"] for row in unresolved_editions)

    finish_candidate = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceKind") == "finish-printing-record"
        and row["payload"].get("disposition") == "candidate-needs-evidence"
    )
    assert ("candidate-claim", finish_candidate["claimId"], "proposes-for", "card-release",
            finish_candidate["proposedCardReleaseId"]) in edge_keys

    # A contradicted claim must not be promotable merely by changing its disposition
    # and pointing it at an existing release.
    tampered = deepcopy(graph)
    tampered_claim = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("evidenceStatus") == "contradicted"
    )
    release_id = next(
        row["entityId"] for row in tampered["entities"]
        if row["entityType"] == "card-release"
    )
    tampered_claim["disposition"] = "established-and-mapped"
    tampered_claim["proposedTargetId"] = release_id
    tampered_claim["materializedTargetId"] = release_id
    assert any("positive evidence" in error for error in validate(tampered))

    # Appending to the raw registry without adding graph nodes/dispositions must fail
    # the cross-store accounting check.
    registry = json.loads((ROOT / "verification/set_catalogue_sources.json").read_text(encoding="utf-8"))
    extra = deepcopy(registry["sourceRecords"][0])
    extra["sourceRecordId"] = "SET-SRC-TEST-UNACCOUNTED"
    registry["sourceRecords"].append(extra)
    assert any("source records" in error for error in validate(graph, registry))

    # The other append-only identity stores are covered by the same graph boundary.
    identity_inputs = {
        "source_first": json.loads(
            (ROOT / "verification/source_first_prints.json").read_text(encoding="utf-8")
        ),
    }
    identity_inputs["source_first"]["prints"].append(
        {**identity_inputs["source_first"]["prints"][0], "printId": "TEST-UNACCOUNTED"}
    )
    assert any("identity input claims" in error for error in validate(graph, identity_inputs=identity_inputs))

    # External finish profiles cannot close a list.
    tampered = deepcopy(graph)
    next(row["payload"] for row in tampered["entities"] if row["entityType"] == "finish-profile")[
        "closedWithinScope"
    ] = True
    assert any("claims closure" in error for error in validate(tampered))

    # Rarity observations must stay in the locality of the release they describe.
    tampered = deepcopy(graph)
    rarity = next(row["payload"] for row in tampered["entities"] if row["entityType"] == "rarity-claim")
    release = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "card-release" and row["entityId"] == rarity["cardReleaseId"]
    )
    other_source = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "set-source-record"
        and (row["payload"].get("raw") or {}).get("locality")
        and (row["payload"].get("raw") or {}).get("locality") != release["locality"]
    )
    rarity["sourceRecordId"] = other_source["sourceRecordId"]
    rarity["sourceProvider"] = other_source["provider"]
    assert any("rarity claim source locality mismatch" in error for error in validate(tampered))

    # Re-key decisions must round-trip into both equivalence assertions and migration
    # targetRefs, including one-to-many decisions such as U0414.
    rekeys = json.loads(
        (ROOT / "verification/legacy_issue_rekeys.json").read_text(encoding="utf-8")
    )
    rekeys["questionSets"][0]["mappings"][0]["sourceFirstRecordId"] = "TW:AS5a:117/184:base"
    assert any("re-key" in error for error in validate(graph, identity_inputs={"rekeys": rekeys}))

    # A specimen observation must remain attached to a release with the same local
    # set, number and language, not merely to a printing with matching finish fields.
    tampered = deepcopy(graph)
    specimen_claim = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceId") == "SPEC-0001"
    )
    specimen_printing = next(
        row["payload"] for row in tampered["entities"]
        if row["entityType"] == "physical-printing"
        and row["entityId"] == specimen_claim["provenanceTargetId"]
    )
    specimen_printing["cardReleaseId"] = next(
        row["entityId"] for row in tampered["entities"]
        if row["entityType"] == "card-release"
        and row["entityId"] != specimen_printing["cardReleaseId"]
    )
    assert any("specimen release identity is stale" in error for error in validate(tampered))

    # Explicit specimen conflicts remain reviewable candidates; they never materialize
    # a physical printing until the conflict is resolved.
    conflict_graph = deepcopy(graph)
    conflict_claim = next(
        row["payload"] for row in conflict_graph["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceKind") == "finish-printing-record"
        and row["payload"].get("disposition") == "candidate-needs-evidence"
    )
    conflict_claim["evidenceStatus"] = "pending"
    conflict_claim["conflictsWith"] = ["SPEC-0040"]
    conflicted_finishes = json.loads(
        (ROOT / "verification/finish_units.json").read_text(encoding="utf-8")
    )
    conflicted_printing_id = conflict_claim["sourceId"]
    for finish_unit in conflicted_finishes["units"]:
        for printing in finish_unit.get("printings", []):
            if printing.get("printingId") == conflicted_printing_id:
                printing["verificationStatus"] = "pending"
    assert not validate(conflict_graph, identity_inputs={"finishes": conflicted_finishes})
    conflict_claim["conflictsWith"] = ["SPEC-NOT-RECORDED"]
    assert any(
        "finish conflict claim" in error
        for error in validate(conflict_graph, identity_inputs={"finishes": conflicted_finishes})
    )

    # A conflicted specimen may identify a source-first release, but it must remain pending
    # rather than materializing through the standalone-specimen fallback.
    with tempfile.TemporaryDirectory() as directory:
        finish_path = Path(directory) / "finish_units.json"
        specimens_path = Path(directory) / "specimens.json"
        finish_copy = json.loads(
            (ROOT / "verification/finish_units.json").read_text(encoding="utf-8")
        )
        conflicted_printing = next(
            printing for unit in finish_copy["units"]
            for printing in unit.get("printings", [])
        )
        conflicted_printing["verificationStatus"] = "pending"
        conflicted_printing["specimenIds"] = ["SPEC-0030"]
        conflicted_printing["conflictsWith"] = ["SPEC-0040"]
        finish_path.write_text(json.dumps(finish_copy), encoding="utf-8")
        specimens_path.write_text(
            (ROOT / "verification/specimens.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        original_finish_path = graph_module.FINISH_UNITS
        original_specimens_path = graph_module.SPECIMENS
        graph_module.FINISH_UNITS = finish_path
        graph_module.SPECIMENS = specimens_path
        try:
            conflict_projection = project_physical_evidence(deepcopy(graph))
        finally:
            graph_module.FINISH_UNITS = original_finish_path
            graph_module.SPECIMENS = original_specimens_path
    conflict_specimen_claim = next(
        row["payload"] for row in conflict_projection["entities"]
        if row["entityType"] == "candidate-claim"
        and row["payload"].get("sourceId") == "SPEC-0030"
    )
    assert conflict_specimen_claim["disposition"] == "candidate-needs-evidence"
    assert conflict_specimen_claim["materializedTargetId"] is None
    assert not any(
        row["entityId"] == "PHYSICAL:specimen:SPEC-0030"
        for row in conflict_projection["entities"]
    )

    identity = identity_view(graph)
    migrations = {
        (row["sourceKind"], row["sourceId"]): row
        for row in graph["migrationDispositions"]
    }
    for original_id in ("F0167-P01", "F0167-P02", "F0174-P01", "F0174-P02"):
        physical = next(e["payload"] for e in graph["entities"]
                        if e["entityId"] == f"PHYSICAL:{original_id}")
        assert migrations[("finish-printing-record", physical["sourcePrintingId"])]["targetRef"] == f"PHYSICAL:{original_id}"
    u0414 = migrations[("legacy-issue-rekey", "U0414")]
    assert u0414["targetRefs"] == [
        "RELEASE:TW:T-Chinese:AS5a:117/184:Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX",
        "RELEASE:TW:T-Chinese:SM-P:053:Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX",
    ]
    assert u0414["targetRef"] == u0414["targetRefs"][0]
    rekey = next(row for row in identity["reports"]["legacyIssueRekeys"][0]["rows"]
                 if row["legacyUnitId"] == "U0414")
    assert rekey["localCardReleaseIds"] == u0414["targetRefs"]

    with sqlite3.connect(ROOT / "snoredex.sqlite") as connection:
        target_ref, target_refs_json = connection.execute(
            "SELECT target_ref, target_refs_json "
            "FROM graph_migration_dispositions "
            "WHERE source_kind = 'legacy-issue-rekey' AND source_id = 'U0414'"
        ).fetchone()
    assert target_ref == u0414["targetRef"]
    assert json.loads(target_refs_json) == u0414["targetRefs"]

    with tempfile.TemporaryDirectory() as directory:
        temporary_root = Path(directory)
        output = temporary_root / "authoritative_graph.json"
        invalid = deepcopy(graph)
        localization = next(
            row for row in invalid["entities"] if row["entityType"] == "localization"
        )
        localization["payload"]["localizationId"] = "INVALID"
        output.write_text(json.dumps(invalid), encoding="utf-8")
        before = output.read_bytes()
        original_output = graph_module.OUTPUT
        original_arguments = sys.argv
        graph_module.OUTPUT = output
        try:
            sys.argv = ["authoritative_graph.py", "--write"]
            assert graph_module.main() == 1
        finally:
            sys.argv = original_arguments
            graph_module.OUTPUT = original_output
        assert output.read_bytes() == before

        if os.name == "posix":
            mode_output = temporary_root / "mode_graph.json"
            mode_output.write_bytes(b"old graph")
            os.chmod(mode_output, 0o640)
            graph_module.OUTPUT = mode_output
            try:
                graph_module.write_graph(graph)
            finally:
                graph_module.OUTPUT = original_output
            assert stat.S_IMODE(mode_output.stat().st_mode) == 0o640

        for operation in ("fsync", "replace"):
            with patch.object(graph_module, "OUTPUT", output), patch(
                f"atomic_write.os.{operation}", side_effect=OSError("simulated write failure"),
            ):
                try:
                    graph_module.write_graph(graph)
                except OSError:
                    pass
                else:
                    raise AssertionError("write failure must propagate")
            assert output.read_bytes() == before
            assert not list(temporary_root.glob(".authoritative_graph.json.*.tmp"))
        with patch.object(graph_module, "OUTPUT", output):
            graph_module.write_graph(graph)
        assert output.read_bytes() == (json.dumps(graph, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        if os.name == "nt":
            os.chmod(output, 0o444)
            try:
                with patch.object(graph_module, "OUTPUT", output):
                    try:
                        graph_module.write_graph(graph)
                    except PermissionError:
                        pass
                    else:
                        raise AssertionError("read-only replacement must fail on Windows")
                assert output.read_bytes() == (json.dumps(graph, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                assert not list(temporary_root.glob(".authoritative_graph.json.*.tmp"))
            finally:
                os.chmod(output, 0o600)
    print(
        "authoritative graph regression passed: "
        f"{len(entities)} entities, {len(edges)} edges, "
        f"{len(graph['migrationDispositions'])} dispositions"
    )


if __name__ == "__main__":
    main()
