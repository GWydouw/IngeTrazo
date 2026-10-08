"""Exercise publication boundaries with real isolated Git histories."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "pre_push_guard.py"
PUBLIC = "https://github.com/GWydouw/IngeTrazo.git"
PRIVATE = "git@github.com:GWydouw/SiteRef-IngeTrazo.git"


class PushGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")
        self.commit_file("public.txt")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def commit_file(self, path):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("test\n")
        self.git("add", path)
        self.git("commit", "-qm", "test")

    def push(self, destination=PUBLIC, ref="refs/heads/ordinary", sha=None):
        sha = sha or self.git("rev-parse", "HEAD")
        return subprocess.run(["python3", str(SCRIPT), "test", destination],
                              cwd=self.root, input=f"{ref} {sha} {ref} {'0' * 40}\n",
                              capture_output=True, text=True)

    def test_public_history_allowed(self):
        self.assertEqual(self.push().returncode, 0)

    def test_private_history_blocked_even_after_deletion(self):
        self.commit_file("poc/siteref/private.py")
        self.git("rm", "poc/siteref/private.py")
        self.git("commit", "-qm", "remove")
        self.assertNotEqual(self.push().returncode, 0)

    def test_private_history_allowed_only_on_private_repository(self):
        self.commit_file(".siteref-private")
        self.assertEqual(self.push(PRIVATE).returncode, 0)
        self.assertNotEqual(self.push(PRIVATE + "-other").returncode, 0)

    def test_private_branch_name_blocked_without_private_files(self):
        self.assertNotEqual(self.push(ref="refs/heads/codex/siteref-for-it").returncode, 0)

    def test_private_profile_blocked(self):
        self.commit_file("products/siteref-for-it.json")
        self.assertNotEqual(self.push().returncode, 0)

    def test_annotated_tag_does_not_hide_private_history(self):
        self.commit_file("siteref/cloud.py")
        self.git("tag", "-a", "release", "-m", "release")
        self.assertNotEqual(self.push(ref="refs/tags/release",
                                     sha=self.git("rev-parse", "release")).returncode, 0)

    def test_official_direct_push_blocked(self):
        self.assertNotEqual(self.push("https://github.com/ingelibre/ingetrazo.git").returncode, 0)

    def test_deletion_allowed(self):
        self.assertEqual(self.push(sha="0" * 40).returncode, 0)

    def test_unknown_object_fails_closed(self):
        self.assertNotEqual(self.push(sha="a" * 40).returncode, 0)


if __name__ == "__main__":
    unittest.main()
