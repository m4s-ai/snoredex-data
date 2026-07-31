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
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "verification" / "source_registry.json"
MARKDOWN_PATH = ROOT / "verification" / "SOURCES.md"

# --------------------------------------------------------------------------------------------
# Provider definitions
#
# `authorityTier` ranks how much weight a source carries, and `supportsAbsence` records the one
# thing that actually matters for this project's discipline: whether a missing row in that source
# is evidence of anything. Only a complete official manifest may say "not printed"; everything
# else is positive-only, which is why every other provider is false.
# --------------------------------------------------------------------------------------------

PROVIDERS: list[dict[str, Any]] = [
    {
        "providerId": "pokemon-official",
        "displayName": "The Pokémon Company official checklists",
        "organization": "The Pokémon Company International",
        "homepage": "https://www.pokemon.com",
        "hosts": ["assets.pokemon.com", "d1wx537rtdixyy.cloudfront.net", "www.pokemon.com"],
        "licenseOrTerms": "Publisher's own terms; used for identification and verification only.",
        "category": "official-publisher",
        "authorityTier": 1,
        "coverage": "complete-manifest within the stated set or Prize Pack scope",
        "supportsAbsence": True,
        "usedFor": ["finish", "product"],
        "attribution": "Official product checklists © The Pokémon Company International.",
        "notes": "The only source permitted to establish that a finish is absent, and only inside its stated scope.",
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
        "authorityTier": 3,
        "coverage": "set lists, release fields, per-language articles, promo series",
        "supportsAbsence": False,
        "usedFor": ["language", "edition", "date", "finish"],
        "attribution": "Content from Bulbapedia, licensed CC BY-NC-SA 2.5.",
        "notes": "Preferred for set release dates when the article identifies the matching market field. Korean and Chinese promo articles are {{incomplete}}-tagged; never contradict on their silence.",
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
        "usedFor": ["language"],
        "attribution": "Promo printing data from pokumon.com.",
        "notes": "Indexes English names only. Absence never contradicts a Western language.",
    },
    {
        "providerId": "elitefourum",
        "displayName": "Elite Fourum",
        "organization": "Elite Fourum community",
        "homepage": "https://elitefourum.com",
        "hosts": ["elitefourum.com", "www.elitefourum.com"],
        "licenseOrTerms": "Forum terms; community-contributed content.",
        "category": "collector-community",
        "authorityTier": 4,
        "coverage": "promo language tables and the 1st-edition timeline",
        "supportsAbsence": False,
        "usedFor": ["language", "edition"],
        "attribution": "Collector-community reference tables from Elite Fourum.",
        "notes": "Community-maintained; corroborate where it carries a claim alone.",
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
        "coverage": "product catalogue, images, and marketplace availability",
        "supportsAbsence": False,
        "usedFor": ["product", "image", "finish"],
        "attribution": "Product catalogue and images via Cardmarket.",
        "notes": "The catalogue over-claims languages — this is the finding the project exists to document. Never verification.",
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
        "providerId": "photographed-specimen",
        "displayName": "Photographed physical specimen",
        "organization": None,
        "homepage": None,
        "hosts": [],
        "licenseOrTerms": "Photographs of physical cards; depicted artwork remains the rights holders'.",
        "category": "non-url-evidence",
        "authorityTier": 1,
        "coverage": "individual cards whose text and markings were read from a photograph",
        "supportsAbsence": False,
        "usedFor": ["language", "finish"],
        "attribution": "Physical card, photographed specimen.",
        "notes": "The strongest evidence class here: it defeated three databases at once on XYPR 179.",
    },
]

PROVIDER_BY_ID = {provider["providerId"]: provider for provider in PROVIDERS}
HOST_TO_PROVIDER = {
    host: provider["providerId"] for provider in PROVIDERS for host in provider["hosts"]
}

# Fallback matching for non-URL evidence, keyed on the wording the stores already use.
SOURCE_TYPE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"photograph", re.I), "photographed-specimen"),
    (re.compile(r"owner attestation", re.I), "owner-attestation"),
    (re.compile(r"bulbapedia", re.I), "bulbapedia"),
    (re.compile(r"tcgdex", re.I), "tcgdex"),
    (re.compile(r"pokemon-card\.com|official pokemon japan", re.I), "pokemon-card-jp"),
    (re.compile(r"asia\.pokemon-card|official pokemon asia", re.I), "pokemon-card-asia"),
    (re.compile(r"elite ?fourum", re.I), "elitefourum"),
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
    """Normalize path encoding, fragments and slashes so a page is counted once.

    Query strings are preserved: several providers put the language or the card id in the query,
    so dropping it would merge genuinely different endpoints.
    """
    parts = urlsplit(url.strip())
    # Evidence stores historically mixed Unicode/raw ampersands with percent-encoded paths.
    # Keep ordinary path punctuation readable, but encode ampersands and non-ASCII characters.
    path = quote(unquote(parts.path), safe="/:@!$'()*+,;=-._~").rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def resolve_provider(url: str | None, source_type: str | None) -> str | None:
    if url:
        host = urlsplit(url).netloc.lower()
        if host in HOST_TO_PROVIDER:
            return HOST_TO_PROVIDER[host]
        for known_host, provider_id in HOST_TO_PROVIDER.items():
            if host.endswith("." + known_host) or host == known_host:
                return provider_id
    for pattern, provider_id in SOURCE_TYPE_PATTERNS:
        if source_type and pattern.search(source_type):
            return provider_id
    return None


def main() -> int:
    units = read_json(ROOT / "verification" / "units.json")
    finish_units = read_json(ROOT / "verification" / "finish_units.json")["units"]
    overrides = read_json(ROOT / "verification" / "finish_overrides.json")
    cards = read_json(ROOT / "snorlax_cards.json")["cards"]
    artists = read_json(ROOT / "artists_pokemontcgio.json")
    bulbapedia_dates = read_json(
        ROOT / "verification" / "bulbapedia_release_dates.json"
    )

    evidence: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []

    def record(url: str | None, source_type: str | None, dimension: str, stable_id: str,
               retrieved: str | None = None) -> None:
        provider_id = resolve_provider(url, source_type)
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
                   unit["unitId"], (unit.get("checkedAt") or "")[:10] or None)

    for unit in finish_units:
        for printing in unit["printings"]:
            for source in printing.get("sources") or []:
                record(source.get("url"), source.get("sourceType"), "finish",
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
        rows.append({
            "canonicalUrl": entry["canonicalUrl"],
            "nonUrlEvidenceId": entry["nonUrlEvidenceId"],
            "providerId": entry["providerId"],
            "sourceTypes": sorted(entry["sourceTypes"]),
            "dimensions": sorted(entry["dimensions"]),
            "stableIdCount": len(entry["stableIds"]),
            "stableIds": sorted(entry["stableIds"])[:50],
            "retrievedAt": entry["retrievedAt"],
            "usageCount": entry["usageCount"],
        })

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
            "generated": date.today().isoformat(),
            "policy": [
                "Every sourced claim maps to exactly one provider. An unmatched source fails generation.",
                "supportsAbsence is true only for complete official manifests, and only within their stated scope.",
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
        if not REGISTRY_PATH.exists() or json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))["evidence"] != rows:
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
        "**`supportsAbsence` is the column that matters.** Only a complete official manifest may",
        "establish that a printing or finish does *not* exist, and only within its stated scope.",
        "For every other provider a missing row is a coverage gap, never a finding.",
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
