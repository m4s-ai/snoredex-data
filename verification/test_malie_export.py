#!/usr/bin/env python3
"""Independent synthetic Malie contract regressions; never real-card evidence."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import malie_export as exporter


def synthetic_inputs(profile, fixture):
    profile = copy.deepcopy(profile)
    release = "SYNTHETIC-RELEASE"
    items = []
    for suffix in ("a", "b"):
        items.append({"itemId": "synthetic-" + suffix, "cardReleaseId": release,
                      "physicalPrintingId": "SYNTHETIC-PRINTING-" + suffix,
                      "localizationId": "LOCALIZATION:WEST:en", "localSetId": "LOCALSET:WEST:MEW",
                      "localSetCode": "MEW", "collectorNumber": "001", "collectorNumberDenominator": "165",
                      "rarity": {"evidenceStatus": "source-backed", "normalizedId": "uncommon"},
                      "itemKind": "verified-printing", "finishVerificationStatus": "confirmed",
                      "finish": "non-holo", "cardSize": "standard",
                      "edition": None, "markings": [], "distribution": None})
    profile["pilot"] = [{key: row[key] for key in ("itemId", "cardReleaseId", "physicalPrintingId", "localizationId")}
                        for row in items]
    source = {"sourceId": "fixture", "providerId": "fixture", "url": "https://example.invalid/synthetic",
              "retainedPath": "verification/fixtures/malie_contract.json", "sha256": "0" * 64,
              "retrievedAt": "2026-09-21",
              "scope": {"cardReleaseId": release, "physicalPrintingIds": [row["physicalPrintingId"] for row in items],
                        "fields": ["/" + name for name in set(fixture["validPayload"]) | set(fixture["knownInapplicableFields"])],
                        "limits": "Synthetic contract input, not accepted physical-card evidence."}}
    observations = []
    for name in sorted(set(fixture["validPayload"]) | set(fixture["knownInapplicableFields"])):
        known = name in fixture["validPayload"]
        row = {"observationId": "synthetic-" + name, "cardReleaseId": release,
               "physicalPrintingIds": [item["physicalPrintingId"] for item in items],
               "field": "/" + name, "state": "known" if known else "not-applicable",
               "sourceIds": ["fixture"], "observedAt": "2026-09-21", "method": "synthetic fixture",
               "basis": "Invented test content, not an observation."}
        if known:
            row["value"] = copy.deepcopy(fixture["validPayload"][name])
        observations.append(row)
    content = {"sources": [source], "observations": observations}
    providers = {"fixture": {"authorityTier": 2, "licenseOrTerms": "Synthetic test fixture only."}}
    digests = {path: "0" * 64 for path in (*exporter.INPUT_FILES, source["retainedPath"])}
    return profile, {"items": items}, content, digests, providers, {}


def check_bundle_contract(profile, fixture):
    inputs = synthetic_inputs(profile, fixture)
    bundle = exporter.build_bundle(*inputs)
    cards, report = (json.loads(bundle[name]) for name in ("cards.json", "report.json"))
    assert cards == [fixture["validPayload"], fixture["validPayload"]]
    assert [r["physicalPrintingId"] for r in report["entries"]] == ["SYNTHETIC-PRINTING-a", "SYNTHETIC-PRINTING-b"]
    assert [r["cardIndex"] for r in report["entries"]] == [0, 1]
    assert all(row["identity"]["distribution"] is None for row in report["entries"])
    assert report["summary"] == {"selected": 2, "exported": 2, "needs-evidence": 0,
                                 "needs-mapping": 0, "outside-profile": 0, "blocked-by-source": 0}
    reordered = copy.deepcopy(inputs)
    reordered[0]["pilot"].reverse()
    reordered[1]["items"].reverse()
    reordered[2]["observations"].reverse()
    assert exporter.build_bundle(*reordered) == bundle
    check_disposition_reasons(inputs)
    check_physical_boundaries(inputs)
    check_observation_agreement(inputs)
    check_withheld_companions(inputs)
    check_foil_applicability(inputs)
    check_identity_digests(inputs)
    check_entry_digests(inputs)
    check_envelope_contract(bundle)
    check_input_dependencies(inputs)

    for field in ("/foil", "/copyright", "/name"):
        altered = copy.deepcopy(inputs)
        altered[2]["observations"] = [r for r in altered[2]["observations"] if r["field"] != field]
        withheld = exporter.build_bundle(*altered)
        assert json.loads(withheld["cards.json"]) == []
        rows = json.loads(withheld["report.json"])["entries"]
        assert len(rows) == 2 and all(r["status"] == "needs-evidence" for r in rows)
        assert all(any(reason["field"] == field for reason in r["reasons"]) for r in rows)
        assert all("cardIndex" not in row for row in rows)
    altered = copy.deepcopy(inputs)
    altered[1]["items"][0]["finish"] = "unknown"
    rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
    assert rows[0]["status"] == "needs-evidence" and rows[1]["status"] == "exported"
    altered = copy.deepcopy(inputs)
    altered[0]["pilot"][0]["localizationId"] = "LOCALIZATION:WEST:de"
    altered[1]["items"][0]["localizationId"] = "LOCALIZATION:WEST:de"
    rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
    assert rows[0]["status"] == "needs-mapping" and rows[1]["status"] == "exported"
    for mutate in (lambda a: a[0]["pilot"].append(copy.deepcopy(a[0]["pilot"][0])),
                   lambda a: a[0]["pilot"][0].update(physicalPrintingId="UNRELATED")):
        altered = copy.deepcopy(inputs)
        mutate(altered)
        try:
            exporter.build_bundle(*altered)
        except exporter.ExportError:
            pass
        else:
            raise AssertionError("accepted duplicate or mismatched selection")
    for mutate in (lambda r: r["entries"].pop(), lambda r: r["entries"][0].update(cardIndex=1),
                   lambda r: r.update(cardsSha256="0" * 64), lambda r: r["summary"].update(exported=1),
                   lambda r: r.update(inputs={"synthetic.json": "invalid"}),
                   lambda r: r["entries"][0]["identity"].update(finish="unknown"),
                   lambda r: r["entries"][0]["fieldSources"]["/name"].update(sources=[]),
                   lambda r: r["entries"][0]["fieldSources"]["/text"].update(covers=[])):
        broken = dict(bundle)
        report = json.loads(bundle["report.json"])
        mutate(report)
        broken["report.json"] = exporter.canonical_bytes(report)
        try:
            exporter.validate_bundle(broken)
        except exporter.ExportError:
            pass
        else:
            raise AssertionError("accepted corrupt bundle accounting/digests")
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "absent"
        try:
            exporter.check_outputs(destination, bundle)
        except exporter.ExportError:
            pass
        else:
            raise AssertionError("missing bundle passed")
        assert not destination.exists(), "check created an absent directory"
        exporter.write_outputs(destination, bundle)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in destination.iterdir()}
        exporter.check_outputs(destination, bundle)
        assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in destination.iterdir()}
        (destination / "cards.json").write_bytes(b"[]\n")
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in destination.iterdir()}
        try:
            exporter.check_outputs(destination, bundle)
        except exporter.ExportError:
            pass
        else:
            raise AssertionError("stale bundle passed")
        assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in destination.iterdir()}
    print("Bundle checks: distinct equal payloads, complete dispositions, stable traversal order and observational checks passed.")


def check_disposition_reasons(inputs):
    conflicting = copy.deepcopy(inputs)
    original = next(row for row in conflicting[2]["observations"] if row["field"] == "/name")
    conflicting[2]["observations"].append({**original, "observationId": "conflicting-name", "value": "Other name"})
    rows = json.loads(exporter.build_bundle(*conflicting)["report.json"])["entries"]
    assert all(row["status"] == "needs-mapping" for row in rows)
    assert all(any(reason["code"] == "conflicting-observations" for reason in row["reasons"]) for row in rows)
    altered = copy.deepcopy(inputs)
    name = next(row for row in altered[2]["observations"] if row["field"] == "/name")
    name.update(state="blocked-by-source", basis="Retained source could not be decoded.", nextStep="Retrieve a readable exact record.")
    name.pop("value")
    unknown = {**name, "observationId": "synthetic-unknown", "state": "unknown", "basis": "Alternative source needs inspection."}
    altered[2]["observations"].append(unknown)
    bundle = exporter.build_bundle(*altered)
    report = json.loads(bundle["report.json"])
    assert all(row["status"] == "blocked-by-source" for row in report["entries"])
    assert {r["status"] for r in report["entries"][0]["reasons"]} == {"blocked-by-source", "needs-evidence"}
    report["entries"][0]["status"] = "needs-evidence"
    bundle["report.json"] = exporter.canonical_bytes(report)
    try:
        exporter.validate_bundle(bundle)
    except exporter.ExportError as error:
        assert "precedence" in str(error)
    else:
        raise AssertionError("incorrect main status accepted")


def check_physical_boundaries(inputs):
    altered = copy.deepcopy(inputs)
    number = next(row for row in altered[2]["observations"] if row["field"] == "/collector_number")
    number["value"].pop("denominator")
    number["value"]["full"] = "001"
    rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
    assert all(row["status"] == "needs-mapping" for row in rows)
    assert all(any(r["field"] == "/collector_number/denominator" for r in row["reasons"]) for row in rows)
    for size, status in (("unknown", "needs-evidence"), (None, "needs-evidence"), ("oversized", "outside-profile")):
        altered = copy.deepcopy(inputs)
        altered[1]["items"][0]["cardSize"] = size
        rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
        assert rows[0]["status"] == status and rows[1]["status"] == "exported"
    for key, value in (("distribution", {"kind": "elite-trainer-box"}),
                       ("markings", [{"role": "distribution-promo", "text": "Pokemon Center"}]),
                       ("edition", "1st Edition"), ("errorClass", "misprint"), ("foilPattern", "unknown-pattern")):
        altered = copy.deepcopy(inputs)
        altered[1]["items"][0][key] = value
        rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
        assert rows[0]["status"] == "needs-mapping" and rows[1]["status"] == "exported", key
        assert rows[0]["identity"][key] == value, key
        assert any(r["field"] == "/identity/" + key for r in rows[0]["reasons"]), key


def check_observation_agreement(inputs):
    altered = copy.deepcopy(inputs)
    rarity = next(row for row in altered[2]["observations"] if row["field"] == "/rarity")
    rarity.update(state="not-applicable")
    rarity.pop("value")
    rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
    assert all(row["status"] == "needs-mapping" for row in rows)
    assert all(any(r["code"] == "rarity-owner-conflict" for r in row["reasons"]) for row in rows)
    altered = copy.deepcopy(inputs)
    tags = next(row for row in altered[2]["observations"] if row["field"] == "/tags")
    tags.update(state="known", value=["FUTURE", "ANCIENT"])
    altered[2]["observations"].append({**tags, "observationId": "second-tags", "value": ["ANCIENT", "FUTURE"]})
    bundle = exporter.build_bundle(*altered)
    assert tags["value"] == ["FUTURE", "ANCIENT"], "normalization changed accepted input observations"
    assert all(card["tags"] == ["ANCIENT", "FUTURE"] for card in json.loads(bundle["cards.json"]))
    assert len(json.loads(bundle["cards.json"])) == 2
    reordered = copy.deepcopy(altered)
    reordered[2]["observations"].reverse()
    assert exporter.build_bundle(*reordered) == bundle
    altered = copy.deepcopy(inputs)
    altered[1]["items"][0]["finish"] = "holo"
    foil = next(row for row in altered[2]["observations"] if row["field"] == "/foil")
    foil.update(state="known", value={"type": "FLAT_SILVER", "mask": "REVERSE"})
    rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
    assert rows[0]["status"] == "needs-mapping"
    assert any(r["code"] == "foil-mask-conflict" for r in rows[0]["reasons"])
    foil["value"]["mask"] = "HOLO"
    rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
    assert rows[0]["status"] == "exported", "matching holo treatment was rejected"


def check_withheld_companions(inputs):
    altered = copy.deepcopy(inputs)
    altered[1]["items"][0]["finish"] = "unknown"
    altered[1]["items"][1]["cardSize"] = "unknown"
    bundle = exporter.build_bundle(*altered)
    report = json.loads(bundle["report.json"])
    assert report["entries"][0]["status"] == "needs-evidence"
    mutations = [
        lambda row: row.pop("identity"), lambda row: row.pop("fieldSources"),
        lambda row: row["identity"].update(localizationId="LOCALIZATION:WEST:de"),
        lambda row: row.update(reasons=[{"status": "needs-evidence"}]),
        lambda row: row["fieldSources"]["/name"].pop("observations"),
        lambda row: row["fieldSources"]["/name"]["sources"][0].pop("sha256"),
        lambda row: row["fieldSources"]["/name"]["observations"][0].update(sourceIds=["missing"]),
        lambda row: row["fieldSources"]["/name"]["sources"][0]["scope"].update(cardReleaseId="other"),
        lambda row: row.update(identity=copy.deepcopy(report["entries"][1]["identity"])),
    ]
    for mutate in mutations:
        corrupt = copy.deepcopy(report)
        mutate(corrupt["entries"][0])
        try:
            exporter.validate_bundle({**bundle, "report.json": exporter.canonical_bytes(corrupt)})
        except exporter.ExportError:
            pass
        else:
            raise AssertionError("accepted damaged withheld companion")


def check_input_dependencies(inputs):
    altered = copy.deepcopy(inputs)
    altered[3]["nonexistent.json"] = "0" * 64
    try:
        exporter.build_bundle(*altered)
    except exporter.ExportError as error:
        assert "input digest set" in str(error)
    else:
        raise AssertionError("producer accepted a fabricated input dependency")
    # The loader validates every retained content source, even without a selected
    # observation. Its actual read remains a dependency of the successful build.
    altered = copy.deepcopy(inputs)
    source = copy.deepcopy(altered[2]["sources"][0])
    source.update(sourceId="unused-fixture", retainedPath="verification/fixtures/unused.json")
    altered[2]["sources"].append(source)
    altered[3][source["retainedPath"]] = source["sha256"]
    bundle = exporter.build_bundle(*altered)
    report = json.loads(bundle["report.json"])
    assert source["retainedPath"] in report["inputs"]
    assert all(source["sourceId"] != row["sourceId"] for entry in report["entries"]
               for field in entry["fieldSources"].values() for row in field["sources"])


def check_envelope_contract(bundle):
    mutations = [
        lambda d: d["profile.json"]["payloadSchema"]["properties"]["name"].update(type="integer"),
        lambda d: d["profile.json"].pop("payloadSchema"),
        lambda d: d["report.json"].update(inputs={"collector_catalogue.json": "0" * 64}),
        lambda d: d["report.json"]["inputs"].pop("verification/fixtures/malie_contract.json"),
        lambda d: d["report.json"]["inputs"].update({"collector_catalogue.json": "1" * 64}),
    ]
    for mutate in mutations:
        documents = {name: json.loads(raw) for name, raw in bundle.items()}
        mutate(documents)
        documents["report.json"]["profileSha256"] = exporter.digest(documents["profile.json"])
        try:
            exporter.validate_bundle({name: exporter.canonical_bytes(value) for name, value in documents.items()})
        except exporter.ExportError:
            pass
        else:
            raise AssertionError("accepted inconsistent published schema or input accounting")


def check_entry_digests(inputs):
    altered = copy.deepcopy(inputs)
    altered[1]["items"][1]["localSetId"] = "LOCALSET:outside"
    bundle = exporter.build_bundle(*altered)
    report = json.loads(bundle["report.json"])
    mutations = [
        lambda r: r["entries"][0]["fieldSources"]["/name"]["sources"][0].update(
            providerId="other", url="https://example.invalid/other", authorityTier=5, licenseOrTerms="other"),
        lambda r: r["entries"][1].update(reasons=[{"status": "outside-profile", "code": "unrelated",
                                                  "field": "/name", "message": "Unrelated but well-formed."}]),
    ]
    for mutate in mutations:
        broken = copy.deepcopy(report)
        mutate(broken)
        try:
            exporter.validate_bundle({**bundle, "report.json": exporter.canonical_bytes(broken)})
        except exporter.ExportError as error:
            assert "entry digest" in str(error)
        else:
            raise AssertionError("accepted replaced provenance or reasons")


def check_identity_digests(inputs):
    for withheld in (False, True):
        altered = copy.deepcopy(inputs)
        if withheld:
            altered[1]["items"][0]["finish"] = "unknown"
        bundle = exporter.build_bundle(*altered)
        report = json.loads(bundle["report.json"])
        identity = report["entries"][0]["identity"]
        mutations = [(field, "changed" if value is None else None) for field, value in identity.items()]
        mutations.extend([("localSetId", "LOCALSET:WEST:SVP"), ("finish", "holo"),
                          ("distribution", {"kind": "elite-trainer-box"}),
                          ("physicalSources", [{"sourceId": "unrelated-printing"}])])
        for field, value in mutations:
            broken = copy.deepcopy(report)
            broken["entries"][0]["identity"][field] = value
            try:
                exporter.validate_bundle({**bundle, "report.json": exporter.canonical_bytes(broken)})
            except exporter.ExportError:
                pass
            else:
                raise AssertionError(f"accepted changed identity field {field}; withheld={withheld}")


def check_foil_applicability(inputs):
    for finish in ("holo", "reverse-holo", "mirror-holo"):
        altered = copy.deepcopy(inputs)
        altered[1]["items"][0]["finish"] = finish
        rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
        assert rows[0]["status"] == "needs-mapping", finish
        assert any(r["code"] == "foil-applicability-conflict" for r in rows[0]["reasons"])
        assert not any(r["code"] == "missing-foil-mapping" for r in rows[0]["reasons"])
        assert rows[1]["status"] == "exported", "explicit non-foil sibling no longer exports"
        altered[2]["observations"] = [r for r in altered[2]["observations"] if r["field"] != "/foil"]
        rows = json.loads(exporter.build_bundle(*altered)["report.json"])["entries"]
        assert rows[0]["status"] == "needs-evidence"
        assert any(r["code"] == "missing-foil-mapping" for r in rows[0]["reasons"])


def main():
    profile = json.loads((ROOT / "verification/malie_profile.json").read_text(encoding="utf-8"))
    fixture = json.loads((ROOT / "verification/fixtures/malie_contract.json").read_text(encoding="utf-8"))
    assert fixture["fixtureKind"] == "synthetic-contract-only"
    valid = fixture["validPayload"]
    assert exporter.payload_errors(valid, profile) == []
    for number in fixture["numberCases"]:
        card = copy.deepcopy(valid)
        card["collector_number"] = number
        assert exporter.payload_errors(card, profile) == [], number
        assert json.loads(exporter.canonical_bytes(card))["collector_number"] == number
    # Mutation expectations are specified independently of the validator's branches.
    invalid = [
        lambda c: c.pop("copyright"),
        lambda c: c.update(retreat=None),
        lambda c: c.update(hp=True),
        lambda c: c.update(name="   "),
        lambda c: c.update(lang="pt-BR"),
        lambda c: c.update(foil={"type": "unknown", "mask": "REVERSE"}),
        lambda c: c["text"][1].update(cost=[]),
        lambda c: c["text"][1].update(cost=["FREE", "COLORLESS"]),
        lambda c: c["text"][1]["damage"].update(amount=False),
        lambda c: c["text"][1]["damage"].update(suffix="*"),
        lambda c: c["rarity"].update(icon="SOLID_CIRCLE"),
        lambda c: c["collector_number"].update(numeric=2),
        lambda c: c["collector_number"].update(full="1/165"),
        lambda c: c["copyright"].update(year=2022),
        lambda c: c.update(tags=["FUTURE", "FUTURE"]),
        lambda c: c.update(images={}),
        lambda c: c.update(subtype="ITEM"),
        lambda c: c["weakness"].update(extra="unsupported"),
    ]
    for index, mutate in enumerate(invalid):
        card = copy.deepcopy(valid)
        mutate(card)
        assert exporter.payload_errors(card, profile), f"accepted invalid synthetic case {index}"
    rendered = exporter.canonical_bytes(valid)
    assert not rendered.startswith(b"\xef\xbb\xbf") and b"\r" not in rendered
    assert rendered.endswith(b"\n") and b'"retreat": 0' in rendered
    assert exporter.canonical_bytes(dict(reversed(list(valid.items())))) == rendered
    incomplete = copy.deepcopy(valid)
    incomplete.pop("text")
    incomplete["copyright"]["year"] = 2022
    incomplete["collector_number"]["numeric"] = 9
    incomplete["hp"] = True
    errors = exporter.observation_value_errors(incomplete, profile)
    assert any("copyright.year" in error for error in errors), errors
    assert any("collector_number.numeric" in error for error in errors), errors
    assert len(errors) >= 3, errors
    check_bundle_contract(profile, fixture)
    print(f"Malie payload contract: {len(invalid)} invalid cases rejected; prefixes, zero and canonical bytes preserved.")


if __name__ == "__main__":
    main()
