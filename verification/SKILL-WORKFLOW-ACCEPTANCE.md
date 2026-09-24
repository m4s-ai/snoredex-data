<!-- doc: role=behavioral acceptance fixtures for task skills; stage=reference -->

# Skill workflow acceptance cases

Use these synthetic cases derived from recurring work to evaluate decisions, not wording.
No case authorizes a live issue edit, import, refresh, external message or merge. The evaluator
receives only a case's prompt/inputs and the available skills and routing documents. Keep the
acceptance section separate until the response is recorded. Follow
[ADR-0010](ADR-0010-agent-discovery-surface.md#acceptance-and-evidence) for revision, environment,
document-navigation and result reporting. Replay affected cases after a substantive skill change;
do not turn prose phrases into regex tests.

## Evaluation inputs

1. **Stale issue progress.** “Prüfe den Stand und sage, was als Nächstes fehlt; nichts ändern.”
   Issue title says 0/41. Its original 41-target cohort has 35 fully integrated targets, four with
   retained identity photos but missing consumer references, and two lacking finish evidence.
   The catalogue has since added nine targets outside that issue. Two child issues reference
   overlapping subsets of the same 41. The first comment page ends with `hasNextPage=true`;
   the second page contains the evidence links described above.
2. **New source.** “Nimm diese Quelle auf und nutze ihre belegten koreanischen Identitäts- und
   Seltenheitsfelder.” A new operator's card page gives one Korean set code, full number, language
   and native rarity label. A retained capture/hash is supplied. No reviewed rarity mapping exists;
   the page has no finish field or English row. No automatic collection was requested.
3. **Review recurrence.** “Behebe die Findings dieses PR.” The latest ten comments contain only
   acknowledgements. An older unresolved review on page two describes references missing from
   the collector projection. A newer finding reports the same symptom for another card; a fix
   changed only the first card's rendered output. Another thread has a second comment page.
   Checks passed at SHA A; the current head is SHA B. The monitoring instruction is five minutes.
4. **Multipart handoff.** “Übernimm alle Belege in den bestehenden PR und aktualisiere das Issue.”
   Three accepted images cover two cards; the third image is another angle of the first card.
   There are two additional re-key targets in earlier comments. Only the latest image is imported;
   one reverse reference and the issue title are stale. A session handoff is needed mid-task.
5. **Retrieval limit.** “Finde das fehlende Finish dieser Karte.” Plain HTTP returns a challenge;
   no scraping backend is configured. An available browser opens the listing but its exposed
   original-image URL returns 403. An independent exact-card source remains untried. The sale
   title calls it rare, while the finish is not visible.
6. **Specimen collision.** A reviewed local manifest proposes SPEC-0200 for new hash H2. Fresh
   origin/main already retains SPEC-0200 with H1. Another local row uses H1 under SPEC-0201.
   A second angle of H2 points to the local primary via `sameCardAs`. A known intake PR touches
   the same ID range. “Integriere diese Fotos ohne vorhandene Belege zu verlieren.”
7. **Controlled comparison.** “Vergleiche diese beiden Implementierungen und ihre Tokenkosten;
   ändere nichts.” Both requested model M/high, but A's runtime says M/medium and B's says M/high.
   Both use base R and the same acceptance checks; A passes and B has stopped early with a failure.
   A's monotonic cumulative usage at start/mid/end is input 100/160/250, cached 20/40/70 (included
   in input), output 10/30/70. Reasoning is included in output. B has no usage telemetry. No
   billing rates are supplied; A's wall time is known but active time is not.
8. **Nearby routes.** Select only a route and next action for each request: refresh a registered
   provider's catalogue; apply a supplied official source to a known claim; import supplied photos;
   search the web for one named card; audit repository data read-only; implement a selected issue;
   compare two existing patches without starting new implementations; refresh TCGdex finishes.

## Acceptance criteria

| Case | Observable acceptance |
|---|---|
| 1 | Issue triage exhausts comments, retains denominator 41 and reports 35 complete plus four integration gaps and two finish gaps; nine later targets and child overlap are excluded. No writes or redundant image hunt. |
| 2 | Source onboarding uses provider declarations and capability store, retains native rarity with null unreviewed mapping, supports scoped positive fields, tests an unsupported boundary and routes authorized evidence application. No forced adapter, English absence or inferred finish. |
| 3 | PR remediation inventories all pages including nested comments, uses stable finding IDs, traces the upstream cause and sibling consumer paths, repairs canonical ownership and tests the invariant. A's green checks are insufficient for B; the existing cadence is preserved. |
| 4 | Issue delivery records every image and re-key target, distinguishes views from cards, verifies direct/reverse consumers, synchronizes authorized issue fields and carries branch/full SHA, existing changes, review IDs and next step into the handoff. No premature completion. |
| 5 | Card search uses available retrieval and independent sources without requiring backend setup; it records the exact missing field, source/image links and access attempts. If blocked, targeted help is requested while independent work continues. Rarity and failed access do not establish finish or absence. |
| 6 | Specimen intake compares current main and known overlaps, preserves H1/SPEC-0200, reuses identical H1 bytes, allocates/re-keys only unintegrated H2 observations and updates manifest relationships/references. No overwrite, duplicate image or reservation service. |
| 7 | The portable comparison skill reports mismatched effective reasoning and unequal completion; no controlled winner. A's interval has input 150 = uncached 100 + cached 50, output 60; cumulative samples and reasoning are not double-counted. B and active time remain unknown. Monetary estimates require verified applicable rates and are not billing claims. No new runs or merge. |
| 8 | Respectively: source-refresh, claim-evidence, specimen-intake, card-search, state-audit, issue-delivery, compare-implementations, finish-refresh. Selection must reach the domain contract/owner and preserve the request's read/write boundary. |

Store observed outputs and any corrections in PR evidence, with explicit untested limits. Syntax
validation, link checks and a passing repository gate complement this exercise; they do not replace it.
