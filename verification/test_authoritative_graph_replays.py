#!/usr/bin/env python3
"""Replays of reviewed graph migrations against the current stores (split from
test_authoritative_graph.py so the two halves run in parallel, #460)."""

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
    # #437 admits its own high-class-pack observations after this correction; they stay native too.
    issue437 = [row for row in claims if row["rarityClaimId"].startswith("RARITYCLAIM:issue437:")]
    assert len(issue437) == 3 and all(row["normalizedRarityId"] is None for row in issue437)
    unresolved = [row for row in claims if row.get("normalizedRarityId") is None
                  and row["cardReleaseId"].split(":")[1] in ("ID", "KR", "TH")
                  and row not in issue437]
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


def main() -> None:
    verify_research_correction()
    verify_30th_admission_replay()
    verify_kss_retirement_replay()
    print("authoritative graph replays passed: research correction, 30th admission, KSS retirement")


if __name__ == "__main__":
    main()
