<!-- doc: role=retained evidence for issue 438, Quuador's language list on the Sun & Moon era sets; stage=history -->

> Historical record — 2026-11-02; current values are determined by canonical stores.

# #438 — Quuador's list on Double Blaze, Rebellion Crash and Amazing Volt Tackle

Quuador's [Sets and Languages: Compilation overview list](https://www.elitefourum.com/t/sets-and-languages-compilation-overview-list/16565)
(post 1, author-updated 2026-10-02, retrieved 2026-11-02 via the Discourse JSON endpoint) enumerates
each set's variants per language and writes a `Reverse Holo` line **only where the author records
one**. That makes a missing line a statement about this set, not a blank page.

The owner read the list against the Japanese and Korean candidates:

> "doch die liste führt explizit auf wenn sets reverse holos haben und unter 'Unbroken Bonds / Double
> Blaze' fehlt bei Japanese ein Reverse Holo eintrag, ergo kann man daraus schließen das es kein
> Reverse Holo für sm10 auf japanisch und koreanisch gibt"

[`excerpts.json`](excerpts.json) retains the relevant sections and the SHA-256 of the full post text:

| Section | Japanese | Korean |
|---|---|---|
| Unbroken Bonds / Double Blaze (`sm10`) | `Japanese UED` — no reverse holo | `Korean` — no reverse holo |
| Rebel Clash / Rebellion Crash (`s2`) | `Japanese UED` — no reverse holo | `Korean` — no reverse holo |
| Vivid Voltage / Amazing Volt Tackle (`s4`) | `Japanese UED` — no reverse holo | `Korean` — no reverse holo |
| GG End (contrast) | `Japanese UED` | `Korean`, **`Korean Reverse Holo`** |
| Sky Legend (contrast) | `Japanese UED` | `Korean`, **`Korean Reverse Holo`** |

All three target sets do list `English`, `German`, `French`, `Italian`, `Spanish` and `Portuguese`
Reverse Holo entries, so the omission is specific to Japanese and Korean.

## What was recorded, and what was not

An external source cannot settle an absence (rule 4), so the conclusion is recorded as an owner
decision, exactly as the KSS 26 and Portuguese cases were on 2026-11-01:

| Unit | Decision | Rejected | Result |
|---|---|---|---|
| `s2 77` Japanese | `finish-complete` at `non-holo` | `reverse-holo` | closed (`OAF-20261102-S2-77-ja`) |
| `s2 77` Korean | `finish-complete` at `non-holo` | `reverse-holo` | closed (`OAF-20261102-S2-77-ko`) |
| `s4 84` Japanese | `finish-complete` at `holo` | `non-holo`, `reverse-holo` | closed (`OAF-20261102-S4-84-ja`) |
| `s4 84` Korean | `finish-complete` at `holo` | `non-holo`, `reverse-holo` | closed (`OAF-20261102-S4-84-ko`) |
| `sm10 076` Japanese | `finish-complete` at `holo` | `non-holo`, `reverse-holo` | closed (`OAF-20261102-SM10-076-ja`) |
| `sm10 076` Korean | `finish-complete` at `holo` | `non-holo`, `reverse-holo` | closed (`OAF-20261102-SM10-076-ko`) |

The owner extended his reading to the same evidence once the reverse claims sat next to the retained
images: "reverse holo ist doch jetzt widerlegt für die beiden sets sowohl auf japanisch als auch
koreanisch". All four `s4 84` and `sm10 076` units are closed and their reverse holo rejected.

`non-holo` went with it. The owner: "da in dem Set alle rares nur als holo drin sind kann non-holo
raus". No image ever supported the row — the Japanese `s4 84` catalogue scan is byte-identical to the
confirmed `holo` photograph (`SPEC-0210.jpg`) — and the Korean reverse claims rested on renders that
cannot show foil at all. Both sets now stand at `['holo']` in both languages, closed. Candidate
count 75 -> 65.

The list ends around 2020, so it says nothing about `s10a`, `s10b`, `s5a`, `s8b`, `sI` or any
2021+ set, and nothing about the Asian-language candidates.

Written by [`record_438_owner_jp_ko_reverse_20261102.py`](../../passes/record_438_owner_jp_ko_reverse_20261102.py).
