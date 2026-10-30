"""Route the checklist ids that carried an `unknown` card size to their standard-size ids.

Pokémon cards have one defined standard size; a jumbo or other size is the deviation that needs
evidence (owner decision 2026-10-29: "ist doch logisch das es einen Standard Kartengröße gibt ...
Das hätte niemals auf unknown stehen müssen"). The finish projection and the checklist now default
an unproven size to standard, so the size suffix `-unknown` leaves these 58 checklist ids.
Each old id gets a reviewed cumulative rekey to the same id without the suffix, so collection
state recorded under the old id migrates instead of disappearing (`retainsItemId` keeps the
collector item id of research placeholders anchored on the old id), and reviewed release dates
that name an old id are retargeted to the new one.

Idempotent; `--check` reports missing routes and routes whose target is not a current checklist id.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTES = ROOT / "verification" / "collector_migration_routes.json"
CHECKLIST = ROOT / "analysis_checklist.json"
DATES = ROOT / "verification" / "confirmed_release_overrides.json"
REASON = "Card size defaults to standard (owner decision 2026-10-29); the unknown-size suffix is retired."
SUFFIX = "-unknown"
OLD_IDS = [
    "20th-047-korean-unl-non-holo-unknown",
    "bw-p-207-japanese-none-holo-unknown",
    "clf-016-korean-none-holo-unknown",
    "csm2bc-124-s-chinese-none-reverse-holo-large-type-symbol-left-unknown",
    "csvh1c-a001-s-chinese-none-non-holo-unknown",
    "csvh4c-a003-s-chinese-none-non-holo-unknown",
    "dp-p-127-korean-none-unresolved-unknown",
    "hxy-026-korean-none-non-holo-unknown",
    "ju-27-spanish-1e-non-holo-edition-stamp-edici-n-1-unknown",
    "ju-27-spanish-unl-non-holo-unknown",
    "m2a-136-t-chinese-none-unresolved-unknown",
    "m2a-136-thai-none-unresolved-unknown",
    "mc-567-korean-none-non-holo-unknown",
    "mc-567-t-chinese-none-non-holo-unknown",
    "mc-568-korean-none-non-holo-unknown",
    "mc-569-korean-none-non-holo-unknown",
    "mc-569-t-chinese-none-non-holo-unknown",
    "pkmtch-s-p-s-p-145-t-chinese-none-unresolved-unknown",
    "s10a-058-indonesian-none-holo-unknown",
    "s10a-058-thai-none-holo-unknown",
    "s10a-077-indonesian-none-holo-unknown",
    "s10a-077-korean-none-holo-unknown",
    "s10a-077-thai-none-holo-unknown",
    "s10b-056-thai-none-holo-unknown",
    "s5a-93-indonesian-none-holo-unknown",
    "s5a-93-thai-none-holo-unknown",
    "s8b-126-thai-none-holo-unknown",
    "sa-10-korean-none-unresolved-unknown",
    "sh-038-korean-none-non-holo-unknown",
    "sh-038-s-chinese-none-non-holo-unknown",
    "sm-p-1-korean-none-unresolved-unknown",
    "sm-p-297-korean-none-unresolved-unknown",
    "sm10-076-korean-none-holo-unknown",
    "sm9-066-korean-none-holo-unknown",
    "sm9-106-korean-none-holo-unknown",
    "sml-038-korean-none-non-holo-unknown",
    "sv2a-143-korean-none-mirror-holo-unknown",
    "sv2a-181-indonesian-none-holo-unknown",
    "sv2a-181-korean-none-holo-unknown",
    "sv4a-145-indonesian-none-non-holo-unknown",
    "sv4a-145-korean-none-mirror-holo-unknown",
    "sv4a-310-japanese-none-holo-unknown",
    "sv4a-310-korean-none-holo-unknown",
    "sv4a-310-thai-none-holo-unknown",
    "svg-021-korean-none-non-holo-unknown",
    "sviba-046-korean-none-unresolved-unknown",
    "sviba-046-s-chinese-none-non-holo-unknown",
    "svln-010-korean-none-non-holo-unknown",
    "svm-094-indonesian-none-unresolved-unknown",
    "svm-094-korean-none-holo-unknown",
    "svm-094-t-chinese-none-holo-unknown",
    "svm-094-thai-none-non-holo-unknown",
    "svp-184-french-none-holo-staff-staff-prerelease-staff-unknown",
    "svp-184-german-none-holo-staff-staff-prerelease-staff-unknown",
    "svp-184-italian-none-holo-staff-staff-prerelease-staff-unknown",
    "svp-184-portuguese-none-holo-staff-staff-prerelease-staff-unknown",
    "svp-184-spanish-none-holo-staff-staff-prerelease-staff-juntos-de-aventuras-prerelease-staff-unknown",
    "xy2-066-japanese-unl-unresolved-unknown",
]


def route(old_id: str) -> dict:
    return {"from": old_id, "to": old_id[:-len(SUFFIX)], "reason": REASON, "retainsItemId": True}


def stale_date_targets(dates: dict) -> list[dict]:
    return [row for row in dates["releaseDates"]["reviewedItems"]
            if set(row.get("legacyChecklistIds") or []) & set(OLD_IDS)]


def retarget_dates(dates: dict) -> None:
    for row in stale_date_targets(dates):
        row["legacyChecklistIds"] = [legacy_id[:-len(SUFFIX)] if legacy_id in OLD_IDS else legacy_id
                                     for legacy_id in row["legacyChecklistIds"]]
    DATES.write_text(json.dumps(dates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main(argv) -> int:
    dates = json.loads(DATES.read_text(encoding="utf-8"))
    text = ROUTES.read_text(encoding="utf-8")
    document = json.loads(text)
    present = {row["from"] for row in document["cumulativeChecklistRekeys"]}
    pending = [route(old_id) for old_id in OLD_IDS if old_id not in present]
    if "--check" in argv:
        current = {row["checklistId"] for row in json.loads(CHECKLIST.read_text(encoding="utf-8"))["items"]}
        stale = [row for row in map(route, OLD_IDS) if row["to"] not in current or row["from"] in current]
        for row in pending:
            print("pending:", row["from"])
        for row in stale:
            print("stale route:", row["from"], "->", row["to"])
        for row in stale_date_targets(dates):
            print("pending: reviewed date retarget", row["itemId"])
        return 1 if pending or stale or stale_date_targets(dates) else 0
    if stale_date_targets(dates):
        retarget_dates(dates)
    if pending:
        # The store keeps one compact route per line; append in the same layout.
        lines = ",\n".join("    " + json.dumps(row, ensure_ascii=False) for row in pending)
        marker = "\n  ],\n  \"cardReleaseRekeys\""
        if marker not in text:
            raise SystemExit("unexpected collector_migration_routes.json layout")
        text = text.replace(marker, ",\n" + lines + marker, 1)
        json.loads(text)
        ROUTES.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
