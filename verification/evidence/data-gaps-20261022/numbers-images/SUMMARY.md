<!-- doc: role=retained research workstream report; stage=history -->

# numbers-images — summary (2026-10-22)

Targets: 15 collectorNumber rows (14 distinct items) + 11 image rows. findings.json: 17 findings, 4 unresolved groups. Every target appears.

## collectorNumber
- Found (9 items):
  - DP1 Snorlax Lv.35 x3: `DPBP#174`. This is the DP Battle Pokédex ID printed on the card. It has no denominator. Source: official pokemon-card.com card 1082, with 52poke agreeing. Owner decides whether collectorNumber may hold it.
  - S-Chinese: s4 84 x2 -> `086/115` (浓墨重彩 黎); sH 038 -> `038/053`; sI100 341 -> `341/414`; 342 -> `342/414`; svIba 046 -> `046/066`. Source: the 52poke 简体中文版 rows, with PokéCottage SC rows agreeing. These match the prints already in source_first_prints.json.
  - Hungry Snorlax (UNP): "no collector number printed" (low confidence). 52poke files it under 无编号特典卡 ("Unnumbered Promo cards"), and the scans show only No.143.
- Unresolved (5 items): PJU x2, EXS x2, G2 Rocket's Snorlax. 52poke shows "—" in the number column, and the scans show only "No.143". No source we could reach says "unnumbered" outright. PokéCottage numbers (047/048, 34, 073/098) are its own catalogue indexes and are not printed on the cards.

## image
- Found (10): TCGdex EN JU 11/27, FR JU 11/27 and EN GH 33. PokéCottage scans for the JP EXS (1998-03-23), PCG1 074/082, PCG3 062/084 and PCG9 001/068. PokéWiki scan for DE JU 27/64.
- Unresolved (1): DE JU 11 holo. TCGdex de has no image, and the PokéWiki file named "Dschungel 11" actually shows 27/64.

## Cautions / conflicts
- Bulbagarden File:SnorlaxVendingS1.jpg carries the CoroCoro contest footnote, so it shows the Quick Starter Gift Set (1998-12-04) print and not the 1998-03-23 Expansion Sheet print.
- The PokéWiki file name does not match the card it shows (it is named 11 but shows 27/64).
- The EN TCGdex scans and the JP PCG scans show the 1st Edition print. The target edition field is null.
- The PCG1 074 scan looks holo, but the target finish is non-holo. No finish was inferred.
- The SC legacy rows carry JP release dates (e.g. svIba 2024-03-08). The SC releases are 2023-08-18, 2023-11-17, 2024-05-17 and 2026-01-16. This is for the date owner to handle.

## Best sources
1. pokemon-card.com official JP detail page and image (DP1).
2. TCGdex API and assets (EN/FR Jungle, Gym Heroes).
3. 52poke card pages (SC numbers). Fetch /wiki/ HTML; api.php parse needs a login.

## Dead ends
- Bulbapedia: 403 to curl and WebFetch.
- web.archive.org: connection reset.
- pikaqian.com: Cloudflare.
- 52poke api.php parse/raw: login or Cloudflare.
- pokemon-card.com has no rows before DP1.
- TCGdex ja PCG cards and de base2 cards have no image.
