<!-- doc: role=retained rarity research evidence for #437; stage=history -->

> Historical record — research snapshot from 2026-10-30; current rarities are determined by canonical stores.

# Marketplace-only rarities resolved — 2026-10-30 (#437)

After rarity claims were scoped to their own marketplace product, seven catalogue items were still open. Six Korean items carried a rarity that rested on the Cardmarket catalogue alone, and the CL 33 Staff promo had no product of its own. A rarity is recorded only where the collector line is legible on the exact card or the collection owner states it explicitly. A missing value on a page establishes nothing.

| Release | Items | Finding | Evidence |
|---|---|---|---|
| KR m2a 136/193 Hop's Snorlax | holo | **No printed rarity symbol** after `136/193` | Official Pokémon Korea render [`raw/pokemonkorea-M2a_136.png`](raw/pokemonkorea-M2a_136.png). The detail page `BS2025015136` lists no rarity either; that silence is context, not the evidence. |
| KR xm2a 136/193 V2 (Poké Ball mirror) | mirror-holo | **No printed rarity symbol** after `136/193` | SPEC-0410, a complete Cardmarket seller photograph of this exact V2 product |
| KR xm2a 136/193 V1 (Colorless Energy mirror) | mirror-holo | **No printed rarity symbol** (owner attestation) | The owner, 2026-10-30: "m2a 136 v1 ist bis auf die art des reverse holo komplett gleich also auch kein Symbol". SPEC-0437 (480 px) identifies the card, but its collector line is too small to read. |
| KR xsv2a 143/165 V1 (Poké Ball mirror) | mirror-holo | **U** | SPEC-0660, an owner-supplied photograph with a legible `143/165 U` |
| KR xsv2a 143/165 V2 (Master Ball mirror) | mirror-holo | **U** | SPEC-0659, an owner-supplied photograph with a legible `143/165 U`. A sv2a 181/165 AR card sits beside it in the frame and is not part of the record. |
| EN CL 33 prerelease and prerelease Staff promos | holo | **Promo** (owner decision) | The owner, 2026-10-30: "und ja die CL 33 ist Promo in der Prerelease und Prerelease Staff Variante". The claim names the two distribution kinds, so the regular CL 33 stays Rare. |

The official Korean render of the regular sv2a 143/165 prints `U`. Under the owner's rule that Cardmarket "Additionals" (`x…`) products are verified independently, that value is not carried over to the xsv2a mirrors.

MEGA Dream ex is a high-class pack. Its regular cards print no rarity symbol, as the Shiny Treasure ex cards do (`SV4a I 145`). The value stays source-native: `no printed rarity symbol` with no normalized id, because `fixed` is reserved for fixed-deck contents.

Owner statements are recorded under their own `owner-attestation` source records (`SET-SRC-OWNER-XM2A-136-V1-RARITY-20261030`, `SET-SRC-OWNER-CL-33-PROMO-RARITY-20261030`). [`intake-manifest.json`](intake-manifest.json) and [`sources.json`](sources.json) hold the imports of the two owner photographs: the original WebP files, decoded losslessly to PNG with pixel equality checked.

| File | sha256 |
|---|---|
| `raw/pokemonkorea-M2a_136.png` (868×1212, fetched 2026-10-30 from `https://cards.image.pokemonkorea.co.kr/data/wmimages/MEGA/M2a/M2a_136.png`) | `5141239033c1e916f154a65a7259d7afd1bbfccb3aaa3ac98e3c363824626239` |

Applied by [`record_kr_hop_snorlax_rarity_20261030.py`](../../passes/record_kr_hop_snorlax_rarity_20261030.py).
