<!-- doc: role=retained Japanese finish research and acceptance; stage=task -->
# Japanese finish research — 2026-09-29

**Research snapshot at 5ab43d1, before the later owner photo batch.** Its 12 remaining targets
were reduced to three by the [Non-Holo intake](../owner-nonholo-20260929/README.md).
The dated search outcomes below describe this earlier round, not the current remaining-work list.

Three `gpt-6-luna` subagents, each with `max` reasoning, researched the 14 Japanese
releases with unresolved physical finishes. The parent reviewed the positive evidence
and applied it to draft PR #402. This is a bounded research round, not a complete finish inventory.

## Accepted sv4a 145/190 Reverse Holo

The [PSA Snorlax master-set gallery](https://www.psacard.com/psasetregistry/tcg/pokemon-sets/pokemon-snorlax-master-set/imagegallery/495231)
names **2023 POKEMON JAPANESE SV4a-SHINY TREASURE ex 145 SNORLAX REVERSE HOLO**.
The linked front and back show the same certificate **94474867**. The front identifies
Japanese Snorlax, `sv4a`, `145/190`, and HYOGONOSUKE; its slab label says **REVERSE HOLO**.

- [SPEC-0579 front](../../specimens/SPEC-0579.jpg), SHA-256 `cc91cce1ac937875325cff638e56c3c988f1cdd0797aa7319ef5fd911d1bc1ef`.
- [SPEC-0580 back](../../specimens/SPEC-0580.jpg), SHA-256 `bc030219cbd9d0fe41529e843238f55833da4cdd24542d3060f383fcec9a4fda`.
- [Manifest](manifest.json), [source observations and retrieval limits](../jp-finish-20260929-modern/sources.json),
  and [original photograph metadata](../jp-finish-20260929-modern/photos.json).

The finish rests on PSA's named grading variety (tier 2). The photographs establish
the exact card and certificate identity; a flat scan alone does not establish the finish.
The retained registry row was accessible through indexed page text; the live registry
browser page showed a challenge. The original paired PSA photographs were reachable
and downloaded through the browser on the observation date. No challenge was bypassed.

The existing `F0471-P01` reverse-holo candidate is confirmed through
`psa-sv4a-145-reverse-holo-20260929` in `finish_overrides.json` using the existing
`evidenceOnlyForExistingPrintings` path. Its collector item
`item-f7167a5e-ef9e-5eb9-8173-8197fde4cbbb` and semantic printing
`PRINTING:f0a74ab4ae8e4ef7c823595d` are preserved. The existing PSA surface gains only
the reviewed positive identity capability for its identified slab photographs.
No foil pattern, edition, additional treatment or finish-list closure is inferred.

## M6a 095/103 owner determination

The collection owner explicitly confirms **Holo**, with no reverse/mirror variant.
The [exact statement and prior observation](m6a-owner-determination.json) are retained.
[The owner manifest](m6a-owner-manifest.json) updates existing SPEC-0514 using its
unchanged publisher-image bytes, with `ownerAttestedFields: ["finish"]`.
`OAF-20260929-M6a-095-ja` separately closes the finish list to that positively
established Holo printing. Neither conclusion is attributed to an external absence source.

This source-first release has no legacy finish unit. The existing collector generator
now applies the same owner-closure contract to such releases: exact identity, unique
target, owner authority, and equality with a nonempty set of positive physical finishes
are required. Regression checks reject empty, mismatching and externally claimed lists.

## All 14 targets

| Card | Result of this round | Retained research |
|---|---|---|
| Rocket's Snorlax G2, unnumbered | Open; conflicting seller finish descriptions and inconclusive photos | [Early group](../jp-finish-20260929-early/README.md) |
| DP1, unnumbered | Open; DPBP#174 is an identity code, not a collector number or finish | [Early group](../jp-finish-20260929-early/README.md) |
| Pt2 070/090 | Open; inspected surface close-up shows texture/glare without a conclusive finish | [Early group](../jp-finish-20260929-early/README.md) |
| BW7 055/070 | Open; seller Holo description is not established by the inspected image | [Early group](../jp-finish-20260929-early/README.md) |
| EC5 062/088 | Open; inspected gallery does not establish finish | [Early group](../jp-finish-20260929-early/README.md) |
| XY2 066/080 | Open | [XY group](../jp-finish-20260929-xy/README.md) |
| XY-P 149 | Open | [XY group](../jp-finish-20260929-xy/README.md) |
| 20th 047/072 | Open | [XY group](../jp-finish-20260929-xy/README.md) |
| XY10 057/078 | Open | [XY group](../jp-finish-20260929-xy/README.md) |
| s2 077/096 | Open; catalogue descriptions and static photos are insufficient | [Modern group](../jp-finish-20260929-modern/README.md) |
| sI100 341/414 | Open; exact identity confirmed, technical finish unresolved | [Modern group](../jp-finish-20260929-modern/README.md) |
| sI100 342/414 | Open; conflicting retailer mirror descriptions remain leads | [Modern group](../jp-finish-20260929-modern/README.md) |
| sv4a 145/190 | **Reverse Holo confirmed in draft #402** | SPEC-0579/0580 and PSA named variety above |
| M6a 095/103 | **Holo confirmed; finish list closed by the owner in draft #402** | [Modern group](../jp-finish-20260929-modern/README.md) |

For M6a, the [official product page](https://www.30th.pokemon-card.com/product/m6a)
states `キラカード6枚入り` (six shiny/foil cards). The
[exact official card record](https://www.pokemon-card.com/card-search/details.php/card/50707/regu/all)
places Snorlax 095/103 in that product. This supports a shiny/foil printing, but the
wording does not distinguish technical `holo`, `reverse-holo`, and `mirror-holo`.
Its native wording is retained as context; the owner determination above supplies
the technical Holo classification and separately closes the list.
The separate owner-confirmed Common rarity remains unchanged.

Missing finish vocabulary, a flat photograph and a seller's generic title are not
evidence of non-holo. No unresolved target was contradicted or adjudicated absent.
The next useful input for the remaining targets is an exact named grading variety,
scoped official finish statement, revealing card-surface view, or explicit owner determination.

## Consumer and backlog acceptance

Relative to pre-research draft head `1a4d7f6`, two Japanese releases gain verified
finishes: sv4a 145/190 retains its collector item ID and gains PSA/specimen provenance;
the M6a research placeholder is replaced by its SPEC-0514-backed Holo printing and
owner-adjudicated completeness. Both new SPEC references reach the source registry,
authoritative graph, artwork projection and collector evidence links. No existing
specimen ID or photograph is replaced; the M6a placeholder-to-printing transition
follows the existing collector migration contract.

| Snapshot | Japan gap-free / total | Japan remaining | All releases gap-free / total | All remaining |
|---|---:|---:|---:|---:|
| Main `d1dc293` | 53/67 | 14 | 510/633 | 123 |
| Draft after this research | 55/67 | 12 | 515/633 | 118 |

These are tracked-field release counts, not claims of finish-list completeness.
The draft now has six Japanese candidate finish gaps and six without a candidate.
The five previously reviewed Japanese unnumbered identities remain valid and are
excluded from false collector-number gaps. Main remains unchanged until merge.

Validation and the exact delivered head are recorded on PR #402. The import manifest,
canonical source/finish declarations and generated consumers are delivered together.
