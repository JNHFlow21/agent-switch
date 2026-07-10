from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_switch.security.secrets import _secret_lock, read_env_file, set_secret


ROOT = Path(__file__).resolve().parents[1]


class SecretStorageTests(unittest.TestCase):
    def test_secret_write_is_atomic_fsynced_and_private(self) -> None:
        fixture_value = "fixture-atomic-value"
        real_fsync = os.fsync
        real_replace = os.replace
        observed: dict[str, object] = {}

        def checked_replace(source: str, target: str) -> None:
            source_path = Path(source)
            observed["source_parent"] = source_path.parent
            observed["source_mode"] = stat.S_IMODE(source_path.stat().st_mode)
            observed["target"] = Path(target)
            real_replace(source, target)

        with tempfile.TemporaryDirectory() as tmp:
            secret_dir = Path(tmp) / "agent"
            secret_dir.mkdir(mode=0o755)
            secret_file = secret_dir / "secrets.env"
            with patch("agent_switch.atomic.os.fsync", side_effect=real_fsync) as fsync_mock:
                with patch("agent_switch.atomic.os.replace", side_effect=checked_replace) as replace_mock:
                    set_secret(secret_file, "ATOMIC_API_KEY", fixture_value)

            self.assertTrue(fsync_mock.called)
            self.assertEqual(replace_mock.call_count, 1)
            self.assertEqual(observed["source_parent"], secret_dir)
            self.assertEqual(observed["source_mode"], 0o600)
            self.assertEqual(observed["target"], secret_file)
            self.assertEqual(stat.S_IMODE(secret_dir.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(secret_file.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE((secret_dir / ".secrets.env.lock").stat().st_mode), 0o600)

            secret_file.chmod(0o644)
            set_secret(secret_file, "ATOMIC_API_KEY", fixture_value)
            self.assertEqual(stat.S_IMODE(secret_file.stat().st_mode), 0o600)

    def test_permission_failure_is_not_silently_ignored(self) -> None:
        fixture_value = "fixture-permission-value"
        with tempfile.TemporaryDirectory() as tmp:
            secret_file = Path(tmp) / "agent" / "secrets.env"
            with patch.object(Path, "chmod", side_effect=PermissionError("fixture permission denied")):
                with self.assertRaises(PermissionError) as raised:
                    set_secret(secret_file, "PERMISSION_API_KEY", fixture_value)
            self.assertNotIn(fixture_value, str(raised.exception))

    def test_set_secret_honors_interprocess_lock_and_preserves_existing_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            secret_file = Path(tmp) / "agent" / "secrets.env"
            set_secret(secret_file, "FIRST_API_KEY", "fixture-first-value")

            env = os.environ.copy()
            source_path = str(ROOT / "src")
            env["PYTHONPATH"] = source_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            script = (
                "import sys\n"
                "from agent_switch.security.secrets import set_secret\n"
                "print('READY', flush=True)\n"
                "set_secret(sys.argv[1], 'SECOND_API_KEY', 'fixture-second-value')\n"
                "print('DONE', flush=True)\n"
            )

            with _secret_lock(secret_file):
                child = subprocess.Popen(
                    [sys.executable, "-c", script, str(secret_file)],
                    cwd=ROOT,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                assert child.stdout is not None
                self.assertEqual(child.stdout.readline().strip(), "READY")
                time.sleep(0.1)
                self.assertIsNone(child.poll(), "child bypassed the secret-file lock")

            stdout, stderr = child.communicate(timeout=5)
            self.assertEqual(child.returncode, 0, stderr)
            self.assertEqual(stdout.strip(), "DONE")
            values = read_env_file(secret_file)
            self.assertEqual(set(values), {"FIRST_API_KEY", "SECOND_API_KEY"})


if __name__ == "__main__":
    unittest.main()
