"""Uploader errors identify the request, including a missing route on an old build (#741)."""

from io import BytesIO
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from posting import Uploader, UploaderError


class UploaderErrors(unittest.TestCase):
    def test_request_context(self):
        uploader = Uploader("https://uploader.test", "private-key")
        cases = (
            ("media", (b"private-jpeg",), "POST /api/v1/media",
             HTTPError("https://uploader.test/api/v1/media", 404, "Not Found", {},
                       BytesIO(b"<pre>Cannot POST /api/v1/media</pre>")), "HTTP 404"),
            ("upload", ({"caption": "private-caption"},), "POST /api/v1/upload",
             HTTPError("https://uploader.test/api/v1/upload", 400, "Bad Request", {},
                       BytesIO(b'{"error":"Konto fehlt"}')), "HTTP 400: Konto fehlt"),
            ("job", ("job-1",), "GET /api/v1/jobs/job-1",
             HTTPError("https://uploader.test/api/v1/jobs/job-1", 404, "Not Found", {},
                       BytesIO(b'{"error":"Job nicht gefunden"}')), "HTTP 404: Job nicht gefunden"),
            ("accounts", (), "GET /api/v1/accounts", URLError("offline"), "nicht erreichbar"),
        )
        for method, args, context, error, detail in cases:
            with self.subTest(method=method), patch("posting.urlopen", side_effect=error):
                with self.assertRaises(UploaderError) as caught:
                    getattr(uploader, method)(*args)
                message = str(caught.exception)
                self.assertIn(context, message)
                self.assertIn(detail, message)
                for private in ("private-key", "private-jpeg", "private-caption", "<pre>"):
                    self.assertNotIn(private, message)


if __name__ == "__main__":
    unittest.main()
