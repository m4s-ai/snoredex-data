#!/usr/bin/env python3
"""Independent, isolated consumption and staged-package integrity regressions."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import publish

NAMES = ("cards.json", "report.json", "profile.json")


def run_reader(script, bundle):
    return subprocess.run([sys.executable, "-I", str(script), str(bundle)], cwd=script.parent,
                          capture_output=True, encoding="utf-8")


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def expected_pilot(result):
    assert result["profileId"] == "snoredex-malie-sv-pilot/1"
    assert result["summary"] == {"selected": 6, "exported": 3, "needs-evidence": 2,
                                 "outside-profile": 1, "needs-mapping": 0, "blocked-by-source": 0}
    cards = {row["physicalPrintingId"]: row["card"] for row in result["items"] if "card" in row}
    assert set(cards) == {"PHYSICAL:F0225-P01", "PHYSICAL:F0225-P02", "PHYSICAL:F0227-P01"}
    assert cards["PHYSICAL:F0225-P01"]["name"] == "Snorlax"
    assert "foil" not in cards["PHYSICAL:F0225-P01"]
    assert cards["PHYSICAL:F0225-P02"]["foil"] == {"type": "FLAT_SILVER", "mask": "REVERSE"}
    german = cards["PHYSICAL:F0227-P01"]
    assert (german["name"], german["lang"], german["stage_text"]) == ("Relaxo", "de-DE", "BASIS")
    assert german["collector_number"]["full"] == "143/165"
    assert german["artists"]["text"] == "Illustr. HYOGONOSUKE"
    assert german["copyright"]["text"] == "©2023 Pokémon/Nintendo/Creatures/GAME FREAK"
    assert german["text"][1]["name"] == "Prallpresse" and german["text"][1]["damage"]["amount"] == 130
    withheld = {row["physicalPrintingId"]: row for row in result["items"] if "card" not in row}
    assert set(withheld) == {None, "PHYSICAL:F0507-P01", "PHYSICAL:F0507-P02"}
    assert withheld[None]["status"] == "outside-profile"
    assert withheld["PHYSICAL:F0507-P01"]["identity"]["distribution"]["kind"] == "elite-trainer-box"
    assert withheld["PHYSICAL:F0507-P02"]["identity"]["distribution"]["kind"] == "pokemon-center-elite-trainer-box"
    assert withheld["PHYSICAL:F0507-P02"]["identity"]["markings"][0]["role"] == "distribution-promo"
    assert all(row["reasons"] for row in withheld.values())


def corruptions(script, bundle, original):
    mutations = [
        lambda d: d["report.json"]["entries"].pop(),
        lambda d: d["report.json"]["entries"][1].update(physicalPrintingId="PHYSICAL:F0227-P01"),
        lambda d: d["profile.json"].update(profileId="stale-profile"),
        lambda d: d["cards.json"][1].pop("foil"),
        lambda d: d["report.json"]["entries"][0].pop("identity"),
        lambda d: d["report.json"]["entries"][0]["identity"].update(localizationId="LOCALIZATION:WEST:en"),
        lambda d: d["report.json"]["entries"][0].pop("fieldSources"),
        lambda d: d["report.json"]["entries"][0].update(reasons=[{"status": "outside-profile"}]),
        lambda d: d["report.json"]["entries"][2].update(identity=d["report.json"]["entries"][5]["identity"]),
        lambda d: d["report.json"]["entries"][1]["identity"].update(localSetId="LOCALSET:WEST:SVP"),
        lambda d: d["report.json"]["entries"][2]["identity"].update(physicalSources=[]),
    ]
    for mutate in mutations:
        docs = {name: json.loads(raw) for name, raw in original.items()}
        mutate(docs)
        for name, value in docs.items():
            (bundle / name).write_bytes(canonical(value))
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in bundle.iterdir()}
        assert run_reader(script, bundle).returncode != 0
        assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in bundle.iterdir()}
        assert publish.malie_problems(bundle.parent.parent)
    for name, raw in original.items():
        (bundle / name).write_bytes(raw)
    # Keep hashes internally consistent to exercise identity/finish guards themselves.
    for field, value in (("lang", "de-DE"), ("foil", None)):
        docs = {name: json.loads(raw) for name, raw in original.items()}
        card = docs["cards.json"][1]
        if value is None:
            card.pop(field)
        else:
            card[field] = value
        refresh_bindings(docs)
        for name, value in docs.items():
            (bundle / name).write_bytes(canonical(value))
        assert run_reader(script, bundle).returncode != 0
    for name, raw in original.items():
        (bundle / name).write_bytes(raw)
    (bundle / "profile.json").unlink()
    assert run_reader(script, bundle).returncode != 0
    assert publish.malie_problems(bundle.parent.parent)


def refresh_bindings(docs):
    report, profile = docs["report.json"], docs["profile.json"]
    targets = {target["itemId"]: target for target in profile["pilot"]}
    for entry in report["entries"]:
        if "cardIndex" in entry:
            entry["cardSha256"] = hashlib.sha256(canonical(docs["cards.json"][entry["cardIndex"]])).hexdigest()
        targets[entry["itemId"]]["entrySha256"] = hashlib.sha256(canonical(entry)).hexdigest()
    report["cardsSha256"] = hashlib.sha256(canonical(docs["cards.json"])).hexdigest()
    report["profileSha256"] = hashlib.sha256(canonical(profile)).hexdigest()


def semantic_corruptions(script, bundle, original):
    """A coherently rehashed package must still satisfy payload/evidence rules."""
    mutations = [
        remove_name_contract,
        replace_pilot_identity,
        lambda d: d["profile.json"]["languages"].update({"LOCALIZATION:WEST:en": "de-DE"}),
        lambda d: d["report.json"].update(inputs={"collector_catalogue.json": "0" * 64}),
        lambda d: d["cards.json"][0].pop("name"),
        lambda d: d["cards.json"][0].pop("stage_text"),
        lambda d: d["cards.json"][0].update(hp=True),
        lambda d: d["cards.json"][0].update(retreat=None),
        lambda d: d["cards.json"][0].update(types=["INVALID"]),
        lambda d: d["cards.json"][0].update(unexpected="field"),
        lambda d: d["cards.json"][0]["text"][0].pop("text"),
        lambda d: d["cards.json"][0]["text"][1].update(cost=[]),
        lambda d: d["cards.json"][0]["text"][1].update(cost=["FREE", "COLORLESS"]),
        lambda d: d["cards.json"][0]["collector_number"].update(numeric=42),
        lambda d: d["cards.json"][0]["rarity"].update(icon="SOLID_STAR"),
        lambda d: d["cards.json"][0]["copyright"].update(year=1999),
        lambda d: d["report.json"]["entries"][1]["fieldSources"]["/name"].update(
            observations=[], sources=[], covers=[]),
        lambda d: d["report.json"]["entries"][1]["fieldSources"]["/name"]["observations"][0].update(sourceIds=["missing"]),
        lambda d: d["report.json"]["entries"][1]["fieldSources"]["/name"]["observations"][0].update(state="not-a-state"),
        lambda d: d["report.json"]["entries"][1]["fieldSources"]["/name"]["sources"][0]["scope"].update(physicalPrintingIds=[]),
        lambda d: d["report.json"]["entries"][1]["fieldSources"]["/name"]["sources"][0].update(sha256="bad"),
        lambda d: d["report.json"]["entries"][1]["fieldSources"]["/text"].update(covers=[]),
    ]
    for mutate in mutations:
        docs = {name: json.loads(raw) for name, raw in original.items()}
        mutate(docs)
        refresh_bindings(docs)
        for name, value in docs.items():
            (bundle / name).write_bytes(canonical(value))
        assert run_reader(script, bundle).returncode != 0
    for name, raw in original.items():
        (bundle / name).write_bytes(raw)


def replace_pilot_identity(documents):
    old, new = "PHYSICAL:F0225-P01", "PHYSICAL:FAKE-P99"
    for target in documents["profile.json"]["pilot"]:
        if target["physicalPrintingId"] == old:
            target["physicalPrintingId"] = new
    for entry in documents["report.json"]["entries"]:
        if entry["physicalPrintingId"] == old:
            entry["physicalPrintingId"] = new
            entry["identity"]["physicalPrintingId"] = new
        for provenance in entry["fieldSources"].values():
            for source in provenance["sources"]:
                source["scope"]["physicalPrintingIds"] = [
                    new if value == old else value for value in source["scope"]["physicalPrintingIds"]]


def remove_name_contract(documents):
    documents["cards.json"][0].pop("name")
    documents["profile.json"]["payloadSchema"]["required"].remove("name")
    field = documents["report.json"]["entries"][1]["fieldSources"]["/name"]
    field["covers"] = []
    for observation in field["observations"]:
        observation["state"] = "not-applicable"


def check_failed_build_preserves_stage(directory):
    source = directory / "missing-source"
    stage = source / "_site-preserved"
    stage.mkdir(parents=True)
    sentinel = stage / "existing.txt"
    sentinel.write_bytes(b"existing staged package")
    before = (sentinel.read_bytes(), sentinel.stat().st_mtime_ns)
    saved = publish.ROOT
    try:
        publish.ROOT = source
        try:
            publish.build(stage)
        except (OSError, ValueError):
            pass
        else:
            raise AssertionError("built a package without its required source bundle")
        assert (sentinel.read_bytes(), sentinel.stat().st_mtime_ns) == before
    finally:
        publish.ROOT = saved


def main():
    original = {name: (ROOT / "exports/malie" / name).read_bytes() for name in NAMES}
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        script = directory / "reader.py"
        shutil.copyfile(ROOT / "scripts/malie_consumer.py", script)
        bundle = directory / "exports/malie"
        bundle.mkdir(parents=True)
        for name, raw in original.items():
            (bundle / name).write_bytes(raw)
        # The isolated interpreter has only the standalone reader and three inputs.
        assert sorted(p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()) == [
            "exports/malie/cards.json", "exports/malie/profile.json", "exports/malie/report.json", "reader.py"]
        result = run_reader(script, bundle)
        assert result.returncode == 0, result.stderr
        decoded = json.loads(result.stdout)
        expected_pilot(decoded)
        assert decoded["digests"] == {name: hashlib.sha256(raw).hexdigest() for name, raw in original.items()}
        assert not publish.malie_problems(directory)
        semantic_corruptions(script, bundle, original)
        corruptions(script, bundle, original)
        check_failed_build_preserves_stage(directory)
    print("Standalone Malie consumer passed with only 3 bundle inputs: exact pilot values, IDs, gaps, digests and corruption rejection.")


if __name__ == "__main__":
    main()
