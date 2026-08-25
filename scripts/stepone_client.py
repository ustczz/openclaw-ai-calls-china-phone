#!/usr/bin/env python3
"""Safe command-line client for Stepone AI's China phone API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Iterable, Sequence
from typing import Any

SKILL_VERSION = "1.0.14"
API_PROTOCOL_VERSION = "1.0.0"
DEFAULT_API_BASE = "https://open-skill-api.steponeai.com"
DEFAULT_TIMEOUT = 30.0
CALL_ID_RE = re.compile(r"^[A-Za-z0-9_.:^~-]{1,256}$")
CHINA_MOBILE_RE = re.compile(r"^1[3-9][0-9]{9}$")
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
ATTRIBUTION_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
TERMINAL_STATUSES = {
    "completed",
    "complete",
    "ended",
    "hung_up",
    "hangup",
    "failed",
    "cancelled",
    "canceled",
    "no_answer",
    "busy",
    "declined",
    "rejected",
    "timeout",
    "voicemail",
}
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
CALL_SAFETY_RULES = """必须遵守以下电话安全规则：
1. 开场明确说明自己是 AI 助手，并说明受谁委托及本次来电目的。
2. 不索取密码、验证码、支付卡号或与任务无关的敏感信息。
3. 对方要求停止、拒绝继续或要求挂断时，立即礼貌结束并挂断。
4. 任务目标已完成或确认无法完成时，简短总结后立即挂断，不继续闲聊。

本次任务："""


class ClientError(RuntimeError):
    pass


class RequestTransportError(ClientError):
    pass


def env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def api_base() -> str:
    value = os.environ.get("STEPONEAI_API_BASE", DEFAULT_API_BASE).strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    if not parsed.scheme or not parsed.netloc or parsed.hostname is None:
        raise ClientError("STEPONEAI_API_BASE must be an absolute HTTPS URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ClientError("STEPONEAI_API_BASE cannot include credentials, a query, or a fragment")
    if parsed.path not in {"", "/"}:
        raise ClientError("STEPONEAI_API_BASE cannot include a path")
    if parsed.scheme != "https":
        insecure_loopback = (
            parsed.scheme == "http"
            and parsed.hostname.lower() in LOOPBACK_HOSTS
            and env_enabled("STEPONEAI_ALLOW_INSECURE_HTTP")
        )
        if not insecure_loopback:
            raise ClientError("STEPONEAI_API_BASE must use HTTPS")
    normalized = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
    if normalized != DEFAULT_API_BASE and not env_enabled("STEPONEAI_ALLOW_CUSTOM_API_BASE"):
        raise ClientError(
            "custom STEPONEAI_API_BASE blocked; set STEPONEAI_ALLOW_CUSTOM_API_BASE=1 "
            "only for a trusted private deployment"
        )
    return normalized


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


def is_instruction_field(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", key.lower())
    return "instruction" in normalized and any(
        token in normalized for token in ("llm", "system", "assistant", "agent", "prompt")
    )


def strip_instruction_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_instruction_fields(child)
            for key, child in value.items()
            if not is_instruction_field(str(key))
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


def attribution_value(env_name: str, default: str | None = None) -> str | None:
    value = os.environ.get(env_name, default or "").strip()
    if not value:
        return None
    if not ATTRIBUTION_RE.fullmatch(value):
        raise ClientError(f"{env_name} may contain only letters, numbers, ., _, and -")
    return value


def request_headers(
    *, authenticated: bool, extra_headers: dict[str, str] | None = None
) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": f"openclaw-ai-calls-china-phone/{SKILL_VERSION}",
        "X-Skill-Version": API_PROTOCOL_VERSION,
        "X-Client-Version": SKILL_VERSION,
        "X-Client-Platform": (
            attribution_value("STEPONEAI_CLIENT_PLATFORM", "clawhub") or "clawhub"
        ),
    }
    campaign = attribution_value("STEPONEAI_CAMPAIGN")
    if campaign:
        headers["X-Campaign"] = campaign
    if authenticated:
        headers["X-API-Key"] = api_key()
    if extra_headers:
        headers.update(extra_headers)
    return headers


def open_request(req: urllib.request.Request, timeout: float):
    scheme = urllib.parse.urlsplit(req.full_url).scheme
    if scheme not in {"https", "http"}:
        raise ClientError("request URL must use HTTP or HTTPS")
    # The URL scheme is allowlisted immediately above.
    return urllib.request.urlopen(req, timeout=timeout)  # nosec B310


def request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    authenticated: bool = True,
    extra_headers: dict[str, str] | None = None,
) -> Any:
    headers = request_headers(authenticated=authenticated, extra_headers=extra_headers)
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(api_base() + path, data=data, headers=headers, method=method)
    try:
        with open_request(req, timeout_seconds()) as response:
            result = decode_json(response.read(), path)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            detail = json.dumps(decode_json(body, path), ensure_ascii=False, separators=(",", ":"))
        except ClientError:
            detail = "response body omitted because it was not valid JSON"
        raise ClientError(f"HTTP {exc.code} from {path}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RequestTransportError(f"Request to {path} failed: {exc}") from exc
    if isinstance(result, dict) and result.get("success") is False:
        raise ClientError(
            "API rejected the request: "
            + json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        )
    return result


def validate_call_id(value: str) -> str:
    if not CALL_ID_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "call_id may contain only letters, numbers, _, -, ., :, ^, and ~"
        )
    return value


def validate_phone(value: str) -> str:
    normalized = value.removeprefix("+86")
    if not CHINA_MOBILE_RE.fullmatch(normalized):
        raise argparse.ArgumentTypeError(
            "phone must be one China mobile number in 11-digit or +86 format; "
            "use ClawCall for other countries"
        )
    return normalized


def validate_idempotency_key(value: str) -> str:
    if not IDEMPOTENCY_KEY_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "idempotency key must be 8-128 characters using letters, numbers, ., _, :, or -"
        )
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


def find_first(value: Any, keys: Sequence[str]) -> Any:
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
    call_ids = find_first(result, ("call_ids",))
    if isinstance(call_ids, list) and call_ids and isinstance(call_ids[0], str):
        return call_ids[0]
    for key in ("call_id", "provider_call_id"):
        value = find_first(result, (key,))
        if isinstance(value, str):
            return value
    return None


def is_terminal(result: Any) -> bool:
    status = find_first(result, ("status", "call_status", "state"))
    if isinstance(status, str) and status.strip().lower() in TERMINAL_STATUSES:
        return True
    ended_at = find_first(result, ("ended_at", "end_time", "endedAt"))
    return ended_at not in (None, "", 0, False)


def build_call_requirement(task: str | None) -> str:
    user_task = bounded_text(task, "task", 19500)
    requirement = CALL_SAFETY_RULES + (user_task or "按照已配置智能体的任务执行。")
    return bounded_text(requirement, "task with safety rules", 20000) or ""


def result_with_idempotency(result: Any, key: str) -> Any:
    if isinstance(result, dict):
        output = dict(result)
        output["client_idempotency_key"] = key
        return output
    return {"result": result, "client_idempotency_key": key}


def command_call(args: argparse.Namespace) -> None:
    if not args.confirm:
        raise ClientError(
            "real call blocked: obtain the user's explicit confirmation, then pass --confirm"
        )
    if args.task is None and args.agent_id is None:
        raise ClientError("provide a task or --agent-id")
    if args.agent_id is not None and args.agent_id <= 0:
        raise ClientError("agent_id must be a positive integer")
    idempotency_key = args.idempotency_key or f"china-call-{uuid.uuid4()}"
    payload: dict[str, Any] = {"phones": args.phone}
    optionals = {
        "agent_id": args.agent_id,
        "user_requirement": build_call_requirement(args.task),
        "model_engine": bounded_text(args.model_engine, "model_engine", 100),
        "voice_id": bounded_text(args.voice_id, "voice_id", 100),
        "volume": args.volume,
        "speed": args.speed,
        "emotion": bounded_text(args.emotion, "emotion", 100),
    }
    payload.update({key: value for key, value in optionals.items() if value is not None})
    try:
        result = request(
            "POST",
            "/api/v1/callinfo/initiate_call",
            payload,
            extra_headers={"Idempotency-Key": idempotency_key},
        )
    except RequestTransportError as exc:
        raise ClientError(
            f"{exc}; call outcome is unknown. Check call records before retrying and reuse "
            f"--idempotency-key {idempotency_key}"
        ) from exc
    if not args.wait:
        render_json(result_with_idempotency(result, idempotency_key))
        return
    call_id = extract_call_id(result)
    if not call_id:
        raise ClientError("call was accepted but no call_id was returned")
    deadline = time.monotonic() + args.wait_timeout
    while time.monotonic() < deadline:
        time.sleep(args.poll_interval)
        status = request("POST", "/api/v1/callinfo/search_callinfo", {"call_id": call_id})
        if is_terminal(status):
            render_json(result_with_idempotency(status, idempotency_key))
            return
    raise ClientError(f"timed out waiting for call {call_id}; query it with ./callinfo.sh {call_id}")


def command_callinfo(args: argparse.Namespace) -> None:
    render_json(request("POST", "/api/v1/callinfo/search_callinfo", {"call_id": args.call_id}))


def iter_sse_lines(response: Any) -> Iterable[str]:
    for raw_line in response:
        yield raw_line.decode("utf-8", errors="replace").rstrip("\r\n")


def command_stream(args: argparse.Namespace) -> None:
    headers = request_headers(authenticated=True)
    headers.update(
        {"Accept": "text/event-stream", "Content-Type": "application/json; charset=utf-8"}
    )
    body = json.dumps({"call_id": args.call_id}, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        api_base() + "/api/v1/callinfo/stream_chat_history",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with open_request(req, args.stream_timeout) as response:
            for line in iter_sse_lines(response):
                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    continue
                raw_payload = line[5:].strip()
                try:
                    event = strip_instruction_fields(json.loads(raw_payload))
                except json.JSONDecodeError:
                    if args.json_output:
                        print(
                            'data: {"role":"system","content":"[UNPARSEABLE_EVENT]"}',
                            flush=True,
                        )
                    else:
                        print("[系统] 收到无法解析的流事件", flush=True)
                    continue
                if args.json_output:
                    print(
                        "data: "
                        + json.dumps(
                            event,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                        flush=True,
                    )
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
    except (urllib.error.URLError, TimeoutError) as exc:
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


def command_setup(_: argparse.Namespace) -> None:
    render_json(
        {
            "signup_url": "https://open-skill.steponeai.com",
            "api_keys_url": "https://open-skill.steponeai.com/keys",
            "free_trial": "New users receive five trial calls, subject to current platform terms.",
            "next_step": "Create an API key, export STEPONEAI_API_KEY, then run ./stepone.sh doctor.",
        }
    )


def command_doctor(_: argparse.Namespace) -> None:
    report: dict[str, Any] = {
        "client_version": SKILL_VERSION,
        "api_protocol_version": API_PROTOCOL_VERSION,
        "api_base": api_base(),
        "client_platform": attribution_value("STEPONEAI_CLIENT_PLATFORM", "clawhub"),
        "api_key_configured": bool(os.environ.get("STEPONEAI_API_KEY", "").strip()),
    }
    try:
        report["service_version"] = request(
            "GET", "/api/v1/callinfo/skill_version", authenticated=False
        )
        if report["api_key_configured"]:
            report["balance"] = request("GET", "/api/v1/callinfo/balance")
        report["ready"] = report["api_key_configured"]
    except ClientError as exc:
        report["ready"] = False
        report["error"] = str(exc)
    render_json(report)


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
    call.add_argument("--idempotency-key", type=validate_idempotency_key)
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

    setup = subparsers.add_parser("setup", help="show registration and API key setup links")
    setup.set_defaults(func=command_setup)

    doctor = subparsers.add_parser("doctor", help="check local configuration and service access")
    doctor.set_defaults(func=command_doctor)
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
