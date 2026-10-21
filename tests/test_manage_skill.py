import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("manage_skill", ROOT / "scripts/manage_skill.py")
manager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manager)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "测试 Codex home"
        self.target = self.home / "skills/auto-continue"

    def snapshot(self):
        return {str(p.relative_to(self.home)): p.read_bytes()
                for p in self.home.rglob("*") if p.is_file()}

    def test_round_trip_preserves_unrelated_skill_and_config(self):
        other = self.home / "skills/other/SKILL.md"
        other.parent.mkdir(parents=True)
        other.write_text("keep", encoding="utf-8")
        (self.home / "config.toml").write_text("# keep", encoding="utf-8")
        before = self.snapshot()
        manager.install(self.home)
        for name in manager.FILES:
            self.assertEqual((self.target / name).read_bytes(), (manager.SOURCE / name).read_bytes())
        manager.uninstall(self.home)
        self.assertEqual(before, self.snapshot())

    def test_second_install_does_not_overwrite(self):
        manager.install(self.home)
        before = self.snapshot()
        with self.assertRaises(manager.InstallError):
            manager.install(self.home)
        self.assertEqual(before, self.snapshot())

    def test_manual_install_is_not_removed(self):
        self.target.mkdir(parents=True)
        (self.target / "SKILL.md").write_text("manual", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(manager.InstallError):
            manager.uninstall(self.home)
        self.assertEqual(before, self.snapshot())

    def test_local_edits_are_not_removed(self):
        manager.install(self.home)
        (self.target / "SKILL.md").write_text("edited", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(manager.InstallError):
            manager.uninstall(self.home)
        self.assertEqual(before, self.snapshot())

    def test_extra_file_is_not_removed(self):
        manager.install(self.home)
        (self.target / "notes.txt").write_text("keep", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(manager.InstallError):
            manager.uninstall(self.home)
        self.assertEqual(before, self.snapshot())

    def test_missing_file_does_not_partially_remove(self):
        manager.install(self.home)
        (self.target / "agents/openai.yaml").unlink()
        before = self.snapshot()
        with self.assertRaises(manager.InstallError):
            manager.uninstall(self.home)
        self.assertEqual(before, self.snapshot())

    def test_bad_receipt_is_not_trusted(self):
        manager.install(self.home)
        (self.target / manager.RECEIPT).write_text("not json", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(manager.InstallError):
            manager.uninstall(self.home)
        self.assertEqual(before, self.snapshot())

    def test_receipt_cannot_select_external_file(self):
        manager.install(self.home)
        receipt_path = self.target / manager.RECEIPT
        receipt = json.loads(receipt_path.read_text())
        receipt["files"]["../../config.toml"] = "abc"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(manager.InstallError):
            manager.uninstall(self.home)
        self.assertEqual(before, self.snapshot())

    def test_wrong_package_receipt_is_refused(self):
        manager.install(self.home)
        receipt_path = self.target / manager.RECEIPT
        receipt = json.loads(receipt_path.read_text())
        receipt["package"] = "another-skill"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaises(manager.InstallError):
            manager.uninstall(self.home)
        self.assertTrue((self.target / "SKILL.md").is_file())

    def test_missing_source_leaves_no_installation(self):
        with self.assertRaises(OSError):
            manager.install(self.home, self.base / "missing")
        self.assertFalse(self.target.exists())

    def test_invalid_source_leaves_no_installation(self):
        source = self.base / "source"
        (source / "agents").mkdir(parents=True)
        (source / "SKILL.md").write_text("invalid", encoding="utf-8")
        (source / "agents/openai.yaml").write_text("interface: {}", encoding="utf-8")
        with self.assertRaises(manager.InstallError):
            manager.install(self.home, source)
        self.assertFalse(self.target.exists())

    def test_symlink_destination_is_refused(self):
        other = self.base / "other"
        other.mkdir()
        (self.home / "skills").mkdir(parents=True)
        try:
            self.target.symlink_to(other, target_is_directory=True)
        except OSError:
            self.skipTest("Creating symlinks requires privileges on this machine")
        with self.assertRaises(manager.InstallError):
            manager.install(self.home)
        with self.assertRaises(manager.InstallError):
            manager.uninstall(self.home)
        self.assertEqual([], list(other.iterdir()))

    def test_failure_rolls_back_only_new_files(self):
        original = Path.open
        def failing_open(path, *args, **kwargs):
            if path == self.target / "agents/openai.yaml" and args and args[0] == "xb":
                raise OSError("simulated disk failure")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", failing_open):
            with self.assertRaises(OSError):
                manager.install(self.home)
        self.assertFalse(self.target.exists())

    def test_cli_honors_explicit_home(self):
        with patch("builtins.print"):
            self.assertEqual(0, manager.main(["install", "--codex-home", str(self.home)]))
            self.assertEqual(1, manager.main(["install", "--codex-home", str(self.home)]))
            self.assertEqual(0, manager.main(["uninstall", "--codex-home", str(self.home)]))


if __name__ == "__main__":
    unittest.main()
