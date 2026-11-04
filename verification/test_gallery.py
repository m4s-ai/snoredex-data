"""Regression tests for the artwork gallery projection."""

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from collector_catalogue import rejected_release_finishes
from gallery import gallery_cards, release_groups

# The standard-library site module is loaded at Python startup.
spec = spec_from_file_location("snoredex_site", ROOT / "scripts/site.py")
site = module_from_spec(spec)
spec.loader.exec_module(site)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main():
    catalogue = load("collector_catalogue.json")
    artwork = load("verification/artwork_review_projection.json")
    review = load("site/gallery-review.json")
    derivatives = load("verification/artwork_derivative_manifest.json")["sources"]
    rejected = rejected_release_finishes(catalogue["items"])
    verdicts = {row["unitId"]: row["applicationStatus"] for row in
                load("verification/evidence_semantics.json")["units"]}

    def project(excluded):
        return gallery_cards(catalogue, artwork, review, derivatives, [], site.release_sort, excluded, verdicts)

    cards = project(rejected)
    specimen = next(card for card in cards if card["imageSource"] == "verification/specimens/SPEC-0601.png")
    assert specimen["imageScope"] == "exact-printing"
    assert specimen["preview"] == derivatives[specimen["imageSource"]]["preview"]["path"]
    representative = {card["id"] for card in cards if card["imageScope"] == "representative"}
    assert representative == review["representativeImages"].keys()
    assert len({card["id"] for card in cards}) == len(cards)
    artwork_numbers = list(dict.fromkeys(card["artworkNumber"] for card in cards))
    assert artwork_numbers == list(range(1, len(artwork_numbers) + 1))
    assert [c["artworkNumber"] for c in cards] == sorted(c["artworkNumber"] for c in cards)
    positions = [i for i, card in enumerate(cards) if card["group"] == "jungle-snorlax"]
    assert positions[0] == 0
    assert positions == list(range(positions[0], positions[-1] + 1))
    jungle = [cards[i] for i in positions]
    assert {c["artworkNumber"] for c in jungle} == {1}
    assert jungle[0]["setCode"] == "PJU"
    assert {"1st Edition", "Unlimited"} <= {c["edition"] for c in jungle if c["setCode"] == "JU"}
    assert {c["date"] for c in jungle if c["setCode"] == "LC"} == {"2002-05-24"}
    assert {c["date"] for c in jungle if c["setCode"] == "XYPR"} == {"2016-12-14"}
    assert {"B2", "XY-P"} <= {c["setCode"] for c in jungle}
    def artwork_number(set_code, number):
        return next(c["artworkNumber"] for c in cards if c["setCode"] == set_code and c["number"] == number)

    # Same-day groups follow the set's collector numbers, not their group ids.
    assert artwork_number("s10a", "058/071") < artwork_number("s10a", "077/071")
    assert artwork_number("sv2a", "143/165") < artwork_number("sv2a", "181/165")
    assert artwork_number("sm9", "066/095") < artwork_number("sm9", "106/095")
    assert artwork_number("s1H", "045/060") < artwork_number("s1H", "046/060") < artwork_number("s1H", "066/060")
    groups = release_groups(artwork, review)
    image_groups = [image_group for family in review["artworkGroups"].values() for image_group in family]
    assert len(image_groups) == len(set(image_groups))
    assert set(image_groups) <= {group["groupId"] for group in artwork["groups"]}
    assert {item["cardReleaseId"] for item in catalogue["items"] if item["active"]} <= groups.keys()
    assert len({c["group"] for c in cards if c["setCode"] in {"HXY", "KSS"}}) == 1
    assert len({c["group"] for c in cards if c["setCode"] in {"GEN", "XY2", "FLF", "20th"}}) == 1
    assert {c["group"] for c in cards if c["setCode"] == "SSH" and c["number"] in {"142/202", "206/202"}} == {
        "snorlax-vmax-landscape"}
    assert {c["group"] for c in cards if c["setCode"] == "VIV" and c["number"] == "131/185"} == {
        "snorlax-vivid-voltage"}
    assert {c["group"] for c in cards if c["setCode"] == "SWSH" and c["number"] == "068"} == {
        "snorlax-prerelease-sky"}
    assert {card["distribution"] for card in cards if card["setCode"] == "CL" and card["distribution"]} == {
        "Call of Legends Prerelease", "Call of Legends Prerelease Staff"}
    hypothesis = next(card for card in cards if card["id"] == "research-kss-26-it-wave-holo")
    assert hypothesis["status"] == "pending" and hypothesis["preview"] is None
    assert "closed at non-holo" in hypothesis["note"]
    release = next(row["release"] for row in review["research"] if row["id"] == hypothesis["id"])
    assert not any(c["id"] == hypothesis["id"] for c in project(rejected | {f"{release}\x1fholo"}))
    open_promos = [c for c in cards if c["setCode"] == "CL" and c["kind"] == "research-placeholder"]
    assert {c["language"] for c in open_promos} == {"French", "Italian"}
    assert all(c["status"] == "needs-evidence" and c["date"] is None for c in open_promos)
    verdicts["U0469"] = "not-printed"
    assert not any(c["id"] == "research-cl-33-fr-prerelease" for c in project(rejected))
    verdicts["U0469"] = "needs-evidence"
    assert all((ROOT / card[kind]).is_file() for card in cards for kind in ("thumbnail", "preview") if card[kind])
    catalogue["items"].reverse()
    artwork["groups"].reverse()
    assert cards == project(rejected)
    print("Gallery projection checks passed.")


if __name__ == "__main__":
    main()
