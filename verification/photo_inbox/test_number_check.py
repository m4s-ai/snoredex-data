"""Checks for the number guard (#658): what a reading means, and when it stops intake.

    python verification/photo_inbox/test_number_check.py
"""

from intake import Refused, number_guard
from number_check import expected, verdict

READINGS = [  # (expected, Tesseract text, result), from the misreadings seen in #655
    ("066/080", "Illus.Mitsuhiro Arita 066/080 U XY2", "match"),
    ("066/080", "Wuんamuho Anita oee/ogou ra es", "unreadable"),
    ("066/080", "067/080", "mismatch"),
    ("143/165", "143/365", "mismatch"),
    ("136/193", "736/193", "match"),          # the small italic 1 read as 7
    ("033/132", "O33/132", "match"),          # O read for 0
    ("066/080", "066 / 080", "match"),        # a slash with spaces around it
    ("1", "SM169 1/64", "match"),             # no denominator in the catalogue: the numerator counts
    ("1", "SM169", "unreadable"),             # digits inside another word are not the number
    ("169", "SM169", "match"),
    ("2/64", "1/64", "mismatch"),
]


def main():
    for wanted, text, result in READINGS:
        assert verdict(wanted, text)[0] == result, (wanted, text, verdict(wanted, text))
    assert expected("066", "080") == "066/080" and expected("LOR 143", None) == "143"

    job = {"itemId": "item-a", "numberCheck": {"itemId": "item-a", "result": "mismatch", "expected": "066/080",
                                               "read": ["067/080"]}}
    try:
        number_guard(job)
    except Refused as error:
        assert "067/080" in str(error) and "066/080" in str(error)
    else:
        raise AssertionError("an unconfirmed mismatch must stop intake")
    number_guard(dict(job, numberConfirmedAt="2026-11-25T10:00:00+00:00"))  # the owner confirmed it
    number_guard(dict(job, itemId="item-b"))  # a check of another printing says nothing about this one
    for result in ("match", "unreadable", "unavailable"):
        number_guard({"itemId": "item-a", "numberCheck": {"itemId": "item-a", "result": result}})
    number_guard({"itemId": "item-a"})  # never checked
    print("number check: all checks passed")


if __name__ == "__main__":
    main()
