#!/usr/bin/env python3
"""Structural invariants inside each state store (#50, Wave 1).

Ported from `review_integrity.ps1`. This validates invariants *within* each store; run
`verification/review_findings.py` for consistency *between* the stores and the artifacts
consumers read. Both now declare checks through `verification/checks.py`, so there is one
implementation of what a check is and two suites that use it.

    python verification/review_integrity.py

Exit code 0 when every structural check passes, 1 otherwise.

Counts are not invariants. Closing an open unit is the project's declared next action, and a
suite that goes red when that succeeds trains people to edit the assertion instead of reading
it. Counts are reported; only a count going *backwards* — the direction that actually signals
data loss — is a finding. That rule came from the PowerShell original and is preserved verbatim.
"""

from __future__ import annotations

import json
import sys

import checks
from checks import (ROOT, STATUSES as KNOWN_STATUSES, VERIFICATION, Check, Metric,
                    Suite, read_json)

RESOLVED = ("confirmed", "contradicted")
# KNOWN_STATUSES is imported above: one definition shared with the writers, so a value
# cannot be valid to write and invalid to check (#29).

ALLOWED_FINISHES = ("non-holo", "holo", "reverse-holo", "mirror-holo", "unknown")
ALLOWED_AVAILABILITY = ("confirmed", "owner-attested", "marketplace-claimed", "pending",
                        "not-applicable")
ALLOWED_PRINTING = ("confirmed", "owner-attested", "marketplace-claimed", "pending")
ALLOWED_MAPPING = ("confirmed", "partial", "pending", "not-applicable")
ALLOWED_PATTERN = ("confirmed", "partial", "pending", "not-applicable")
# "owner-adjudicated" is rule 4 applied to finishes (#119): the collection owner closing a list
# the evidence already established, where no manifest covers the product. Kept separate from
# "complete-manifest", which stays source-derived; E13 holds the decision to what it may do.
ALLOWED_COMPLETENESS = ("complete-manifest", "owner-adjudicated", "positive-evidence-only",
                        "pending", "not-applicable")
ALLOWED_CLOSURE_SCOPES = ("finish-unit", "standard-set")
ALLOWED_MARKING_ROLES = ("print-identity", "reverse-holo-treatment", "distribution-promo")
ALLOWED_EDITIONS = ("1st Edition", "Unlimited")


def first(items: list, count: int = 5) -> list:
    return items[:count]


def emit(result: Check | Metric) -> None:
    """This suite's output format, unchanged from the PowerShell it replaces."""
    if isinstance(result, Check):
        mark = "OK  " if result.ok else "FAIL"
        print(f"[{mark}] {result.name}" + (f" - {result.detail}" if result.detail else ""))
        return
    mark = "WARN" if result.regressed else "INFO"
    if result.drift > 0:
        arrow = f" (+{result.drift} since baseline {result.baseline})"
    elif result.drift < 0:
        arrow = f" ({result.drift} since baseline {result.baseline})"
    else:
        arrow = ""
    print(f"[{mark}] {result.name} = {result.value}{arrow}"
          + (f" - {result.detail}" if result.detail else ""))


def unit_of(units: list[dict], **match) -> dict | None:
    for unit in units:
        if all(unit.get(key) == value for key, value in match.items()):
            return unit
    return None


def printings_of(unit: dict | None) -> list[dict]:
    return list(unit.get("printings") or []) if unit else []


def _check_unit_store(suite: Suite, units: list[dict], cards: list[dict], excluded: list[dict]) -> None:
    """Check unit identity, status shape, evidence, and card coverage."""
    suite.report("units total", len(units), 719)
    seen: dict[str, int] = {}
    for unit in units:
        seen[unit.get("unitId")] = seen.get(unit.get("unitId"), 0) + 1
    duplicate_ids = [name for name, count in seen.items() if count > 1]
    suite.check("unitIds unique", not duplicate_ids, f"{len(duplicate_ids)} duplicates")

    status_counts: dict[str, int] = {}
    for unit in units:
        status = unit.get("status")
        status_counts[status] = status_counts.get(status, 0) + 1
    stray = [status for status in status_counts if status not in KNOWN_STATUSES]
    suite.check("no stray statuses", not stray,
                ", ".join(f"{name}={status_counts[name]}" for name in sorted(status_counts)))
    total = sum(status_counts.values())
    suite.check("status sum equals unit count", total == len(units),
                f"sum={total} units={len(units)}")

    bad_evidence, bad_source = [], []
    for unit in units:
        if unit.get("status") in RESOLVED:
            evidence = unit.get("evidence")
            if not isinstance(evidence, str) or len(evidence) < 20:
                bad_evidence.append(unit.get("unitId"))
            source_type = unit.get("sourceType")
            if not isinstance(source_type, str) or not source_type.strip():
                bad_source.append(unit.get("unitId"))
    suite.check("resolved units have evidence", not bad_evidence,
                ",".join(first(bad_evidence)))
    suite.check("resolved units have sourceType", not bad_source, ",".join(first(bad_source)))

    stale = [u for u in units if u.get("status") in RESOLVED and u.get("manualReason")]
    suite.check("no manualReason on resolved units", not stale,
                ",".join(u.get("unitId") for u in first(stale)))
    expected = sum(len(c.get("languages") or []) for c in cards if not c.get("isCodeCard"))
    suite.check("unit rows match non-code card language claims", expected == len(units),
                f"non-code card langs={expected}, units={len(units)}")
    suite.report("excluded code-card units", len(excluded), 75)

    card_keys = {f"{c.get('setCode')}|{c.get('number')}|{c.get('variantToken') or 'base'}"
                 for c in cards}
    orphans = [u for u in units
               if f"{u.get('setCode')}|{u.get('number')}|{u.get('variant')}" not in card_keys]
    suite.check("no orphaned units", not orphans,
                "; ".join(f"{u.get('setCode')} {u.get('number')} {u.get('variant')}"
                           for u in first(orphans)))


def _check_card_metadata(suite: Suite, cards: list[dict]) -> None:
    missing_images = [c for c in cards if not (ROOT / str(c.get("imageFile"))).exists()]
    suite.check("all 198 images on disk", not missing_images, f"{len(missing_images)} missing")
    suite.report("named variants", sum(1 for c in cards if c.get("variantName")), 11)
    suite.report("artist coverage", sum(1 for c in cards if c.get("artist")), 115,
                 f"of {len(cards)} cards")


def _check_evidence_log(suite: Suite) -> None:
    bad_lines = 0
    line_number = 0
    for line in (VERIFICATION / "evidence.jsonl").read_text(encoding="utf-8-sig").splitlines():
        line_number += 1
        if not line.strip():
            continue
        try:
            json.loads(line)
        except ValueError:
            bad_lines += 1
    suite.check(f"evidence.jsonl parses ({line_number} lines)", bad_lines == 0,
                f"{bad_lines} bad lines")


def _check_work_queue(suite: Suite, units: list[dict]) -> None:
    pending = [u for u in units if u.get("status") == "pending"]
    manual = [u for u in units if u.get("status") == "needs-manual-review"]
    suite.report("pending units", len(pending), 0,
                 "; ".join(f"{u.get('setCode')} {u.get('number')} {u.get('language')}"
                           for u in pending),
                 direction=checks.DOWN_IS_PROGRESS)
    suite.report("manual-review units", len(manual), 0,
                 "; ".join(f"{u.get('setCode')} {u.get('variant')}" for u in manual),
                 direction=checks.DOWN_IS_PROGRESS)


def _check_finish_identity(suite: Suite, units: list[dict], finish_units: list[dict]) -> None:
    suite.report("finish units", len(finish_units), 637)
    finish_seen: dict[str, int] = {}
    for unit in finish_units:
        key = unit.get("finishUnitId")
        finish_seen[key] = finish_seen.get(key, 0) + 1
    finish_duplicates = [name for name, count in finish_seen.items() if count > 1]
    suite.check("finishUnitIds unique", not finish_duplicates,
                f"{len(finish_duplicates)} duplicates")

    claim_keys = {f"{u.get('setCode')}|{u.get('number')}|{u.get('language')}" for u in units}
    actual_keys = {f"{u.get('setCode')}|{u.get('number')}|{u.get('language')}"
                   for u in finish_units}
    key_differences = claim_keys ^ actual_keys
    suite.check("finish units exactly cover claim groups", not key_differences,
                f"{len(key_differences)} key differences")


def _check_finish_states(suite: Suite, finish_units: list[dict], finish_review: dict) -> None:
    bad_state = []
    for unit in finish_units:
        printings = list(unit.get("printings") or [])
        broken = (
            unit.get("applicabilityStatus") not in ("applicable", "not-applicable")
            or unit.get("availabilityStatus") not in ALLOWED_AVAILABILITY
            or unit.get("productMappingStatus") not in ALLOWED_MAPPING
            or unit.get("patternStatus") not in ALLOWED_PATTERN
            or unit.get("completenessStatus") not in ALLOWED_COMPLETENESS
            or any(p.get("finish") not in ALLOWED_FINISHES
                   or p.get("verificationStatus") not in ALLOWED_PRINTING
                   or (p.get("edition") is not None and p.get("edition") not in ALLOWED_EDITIONS)
                   for p in printings)
            or (unit.get("applicabilityStatus") == "not-applicable" and (
                unit.get("availabilityStatus") != "not-applicable"
                or len(printings) != 0
                or len(unit.get("unresolved") or []) != 0
                or any(p.get("claimStatus") != "contradicted"
                       for p in (unit.get("products") or []))))
        )
        if broken:
            bad_state.append(unit)
    not_applicable = [u for u in finish_units if u.get("applicabilityStatus") == "not-applicable"]
    review_not_applicable = [u for u in (finish_review.get("units") or [])
                             if u.get("availabilityStatus") == "not-applicable"]
    review_count = finish_review.get("meta", {}).get("count")
    state_ok = (
        not bad_state
        and not review_not_applicable
        and review_count == len(finish_review.get("units") or [])
    )
    suite.check("finish taxonomy, applicability, and review queue valid", state_ok,
                f"bad={len(bad_state)}, not-applicable={len(not_applicable)}, "
                f"review={review_count}")


def _check_finish_unknowns(suite: Suite, finish_units: list[dict]) -> None:
    hidden_unknown_finishes = [
        unit.get("finishUnitId") for unit in finish_units
        if any(p.get("finish") == "unknown" for p in (unit.get("printings") or []))
        and (unit.get("completenessStatus") == "complete-manifest" or not unit.get("unresolved"))
    ]
    suite.check("unknown finish printings remain unresolved", not hidden_unknown_finishes,
                ",".join(first(hidden_unknown_finishes)))


def _check_finish_scopes(suite: Suite, finish_units: list[dict], finish_review: dict) -> None:
    improperly_closed_scopes, hidden_out_of_scope_printings = [], []
    for unit in finish_units:
        manifests = [
            source
            for printing in (unit.get("printings") or [])
            for source in (printing.get("sources") or [])
            if source.get("supportsAbsence") is True
            and source.get("coverage") == "complete-manifest"
            and (not source.get("languages") or unit.get("language") in source["languages"])
        ]
        scopes = {source.get("closureScope") for source in manifests}
        if scopes and "finish-unit" not in scopes \
                and unit.get("completenessStatus") == "complete-manifest":
            improperly_closed_scopes.append(unit.get("finishUnitId"))
        bounded_urls = {
            source.get("url") for source in manifests
            if source.get("closureScope") != "finish-unit" and source.get("url")
        }
        uncovered = [
            printing for printing in (unit.get("printings") or [])
            if bounded_urls and not any(
                source.get("url") in bounded_urls for source in (printing.get("sources") or []))
        ]
        if uncovered and "finish-unit" not in scopes and not unit.get("unresolved"):
            hidden_out_of_scope_printings.append(unit.get("finishUnitId"))
    suite.check("scoped manifests do not close finish units", not improperly_closed_scopes,
                ",".join(first(improperly_closed_scopes)))
    suite.check("out-of-scope printings remain unresolved", not hidden_out_of_scope_printings,
                ",".join(first(hidden_out_of_scope_printings)))
    suite.report("finish units covered by a complete manifest",
                 sum(1 for u in finish_units
                     if u.get("completenessStatus") == "complete-manifest"), 4)
    suite.report("finish review queue", len(finish_review.get("units") or []), 234,
                 direction=checks.DOWN_IS_PROGRESS)


def _check_finish_printings(suite: Suite, finish_units: list[dict]) -> None:
    printing_ids = [p.get("printingId")
                    for u in finish_units for p in (u.get("printings") or [])]
    printing_seen: dict[str, int] = {}
    for printing_id in printing_ids:
        printing_seen[printing_id] = printing_seen.get(printing_id, 0) + 1
    duplicate_printings = [name for name, count in printing_seen.items() if count > 1]
    suite.check("printingIds unique", bool(printing_ids) and not duplicate_printings,
                f"{len(duplicate_printings)} duplicates")

    bad_sources, bad_mappings, bad_roles = [], [], []
    for unit in finish_units:
        product_variants = {p.get("variant") for p in (unit.get("products") or [])}
        for printing in (unit.get("printings") or []):
            sources = list(printing.get("sources") or [])
            if not sources:
                bad_sources.append(printing.get("printingId"))
            for source in sources:
                if source.get("supportsAbsence") is True and (
                        source.get("authorityTier") != "official-primary"
                        or source.get("coverage") != "complete-manifest"
                        or source.get("closureScope") not in ALLOWED_CLOSURE_SCOPES):
                    bad_sources.append(printing.get("printingId"))
            for mapped in (printing.get("mappedVariants") or []):
                if mapped not in product_variants:
                    bad_mappings.append(printing.get("printingId"))
            for marking in (printing.get("markings") or []):
                if not marking:
                    continue
                if marking.get("role") not in ALLOWED_MARKING_ROLES:
                    bad_roles.append(printing.get("printingId"))
                if (marking.get("role") == "reverse-holo-treatment"
                        and printing.get("finish") != "reverse-holo"):
                    bad_roles.append(printing.get("printingId"))
    suite.check("finish printings have sources", not bad_sources, ",".join(first(bad_sources)))
    suite.check("finish mappings reference local products", not bad_mappings,
                ",".join(first(bad_mappings)))
    suite.check("stamp roles valid and finish-safe", not bad_roles, ",".join(first(bad_roles)))


def _check_tcgdex_positives(
    suite: Suite, units: list[dict], finish_units: list[dict], tcgdex_snapshot: dict
) -> None:
    finish_units_by_key = {
        (unit.get("setCode"), str(unit.get("number")), unit.get("language")): unit
        for unit in finish_units
    }
    missing_tcgdex_positives = []
    for unit in units:
        url = str(unit.get("sourceUrl") or "")
        if unit.get("status") != "confirmed" or not url.startswith("https://api.tcgdex.net/"):
            continue
        finish_unit = finish_units_by_key.get(
            (unit.get("setCode"), str(unit.get("number")), unit.get("language"))
        )
        variants = (tcgdex_snapshot.get(url) or {}).get("payload", {}).get("variants", {})
        for field, finish in (
            ("normal", "non-holo"), ("holo", "holo"), ("reverse", "reverse-holo")
        ):
            if variants.get(field) is not True:
                continue
            preserved = any(
                printing.get("finish") == finish
                and any(source.get("url") == url for source in (printing.get("sources") or []))
                for printing in (finish_unit or {}).get("printings", [])
            )
            if not preserved:
                missing_tcgdex_positives.append(
                    f"{unit.get('setCode')} {unit.get('number')} {unit.get('language')} {finish}"
                )
    suite.check("TCGdex positive finish evidence is preserved", not missing_tcgdex_positives,
                ",".join(first(missing_tcgdex_positives)))


def _check_standard_set_mappings(suite: Suite, finish_units: list[dict]) -> None:
    bad_standard_set_mappings = []
    for unit in finish_units:
        standard_variants = {
            product.get("variant") for product in (unit.get("products") or [])
            if product.get("rarity") != "Oversized"
        }
        for printing in (unit.get("printings") or []):
            if not any(
                source.get("closureScope") == "standard-set"
                for source in (printing.get("sources") or [])
            ):
                continue
            mapped = set(printing.get("mappedVariants") or [])
            if printing.get("cardSize") != "standard" or (
                len(standard_variants) == 1 and not standard_variants <= mapped
            ):
                bad_standard_set_mappings.append(printing.get("printingId"))
    suite.check("standard-set checklist printings map to the standard product",
                not bad_standard_set_mappings,
                ",".join(first(bad_standard_set_mappings)))


def _check_finish_overrides(
    suite: Suite, finish_units: list[dict], finish_overrides: dict
) -> None:
    override_sources = finish_overrides.get("sources") or {}
    unbounded_language_overrides = []
    for override in (finish_overrides.get("overrides") or []):
        override_languages = set(override.get("languages") or [])
        for printing in (override.get("printings") or []):
            refs = printing.get("sourceRefs") or []
            scoped_languages = [
                set(override_sources[ref].get("languages") or []) for ref in refs
            ]
            if refs and all(scoped_languages):
                supported_languages = set().union(*scoped_languages)
                if not override_languages or not override_languages <= supported_languages:
                    unbounded_language_overrides.append(
                        f"{override.get('setCode')} {override.get('number')} {printing.get('finish')}"
                    )
    suite.check("language-scoped-only overrides stay within source coverage",
                not unbounded_language_overrides,
                ",".join(first(unbounded_language_overrides)))
    unsupported_override_patterns = [
        f"{override.get('setCode')} {override.get('number')} {','.join(override.get('languages') or [])}"
        for override in (finish_overrides.get("overrides") or [])
        for printing in (override.get("printings") or [])
        if printing.get("foilPattern")
        and printing.get("sourceRefs")
        and all(override_sources[ref].get("closureScope") == "standard-set"
                for ref in printing["sourceRefs"])
    ]
    suite.check("finish-only checklists do not assert foil patterns",
                not unsupported_override_patterns,
                ",".join(first(unsupported_override_patterns)))
    ambiguous_pattern_duplicates = []
    for unit in finish_units:
        by_patternless_identity: dict[tuple, set] = {}
        for printing in (unit.get("printings") or []):
            identity = (
                printing.get("finish"), printing.get("edition"),
                json.dumps(printing.get("markings"), sort_keys=True),
                json.dumps(printing.get("distribution"), sort_keys=True),
                printing.get("releaseDate"), printing.get("cardSize"),
                tuple(sorted(printing.get("mappedVariants") or [])),
            )
            by_patternless_identity.setdefault(identity, set()).add(printing.get("foilPattern"))
        if any(None in patterns and len(patterns) > 1
               for patterns in by_patternless_identity.values()):
            ambiguous_pattern_duplicates.append(unit.get("finishUnitId"))
    suite.check("pattern placeholders do not duplicate identified printings",
                not ambiguous_pattern_duplicates,
                ",".join(first(ambiguous_pattern_duplicates)))


def _special_finish_core(finish_units: list[dict]) -> dict[str, object]:
    dragon_frontiers = [
        p for u in finish_units if u.get("setCode") == "DF" and u.get("number") == "10"
        for p in (u.get("printings") or [])
        if p.get("finish") == "reverse-holo" and p.get("foilPattern") == "plain-foil-on-pokemon"
        and sum(1 for m in (p.get("markings") or [])
                if m and m.get("kind") == "set-logo"
                and m.get("role") == "reverse-holo-treatment") == 1
    ]
    battle_academy = unit_of(finish_units, setCode="BA20", number="MWT", language="English")
    classic = unit_of(finish_units, setCode="CLV", number="016", language="English")
    prize3 = unit_of(finish_units, setCode="PPS3 LOR", number="LOR 143", language="English")
    prize7 = unit_of(finish_units, setCode="PPS7 JTG", number="JTG 117", language="English")
    jtg_promos = unit_of(finish_units, setCode="xJTG", number="117", language="English")
    prismatic = unit_of(finish_units, setCode="xPRE", number="076", language="English")
    exs = unit_of(finish_units, setCode="EXS", number="", language="Japanese")
    exs_printings = printings_of(exs)
    exs_dates = [p.get("releaseDate") for p in exs_printings]
    exs_roles = {m.get("role") for p in exs_printings for m in (p.get("markings") or []) if m}
    return {
        "dragon_frontiers": dragon_frontiers,
        "battle_academy": battle_academy,
        "classic": classic,
        "prize3": prize3,
        "prize7": prize7,
        "jtg_promos": jtg_promos,
        "prismatic": prismatic,
        "exs_printings": exs_printings,
        "exs_dates": exs_dates,
        "exs_roles": exs_roles,
    }


def _special_finish_prizes(finish_units: list[dict]) -> tuple[list[dict], list[str]]:
    prize8_units = [
        unit for unit in finish_units
        if unit.get("setCode") == "PPS8 JTG" and unit.get("number") == "JTG 117"
    ]
    hop_english = unit_of(finish_units, setCode="JTG", number="117", language="English")
    return prize8_units, list((hop_english or {}).get("availableFinishes") or [])


def _check_special_finish_cases(suite: Suite, finish_units: list[dict]) -> None:
    core = _special_finish_core(finish_units)
    dragon_frontiers = core["dragon_frontiers"]
    battle_academy = core["battle_academy"]
    classic = core["classic"]
    prize3 = core["prize3"]
    prize7 = core["prize7"]
    jtg_promos = core["jtg_promos"]
    prismatic = core["prismatic"]
    exs_printings = core["exs_printings"]
    exs_dates = core["exs_dates"]
    exs_roles = core["exs_roles"]
    special_ok = (
        len(dragon_frontiers) == 4
        and sum(1 for p in printings_of(battle_academy) if p.get("finish") == "non-holo") == 1
        and sum(1 for p in printings_of(classic) if p.get("finish") == "holo") == 1
        and sum(1 for p in printings_of(prize3) if p.get("finish") == "non-holo") == 1
        and sum(1 for p in printings_of(prize7) if p.get("finish") == "non-holo") == 1
        and sum(1 for p in printings_of(jtg_promos)
                if p.get("finish") == "holo" and p.get("foilPattern") == "cosmos") == 3
        and sum(1 for p in printings_of(prismatic)
                if p.get("finish") == "holo" and p.get("cardSize") == "standard") == 1
        and sum(1 for p in printings_of(prismatic)
                if p.get("finish") == "holo" and p.get("cardSize") == "jumbo") == 1
        and sum(1 for p in exs_printings if p.get("finish") == "non-holo") == 2
        and all(date in exs_dates for date in ("1998-03-23", "1998-12-04"))
        and "print-identity" in exs_roles
    )
    suite.check("special finish cases modeled", special_ok,
                f"DF={len(dragon_frontiers)}, xJTG={len(printings_of(jtg_promos))}, "
                f"xPRE={len(printings_of(prismatic))}, EXS={len(exs_printings)}")

    prize8_units, hop_finishes = _special_finish_prizes(finish_units)
    prize8_ok = len(prize8_units) == 6 and all(
        len(printings_of(unit)) == 2
        and {printing.get("finish") for printing in printings_of(unit)} == {"non-holo", "holo"}
        for unit in prize8_units
    )
    suite.check("Prize Pack Series Eight products are not duplicated", prize8_ok,
                ",".join(f"{unit.get('language')}={len(printings_of(unit))}"
                         for unit in prize8_units))

    hop_ok = len(hop_finishes) == 2 and all(f in hop_finishes for f in ("holo", "reverse-holo"))
    suite.check("regular JTG 117 discloses holo + reverse only", hop_ok, ",".join(hop_finishes))


def _check_finish_projection(suite: Suite, cards: list[dict], finish_units: list[dict]) -> None:
    bad_summaries = []
    for card in cards:
        summary = card.get("finishAvailability")
        if card.get("isCodeCard"):
            if (summary or {}).get("status") != "not-applicable":
                bad_summaries.append(card)
        elif not summary or len(summary.get("byLanguage") or []) != len(card.get("languages") or []):
            bad_summaries.append(card)
    suite.check("all cards carry finish summaries", not bad_summaries,
                "; ".join(f"{c.get('setCode')} {c.get('number')}" for c in first(bad_summaries)))

    reachable = {p.get("printingId")
                 for c in cards
                 for row in ((c.get("finishAvailability") or {}).get("byLanguage") or [])
                 for p in (row.get("printings") or []) if p.get("printingId")}
    unreachable = [p.get("printingId")
                   for u in finish_units for p in (u.get("printings") or [])
                   if p.get("verificationStatus") == "confirmed"
                   and p.get("printingId") not in reachable]
    suite.check("confirmed printings reachable from a product view", not unreachable,
                ", ".join(first(unreachable)))

    missing_status = [
        c for c in cards if not c.get("isCodeCard")
        and any(not row.get("unitFinishStatus") or not row.get("productMappingStatus")
                for row in ((c.get("finishAvailability") or {}).get("byLanguage") or []))
    ]
    suite.check("projected finish rows carry unit status and mapping status", not missing_status,
                "; ".join(f"{c.get('setCode')} {c.get('number')}" for c in first(missing_status)))


def main() -> int:
    suite = Suite()
    units = read_json(VERIFICATION / "units.json")
    cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    excluded = read_json(VERIFICATION / "excluded_codecards.json")
    finish_units = read_json(VERIFICATION / "finish_units.json")["units"]
    finish_review = read_json(VERIFICATION / "FINISH_REVIEW.json")
    finish_overrides = read_json(VERIFICATION / "finish_overrides.json")
    tcgdex_snapshot = read_json(VERIFICATION / "finish_tcgdex_snapshot.json")["records"]

    _check_unit_store(suite, units, cards, excluded)
    _check_card_metadata(suite, cards)
    _check_evidence_log(suite)
    _check_work_queue(suite, units)
    _check_finish_identity(suite, units, finish_units)
    _check_finish_states(suite, finish_units, finish_review)
    _check_finish_unknowns(suite, finish_units)
    _check_finish_scopes(suite, finish_units, finish_review)
    _check_finish_printings(suite, finish_units)
    _check_tcgdex_positives(suite, units, finish_units, tcgdex_snapshot)
    _check_standard_set_mappings(suite, finish_units)
    _check_finish_overrides(suite, finish_units, finish_overrides)
    _check_special_finish_cases(suite, finish_units)
    _check_finish_projection(suite, cards, finish_units)

    suite.render(emit)
    print()
    if suite.failed:
        print(f"=== REVIEW FAILED: {', '.join(suite.failed)} ===")
        return 1
    if suite.regressed:
        print(f"=== COUNTS WENT BACKWARDS: {', '.join(suite.regressed)} ===")
        print("A metric moved in the losing direction. That is data loss or a reopened queue, not")
        print("a stale baseline: find what changed rather than editing the number it is held to.")
        return 1
    print("=== ALL STRUCTURAL CHECKS PASSED ===")
    print("Counts above are reported, not asserted: only a move in the losing direction fails.")
    print("Run 'python verification/review_findings.py' for cross-artifact consistency checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
