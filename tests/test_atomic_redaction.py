from __future__ import annotations

import tempfile
import unittest
import stat
from pathlib import Path

from agent_switch.atomic import write_if_changed
from agent_switch.security.redaction import redact_mapping, redact_text


class AtomicAndRedactionTests(unittest.TestCase):
    def test_write_if_changed_is_atomic_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "config.json"
            backups = Path(tmp) / "backups"
            first = write_if_changed(target, "one", backup_dir=backups)
            second = write_if_changed(target, "one", backup_dir=backups)
            third = write_if_changed(target, "two", backup_dir=backups)

            self.assertTrue(first.changed)
            self.assertFalse(second.changed)
            self.assertTrue(third.changed)
            self.assertEqual(target.read_text(), "two")
            self.assertIsNotNone(third.backup_path)
            self.assertEqual(third.backup_path.read_text(), "one")
            self.assertIn("7692c3ad3540", third.backup_path.name)
            self.assertEqual(stat.S_IMODE(backups.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(third.backup_path.stat().st_mode), 0o600)

    def test_backup_name_distinguishes_same_named_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            backups = root / "backups"
            left = root / "one" / "config.json"
            right = root / "two" / "config.json"
            for path in (left, right):
                path.parent.mkdir()
                path.write_text("same\n")
            first = write_if_changed(left, "left\n", backup_dir=backups)
            second = write_if_changed(right, "right\n", backup_dir=backups)
            self.assertNotEqual(first.backup_path, second.backup_path)

    def test_redacts_secret_shapes_without_removing_names(self) -> None:
        text = "provider tavily API_KEY=sk-aaaaaaaa token=xai-bbbbbbbb"
        redacted = redact_text(text)
        self.assertIn("provider tavily", redacted)
        self.assertNotIn("sk-aaaaaaaa", redacted)
        self.assertNotIn("xai-bbbbbbbb", redacted)

    def test_redacts_secret_mapping_values(self) -> None:
        result = redact_mapping({"apiKey": "sk-aaaaaaaa", "provider": "xcrawl"})
        self.assertEqual(result["apiKey"], "[REDACTED]")
        self.assertEqual(result["provider"], "xcrawl")


if __name__ == "__main__":
    unittest.main()
