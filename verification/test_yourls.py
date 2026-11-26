"""Offline YOURLS protocol and safety checks."""
from email.message import Message
from contextlib import redirect_stdout
from io import BytesIO
from io import StringIO
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from yourls_cards import ROOT, SHORT_BASE, batch_plans, card_plan, main, provision, run_batch, verify_public_page, verify_redirect

POKE = "item-b26a638d-ed89-538b-ab49-a5c879572f60"
MASTER = "item-a2f8335e-94ff-54d2-8b10-5bdf55349451"
PLAIN = "item-bbea2621-c8f4-5647-b576-e309aa29d24a"


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

    def test_uncertain_create_is_reconciled_without_retry(self):
        for response in (TimeoutError(), {"shorturl": SHORT_BASE + "sddifferent"}):
            with self.subTest(response=response):
                api = Mock(side_effect=[self.missing, response, self.found])
                with patch("yourls_cards.verify_public_page"):
                    self.assertEqual(provision(api, self.plan, self.preview, True), "verified")
                self.assertEqual([call.args[0] for call in api.call_args_list], ["expand", "shorturl", "expand"])

                api = Mock(side_effect=[self.missing, response, self.missing])
                with patch("yourls_cards.verify_public_page"):
                    with self.assertRaisesRegex(ValueError, "No creation was retried"):
                        provision(api, self.plan, self.preview, True)
                self.assertEqual(api.call_count, 3)

    def test_failed_expansion_is_not_absence(self):
        api = Mock(side_effect=ValueError("HTTP 403"))
        with self.assertRaisesRegex(ValueError, "403"):
            provision(api, self.plan, self.preview, True)
        api.assert_called_once_with("expand", shorturl=self.plan["shortAlias"])

    def test_batch_preserves_variant_identity_and_order(self):
        normal = batch_plans([POKE, MASTER], None)
        reversed_order = batch_plans([MASTER, POKE], None)
        self.assertEqual(reversed_order, normal[::-1])
        self.assertEqual(batch_plans([POKE, MASTER], None), normal)
        for item_ids, keyword in (([POKE, POKE], None), ([POKE, "unknown"], None), ([POKE], "existing")):
            with self.assertRaises(ValueError):
                batch_plans(item_ids, keyword)

    def test_batch_provisions_distinct_variants_once_each_in_either_order(self):
        targets, created = {}, []

        def fake_api(_, action, **params):
            if action == "shorturl":
                keyword = params["keyword"]
                created.append(keyword)
                targets[keyword] = params["url"]
                return {"shorturl": SHORT_BASE + keyword}
            keyword = params["shorturl"]
            if keyword not in targets:
                return {"keyword": keyword, "errorCode": "404"}
            return {"keyword": keyword, "statusCode": "200",
                    "shorturl": SHORT_BASE + keyword, "longurl": targets[keyword]}

        with (patch.dict("os.environ", SNOREDEX_YOURLS_SIGNATURE="mock-value"),
              patch("yourls_cards.call_api", side_effect=fake_api),
              patch("yourls_cards.verify_public_page"), patch("yourls_cards.verify_redirect", return_value=302)):
            first = run_batch(SimpleNamespace(item_id=[POKE, MASTER], keyword=None, check=False, create=True))
            reverse = run_batch(SimpleNamespace(item_id=[MASTER, POKE], keyword=None, check=False, create=True))
        self.assertEqual(first, reverse[::-1])
        self.assertEqual(created, [row["shortAlias"] for row in first])
        self.assertEqual(len(targets), 2)

    def test_batch_keeps_successes_before_and_after_a_failed_item(self):
        args = SimpleNamespace(item_id=[POKE, MASTER, PLAIN], keyword=None, check=False, create=True)
        with (patch.dict("os.environ", SNOREDEX_YOURLS_SIGNATURE="mock-value"),
              patch("yourls_cards.provision", side_effect=["verified", ValueError("Keyword points elsewhere"), "verified"]),
              patch("yourls_cards.verify_redirect", return_value=302)):
            results = run_batch(args)
        self.assertEqual([row["itemId"] for row in results], args.item_id)
        self.assertEqual([row["status"] for row in results], ["verified", "failed", "verified"])
        self.assertEqual([results[0]["redirectStatus"], results[2]["redirectStatus"]], [302, 302])
        self.assertNotIn("redirectStatus", results[1])
        self.assertIn("Keyword points elsewhere", results[1]["error"])

    def test_failed_public_redirect_is_not_a_verified_result(self):
        args = SimpleNamespace(item_id=[POKE, MASTER], keyword=None, check=False, create=True)
        with (patch.dict("os.environ", SNOREDEX_YOURLS_SIGNATURE="mock-value"),
              patch("yourls_cards.provision", return_value="verified"),
              patch("yourls_cards.verify_redirect", side_effect=[TimeoutError("Redirect timed out"), 302])):
            results = run_batch(args)
        self.assertEqual([row["status"] for row in results], ["failed", "verified"])
        self.assertNotIn("redirectStatus", results[0])

    def test_cli_preserves_partial_json_and_returns_failure(self):
        results = [dict(self.plan, status="verified", redirectStatus=302), {"itemId": MASTER, "status": "failed"}]
        output = StringIO()
        with (patch("sys.argv", ["yourls_cards.py", "--create", POKE, MASTER]),
              patch("yourls_cards.run_batch", return_value=results), redirect_stdout(output)):
            self.assertEqual(main(), 2)
        self.assertEqual(json.loads(output.getvalue()), results)

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
            self.assertEqual(opener.return_value.open.call_args.args[0].get_method(), "GET")


if __name__ == "__main__":
    unittest.main()
