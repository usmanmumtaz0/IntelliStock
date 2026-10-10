"""Allowlisted provider transports. No database access or arbitrary endpoint URLs."""
import json

import httpx

from app.core.config import settings


def provider_key(config=settings) -> str:
    if config.CHAT_PROVIDER == "openai":
        secret = config.OPENAI_API_KEY
    elif config.CHAT_PROVIDER == "openrouter":
        secret = config.OPENROUTER_API_KEY
    else:
        return ""
    key = secret.get_secret_value().strip() if secret else ""
    # Never send the common accidentally pasted OpenRouter key to OpenAI.
    if config.CHAT_PROVIDER == "openai" and key.startswith("sk-or-"):
        return ""
    return key


def provider_ready(config=settings) -> bool:
    """Configuration readiness only; does not verify credentials/model access."""
    return bool(config.CHAT_PROVIDER in ("openai", "openrouter")
                and config.CHAT_MODEL.strip() and provider_key(config))


def data_policy(config=settings) -> str:
    if config.CHAT_PROVIDER == "local":
        return "Local mode makes no provider request."
    destination = ("OpenRouter and the upstream model host" if config.CHAT_PROVIDER == "openrouter"
                   else "OpenAI")
    return (f"When configured, this mode sends your current question and previous product/query context to {destination}. "
            "Database records, source snapshots and prior answers are not sent. Review provider retention policies before enabling.")


def _openai_text(payload: dict) -> str:
    if payload.get("status") != "completed" or payload.get("error"):
        raise ValueError("Incomplete provider response")
    parts = [part for item in payload.get("output", []) if item.get("type") == "message"
             for part in item.get("content", [])]
    if any(part.get("type") == "refusal" for part in parts):
        raise ValueError("Provider refused the request")
    chunks = [part.get("text") for part in parts if part.get("type") == "output_text"]
    if len(chunks) != 1 or not isinstance(chunks[0], str) or not chunks[0].strip():
        raise ValueError("Provider returned no single plan")
    return chunks[0]


def _openrouter_text(payload: dict) -> str:
    choices = payload.get("choices", [])
    if payload.get("error") or len(choices) != 1 or choices[0].get("finish_reason") != "stop":
        raise ValueError("Incomplete provider response")
    message = choices[0].get("message", {})
    text = message.get("content")
    if message.get("refusal") or message.get("tool_calls") or not isinstance(text, str) or not text.strip():
        raise ValueError("Provider refused or returned no text plan")
    return text


def generate_plan(question: str, previous_plan: dict | None, schema: dict,
                  instructions: str, config=settings) -> str:
    if not provider_ready(config):
        raise ValueError("Provider not configured")
    context = json.dumps({"question": question, "previous_plan": previous_plan})
    format_schema = {"name": "inventory_read_plan", "strict": True, "schema": schema}
    if config.CHAT_PROVIDER == "openai":
        endpoint = "https://api.openai.com/v1/responses"
        body = {"model": config.CHAT_MODEL.strip(), "store": False, "max_output_tokens": 500,
                "instructions": instructions, "input": context,
                "text": {"format": {"type": "json_schema", **format_schema}}}
        parse = _openai_text
    else:
        endpoint = "https://openrouter.ai/api/v1/chat/completions"
        body = {"model": config.CHAT_MODEL.strip(), "max_tokens": 500, "stream": False,
                "messages": [{"role": "system", "content": instructions},
                             {"role": "user", "content": context}],
                "response_format": {"type": "json_schema", "json_schema": format_schema},
                "provider": {"require_parameters": True, "data_collection": "deny"}}
        parse = _openrouter_text
    # Single attempt, fixed HTTPS destinations, TLS verification on; no redirects/proxy inheritance.
    with httpx.Client(timeout=config.CHAT_TIMEOUT_SECONDS, follow_redirects=False, trust_env=False) as client:
        response = client.post(endpoint, headers={"Authorization": f"Bearer {provider_key(config)}"}, json=body)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Invalid provider response")
    return parse(payload)
