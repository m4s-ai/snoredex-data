# Third-party notices

This project's own licences (see `LICENSE.md`) cover only its original software, data selection
and arrangement, verification annotations, and documentation. Everything listed here belongs to
someone else and is used under that party's terms.

## Rights holders

**Pokémon.** Pokémon and all related names, characters, artwork, logos, and trademarks are the
property of Nintendo, Creatures Inc., and GAME FREAK inc.
© Pokémon / Nintendo / Creatures / GAME FREAK. Trading card game © The Pokémon Company.

This project is an unofficial fan project and is **not affiliated with, endorsed by, or sponsored
by** any of them. No claim of ownership is made over any Pokémon intellectual property.

**Card images.** Every file in `images/` depicts a Pokémon trading card and is served from
Cardmarket's product image host. The depicted artwork is the rights holders' property; the card
photography and hosting are Cardmarket's. They are included for identification only.

## Data providers

Each provider below appears in the generated source registry
(`verification/source_registry.json`) with its stable ID, coverage limits, and attribution
wording. The registry is the machine-readable form of this section.

| Provider | Used for | Terms |
|---|---|---|
| **Cardmarket** (`cardmarket`) | product catalogue, product identity, images, marketplace language and finish hints | Site terms at <https://www.cardmarket.com>. Catalogue claims are treated as hints, never as verification. |
| **Bulbapedia** (`bulbapedia`) | set lists, release fields, per-language articles, promo series | Content licensed **CC BY-NC-SA 2.5**. Attribution and ShareAlike apply to quoted or derived content. <https://bulbapedia.bulbagarden.net/wiki/Bulbapedia:Copyrights> |
| **TCGdex** (`tcgdex`) | card existence per language; positive normal/holo/reverse flags | Open card database, <https://api.tcgdex.net>. Variant coverage is explicitly incomplete upstream; false flags are never treated as absence. |
| **The Pokémon Company official sites** (`pokemon-official`, `pokemon-card-jp`, `pokemon-card-asia`) | official checklists and Prize Pack manifests; Japanese and Asian card databases | Publisher's own terms. The only sources permitted to establish absence, and only within their stated scope. |
| **TCGCSV / TCGplayer** (`tcgcsv`) | reproducible product identity and positive Normal/Holofoil/Reverse Holofoil subtypes | <https://tcgcsv.com>. Positive-only marketplace evidence. |
| **PSA** (`psa`) | named grading varieties | <https://www.psacard.com>. Population counts and omissions are never used as negative evidence. |
| **pokumon.com** (`pokumon`) | per-market promo printings | Collector database. Indexes English names only and lumps all Western languages into one row; absence is never used to contradict a Western language. |
| **Elite Fourum** (`elitefourum`) | collector-community facts: promo languages, 1st-edition timeline | Community forum, <https://elitefourum.com>. |
| **LigaPokemon** (`ligapokemon`) | Brazilian/Portuguese marketplace listings | <https://www.ligapokemon.com.br>. Marketplace listing evidence. |

## Evidence that is not a link

Some confirmations rest on the collection owner's inspection of a physical card, recorded as
`Owner attestation (domain expert)` or `Physical card, photographed specimen`. These are
represented in the source registry as **anonymous named evidence classes**, never as fabricated
hyperlinks and never with personal identifiers. Their publication is subject to the owner's
consent (see `LICENSE.md`, *Open decisions*).

## Reporting

If you hold rights in material used here and want it removed or its attribution corrected, open
an issue at <https://github.com/m4s-ai/snoredex-data/issues>.
