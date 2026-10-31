<!-- doc: role=retained owner-input evidence for issue 436; stage=history -->

> Historical record — owner input of 2026-10-31; current values are determined by canonical stores.

# Issue #436 — owner-supplied names, 2026-10-31

The four identity gaps left open in [issue-436-identity-gaps-20261031](../issue-436-identity-gaps-20261031/README.md)
are closed with the collection owner's input. [`record_owner_names_20261031.py`](../../passes/record_owner_names_20261031.py)
writes them.

| Gap | Value | Basis |
|---|---|---|
| Italian DF 10 `localCardName` | `Snorlax δ` | SPEC-0662, a photograph supplied by the owner, shows the Italian face: name bar "Snorlax" with "δ SPECIE DELTA", Italian attack and label text, 10/101. Written with δ as for the other DF 10 releases. |
| ID SM-P local set name | `Sun & Moon Indonesian Promos` | Owner statement: the series has an English name only. |
| TH SM-P local set name | `Sun & Moon Thai Promos` | Owner statement, same convention. |
| KR S-P local set name | `Sword & Shield Era Promo` | Owner statement. |

The WebP original, its lossless PNG decode and the conversion record are in [`sources.json`](sources.json) and `raw/`;
the import manifest is [`intake-manifest.json`](intake-manifest.json).

## Finish of SPEC-0662 (added for #438)

The photographed face carries no EX Dragon Frontiers set-logo stamp. The official checklist gives
DF 1–12 exactly two foil versions, and only the reverse holo has that stamp, so SPEC-0662 records
the regular holo as a photographed observation (`FINISH_SOURCES.md`, *Recording what a scan shows*).
