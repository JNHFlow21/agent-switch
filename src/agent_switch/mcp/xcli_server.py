from __future__ import annotations

import subprocess
from typing import Any

from agent_switch.mcp.simple_stdio import StdioMCPServer, Tool


def _run_xcli(args: list[str], *, timeout: int = 30) -> str:
    result = subprocess.run(
        ["x-cli-auth", "-j", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or f"x-cli-auth exited with code {result.returncode}")
    return result.stdout.strip()


def _tweet_get(args: dict[str, Any]) -> str:
    url_or_id = str(args.get("url_or_id") or "").strip()
    if not url_or_id:
        raise ValueError("url_or_id is required")
    return _run_xcli(["tweet", "get", url_or_id])


def _tweet_search(args: dict[str, Any]) -> str:
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    max_results = int(args.get("max") or 10)
    max_results = max(1, min(max_results, 20))
    return _run_xcli(["tweet", "search", query, "--max", str(max_results)], timeout=45)


def _user_get(args: dict[str, Any]) -> str:
    username = str(args.get("username") or "").strip().lstrip("@")
    if not username:
        raise ValueError("username is required")
    return _run_xcli(["user", "get", username])


def build_server() -> StdioMCPServer:
    string_arg = {"type": "string"}
    return StdioMCPServer(
        name="agent-xurl-fallback",
        version="0.1.3",
        tools=[
            Tool(
                name="x_api_get_post",
                description="Fetch an X/Twitter post through the official X API wrapper.",
                input_schema={
                    "type": "object",
                    "properties": {"url_or_id": string_arg},
                    "required": ["url_or_id"],
                },
                handler=_tweet_get,
            ),
            Tool(
                name="x_api_search_posts",
                description="Search X/Twitter through the official X API wrapper.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": string_arg,
                        "max": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                    },
                    "required": ["query"],
                },
                handler=_tweet_search,
            ),
            Tool(
                name="x_api_get_user",
                description="Fetch an X/Twitter user through the official X API wrapper.",
                input_schema={
                    "type": "object",
                    "properties": {"username": string_arg},
                    "required": ["username"],
                },
                handler=_user_get,
            ),
        ],
    )


def main() -> int:
    return build_server().run()


if __name__ == "__main__":
    raise SystemExit(main())
