#!/usr/bin/env python3
"""Real pilot acceptance and preservation checks over the committed export bundle."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import malie_export as exporter

EXPECTED = {
    "item-345ada2b-32ce-5fa1-8132-308cba7b3c54": ("PHYSICAL:F0225-P01", "en-US", "Snorlax", None),
    "item-86d6224a-18c1-584c-96bb-5eaf92f6c2ec": (
        "PHYSICAL:F0225-P02", "en-US", "Snorlax", {"type": "FLAT_SILVER", "mask": "REVERSE"}),
    "item-9781d666-3475-5612-86d6-0e0a3c9e0f96": ("PHYSICAL:F0227-P01", "de-DE", "Relaxo", None),
}
WITHHELD = {
    "item-2645c53d-7c6e-5b47-ad37-51c2e959df6e": "outside-profile",
    "item-85d569de-bd2a-51f6-a00e-7d870e35b60f": "needs-evidence",
    "item-d8a77dec-1a8d-55a7-910c-7f72d0e28085": "needs-evidence",
}


def snapshot(paths):
    return {path: (hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                   (ROOT / path).stat().st_mtime_ns) for path in paths}


def check_real_values(cards, report):
    entries = {row["itemId"]: row for row in report["entries"]}
    assert set(entries) == EXPECTED.keys() | WITHHELD.keys()
    assert len(cards) == 3 and len(entries) == 6
    assert report["summary"] == {"selected": 6, "exported": 3, "outside-profile": 1,
                                  "needs-evidence": 2, "needs-mapping": 0, "blocked-by-source": 0}
    for iid, (printing, language, name, foil) in EXPECTED.items():
        entry = entries[iid]
        assert entry["status"] == "exported" and entry["physicalPrintingId"] == printing
        card = cards[entry["cardIndex"]]
        assert (card["lang"], card["name"], card.get("foil")) == (language, name, foil)
        assert card["collector_number"] == {"full": "143/165", "numerator": "143", "denominator": "165", "numeric": 143}
        assert card["hp"] == 150 and card["retreat"] == 4
        assert card["size"] == "STANDARD" and card["back"] == "POKEMON_1999"
        assert card["rarity"] == {"designation": "UNCOMMON", "icon": "SOLID_DIAMOND"}
        assert card["text"][1]["damage"] == {"amount": 130}
        assert card["text"][1]["cost"] == ["COLORLESS", "COLORLESS", "COLORLESS"]
        if language == "de-DE":
            assert card["stage_text"] == "BASIS" and card["text"][1]["name"] == "Prallpresse"
            assert card["artists"]["text"] == "Illustr. HYOGONOSUKE"
            assert card["copyright"]["text"] == "©2023 Pokémon/Nintendo/Creatures/GAME FREAK"
        else:
            assert card["stage_text"] == "BASIC" and card["text"][1]["name"] == "Thudding Press"
            assert card["artists"]["text"] == "Illus. HYOGONOSUKE"
        providers = {source["providerId"] for field in entry["fieldSources"].values() for source in field["sources"]}
        assert providers == {"tcgdex", "malie"}
    for iid, status in WITHHELD.items():
        assert entries[iid]["status"] == status and entries[iid]["reasons"]
        assert "cardIndex" not in entries[iid]
    assert entries["item-2645c53d-7c6e-5b47-ad37-51c2e959df6e"]["physicalPrintingId"] is None
    for iid in list(WITHHELD)[1:]:
        assert any(reason["field"] == "/identity/distribution" for reason in entries[iid]["reasons"])


def rejects_bundle(bundle, mutate):
    changed = {name: json.loads(raw) for name, raw in bundle.items()}
    mutate(changed)
    try:
        exporter.validate_bundle({name: exporter.canonical_bytes(value) for name, value in changed.items()})
    except (ValueError, KeyError, TypeError):
        return
    raise AssertionError("accepted corrupted real bundle")


def check_corruptions(bundle):
    rejects_bundle(bundle, lambda b: b["report.json"]["entries"].pop())
    rejects_bundle(bundle, lambda b: b["report.json"]["entries"][1].update(physicalPrintingId="PHYSICAL:F0227-P01"))
    rejects_bundle(bundle, lambda b: b["report.json"]["entries"][1]["identity"].update(localizationId="LOCALIZATION:WEST:de"))
    rejects_bundle(bundle, lambda b: b["cards.json"][1].pop("foil"))
    rejects_bundle(bundle, lambda b: b["profile.json"].update(profileId="stale-profile"))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)
        exporter.write_outputs(path, bundle)
        report = json.loads(bundle["report.json"])
        report["inputs"]["collector_catalogue.json"] = "0" * 64
        (path / "report.json").write_bytes(exporter.canonical_bytes(report))
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in path.iterdir()}
        try:
            exporter.check_outputs(path, bundle)
        except ValueError:
            pass
        else:
            raise AssertionError("stale input digest accepted")
        assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in path.iterdir()}


def main():
    bundle = {name: (ROOT / "exports/malie" / name).read_bytes()
              for name in ("cards.json", "report.json", "profile.json")}
    report = json.loads(bundle["report.json"])
    paths = set(report["inputs"]) | {"exports/malie/" + name for name in bundle} | {
        "collector_migrations.json", "collector_catalogue.fixture.json", "snoredex-tracker-template.sqlite"}
    before = snapshot(paths)
    inputs = exporter.read_inputs()
    assert exporter.build_bundle(*inputs) == bundle
    exporter.validate_bundle(bundle)
    check_real_values(json.loads(bundle["cards.json"]), report)
    check_corruptions(bundle)
    for _ in range(2):
        subprocess.run([sys.executable, str(ROOT / "scripts/malie_export.py"), "--check"],
                       cwd=ROOT.parent, check=True, capture_output=True)
    invalid = subprocess.run([sys.executable, str(ROOT / "scripts/malie_export.py"), "--write", "--check"],
                             cwd=ROOT.parent, capture_output=True)
    assert invalid.returncode != 0
    assert snapshot(paths) == before, "pure export/check changed canonical or output files/metadata"
    print("Real Malie pilot: 3 printings, 2 languages, all 6 inputs accounted; corruption and preservation checks passed.")


if __name__ == "__main__":
    main()
