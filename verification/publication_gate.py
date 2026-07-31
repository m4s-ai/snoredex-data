#!/usr/bin/env python3
"""Require explicit owner approval before an irreversible public deployment (#5, #11)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECISIONS = ROOT / "publication-decisions.json"

# The licensor the owner selected on 2026-07-26. Pinned to one exact string rather than a list of
# candidates: the name is what downstream CC BY-NC-SA attribution must reproduce and who a
# commercial exception would be sought from, so a near-miss spelling is a real defect, not a
# stylistic one. Changing the licensor is an owner decision — edit here and in LICENSE.md together.
LICENSOR = "M4S.Collection"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--actual-visibility",
        help="the repository's real visibility, read from the GitHub API by the deploy workflow. "
        "Without it this gate can only check what the decision file claims.",
    )
    args = parser.parse_args()

    try:
        decision = json.loads(DECISIONS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"publication approval unavailable: {error}", file=sys.stderr)
        return 1

    required_true = {
        "sitePublicationApproved",
        "licenseGrantsApproved",
        "ownerAttestationsApproved",
        "thirdPartyImagesApproved",
    }
    problems = [f"{key} must be true" for key in sorted(required_true) if decision.get(key) is not True]

    if decision.get("licensor") != LICENSOR:
        problems.append(f"licensor must be exactly {LICENSOR!r}")
    if not decision.get("approvedBy"):
        problems.append("approvedBy must identify the approving repository owner")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(decision.get("approvedAt") or "")):
        problems.append("approvedAt must be an ISO date")

    visibility = decision.get("repositoryVisibility")
    if visibility not in {"private", "public"}:
        problems.append("repositoryVisibility must be private or public")
    if visibility == "public" and decision.get("repositoryPublicationApproved") is not True:
        problems.append("repositoryPublicationApproved must be true before public visibility")

    # The site's only correction affordance is a link into this repository's issue tracker. A
    # public site in front of a private tracker asks strangers for help and then 404s them, so
    # the two decisions are not independent. Check P8 in review_findings.py mirrors this.
    site = ROOT / "index.html"
    if site.exists() and "github.com/m4s-ai/snoredex-data" in site.read_text(encoding="utf-8"):
        if visibility != "public" or decision.get("repositoryPublicationApproved") is not True:
            problems.append(
                "the site links corrections to this repository, so repositoryVisibility must be "
                "public and repositoryPublicationApproved true — otherwise every correction link "
                "on the published site is a 404 for visitors"
            )

    # Everything above trusts the decision file's claim about visibility. That claim is the one
    # the correction loop depends on, and it is easy to record without performing: set it to
    # "public", forget the actual toggle, and the site publishes with every correction link 404ing
    # for the visitors it is asking for help. The deploy workflow reads the real value from the
    # API and passes it here, so the record has to match the world.
    if args.actual_visibility:
        if args.actual_visibility not in {"private", "public"}:
            problems.append(f"unrecognized actual visibility {args.actual_visibility!r}")
        elif args.actual_visibility != visibility:
            problems.append(
                f"the decision file records repositoryVisibility={visibility!r}, but the "
                f"repository is actually {args.actual_visibility!r}. Fix whichever is wrong "
                f"before publishing — a public site in front of a private tracker is broken"
            )

    if problems:
        print("publication remains blocked:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"publication approved by {decision['approvedBy']} on {decision['approvedAt']}")
    if args.actual_visibility:
        print(f"repository visibility: {visibility} (verified against the GitHub API)")
    else:
        print(f"repository visibility decision: {visibility} (recorded, not verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
