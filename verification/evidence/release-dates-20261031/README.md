<!-- doc: role=retained release-date research evidence and intake report; stage=history -->

> Historical record — research snapshot from 2026-10-31; current dates are determined by canonical stores.

# Day-precision release-date research — second pass, 2026-10-31

Issue #442 lists the 38 catalogue items whose release date still has only month or year precision
after the [2026-10-23 research](../release-dates-20261023/README.md). This pass retried the leads
that are reachable from the research environment. [findings.json](findings.json) records each
attempt and the 38 items whose value is unchanged.

No item could be dated to the day, so no value changes. Under #442's done-when, every item keeps
its current value and these attempts are recorded. An unsuccessful search establishes no absence.

| Lead | Result |
|---|---|
| JP CLF 016: official [Classic page](https://www.pokemon-card.com/ex/classic/) | First lottery shipping is "2023年10月下旬以降予定" (late October onward); no day, so 2023-10 stays. |
| JP sN 008: `/ex/sN/` product page | 404; 2022-03 stays. |
| ID S-P 030/052/100, ID SV-P 286, TH SM-P 083, TW SM-P 053: Asia info and event pages | Rendered client-side; `news/` and the WordPress posts API return 404. The TW card search carries no dates. |
| Western retailer and pokemon.com leads | pokemon.com, PokéBeach and the Wayback Machine are blocked from this environment. The predecessor bundle's leads remain the next step. |

A future day date still needs a retained, market-specific availability or debut source, applied
through a reviewed pass to `confirmed_release_overrides.json`.
