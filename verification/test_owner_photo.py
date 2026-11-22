"""The Instagram selection must reach one exact, owned archive photo."""
import copy
from hashlib import sha256
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check import load
from owner_photo import owner_specimen, verified_owner_photo


class OwnerPhotoTests(unittest.TestCase):
    def test_pilot_printings_and_unapproved_sources(self):
        model = load()
        for key, expected in (
            ("SPEC-0774", "item-bbea2621-c8f4-5647-b576-e309aa29d24a"),
            ("SPEC-0779", "item-b26a638d-ed89-538b-ab49-a5c879572f60"),
            ("SPEC-0780", "item-a2f8335e-94ff-54d2-8b10-5bdf55349451"),
        ):
            with self.subTest(specimen=key):
                self.assertEqual(owner_specimen(model, key)[1]["itemId"], expected)
        for key in ("SPEC-0641", "SPEC-0489"):
            with self.assertRaisesRegex(ValueError, "no documented"):
                owner_specimen(model, key)

    def test_wrong_bytes_and_multiple_matches(self):
        model = load()
        specimen, item = owner_specimen(model, "SPEC-0774")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "verification/specimens" / specimen["photograph"]
            path.parent.mkdir(parents=True)
            content = b"synthetic archive fixture"
            path.write_bytes(content)
            with self.assertRaisesRegex(ValueError, "does not match"):
                verified_owner_photo(model, "SPEC-0774", root)
            model = copy.deepcopy(model)
            model["specimens"]["SPEC-0774"]["photographSha256"] = "sha256:" + sha256(content).hexdigest()
            self.assertEqual(verified_owner_photo(model, "SPEC-0774", root)[2], content)
        model["printings"]["printings"].append(dict(item, itemId="another-printing"))
        with self.assertRaisesRegex(ValueError, "found 2"):
            owner_specimen(model, "SPEC-0774")


if __name__ == "__main__":
    unittest.main()
