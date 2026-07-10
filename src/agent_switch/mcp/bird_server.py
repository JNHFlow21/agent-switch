from __future__ import annotations

import json
import subprocess
from typing import Any

from agent_switch.mcp.simple_stdio import StdioMCPServer, Tool


def _run_bird(args: list[str], *, timeout: int = 30) -> str:
    result = subprocess.run(
        ["bird", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"bird exited with code {result.returncode}")
    return result.stdout.strip()


def _read(args: dict[str, Any]) -> str:
    url_or_id = str(args.get("url_or_id") or "").strip()
    if not url_or_id:
        raise ValueError("url_or_id is required")
    return _run_bird(["read", url_or_id, "--json"])


def _thread(args: dict[str, Any]) -> str:
    url_or_id = str(args.get("url_or_id") or "").strip()
    if not url_or_id:
        raise ValueError("url_or_id is required")
    return _run_bird(["thread", url_or_id, "--json"], timeout=45)


def _search(args: dict[str, Any]) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    count = int(args.get("count") or 5)
    count = max(1, min(count, 20))
    return _run_bird(["search", query, "-n", str(count), "--json"], timeout=45)


def _check(_: dict[str, Any]) -> str:
    raw = _run_bird(["check"], timeout=15)
    return json.dumps({"ok": True, "message": raw}, ensure_ascii=False)


def build_server() -> StdioMCPServer:
    string_arg = {"type": "string"}
    return StdioMCPServer(
        name="agent-birdread",
        version="0.1.3",
        tools=[
            Tool(
                name="read_x_post",
                description="Read a single X/Twitter post by URL or status id using the local bird CLI.",
                input_schema={
                    "type": "object",
                    "properties": {"url_or_id": string_arg},
                    "required": ["url_or_id"],
                },
                handler=_read,
            ),
            Tool(
                name="read_x_thread",
                description="Read an X/Twitter conversation thread by URL or status id using the local bird CLI.",
                input_schema={
                    "type": "object",
                    "properties": {"url_or_id": string_arg},
                    "required": ["url_or_id"],
                },
                handler=_thread,
            ),
            Tool(
                name="search_x_posts",
                description="Search X/Twitter posts using the local bird CLI.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": string_arg,
                        "count": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                    },
                    "required": ["query"],
                },
                handler=_search,
            ),
            Tool(
                name="check_x_reader",
                description="Check whether the local bird CLI can access X/Twitter credentials.",
                input_schema={"type": "object", "properties": {}},
                handler=_check,
            ),
        ],
    )


def main() -> int:
    return build_server().run()


if __name__ == "__main__":
    raise SystemExit(main())
