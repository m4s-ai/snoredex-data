"""Local Instagram draft regression checks. Requires Pillow like the exporter."""
from io import BytesIO
import re
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image, ImageCms, ImageDraw

from instagram_package import digest, edited_post_image, load, package, post_copy, post_image, release_label
from owner_photo import owner_specimen


class InstagramDraftTests(unittest.TestCase):
    def test_release_precision_keeps_estimate(self):
        edition = {"releaseDate": "2026-11-01", "releaseDatePrecision": "month", "releaseApproximate": True}
        self.assertEqual(release_label({}, edition), "c. November 2026")
        self.assertEqual(release_label({"releaseDate": "2026", "releaseDatePrecision": "year"}, edition), "2026")
        self.assertEqual(release_label({"releaseDate": "2026-11-12", "releaseDatePrecision": "day"}, {}),
                         "12 November 2026")
        self.assertEqual(release_label({"releaseDate": "2026-11-01"}, edition), "")

    def test_adjacent_variants_keep_distinct_copy(self):
        model = load()
        cases = [("SPEC-0779", "Poké Ball", "pilot-poke"), ("SPEC-0780", "Master Ball", "pilot-master")]
        for sid, foil, alias in cases:
            with self.subTest(specimen=sid):
                _, item = owner_specimen(model, sid)
                caption, alt = post_copy(model, item, f"https://go.m4s.eu/{alias}")
                self.assertIn("158/204", caption)
                self.assertIn(foil, caption)
                self.assertIn(foil, alt)
                self.assertIn(f"https://go.m4s.eu/{alias}", caption)
                self.assertNotIn("[short link missing]", caption)
                # the account is English; a localized name joins Snorlax and never replaces it
                self.assertIn("(Snorlax)", caption)
                self.assertIn("Chinese (Simplified)", caption)
                self.assertTrue(alt.startswith("Own photo of "))

    def test_mirror_patterns_name_themselves(self):
        # Japanese m2a 136: the two mirror cards differ only by their pattern
        model = load()
        for sid, foil in (("SPEC-1124", "Poké Ball pattern"), ("SPEC-1120", "Colorless Energy pattern")):
            with self.subTest(specimen=sid):
                _, item = owner_specimen(model, sid)
                caption, alt = post_copy(model, item, "https://go.m4s.eu/sdtest")
                self.assertIn(foil, caption)
                self.assertIn(foil, alt)

    def test_hashtags_close_the_caption(self):
        model = load()
        cases = [("SPEC-1114", "#Snorlax #PokemonTCG #PokemonCards #GymHeroes"),
                 ("SPEC-1113", "#Snorlax #PokemonTCG #PokemonCards #Relaxo #RisingRivals"),
                 ("SPEC-1120", "#Snorlax #PokemonTCG #PokemonCards #カビゴン #MEGADreamEx")]
        for sid, line in cases:
            with self.subTest(specimen=sid):
                _, item = owner_specimen(model, sid)
                caption, alt = post_copy(model, item, "https://go.m4s.eu/sdtest")
                self.assertEqual(caption.rstrip("\n").splitlines()[-1], line)
                self.assertNotIn("#", alt)
        # Instagram refuses more than five; every printing stays within it, without repeats or spaces
        for item in model["printings"]["printings"]:
            caption, _ = post_copy(model, item, None)
            tags = caption.rstrip("\n").splitlines()[-1].split(" ")
            self.assertTrue(3 <= len(tags) <= 5 and len(set(tags)) == len(tags), (item["itemId"], tags))
            self.assertTrue(all(re.fullmatch(r"#[^\s#$%&.,!?'()<>·-]+", tag) for tag in tags), tags)

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

    def test_dark_cover_keeps_the_card_and_marks_the_corner(self):
        # a light wall with a yellow card standing in it, as photographed on its stand
        photo = Image.new("RGB", (3000, 4000), (225, 225, 220))
        ImageDraw.Draw(photo).rounded_rectangle((700, 800, 2300, 3040), radius=70, fill=(230, 210, 40))
        raw = BytesIO()
        photo.save(raw, "PNG")
        corners = [(700, 800), (2300, 800), (2300, 3040), (700, 3040)]
        data, geometry = post_image(raw.getvalue(), corners)
        left, top, right, bottom = geometry["frame"]
        self.assertAlmostEqual(1600 / (right - left), 0.6, places=2)
        self.assertEqual((right - left) * 5, (bottom - top) * 4)
        with Image.open(BytesIO(data)) as draft:
            scale = 1080 / (right - left)
            def at(x, y):
                return draft.getpixel((round((x - geometry["frame"][0]) * scale),
                                       round((y - geometry["frame"][1]) * scale)))
            self.assertGreater(at(1500, 1900)[0], 215, "the card stays as photographed")
            self.assertLess(at(400, 600)[0], 70, "the wall is darkened")
            self.assertLess(at(712, 812)[0], 70, "outside the rounded corner is wall")
            mark = draft.crop((780, 1280, 1050, 1330)).convert("L")
            self.assertGreater(mark.getextrema()[1], 150, "the @SnoreDex watermark is drawn")

    def test_edited_photo_preserves_full_frame_and_records_source(self):
        data = BytesIO()
        exif = Image.Exif()
        exif[315] = "private camera metadata"
        exif[34853] = {1: "N", 2: (1, 2, 3)}
        picture = Image.new("RGB", (1200, 1500), "navy")
        ImageDraw.Draw(picture).rectangle((0, 1300, 1199, 1499), fill="yellow")
        srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
        picture.save(data, "JPEG", exif=exif, xmp=b"<x:xmpmeta>private metadata</x:xmpmeta>",
                     icc_profile=srgb.tobytes())
        feed_bytes = data.getvalue()
        alt = "Snorlax-Karte auf einem Kartenhalter."
        specimen_id = "SPEC-0774"
        model = load()
        original = b"test archive input"
        model["specimens"][specimen_id]["photographSha256"] = f"sha256:{digest(original)}"
        with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            archive = Path(directory)
            photos = archive / "verification/specimens"
            photos.mkdir(parents=True)
            (photos / model["specimens"][specimen_id]["photograph"]).write_bytes(original)
            feed = archive / "feed.jpg"
            feed.write_bytes(feed_bytes)
            files, manifest = package(model, specimen_id, archive, owner_feed_jpeg=feed, feed_alt=alt)
            with self.assertRaisesRegex(ValueError, "Alt-Text"):
                package(model, specimen_id, archive, owner_feed_jpeg=feed)
        self.assertEqual(manifest["specimenId"], specimen_id)
        self.assertEqual(manifest["photoSha256"], f"sha256:{digest(original)}")
        self.assertEqual(manifest["feedPhoto"]["sha256"], f"sha256:{digest(feed_bytes)}")
        self.assertEqual(manifest["files"]["post.jpg"], digest(files["post.jpg"]))
        self.assertEqual(files["alt-text.txt"].decode(), alt + "\n")
        self.assertIn("Owner review", manifest["requiredBeforePosting"])
        self.assertIn(b"https://go.m4s.eu/sdbbea2621c8f4", files["caption-draft.txt"])
        with Image.open(BytesIO(files["post.jpg"])) as draft:
            self.assertEqual(draft.size, (1080, 1350))
            self.assertGreater(draft.getpixel((10, 10))[2], 110)
            self.assertGreater(draft.getpixel((1070, 1340))[0], 230)
            self.assertFalse(draft.getexif())
            self.assertNotIn("xmp", draft.info)
            self.assertNotIn("icc_profile", draft.info)

    def test_feed_rejects_wrong_format(self):
        data = BytesIO()
        Image.new("RGB", (800, 1000)).save(data, "PNG")
        with self.assertRaisesRegex(ValueError, "JPEG"):
            edited_post_image(data.getvalue())


if __name__ == "__main__":
    unittest.main()
