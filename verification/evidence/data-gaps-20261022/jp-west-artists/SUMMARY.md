<!-- doc: role=retained research workstream report; stage=history -->

# jp-west-artists — illustrator research (2026-10-22)

Targets: 80 card releases (42 JP + 38 WEST/LATAM). **Found 79, unresolved 1.**
All targets have a finding with `method`, following ARTIST-RULE.md:
- database-credit: 53 (pokemon-card.com 30, TCGdex 22, pokemon.com LATAM 1)
- image-transcription: 25 (credit read off an image of the exact print)
- artwork-propagation: 1 (Italian FL 15; anchor German FL 15 from TCGdex; tiny target image, composition matched)
- confidence: 71 high, 8 medium (credit legible only on upscaled 255px images: PJU, PCG1, PCG9,
  sm9 115, s1H 70, s5a 93, HIF 50 PT; plus the IT FL 15 propagation)

Unresolved: Italian DF 10. TCGdex has no it/ex15-10 and the repo has no image of an Italian copy.
Lead: EN DF 10 / JP PCG9 001 = Masakazu Fukuda is a ready anchor once an Italian image is found.

## Best sources
1. pokemon-card.com detail pages (official JP database): search API
   `resultAPI.php?keyword=カビゴン&regulation_sidebar_form=all&page=N` lists 58 entries, including
   promos (BW-P 207, XY-P 149/261) and DP1 (DPBP#174). Pt2, BW7 and XY10 are listed under the set
   mark files "DPt2-B", "BW7-B" and "XY10-B". In each case the number and denominator match.
2. TCGdex `/v2/{lang}/cards/{id}`: DE/EN/FR/IT/PT prints exist for JU, KSS, GEN (fr), BCR, PLS, BKT,
   FCO, VIV, PGO. Returns 404 for es/base2, pt/base2, it/ecard3, it/ex6, it/ex15, pt/dp1, it/pt g1 and
   pt/sm115. Returned 503 for ja/PCG*.
3. Repo specimen photographs (verification/specimens, copied into raw/repo_*) and Cardmarket product
   images (images/). These were used for Method A on old JP prints and on PT/ES/IT localized prints.

## Dead ends
- pokemontcg.io v2 returned 500/502 for base2-11, base2-27, gym1-33, xy0-26 and swsh1-206.
  g1-58, xy2-80, swsh6-224 and sm9-191 worked.
- pokemon.com /el/ card pages for sv09/117 and me03/63 return a bot interstitial (403).
  svp/184 worked.
- pkparaiso.com: connection reset, so the repo copy SPEC-0131 was used.

## Notes and conflicts
- No conflicts with the dataset: every target had `artist: null`.
- TCGdex ja SV4a-310 labels the set "レイジングサーフ" (Raging Surf), but the card is Shiny Treasure ex
  310/190. This is a TCGdex metadata error; the illustrator agrees with pokemon-card.com.
- PJU (1997 Japanese Jungle) prints a credit line on the card ("Illus Ken Sugimori").
- retrievedAt for repo-copied images is the time they were read from the repository (no web fetch).
  Web fetch times are in raw/_fetchlog.tsv.
