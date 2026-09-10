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
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote, unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "verification" / "source_registry.json"
MARKDOWN_PATH = ROOT / "verification" / "SOURCES.md"


PROVIDERS: list[dict[str, Any]] = [
    {
        "providerId": "pokemon-official",
        "displayName": "The Pokémon Company official cards and checklists",
        "organization": "The Pokémon Company International",
        "homepage": "https://www.pokemon.com",
        "hosts": ["assets.pokemon.com", "d1wx537rtdixyy.cloudfront.net", "www.pokemon.com",
                  "tcg.pokemon.com", "dz3we2x72f7ol.cloudfront.net"],
        "licenseOrTerms": "Publisher's own terms; used for identification and verification only.",
        "category": "official-publisher",
        "authorityTier": 1,
        "coverage": "positive localized card pages and listed checklist entries",
        "supportsAbsence": False,
        "usedFor": ["language", "finish", "product"],
        "attribution": "Official card pages and product checklists © The Pokémon Company International.",
        "notes": ("Localized pages and checklists confirm only the cards, languages, regions, "
                  "and finishes they explicitly list. Missing entries remain unknown."),
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
        "hosts": ["www.pokemon-card.com", "pokemon-card.com", "www.30th.pokemon-card.com", "30th.pokemon-card.com"],
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
        "providerId": "collectory",
        "displayName": "Collectory",
        "organization": "Collectory",
        "homepage": "https://collectory.cc",
        "hosts": ["collectory.cc", "www.collectory.cc", "cdn.collectory.cc"],
        "licenseOrTerms": "Site terms; hosted card renders are used for identification and verification only.",
        "category": "collector-database",
        "authorityTier": 3,
        "coverage": "positive localized card identity and printed rarity shown by retained database renders",
        "supportsAbsence": False,
        "usedFor": ["identity", "rarity"],
        "attribution": "Card renders from Collectory.",
        "notes": "A retained database render establishes only the visible card identity and printed "
                 "rarity. It is not physical-finish evidence. Missing cards, variants, or languages "
                 "never establish absence or completeness.",
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
        "usedFor": ["identity", "language"],
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
        "hosts": ["wiki.52poke.com", "s1.52poke.com", "s2.52poke.com", "media.52poke.com"],
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
        "coverage": "positive promo language tables and the 1st-edition timeline",
        "supportsAbsence": False,
        "usedFor": ["language", "edition"],
        "attribution": "Collector-community reference tables from Elite Fourum.",
        "notes": "High-authority community reference. Listed language and edition facts are positive evidence. Missing flags or rows remain unknown.",
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
        "licenseOrTerms": "Site terms.",
        "category": "marketplace-catalogue",
        "authorityTier": 5,
        "coverage": "product/filter metadata and unreviewed catalogue images",
        "supportsAbsence": False,
        "usedFor": ["product", "image", "finish"],
        "attribution": "Product catalogue via Cardmarket.",
        "notes": (
            "Product/language filter combinations and catalogue language metadata do not "
            "establish a localized release or collector number; in particular, a Traditional "
            "Chinese filter is not evidence that the card was released under that product "
            "number. Missing products, images, filters, or listings never establish absence."
        ),
    },
    {
        "providerId": "cardmarket-product-image",
        "displayName": "Cardmarket exact product image",
        "organization": "Cardmarket (Sammelkartenmarkt GmbH & Co. KG)",
        "homepage": "https://www.cardmarket.com",
        "hosts": [],
        "licenseOrTerms": "Site terms. Product images remain Cardmarket's; artwork remains the rights holders'.",
        "category": "marketplace-photo",
        "authorityTier": 2,
        "coverage": "individual cards whose printed text, identity or finish is visible in an exact retained product image",
        "supportsAbsence": False,
        "usedFor": ["language", "identity", "finish", "edition", "image"],
        "attribution": "Exact retained product image via Cardmarket.",
        "notes": (
            "The image is positive evidence only for properties visible on the pictured card. "
            "The surrounding product page, selected language filter, offers and counts remain "
            "tier-5 catalogue metadata and never establish another localized release or absence. "
            "Retain accepted images as SPEC-nnnn records so the observation is reviewable."
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
        "coverage": "positive Prize Pack cards and finishes shown in the gallery",
        "supportsAbsence": False,
        "usedFor": ["finish", "product"],
        "attribution": "Prize Pack contents © The Pokémon Company International.",
        "notes": "The gallery confirms displayed Prize Pack cards and finishes. Omitted alternatives remain unknown.",
    },
    {
        "providerId": "retailer-listing",
        "displayName": "Retailer and specialist card listings",
        "organization": "Various independent retailers",
        "homepage": None,
        "hosts": [
            "www.target.com", "exorgames.com", "shopping.fullcomp.jp", "www.pokeca.net",
            "www.ebay.de", "pokipair.com", "www.pokipair.com", "media.pokipair.com",
            "coleka.com", "www.coleka.com",
            "beehivetcg.com", "rocketcoll.com",
        ],
        "licenseOrTerms": "Individual retailer site terms; used for identification only.",
        "category": "retail-listing",
        "authorityTier": 3,
        "coverage": "individual listings or retained set-list images that identify an exact physical printing",
        "supportsAbsence": False,
        "usedFor": ["finish", "product", "language"],
        "attribution": "Retail listings from independent sellers.",
        "notes": (
            "Grouped deliberately: these are one-off listings or retained retailer set-list images, "
            "not authoritative catalogues, so per-host provider entries would imply a coverage "
            "guarantee none of them offers. An image counts only when it identifies the printing."
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
        "notes": "Stable specimen records retain the observation and available photograph provenance. Each claim must cite the exact specimen it uses.",
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
SOURCE_TYPE_PATTERNS: list[tuple[re.Pattern[str], str | None]] = [
    # Ahead of both `photograph` and `cardmarket`: a seller's listing photograph is evidence and
    # the catalogue it sits on is not, so the two must never collapse onto one provider. The
    # tie-break is earliest mention, and "Cardmarket seller ..." starts at the same offset as the
    # bare catalogue pattern, so list order decides it here.
    (re.compile(r"cardmarket seller", re.I), "cardmarket-listing-photo"),
    (re.compile(r"seller listing photograph|listing photograph", re.I),
     "seller-listing-photo"),
    (re.compile(r"pok[eé]cardex", re.I), "pokecardex"),
    # A generic archive is not a provider.  Keep it in the earliest-source tie-break as an
    # unresolved sentinel so later corroborators cannot inherit an unknown archive URL.
    (re.compile(r"third-party scan archive", re.I), None),
    (re.compile(r"pkparaiso", re.I), "pkparaiso"),
    (re.compile(r"collectory", re.I), "collectory"),
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
SCAN_ARCHIVE_PROVIDER_IDS = {"pokecardex", "pkparaiso", "collectory", "wikidex"}


def read_json(path: Path) -> Any:
    # Tolerate historical PowerShell 5.1 BOM output; all active writers now emit UTF-8 no-BOM.
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def latest_input_date(*documents: Any) -> str:
    keys = {"checkedAt", "decidedAt", "generated", "lastUpdated", "recordedAt", "retrievedAt"}
    dates: list[str] = []
    stack = list(documents)
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            for key, item in value.items():
                if key in keys and isinstance(item, str) and re.match(r"^\d{4}-\d{2}-\d{2}", item):
                    dates.append(item[:10])
                elif isinstance(item, (dict, list)):
                    stack.append(item)
        elif isinstance(value, list):
            stack.extend(value)
    if not dates:
        raise ValueError("source inputs contain no dated evidence")
    return max(dates)


def provenance_url(value: Any) -> str | None:
    """Return a public HTTP(S) link, separating a trailing prose annotation."""
    if not isinstance(value, str):
        return None
    value = re.sub(r" \([^()\r\n]*\)$", "", value.strip())
    if re.search(r'[\s<>"\\\x00-\x1f\x7f]', value):
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() in {"http", "https"} and parts.hostname and parts.port != 0:
            return value
    except ValueError:
        pass
    return None


def specimen_markings(observation: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize an observed specimen marking into a typed markup kind.

    Shared by the finish and authoritative-graph projectors so a marking
    classification cannot drift between the two generators. The original text
    and the recorded ``markingRole`` are preserved; only the ``kind`` is typed.
    """
    text = observation.get("markings")
    if not text:
        return []
    normalized = str(text).strip()
    if normalized.casefold() in {"editie 1", "edizione 1", "edición 1"}:
        kind = "edition-stamp"
    elif normalized.casefold() == "staff":
        kind, normalized = "staff", "Staff"
    elif normalized.casefold().endswith(" deck silhouette"):
        kind, normalized = "deck-logo", normalized[:-16].strip()
    elif normalized.casefold().endswith(" replica signature"):
        kind, normalized = "championship-signature", normalized[:-18].strip()
    else:
        kind = "observed-marking"
    return [{"kind": kind, "role": observation.get("markingRole"), "text": normalized}]


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


def is_cardmarket_product_image(url: str | None) -> bool:
    return bool(
        url
        and urlsplit(url).netloc.lower() == "product-images.s3.cardmarket.com"
    )


def retained_cardmarket_product_image_urls(
    specimens: list[dict[str, Any]],
) -> set[str]:
    return {
        canonical_url(specimen["photographSource"])
        for specimen in specimens
        if is_cardmarket_product_image(specimen.get("photographSource"))
    }


def prefer_explicit_archive_provider(
    source_type: str,
    named: list[tuple[int, int, str | None]],
) -> list[tuple[int, int, str | None]]:
    archive = re.search(r"third-party scan archive", source_type, re.I)
    if not archive:
        return named
    names_archive_provider = any(
        provider_id in SCAN_ARCHIVE_PROVIDER_IDS
        and start >= archive.end()
        and re.fullmatch(r"\s+from\s+", source_type[archive.end():start], re.I)
        for start, _order, provider_id in named
    )
    if not names_archive_provider:
        return named
    return [
        candidate
        for candidate in named
        if candidate[2] is not None or candidate[0] != archive.start()
    ]


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
    named: list[tuple[int, int, str | None]] = []
    for order, (pattern, provider_id) in enumerate(SOURCE_TYPE_PATTERNS):
        found = pattern.search(source_type)
        if found:
            # List order stays the tie-break for two sources named at the same offset, so the
            # result is deterministic rather than dependent on dict or set iteration.
            named.append((found.start(), order, provider_id))
    named = prefer_explicit_archive_provider(source_type, named)
    return min(named)[2] if named else None


def resolve_evidence_provider(
    url: str | None,
    source_type: str | None,
    provider_id: str | None,
    retained_cardmarket_images: set[str],
) -> str | None:
    if provider_id is not None:
        return provider_id
    if is_cardmarket_product_image(url):
        return (
            "cardmarket-product-image"
            if canonical_url(url) in retained_cardmarket_images
            else "cardmarket"
        )
    return resolve_provider(url, source_type)


SPECIMEN_SOURCE_TYPES = {
    "collection owner": "Owner-supplied physical card photograph",
    "collection-owner supplied source image": "Owner-supplied physical card photograph",
    "third-party retailer": "Retail listing",
    "third-party seller": "Seller listing photograph",
    "third-party scan archive": "Third-party scan archive",
    "third-party collector": "Third-party collector photograph",
    "publisher or database": "Inspected reference photograph; original provider unspecified",
    "not established; retailer reference image": "Retail listing",
    "not established; owner supplied seller image url": "Seller listing photograph",
    "not established; image supplied by collection owner": "Inspected card photograph; external origin unknown",
}


def reviewed_candidate_claims(graph):
    return [row for row in (graph or {}).get("entities", [])
            if row["entityType"] == "candidate-claim" and row["origin"] != "physical-evidence-projection"]


def registry_claim_ids(units: list[dict], source_first: list[dict], finish_units: list[dict],
                       reviewed_graph: dict | None = None) -> set[str]:
    """Resolve citation targets from upstream canonical stores, without grading their evidence."""
    # The retained graph base owns reviewed claims. Its generated physical slice is downstream
    # of this registry and must not feed back into reference resolution.
    reviewed_ids = {row["entityId"] for row in reviewed_candidate_claims(reviewed_graph)}
    return ({unit["unitId"] for unit in units}
            | {row["printId"] for row in source_first}
            | {printing["printingId"] for unit in finish_units for printing in unit["printings"]}
            | reviewed_ids)


def record_product_render_context(specimen: dict, references: list[str], units: dict,
                                  record: Callable) -> bool:
    """Attach an unlocated historical render to its existing claim, never invent image authority."""
    if specimen.get("inspectedFrom") != "product image" or any(
        provenance_url(specimen.get(key)) for key in ("listingUrl", "photographSource")
    ):
        return False
    if not all(ref in units for ref in references):
        return False
    for ref in references:
        unit = units[ref]
        for stable_id in (ref, specimen["specimenId"]):
            record(unit.get("sourceUrl"), "Referenced product render (context only); " + str(unit.get("sourceType")),
                   "language", stable_id, (unit.get("checkedAt") or "")[:10] or None,
                   provider_id=unit.get("providerId"))
    return bool(references)


def specimen_claim_ids(specimen, accepted, direct) -> list[str]:
    return sorted((set(specimen.get("citedBy") or []) & accepted)
                  | direct.get(specimen["specimenId"], set()))


def direct_specimen_claims(units, source_first, reviewed_graph) -> dict[str, set[str]]:
    direct = defaultdict(set)
    for unit in units:
        source_ref = unit.get("sourceRef") or ""
        if source_ref.startswith("specimen:"):
            direct[source_ref.removeprefix("specimen:")].add(unit["unitId"])
    for row in source_first:
        ids = set(row.get("corroboratingSpecimenIds") or []) | {row.get("specimenId")}
        for specimen_id in ids - {None}:
            direct[specimen_id].add(row["printId"])
    for row in reviewed_candidate_claims(reviewed_graph):
        for specimen_id in row.get("payload", {}).get("specimenIds") or []:
            direct[specimen_id].add(row["entityId"])
    return direct


def record_linked_specimens(
    specimens: list[dict[str, Any]], units: list[dict[str, Any]],
    record: Callable[..., None], source_first: list[dict[str, Any]] = (),
    finish_units: list[dict[str, Any]] = (),
    reviewed_graph: dict | None = None,
) -> None:
    """Project linked identity and physical evidence without inferring corroboration."""
    accepted = registry_claim_ids(units, source_first, finish_units, reviewed_graph)
    units_by_id = {unit["unitId"]: unit for unit in units}
    direct = direct_specimen_claims(units, source_first, reviewed_graph)
    surfaces = specimen_surfaces()
    for specimen in specimens:
        unit_ids = specimen_claim_ids(specimen, accepted, direct)
        physical = specimen.get("physicalObservation") or {}
        if not unit_ids and not physical:
            continue
        if record_product_render_context(specimen, unit_ids, units_by_id, record):
            continue
        source_type = SPECIMEN_SOURCE_TYPES.get(
            str(specimen.get("heldBy", "")).casefold(),
            str(specimen.get("inspectedFrom") or "Inspected physical specimen photograph"),
        )
        record_specimen_sources(specimen, unit_ids, source_type, physical, record, surfaces)


def record_specimen_sources(specimen: dict, unit_ids: list[str], source_type: str,
                           physical: dict, record: Callable[..., None], surfaces: dict) -> None:
    photo_url = provenance_url(specimen.get("photographSource"))
    listing_url = provenance_url(specimen.get("listingUrl"))
    urls = {photo_url, listing_url} - {None}
    observed_url = photo_url or listing_url
    retained_product_images = retained_cardmarket_product_image_urls([specimen])
    for url in sorted(urls) or [None]:
        provider = specimen_provider(url, source_type)
        if provider == "cardmarket" and url and canonical_url(url) in retained_product_images:
            provider = "cardmarket-product-image"
        dimension = card_evidence_dimension(url, provider, surfaces, "identity")
        for stable_id in [specimen["specimenId"], *unit_ids]:
            record_specimen_claim(url, source_type, provider, dimension, stable_id,
                                  specimen.get("recordedAt"), physical if url == observed_url else {},
                                  record, surfaces)


def specimen_surfaces() -> dict:
    surfaces: dict[str, list] = defaultdict(list)
    for surface in read_json(ROOT / "verification/source_capabilities.json")["surfaces"]:
        surfaces[surface["providerId"]].append(surface)
    return surfaces


def card_evidence_dimension(url: str | None, provider: str | None, surfaces: dict,
                            preferred: str) -> str:
    from source_capabilities import route_evidence
    if provider is None:
        return "identity"  # The registry records an unresolved provider, never invents one.
    surface = route_evidence({"canonicalUrl": url, "providerId": provider}, surfaces)
    capabilities = {value for edge in surface["coverageEdges"] for value in edge["positiveEvidenceCapabilities"]}
    # Use the surface's existing positive card contract; never broaden it.
    for dimension in (preferred, "identity", "card-release", "card-existence", "language"):
        if dimension in capabilities:
            return dimension
    return "identity"  # Unsupported evidence must still fail capability validation.


def surface_supports_observed_finish(url, provider, surfaces) -> bool:
    from source_capabilities import route_evidence
    if provider is None:
        return False
    surface = route_evidence({"canonicalUrl": url, "providerId": provider}, surfaces)
    return surface["finishCapability"]["mode"] == "specimen-observation" and any(
        "finish" in edge["positiveEvidenceCapabilities"] for edge in surface["coverageEdges"]
    )


def record_specimen_claim(url, source_type, provider, dimension, stable_id, retrieved, physical, record,
                          surfaces):
    if provider == "cardmarket" and not is_cardmarket_product_image(url):
        record(url, source_type, "product", stable_id, retrieved, provider_id=provider)
        record(None, source_type, "identity", stable_id, retrieved, provider_id="inspected-specimen")
    else:
        record(url, source_type, dimension, stable_id, retrieved,
               provider_id=None if provider == "cardmarket" else provider)
    if physical.get("finish"):
        if "finish" in (physical.get("ownerAttestedFields") or []):
            record(None, "Owner attestation", "finish", stable_id, retrieved,
                   provider_id="owner-attestation")
            return
        inspected = surface_supports_observed_finish(url, provider, surfaces)
        record(url if inspected else None, source_type, "finish", stable_id, retrieved,
               provider_id=provider if inspected else "inspected-specimen")


def specimen_provider(url: str | None, source_type: str) -> str | None:
    provider = resolve_provider(url, source_type)
    if source_type == "Seller listing photograph" and provider in {None, "retailer-listing"}:
        return "seller-listing-photo"
    return provider


def source_first_registry_urls(entry: dict[str, Any]) -> set[str]:
    """Keep the declared primary source and only assets owned by that provider.

    Foreign or unknown-host assets use their own specimen provenance; a link from the
    primary source never gives them its authority or claim dimension.
    """
    assets = {entry.get("cardImageUrl"), entry.get("comparisonAssetUrl")} - {None}
    return ({entry.get("sourceUrl")} - {None}) | {
        url for url in assets if resolve_provider(url, None) == entry["providerId"]
    }


def _specimen_indexed_directly(entry: dict, specimens_by_id: dict | None) -> bool:
    """True when the specimen's direct path indexes a URL under inspected-specimen authority.

    The anonymous inspected-specimen record carries the owned photograph's evidence. It
    must stay when not one of the specimen's URLs resolves to inspected-specimen
    provenance, because then the inspected evidence would otherwise be lost (e.g. a
    specimen whose only link is a foreign corroborating page like Pokumon). Suppress it
    only when a validated photo or listing URL actually resolves to inspected-specimen.
    """
    spec = (specimens_by_id or {}).get(str(entry.get("specimenId")))
    if not spec:
        return False
    source_type = SPECIMEN_SOURCE_TYPES.get(
        str(spec.get("heldBy", "")).casefold(),
        str(spec.get("inspectedFrom") or "Inspected physical specimen photograph"),
    )
    candidate_urls = {
        provenance_url(spec.get("photographSource")),
        provenance_url(spec.get("listingUrl")),
    } - {None}
    return any(
        specimen_provider(url, source_type) == "inspected-specimen"
        for url in candidate_urls
    )


def record_source_first_identity(entry: dict, record: Callable, surfaces: dict,
                                 specimens_by_id: dict[str, dict] | None = None) -> None:
    """Index admitted claims under existing provider capabilities, without a provider allowlist."""
    provider = entry["providerId"]
    if provider not in surfaces or provider == "cardmarket-listing-photo":
        # Historical marketplace aliases and listing photographs are indexed through
        # their specimen; a Cardmarket product URL must retain catalogue-only authority.
        if not entry.get("specimenId"):
            raise ValueError(f"Source-first provider {provider} requires a retained specimen")
        return
    # A neighbouring page is not the inspected specimen's authority. When the governed
    # specimen already supplies a validated photo/listing URL, the direct specimen path
    # indexes that unit under the real URL; an anonymous inspected-specimen projection
    # would duplicate the same observation as a second, untraceable evidence record.
    if provider == "inspected-specimen" and _specimen_indexed_directly(entry, specimens_by_id):
        return
    urls = [] if provider == "inspected-specimen" else sorted(source_first_registry_urls(entry))
    for url in urls or [None]:
        dimension = card_evidence_dimension(url, provider, surfaces, "card-release")
        record(url, "Positive source-first card record", dimension,
               entry["printId"], entry.get("retrievedAt"), provider_id=provider)


def main() -> int:
    units = read_json(ROOT / "verification" / "units.json")
    finish_document = read_json(ROOT / "verification" / "finish_units.json")
    finish_units = finish_document["units"]
    specimen_document = read_json(ROOT / "verification" / "specimens.json")
    specimens = specimen_document["specimens"]
    overrides = read_json(ROOT / "verification" / "finish_overrides.json")
    cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    artists = read_json(ROOT / "artists_pokemontcgio.json")
    source_first = read_json(ROOT / "verification" / "source_first_prints.json")
    bulbapedia_dates = read_json(
        ROOT / "verification" / "bulbapedia_release_dates.json"
    )
    generated = latest_input_date(
        units,
        finish_document,
        specimen_document,
        overrides,
        cards,
        artists,
        source_first,
        bulbapedia_dates,
    )
    retained_cardmarket_images = retained_cardmarket_product_image_urls(specimens)

    evidence: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []

    def record(url: str | None, source_type: str | None, dimension: str, stable_id: str,
               retrieved: str | None = None, provider_id: str | None = None) -> None:
        # A language unit already names its provider; inferring one from prose that the unit could
        # simply be asked is how the registry came to disagree with the store (#73). Inference is
        # for the records that carry no provider — finish sources, artist credits, release dates.
        provider_id = resolve_evidence_provider(
            url, source_type, provider_id, retained_cardmarket_images
        )
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

    # Citation resolution is independent of corroboration or the target's verdict.
    # A linked observation neither confirms its target nor becomes independent agreement.
    reviewed_graph = read_json(ROOT / "verification" / "authoritative_graph.json")
    record_linked_specimens(specimens, units, record, source_first["prints"], finish_units,
                           reviewed_graph)

    surfaces = specimen_surfaces()
    specimens_by_id = {str(s.get("specimenId")): s for s in specimens}
    for entry in source_first["prints"]:
        record_source_first_identity(entry, record, surfaces, specimens_by_id)
        if entry.get("raritySourceUrl"):
            record(
                entry["raritySourceUrl"], "Positive source-native rarity record", "rarity",
                entry["printId"], entry.get("rarityRetrievedAt"),
                provider_id=entry.get("rarityProviderId"),
            )
        for url in entry.get("raritySupportingSourceUrls") or []:
            record(
                url, "Positive fixed-product membership record", "set-membership",
                entry["printId"], entry.get("rarityRetrievedAt"),
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
               entry["setCode"], entry.get("retrievedAt") or bulbapedia_dates["generated"])

    rows = []
    for entry in sorted(evidence.values(), key=lambda e: (e["providerId"], e["canonicalUrl"] or "")):
        row = {
            "canonicalUrl": entry["canonicalUrl"],
            "nonUrlEvidenceId": entry["nonUrlEvidenceId"],
            "providerId": entry["providerId"],
            "sourceTypes": sorted(entry["sourceTypes"]),
            "dimensions": sorted(entry["dimensions"]),
            "stableIdCount": len(entry["stableIds"]),
            "stableIds": sorted(entry["stableIds"]),
            "retrievedAt": entry["retrievedAt"],
            "usageCount": entry["usageCount"],
        }
        rows.append(row)

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
            "generated": generated,
            "policy": [
                "Every sourced claim maps to exactly one provider. An unmatched source fails generation.",
                "External providers record positive evidence only. Missing rows, fields, pages, and results remain unknown.",
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
    registry_rendered = json.dumps(document, ensure_ascii=False, indent=1) + "\n"

    if "--check" in sys.argv:
        stale = []
        if not REGISTRY_PATH.exists() or REGISTRY_PATH.read_text(
                encoding="utf-8") != registry_rendered:
            stale.append(str(REGISTRY_PATH.relative_to(ROOT)))
        if not MARKDOWN_PATH.exists() or MARKDOWN_PATH.read_text(encoding="utf-8") != markdown:
            stale.append(str(MARKDOWN_PATH.relative_to(ROOT)))
        if stale:
            print(f"stale: {', '.join(stale)}. Run python scripts/source_registry.py")
            return 1
        print("source registry is current")
        return 0

    with REGISTRY_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(registry_rendered)
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
        "Every external provider is positive-only. An official Pokémon page confirms what it",
        "explicitly lists for the corresponding language or region. A missing card, language,",
        "finish, page, or result remains unknown. Final absence decisions are stored separately",
        "in `verification/owner_adjudications.json`.",
        "",
        "| Provider | Category | Tier | Evidence mode | Sources | Claims | Used for |",
        "|---|---|---:|:---:|---:|---:|---|",
    ]
    for provider in sorted(document["providers"], key=lambda p: (p["authorityTier"], p["displayName"])):
        lines.append(
            f"| **{provider['displayName']}** | {provider['category']} | {provider['authorityTier']} | "
            f"positive only | {provider['uniqueSources']} | "
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
            "- **Evidence mode:** positive only",
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
