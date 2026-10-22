#!/usr/bin/env python3
"""Recheck exact TCGCSV product identity and declared subtypes (#50, Wave 3).

Ported from `verify_finish_sources.ps1`. `finish_overrides.json` claims that specific TCGplayer
products exist and carry specific printings; this asks TCGCSV whether that is still true. It is
the only check in the toolchain whose input is somebody else's server, which is why it went last.

    python verification/verify_finish_sources.py              # live, as the release gate runs it
    python verification/verify_finish_sources.py --replay     # against the recorded fixture
    python verification/verify_finish_sources.py --record     # refresh the fixture from live

Exit codes are the PowerShell's and the gate depends on them: 0 when every assertion holds, 1 on
a data mismatch, 2 when an endpoint could not be reached. The distinction matters — a mismatch
means the claim is wrong and someone must look, an unreachable endpoint means try again later.

A product that still exists but has no current price row at all is reported as `[NODATA]` and
does not fail: the price export only lists products with current market data, so its silence is a
gap, never a contradiction of the retained observation (AGENTS rule 3). A missing product, or a
price row present without the expected subtype, still fails. `--record` refuses (exit 2) while any
product has no price row, so a gap can never overwrite the fixture's positive rows.

The fixture exists so the *logic* can be proved when TCGCSV is down, slow, or drifting. It keeps
only the rows these assertions look up, projected to the two fields they read, so it is a
projection rather than a recording: four kilobytes instead of a megabyte of somebody else's
catalogue, and it cannot prove that a change in the upstream payload shape is handled. The live
path proves that, and the gate runs the live path.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import date

from checks import VERIFICATION, read_json, write_json

FIXTURE = VERIFICATION / "fixtures" / "tcgcsv_finish_sources.json"
USER_AGENT = "snoredex-data/finish-source-verification"
TIMEOUT = 60

# Only what the assertions read. A product is identified by id and named for the failure message;
# a price row contributes its subtype. Recording whole payloads would put megabytes of somebody
# else's catalogue in the repository to prove one field each.
PRODUCT_FIELDS = ("productId", "name")
PRICE_FIELDS = ("productId", "subTypeName")


class Responses:
    """Fetches, or replays, keyed by URL. One request per URL however often it is asked for."""

    def __init__(self, replay: dict | None = None) -> None:
        self.cache: dict[str, dict] = dict(replay or {})
        self.live = replay is None
        self.network_failures: list[str] = []

    def get(self, url: str) -> dict:
        if url not in self.cache:
            if not self.live:
                detail = "not present in the fixture"
                self.network_failures.append(f"{url} — {detail}")
                self.cache[url] = {"success": False, "results": [], "error": detail}
                return self.cache[url]
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                    payload = json.load(response)
                self.cache[url] = {"success": True,
                                   "results": list(payload.get("results") or []), "error": None}
            except (urllib.error.URLError, OSError, ValueError) as error:
                detail = str(error)
                self.network_failures.append(f"{url} — {detail}")
                self.cache[url] = {"success": False, "results": [], "error": detail}
        return self.cache[url]


def project(results: list[dict], fields: tuple[str, ...]) -> list[dict]:
    return [{field: row.get(field) for field in fields} for row in results]


def product_subtypes(prices: list[dict], product_id: int) -> list[str]:
    """The distinct price subtypes TCGCSV currently reports for one product, in export order."""
    actual: list[str] = []
    for row in prices:
        if row.get("productId") == product_id and row.get("subTypeName") not in actual:
            actual.append(row.get("subTypeName"))
    return actual


def blocking_exit(failures: list[str], no_price_data: list[str],
                  network_failures: list[str], recording: bool) -> int | None:
    """Report the outcome and return the exit code that stops the run, or None to continue."""
    for notice in no_price_data:
        print(f"[NODATA] {notice}")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print(f"Finish-source DATA MISMATCH for {len(failures)} assertion(s).", file=sys.stderr)
        return 1

    if network_failures:
        for failure in network_failures:
            print(f"[RETRY] {failure}")
        print(f"Finish-source verification could not reach {len(network_failures)} "
              "endpoint(s); this is a transient network failure, not a data mismatch.",
              file=sys.stderr)
        return 2

    if recording and no_price_data:
        # Recording now would replace the fixture's last positive rows with the export's gap.
        print("Refusing to record the fixture while a product has no current price row; "
              "retry after the next TCGCSV update.", file=sys.stderr)
        return 2
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--replay", action="store_true", help="use the recorded fixture")
    group.add_argument("--record", action="store_true", help="refresh the fixture from live")
    args = parser.parse_args()

    overrides = read_json(VERIFICATION / "finish_overrides.json")

    replay = None
    if args.replay:
        if not FIXTURE.exists():
            print(f"no fixture at {FIXTURE.relative_to(VERIFICATION.parent)}; "
                  "run with --record first", file=sys.stderr)
            return 2
        replay = read_json(FIXTURE)["responses"]
    responses = Responses(replay)

    failures: list[str] = []
    no_price_data: list[str] = []
    checked_sources = 0
    checked_products = 0
    wanted_rows: dict[str, tuple[tuple[str, ...], set[int]]] = {}

    for name, source in (overrides.get("sources") or {}).items():
        expectations = source.get("expectedSubtypes")
        if not expectations:
            continue

        checked_sources += 1
        identity_url = (source.get("identityUrl") or "").strip()
        price_url = (source.get("url") or "").strip()
        if not identity_url or not price_url:
            failures.append(f"{name} has expectedSubtypes but no identityUrl or price URL")
            continue

        product_response = responses.get(identity_url)
        price_response = responses.get(price_url)
        if not product_response["success"] or not price_response["success"]:
            continue
        products = product_response["results"]
        prices = price_response["results"]
        # Accumulated per URL, not per source: two sources share the .../2374/products endpoint,
        # and recording each source's slice separately let the second overwrite the first, which
        # made three products vanish from the fixture and fail on replay.
        wanted = {int(raw_id) for raw_id in expectations}
        wanted_rows.setdefault(identity_url, (PRODUCT_FIELDS, set()))[1].update(wanted)
        wanted_rows.setdefault(price_url, (PRICE_FIELDS, set()))[1].update(wanted)

        for raw_id, expected in expectations.items():
            checked_products += 1
            product_id = int(raw_id)
            product = next((p for p in products if p.get("productId") == product_id), None)
            if not product:
                failures.append(f"{name} product {product_id} is absent from {identity_url}")
                continue

            actual = product_subtypes(prices, product_id)
            expected_subtypes = list(expected)
            if not actual:
                # The product still exists but has no current price row at all. That is the
                # export's silence, not a disagreement: the retained observation stands (rule 3).
                no_price_data.append(f"{name} product {product_id} ({product.get('name')}) "
                                     "has no current price row; expected "
                                     f"{', '.join(expected_subtypes)}")
                continue
            missing = [subtype for subtype in expected_subtypes if subtype not in actual]
            if missing:
                failures.append(f"{name} product {product_id} ({product.get('name')}) "
                                f"is missing: {', '.join(missing)}")
                continue

            print(f"[OK  ] {name} product {product_id}: {' + '.join(expected_subtypes)}")

    stop = blocking_exit(failures, no_price_data, responses.network_failures, args.record)
    if stop is not None:
        return stop

    if args.record:
        recorded = {
            url: {"success": True, "error": None,
                  "results": project([row for row in responses.cache[url]["results"]
                                      if row.get("productId") in ids], fields)}
            for url, (fields, ids) in wanted_rows.items()
        }
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        write_json(FIXTURE, {
            "recordedAt": date.today().isoformat(),
            "note": ("Projection of the TCGCSV responses this check reads, so its logic can be "
                     "proved offline. Refresh with: python verification/verify_finish_sources.py "
                     "--record"),
            "responses": recorded,
        })
        print(f"\nrecorded {len(recorded)} responses to "
              f"{FIXTURE.relative_to(VERIFICATION.parent)}")
        return 0

    print()
    print(f"Verified {checked_products - len(no_price_data)} TCGCSV products across "
          f"{checked_sources} source records; {len(no_price_data)} without a current price row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
