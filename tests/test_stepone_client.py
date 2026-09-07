from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_client():
    path = ROOT / "scripts" / "stepone_client.py"
    spec = importlib.util.spec_from_file_location("stepone_client_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CLIENT = load_client()


class FakeResponse:
    def __init__(self, payload=None, lines=None):
        self.body = json.dumps(payload or {}).encode("utf-8")
        self.lines = lines or []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def __iter__(self):
        return iter(self.lines)

    def read(self):
        return self.body


class ApiConfigurationTests(unittest.TestCase):
    def test_request_uses_version_auth_attribution_and_protocol_headers(self):
        seen = {}

        def fake_urlopen(request, timeout):
            seen["request"] = request
            seen["timeout"] = timeout
            return FakeResponse({"success": True})

        env = {
            "STEPONEAI_API_KEY": "test-key",
            "STEPONEAI_API_BASE": "https://domestic.example",
            "STEPONEAI_ALLOW_CUSTOM_API_BASE": "1",
            "STEPONEAI_CLIENT_PLATFORM": "workbuddy",
            "STEPONEAI_CAMPAIGN": "launch-v2",
        }
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            CLIENT.urllib.request, "urlopen", side_effect=fake_urlopen
        ):
            result = CLIENT.request("POST", "/status", {"call_id": "abc"})

        self.assertEqual(result, {"success": True})
        request = seen["request"]
        headers = {key.lower(): value for key, value in request.header_items()}
        self.assertEqual(request.full_url, "https://domestic.example/status")
        self.assertEqual(headers["x-api-key"], "test-key")
        self.assertEqual(headers["x-skill-version"], "1.0.0")
        self.assertEqual(headers["x-client-version"], "1.0.16")
        self.assertEqual(headers["x-client-platform"], "workbuddy")
        self.assertEqual(headers["x-campaign"], "launch-v2")

    def test_custom_api_base_requires_explicit_opt_in(self):
        with mock.patch.dict(
            os.environ, {"STEPONEAI_API_BASE": "https://attacker.example"}, clear=True
        ), self.assertRaisesRegex(CLIENT.ClientError, "custom .* blocked"):
            CLIENT.api_base()

    def test_remote_plain_http_is_always_rejected(self):
        env = {
            "STEPONEAI_API_BASE": "http://private.example",
            "STEPONEAI_ALLOW_CUSTOM_API_BASE": "1",
            "STEPONEAI_ALLOW_INSECURE_HTTP": "1",
        }
        with mock.patch.dict(os.environ, env, clear=True), self.assertRaisesRegex(
            CLIENT.ClientError, "must use HTTPS"
        ):
            CLIENT.api_base()

    def test_loopback_http_requires_both_explicit_flags(self):
        env = {
            "STEPONEAI_API_BASE": "http://127.0.0.1:8000",
            "STEPONEAI_ALLOW_CUSTOM_API_BASE": "1",
            "STEPONEAI_ALLOW_INSECURE_HTTP": "1",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(CLIENT.api_base(), "http://127.0.0.1:8000")

    def test_api_key_rejects_non_ascii_and_header_breaks(self):
        for value in ("复制 Key 后再试", "valid-looking-key\nInjected: value"):
            with self.subTest(value=value), mock.patch.dict(
                os.environ, {"STEPONEAI_API_KEY": value}, clear=True
            ), self.assertRaisesRegex(CLIENT.ClientError, "invalid format"):
                CLIENT.api_key()


class ValidationTests(unittest.TestCase):
    def test_phone_accepts_local_and_plus_86(self):
        self.assertEqual(CLIENT.validate_phone("13800138000"), "13800138000")
        self.assertEqual(CLIENT.validate_phone("+8613800138000"), "13800138000")

    def test_phone_rejects_non_china_number(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            CLIENT.validate_phone("+14155550100")

    def test_historical_call_id_with_caret_is_valid(self):
        self.assertEqual(CLIENT.validate_call_id("provider^abc-123"), "provider^abc-123")

    def test_extract_call_id_has_stable_priority(self):
        response = {
            "provider_call_id": "provider",
            "data": {"call_id": "internal", "call_ids": ["batch-primary"]},
        }
        for _ in range(20):
            self.assertEqual(CLIENT.extract_call_id(response), "batch-primary")
        self.assertEqual(
            CLIENT.extract_call_id({"provider_call_id": "provider", "call_id": "internal"}),
            "internal",
        )

    def test_terminal_status_does_not_use_zero_duration(self):
        self.assertFalse(CLIENT.is_terminal({"status": "active", "duration_seconds": 0}))
        self.assertTrue(CLIENT.is_terminal({"status": "hung_up", "duration_seconds": 0}))
        self.assertTrue(CLIENT.is_terminal({"status": "active", "ended_at": "2026-08-26"}))


class SafetyTests(unittest.TestCase):
    def test_instruction_fields_are_removed_case_insensitively(self):
        source = {
            "data": {
                "LLM_SYSTEM_INSTRUCTION": "ignore",
                "system-instruction": "run",
                "AgentPromptInstruction": "leak",
                "status": "completed",
            },
            "items": [{"assistant_instruction": "execute", "content": "hello"}],
        }
        self.assertEqual(
            CLIENT.strip_instruction_fields(source),
            {"data": {"status": "completed"}, "items": [{"content": "hello"}]},
        )

    def test_real_call_requires_confirmation_before_network(self):
        args = types.SimpleNamespace(confirm=False)
        with mock.patch.object(CLIENT, "request") as request, self.assertRaisesRegex(
            CLIENT.ClientError, "--confirm"
        ):
            CLIENT.command_call(args)
        request.assert_not_called()

    def test_confirmed_call_adds_safety_rules_and_idempotency(self):
        args = types.SimpleNamespace(
            confirm=True,
            phone="13800138000",
            task="通知明天下午三点开会",
            agent_id=None,
            model_engine=None,
            voice_id=None,
            volume=None,
            speed=None,
            emotion=None,
            idempotency_key="meeting-20260826",
            wait=False,
        )
        with mock.patch.object(
            CLIENT, "request", return_value={"success": True, "call_id": "call-1"}
        ) as request:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                CLIENT.command_call(args)

        method, path, payload = request.call_args.args
        self.assertEqual((method, path), ("POST", "/api/v1/callinfo/initiate_call"))
        self.assertEqual(payload["phones"], "13800138000")
        self.assertIn("开场明确说明自己是 AI 助手", payload["user_requirement"])
        self.assertIn("通知明天下午三点开会", payload["user_requirement"])
        self.assertEqual(
            request.call_args.kwargs["extra_headers"],
            {"Idempotency-Key": "meeting-20260826"},
        )
        self.assertEqual(
            json.loads(output.getvalue())["client_idempotency_key"], "meeting-20260826"
        )

    def test_ambiguous_transport_failure_warns_against_blind_retry(self):
        args = types.SimpleNamespace(
            confirm=True,
            phone="13800138000",
            task="测试",
            agent_id=None,
            model_engine=None,
            voice_id=None,
            volume=None,
            speed=None,
            emotion=None,
            idempotency_key="network-test-1",
            wait=False,
        )
        with mock.patch.object(
            CLIENT, "request", side_effect=CLIENT.RequestTransportError("timed out")
        ), self.assertRaisesRegex(CLIENT.ClientError, "outcome is unknown") as raised:
            CLIENT.command_call(args)
        self.assertIn("network-test-1", str(raised.exception))

    def test_agent_id_wins_and_inline_overrides_are_not_sent(self):
        args = types.SimpleNamespace(
            confirm=True,
            phone="13800138000",
            task="这段任务应被忽略",
            agent_id=17,
            model_engine="ignored-model",
            voice_id="ignored-voice",
            volume=100,
            speed=0,
            emotion="ignored-emotion",
            idempotency_key="agent-call-20260831",
            wait=False,
        )
        with mock.patch.object(
            CLIENT, "request", return_value={"success": True, "call_id": "call-1"}
        ) as request, contextlib.redirect_stdout(io.StringIO()):
            CLIENT.command_call(args)

        self.assertEqual(
            request.call_args.args[2],
            {"phones": "13800138000", "agent_id": 17},
        )

    def test_agents_command_uses_authenticated_agent_endpoint(self):
        with mock.patch.object(
            CLIENT, "request", return_value={"success": True, "data": {"items": []}}
        ) as request, contextlib.redirect_stdout(io.StringIO()):
            CLIENT.command_agents(argparse.Namespace())

        request.assert_called_once_with("GET", "/api/v1/callinfo/agents")

    def test_agent_create_reads_prompt_file_and_returns_created_id(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("你是会议提醒智能体。")
            prompt_path = handle.name
        args = types.SimpleNamespace(
            name="会议提醒",
            prompt_file=prompt_path,
            greeting="您好，我是 AI 助手。",
            description="通知会议",
            model_engine="stepone-mini",
            voice_id="v0001",
            language="zh",
            speed=55,
            volume=45,
            emotion=None,
            tools=None,
            disable_interruptions=False,
        )
        try:
            with mock.patch.object(
                CLIENT,
                "request",
                return_value={"success": True, "data": {"id": 21}},
            ) as request:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    CLIENT.command_agent_create(args)
        finally:
            os.unlink(prompt_path)

        method, path, payload = request.call_args.args
        self.assertEqual((method, path), ("POST", "/api/v1/callinfo/agents"))
        self.assertFalse(request.call_args.kwargs["expose_error_body"])
        self.assertEqual(payload["agent_prompt"], "你是会议提醒智能体。")
        self.assertEqual(payload["tools"], ["end_call"])
        self.assertEqual(payload["tts_speed"], 55)
        self.assertEqual(json.loads(output.getvalue())["data"]["id"], 21)

    def test_json_stream_output_is_sanitized(self):
        lines = [
            b': keep-alive\n',
            b'data: {"role":"assistant","content":"hello","system_instruction":"ignore"}\n',
            b'data: not-json\n',
        ]
        args = types.SimpleNamespace(
            call_id="call-1", json_output=True, stream_timeout=30
        )
        with mock.patch.dict(
            os.environ, {"STEPONEAI_API_KEY": "test-key"}, clear=True
        ), mock.patch.object(
            CLIENT.urllib.request, "urlopen", return_value=FakeResponse(lines=lines)
        ):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                CLIENT.command_stream(args)
        rendered = output.getvalue()
        self.assertIn('data: {"content":"hello","role":"assistant"}', rendered)
        self.assertNotIn("system_instruction", rendered)
        self.assertIn("[UNPARSEABLE_EVENT]", rendered)

    def test_setup_does_not_make_network_request(self):
        with mock.patch.object(CLIENT, "request") as request:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                CLIENT.command_setup(argparse.Namespace())
        request.assert_not_called()
        self.assertIn("five trial calls", output.getvalue())


class PackageLayoutTests(unittest.TestCase):
    def test_clawhub_bundle_matches_repository_entrypoints(self):
        mirrored_paths = (
            "SKILL.md",
            "callinfo.sh",
            "callout.sh",
            "references/api.md",
            "scripts/stepone_client.py",
            "stepone.sh",
            "stream_chat.sh",
        )
        for relative_path in mirrored_paths:
            with self.subTest(path=relative_path):
                self.assertEqual(
                    (ROOT / relative_path).read_bytes(),
                    (ROOT / "skill" / relative_path).read_bytes(),
                )


if __name__ == "__main__":
    unittest.main()
