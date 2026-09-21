#!/usr/bin/env python3
"""Real pilot field evidence and adversarial provenance-boundary checks (#386)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import card_content as content


def rejects(document, mutate, expected):
    broken = copy.deepcopy(document)
    mutate(broken)
    try:
        content.validate(broken)
    except ValueError as error:
        assert expected in str(error), str(error)
    else:
        raise AssertionError(f"accepted corrupt evidence: {expected}")


def main():
    document = content.load()
    rows = document["observations"]
    # Independently transcribed expectations, not values produced by the exporter.
    expected = {
        "PHYSICAL:F0225-P01": ("en-US", "Snorlax", "BASIC", "Illus. HYOGONOSUKE", "Thudding Press"),
        "PHYSICAL:F0227-P01": ("de-DE", "Relaxo", "BASIS", "Illustr. HYOGONOSUKE", "Prallpresse"),
    }
    required = {
        "/lang", "/card_type", "/name", "/artists", "/regulation_mark", "/set_icon",
        "/collector_number", "/rarity", "/copyright", "/size", "/back", "/text",
        "/stage", "/stage_text", "/hp", "/types", "/weakness", "/retreat", "/flavor_text",
    }
    for printing, (lang, name, stage, credit, attack) in expected.items():
        fields = {row["field"]: row for row in rows if printing in row["physicalPrintingIds"]}
        assert required <= fields.keys()
        assert all(fields[field]["state"] == "known" for field in required)
        values = {field: row.get("value") for field, row in fields.items()}
        assert (values["/lang"], values["/name"], values["/stage_text"], values["/artists"]["text"],
                values["/text"][1]["name"]) == (lang, name, stage, credit, attack)
        assert values["/collector_number"] == {"full": "143/165", "numerator": "143", "denominator": "165", "numeric": 143}
        assert values["/hp"] == 150 and values["/retreat"] == 4
        assert values["/back"] == "POKEMON_1999" and values["/size"] == "STANDARD"
        assert values["/text"][1]["damage"] == {"amount": 130}
        for field in ("/foil", "/subtype", "/subtitle", "/tags", "/resistance"):
            assert fields[field]["state"] == "not-applicable" and "value" not in fields[field]
    reverse = next(row for row in rows if row["field"] == "/foil" and row["state"] == "known")
    assert reverse["physicalPrintingIds"] == ["PHYSICAL:F0225-P02"]
    assert reverse["value"] == {"type": "FLAT_SILVER", "mask": "REVERSE"}

    rejects(document, lambda d: d["sources"][0].update(sha256="0" * 64), "source digest mismatch")
    rejects(document, lambda d: d["sources"][0].update(retainedPath="../outside.png"), "unsafe retained path")
    rejects(document, lambda d: d["sources"][0].update(providerId="pokemon-official"), "provider mismatch")
    rejects(document, lambda d: d["observations"][0].update(physicalPrintingIds=["PHYSICAL:F0227-P01"]),
            "printing does not belong to release")
    rejects(document, lambda d: d["observations"][0].update(sourceIds=["tcgdex-mew143-de-front"]),
            "source outside reviewed field/printing scope")
    rejects(document, lambda d: d["sources"][0]["scope"].update(fields=["/back"]),
            "unsupported source capability")
    rejects(document, lambda d: d["observations"][0].update(sourceIds=[]), "expected nonempty string array")
    rejects(document, lambda d: d["observations"][0].update(state="not-applicable"), "value/state mismatch")
    rejects(document, lambda d: d["observations"].append(copy.deepcopy(d["observations"][0])), "duplicate observationId")
    rejects(document, lambda d: d["sources"][1]["scope"]["recordBindings"][0].update(arrayIndex=275),
            "reference variant mismatch")
    rejects(document, lambda d: next(r for r in d["observations"] if r["field"] == "/back").update(value="invented"),
            "value differs from bound reference")
    rejects(document, lambda d: d["sources"][1]["scope"].update(language="de-DE"),
            "reference language does not match target profile")
    unresolved = copy.deepcopy(document)
    sid = unresolved["sources"][1]["sourceId"]
    unresolved["sources"][1]["scope"].pop("recordBindings")
    for row in unresolved["observations"]:
        if sid in row["sourceIds"]:
            row.update(state="blocked-by-source", nextStep="Retrieve and review the exact localized record.")
            row.pop("value", None)
    content.validate(unresolved)  # A blocked source is retained uncertainty, not an accepted assertion.
    print("Card-content checks passed: two real languages, exact variant scope, retained hashes and rejected provenance corruptions.")
    print("This checks accepted field inputs; complete export conformance remains the exporter/integration gate.")


if __name__ == "__main__":
    main()
