<!-- doc: role=fifth research round unresolved Thai marketplace leads for issues 256 and 262; stage=reference -->
# Thai marketplace follow-up — 2026-09-21

This round adds research leads only. No card identity, finish, rarity, date, or absence verdict changes. The catalogue remains at 16/28 Thai releases without tracked-field gaps, 12 Thai releases still open, and 148/641 releases with tracked gaps overall. Draft PR #390 remains unmerged.

## Retrieval and limits

Exact Thai names, set codes and collector numbers were searched across Shopee, eBay, local retailers and broader web/image search. The accessible Shopee search pages exposed individual listing identifiers, but the ten leads below did not yield a usable inspected original card image in this round. An HTTP 200 application shell is not a recovered product page. No authentication challenge was bypassed and no seller was contacted.

Discovery pages:

- https://shopee.co.th/search?keyword=%E0%B8%84%E0%B8%B2%E0%B8%9A%E0%B8%B4%E0%B8%81%E0%B8%AD%E0%B8%99&page=0
- https://shopee.co.th/search?keyword=%E0%B8%84%E0%B8%B2%E0%B8%9A%E0%B8%B4%E0%B8%81%E0%B8%AD%E0%B8%99&page=4
- https://www.ebay.com.au/str/tcgbangkok
- https://www.ebay.com/itm/127890556065 (historical purchase-feedback lead for AS5D)

Search snippets and opened Shopee result pages differed, including an unrelated toy-only response for page 1. Neither snippet position nor title alone identifies a specimen. Plain JPEG/PNG originals remain required before physical observations enter the importer.

## Retained leads

| Target | Listing or store | Result / next check |
|---|---|---|
| TH:MA4:091/123 | https://shopee.co.th/product/136710401/41979577897 | Listing title associates C/SD with Thai MA4 091; no inspected image or finish inference. |
| TH:MA4:091/123 | https://shopee.co.th/product/42807282/51460937608 | Multi-option Void Blast / Mega Dream listing; foil wording cannot be assigned to MA4 from this title. |
| TH:s10a:058/071 | https://shopee.co.th/product/264581611/21684853745 | Exact number and Thai language advertised. Web reader failed; direct public HTTP returned an application shell without product image metadata. |
| TH:svM:094/175 | https://shopee.co.th/product/264581611/27226459086 | Generations multi-card listing advertises non-foil Thai ex cards including Snorlax; exact face and selected option unverified. Direct HTTP returned an application shell. |
| TH:s10b:056/071 | https://shopee.co.th/product/264581611/18716154951 | Thai Pokemon GO Rare multi-card listing includes Snorlax; no original photograph inspected. |
| TH:s8b:126/184 | https://shopee.co.th/product/100230873/11878972765 | VMAX Climax multi-card listing includes Snorlax; printed set and denominator unverified. Does not resolve existing 126/184 versus 126/158 conflict. |
| unresolved Thai Snorlax identity | https://shopee.co.th/product/425086629/13703047839 | Listing names Collect attack and U/SD; exact number/set not established. |
| multiple unresolved Thai Snorlax identities | https://shopee.co.th/product/412643607/52112008796 | Multi-option Thai Snorlax/Munchlax booster-card listing; exact options and images inaccessible. |
| TH:svM:094/175 | https://www.ebay.com.au/str/tcgbangkok | Search-indexed store page explicitly advertises Snorlax EX 094/175, Thai svM starter deck. Individual listing ID and original scan not recovered. No Rarity is seller wording; not finish evidence. |
| TH:AS5D:118/169 | https://www.ebay.com/itm/127877826164 | Historical listing identifier recovered from verified-purchase feedback on other TCG Bangkok listings; target returned HTTP 403. Sold feedback establishes only a lead, not card-face/finish verification. |

## Rejected transfers and next priorities

- eBay https://www.ebay.com/itm/334500578693 and https://www.ebay.co.uk/itm/389918062159 explicitly advertise Japanese s10b 056/071. A Thai search result or Thai marketplace location does not turn them into Thai evidence.
- SASOM's Snorlax category mixes Japanese and explicitly Thai rows; an unqualified svM entry cannot establish Thai identity.
- Existing Thai s10b digital rendering from round four remains insufficient for physical finish; additional retailer rarity wording does not cure that limitation.
- For svM, recover the specific eBay listing and original front scan, then match printed Thai text, svM T and 094/175. Assess finish separately from seller words such as No Rarity or non-foil.
- For s10a and s10b, recover the exact option photograph from the listed Thai seller. For MA4 multi-option listings, verify that any foil claim applies to MA4 rather than the adjacent MA3 choice.
- For s8b, first resolve the printed set/number conflict; do not transfer sc3b 126/158 evidence.

These are retrieval findings, not assertions of non-existence. No specimen IDs were allocated. Research leaves card facts unchanged; the separate review correction below changes export metadata.

## Review correction

Review comment 4061943684 identified a separate freshness bug: `analysis_confirmed_releases.json` reported 2026-09-10 while its finish evidence was generated on 2026-09-21. The exporter now takes the later language-check or finish-document date. A regression failed on the old export before the fix and checks both evidence inputs. This changes export metadata, not release dates, card facts or catalogue counts.

## Validation

The pre-change full check and final full regeneration/core gate passed. The new freshness assertion failed on the old export and passed after the fix. The catalogue, specimen registry, finish store and authoritative graph are byte-identical to aa134a6; only the confirmed-release generated field changes within that JSON export. Existing local browser validation was 155/155 at aa134a6; this round makes no UI changes. Post-push history checks and exact-head review are tracked in PR/issue updates.
