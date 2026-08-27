#!/usr/bin/env python3
"""Small end-to-end regression for the physical-card evidence loop (#269)."""

from __future__ import annotations

import json
import importlib.util
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(name: str) -> dict:
    return json.loads((ROOT / "verification" / name).read_text(encoding="utf-8"))


def observation_signature(specimen: dict) -> tuple:
    observation = specimen["physicalObservation"]
    markings = observation.get("markings")
    if isinstance(markings, list):
        markings = tuple(json.dumps(marking, sort_keys=True) for marking in markings)
    return (
        specimen["setCode"],
        specimen["number"].split("/", 1)[0],
        specimen["language"],
        specimen["variant"],
        observation.get("finish"),
        observation.get("edition"),
        markings,
        observation.get("foilPattern"),
        observation.get("cardSize"),
    )


def finish_projector():
    spec = importlib.util.spec_from_file_location("finishes", ROOT / "scripts" / "finishes.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    specimens = read("specimens.json")["specimens"]
    fixture = [row for row in specimens if row["specimenId"] in {
        "SPEC-0040", "SPEC-0041", "SPEC-0042", "SPEC-0043", "SPEC-0044",
    }]
    assert len(fixture) == 5, "#269 fixture must contain five physical specimens"
    assert len({observation_signature(row) for row in fixture}) == 4

    # A missing edition observation remains missing; the projector must not turn the absence of
    # a stamp into an Unlimited claim.
    no_edition = dict(fixture[0])
    no_edition["physicalObservation"] = {
        key: value for key, value in fixture[0]["physicalObservation"].items()
        if key != "edition"
    }
    assert "edition" not in finish_projector().specimen_printing(no_edition)

    by_signature: dict[tuple, list[str]] = defaultdict(list)
    for specimen in fixture:
        observation = specimen["physicalObservation"]
        assert observation.get("finish") in {"holo", "non-holo"}
        assert observation.get("edition") in {"1st Edition", "Unlimited"}
        if observation["edition"] == "Unlimited":
            assert "explicitly identified" in observation["basis"]
        by_signature[observation_signature(specimen)].append(specimen["specimenId"])
    assert sorted(by_signature.values(), key=lambda ids: ids[0]) == [
        ["SPEC-0040"], ["SPEC-0041"], ["SPEC-0042", "SPEC-0043"], ["SPEC-0044"],
    ]

    finish_units = read("finish_units.json")["units"]
    dutch = {
        (unit["number"], printing["edition"]): printing
        for unit in finish_units
        if unit["setCode"] == "JU" and unit["language"] == "Dutch"
        and unit["number"] in {"11", "27"}
        for printing in unit["printings"]
        if printing.get("edition") in {"1st Edition", "Unlimited"}
    }
    assert set(dutch) == {
        ("11", "1st Edition"), ("11", "Unlimited"),
        ("27", "1st Edition"), ("27", "Unlimited"),
    }
    assert len(dutch[("27", "1st Edition")]["sources"]) == 2
    assert dutch[("27", "1st Edition")]["specimenIds"] == ["SPEC-0042", "SPEC-0043"]

    projector = finish_projector()
    seller_source = projector.specimen_printing(fixture[2])["sources"][0]
    assert seller_source["sourceType"] == "Seller listing photograph"
    portuguese_owner_confirmed = {
        row["specimenId"]: projector.specimen_printing(row)
        for row in specimens
        if row["specimenId"] in {"SPEC-0053", "SPEC-0054", "SPEC-0055", "SPEC-0056"}
    }
    assert set(portuguese_owner_confirmed) == {
        "SPEC-0053", "SPEC-0054", "SPEC-0055", "SPEC-0056"
    }
    for specimen_id, printing in portuguese_owner_confirmed.items():
        assert [source["sourceType"] for source in printing["sources"]] == [
            "Seller listing photograph", "Owner attestation (domain expert)"
        ]
        owner_evidence = printing["sources"][1]["evidence"]
        expected_property = "edition" if specimen_id == "SPEC-0055" else "finish"
        assert expected_property in owner_evidence
        assert printing["sources"][1]["claimFields"] == [expected_property]
        expected_photo_fields = ["identity", "finish"] if specimen_id == "SPEC-0055" else ["identity"]
        assert printing["sources"][0]["claimFields"] == expected_photo_fields

    source_registry = read("source_registry.json")["evidence"]
    target_specimens = {
        row["specimenId"]: row for row in specimens if row["specimenId"] in portuguese_owner_confirmed
    }
    target_urls = {row["photographSource"] for row in target_specimens.values()}
    seller_dimensions = {
        source["canonicalUrl"]: source["dimensions"]
        for source in source_registry
        if source.get("canonicalUrl") in target_urls
    }
    assert seller_dimensions == {
        target_specimens["SPEC-0053"]["photographSource"]: ["identity"],
        target_specimens["SPEC-0054"]["photographSource"]: ["identity"],
        target_specimens["SPEC-0055"]["photographSource"]: ["finish", "identity"],
        target_specimens["SPEC-0056"]["photographSource"]: ["identity"],
    }
    omitted_size = dict(fixture[0])
    omitted_size["physicalObservation"] = {
        key: value for key, value in fixture[0]["physicalObservation"].items()
        if key != "cardSize"
    }
    assert projector.specimen_printing(omitted_size)["cardSize"] == "unknown"
    merged_without_image = projector.specimen_printing(fixture[0])
    merged_without_image.pop("image")
    merged_without_image["_origin"] = "auto"
    merged: list[dict] = [merged_without_image]
    projector.add_printing(merged, projector.specimen_printing(fixture[0]))
    assert merged[0]["image"] == "verification/specimens/SPEC-0040.png"
    assert merged[0]["_origin"] == "specimen"
    patterned = dict(fixture[0])
    patterned["physicalObservation"] = {
        **fixture[0]["physicalObservation"], "foilPattern": "Poké Ball mirror"
    }
    assert projector.specimen_printing(patterned)["foilPattern"] == "poke-ball"
    assert projector.specimen_markings({
        "markings": "STAFF", "markingRole": "distribution-promo"
    }) == [{"kind": "staff", "role": "distribution-promo", "text": "Staff"}]
    mp1_specimen = next(row for row in specimens if row["specimenId"] == "SPEC-0025")
    mp1_candidate = projector.specimen_printing(mp1_specimen)
    assert mp1_candidate is not None
    assert projector.merge_curated_specimen_identity(
        mp1_candidate,
        {
            "finish": "non-holo", "mappedVariants": ["base"],
            "distribution": {"kind": "fixed-deck", "text": "Start Deck 100"},
            "sourceRefs": ["snkrdunk-mp1-012"],
        },
        {"snkrdunk-mp1-012": {"url": mp1_specimen["photographSource"]}},
    )
    assert mp1_candidate["distribution"]["kind"] == "fixed-deck"
    mp1 = next(unit for unit in finish_units
               if unit["setCode"] == "mP1" and unit["number"] == "012"
               and unit["language"] == "Japanese")
    assert len(mp1["printings"]) == 1
    assert mp1["printings"][0]["specimenIds"] == ["SPEC-0025"]
    assert mp1["printings"][0]["distribution"]["kind"] == "fixed-deck"
    indonesian = next(unit for unit in finish_units
                      if unit["setCode"] == "SV-P/ID" and unit["number"] == "117"
                      and unit["language"] == "Indonesian")
    assert len(indonesian["printings"]) == 2
    assert {printing["foilPattern"] for printing in indonesian["printings"]} == {
        "poke-ball", "master-ball"
    }
    conflict = dict(fixture[0])
    conflict["physicalObservation"] = {
        **fixture[0]["physicalObservation"],
        "conflictsWith": ["SPEC-0044"],
    }
    conflicted = projector.specimen_printing(conflict)
    assert conflicted["conflictsWith"] == ["SPEC-0044"]
    reverse = projector.add_reverse_specimen_conflicts(
        projector.specimen_printing(fixture[1]), "SPEC-0041", {"SPEC-0041": {"SPEC-0040"}}
    )
    assert reverse["conflictsWith"] == ["SPEC-0040"]
    projected: list[dict] = []
    projector.add_printing(projected, conflicted)
    assert projected[0]["verificationStatus"] == "pending"
    assert projected[0]["conflictsWith"] == ["SPEC-0044"]
    # A later clean candidate must not promote a printing whose earlier specimen conflict is
    # still present; the conflict remains pending until explicitly resolved.
    clean_candidate = dict(projected[0])
    clean_candidate.pop("conflictsWith")
    clean_candidate["verificationStatus"] = "confirmed"
    projector.add_printing(projected, clean_candidate)
    assert projected[0]["verificationStatus"] == "pending"
    assert projected[0]["conflictsWith"] == ["SPEC-0044"]
    projector.validate_specimen_conflicts({"specimens": [
        {"specimenId": "SPEC-A", "physicalObservation": {"conflictsWith": ["SPEC-B"]}},
        {"specimenId": "SPEC-B"},
    ]})
    try:
        projector.validate_specimen_conflicts({
            "specimens": [{"specimenId": "SPEC-A", "physicalObservation": {
                "conflictsWith": ["SPEC-MISSING"]
            }}]
        })
    except ValueError:
        pass
    else:
        raise AssertionError("unknown conflict target must fail closed")

    graph = read("authoritative_graph.json")
    physical_ids = {
        row["entityId"] for row in graph["entities"]
        if row["entityType"] == "physical-printing"
    }
    assert {"PHYSICAL:F0167-P01", "PHYSICAL:F0167-P02",
            "PHYSICAL:F0174-P01", "PHYSICAL:F0174-P02"} <= physical_ids

    print("physical evidence workflow regression passed: 5 specimens -> 4 printings")


if __name__ == "__main__":
    main()
