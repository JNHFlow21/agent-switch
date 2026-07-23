from __future__ import annotations

import contextlib
import io
import os
import pty
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_switch.cli import _duplicate_secret_output_fd, _read_secret_stream, _write_all, main
from agent_switch.security.secrets import MAX_SECRET_BYTES, set_secret


ROOT = Path(__file__).resolve().parents[1]


def run_cli(
    args: list[str],
    *,
    input_data: bytes | None = None,
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    source_path = str(ROOT / "src")
    env["PYTHONPATH"] = source_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return subprocess.run(
        [sys.executable, "-m", "agent_switch", *args],
        cwd=ROOT,
        env=env,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=pass_fds,
        check=False,
    )


class TtyBytesIO(io.BytesIO):
    def isatty(self) -> bool:
        return True


def read_all(fd: int) -> bytes:
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 4096)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


class CliTests(unittest.TestCase):
    def test_doctor_json_runs_against_fixture_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "--home",
                        str(Path(tmp) / "agent"),
                        "--user-home",
                        str(Path(tmp) / "user"),
                        "doctor",
                        "--json",
                        "--no-ccswitch",
                    ]
                )
            self.assertEqual(code, 0)

    def test_doctor_strict_fails_for_drift_or_missing_required_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            common = ["--home", str(root / "agent"), "--user-home", str(root / "user")]
            clean = run_cli([*common, "doctor", "--strict", "--no-ccswitch"])
            self.assertEqual(clean.returncode, 0, clean.stderr.decode(errors="replace"))

            added = run_cli(
                [
                    *common,
                    "mcp",
                    "add",
                    "strict-demo",
                    "--command",
                    "demo",
                    "--secret",
                    "STRICT_API_KEY",
                ]
            )
            self.assertEqual(added.returncode, 0, added.stderr.decode(errors="replace"))
            missing = run_cli([*common, "doctor", "--strict", "--no-ccswitch"])
            self.assertEqual(missing.returncode, 1)
            self.assertIn(b"STRICT_API_KEY", missing.stdout)

    def test_agents_json_reports_supported_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cli(
                [
                    "--home",
                    str(Path(tmp) / "agent"),
                    "--user-home",
                    str(Path(tmp) / "user"),
                    "agents",
                    "--json",
                ]
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
            payload = __import__("json").loads(result.stdout)
            self.assertEqual([item["id"] for item in payload["agents"]], ["codex", "claude", "hermes"])

    def test_clis_json_reports_curated_inventory(self) -> None:
        result = run_cli(["clis", "--json"])
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        payload = __import__("json").loads(result.stdout)
        self.assertIn("codex", [item["id"] for item in payload["clis"]])

    def test_skills_json_uses_configured_skill_hub(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp) / "hub"
            (hub / "config").mkdir(parents=True)
            (hub / "profiles").mkdir()
            (hub / "config" / "registry.json").write_text('{"sources": {}}')
            previous = os.environ.get("SKILL_HUB_HOME")
            os.environ["SKILL_HUB_HOME"] = str(hub)
            try:
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = main(["skills", "--json"])
            finally:
                if previous is None:
                    os.environ.pop("SKILL_HUB_HOME", None)
                else:
                    os.environ["SKILL_HUB_HOME"] = previous
            self.assertEqual(code, 0)
            self.assertEqual(__import__("json").loads(stdout.getvalue())["hubPath"], str(hub.resolve()))

    def test_preview_json_classifies_mcp(self) -> None:
        import base64
        import json

        payload = {"mcpServers": {"xcrawl": {"command": "node", "env": {"XCRAWL_API_KEY": "fixture-value"}}}}
        config = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(["preview", f"ccswitch://v1/import?resource=mcp&config={config}", "--json"])
        self.assertEqual(code, 0)

    def test_secret_stdin_and_list_do_not_print_value(self) -> None:
        fixture_value = b"fixture-stdin-value"
        with tempfile.TemporaryDirectory() as tmp:
            agent_home = Path(tmp) / "agent"
            agent_home.mkdir(mode=0o755)
            args = [
                "--home",
                str(agent_home),
                "--user-home",
                str(Path(tmp) / "user"),
                "secret",
                "set",
                "--stdin",
                "EXAMPLE_API_KEY",
            ]
            result = run_cli(args, input_data=fixture_value + b"\r\n")
            combined = result.stdout + result.stderr

            self.assertEqual(result.returncode, 0, combined.decode(errors="replace"))
            self.assertNotIn(fixture_value, combined)
            self.assertNotIn(b"deprecated", result.stderr)
            secret_file = agent_home / "secrets.env"
            self.assertEqual(secret_file.read_bytes(), b"EXAMPLE_API_KEY=" + fixture_value + b"\n")
            self.assertEqual(stat.S_IMODE(agent_home.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(secret_file.stat().st_mode), 0o600)

            listed = run_cli([*args[:4], "secret", "list"])
            self.assertEqual(listed.returncode, 0)
            self.assertEqual(listed.stdout.strip(), b"EXAMPLE_API_KEY")
            self.assertNotIn(fixture_value, listed.stdout + listed.stderr)

    def test_secret_delete_removes_name_without_printing_value(self) -> None:
        fixture_value = b"fixture-delete-value"
        with tempfile.TemporaryDirectory() as tmp:
            common = ["--home", str(Path(tmp) / "agent"), "--user-home", str(Path(tmp) / "user")]
            created = run_cli([*common, "secret", "set", "--stdin", "DELETE_API_KEY"], input_data=fixture_value)
            self.assertEqual(created.returncode, 0)

            deleted = run_cli([*common, "secret", "delete", "DELETE_API_KEY"])
            self.assertEqual(deleted.returncode, 0, deleted.stderr.decode(errors="replace"))
            self.assertIn(b"DELETE_API_KEY", deleted.stdout)
            self.assertNotIn(fixture_value, deleted.stdout + deleted.stderr)
            self.assertNotIn("DELETE_API_KEY", (Path(tmp) / "agent" / "secrets.env").read_text())

            missing = run_cli([*common, "secret", "delete", "DELETE_API_KEY"])
            self.assertEqual(missing.returncode, 2)
            self.assertNotIn(fixture_value, missing.stdout + missing.stderr)

    def test_secret_fd_reads_inherited_descriptor_without_printing_value(self) -> None:
        fixture_value = b"fixture-fd-value"
        with tempfile.TemporaryDirectory() as tmp:
            read_fd, write_fd = os.pipe()
            try:
                os.write(write_fd, fixture_value + b"\n")
            finally:
                os.close(write_fd)
            try:
                result = run_cli(
                    [
                        "--home",
                        str(Path(tmp) / "agent"),
                        "--user-home",
                        str(Path(tmp) / "user"),
                        "secret",
                        "set",
                        "--fd",
                        str(read_fd),
                        "FD_API_KEY",
                    ],
                    pass_fds=(read_fd,),
                )
            finally:
                os.close(read_fd)

            combined = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, combined.decode(errors="replace"))
            self.assertNotIn(fixture_value, combined)
            self.assertEqual((Path(tmp) / "agent" / "secrets.env").read_bytes(), b"FD_API_KEY=" + fixture_value + b"\n")

    def test_positional_secret_value_is_rejected_without_leaking_value(self) -> None:
        fixture_value = "fixture-legacy-value"
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "--home",
                        str(Path(tmp) / "agent"),
                        "--user-home",
                        str(Path(tmp) / "user"),
                        "secret",
                        "set",
                        "LEGACY_API_KEY",
                        fixture_value,
                    ]
                )
            combined = stdout.getvalue() + stderr.getvalue()
            self.assertEqual(code, 2)
            self.assertIn("not supported", stderr.getvalue())
            self.assertNotIn(fixture_value, combined)

    def test_secret_source_must_be_exactly_one(self) -> None:
        fixture_value = "fixture-conflict-value"
        with tempfile.TemporaryDirectory() as tmp:
            common = ["--home", str(Path(tmp) / "agent"), "--user-home", str(Path(tmp) / "user"), "secret", "set"]
            cases = (
                (["NO_SOURCE_KEY"], "exactly one secret source"),
                (["--stdin", "CONFLICT_KEY", fixture_value], "positional secret values are not supported"),
            )
            for suffix, expected in cases:
                with self.subTest(suffix=suffix):
                    stdout = io.StringIO()
                    stderr = io.StringIO()
                    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                        code = main([*common, *suffix])
                    combined = stdout.getvalue() + stderr.getvalue()
                    self.assertEqual(code, 2)
                    self.assertIn(expected, stderr.getvalue())
                    self.assertNotIn(fixture_value, combined)

    def test_secret_stdin_rejects_invalid_inputs_without_echoing_them(self) -> None:
        cases = {
            "empty": (b"", None),
            "nul": (b"fixture-nul\x00value", b"fixture-nul"),
            "multiline": (b"fixture-line-one\nfixture-line-two", b"fixture-line-one"),
            "invalid-utf8": (b"\xfffixture-invalid", b"fixture-invalid"),
            "oversize": (b"fixture-oversize-" + b"x" * MAX_SECRET_BYTES, b"fixture-oversize"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            for label, (input_data, leak_marker) in cases.items():
                with self.subTest(label=label):
                    agent_home = Path(tmp) / label
                    result = run_cli(
                        [
                            "--home",
                            str(agent_home),
                            "--user-home",
                            str(Path(tmp) / "user"),
                            "secret",
                            "set",
                            "--stdin",
                            "REJECTED_API_KEY",
                        ],
                        input_data=input_data,
                    )
                    combined = result.stdout + result.stderr
                    self.assertEqual(result.returncode, 2, combined.decode(errors="replace"))
                    self.assertLess(len(combined), 1024)
                    if leak_marker is not None:
                        self.assertNotIn(leak_marker, combined)
                    self.assertFalse((agent_home / "secrets.env").exists())

    def test_secret_stdin_accepts_exact_64_kib_boundary(self) -> None:
        fixture_value = b"x" * MAX_SECRET_BYTES
        with tempfile.TemporaryDirectory() as tmp:
            agent_home = Path(tmp) / "agent"
            result = run_cli(
                ["--home", str(agent_home), "--user-home", str(Path(tmp) / "user"), "secret", "set", "--stdin", "MAX_API_KEY"],
                input_data=fixture_value + b"\n",
            )
            combined = result.stdout + result.stderr
            self.assertEqual(result.returncode, 0, combined.decode(errors="replace"))
            self.assertNotIn(fixture_value[:32], combined)
            self.assertEqual((agent_home / "secrets.env").stat().st_size, MAX_SECRET_BYTES + len("MAX_API_KEY=\n"))

    def test_secret_input_rejects_tty_and_standard_descriptors(self) -> None:
        with self.assertRaisesRegex(ValueError, "TTY"):
            _read_secret_stream(TtyBytesIO(b"fixture-tty-value"), "stdin")

        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = main(
                    [
                        "--home",
                        str(Path(tmp) / "agent"),
                        "--user-home",
                        str(Path(tmp) / "user"),
                        "secret",
                        "set",
                        "--fd",
                        "0",
                        "FD_ZERO_KEY",
                    ]
                )
            self.assertEqual(code, 2)
            self.assertIn("3 or higher", stderr.getvalue())

    def test_secret_get_writes_only_inherited_fd_and_round_trips_special_characters(self) -> None:
        fixture_value = 'fixture space\\unknown "$HOME" `command` single\'quote'
        with tempfile.TemporaryDirectory() as tmp:
            agent_home = Path(tmp) / "agent"
            set_secret(agent_home / "secrets.env", "GET_API_KEY", fixture_value)
            read_fd, write_fd = os.pipe()
            try:
                result = run_cli(
                    [
                        "--home",
                        str(agent_home),
                        "--user-home",
                        str(Path(tmp) / "user"),
                        "secret",
                        "get",
                        "--fd",
                        str(write_fd),
                        "GET_API_KEY",
                    ],
                    pass_fds=(write_fd,),
                )
            finally:
                os.close(write_fd)
            try:
                output = read_all(read_fd)
            finally:
                os.close(read_fd)

            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
            self.assertEqual(result.stdout, b"")
            self.assertEqual(result.stderr, b"")
            self.assertEqual(output, fixture_value.encode("utf-8"))

    def test_secret_get_rejects_missing_invalid_fd_and_tty_without_leaking(self) -> None:
        fixture_value = b"fixture-get-never-output"
        with tempfile.TemporaryDirectory() as tmp:
            agent_home = Path(tmp) / "agent"
            set_secret(agent_home / "secrets.env", "PRESENT_API_KEY", fixture_value.decode())

            for name in ("MISSING_API_KEY", "invalid-name"):
                with self.subTest(name=name):
                    read_fd, write_fd = os.pipe()
                    try:
                        result = run_cli(
                            [
                                "--home",
                                str(agent_home),
                                "--user-home",
                                str(Path(tmp) / "user"),
                                "secret",
                                "get",
                                "--fd",
                                str(write_fd),
                                name,
                            ],
                            pass_fds=(write_fd,),
                        )
                    finally:
                        os.close(write_fd)
                    try:
                        self.assertEqual(read_all(read_fd), b"")
                    finally:
                        os.close(read_fd)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, b"")
                    self.assertNotIn(fixture_value, result.stderr)

            for fd in (1, 2, 9999):
                with self.subTest(fd=fd):
                    result = run_cli(
                        [
                            "--home",
                            str(agent_home),
                            "--user-home",
                            str(Path(tmp) / "user"),
                            "secret",
                            "get",
                            "--fd",
                            str(fd),
                            "PRESENT_API_KEY",
                        ]
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, b"")
                    self.assertNotIn(fixture_value, result.stderr)

            common = ["--home", str(agent_home), "--user-home", str(Path(tmp) / "user"), "secret", "get"]
            for suffix in (["PRESENT_API_KEY"], ["--fd", "3"]):
                with self.subTest(missing_argument=suffix):
                    result = run_cli([*common, *suffix])
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, b"")
                    self.assertNotIn(fixture_value, result.stderr)

            master_fd, tty_fd = pty.openpty()
            try:
                result = run_cli(
                    [
                        "--home",
                        str(agent_home),
                        "--user-home",
                        str(Path(tmp) / "user"),
                        "secret",
                        "get",
                        "--fd",
                        str(tty_fd),
                        "PRESENT_API_KEY",
                    ],
                    pass_fds=(tty_fd,),
                )
            finally:
                os.close(tty_fd)
                os.close(master_fd)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"TTY", result.stderr)
            self.assertNotIn(fixture_value, result.stderr)

    def test_secret_get_rejects_stdout_alias_and_handles_short_writes(self) -> None:
        alias_fd = os.dup(1)
        try:
            with self.assertRaisesRegex(ValueError, "stdout or stderr"):
                _duplicate_secret_output_fd(alias_fd)
        finally:
            os.close(alias_fd)

        fixture_value = b"fixture-short-write-value"
        written: list[bytes] = []

        def short_write(_fd: int, data: bytes | memoryview) -> int:
            chunk = bytes(data[:3])
            written.append(chunk)
            return len(chunk)

        with patch("agent_switch.cli.os.write", side_effect=short_write) as write_mock:
            _write_all(123, fixture_value)
        self.assertGreater(write_mock.call_count, 1)
        self.assertEqual(b"".join(written), fixture_value)


if __name__ == "__main__":
    unittest.main()
