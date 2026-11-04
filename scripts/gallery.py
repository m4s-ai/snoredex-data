"""Project the current catalogue into the artwork gallery rendered by site.py."""

UNDATED = "9999-99-99"


def release_groups(artwork, review):
    aliases = {image_group: group for group, members in review["artworkGroups"].items()
               for image_group in members}
    groups = {}
    for group in artwork["groups"]:
        group_id = group["groupId"]
        family = aliases.get(group_id, group_id)
        for member in group["members"]:
            groups[member["cardReleaseId"]] = member.get("reviewedAppearanceId") or family
    return groups


def is_rejected(item, rejected):
    return f"{item['cardReleaseId']}\x1f{item['finish']}" in rejected


def matches_research(item, candidate):
    return (item["finish"] == candidate["finish"]
            and (not candidate.get("foilPattern") or "wave" in str(item["foilPattern"]).lower())
            and (item["distribution"] or {}).get("kind") == (candidate.get("distribution") or {}).get("kind"))


def research_item(candidate, related, status):
    base = min((row for row in related if row["finish"] == "non-holo"), default=None,
               key=lambda row: row["itemId"])
    if not base or any(matches_research(row, candidate) for row in related):
        return None
    pattern = candidate.get("foilPattern")
    note = "Italian Wave Holo hypothesis." if pattern else None
    if note and base["completenessStatus"] == "owner-adjudicated" and {row["finish"] for row in related} == {"non-holo"}:
        note += " The documented finish list is closed at non-holo."
    issue = candidate["issue"]
    return dict(base, itemId=candidate["id"], itemKind="research-placeholder",
                finish=candidate["finish"], foilPattern=pattern, finishVerificationStatus=status,
                distribution=candidate.get("distribution"),
                releaseDate=None, releaseDatePrecision=None, releaseApproximate=False,
                imageAssetId=None, sourceLinks=[], markings=[], researchNote=note,
                evidenceLinks=[f"https://github.com/m4s-ai/snoredex-data/issues/{issue}"])


def open_research(items, research, rejected, verdicts):
    for candidate in research:
        release = candidate["release"]
        status = verdicts.get(candidate["unit"]) if "unit" in candidate else "pending"
        if status not in {"pending", "needs-evidence", "disputed"} or f"{release}\x1f{candidate['finish']}" in rejected:
            continue
        related = [row for row in items if row["cardReleaseId"] == release]
        if row := research_item(candidate, related, status):
            yield row


def gallery_images(item, assets, review, derivatives):
    source = review["reviewedImages"].get(item["itemId"])
    if item["imageScope"] == "exact-printing":
        source = assets.get(item["imageAssetId"], {}).get("path") or source
    if not source:
        return {}
    if source in review["photoDerivatives"]:
        return dict(review["photoDerivatives"][source], imageSource=source)
    record = derivatives.get(source, {})
    paths = {kind: record.get(kind, {}).get("path") or source for kind in ("thumbnail", "preview")}
    return dict(paths, imageSource=source)


def release_artist_fallbacks(items, artists):
    by_release = {}
    for item in items:
        if artist := artists.get(item["itemId"]):
            by_release.setdefault(item["cardReleaseId"], set()).add(artist)
    return {release: next(iter(credits)) for release, credits in by_release.items() if len(credits) == 1}


def gallery_card(item, group, artist, language, images):
    number = item["collectorNumber"] or ""
    if number and item["collectorNumberDenominator"]:
        number += "/" + item["collectorNumberDenominator"]
    return {
        "id": item["itemId"], "group": group,
        "name": item["localCardName"] or item["cardName"],
        "set": item["localSetName"], "setCode": item["localSetCode"], "number": number,
        "artist": artist, "language": language,
        "edition": item["edition"], "finish": item["finish"], "foilPattern": item["foilPattern"],
        "markings": [mark["text"] for mark in item["markings"] if mark.get("text")],
        "distribution": (item["distribution"] or {}).get("name"), "cardSize": item["cardSize"],
        "date": item["releaseDate"], "datePrecision": item["releaseDatePrecision"],
        "approximate": item["releaseApproximate"],
        "kind": item["itemKind"], "status": item["finishVerificationStatus"],
        "note": item.get("researchNote"), "thumbnail": images.get("thumbnail"),
        "preview": images.get("preview"), "imageSource": images.get("imageSource"),
        "sources": sorted(set(item["sourceLinks"]) | set(item["evidenceLinks"])),
    }


def chronological_cards(cards, release_sort):
    group_dates = {}
    dates = {card["id"]: release_sort(card["date"]) if card["date"] else UNDATED for card in cards}
    for card in cards:
        if card["kind"] == "verified-printing":
            group = card["group"]
            group_dates[group] = min(group_dates.get(group, UNDATED), dates[card["id"]])
    ordered = sorted(cards, key=lambda row: (group_dates.get(row["group"], UNDATED), row["group"],
                                            dates[row["id"]], row["id"]))
    groups = dict.fromkeys(card["group"] for card in ordered)
    numbers = {group: number for number, group in enumerate(groups, start=1)}
    return [dict(card, artworkNumber=numbers[card["group"]]) for card in ordered]


def gallery_cards(catalogue, artwork, review, derivatives, releases, release_sort, rejected, verdicts):
    localizations = {row["localizationId"]: row["displayName"] for row in catalogue["localizations"]}
    assets = {row["assetId"]: row for row in catalogue["assets"]}
    artists = {row["rowId"]: row["artist"] for row in releases if row["artist"]}
    groups = release_groups(artwork, review)
    items = [row for row in catalogue["items"] if row["active"] and not is_rejected(row, rejected)]
    release_artists = release_artist_fallbacks(items, artists)
    candidates = list(open_research(items, review["research"], rejected, verdicts))
    cards = []
    for item in items + candidates:
        release = item["cardReleaseId"]
        cards.append(gallery_card(
            item, groups.get(release, release), artists.get(item["itemId"], release_artists.get(release)),
            localizations[item["localizationId"]], gallery_images(item, assets, review, derivatives),
        ))
    return chronological_cards(cards, release_sort)
