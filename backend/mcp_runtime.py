from __future__ import annotations
import json, os, re, time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler

_PROTOCOL_VERSION = "2025-03-26"
try:
    _TIMEOUT = min(1.5, max(0.8, float(os.getenv("SAARTHI_MCP_TIMEOUT_SECONDS", "1.2"))))
except ValueError:
    _TIMEOUT = 1.2
_CACHE_TTL = 45.0
_cache: dict[str, Any] = {"at": 0.0, "tools": [], "errors": []}

def _servers() -> list[dict[str, Any]]:
    try:
        items = json.loads(os.getenv("SAARTHI_MCP_SERVERS_JSON", "[]"))
    except json.JSONDecodeError:
        return []
    if not isinstance(items, list):
        return []
    result = []
    for item in items[:8]:
        if not isinstance(item, dict) or item.get("enabled", True) is not True:
            continue
        name = re.sub(r"[^a-zA-Z0-9_-]", "_", str(item.get("name") or "remote"))[:40]
        url = str(item.get("url") or "").strip()
        parsed = urlparse(url)
        # Reject malformed URLs and URL components that can change request routing.
        try:
            port = parsed.port
        except ValueError:
            continue
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or port not in (None, 443)
        ):
            continue
        hostname = parsed.hostname.lower().rstrip(".")
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost") or hostname.endswith(".local"):
            continue
        try:
            import ipaddress
            address = ipaddress.ip_address(hostname.strip("[]"))
            if not address.is_global:
                continue
        except ValueError:
            # DNS names are permitted; do not resolve them here to avoid startup DNS calls.
            pass
        allowed = item.get("allowed_tools", [])
        if not isinstance(allowed, list) or not all(isinstance(x, str) for x in allowed):
            continue
        token_env = str(item.get("token_env") or "").strip()
        result.append({"name": name, "url": url, "token": os.getenv(token_env, "") if token_env else "",
                       "token_env": token_env, "allowed_tools": set(allowed),
                       "allow_write": item.get("allow_write") is True})
    return result

def status() -> dict[str, Any]:
    servers = _servers()
    return {"configured": bool(servers), "server_count": len(servers),
            "servers": [{"name": s["name"], "authenticated": bool(s["token"]),
                         "allowlisted_tool_count": len(s["allowed_tools"])} for s in servers],
            "transport": "MCP Streamable HTTP", "self_hosted_servers_required": False,
            "note": "Configure remote endpoints and secret environment variables on the hosted backend."}

def _read_response(response) -> dict[str, Any]:
    body = response.read(1_000_000).decode("utf-8", errors="replace")
    content_type = str(response.headers.get("Content-Type", "")).lower()
    if "text/event-stream" in content_type:
        for line in reversed(body.splitlines()):
            if line.startswith("data:"):
                value = line[5:].strip()
                if value and value != "[DONE]":
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        pass
        raise RuntimeError("MCP endpoint returned no JSON-RPC result")
    parsed = json.loads(body or "{}")
    if not isinstance(parsed, dict):
        raise RuntimeError("MCP endpoint returned invalid JSON-RPC data")
    return parsed

def _post(server: dict[str, Any], payload: dict[str, Any], session_id: str | None = None) -> tuple[dict[str, Any], str | None]:
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": _PROTOCOL_VERSION, "User-Agent": "SAARTHI-MCP-Client/1.0"}
    if server["token"]:
        headers["Authorization"] = "Bearer " + server["token"]
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    from .research import _public_url
    if not _public_url(server["url"]):
        raise ValueError("MCP destination must resolve to a public address")
    request = Request(server["url"], data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None
        with build_opener(NoRedirect()).open(request, timeout=_TIMEOUT) as response:
            result = {} if getattr(response, "status", 200) in (202, 204) else _read_response(response)
            return result, response.headers.get("Mcp-Session-Id") or session_id
    except HTTPError as exc:
        raise RuntimeError(f"MCP HTTP error {exc.code}") from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise RuntimeError("MCP endpoint unavailable or timed out") from None

def _initialize(server: dict[str, Any]) -> str | None:
    response, session_id = _post(server, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": _PROTOCOL_VERSION, "capabilities": {},
                   "clientInfo": {"name": "SAARTHI", "version": "0.5.0"}}})
    if response.get("error"):
        raise RuntimeError("MCP initialization failed")
    _post(server, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, session_id)
    return session_id

def _tools_for_server(server: dict[str, Any]) -> list[dict[str, Any]]:
    session_id = _initialize(server)
    values, seen_cursors, cursor = [], set(), None
    for page in range(8):
        params = {"cursor": cursor} if cursor else {}
        response, session_id = _post(server, {"jsonrpc": "2.0", "id": 2 + page, "method": "tools/list", "params": params}, session_id)
        result = response.get("result")
        if response.get("error") or not isinstance(result, dict) or not isinstance(result.get("tools"), list):
            raise RuntimeError("MCP tools/list failed or returned an invalid catalog")
        values.extend(result["tools"])
        if len(values) > 1000:
            raise RuntimeError("MCP tool catalog exceeds the supported limit")
        cursor = result.get("nextCursor")
        if cursor is None:
            break
        if not isinstance(cursor, str) or not cursor or len(cursor) > 2000 or cursor in seen_cursors:
            raise RuntimeError("MCP tool catalog returned an invalid or repeated cursor")
        seen_cursors.add(cursor)
    else:
        raise RuntimeError("MCP tool catalog exceeds the supported page limit")
    output = []
    seen_names = set()
    for tool in values if isinstance(values, list) else []:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "")
        if not name or name in seen_names:
            raise RuntimeError("MCP tool catalog contains missing or duplicate names")
        seen_names.add(name)
        annotations = tool.get("annotations") if isinstance(tool.get("annotations"), dict) else {}
        approved = name in server["allowed_tools"]
        read_only = annotations.get("readOnlyHint") is True
        safe_to_call = read_only or server["allow_write"]
        public_name = ("mcp__" + re.sub(r"[^a-zA-Z0-9_]", "_", server["name"]) + "__" + re.sub(r"[^a-zA-Z0-9_]", "_", name))[:64]
        schema = tool.get("inputSchema") if isinstance(tool.get("inputSchema"), dict) else {"type": "object", "properties": {}}
        # Remote schemas are untrusted. Never resolve network references during validation.
        def unsafe_schema(value, depth=0):
            if depth > 20:
                return True
            if isinstance(value, dict):
                if "$ref" in value and not str(value["$ref"]).startswith("#/"):
                    return True
                return any(unsafe_schema(child, depth+1) for child in value.values())
            if isinstance(value, list):
                return any(unsafe_schema(child, depth+1) for child in value)
            return False
        if len(json.dumps(schema)) > 20000 or unsafe_schema(schema):
            continue
        try:
            from jsonschema import Draft202012Validator
            Draft202012Validator.check_schema(schema)
        except Exception:
            continue
        output.append({"type": "function", "function": {"name": public_name,
            "description": str(tool.get("description") or f"Remote MCP tool {name}")[:700],
            "parameters": schema}, "_server": server["name"], "_remote_tool": name,
            "_read_only": read_only, "_approved": approved, "_safe_to_call": safe_to_call})
    return output

def list_tools(force_refresh: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    now = time.monotonic()
    if not force_refresh and now - float(_cache["at"]) < _CACHE_TTL:
        return list(_cache["tools"]), list(_cache["errors"])
    tools, errors = [], []
    for server in _servers():
        try:
            tools.extend(_tools_for_server(server))
        except Exception as exc:
            errors.append({"server": server["name"], "error": str(exc)[:160]})
    _cache.update({"at": now, "tools": tools, "errors": errors})
    return list(tools), list(errors)

def openai_tool_definitions() -> list[dict[str, Any]]:
    tools, _ = list_tools()
    return [{"type": "function", "function": item["function"]} for item in tools
            if item.get("_approved") is True and item.get("_safe_to_call") is True and item.get("_read_only") is True]

def call_tool(public_name: str, arguments: dict[str, Any], *, confirmed: bool = False) -> dict[str, Any]:
    tools, _ = list_tools()
    match = next((item for item in tools if item["function"]["name"] == public_name), None)
    if not match or match.get("_approved") is not True or match.get("_safe_to_call") is not True:
        raise ValueError("MCP tool is not approved for execution or is unavailable")
    if match.get("_read_only") is not True and not confirmed:
        raise ValueError("Sensitive MCP tool requires explicit user confirmation for this invocation")
    from jsonschema import Draft202012Validator
    schema = match["function"]["parameters"]
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(arguments)
    except Exception:
        raise ValueError("MCP arguments do not match the tool schema") from None
    server = next((item for item in _servers() if item["name"] == match["_server"]), None)
    if not server or match["_remote_tool"] not in server["allowed_tools"]:
        raise ValueError("MCP server or tool permission is no longer configured")
    if match.get("_read_only") is not True and not server["allow_write"]:
        raise ValueError("Sensitive MCP permission has been revoked")
    session_id = _initialize(server)
    response, _ = _post(server, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": match["_remote_tool"], "arguments": arguments if isinstance(arguments, dict) else {}}}, session_id)
    if response.get("error"):
        raise RuntimeError("MCP tool execution failed")
    serialized = json.dumps(response.get("result", {}), ensure_ascii=False, default=str)
    return {"server": server["name"], "tool": match["_remote_tool"],
            "result": serialized[:12000] + ("…[truncated]" if len(serialized) > 12000 else "")}
