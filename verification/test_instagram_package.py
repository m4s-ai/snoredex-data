"""Local Instagram draft regression checks. Requires Pillow like the exporter."""
from io import BytesIO
import unittest

from PIL import Image

from instagram_package import load, post_copy, post_image, release_label
from owner_photo import owner_specimen


class InstagramDraftTests(unittest.TestCase):
    def test_release_precision_keeps_estimate(self):
        edition = {"releaseDate": "2026-11-01", "releaseDatePrecision": "month", "releaseApproximate": True}
        self.assertEqual(release_label({}, edition), "ca. November 2026")
        self.assertEqual(release_label({"releaseDate": "2026", "releaseDatePrecision": "year"}, edition), "2026")
        self.assertEqual(release_label({"releaseDate": "2026-11-12", "releaseDatePrecision": "day"}, {}),
                         "12. November 2026")
        self.assertEqual(release_label({"releaseDate": "2026-11-01"}, edition), "")

    def test_adjacent_variants_keep_distinct_copy(self):
        model = load()
        cases = [("SPEC-0779", "Pokéball", "pilot-poke"), ("SPEC-0780", "Meisterball", "pilot-master")]
        for sid, foil, alias in cases:
            with self.subTest(specimen=sid):
                _, item = owner_specimen(model, sid)
                caption, alt = post_copy(model, item, f"https://go.m4s.eu/{alias}")
                self.assertIn("158/204", caption)
                self.assertIn(foil, caption)
                self.assertIn(foil, alt)
                self.assertIn(f"https://go.m4s.eu/{alias}", caption)
                self.assertNotIn("[Kurzlink fehlt]", caption)

    def test_orientation_and_crop(self):
        raw = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new("RGB", (1000, 800), "navy").save(raw, "JPEG", exif=exif)
        corners = [(10, 10), (789, 10), (789, 989), (10, 989)]
        data, geometry = post_image(raw.getvalue(), corners)
        self.assertEqual(geometry["outputDimensions"], [779, 979])
        with Image.open(BytesIO(data)) as draft:
            self.assertEqual(draft.size, (1080, 1350))
            self.assertEqual(len(draft.getexif()), 0)


if __name__ == "__main__":
    unittest.main()
