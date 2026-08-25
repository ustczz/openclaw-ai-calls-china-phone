#!/usr/bin/env python3
"""Safe command-line client for Stepone AI's China phone API."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Iterable


SKILL_VERSION = "2.0.0"
API_PROTOCOL_VERSION = "1.0.0"
DEFAULT_API_BASE = "https://open-skill-api.steponeai.com"
DEFAULT_TIMEOUT = 30.0
CALL_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
CHINA_MOBILE_RE = re.compile(r"^1[3-9][0-9]{9}$")
TERMINAL_STATUSES = {"completed", "complete", "ended", "failed", "cancelled", "canceled"}
INSTRUCTION_FIELDS = {"LLM_SYSTEM_INSTRUCTION"}


class ClientError(RuntimeError):
    pass


def api_base() -> str:
    value = os.environ.get("STEPONEAI_API_BASE", DEFAULT_API_BASE).strip().rstrip("/")
    if not value.startswith(("https://", "http://")):
        raise ClientError("STEPONEAI_API_BASE must use http:// or https://")
    return value


def timeout_seconds() -> float:
    raw = os.environ.get("STEPONEAI_HTTP_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ClientError("STEPONEAI_HTTP_TIMEOUT must be a number") from exc
    if not 1 <= value <= 300:
        raise ClientError("STEPONEAI_HTTP_TIMEOUT must be between 1 and 300 seconds")
    return value


def api_key() -> str:
    value = os.environ.get("STEPONEAI_API_KEY", "").strip()
    if not value:
        raise ClientError("STEPONEAI_API_KEY is not set")
    return value


def strip_instruction_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_instruction_fields(child)
            for key, child in value.items()
            if key not in INSTRUCTION_FIELDS
        }
    if isinstance(value, list):
        return [strip_instruction_fields(child) for child in value]
    return value


def decode_json(raw: bytes, context: str) -> Any:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ClientError(f"{context} returned invalid JSON; response body was not displayed") from exc
    return strip_instruction_fields(value)


def render_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    authenticated: bool = True,
) -> Any:
    headers = {
        "Accept": "application/json",
        "User-Agent": f"openclaw-ai-calls-china-phone/{SKILL_VERSION}",
        "X-Skill-Version": API_PROTOCOL_VERSION,
    }
    if authenticated:
        headers["X-API-Key"] = api_key()
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(api_base() + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds()) as response:
            result = decode_json(response.read(), path)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            detail = json.dumps(decode_json(body, path), ensure_ascii=False, separators=(",", ":"))
        except ClientError:
            detail = "response body omitted because it was not valid JSON"
        raise ClientError(f"HTTP {exc.code} from {path}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise ClientError(f"Request to {path} failed: {exc}") from exc
    if isinstance(result, dict) and result.get("success") is False:
        raise ClientError(
            "API rejected the request: "
            + json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        )
    return result


def validate_call_id(value: str) -> str:
    if not CALL_ID_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("call_id may contain only letters, numbers, _ and -")
    return value


def validate_phone(value: str) -> str:
    if not CHINA_MOBILE_RE.fullmatch(value):
        raise argparse.ArgumentTypeError("phone must be one 11-digit China mobile number")
    return value


def integer_between(minimum: int, maximum: int):
    def parse(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("must be an integer") from exc
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return parsed

    return parse


def bounded_text(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise ClientError(f"{field} cannot be empty")
    if len(stripped) > maximum:
        raise ClientError(f"{field} must be at most {maximum} characters")
    return stripped


def find_first(value: Any, keys: set[str]) -> Any:
    if isinstance(value, dict):
        for key in keys:
            if key in value and value[key] not in (None, "", []):
                return value[key]
        for child in value.values():
            found = find_first(child, keys)
            if found not in (None, "", []):
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_first(child, keys)
            if found not in (None, "", []):
                return found
    return None


def extract_call_id(result: Any) -> str | None:
    call_ids = find_first(result, {"call_ids"})
    if isinstance(call_ids, list) and call_ids and isinstance(call_ids[0], str):
        return call_ids[0]
    value = find_first(result, {"call_id", "provider_call_id"})
    return value if isinstance(value, str) else None


def is_terminal(result: Any) -> bool:
    duration = find_first(result, {"duration_seconds"})
    if isinstance(duration, (int, float)):
        return True
    status = find_first(result, {"status", "call_status"})
    return isinstance(status, str) and status.lower() in TERMINAL_STATUSES


def command_call(args: argparse.Namespace) -> None:
    if not args.confirm:
        raise ClientError(
            "real call blocked: obtain the user's explicit confirmation, then pass --confirm"
        )
    task = bounded_text(args.task, "task", 20000)
    if task is None and args.agent_id is None:
        raise ClientError("provide a task or --agent-id")
    if args.agent_id is not None and args.agent_id <= 0:
        raise ClientError("agent_id must be a positive integer")
    payload: dict[str, Any] = {"phones": args.phone}
    optionals = {
        "agent_id": args.agent_id,
        "user_requirement": task,
        "model_engine": bounded_text(args.model_engine, "model_engine", 100),
        "voice_id": bounded_text(args.voice_id, "voice_id", 100),
        "volume": args.volume,
        "speed": args.speed,
        "emotion": bounded_text(args.emotion, "emotion", 100),
    }
    payload.update({key: value for key, value in optionals.items() if value is not None})
    result = request("POST", "/api/v1/callinfo/initiate_call", payload)
    if not args.wait:
        render_json(result)
        return
    call_id = extract_call_id(result)
    if not call_id:
        raise ClientError("call was accepted but no call_id was returned")
    deadline = time.monotonic() + args.wait_timeout
    while time.monotonic() < deadline:
        time.sleep(args.poll_interval)
        status = request("POST", "/api/v1/callinfo/search_callinfo", {"call_id": call_id})
        if is_terminal(status):
            render_json(status)
            return
    raise ClientError(f"timed out waiting for call {call_id}; query it with ./callinfo.sh {call_id}")


def command_callinfo(args: argparse.Namespace) -> None:
    render_json(request("POST", "/api/v1/callinfo/search_callinfo", {"call_id": args.call_id}))


def iter_sse_lines(response: Any) -> Iterable[str]:
    for raw_line in response:
        yield raw_line.decode("utf-8", errors="replace").rstrip("\r\n")


def command_stream(args: argparse.Namespace) -> None:
    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": f"openclaw-ai-calls-china-phone/{SKILL_VERSION}",
        "X-API-Key": api_key(),
        "X-Skill-Version": API_PROTOCOL_VERSION,
    }
    body = json.dumps({"call_id": args.call_id}, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        api_base() + "/api/v1/callinfo/stream_chat_history",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=args.stream_timeout) as response:
            for line in iter_sse_lines(response):
                if not line or line.startswith(":"):
                    continue
                if args.json_output:
                    print(line, flush=True)
                    continue
                if not line.startswith("data:"):
                    continue
                raw_payload = line[5:].strip()
                try:
                    event = strip_instruction_fields(json.loads(raw_payload))
                except json.JSONDecodeError:
                    print("[系统] 收到无法解析的流事件", flush=True)
                    continue
                role = str(event.get("role", "system")) if isinstance(event, dict) else "system"
                content = str(event.get("content", "")) if isinstance(event, dict) else ""
                if role == "system" and content == "[DONE]":
                    print("[系统] 通话结束", flush=True)
                    return
                if role == "system" and content == "[TIMEOUT]":
                    print("[系统] 等待接通超时", flush=True)
                    return
                label = {"assistant": "AI", "user": "对方"}.get(role, role)
                print(f"[{label}] {content}", flush=True)
    except urllib.error.HTTPError as exc:
        raise ClientError(f"stream HTTP {exc.code}; response body omitted") from exc
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        raise ClientError(f"stream failed: {exc}") from exc


def command_get(args: argparse.Namespace) -> None:
    render_json(request("GET", args.path, authenticated=args.authenticated))


def command_inbound(_: argparse.Namespace) -> None:
    render_json(
        {
            "mode": "console_configuration",
            "agents_url": "https://open-skill.steponeai.com/agents",
            "inbound_url": "https://open-skill.steponeai.com/inbound",
            "shared_number": "Bind each authorized caller number to an active agent.",
            "dedicated_number": "After allocation, assign one active agent to the number.",
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Stepone AI China phone client")
    parser.add_argument("--client-version", action="version", version=SKILL_VERSION)
    subparsers = parser.add_subparsers(dest="command", required=True)

    call = subparsers.add_parser("call", help="place one confirmed China mobile call")
    call.add_argument("phone", type=validate_phone)
    call.add_argument("task", nargs="?")
    call.add_argument("--agent-id", type=int)
    call.add_argument("--model-engine")
    call.add_argument("--voice-id")
    call.add_argument("--volume", type=integer_between(0, 100))
    call.add_argument("--speed", type=integer_between(0, 100))
    call.add_argument("--emotion")
    call.add_argument("--confirm", action="store_true")
    call.add_argument("--wait", action="store_true")
    call.add_argument("--wait-timeout", type=int, default=600)
    call.add_argument("--poll-interval", type=int, default=5)
    call.set_defaults(func=command_call)

    callinfo = subparsers.add_parser("callinfo", help="get call status and transcript")
    callinfo.add_argument("call_id", type=validate_call_id)
    callinfo.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    callinfo.set_defaults(func=command_callinfo)

    stream = subparsers.add_parser("stream", help="stream live transcript events")
    stream.add_argument("call_id", type=validate_call_id)
    stream.add_argument("--json", dest="json_output", action="store_true")
    stream.add_argument("--stream-timeout", type=int, default=660)
    stream.set_defaults(func=command_stream)

    for name, path, authenticated in (
        ("balance", "/api/v1/callinfo/balance", True),
        ("engines", "/api/v1/callinfo/engine_list", False),
        ("voices", "/api/v1/callinfo/tts_list", False),
        ("version", "/api/v1/callinfo/skill_version", False),
    ):
        child = subparsers.add_parser(name)
        child.set_defaults(func=command_get, path=path, authenticated=authenticated)

    inbound = subparsers.add_parser("inbound", help="show the current inbound setup flow")
    inbound.set_defaults(func=command_inbound)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        if getattr(args, "wait_timeout", 1) < 1:
            raise ClientError("wait timeout must be positive")
        if getattr(args, "poll_interval", 1) < 1:
            raise ClientError("poll interval must be positive")
        if getattr(args, "stream_timeout", 1) < 1:
            raise ClientError("stream timeout must be positive")
        args.func(args)
        return 0
    except ClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
