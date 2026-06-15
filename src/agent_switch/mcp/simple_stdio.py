from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


Handler = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Handler

    def to_mcp(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class StdioMCPServer:
    def __init__(self, *, name: str, version: str, tools: list[Tool]) -> None:
        self.name = name
        self.version = version
        self.tools = {tool.name: tool for tool in tools}

    def run(self) -> int:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self._handle(request)
            except Exception as exc:  # pragma: no cover - defensive stdio boundary
                response = self._error(None, -32603, f"Internal error: {exc}")
            if response is not None:
                self._write(response)
        return 0

    def _handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")

        if request_id is None:
            return None

        if method == "initialize":
            return self._result(
                request_id,
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": self.name, "version": self.version},
                },
            )
        if method == "ping":
            return self._result(request_id, {})
        if method == "tools/list":
            return self._result(request_id, {"tools": [tool.to_mcp() for tool in self.tools.values()]})
        if method == "tools/call":
            return self._call_tool(request_id, request.get("params") or {})

        return self._error(request_id, -32601, f"Method not found: {method}")

    def _call_tool(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        tool = self.tools.get(name)
        if tool is None:
            return self._error(request_id, -32602, f"Unknown tool: {name}")
        try:
            text = tool.handler(arguments)
            return self._result(request_id, {"content": [{"type": "text", "text": text}]})
        except Exception as exc:
            return self._result(
                request_id,
                {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            )

    @staticmethod
    def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    @staticmethod
    def _write(message: dict[str, Any]) -> None:
        sys.stdout.write(json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n")
        sys.stdout.flush()
