"""Build-profile readiness and public/private checkout boundaries."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "product_profile.py"
spec = importlib.util.spec_from_file_location("product_profile", SCRIPT)
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


class ProductProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "products").mkdir()
        (self.root / "main.py").touch()
        (self.root / "app.spec").touch()
        self.data = {"id": "mijn-it", "name": "mijn iT", "visibility": "public",
                     "entrypoint": "main.py", "packaging": "app.spec",
                     "source_ready": True, "packaging_ready": True, "notes": "Test"}

    def write(self):
        (self.root / "products" / f"{self.data['id']}.json").write_text(json.dumps(self.data))

    def test_existing_public_profile_ready(self):
        self.write()
        self.assertTrue(profile.inspect_profile(self.root, "mijn-it", True)["source_ready"])

    def test_public_profile_refused_in_private_checkout(self):
        self.write()
        (self.root / ".siteref-private").touch()
        with self.assertRaisesRegex(ValueError, "public checkout"):
            profile.inspect_profile(self.root, "mijn-it", True)

    def test_missing_entrypoint_cannot_claim_ready(self):
        self.write()
        (self.root / "main.py").unlink()
        with self.assertRaisesRegex(ValueError, "Missing entrypoint"):
            profile.inspect_profile(self.root, "mijn-it", True)

    def test_incomplete_private_product_is_reportable_but_not_buildable(self):
        self.data.update(id="siteref-for-it", name="SiteRef for iT", visibility="private",
                         source_ready=False, packaging_ready=False, packaging=None)
        self.write()
        (self.root / ".siteref-private").touch()
        self.assertFalse(profile.inspect_profile(self.root, "siteref-for-it")["source_ready"])
        with self.assertRaisesRegex(ValueError, "not ready"):
            profile.inspect_profile(self.root, "siteref-for-it", True)

    def test_entrypoint_cannot_escape_checkout(self):
        self.data["entrypoint"] = "../main.py"
        self.write()
        with self.assertRaisesRegex(ValueError, "inside"):
            profile.inspect_profile(self.root, "mijn-it")


if __name__ == "__main__":
    unittest.main()
