"""Offline YOURLS protocol and safety checks."""
from email.message import Message
from io import BytesIO
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from yourls_cards import ROOT, SHORT_BASE, card_plan, provision, verify_public_page, verify_redirect

POKE = "item-b26a638d-ed89-538b-ab49-a5c879572f60"
MASTER = "item-a2f8335e-94ff-54d2-8b10-5bdf55349451"


class YourlsTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.preview = card_plan(POKE, None)
        self.missing = {"keyword": self.plan["shortAlias"], "errorCode": "404"}
        self.found = {"keyword": self.plan["shortAlias"], "statusCode": "200",
                      "shorturl": self.plan["shortUrl"], "longurl": self.plan["targetUrl"]}

    def test_variant_plans_have_distinct_links_and_previews(self):
        other, _ = card_plan(MASTER, None)
        for field in ("shortUrl", "targetUrl", "previewUrl"):
            self.assertNotEqual(self.plan[field], other[field])

    def test_check_and_collision_never_create(self):
        api = Mock(return_value=self.missing)
        self.assertEqual(provision(api, self.plan, self.preview, False), "unassigned")
        api.assert_called_once_with("expand", shorturl=self.plan["shortAlias"])
        for invalid in (dict(self.found, longurl="https://example.com/"), dict(self.found, keyword="else")):
            api = Mock(return_value=invalid)
            with self.assertRaises(ValueError):
                provision(api, self.plan, self.preview, True)
            api.assert_called_once_with("expand", shorturl=self.plan["shortAlias"])

    def test_create_waits_for_public_target_and_checks_assignments(self):
        api = Mock(side_effect=[self.missing, {"status": "success"}, self.found])
        with patch("yourls_cards.verify_public_page", side_effect=ValueError):
            with self.assertRaises(ValueError):
                provision(api, self.plan, self.preview, True)
        self.assertEqual(api.call_count, 1)
        api = Mock(side_effect=[self.missing, {"status": "success"}, self.found, self.found])
        with patch("yourls_cards.verify_public_page"):
            self.assertEqual(provision(api, self.plan, self.preview, True), "verified")
            self.assertEqual(provision(api, self.plan, self.preview, True), "verified")
        self.assertEqual([call.args[0] for call in api.call_args_list], ["expand", "shorturl", "expand", "expand"])

    def test_published_metadata_and_preview_must_match(self):
        markup = (f'<meta property="og:url" content="{self.plan["targetUrl"]}">'
                  f'<meta property="og:image" content="{self.plan["previewUrl"]}">').encode()
        png = (ROOT / self.preview).read_bytes()
        with patch("yourls_cards.request", side_effect=[markup, png]):
            verify_public_page(self.plan, self.preview)
        with patch("yourls_cards.request", side_effect=[markup, b"wrong photo"]):
            with self.assertRaisesRegex(ValueError, "preview bytes"):
                verify_public_page(self.plan, self.preview)

    def test_public_redirect_is_detected_without_following_it(self):
        headers = Message()
        headers["Location"] = self.plan["targetUrl"]
        response = HTTPError(SHORT_BASE, 301, "Moved", headers, BytesIO())
        with patch("yourls_cards.build_opener") as opener:
            opener.return_value.open.side_effect = response
            self.assertEqual(verify_redirect(self.plan), 301)
            self.assertEqual(opener.return_value.open.call_args.args[0].method, "HEAD")


if __name__ == "__main__":
    unittest.main()
