"""Check exact accepted finishes and conservation against the pre-acceptance head."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "8f6dc2bd231d5d380fbaf31eacf5f0357ae06e67"
ACCEPTED = "ba97d92cd51bcb25fee02b6821e32eefd977f7e9"
TARGETS = {("AS1D", "108"): "non-holo", ("AC3D", "120"): "non-holo",
           ("sc1D I", "132"): "non-holo", ("sc1D I", "133"): "non-holo",
           ("scA I", "084"): "non-holo", ("scD I", "111"): "non-holo",
           ("sc1b I", "119"): "holo"}


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def baseline(path, ref=BASE):
    return json.loads(subprocess.check_output(["git", "show", ref + ":" + path], cwd=ROOT))


def targeted(row):
    return row["localizationId"] == "LOCALIZATION:ID:id" and (row["localSetCode"], row["collectorNumber"]) in TARGETS


def main():
    sys.path.insert(0, str(ROOT / "scripts"))
    import source_registry as registry
    calls = []
    fixture = {"sourceRecords": [dict(sourceRecordId="mixed", sourceKind="edition-availability-record",
        provider="mixed-positive-evidence", retrieved="2026-10-02", raw=dict(physicalPrintingEvidence=dict(
            sourceUrl="https://www.pokemon.com/us/news/example", finish="holo"))),
        dict(sourceRecordId="identity-only", sourceKind="edition-availability-record", provider="bulbapedia", raw={})]}
    registry.record_set_evidence(fixture, lambda *args, **kw: calls.append((args, kw)))
    assert len(calls) == 1 and calls[0][0][2:5] == ("finish", "mixed", "2026-10-02")
    assert calls[0][1]["provider_id"] == "pokemon-official"
    import source_capabilities as capabilities
    surface = next(s for s in load("verification/source_capabilities.json")["surfaces"]
                   if s["surfaceId"] == "tpci-journey-together-build-battle")
    assert capabilities.matching_surfaces(dict(canonicalUrl=surface["query"]["endpoint"]), [surface]) == [surface]
    assert capabilities.matching_surfaces(dict(canonicalUrl="https://www.pokemon.com/us/news/another-product"), [surface]) == []
    assert surface["coverageEdges"][0]["positiveEvidenceCapabilities"] == ["finish"]
    old, new = baseline("collector_catalogue.json"), load("collector_catalogue.json")
    integrated = baseline("collector_catalogue.json", ACCEPTED)
    # The seven-finish batch preserves its siblings at its acceptance boundary.
    # Later owner imports have their own conservation check, not this older baseline.
    assert [r for r in old["items"] if not targeted(r)] == [r for r in integrated["items"] if not targeted(r)]
    accepted = [r for r in new["items"] if r["active"] and targeted(r)]
    assert accepted == [r for r in integrated["items"] if r["active"] and targeted(r)]
    assert len(accepted) == 7
    for row in accepted:
        assert row["itemKind"] == "verified-printing"
        assert row["finish"] == TARGETS[row["localSetCode"], row["collectorNumber"]]
        assert row["completenessStatus"] == "positive-evidence-only"
        prior = next(r for r in old["items"] if r["cardReleaseId"] == row["cardReleaseId"])
        for field in ("cardReleaseId", "setEditionId", "localSetId", "workId", "rarity", "releaseDate"):
            assert row[field] == prior[field], field
    for path in ("verification/units.json", "verification/owner_adjudications.json", "verification/finish_units.json"):
        current, prior = load(path), baseline(path)
        if path.endswith("finish_units.json"):
            # Regeneration date is metadata; finish records and all other fields must match.
            current["meta"].pop("generated")
            prior["meta"].pop("generated")
        assert current == prior, path
    before = baseline("verification/specimens.json")["specimens"]
    after = load("verification/specimens.json")["specimens"]
    accepted_specimens = baseline("verification/specimens.json", ACCEPTED)["specimens"]
    assert accepted_specimens[:-1] == before and accepted_specimens[-1]["specimenId"] == "SPEC-0607"
    specimen = next(s for s in after if s["specimenId"] == "SPEC-0607")
    assert specimen == accepted_specimens[-1]
    assert specimen["recordedAt"] == "2026-10-02"
    assert "ownerAttestedFields" not in specimen["physicalObservation"]
    image = ROOT / "verification/specimens" / specimen["photograph"]
    assert "sha256:" + hashlib.sha256(image.read_bytes()).hexdigest() == specimen["photographSha256"]
    sources = [s for s in load("verification/set_catalogue_sources.json")["sourceRecords"]
               if s["sourceRecordId"].endswith("FINISH-ID-20261005")]
    assert len(sources) == 6
    for source in sources:
        assert source["provider"] == "bulbapedia" and source["retrieved"] == "2026-10-02"
        facts = source["raw"]["physicalPrintingEvidence"]
        assert facts["specimenIds"] == [] and facts["positiveOnly"] and not facts["completenessClaim"]
    indexed = load("verification/source_registry.json")["evidence"]
    for source in load("verification/set_catalogue_sources.json")["sourceRecords"]:
        facts = (source.get("raw") or {}).get("physicalPrintingEvidence")
        if facts and facts.get("finish"):
            assert any(source["sourceRecordId"] in row["stableIds"] and "finish" in row["dimensions"]
                       for row in indexed), source["sourceRecordId"]
    subprocess.run([sys.executable, str(ROOT / "verification/evidence/id-owner-finish-20261005/check_intake.py")], check=True)
    print("Seven exact finishes preserved at current head; both acceptance boundaries conserve unrelated evidence.")


if __name__ == "__main__":
    main()
