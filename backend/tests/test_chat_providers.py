"""Provider adapters use fake HTTP transports only; never use local credentials."""
import json
from unittest.mock import Mock

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, settings
from app.services.chat_planner import interpret, local_plan, provider_plan
from app.services.chat_providers import data_policy, provider_ready


def config(provider="openrouter", **updates):
    return settings.model_copy(update={"CHAT_PROVIDER": provider,
        "CHAT_MODEL": "google/gemini-2.5-flash", "OPENAI_API_KEY": SecretStr("fake-openai"),
        "OPENROUTER_API_KEY": SecretStr("fake-openrouter"), **updates})


def response_payload(text=None):
    return {"choices": [{"finish_reason": "stop", "message": {
        "role": "assistant", "content": text if text is not None else local_plan("inventory").model_dump_json()}}]}


def fake_transport(monkeypatch, payload, status=200):
    response = httpx.Response(status, json=payload,
                              request=httpx.Request("POST", "https://example.invalid"))
    client = Mock()
    client.post.return_value = response
    context = Mock(__enter__=Mock(return_value=client), __exit__=Mock(return_value=False))
    constructor = Mock(return_value=context)
    monkeypatch.setattr("app.services.chat_providers.httpx.Client", constructor)
    return constructor, client


def test_openrouter_request_uses_own_key_and_strict_schema(monkeypatch):
    constructor, client = fake_transport(monkeypatch, response_payload())
    previous = local_plan('Inventory for "Milk"').model_dump()
    assert provider_plan("Show inventory", previous, config()).intent == "inventory"
    args = client.post.call_args
    assert args.args[0] == "https://openrouter.ai/api/v1/chat/completions"
    assert args.kwargs["headers"] == {"Authorization": "Bearer fake-openrouter"}
    body = args.kwargs["json"]
    assert body["model"] == "google/gemini-2.5-flash"
    assert body["max_tokens"] == 500 and body["stream"] is False
    assert body["provider"] == {"require_parameters": True, "data_collection": "deny"}
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    assert len(body["messages"]) == 2
    assert json.loads(body["messages"][1]["content"]) == {"question": "Show inventory", "previous_plan": previous}
    assert "fake-openai" not in json.dumps(body) and "tools" not in body
    assert constructor.call_args.kwargs == {"timeout": settings.CHAT_TIMEOUT_SECONDS,
                                          "follow_redirects": False, "trust_env": False}


@pytest.mark.parametrize("cfg", [
    config("local"), config(OPENROUTER_API_KEY=None), config(OPENROUTER_API_KEY=SecretStr(" ")),
    config(CHAT_MODEL=" "), config("openai", OPENAI_API_KEY=SecretStr("sk-or-v1-fake")),
    config("unknown"),
])
def test_unconfigured_or_wrong_provider_never_calls_network(monkeypatch, cfg):
    constructor, _ = fake_transport(monkeypatch, response_payload())
    assert provider_ready(cfg) is False
    result = interpret("Show inventory", None, cfg)
    assert result["mode"] in ("local", "fallback")
    constructor.assert_not_called()


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_write_request_skips_provider(monkeypatch, provider):
    constructor, _ = fake_transport(monkeypatch, response_payload())
    result = interpret("Set stock to 100", None, config(provider))
    assert result["plan"]["intent"] == "unsupported"
    constructor.assert_not_called()


@pytest.mark.parametrize("payload", [
    {}, [], {"error": {"message": "fake-secret"}}, {"choices": []},
    {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
    {"choices": [{"finish_reason": "stop", "message": {"refusal": "no", "content": "{}"}}]},
    {"choices": [{"finish_reason": "stop", "message": {"content": None}}]},
    {"choices": [{"finish_reason": "stop", "message": {"content": [], "tool_calls": [{}]}}]},
    response_payload("not-json"), response_payload('{"intent":"delete"}'),
    response_payload(json.dumps({**local_plan("inventory").model_dump(), "sql": "SELECT secret"})),
])
def test_invalid_or_refused_openrouter_output_falls_back(monkeypatch, payload):
    fake_transport(monkeypatch, payload)
    result = interpret("Show inventory", None, config())
    assert result["mode"] == "fallback"
    assert "fake-secret" not in json.dumps(result)
    assert result["plan"]["intent"] == "inventory"


@pytest.mark.parametrize("status", [401, 403, 429, 500, 302])
def test_http_error_no_retry_or_raw_error_leak(monkeypatch, status):
    _, client = fake_transport(monkeypatch, {"error": "fake-secret"}, status)
    result = interpret("Show inventory", None, config())
    assert result["mode"] == "fallback"
    assert "fake-secret" not in json.dumps(result)
    assert client.post.call_count == 1


def test_timeout_falls_back(monkeypatch):
    _, client = fake_transport(monkeypatch, response_payload())
    client.post.side_effect = httpx.ReadTimeout("fake-secret")
    result = interpret("Show inventory", None, config())
    assert result["mode"] == "fallback" and "fake-secret" not in json.dumps(result)


def test_openai_refusal_is_not_accepted_even_with_output(monkeypatch):
    fake_transport(monkeypatch, {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "refusal", "refusal": "no"},
        {"type": "output_text", "text": local_plan("inventory").model_dump_json()}]}]})
    assert interpret("Show inventory", None, config("openai"))["mode"] == "fallback"


def test_valid_openrouter_plan_and_followup(monkeypatch):
    plan = local_plan("Show its history")
    fake_transport(monkeypatch, response_payload(plan.model_dump_json()))
    result = interpret("Show its history", {"product_query": "MILK-1"}, config())
    assert result["mode"] == "openrouter"
    assert result["plan"]["product_query"] == "MILK-1"


def test_provider_configuration_and_privacy():
    loaded = Settings(_env_file=None, CHAT_PROVIDER="openrouter", OPENROUTER_API_KEY="fake-secret")
    assert loaded.CHAT_PROVIDER == "openrouter"
    assert "fake-secret" not in repr(loaded)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, CHAT_PROVIDER="arbitrary-provider")
    assert "no provider request" in data_policy(config("local"))
    assert "OpenAI" in data_policy(config("openai"))
    assert "upstream model host" in data_policy(config())
