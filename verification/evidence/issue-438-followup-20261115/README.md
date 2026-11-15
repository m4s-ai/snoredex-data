<!-- doc: role=bounded finish follow-up and implementation handoff; stage=history -->

> Historical record — issue #438 follow-up on 2026-11-15, based on main 60b3e9ba.

# Active finish queue and gallery reconciliation

| Target / evidence | Accepted fields | Recorded in data/ | Outputs / delivery | Remaining |
|---|---|---|---|---|
| KR mC 568/742 Reverse Holo, F0220-P02, item-fe7f86cb-ec63-5207-b6b4-14612e086704 | No new finish evidence | Candidate unchanged | No promotion or new SPEC | Exact Korean physical foil evidence or explicit owner decision |
| Italian KSS 26 Wave Holo gallery hypothesis | Existing owner decision OAF-20261101-KSS-26-it closes the list at non-holo | Remove research-kss-26-it-wave-holo from images.placeholders | Rebuild gallery; preserve every printing and owner record | None for this stale hypothesis |
| Catalogue summary | Active items differ from retained inactive records | No printing or identity changes | build.py separates active/inactive item totals and uses active kind/graph counts; legacy compatibility retains its historical denominator | Deliver scoped branch after checks; no merge/deployment authorized |

## Retained evidence checked first

- `data/evidence.json` already cites Bunjang 433165345 and the exact Korean publisher card.
- `verification/evidence/rarity-finish-research-20261006/` retains the two Korean identity-only
  seller views; its intake notes explicitly do not establish physical foil.
- `verification/evidence/all-open-research-20261007/kr-modern-results.json` records the same
  Bunjang leads, the six inspected views of 433165345, the deleted 429503725 offer, and the
  explicitly Japanese 434794829 mirror offer. None is a new independent confirmation today.
- `verification/evidence/owner-mc568-non-holo-20261008/owner-statement.json` records the owner's
  explicit Non-Holo determination for SPEC-0614. Its Bunjang seller title says Holo, but that
  metadata does not override the field-specific owner determination or establish the candidate.
- `verification/owner_adjudications.json` contains the Italian KSS decision cited above. It is
  reused without modification. Removing a contradictory gallery hypothesis adds no absence verdict.

## Bounded retrieval round

Queries included native name plus `568/742`, Korean-language/mirror terms, and regional Bunjang
offers. Search results are leads only; seller titles do not establish either language or finish.

| Source / route | Observation and limit |
|---|---|
| https://pokemoncard.co.kr/cards/detail/BS2026001568 | Publisher page reachable; exact Korean name, 568/742, Po-Suzuki, HP160 and attack text. No card-specific physical finish assertion accepted. |
| https://pokemoncard.co.kr/card/864 | Localized product page reachable; descriptive text names the random 60-card deck product. No positive finish assertion for this target accepted. |
| https://m.bunjang.co.kr/products/433165345 | Indexed as Korean Holo; ordinary HTTP returns only a JavaScript shell. Already retained identity evidence, not a new foil observation. Public detail route exposed by the site's JavaScript returned HTTP 403. |
| https://m.bunjang.co.kr/products/429503725 | Indexed mirror offer; ordinary HTTP returns a JavaScript shell. Public detail route returned HTTP 400. Card language/foil not inspected today. |
| https://m.bunjang.co.kr/products/434794829 | Search excerpt explicitly identifies a Japanese mirror card; excluded from Korean evidence. |
| https://cardticker.kr/card/669524 | Explicitly Japanese edition with TCGplayer-derived pricing; not Korean printing evidence. |
| Local browser fallback | Computer Use app approval timed out; no page/image inspection was completed through this route. |

No new photograph, source assertion, provider or physical-printing record was accepted. Original
photo bytes were not downloaded or rehashed. The candidate remains active and marketplace-claimed;
an access failure or lack of a usable photograph never proves that it was not printed.

## Verification contract

`verification/test_build_summary.py` was first run against the old state: both the inactive-count
and stale-hypothesis regressions failed. After the correction it passes, including the all-inactive
summary case. The same check is part of `scripts/regen.py`. The mobile gallery test uses the still
open French CL hypothesis and asserts that the removed KSS hypothesis is absent.

Run the current full regeneration, browser suite and built Pages artifact verification before
handoff. Their actual results and the final commit belong in the delivery report, not in a claim
of newly established card evidence. No source refresh, owner-file edit or publication is implied.
