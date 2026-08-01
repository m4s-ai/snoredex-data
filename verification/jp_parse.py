#!/usr/bin/env python3
"""Read the illustrator credit from a pokemon-card.com detail page (#33).

The page carries the credit in its own field:

    <div class="author">
      <h4>イラストレーター</h4>
      <a href="/card-search/index.php?regulation_illust=all&illust=Shizurow">Shizurow</a>
    </div>

`archive/passes/jp_fetch.ps1` instead stripped every tag and matched the credit out of the
resulting run-on text, cutting it off at the first of a list of following labels. That cannot
work. Flattening glues the credit to whatever the layout puts next to it, and a real credit may
itself contain spaces and Latin punctuation, so "Shizurow レベルアップ LV. X" is indistinguishable
from a four-word artist name. Two credits reached the committed data that way:

    aky CG Works V進化          (V進化 is the evolution-stage label)
    Shizurow レベルアップ LV. X   (レベルアップ LV. X is the Lv.X stage label)

Widening the terminator list would only have moved the failure to the next stage label. Reading
the anchor removes the ambiguity instead of narrowing it.

The archived pass keeps its original text-matching code: it is the record of how the committed
data was produced, `review_findings.py` check X3 hashes it, and a corrected copy would be a new
script claiming to be the one that ran. This module is what a future JP fetch should call.

Fixtures for the page shapes live in verification/fixtures/jp/, asserted by
verification/test_jp_parser.py.
"""

from __future__ import annotations

import html as html_module
import re

# The anchor inside div.author. Non-greedy on both halves so a later block cannot extend either
# match, and DOTALL because the field spans lines.
_AUTHOR = re.compile(r'<div\s+class="author"\s*>(?P<body>.*?)</div>', re.DOTALL)
_ANCHOR = re.compile(r"<a\b[^>]*>(?P<name>.*?)</a>", re.DOTALL)


def illustrator(page: str | None) -> str | None:
    """Return the credited illustrator, or None if the page does not carry one.

    None means "this page has no illustrator field", which is a different answer from a partial
    name. Returning a best guess is what put the two corrupted credits into the data.
    """
    if not page:
        return None

    author = _AUTHOR.search(page)
    if not author:
        return None

    anchor = _ANCHOR.search(author.group("body"))
    if not anchor:
        return None

    # The anchor text is the name itself. Nested markup would be a page-structure change worth
    # noticing rather than silently stripping, so decode entities and do nothing else.
    name = html_module.unescape(anchor.group("name"))
    name = re.sub(r"\s+", " ", name).strip()
    return name or None
