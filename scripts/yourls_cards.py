#!/usr/bin/env python3
"""Plan or provision a permanent YOURLS alias for an approved Snoredex card."""
from __future__ import annotations

import argparse
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
import re
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from build import ASSET_BASE_URL
from card_pages import ITEM_ID, ROOT, approved_preview, read_social
from check import load

SHORT_BASE = "https://go.m4s.eu/"
API_URL = SHORT_BASE + "yourls-api.php"
KEYWORD = re.compile(r"[a-z0-9]{1,40}")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ShareMetadata(HTMLParser):
    def __init__(self, data: bytes):
        super().__init__()
        self.properties = {}
        self.feed(data.decode("utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        prop = attrs.get("property") or ""
        if tag == "meta" and prop.startswith("og:"):
            self.properties.setdefault(prop, attrs.get("content"))


def request(url: str, limit: int, form=None, expected_errors=()) -> bytes:
    body = urlencode(form).encode("ascii") if form else None
    try:
        response = build_opener(NoRedirect).open(Request(url, data=body), timeout=12)
    except HTTPError as error:
        if error.code not in expected_errors:
            error.close()
            raise ValueError(f"Unexpected HTTP {error.code} from {url}") from None
        response = error
    with response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Response too large from {url}")
    return data


def call_api(signature: str, action: str, **params) -> dict:
    errors = {"expand": (404,), "shorturl": (409,)}
    body = request(API_URL, 65536, dict(params, action=action, format="json", signature=signature),
                   errors[action])
    result = json.loads(body)
    if not isinstance(result, dict):
        raise ValueError("Unexpected YOURLS response")
    return result


def expanded_target(api, alias: str) -> str | None:
    row = api("expand", shorturl=alias)
    if row.get("keyword") != alias:
        raise ValueError("YOURLS did not return the requested keyword")
    if str(row.get("errorCode")) == "404" and "longurl" not in row:
        return None
    if str(row.get("statusCode")) != "200" or row.get("shorturl") != SHORT_BASE + alias:
        raise ValueError("YOURLS did not confirm the requested short URL")
    target = row.get("longurl")
    if not isinstance(target, str) or not target:
        raise ValueError("YOURLS did not return a destination")
    return target


def select_keyword(rows: dict, item_id: str, alias: str | None) -> str:
    recorded = rows[item_id].get("shortAlias")
    alias = alias or recorded or ("sd" + item_id[5:].replace("-", "")[:12])
    if not KEYWORD.fullmatch(alias) or not alias.startswith("sd"):
        raise ValueError("Use a lowercase alphanumeric YOURLS keyword in the sd namespace")
    if recorded and alias != recorded:
        raise ValueError("This printing already has a permanent keyword")
    if any(key != item_id and entry.get("shortAlias") == alias for key, entry in rows.items()):
        raise ValueError("This keyword is already registered for another printing")
    return alias


def card_plan(item_id: str, alias: str | None) -> tuple[dict, str]:
    rows = read_social(ROOT)
    if not ITEM_ID.fullmatch(item_id) or item_id not in rows:
        raise ValueError("A configured Snoredex printing is required")
    row = rows[item_id]
    alias = select_keyword(rows, item_id, alias)
    model = load()
    photos = {asset["path"]: asset for asset in model["images"]["assets"]}
    preview = approved_preview(ROOT, model, row, photos)
    return dict(itemId=item_id, shortAlias=alias, shortUrl=SHORT_BASE + alias,
                targetUrl=f"{ASSET_BASE_URL}cards/{item_id}/", previewUrl=ASSET_BASE_URL + preview), preview


def verify_public_page(plan: dict, preview: str) -> None:
    maximum = 2 * 1024 * 1024
    metadata = ShareMetadata(request(plan["targetUrl"], maximum)).properties
    if metadata.get("og:url") != plan["targetUrl"] or metadata.get("og:image") != plan["previewUrl"]:
        raise ValueError("The published card metadata does not match the selected printing")
    remote = request(plan["previewUrl"], maximum)
    if sha256(remote).digest() != sha256((ROOT / preview).read_bytes()).digest():
        raise ValueError("The published preview bytes do not match the approved specimen preview")


def verify_redirect(plan: dict) -> int:
    try:
        with build_opener(NoRedirect).open(Request(plan["shortUrl"]), timeout=12):
            raise ValueError("The public short URL did not redirect")
    except HTTPError as response:
        with response:
            if response.code not in (301, 302, 303, 307, 308) or response.headers["Location"] != plan["targetUrl"]:
                raise ValueError("The public short URL does not redirect to the verified card") from None
            return response.code


def provision(api, plan: dict, preview: str, create: bool) -> str:
    alias, target = plan["shortAlias"], plan["targetUrl"]
    selected = expanded_target(api, alias)
    if selected == target:
        verify_public_page(plan, preview)
        return "verified"
    if selected is not None:
        raise ValueError("Keyword points elsewhere. It was not changed.")
    if not create:
        return "unassigned"
    verify_public_page(plan, preview)
    create_keyword(api, plan)
    return "verified"


def create_keyword(api, plan: dict) -> None:
    alias, target = plan["shortAlias"], plan["targetUrl"]
    try:
        result = api("shorturl", keyword=alias, url=target, title=f"Snoredex {plan['itemId']}")
        if result.get("shorturl") != plan["shortUrl"]:
            raise ValueError("YOURLS returned a different short URL")
    except (OSError, ValueError):
        # A timeout or duplicate response can follow a write. Never retry before expanding again.
        pass
    if expanded_target(api, alias) != target:
        raise ValueError("YOURLS did not confirm the exact assignment. No creation was retried.")


def batch_plans(item_ids: list[str], keyword: str | None) -> list[tuple[dict, str]]:
    if not 1 <= len(item_ids) <= 3 or len(set(item_ids)) != len(item_ids):
        raise ValueError("Supply one to three distinct item IDs")
    if keyword and len(item_ids) != 1:
        raise ValueError("A custom keyword applies to a single printing")
    plans = [card_plan(item_id, keyword) for item_id in item_ids]
    if len({plan["shortAlias"] for plan, _ in plans}) != len(plans):
        raise ValueError("Two items in the batch would use the same YOURLS keyword")
    return plans


def run_batch(args) -> list[dict]:
    plans = batch_plans(args.item_id, args.keyword)
    if not (args.check or args.create):
        return [dict(plan, status="plan") for plan, _ in plans]
    signature = os.environ.get("SNOREDEX_YOURLS_SIGNATURE")
    if not signature:
        raise ValueError("The protected execution environment needs SNOREDEX_YOURLS_SIGNATURE")
    return [provision_result(signature, plan, preview, args.create) for plan, preview in plans]


def provision_result(signature: str, plan: dict, preview: str, create: bool) -> dict:
    """Keep every item's outcome so one failure cannot discard its neighbours' verified aliases."""
    try:
        status = provision(lambda action, **params: call_api(signature, action, **params),
                           plan, preview, create)
        result = dict(plan, status=status)
        if status == "verified":
            result["redirectStatus"] = verify_redirect(plan)
        return result
    except (OSError, ValueError) as error:
        return dict(plan, status="failed", error=str(error))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("item_id", nargs="+", help="item IDs of published cards in data/social.json")
    parser.add_argument("--keyword", help="choose a free sd keyword for a single printing")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="check keywords and the published cards")
    mode.add_argument("--create", action="store_true", help="create unused keywords after verifying their cards")
    args = parser.parse_args()
    try:
        results = run_batch(args)
    except (OSError, ValueError) as error:
        parser.exit(2, f"YOURLS: {error}\n")
    print(json.dumps(results[0] if len(results) == 1 else results, indent=2))
    return 2 if any(result["status"] == "failed" for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
