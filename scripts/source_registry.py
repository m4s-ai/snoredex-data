#!/usr/bin/env python3
"""Build the canonical source and attribution registry (#6).

Sourcing was spread across four stores that each recorded provenance differently: language
evidence in `units.json`, finish evidence in `finish_units.json`, a partial curated registry in
`finish_overrides.json`, and edition/artist/image provenance only in prose. Nothing tied a URL to
a *provider*, so the public sourcing section could not be generated and no check could catch an
orphaned or malformed reference.

This produces two generated artifacts:

* `verification/source_registry.json` — provider entries plus a canonical evidence index, one row
  per unique source with the stable IDs it supports and how often it is used;
* `verification/SOURCES.md` — the readable provider summary.

Providers are matched by URL host and by the `sourceType` wording the stores already use. A
source that matches no provider is an error, not a silent "other": the whole point is that every
claim is attributable.

Evidence that is not a URL — owner attestation, photographed specimen — is represented as a
named evidence class with a `nonUrlEvidenceId`, never as a fabricated hyperlink.

    python scripts/source_registry.py
    python scripts/source_registry.py --check   # fail if regeneration would change the output
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "verification" / "source_registry.json"
MARKDOWN_PATH = ROOT / "verification" / "SOURCES.md"


def official_finish_manifest_scopes() -> list[str]:
    """Keep provider absence scopes aligned with the canonical finish-source registry."""
    document = json.loads((ROOT / "verification" / "finish_overrides.json").read_text(encoding="utf-8"))
    official_hosts = {"assets.pokemon.com", "www.pokemon.com", "d1wx537rtdixyy.cloudfront.net"}
    return sorted({
        source["url"]
        for source in document["sources"].values()
        if source.get("supportsAbsence") is True
        and source.get("coverage") == "complete-manifest"
        and urlsplit(source.get("url") or "").hostname in official_hosts
    })

# --------------------------------------------------------------------------------------------
# Provider definitions
#
# `authorityTier` ranks how much weight a source carries. `supportsAbsence` says that a provider
# has one or more explicitly complete scopes; `absenceScopes` names the exact URLs that qualify.
# Provider authority is not itself an absence decision: the collection owner's final cross-source
# adjudications live in `verification/owner_adjudications.json` and are projected into the database.
# --------------------------------------------------------------------------------------------

PROVIDERS: list[dict[str, Any]] = [
    {
        "providerId": "pokemon-official",
        "displayName": "The Pokémon Company official cards and checklists",
        "organization": "The Pokémon Company International",
        "homepage": "https://www.pokemon.com",
        "hosts": ["assets.pokemon.com", "d1wx537rtdixyy.cloudfront.net", "www.pokemon.com"],
        "licenseOrTerms": "Publisher's own terms; used for identification and verification only.",
        "category": "official-publisher",
        "authorityTier": 1,
        "coverage": "positive localized card pages; complete manifests only within named checklists",
        "supportsAbsence": True,
        "usedFor": ["language", "finish", "product"],
        "absenceScopes": official_finish_manifest_scopes(),
        "attribution": "Official card pages and product checklists © The Pokémon Company International.",
        "notes": ("Localized card pages provide positive card/language evidence only. Exact "
                  "checklists may establish finish absence only inside their stated scope."),
    },
    {
        "providerId": "pokemon-cn-official",
        "displayName": "Pokémon official website (Mainland China)",
        "organization": "Pokémon (Shanghai) Toys Co., Ltd.",
        "homepage": "https://www.pokemon.cn/tcg/",
        "hosts": ["www.pokemon.cn", "pokemon.cn", "image.pokemon.com.cn"],
        "licenseOrTerms": "Publisher's own terms; used for identification and verification only.",
        "category": "official-publisher",
        "authorityTier": 1,
        "coverage": "positive Simplified Chinese card, product, rarity and finish statements",
        "supportsAbsence": False,
        "usedFor": ["language", "finish", "product"],
        "attribution": "Mainland Chinese card and product data © Pokémon (Shanghai) Toys Co., Ltd.",
        "notes": ("Only explicit retained publisher statements and card renders are positive "
                  "evidence; missing products, pages, cards or unstated finishes remain unknown."),
    },
    {
        "providerId": "pokemon-card-jp",
        "displayName": "Pokémon Card official database (Japan)",
        "organization": "The Pokémon Company",
        "homepage": "https://www.pokemon-card.com",
        "hosts": ["www.pokemon-card.com", "pokemon-card.com"],
        "licenseOrTerms": "Publisher's own terms.",
        "category": "official-publisher",
        "authorityTier": 1,
        "coverage": "Japanese-market cards and illustrators",
        "supportsAbsence": False,
        "usedFor": ["language", "artist", "date"],
        "attribution": "Japanese card data © The Pokémon Company.",
        "notes": "Never returns Japanese secret/rainbow prints; their absence is not evidence.",
    },
    {
        "providerId": "pokemon-card-asia",
        "displayName": "Pokémon Card official database (Asia)",
        "organization": "The Pokémon Company",
        "homepage": "https://asia.pokemon-card.com",
        "hosts": ["asia.pokemon-card.com"],
        "licenseOrTerms": "Publisher's own terms.",
        "category": "official-publisher",
        "authorityTier": 1,
        "coverage": "recent Traditional Chinese, Indonesian and Thai cards",
        "supportsAbsence": False,
        "usedFor": ["language"],
        "attribution": "Asian card data © The Pokémon Company.",
        "notes": "Recent releases only; older printings are out of coverage.",
    },
    {
        "providerId": "pokemon-card-korea",
        "displayName": "Pokémon Card official database and rules (Korea)",
        "organization": "Pokémon Korea",
        "homepage": "https://pokemoncard.co.kr",
        "hosts": ["pokemoncard.co.kr", "www.pokemoncard.co.kr", "pokemonkorea.co.kr",
                  "www.pokemonkorea.co.kr"],
        "licenseOrTerms": "Publisher's own terms.",
        "category": "official-publisher",
        "authorityTier": 1,
        "coverage": "positive historical Korean card details and official product/rules documents",
        "supportsAbsence": False,
        "usedFor": ["language", "product"],
        "attribution": "Korean card and product data © Pokémon Korea.",
        "notes": ("Historical card-detail endpoints may return HTTP 410; retained exact positive "
                  "observations remain card evidence, while endpoint silence proves nothing."),
    },
    {
        "providerId": "tcgdex",
        "displayName": "TCGdex",
        "organization": "TCGdex",
        "homepage": "https://tcgdex.dev",
        "hosts": ["api.tcgdex.net", "tcgdex.net", "tcgdex.dev"],
        "licenseOrTerms": "Open card database; see https://tcgdex.dev.",
        "category": "open-database",
        "authorityTier": 2,
        "coverage": "card existence per language; positive normal/holo/reverse flags",
        "supportsAbsence": False,
        "usedFor": ["language", "finish"],
        "attribution": "Card data from TCGdex.",
        "notes": "Upstream documents its variant coverage as incomplete, so a false flag is never absence.",
    },
    {
        "providerId": "bulbapedia",
        "displayName": "Bulbapedia",
        "organization": "Bulbagarden",
        "homepage": "https://bulbapedia.bulbagarden.net",
        "hosts": ["bulbapedia.bulbagarden.net"],
        "licenseOrTerms": "CC BY-NC-SA 2.5 — attribution and ShareAlike apply to derived content.",
        "category": "fan-wiki",
        "authorityTier": 2,
        "coverage": "set lists, release fields, per-language articles, promo series",
        "supportsAbsence": False,
        "usedFor": ["language", "edition", "date", "finish"],
        "attribution": "Content from Bulbapedia, licensed CC BY-NC-SA 2.5.",
        "notes": "Tier 2 by owner decision, 2026-08-03. It sat at tier 3 beside retailer listings while carrying 247 of the 252 claims that rested on a single tier-3 source — more of this dataset than anything but TCGdex. The tier is meant to record dependability, and its contributors are dedicated researchers, so the rank now says what the project actually does with their work. Preferred for set release dates when the article identifies the matching market field. Korean and Chinese promo articles are {{incomplete}}-tagged; never contradict on their silence.",
    },
    {
        "providerId": "tcgcsv",
        "displayName": "TCGCSV (TCGplayer product data)",
        "organization": "TCGCSV",
        "homepage": "https://tcgcsv.com",
        "hosts": ["tcgcsv.com", "www.tcgcsv.com"],
        "licenseOrTerms": "Redistributed TCGplayer catalogue data; see https://tcgcsv.com.",
        "category": "marketplace-catalogue",
        "authorityTier": 3,
        "coverage": "product identity and positive Normal/Holofoil/Reverse Holofoil subtypes",
        "supportsAbsence": False,
        "usedFor": ["finish", "product"],
        "attribution": "Product data via TCGCSV, sourced from TCGplayer.",
        "notes": "Subtype omission is a catalogue gap, not proof a finish does not exist.",
    },
    {
        "providerId": "psa",
        "displayName": "PSA certification and registry",
        "organization": "Professional Sports Authenticator",
        "homepage": "https://www.psacard.com",
        "hosts": ["www.psacard.com", "psacard.com"],
        "licenseOrTerms": "Site terms; used for identification only.",
        "category": "grading-registry",
        "authorityTier": 2,
        "coverage": "named grading varieties for graded specimens",
        "supportsAbsence": False,
        "usedFor": ["finish"],
        "attribution": "Grading variety names from PSA.",
        "notes": "Population counts and omissions are never used as negative evidence.",
    },
    {
        "providerId": "cgc",
        "displayName": "CGC certification and registry",
        "organization": "Certified Guaranty Company",
        "homepage": "https://www.cgccards.com",
        "hosts": ["www.cgccards.com", "cgccards.com"],
        "licenseOrTerms": "Site terms; used for identification only.",
        "category": "grading-registry",
        "authorityTier": 2,
        "coverage": "named certifications and concrete collector-registry specimens",
        "supportsAbsence": False,
        "usedFor": ["finish", "language"],
        "attribution": "Certification and registry variety names from CGC.",
        "notes": "A certification or collector-registry row is positive specimen evidence only. Personal sets, population counts and omissions are never negative evidence.",
    },
    {
        "providerId": "pokumon",
        "displayName": "pokumon.com",
        "organization": "pokumon.com",
        "homepage": "https://pokumon.com",
        "hosts": ["pokumon.com", "www.pokumon.com"],
        "licenseOrTerms": "Site terms.",
        "category": "collector-database",
        "authorityTier": 3,
        "coverage": "one row per Asian market printing; Western printings lumped into a single English row",
        "supportsAbsence": False,
        "usedFor": ["language", "finish"],
        "attribution": "Promo printing data from pokumon.com.",
        "notes": "Indexes English names only. Exact per-card pages can positively state a finish, but omissions never contradict a language or finish.",
    },
    {
        "providerId": "pokecottage",
        "displayName": "PokéCottage",
        "organization": "PokéCottage",
        "homepage": "https://pokecottage.com",
        "hosts": ["pokecottage.com", "www.pokecottage.com", "pokecottagecdn.com",
                  "www.pokecottagecdn.com"],
        "licenseOrTerms": "Site terms; fan-made collector content.",
        "category": "collector-checklist",
        "authorityTier": 3,
        "coverage": ("positive card, set, promo and named-variant rows for English, Japanese "
                     "and Simplified Chinese, plus corroboration of explicitly matched Western releases"),
        "supportsAbsence": False,
        "usedFor": ["language", "finish", "product", "date", "artist", "rarity"],
        "attribution": "Card, set, promo and variant confirmation from PokéCottage.",
        "notes": ("Inspect the Snorlax master list and matching set guides when a newly announced "
                  "or released set contains Snorlax. An exact retained row is tier-3 positive "
                  "confirmation for the card, set, promo, date, artist or named variant it states. "
                  "For another Western language, carry only facts shown to belong to an already "
                  "identified matching release and retain that equivalence basis. Omissions, zero "
                  "results and unstated alternatives never establish absence or completeness."),
    },
    {
        "providerId": "pokecardex",
        "displayName": "PokéCardex",
        "organization": "PokéCardex",
        "homepage": "https://www.pokecardex.com",
        "hosts": ["pokecardex.com", "www.pokecardex.com", "pokecardex-scans.b-cdn.net"],
        "licenseOrTerms": "Site terms; scan images are used for identification and verification only.",
        "category": "collector-database",
        "authorityTier": 3,
        "coverage": "positive card identity and source-labelled variants shown by retained scans",
        "supportsAbsence": False,
        "usedFor": ["language", "identity", "finish", "product"],
        "attribution": "Card scans and variant labels from PokéCardex.",
        "notes": ("A retained scan and its deck-specific page may establish only the visible card "
                  "identity and the variant that page positively labels. Missing cards, variants, "
                  "or languages never establish absence or completeness."),
    },
    {
        "providerId": "pkparaiso",
        "displayName": "PKParaiso",
        "organization": "PKParaiso",
        "homepage": "https://www.pkparaiso.com",
        "hosts": ["pkparaiso.com", "www.pkparaiso.com"],
        "licenseOrTerms": "Site terms; scan images are used for identification and verification only.",
        "category": "collector-database",
        "authorityTier": 3,
        "coverage": "positive localized card identity shown by retained database scans",
        "supportsAbsence": False,
        "usedFor": ["identity"],
        "attribution": "Card scans from PKParaiso.",
        "notes": "A retained database scan establishes only the visible card identity. Missing "
                 "cards, variants, or languages never establish absence or completeness.",
    },
    {
        "providerId": "wikidex",
        "displayName": "WikiDex",
        "organization": "WikiDex",
        "homepage": "https://www.wikidex.net",
        "hosts": ["wikidex.net", "www.wikidex.net", "wikidexcdn.net", "images.wikidexcdn.net"],
        "licenseOrTerms": "Site terms; hosted scan images are used for identification and verification only.",
        "category": "collector-database",
        "authorityTier": 3,
        "coverage": "positive localized card identity shown by retained database scans",
        "supportsAbsence": False,
        "usedFor": ["identity"],
        "attribution": "Card scans from WikiDex.",
        "notes": "A retained database scan establishes only the visible card identity. Missing "
                 "cards, variants, or languages never establish absence or completeness.",
    },
    {
        # Added on the owner's evidence in #119: a Japanese secondhand marketplace whose listings
        # photograph the actual card rather than reusing a stock image. That is the whole value —
        # for a fixed-deck Japanese product neither TCGdex nor the official card database records a
        # finish (FINISH_SOURCES.md: the JP card page carries no finish vocabulary at all), so a
        # photograph of the card face is the only route to one.
        #
        # Tier 2 for the same reason cardmarket-listing-photo is: the card text is legible and the
        # printing identifiable, but the listing cannot be re-examined once it sells, and the seller
        # may have mislabelled it. Filed as a SPEC record so the observation outlives the listing.
        "providerId": "snkrdunk",
        "displayName": "SNKRDUNK",
        "organization": "SODA Inc.",
        "homepage": "https://snkrdunk.com",
        "hosts": ["snkrdunk.com", "cdn.snkrdunk.com"],
        "licenseOrTerms": "Marketplace listing content; listing photographs are the seller's.",
        "category": "marketplace",
        "authorityTier": 2,
        "coverage": "individual Japanese-market cards whose finish and card text were read from a "
                    "seller's listing photograph",
        "supportsAbsence": False,
        "usedFor": ["finish", "language"],
        "attribution": "Card photographs from SNKRDUNK marketplace listings.",
        "notes": "Positive evidence only, and no absence scopes are declared: a card missing from "
                 "this marketplace says nothing about whether it was printed. Listings are removed "
                 "once sold, so every use must be recorded as a SPEC-nnnn specimen with the listing "
                 "URL and the image bytes committed, never as a bare link.",
    },
    {
        "providerId": "52poke",
        "displayName": "52poke (Wiki)",
        "organization": "52Poké (神奇宝贝百科)",
        "homepage": "https://wiki.52poke.com",
        "hosts": ["wiki.52poke.com", "s1.52poke.com", "s2.52poke.com"],
        "licenseOrTerms": "Wiki content; attribution per CC BY-NC-SA.",
        "category": "collector-database",
        "authorityTier": 2,
        "coverage": "Traditional-Chinese / Simplified-Chinese market card and set data (卡比獸/Munchlax-family and set composition)",
        "supportsAbsence": False,
        "usedFor": ["language", "artist", "edition", "finish"],
        "attribution": "T-Chinese/S-Chinese card data from 52poke Wiki.",
        "notes": "Added on the owner's recommendation (#84, 2026-08-04) as the trustworthy source for T-Chinese products. Category coverage: dedicated Chinese-market wiki. Absence-capable scopes are NOT declared, so silence here never contradicts a T-Chinese claim on its own — positive evidence only. Static image host s1.52poke.com is reachable without bot protection; the wiki pages themselves sit behind a JS challenge.",
    },
    {
        # Added on the owner's recommendation (#88): "add this site as source - use it as starting
        # point for further research of korean pokemon cards." Korean is the market the toolchain
        # reaches worst — TCGdex serves a `ko` locale but holds one Snorlax-family record, and it
        # is a Trainer item — so a Korean-first catalogue is the gap this fills.
        "providerId": "koreanpokemoncards",
        "displayName": "koreanpokemoncards.com",
        "organization": "koreanpokemoncards.com",
        "homepage": "http://www.koreanpokemoncards.com",
        "hosts": ["koreanpokemoncards.com", "www.koreanpokemoncards.com"],
        "licenseOrTerms": "Site terms.",
        "category": "collector-database",
        "authorityTier": 3,
        "coverage": "Korean-market set and promo listings",
        "supportsAbsence": False,
        "usedFor": ["language", "finish"],
        "attribution": "Korean printing data from koreanpokemoncards.com.",
        "notes": "Declared before any claim cites it, so the research it is meant to start has a place to land. Prove it covers a category before reading its silence as evidence: rule 3 applies here as it does to pokumon, whose Western coverage is one lumped English row.",
    },
    {
        "providerId": "elitefourum",
        "displayName": "Elite Fourum",
        "organization": "Elite Fourum community",
        "homepage": "https://elitefourum.com",
        "hosts": ["elitefourum.com", "www.elitefourum.com"],
        "licenseOrTerms": "Forum terms; community-contributed content.",
        "category": "collector-community",
        "authorityTier": 2,
        "coverage": "promo language tables and the 1st-edition timeline within their stated scope",
        "supportsAbsence": True,
        "usedFor": ["language", "edition"],
        "absenceScopes": [
            "https://www.elitefourum.com/t/black-star-promos-languages/36573",
        ],
        "attribution": "Collector-community reference tables from Elite Fourum.",
        "notes": "High-authority community reference, just below collection-owner authority. Its designated complete table is absence-capable within scope; other final absence decisions require a collection-owner adjudication. This capability is deliberate and pinned by verification/test_owner_adjudications.py; #66 questioned whether it sits well with rule 4, which admits only a complete official manifest, and left the decision with the owner. Nothing currently depends on it either way: all five units citing that thread also carry owner adjudications, so withdrawing it would move no row off not-printed.",
    },
    {
        "providerId": "ligapokemon",
        "displayName": "LigaPokemon",
        "organization": "Liga Pokémon",
        "homepage": "https://www.ligapokemon.com.br",
        "hosts": ["www.ligapokemon.com.br", "ligapokemon.com.br"],
        "licenseOrTerms": "Marketplace site terms.",
        "category": "marketplace",
        "authorityTier": 3,
        "coverage": "Brazilian/Portuguese market listings",
        "supportsAbsence": False,
        "usedFor": ["language", "finish"],
        "attribution": "Marketplace listings from LigaPokemon.",
        "notes": "Blocks datacenter IPs; retrieved through a residential browser session.",
    },
    {
        "providerId": "cardmarket",
        "displayName": "Cardmarket",
        "organization": "Cardmarket (Sammelkartenmarkt GmbH & Co. KG)",
        "homepage": "https://www.cardmarket.com",
        "hosts": ["www.cardmarket.com", "cardmarket.com", "product-images.s3.cardmarket.com"],
        "licenseOrTerms": "Site terms. Product images remain Cardmarket's; artwork remains the rights holders'.",
        "category": "marketplace-catalogue",
        "authorityTier": 5,
        "coverage": "product/filter metadata and retained Japanese or English product images",
        "supportsAbsence": False,
        "usedFor": ["product", "image", "finish"],
        "attribution": "Product catalogue and images via Cardmarket.",
        "notes": (
            "Retained product images may positively establish only facts visible on the pictured "
            "Japanese or English card, including a visible finish. Product/language filter "
            "combinations and catalogue language metadata do not establish a localized release "
            "or collector number; in particular, a Traditional Chinese filter is not evidence "
            "that the card was released under that product number. Missing products, images, "
            "filters, or listings never establish absence."
        ),
    },
    {
        "providerId": "pokemontcgio",
        "displayName": "pokemontcg.io",
        "organization": "Pokémon TCG Developers",
        "homepage": "https://pokemontcg.io",
        "hosts": ["api.pokemontcg.io", "pokemontcg.io"],
        "licenseOrTerms": "Open API; see https://pokemontcg.io.",
        "category": "open-database",
        "authorityTier": 2,
        "coverage": "English-market illustrator credits and exact set release dates",
        "supportsAbsence": False,
        "usedFor": ["artist", "date"],
        "attribution": "Illustrator and release data from pokemontcg.io.",
        "notes": "English-market only.",
    },
    {
        "providerId": "limitlesstcg",
        "displayName": "Limitless TCG",
        "organization": "Limitless",
        "homepage": "https://limitlesstcg.com",
        "hosts": ["limitlesstcg.com", "www.limitlesstcg.com"],
        "licenseOrTerms": "Site terms.",
        "category": "open-database",
        "authorityTier": 3,
        "coverage": "illustrator credits missing upstream from pokemontcg.io",
        "supportsAbsence": False,
        "usedFor": ["artist"],
        "attribution": "Illustrator data from Limitless TCG.",
        "notes": ("Named in the dataset's meta.artistSources for three cards missing upstream from "
                  "pokemontcg.io, but no card row attributes to it individually - those rows carry the "
                  "pokemontcg.io sourceType. Declared here so the gap is visible rather than implied."),
    },
    {
        "providerId": "play-pokemon",
        "displayName": "Play! Pokémon rewards gallery",
        "organization": "The Pokémon Company International",
        "homepage": "https://play.pokemon.com",
        "hosts": ["play.pokemon.com"],
        "licenseOrTerms": "Publisher's own terms.",
        "category": "official-publisher",
        "authorityTier": 1,
        "coverage": "complete-manifest for the Prize Pack series it lists",
        "supportsAbsence": True,
        "usedFor": ["finish", "product"],
        "absenceScopes": [
            "https://play.pokemon.com/en-us/rewards/gallery?filter=series7",
        ],
        "attribution": "Prize Pack contents © The Pokémon Company International.",
        "notes": "Official gallery of Prize Pack series contents; one of the few complete manifests here.",
    },
    {
        "providerId": "retailer-listing",
        "displayName": "Retailer and specialist card listings",
        "organization": "Various independent retailers",
        "homepage": None,
        "hosts": [
            "www.target.com", "exorgames.com", "shopping.fullcomp.jp", "www.pokeca.net",
            "www.ebay.de",
        ],
        "licenseOrTerms": "Individual retailer site terms; used for identification only.",
        "category": "retail-listing",
        "authorityTier": 3,
        "coverage": "individual listings whose photography identifies an exact physical printing",
        "supportsAbsence": False,
        "usedFor": ["finish", "product", "language"],
        "attribution": "Retail listings from independent sellers.",
        "notes": (
            "Grouped deliberately: these are one-off listings, not catalogues, so per-host "
            "provider entries would imply a coverage guarantee none of them offers. A listing "
            "counts only when its image identifies the printing; stock photography does not."
        ),
    },
    {
        "providerId": "internal-derivation",
        "displayName": "Internal derivation from a sibling record",
        "organization": None,
        "homepage": None,
        "hosts": [],
        "licenseOrTerms": "This project's own inference; covered by the project data licence.",
        "category": "internal",
        "authorityTier": 5,
        "coverage": "attributes carried across records established to be the same card",
        "supportsAbsence": False,
        "usedFor": ["artist"],
        "attribution": "Derived within this project from an equivalent record.",
        "notes": (
            "Not an external source, and deliberately labelled so. Used where an attribute is "
            "carried from a sibling printing of the same card - for example an Additionals "
            "product reusing the base printing's illustrator. The underlying claim still rests "
            "on whichever provider sourced the sibling."
        ),
    },
    {
        "providerId": "owner-attestation",
        "displayName": "Collection owner attestation",
        "organization": None,
        "homepage": None,
        "hosts": [],
        "licenseOrTerms": "Contributed to this project; published as an anonymous evidence class.",
        "category": "non-url-evidence",
        "authorityTier": 2,
        "coverage": "specimens physically held or inspected by the collection owner",
        "supportsAbsence": False,
        "usedFor": ["language", "finish", "edition"],
        "attribution": "Owner attestation (domain expert), recorded anonymously.",
        "notes": "Never rendered as a hyperlink. No personal identifiers are published.",
    },
    {
        "providerId": "inspected-specimen",
        "displayName": "Inspected physical specimen",
        "organization": None,
        "homepage": None,
        "hosts": [],
        "licenseOrTerms": "Photographs of physical cards; depicted artwork remains the rights holders'.",
        "category": "non-url-evidence",
        "authorityTier": 1,
        "coverage": "individual cards whose text and markings were read from a photograph",
        "supportsAbsence": False,
        "usedFor": ["language", "identity", "finish", "edition"],
        "attribution": "Physical card, inspected specimen.",
        "notes": "The strongest evidence class here: it defeated three databases at once on XYPR 179. Named for the act that is on the record. It was `photographed-specimen` until 2026-08-03, but no photograph is committed for any of the six specimens, so the label promised a file a reader could open and none existed. The recorded inspection is the evidence either way; rename it back once images land in verification/specimens/.",
    },
    {
        # Cardmarket appears twice on purpose. The catalogue above is tier 5 — the thing this
        # project exists to check. A seller's photograph of the physical card is evidence, and rule
        # 1 has always said so; there was simply no provider to record it under, so the rule was
        # unusable (owner decision, 2026-08-03).
        "providerId": "cardmarket-listing-photo",
        "displayName": "Cardmarket seller listing photograph",
        "organization": "Cardmarket (Sammelkartenmarkt GmbH & Co. KG)",
        "homepage": "https://www.cardmarket.com",
        "hosts": [],
        "licenseOrTerms": "Seller photographs remain the seller's; depicted artwork remains the rights holders'.",
        "category": "marketplace-photo",
        "authorityTier": 2,
        "coverage": "individual cards whose text and markings were read from a seller's listing photograph",
        "supportsAbsence": False,
        "usedFor": ["language", "identity", "finish", "edition"],
        "attribution": "Seller listing photograph via Cardmarket.",
        "notes": "Tier 2, below an owner-inspected specimen: the card text is legible, but it cannot be re-examined and the seller may have mislabelled the language. Record it as a SPEC-nnnn specimen with heldBy 'third-party seller' and the listing URL, never as a bare link — listings are deleted and the observation must outlive them. Positive evidence only: a listing's absence proves nothing, and the language filter above it is not evidence at all. No open API; collection is by hand or a browser session, subject to a rolling ~55-request quota before HTTP 429.",
    },
    {
        "providerId": "seller-listing-photo",
        "displayName": "Seller listing photograph",
        "organization": "Various online marketplaces",
        "homepage": None,
        "hosts": [],
        "licenseOrTerms": "Seller photographs remain the seller's; depicted artwork remains the rights holders'.",
        "category": "marketplace-photo",
        "authorityTier": 2,
        "coverage": "individual cards whose text and markings were read from a retained seller photograph on a non-Cardmarket marketplace",
        "supportsAbsence": False,
        "usedFor": ["language", "identity", "finish", "edition"],
        "attribution": "Seller listing photograph from the marketplace named by the retained listing URL.",
        "notes": "Generic tier-2 provider for retained eBay, Shopee, Enjoei and similar marketplace photographs. The exact marketplace remains explicit in each listing URL and specimen record. Cardmarket photographs retain their dedicated provider. Positive evidence only: a listing proves only the visible specimen and never absence or catalogue completeness.",
    },
]

PROVIDER_BY_ID = {provider["providerId"]: provider for provider in PROVIDERS}
HOST_TO_PROVIDER = {
    host: provider["providerId"] for provider in PROVIDERS for host in provider["hosts"]
}

# Fallback matching for non-URL evidence, keyed on the wording the stores already use.
SOURCE_TYPE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Ahead of both `photograph` and `cardmarket`: a seller's listing photograph is evidence and
    # the catalogue it sits on is not, so the two must never collapse onto one provider. The
    # tie-break is earliest mention, and "Cardmarket seller ..." starts at the same offset as the
    # bare catalogue pattern, so list order decides it here.
    (re.compile(r"cardmarket seller", re.I), "cardmarket-listing-photo"),
    (re.compile(r"seller listing photograph|listing photograph", re.I),
     "seller-listing-photo"),
    (re.compile(r"third-party scan archive|pok[eé]cardex", re.I), "pokecardex"),
    (re.compile(r"pkparaiso", re.I), "pkparaiso"),
    (re.compile(r"wikidex", re.I), "wikidex"),
    (re.compile(r"photograph", re.I), "inspected-specimen"),
    (re.compile(r"owner attestation", re.I), "owner-attestation"),
    (re.compile(r"bulbapedia", re.I), "bulbapedia"),
    (re.compile(r"52poke|51poke|s1\\.52poke\\.com|s2\\.52poke\\.com", re.I), "52poke"),
    (re.compile(r"tcgdex", re.I), "tcgdex"),
    (re.compile(r"pokemon-card\.com|official pokemon japan", re.I), "pokemon-card-jp"),
    (re.compile(r"asia\.pokemon-card|official pokemon asia", re.I), "pokemon-card-asia"),
    (re.compile(r"pokemoncard\.co\.kr|pokemonkorea\.co\.kr|official pokemon korea", re.I),
     "pokemon-card-korea"),
    (re.compile(r"elite ?fourum", re.I), "elitefourum"),
    (re.compile(r"pok[eé]cottage", re.I), "pokecottage"),
    (re.compile(r"pokumon", re.I), "pokumon"),
    (re.compile(r"ligapokemon", re.I), "ligapokemon"),
    (re.compile(r"tcgcsv|tcgplayer", re.I), "tcgcsv"),
    (re.compile(r"psa", re.I), "psa"),
    (re.compile(r"cardmarket", re.I), "cardmarket"),
    (re.compile(r"marketplace listing", re.I), "ligapokemon"),
    (re.compile(r"retail listing|specialist card listing", re.I), "retailer-listing"),
    (re.compile(r"play! ?pokemon|prize pack gallery", re.I), "play-pokemon"),
    (re.compile(r"scan review|downloaded scan", re.I), "owner-attestation"),
    (re.compile(r"stock image", re.I), "cardmarket"),
    (re.compile(r"pokemontcg\.io", re.I), "pokemontcgio"),
    (re.compile(r"limitless", re.I), "limitlesstcg"),
    (re.compile(r"same card as|shared card identity|sibling|reprint of", re.I), "internal-derivation"),
]


def read_json(path: Path) -> Any:
    # Tolerate historical PowerShell 5.1 BOM output; all active writers now emit UTF-8 no-BOM.
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def canonical_url(url: str) -> str:
    """Normalize path encoding, fragments and slashes so a source is counted once.

    Query strings are preserved: several providers put the language or the card id in the query,
    so dropping it would merge genuinely different endpoints.
    """
    parts = urlsplit(url.strip())
    # Evidence stores historically mixed Unicode/raw ampersands with percent-encoded paths.
    # Keep ordinary path punctuation readable, but encode ampersands and non-ASCII characters.
    path = quote(unquote(parts.path), safe="/:@!$'()*+,;=-._~").rstrip("/") or "/"
    fragment = parts.fragment if (
        parts.netloc.casefold() in {"github.com", "www.github.com"}
        and re.fullmatch(r"/[^/]+/[^/]+/issues/\d+", path)
        and re.fullmatch(r"attachment-[1-9]\d*", parts.fragment)
    ) else ""
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, fragment))


def resolve_provider(url: str | None, source_type: str | None) -> str | None:
    """Infer the provider for a record that does not carry one.

    A `sourceType` often names more than one source — "Elite Fourum collector-group confirmation
    corroborated by archived official Copag announcements and owner attestation" names two. This
    used to return whichever pattern sat earliest in `SOURCE_TYPE_PATTERNS`, so position in a
    hand-ordered list decided which source got the credit: three contradictions were attributed to
    the collection owner rather than to Elite Fourum, because "owner attestation" is listed five
    places above "elite ?fourum" (#73).

    The tie-break is now where each source is *named in the text*, earliest first, which matches how
    these strings are written — the source carrying the claim leads, and what corroborates it
    follows. Across all 719 units that agrees with the stored `providerId` every time; the previous
    rule disagreed three times. Check `S15` holds it there.
    """
    # A photograph is the evidence object even when its CDN hostname belongs to the
    # marketplace catalogue.  Keep that narrower provider ahead of host inference.
    if source_type and re.search(r"cardmarket.*(?:seller|listing).*photograph", source_type, re.I):
        return "cardmarket-listing-photo"
    if url:
        host = urlsplit(url).netloc.lower()
        # Cardmarket's image CDN is not the catalogue itself.  A specimen URL on this
        # host is a seller listing photograph, even when the surrounding source type only
        # says "Inspected physical specimen photograph".
        if host == "marketplace-article-scans.s3.cardmarket.com":
            return "cardmarket-listing-photo"
        if host in HOST_TO_PROVIDER:
            return HOST_TO_PROVIDER[host]
        for known_host, provider_id in HOST_TO_PROVIDER.items():
            if host.endswith("." + known_host) or host == known_host:
                return provider_id
    if not source_type:
        return None
    named: list[tuple[int, int, str]] = []
    for order, (pattern, provider_id) in enumerate(SOURCE_TYPE_PATTERNS):
        found = pattern.search(source_type)
        if found:
            # List order stays the tie-break for two sources named at the same offset, so the
            # result is deterministic rather than dependent on dict or set iteration.
            named.append((found.start(), order, provider_id))
    return min(named)[2] if named else None


SPECIMEN_SOURCE_TYPES = {
    "collection owner": "Owner-supplied physical card photograph",
    "third-party seller": "Seller listing photograph",
    "third-party scan archive": "Third-party scan archive",
}


def record_corroborating_specimens(
    specimens: list[dict[str, Any]], units: list[dict[str, Any]],
    record: Callable[..., None],
) -> None:
    """Project every specimen supporting a corroborated unit as identity evidence."""
    corroborated = {unit["unitId"] for unit in units if unit.get("corroborated") is True}
    for specimen in specimens:
        unit_ids = [ref for ref in specimen.get("citedBy") or [] if ref in corroborated]
        if not unit_ids:
            continue
        source_type = SPECIMEN_SOURCE_TYPES.get(
            str(specimen.get("heldBy", "")).casefold(),
            str(specimen.get("inspectedFrom") or "Inspected physical specimen photograph"),
        )
        record(
            specimen.get("photographSource"), source_type,
            "identity", specimen["specimenId"], specimen.get("recordedAt"),
        )
        for unit_id in unit_ids:
            record(
                specimen.get("photographSource"), source_type,
                "identity", unit_id, specimen.get("recordedAt"),
            )


def main() -> int:
    units = read_json(ROOT / "verification" / "units.json")
    finish_units = read_json(ROOT / "verification" / "finish_units.json")["units"]
    specimens = read_json(ROOT / "verification" / "specimens.json")["specimens"]
    overrides = read_json(ROOT / "verification" / "finish_overrides.json")
    cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    artists = read_json(ROOT / "artists_pokemontcgio.json")
    source_first = read_json(ROOT / "verification" / "source_first_prints.json")
    bulbapedia_dates = read_json(
        ROOT / "verification" / "bulbapedia_release_dates.json"
    )

    evidence: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []

    def record(url: str | None, source_type: str | None, dimension: str, stable_id: str,
               retrieved: str | None = None, provider_id: str | None = None) -> None:
        # A language unit already names its provider; inferring one from prose that the unit could
        # simply be asked is how the registry came to disagree with the store (#73). Inference is
        # for the records that carry no provider — finish sources, artist credits, release dates.
        provider_id = provider_id or resolve_provider(url, source_type)
        if provider_id is None:
            unresolved.append(f"{dimension}:{stable_id} url={url!r} sourceType={source_type!r}")
            return
        if url and url.startswith("http"):
            key = canonical_url(url)
            entry = evidence.setdefault(
                key,
                {"canonicalUrl": key, "nonUrlEvidenceId": None, "providerId": provider_id,
                 "sourceTypes": set(), "dimensions": set(), "stableIds": set(),
                 "retrievedAt": None, "usageCount": 0},
            )
        else:
            # Non-URL evidence collapses to one named class per provider, never a fake link.
            key = f"evidence:{provider_id}"
            entry = evidence.setdefault(
                key,
                {"canonicalUrl": None, "nonUrlEvidenceId": key, "providerId": provider_id,
                 "sourceTypes": set(), "dimensions": set(), "stableIds": set(),
                 "retrievedAt": None, "usageCount": 0},
            )
        if source_type:
            entry["sourceTypes"].add(source_type)
        entry["dimensions"].add(dimension)
        entry["stableIds"].add(stable_id)
        entry["usageCount"] += 1
        if retrieved and (entry["retrievedAt"] is None or retrieved > entry["retrievedAt"]):
            entry["retrievedAt"] = retrieved

    for unit in units:
        if unit.get("status") in {"confirmed", "contradicted"}:
            record(unit.get("sourceUrl"), unit.get("sourceType"), "language",
                   unit["unitId"], (unit.get("checkedAt") or "")[:10] or None,
                   provider_id=unit.get("providerId"))

    # Every specimen used to mark a unit corroborated must reach the source graph as identity
    # evidence. Finish/edition observations remain separate and no absence capability is inferred.
    record_corroborating_specimens(specimens, units, record)

    for entry in source_first["prints"]:
        if entry.get("providerId") not in {"pokemon-official", "pokemon-card-korea"}:
            continue
        for url in {
            entry.get("sourceUrl"), entry.get("cardImageUrl"),
            entry.get("comparisonAssetUrl"),
        } - {None}:
            record(
                url, "Positive source-first card record", "card-release",
                entry["printId"], provider_id=entry["providerId"],
            )

    for unit in finish_units:
        for printing in unit["printings"]:
            for source in printing.get("sources") or []:
                dimensions = source.get("claimFields") or ["finish"]
                if (
                    not isinstance(dimensions, list)
                    or not dimensions
                    or any(field not in {"identity", "finish", "edition"} for field in dimensions)
                ):
                    unresolved.append(
                        f"claimFields:{printing['printingId']} value={dimensions!r}"
                    )
                    continue
                for dimension in dimensions:
                    record(source.get("url"), source.get("sourceType"), dimension,
                           printing["printingId"], source.get("retrievedAt"))

    for name, source in (overrides.get("sources") or {}).items():
        record(source.get("url"), source.get("sourceType"), "finish-override", f"override:{name}")

    for card in cards:
        stable = f"{card['setCode']} {card.get('number') or ''} {card.get('variantToken') or 'base'}".strip()
        if card.get("productUrl"):
            record(card["productUrl"], "Cardmarket product page", "product", stable)
        if card.get("imageUrl"):
            record(card["imageUrl"], "Cardmarket product image", "image", stable)
        if card.get("artistSource"):
            record(None, card["artistSource"], "artist", stable)
        editions = card.get("editions") or {}
        if editions.get("source"):
            record(None, "Bulbapedia + Elite Fourum 1st Edition timeline", "edition", stable)

    for entry in artists:
        if entry.get("releaseDate"):
            record("https://api.pokemontcg.io/v2/cards", "pokemontcg.io v2 API", "date",
                   f"{entry.get('setName')} {entry.get('number')}".strip())

    for entry in bulbapedia_dates["records"]:
        page = entry["page"].replace(" ", "_")
        record(f"https://bulbapedia.bulbagarden.net/wiki/{page}",
               "Bulbapedia expansion/product release field", "date",
               entry["setCode"], bulbapedia_dates["generated"])

    rows = []
    for entry in sorted(evidence.values(), key=lambda e: (e["providerId"], e["canonicalUrl"] or "")):
        row = {
            "canonicalUrl": entry["canonicalUrl"],
            "nonUrlEvidenceId": entry["nonUrlEvidenceId"],
            "providerId": entry["providerId"],
            "sourceTypes": sorted(entry["sourceTypes"]),
            "dimensions": sorted(entry["dimensions"]),
            "stableIdCount": len(entry["stableIds"]),
            "stableIds": sorted(entry["stableIds"])[:50],
            "retrievedAt": entry["retrievedAt"],
            "usageCount": entry["usageCount"],
        }
        if entry["canonicalUrl"] and entry["canonicalUrl"] in {
            canonical_url(scope)
            for scope in PROVIDER_BY_ID[entry["providerId"]].get("absenceScopes", [])
        }:
            row["supportsAbsence"] = True
        rows.append(row)

    evidence_urls = {row["canonicalUrl"] for row in rows if row["canonicalUrl"]}
    missing_scopes = {
        provider["providerId"]: sorted(
            canonical_url(scope)
            for scope in provider.get("absenceScopes", [])
            if canonical_url(scope) not in evidence_urls
        )
        for provider in PROVIDERS
        if provider.get("supportsAbsence") and provider.get("absenceScopes")
    }
    missing_scopes = {provider: scopes for provider, scopes in missing_scopes.items() if scopes}
    if missing_scopes:
        print(f"ERROR: absence scopes are not present in the evidence index: {missing_scopes}", file=sys.stderr)
        return 1
    unscopeable = [
        provider["providerId"] for provider in PROVIDERS
        if provider.get("supportsAbsence") and not provider.get("absenceScopes")
    ]
    if unscopeable:
        print(
            "ERROR: absence-capable providers must declare absenceScopes: "
            + ", ".join(unscopeable),
            file=sys.stderr,
        )
        return 1

    usage_by_provider = Counter(row["providerId"] for row in rows)
    urls_by_provider: dict[str, int] = defaultdict(int)
    claims_by_provider: Counter[str] = Counter()
    for row in rows:
        if row["canonicalUrl"]:
            urls_by_provider[row["providerId"]] += 1
        claims_by_provider[row["providerId"]] += row["usageCount"]

    providers_out = []
    for provider in PROVIDERS:
        pid = provider["providerId"]
        providers_out.append({
            **{k: v for k, v in provider.items() if k != "hosts"},
            "hosts": provider["hosts"],
            "uniqueSources": urls_by_provider.get(pid, 0) or usage_by_provider.get(pid, 0),
            "claimsSupported": claims_by_provider.get(pid, 0),
        })

    document = {
        "meta": {
            "description": "Canonical provider registry and evidence index for every sourced claim.",
            "generated": datetime.now(timezone.utc).date().isoformat(),
            "policy": [
                "Every sourced claim maps to exactly one provider. An unmatched source fails generation.",
                "supportsAbsence identifies providers with complete scopes; only evidence URLs marked supportsAbsence=true are absence-capable. Provider authority alone never establishes absence.",
                "Non-URL evidence is a named evidence class, never a fabricated hyperlink.",
                "Duplicate URLs are canonicalized on scheme, host and path; query strings are preserved because several providers encode the language or card id there.",
            ],
            "counts": {
                "providers": len(providers_out),
                "evidenceRecords": len(rows),
                "uniqueUrls": sum(1 for row in rows if row["canonicalUrl"]),
                "nonUrlEvidenceClasses": sum(1 for row in rows if row["nonUrlEvidenceId"]),
                "claimsAttributed": sum(row["usageCount"] for row in rows),
            },
        },
        "providers": providers_out,
        "evidence": rows,
    }

    if unresolved:
        print(f"ERROR: {len(unresolved)} sources match no provider:", file=sys.stderr)
        for item in unresolved[:20]:
            print(f"  {item}", file=sys.stderr)
        return 1

    markdown = render_markdown(document)

    if "--check" in sys.argv:
        stale = []
        current_registry = (
            json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            if REGISTRY_PATH.exists() else {}
        )
        if (current_registry.get("evidence") != rows
                or current_registry.get("providers") != providers_out):
            stale.append(str(REGISTRY_PATH.relative_to(ROOT)))
        if not MARKDOWN_PATH.exists() or MARKDOWN_PATH.read_text(encoding="utf-8") != markdown:
            stale.append(str(MARKDOWN_PATH.relative_to(ROOT)))
        if stale:
            print(f"stale: {', '.join(stale)}; run python scripts/source_registry.py")
            return 1
        print("source registry is current")
        return 0

    with REGISTRY_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    with MARKDOWN_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown)

    counts = document["meta"]["counts"]
    print(f"providers: {counts['providers']}  evidence records: {counts['evidenceRecords']} "
          f"({counts['uniqueUrls']} URLs + {counts['nonUrlEvidenceClasses']} non-URL classes)")
    print(f"claims attributed: {counts['claimsAttributed']}")
    return 0


def render_markdown(document: dict[str, Any]) -> str:
    lines = [
        "<!-- doc: role=source and attribution register; stage=generated -->",
        "# Sources and attribution",
        "",
        "Generated by `python scripts/source_registry.py` — do not hand-edit.",
        "",
        f"Every sourced claim in this project maps to exactly one provider below. "
        f"{document['meta']['counts']['claimsAttributed']} claims are attributed across "
        f"{document['meta']['counts']['evidenceRecords']} distinct sources "
        f"({document['meta']['counts']['uniqueUrls']} unique URLs and "
        f"{document['meta']['counts']['nonUrlEvidenceClasses']} non-URL evidence classes).",
        "",
        "**`supportsAbsence` describes source capability, not a final application decision.** A",
        "complete official manifest may establish that a printing does *not* exist within its",
        "stated scope. The collection owner's cross-source decisions are stored separately in",
        "`verification/owner_adjudications.json`; an evidence row is absence-capable only when its",
        "own `supportsAbsence` flag is true. For every other source a missing row is a coverage",
        "gap, never a finding.",
        "",
        "| Provider | Category | Tier | Absence? | Sources | Claims | Used for |",
        "|---|---|---:|:---:|---:|---:|---|",
    ]
    for provider in sorted(document["providers"], key=lambda p: (p["authorityTier"], p["displayName"])):
        lines.append(
            f"| **{provider['displayName']}** | {provider['category']} | {provider['authorityTier']} | "
            f"{'yes' if provider['supportsAbsence'] else 'no'} | {provider['uniqueSources']} | "
            f"{provider['claimsSupported']} | {', '.join(provider['usedFor'])} |"
        )
    lines += ["", "## Provider detail", ""]
    for provider in sorted(document["providers"], key=lambda p: (p["authorityTier"], p["displayName"])):
        home = f" — <{provider['homepage']}>" if provider["homepage"] else ""
        lines += [
            f"### {provider['displayName']}{home}",
            "",
            f"- **Organization:** {provider['organization'] or 'not applicable (evidence class)'}",
            f"- **Terms:** {provider['licenseOrTerms']}",
            f"- **Coverage:** {provider['coverage']}",
            f"- **Can establish absence:** {'yes, within its stated scope' if provider['supportsAbsence'] else 'no — positive evidence only'}",
            *(["- **Absence-capable source scopes:** " + ", ".join(
                f"<{scope}>" for scope in provider.get("absenceScopes", [])
            )] if provider.get("absenceScopes") else []),
            f"- **Attribution:** {provider['attribution']}",
            f"- **Notes:** {provider['notes']}",
            "",
        ]
    lines += [
        "## Exhaustive source list",
        "",
        "The complete per-URL index lives in `verification/source_registry.json` "
        "(`evidence[]`), with the provider, dimensions, retrieval date, and the stable IDs each "
        "source supports. It is generated rather than hand-listed so it cannot drift from the "
        "evidence stores.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
