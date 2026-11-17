
#!/usr/bin/env python3
"""Regression tests for gallery identity, replay and native crop geometry."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from gallery_apply import face_width, merge, validate_targets
from gallery_prepare import coefficients
from gallery_workflow import confirmed_associations, local_path


class GalleryWorkflowTests(unittest.TestCase):
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
