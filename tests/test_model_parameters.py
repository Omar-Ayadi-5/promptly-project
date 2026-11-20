"""Capture final OpenAI SDK HTTP requests without network or database writes."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch
import httpx
import jwt
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/assets/backend"))
from model_parameters import filter_parameters, openrouter_parameters
from app import create_app
MODELS = json.loads((ROOT / "tests/fixtures/model-capabilities.json").read_text())
FLINT, XINGCHEN = MODELS
USER, CHAT = "000000000000000000000001", "000000000000000000000002"


class ParameterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.environment = patch.dict(os.environ, {
            "openrouter_key": "test-only", "Token_secret_key": "test-only-token-secret-with-at-least-32-bytes",
        })
        cls.environment.start()
        cls.token = jwt.encode({"user_id": USER, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, "test-only-token-secret-with-at-least-32-bytes", algorithm="HS256")

    @classmethod
    def tearDownClass(cls):
        cls.environment.stop()

    def setUp(self):
        self.database = MagicMock()
        self.catalog = {model["id"]: model for model in MODELS}
        self.database["models"].find_one.side_effect = lambda query: self.catalog.get(query["id"])
        self.database["messages"].find.return_value.sort.return_value.limit.return_value = []
        self.payloads = []
        self.upstream_status = 200
        self.upstream_headers = {}
        self.upstream_exception = None
        self.upstream_body = {
            "id": "test", "object": "chat.completion", "created": 0, "model": "test",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "Test answer"}}],
        }

        def handle(request):
            self.payloads.append(json.loads(request.content))
            if self.upstream_exception is not None:
                raise self.upstream_exception
            return httpx.Response(self.upstream_status, json=self.upstream_body, headers=self.upstream_headers)

        self.api = OpenAI(api_key="test-only", base_url="https://test.invalid/v1",
                          http_client=httpx.Client(transport=httpx.MockTransport(handle)))
        self.http = create_app(
            {"TESTING": True}, database=self.database, ai_client=self.api,
        ).test_client()

    def tearDown(self):
        self.api.close()

    def request(self, model, parameters):
        return self.http.post("/api/get_ai_response", headers={"Authorization": f"bearer {self.token}"},
            json={"userId": USER, "chatId": CHAT, "message": "Hello", "model": model, "parameters": parameters})

    def test_flint_filters_unsupported_and_ui_fields_in_final_http_payload(self):
        response = self.request(FLINT["id"], {"temperature": 0.3, "frequency_penalty": 1,
            "repetition_penalty": 1.1, "model": "injected", "messages": [],
            "supported_parameters": ["frequency_penalty"], "default_parameters": {},
            "provider": {"require_parameters": False}, "extra_body": {"top_k": 100}})
        self.assertEqual(response.status_code, 200)
        payload = self.payloads[-1]
        self.assertEqual(set(payload), {"model", "messages", "max_tokens", "temperature", "top_p", "provider"})
        self.assertEqual(payload["temperature"], 0.3)
        self.assertEqual(payload["model"], FLINT["id"])
        self.assertEqual(payload["provider"], {"require_parameters": True})

    def test_xingchen_defaults_and_extra_fields_reach_openrouter(self):
        self.assertEqual(self.request(XINGCHEN["id"], {"top_k": 20, "seed": 0}).status_code, 200)
        payload = self.payloads[-1]
        for key, value in {"temperature": 1, "top_p": 0.95, "repetition_penalty": 1.05, "top_k": 20, "seed": 0}.items():
            self.assertEqual(payload[key], value)
        self.assertTrue(set(payload) - {"model", "messages", "provider"} <= set(XINGCHEN["supported_parameters"]))

    def test_typed_parameters_are_preserved(self):
        parameters = {"stop": ["END"], "reasoning": {"effort": "low"}, "include_reasoning": False,
                      "response_format": {"type": "json_object"}, "tools": [], "tool_choice": "none"}
        self.assertEqual(self.request(XINGCHEN["id"], parameters).status_code, 200)
        for key, value in parameters.items():
            self.assertEqual(self.payloads[-1][key], value)

    def test_empty_capabilities_send_no_generation_fields(self):
        self.catalog["empty"] = {"id": "empty", "supported_parameters": []}
        self.assertEqual(self.request("empty", {"temperature": 1}).status_code, 200)
        self.assertEqual(set(self.payloads[-1]), {"model", "messages"})

    def test_legacy_uses_the_existing_five_parameters(self):
        self.catalog["legacy"] = {"id": "legacy", "default_parameters": None}
        self.assertEqual(self.request("legacy", {"temperature": 0.3, "top_k": 100}).status_code, 200)
        payload = self.payloads[-1]
        self.assertEqual(payload["max_tokens"], 8192)
        self.assertEqual(payload["temperature"], 0.3)
        self.assertNotIn("top_k", payload)
        self.assertNotIn("provider", payload)

    def test_model_details_expose_metadata(self):
        response = self.http.post("/api/Load_model_details", json={"model_id": XINGCHEN["id"]},
                                  headers={"Authorization": f"bearer {self.token}"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["supported_parameters"], XINGCHEN["supported_parameters"])
        self.assertEqual(response.json["default_parameters"], XINGCHEN["default_parameters"])

    def test_unknown_model_and_malformed_parameters_never_call_openrouter(self):
        self.assertEqual(self.request("unknown", {}).status_code, 404)
        for invalid in [["temperature"], [], "bad"]:
            self.assertEqual(self.request(FLINT["id"], invalid).status_code, 400)
        self.assertEqual(self.payloads, [])

    def test_types_ranges_and_malformed_capabilities(self):
        self.assertEqual(filter_parameters(XINGCHEN, {"max_tokens": True, "temperature": "0.5",
            "top_p": 2, "seed": 1.5, "frequency_penalty": float("nan"), "reasoning": [], "stop": [1]}), {})
        self.assertEqual(openrouter_parameters({"supported_parameters": "invalid"}, {}), {})

    def test_authentication_still_required(self):
        self.assertEqual(self.http.post("/api/get_ai_response", json={}).status_code, 401)
        self.assertEqual(self.payloads, [])

    def test_history_is_structured_and_current_message_is_not_duplicated(self):
        self.database["messages"].find.return_value.sort.return_value.limit.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "AI", "content": "Previous answer"},
            {"role": "user", "content": "Previous question"},
        ]
        self.assertEqual(self.request(FLINT["id"], {}).status_code, 200)
        messages = self.payloads[-1]["messages"]
        self.assertEqual([item["role"] for item in messages], ["system", "user", "assistant", "user"])
        self.assertEqual([item["content"] for item in messages[1:]], ["Previous question", "Previous answer", "Hello"])

    def test_legacy_failure_rows_are_not_sent_as_model_answers(self):
        self.database["messages"].find.return_value.sort.return_value.limit.return_value = [
            {"role": "AI", "content": "Failed to generate AI response"},
            {"role": "user", "content": "Hello"},
        ]
        self.assertEqual(self.request(FLINT["id"], {}).status_code, 200)
        self.assertEqual([item["role"] for item in self.payloads[-1]["messages"]], ["system", "user"])

    def test_realistic_rate_limit_returns_429_without_saving_fake_answer(self):
        self.upstream_status = 429
        self.upstream_headers = {"Retry-After": "30"}
        self.upstream_body = {"error": {"code": 429, "message": "Provider returned error",
                                       "metadata": {"provider_name": "Phala", "raw": "Temporarily rate-limited"}}}
        response = self.request(XINGCHEN["id"], {})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json["code"], "rate_limit_exceeded")
        self.assertIn("rate-limited", response.json["error"])
        self.assertEqual(response.headers["Retry-After"], "30")
        self.assertEqual(len(self.payloads), 1)
        self.database["messages"].insert_one.assert_not_called()

    def test_http_200_with_embedded_error_is_not_a_success(self):
        self.upstream_body = {"error": {"code": 503, "message": "Provider failed"}}
        response = self.request(FLINT["id"], {})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "provider_unavailable")
        self.database["messages"].insert_one.assert_not_called()

    def test_missing_choices_or_null_content_returns_a_useful_error(self):
        for body in [{"choices": []}, {}, {"choices": [{"index": 0, "finish_reason": "stop",
                "message": {"role": "assistant", "content": None}}]}]:
            self.upstream_body = body
            response = self.request(FLINT["id"], {})
            self.assertEqual(response.status_code, 502)
            self.assertEqual(response.json["code"], "empty_response")
        self.database["messages"].insert_one.assert_not_called()

    def test_reasoning_only_token_exhaustion_does_not_crash_or_leak_reasoning(self):
        self.upstream_body = {"choices": [{"index": 0, "finish_reason": "length",
            "message": {"role": "assistant", "content": None, "reasoning": "Internal reasoning"}}]}
        response = self.request(FLINT["id"], {})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json["code"], "max_tokens_exhausted")
        self.assertIn("Increase Max Tokens", response.json["error"])
        self.assertNotIn("Internal reasoning", response.get_data(as_text=True))
        self.database["messages"].insert_one.assert_not_called()

    def test_partial_provider_errors_are_not_saved_as_success(self):
        self.upstream_body = {"choices": [{"index": 0, "finish_reason": "error",
            "error": {"code": 502, "message": "Provider disconnected"},
            "message": {"role": "assistant", "content": "Partial"}}]}
        self.assertEqual(self.request(FLINT["id"], {}).status_code, 502)
        self.database["messages"].insert_one.assert_not_called()

    def test_upstream_credentials_do_not_look_like_a_promptly_login_failure(self):
        self.upstream_status = 401
        self.upstream_body = {"error": {"code": 401, "message": "Invalid credentials"}}
        response = self.request(FLINT["id"], {})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json["code"], "upstream_authentication")

    def test_upstream_timeout_returns_504_without_retrying_or_saving(self):
        self.upstream_exception = httpx.ReadTimeout("test timeout")
        response = self.request(FLINT["id"], {})
        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json["code"], "upstream_timeout")
        self.assertEqual(len(self.payloads), 1)
        self.database["messages"].insert_one.assert_not_called()

    def test_upstream_connection_failure_returns_502_without_retrying_or_saving(self):
        self.upstream_exception = httpx.ConnectError("test connection failure")
        response = self.request(FLINT["id"], {})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json["code"], "upstream_connection_error")
        self.assertEqual(len(self.payloads), 1)
        self.database["messages"].insert_one.assert_not_called()

    def test_reply_keeps_message_formatting_and_is_saved_only_on_success(self):
        text = "First paragraph.\n\n- One\n- Two\n\n```python\nprint('hello')\n```"
        self.upstream_body["choices"][0]["message"]["content"] = text
        response = self.request(FLINT["id"], {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"response": text})
        self.assertEqual(self.database["messages"].insert_one.call_args.args[0]["content"], text)

    def test_larger_token_requests_are_capped_at_the_model_output_limit(self):
        self.catalog[FLINT["id"]] = {**FLINT, "max_completion_tokens": 4096}
        self.assertEqual(self.request(FLINT["id"], {"max_tokens": 32768}).status_code, 200)
        self.assertEqual(self.payloads[-1]["max_tokens"], 4096)
        self.assertNotIn("max_completion_tokens", self.payloads[-1])

    def test_long_output_budget_reaches_openrouter_unchanged_when_supported(self):
        self.assertEqual(self.request(FLINT["id"], {"max_tokens": 32768}).status_code, 200)
        self.assertEqual(self.payloads[-1]["max_tokens"], 32768)


if __name__ == "__main__":
    unittest.main()
