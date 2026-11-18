
#!/usr/bin/env python3
"""Regression tests for gallery identity, replay and native crop geometry."""
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from gallery_apply import face_width, merge, specimen_matches, validate_targets
from gallery_prepare import coefficients
from gallery_workflow import IMAGES, REGISTER, confirmed_associations, local_path, sign_off, verification_basis, write


class GalleryWorkflowTests(unittest.TestCase):
    def test_swsh_printed_number_matches_canonical_specimen(self):
        item = {"setEditionId": "EDITION:WEST:English:SWSH", "collectorNumber": "068",
                "collectorNumberDenominator": None}
        row = {"scope": "exact-printing", "setEditionId": item["setEditionId"], "setCode": "SWSH",
               "number": "SWSH068", "language": "English"}
        specimen = {"number": "068", "language": "English"}
        validate_targets(row, ["a"], {"a": {}}, {"a": item})
        self.assertTrue(specimen_matches(specimen, row))
        self.assertFalse(specimen_matches(specimen, dict(row, setCode="XY")))
        self.assertFalse(specimen_matches(dict(specimen, language="German"), row))
        self.assertFalse(specimen_matches(dict(specimen, number="069"), row))
        row.update(setCode="VIV", number="131/185")
        self.assertTrue(specimen_matches(dict(specimen, number="131"), row))
        self.assertTrue(specimen_matches(dict(specimen, number="131/185"), row))
        self.assertFalse(specimen_matches(dict(specimen, number="131/198"), row))

    def test_signoff_rejects_replaced_jpeg_or_png_preview(self):
        with TemporaryDirectory() as directory, patch("gallery_workflow.git", return_value=b"head"):
            root = Path(directory).resolve()
            for name in ("gallery.html", "index.html", "collector_catalogue.json", "snoredex.sqlite",
                         "snoredex-tracker-template.sqlite", REGISTER, IMAGES):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            previews = ["images/previews/registered.jpg", "images/previews/registered.png"]
            (root / previews[0]).parent.mkdir(parents=True)
            write(root / IMAGES, {"assets": [{"preview": path} for path in previews]})
            for preview in previews:
                (root / preview).write_bytes(b"audited bytes")
            before = verification_basis(root)
            report = root / "audit.json"
            write(report, {"basis": before, "visualAcceptance": "pending"})
            for preview in previews:
                with self.subTest(preview=preview):
                    (root / preview).write_bytes(b"changed bytes")
                    with self.assertRaisesRegex(ValueError, "older state"):
                        sign_off(Namespace(repo=root, report=report))
                    (root / preview).write_bytes(b"audited bytes")
                    self.assertEqual(verification_basis(root), before)

    def test_ready_to_resume_from_canonical_rows_without_receipt(self):
        expected = {"source": "verification/specimens/SPEC-0099.png", "scope": "representative", "mediaKind": "photo"}
        self.assertEqual(confirmed_associations({}, {"card": expected}, {"card": dict(expected)}), {"card"})
        self.assertEqual(confirmed_associations(
            {}, {"card": expected}, {"card": dict(expected, scope="exact-printing")}), set())
        rows = {"card": expected.copy()}
        merge(rows, "card", expected.copy())
        with self.assertRaisesRegex(ValueError, "conflicts"):
            merge(rows, "card", dict(expected, source="another specimen"))
        self.assertEqual(rows, {"card": expected})

    def test_intake_rejects_set_code_in_language_field(self):
        item = {"setEditionId": "EDITION:WEST:English:VIV", "collectorNumber": "131",
                "collectorNumberDenominator": "185", "markings": []}
        targets = {"a": {}, "b": {}}
        items = {"a": item, "b": dict(item, markings=["store stamp"])}
        row = {"scope": "representative", "setEditionId": item["setEditionId"], "setCode": "VIV",
               "number": "131/185", "language": "VIV"}
        with self.assertRaisesRegex(ValueError, "language mismatch"):
            validate_targets(row, ["a"], targets, items)
        row["language"] = "English"
        validate_targets(row, ["a"], targets, items)
        with self.assertRaisesRegex(ValueError, "marks|markings"):
            validate_targets(row, ["a", "b"], targets, items)

    def test_native_crop_width_and_corner_mapping(self):
        points = [(10, 8), (629, 25), (620, 890), (19, 890)]
        stage = {"source": {"nativeDimensions": [640, 900]}, "faceExtraction": {
            "sourceCornersClockwiseTLTRBRBL": points, "outputDimensions": [601, 860]}}
        self.assertEqual(face_width(stage), 601)
        a, b, c, d, e, f, g, h = coefficients(points, (601, 860))
        for (x, y), (u, v) in zip([(0, 0), (600, 0), (600, 859), (0, 859)], points):
            divisor = g*x + h*y + 1
            self.assertAlmostEqual((a*x + b*y + c) / divisor, u)
            self.assertAlmostEqual((d*x + e*y + f) / divisor, v)
        stage["faceExtraction"]["outputDimensions"][0] = 602
        with self.assertRaisesRegex(ValueError, "exceeds"):
            face_width(stage)

    def test_image_path_cannot_escape_allowed_subdirectory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with self.assertRaisesRegex(ValueError, "Unsafe path"):
                local_path(root, "images/gallery/../any.webp", "images/gallery/")


if __name__ == "__main__":
    unittest.main()
