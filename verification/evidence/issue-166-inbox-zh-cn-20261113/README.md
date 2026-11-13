# Issue #166 photo drop-off — seven Simplified Chinese Snorlax cards (2026-11-13)

Provisional inbox arrival. The owner supplied these seven photographs directly in chat on 2026-11-13.
They are retained here byte-for-byte so the standing photo inbox in issue #166 has durable, hashed
originals. **Nothing here is integrated**: no `SPEC-nnnn` was allocated, no manifest was written and
no catalogue row changed. These are observations of what each card face shows, plus the catalogue
row each photograph most plausibly belongs to.

All seven files are 1920x2560 JPEG (RGB), i.e. phone originals, unmodified.

| File | Visible print | SHA-256 | Bytes |
|---|---|---|---|
| `01-cn-S-P-061-promo.jpg` | CN · S-P/CS 061 (promo) | `4c1565815d30451f62aedb4c470ac1e64410c0d9d5ee75ca2c58a046087acbbd` | 315558 |
| `02-cn-CS1DC-152-207.jpg` | CN · CS1DC 152/207 (Dynamax Clash V Starter Deck) | `939e57c802bb54946b4fa88c546823534bd3153bd80b853d8a8f9cc1153794b5` | 321296 |
| `03-cn-CS1aC-110-135.jpg` | CN · CS1aC 110/135 (Dynamax Clash - Thunder) | `c2ed41e83080f70b4b5fef09ade535ce87b1b2850d8b4702c2c094fef577887f` | 324051 |
| `04-cn-CSVE2C-122-207.jpg` | CN · CSVE2C 122/207 (Battle Party Shining Dream) | `31a844d3cca3ff40813d22355c131d1178d1d40e3b239842f5f50c9f803bdd21` | 305126 |
| `05-cn-CS2DaC-038-053.jpg` | CN · CS2DaC 038/053 (Family Combo) | `8b2512a414949c2320cb90e47b3ae955df512eb984c24fcd2576ddfb003f4bf3` | 282632 |
| `06-cn-CSV7C-158-204-plain.jpg` | CN · CSV7C 158/204 (Blade Awakening) — matt | `3fc9f139c1d5323febaecbd8451e9c3fb3a5212e2962277d2a5350065d8f4222` | 285357 |
| `07-cn-CSV7C-158-204-foilpattern.jpg` | CN · CSV7C 158/204 (Blade Awakening) — Folienmuster unteres Drittel | `54d642e681b745087b3daed010fba5bcd46486576e541c8788ce569192a7225a` | 324699 |

## Observations read from the card faces

Read with a vision pass over the originals; printed glyphs only. Finish is a *proposed* classification
and needs owner confirmation — a single photograph does not decide foil treatment.

1. **061/S-P** — 150 KP, Illus. chibi, 滚动冲撞 80 / 重磅冲击 130, ©2023, PROMO box, no rarity symbol. Catalogue: `S-P/CS 061/` non-holo Promo (confirmed).
2. **CS1DC 152/207** — 150 KP, Illus. Eri Yamaki, 招来 (draw 2) / 瘫倒 120 + Asleep, D mark. Catalogue: `CS1DC 152/207` non-holo Fixed (confirmed).
3. **CS1aC 110/135** — 150 KP, Illus. Eri Yamaki, same two attacks, D mark, U. Catalogue: `CS1aC 110/135` — non-holo and reverse-holo are marketplace-claimed, mirror-holo is confirmed.
4. **CSVE2C 122/207** — 150 KP, Illus. 0313, ability 无畏脂肪 (Thick Fat) + 轰隆鼾声 180, F mark, ©2023. Catalogue: `CSVE2C 122/207` non-holo Fixed (confirmed).
5. **CS2DaC 038/053** — 160 KP, Illus. Oswaldo KATO, 重磅冲击 80, E mark, ©2023, C. Catalogue: `CS2DaC 038/053` non-holo Fixed (confirmed); the same card is `sH 038/053` in Traditional Chinese.
6. **CSV7C 158/204 (plain)** — 160 KP, Illus. Souichirou Gunjima, 填饱肚子 (attach Energy, heal 60) / 重磅冲击 160, H mark, U. Catalogue: `CSV7C 158/204` non-holo (marketplace-claimed).
7. **CSV7C 158/204 (foil pattern)** — same print; the foil band across the lower third shows a Poké Ball motif. Catalogue: `CSV7C 158/204` mirror-holo (confirmed), reverse-holo marketplace-claimed.

## Open determinations

- Images 3, 6 and 7 are the three rows the catalogue still carries as `marketplace-claimed` for a
  non-mirror finish (`CS1aC 110/135` non-holo, `CSV7C 158/204` non-holo, `CSV7C 158/204` reverse-holo).
  Whether images 3 and 6 are genuinely matte, and whether image 7 is the mirror or the reverse-holo
  product, needs the owner's determination; the vision pass cannot settle foil treatment.
- Image 3 reads as having sheen in the lower third in the automated description, which contradicts a
  plain non-holo reading. Treat it as finish-ambiguous until confirmed.

## Next step for intake

Run the specimen-intake workflow on these files with a local manifest path (the bytes are already in
this directory, no issue attachment is needed). One `SPEC-nnnn` per photograph; images 6 and 7
depict the same print and would need `sameCardAs` if the owner confirms they are views of one
physical card.

Source: owner chat message, 2026-11-13. Issue: https://github.com/M4S-ai/snoredex-data/issues/166
