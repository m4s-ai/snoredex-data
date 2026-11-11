---
name: card-search
description: Search online for evidence of specific Snoredex cards supplied in the prompt or an issue, inspect exact-card sources and images, and route accepted findings into retained evidence and scoped commits. Excludes set discovery, whole-setlist evaluation and foundational market research.
---

<!-- doc: role=targeted card-search workflow skill; stage=task -->

# Card search

Find checkable evidence for the requested cards and missing fields. Derive targets from the
current request; there is no standing card list, issue number or backlog in this skill.
Commands run from the repository root.

## Card-search scope

Read [AGENTS.md](../../../AGENTS.md). Before accepting evidence, read the evidence ladder and the
source techniques in [METHODOLOGY.md](../../../METHODOLOGY.md); for finishes or markings also read
its finish section.

- For an issue request, read its current body, comments and relevant linked PRs. Reconcile open
  rows with `data/` and retained evidence; historical remaining-work lists may be stale.
- For a set-and-number request, resolve language/locality, local set code, full collector number
  including denominator, and requested fields. Preserve leading zeroes and source-native suffixes.
  Ask only for unresolved distinctions that affect identification; continue independent targets.
- Map existing item, release, claim and SPEC IDs. Separate identity gaps from missing finish,
  date, rarity, image or provenance. An unadmitted target is searchable without inventing an ID.
- Check retained photographs, hashes, source captures and previous queries first. For “continue”,
  resume unanswered fields instead of requesting already retained images again.

**Boundary:** discovering sets, processing entire PDFs/checklists, mapping market launches,
general rarity/finish rules and provider-wide refreshes are outside this skill and need their own
explicit task. Reading an exact setlist row to support a
target does not authorize harvesting the rest of that set. Applying an
already supplied source belongs to [claim evidence](../snoredex-claim-evidence/SKILL.md); supplied
photos go to [specimen intake](../snoredex-specimen-intake/SKILL.md).

## Card-search retrieval

Work in bounded rounds over the requested targets. Keep a compact per-target record of queries,
inspected URLs, findings and blockers, prioritizing fields a source can actually establish.

1. Search exact local set code and full number, then native card name, local-language spelling
   and English name. Try padded/unpadded numbers and slash/space spellings separately. Templates:
   `"{setCode}" "{number}/{denominator}"`, `"{nativeName}" "{number}"`,
   `site:{marketplaceDomain} "{setCode}" "{number}"`. Search aliases are not identity mappings.
2. Check exact-card publisher pages and reviewed providers for printed identity fields. For
   physical treatment, seek actual card photographs. Web/image results and snippets are leads:
   open and inspect the original source before accepting a claim.
3. Use seller sources where relevant: Cardmarket offer photographs (see METHODOLOGY.md's
   Cardmarket section), eBay including sold/completed listings, regional Shopee,
   Korean Bunjang, Thai local shops/classifieds such as LnwShop/OjamaCard, and comparable local
   marketplaces. These are options, not guaranteed endpoints. Search quoted titles or item IDs
   for alternate pages and expired listings; a seller's location does not establish card language.
4. Inspect carousel views and click zoom/media viewers for readable originals. Retain listing
   and actual image URLs. Shopee CDN, Bunjang media, eBay image and shop-hosted image links may
   remain accessible when a listing fails. Follow exposed or user-supplied URLs; guessed variants
   are unverified until fetched and inspected. A resized preview is not the original resolution.
5. For blocked pages, try the available browser (see the access notes in METHODOLOGY.md's source
   techniques), then an independent source. Record login/403/expired-image limits; do not retry indefinitely or bypass
   access controls. If images remain inaccessible, give the user both listing and direct-image
   links, target identity and missing field so they can supply the image. Never claim inspection
   of unavailable bytes.

Stop a round when requested fields are supported, promising independent routes are exhausted,
or a specific image/clarification is needed. Record the next useful lead. Zero results and missing
photos are search limitations, never evidence that a printing does not exist.

## Search coverage before reporting remaining gaps

Keep one row per current target and missing field, with attempted routes, inspected evidence,
access blockers and the next useful lead. Reviewing supplied seller links is a link-intake batch,
not coverage of every open card. Distinguish an unsearched route from a searched route with no
usable evidence; neither proves absence.

For a finish gap, inspect the matching localized product article's explanatory text as well as
its exact card row. An explicit deck finish statement may support a named target when language,
product, set symbol and full number match; do not transfer another language's finish or close an
inventory from source silence. Preserve the source wording and its scope separately.

Search native product/distribution aliases and broad multi-variant offers when titles omit card
numbers. Search relevant regional marketplace domains too: an Indonesian card can be sold
elsewhere. Verify the printed language, not the seller's country. Inspect relevant selectors and
carousel images; record when access prevents that inspection. Compare retrieved image hashes
with retained renders before reporting a new photograph or independent corroboration.

When investigating a missed offer, separate demonstrated search-coverage gaps from unknown
historical availability. A listing found today does not prove it was indexed during an earlier run.

## Card-search evidence decisions

Match the visible card face: language/locality markers, set code, numerator **and denominator**,
name/artwork and other identity cues. Titles and categories may be wrong; imported cards and
catch-up/reprint releases must not be assigned to the wrong target. Record unexpected identities
as separate leads. Do not expand the requested scope automatically.

Follow specimen intake's local OCR and visual-inspection guidance; record tool/readability limits.
OCR supports printed text, not foil. Assess identity, rarity, artist, finish and markings separately.
A digital render or legible scan may establish identity without physical finish. Lack of glare
does not prove non-holo. Preserve explicit owner determinations with field-specific attribution.
Never transfer finish from rarity, another language or a neighbouring card; a sale date is not a
release date.

Resolve the provider in `data/evidence.json` before accepting a claim. A source not listed there
stays a lead until a provider record is added with its tier, which needs authorization; never
grant it absence authority. Do not borrow another provider's authority. Reposted photos
and multiple URLs for one listing are not independent corroboration.

## Card-search retention and integration

For research-only requests, deliver evidence and unresolved links without changing verdicts.
When integration is authorized, use the manual procedures (there is no importer; entry is by hand):

| Finding | Retention and writer |
|---|---|
| Exact-card page/assertion | Retain a scoped capture under `verification/evidence/`: source URL, actual retrieval date, capture method, relevant content, SHA-256 and field limits. Distinguish excerpt hashes from full-response hashes. Apply through [claim evidence](../snoredex-claim-evidence/SKILL.md). |
| Photograph or identity-legible image | Follow [specimen intake](../snoredex-specimen-intake/SKILL.md). Preserve original bytes, SPEC ID, hash, listing/image provenance and only supported observations. |
| Target not yet in the catalogue | Retain the evidence and report it as a candidate; admitting a new printing adds a record to `data/printings.json` with a fresh `itemId` and needs explicit authorization. Keep unmapped candidates explicit. |

Derive evidence-directory and manifest names from this task and actual date. Accepted evidence
belongs outside ignored caches. Keep original bytes separate from OCR, crops or format conversions;
label derivatives and preserve their relation to originals. Exclude credentials, cookies and private
retrieval-backend configuration from commits.

Follow the [specimen collision check](../snoredex-specimen-intake/SKILL.md#specimen-intake-collision-check)
before allocation and integration. Reuse identical bytes. Multiple positively
matched views of one physical card use specimen intake's `sameCardAs` contract; do not overwrite
an original to add an angle or infer same-card identity solely from matching artwork.

A saved file or bare URL is not completed integration: the claim must cite the specimen or source,
`python scripts/check.py` must resolve every reference, and the rebuilt outputs must show it. Do not count one seller photo twice as
independent listing and specimen authority.

## Card-search validation and commits

Follow [issue delivery](../snoredex-issue-delivery/SKILL.md) for branch isolation, the complete
target/evidence record and handoff. Reconcile every accepted target before calling the batch done.
Respect session authorization, including “always put accepted findings in the PR” or draft-only
instructions when applicable; do not copy publication decisions from an unrelated research round.

1. Work on an isolated branch from current `origin/main`, with one `python scripts/regen.py --check`
   baseline.
2. Run `python scripts/check.py` after the accumulated edits. Review stable ids, photo hashes,
   supported fields and the references to them. Never hand-edit build outputs or touch the archive.
   Do not close a batch just because one card was found.
3. Run `python scripts/regen.py` once at delivery. Stage reviewed captures, images, data changes
   and the rebuilt outputs together. Inspect staged paths and diff;
   avoid blanket staging of unrelated research.
4. When authorized, commit with the repository's required trailer and push/update the scoped PR.
   After commit and push, run `python verification/publication_audit.py` for history-sensitive checks.
5. Report each target's supported fields, source/image links, SPEC/reference IDs, remaining gaps,
   validation and actual commit/PR status. Synchronize relevant issues/PRs when authorized; one
   resolved field does not complete a card's entire research task.

Merge and publication require their own authorization. Search success, retained evidence,
integrated claims and merged changes are separate outcomes; report only those actually reached.
