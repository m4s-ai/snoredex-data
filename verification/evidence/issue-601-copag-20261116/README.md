# Copag blog pages behind the issue-601 Brazilian release events

Retained text of the fifteen Copag Pokémon blog articles that carry the Brazilian release
information for the `pt` set editions of the „Set-DB 13" work (issue #601). They are kept so every
release event can cite a file (`sourceRef`) instead of a link that may rot: the articles sit in a
CMS whose URLs are not stable, and the Wayback Machine answers `429` under bursts.

Retrieved 2026-11-16 through the Wayback Machine's raw-capture endpoint
(`https://web.archive.org/web/2025id_/<article>`). `manifest.json` records per article the article
URL, the resolved capture URL with its timestamp, the byte count and SHA-256 of the retained text,
and the SHA-256 of the raw capture it was extracted from (the raw HTML itself is not committed —
it carries third-party contact addresses from embedded accreditation scripts, which the publication
audit's P4 rule forbids in the tracked tree).

The `.txt` files are the page text with scripts, styles and markup removed; addresses found in the
page were replaced by `[email removed]`. Nothing else was edited, and the quoted wording is
identical to the live capture.

## What each page proves

| Edition | File | Datum im Dokument | Größe |
|---|---|---|---|
| `BCR` | `pages/chegou-o-box-lendas-da-justica-do-bw-fronteiras-cruzadas.txt` | nur Monatsstempel `08.2013` | 10187 B |
| `CRE` | `pages/vem-ai-a-colecao-reinado-arrepiante.txt` | `Data de lançamento: 18/06/2021` | 10504 B |
| `DP` | `pages/colecao-pokemon-tcg-diamente-e-perola.txt` | nur Monatsstempel `05.2011` | 11195 B |
| `FCO` | `pages/pre-lancamento-de-xy10-fusao-de-destinos.txt` | nur Monatsstempel `06.2016` | 13158 B |
| `FLF` | `pages/vem-por-ai-conheca-as-novidades-da-colecao-xy-flash-de-fogo.txt` | nur Monatsstempel `08.2014` | 10863 B |
| `FST` | `pages/nova-colecao-golpe-fusao.txt` | `Data de lançamento: 26/11/2021` | 11795 B |
| `KSS` | `pages/vem-ai-os-boxes-xy-com-os-pokemon-iniciais-de-kalos.txt` | nur Monatsstempel `05.2014` | 9804 B |
| `LOR` | `pages/nova-colecao-origem-perdida.txt` | `Data de lançamento: 16/09/2022` | 13139 B |
| `MEW` | `pages/nova-colecao-especial-escarlate-e-violeta-151.txt` | `Data de lançamento: 22/09/2023` | 12706 B |
| `PAF` | `pages/novos-produtos-de-destinos-de-paldea.txt` | `Data de lançamento: 23/02/2024` | 12461 B |
| `PGO` | `pages/novos-produtos-da-colecao-pokemon-go.txt` | `Data de lançamento: 07/10/2022` | 11269 B |
| `PLS` | `pages/tudo-sobre-a-nova-colecao-black-white-tempestade-de-plasma.txt` | nur Monatsstempel `09.2013` | 13590 B |
| `RCL` | `pages/rixa-rebelde-metagame-inesperado.txt` | nur Monatsstempel `05.2020` | 12845 B |
| `SSH` | `pages/torneios-de-lancamento-de-ee1-espada-e-escudo.txt` | nur Monatsstempel `01.2020` | 9574 B |
| `TEU` | `pages/torneios-de-lancamento-sl9-uniao-de-aliados.txt` | nur Monatsstempel `01.2019` | 26804 B |

**Neun Artikel tragen nur einen Monatsstempel** (`08.2013`, `05.2011`, …) und kein Feld
`Data de lançamento`; diese Editionen sind mit Monatspräzision erfasst. Der Monatsstempel ist das
Datum des Artikels, nicht notwendig der Verkaufsstart — er ist die einzige brasilianische Angabe, die
es für diese Sets gibt. Sechs Artikel tragen ein echtes `Data de lançamento` (Tagesdatum).

## Provenance rules that apply here

- A capture is evidence of what the page said **at its capture date**, not of today's page. Cite the
  capture, not the live URL.
- The article text is Portuguese and was not translated; dates are quoted verbatim as `DD/MM/YYYY`
  (Brazilian order) and stored as ISO dates in `data/`.
- `releases-601.json` maps every retained file to its edition, the exact quoted wording and what
  that wording proves.
