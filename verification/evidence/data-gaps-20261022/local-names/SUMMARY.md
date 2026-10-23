<!-- doc: role=retained research workstream report; stage=history -->

> Historical record — research snapshot from 2026-10-22; current gaps are determined by canonical stores.

# local-names: summary (2026-10-22)

Field: `localCardName`. Targets: 16 `species:<language>` + pattern×language + all 1030 catalogue items.
Every item appears in findings or unresolved (`findings.json`). Tools that rebuild it are in `tools/` (`build.py` and the `mk*.py` scripts).

## Counts
- Species: all 16 languages found (official Pokédex: ja, zh-Hant, zh-Hans, it, es-419; official card DB: th, id, ko (repo snapshot); owner specimens: en, de, fr, es-ES, pt, nl, pl, ru).
- Patterns: 124 pattern×language findings; 4 unresolved (Thai Eevee & Snorlax GX, Thai Snorlax GX, es-ES Snorlax Lv.35, Italian Snorlax δ).
- Exact prints: 905 of 1030 items have at least one per-print source (968 item finding rows in all); 125 items unresolved.
  Items with null localCardName: 713 of 782 resolved (ja 104/108, de 99/105, en 116/124, fr 98/104, it 90/104,
  es-ES 71/85, pt 70/79, zh-Hans 56/62, ru 3/5, nl 4/4, pl 2/2).
- Conflicts with existing non-null localCardName: 0 against a per-print source. (A parser bug briefly showed Thai/Indonesian Hop's as conflicts; it was fixed: the official h1 is `คาบิกอน <ของฮ็อป>` / `Snorlax <Hop>`, which matches the dataset.)

## Sources (per-print rows)
TCGdex per-language card records 556 (mapped via reviewed finish-unit URLs; TG10 remapped to swsh11tg-TG10);
asia.pokemon-card.com tw/th/id detail pages 139 (repo-retained run 20261008T220000Z); pokemon-card.com JP detail pages 84 (53 pages fetched);
pokemoncard.co.kr structured snapshot 68; owner specimen photos 55 and Cardmarket product images 53 (visual transcription); pokemon.com IT archive 9; LATAM es-xl 4.

## Key format findings
- Hop's: DE "Hops Relaxo", FR "Ronflex de Nabil", IT "Snorlax di Hop", ES/LATAM "Snorlax de Paul", PT "Snorlax do Lupo", JP "ホップのカビゴン", KR "호브의 잠만보", TW "赫普的卡比獸", CN "赫普的卡比兽", TH "คาบิกอน <ของฮ็อป>", ID "Snorlax <Hop>".
- Eevee & Snorlax GX: DE "Evoli & Relaxo GX", FR "Évoli et Ronflex GX", IT/PT "Eevee e Snorlax GX", ES "Eevee y Snorlax GX", JP "イーブイ&カビゴンGX", KR "이브이&잠만보 GX", TW "伊布&卡比獸GX", CN "伊布&卡比兽GX".
- SV-era ex: DE "Relaxo-ex", FR "Ronflex-ex", IT "Snorlax-ex" (TCGdex hyphen), EN/ES/PT "Snorlax ex"; JP "カビゴンex", TW "卡比獸ex", TH "คาบิกอนex", KR "잠만보 ex".
- Doll: DE "Relaxo-Puppe", FR "Poupée Ronflex", IT "Bambola Snorlax", ES "Muñeco de Snorlax", PT "Boneco de Snorlax", JP "カビゴンドール", KR "잠만보인형", TW "卡比獸娃娃", CN "卡比兽娃娃", TH "ตุ๊กตาคาบิกอน", ID "Boneka Snorlax".
- Rocket's: JP "R団のカビゴン" / "R団のカビゴンex"; PT TRR 104 "Snorlax ex dos Rockets" (specimen SPEC-0052). Hungry Snorlax JP "くいしんぼカビゴン". RU species "Снорлакс".
- Levels are not part of the name. TCGdex FR appends "Niv. 37/40/X" (flagged). LV.X is handled inconsistently across sources (see the pattern notes).

## Rejected / dead ends
- TCGdex `ja` for PCG1/PCG3/PCG9 returns English placeholder names ("Snorlax", "Rocket's Snorlax Ex", "Snorlax（デルタ種）"). Rejected; these were resolved from images instead.
- TCGdex LOR TG10 legacy key `swsh11-010` now returns Dustox/Pudox/Papinox. Rejected; current key `swsh11tg-TG10` used.
- pokemon.com Pokédex en/de/fr/es/br and card-archive pages: HTTP 403 (WAF), intermittent; only it/es-xl Pokédex and 5 IT card pages succeeded. pokemonkorea.co.kr: 503. pokemon.cn product pages show no card-name text.
- CN placeholder items (s4/sH/sI100/svIba images) carry Japanese card images, so they are not SC evidence.

## Leads (not conflicts)
- TH `s5a T 093` ×2 and `s10a T 077` have existing localCardName "Snorlax" (Latin). Every Thai official record uses "คาบิกอน". No per-print source was found, so these need checking.
- TH `AS1b 112` "คาบิกอน GX" and `SM-P 083` "อีวุย&คาบิกอน GX" include a space. Other Thai official names have none (คาบิกอนV/ex). They are unverified.
- TW `SM-P 053` "伊布&卡比獸 GX" (with space), while the official TW AS5a/AS5D records read "伊布&卡比獸GX". This is a different print, so it is not a conflict.
- Retry pokemon.com archive (dp1/37, g1/58, sm115/50, xyp/XY179) from a browser for it/pt/es/de.
