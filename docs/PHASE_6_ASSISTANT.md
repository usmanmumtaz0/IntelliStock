# Phase 6: private, read-only inventory assistant

## Scope

The console now has **Assistant**, alongside **Agent Activity**. Its real LangGraph workflow is user-message-triggered: interpret a bounded query plan, run allowlisted database reads, and render the resulting facts and references. It never runs per video frame.

Supported reads: current inventory, active alerts, recorded inventory history (1–90 days), and current inventory aggregates. Queries show their product scope, current stock filter where applicable, total matching rows, and at most 20 detailed source records. Counts, dates, deltas and source URLs are rendered by backend code, not invented by an LLM. History changes are not inferred sales; committed quantities can be stale. Responses are retained snapshots, not live-updating stock records.

This is a bounded operational assistant, **not an unrestricted chatbot**. It cannot execute SQL, change stock, acknowledge alerts, manage users, send messages, make purchases, read credentials or forecast demand. The selected provider interprets questions into an allowlisted plan only; it does not write the final factual answer. A model can still misunderstand a question, so inspect the displayed product scope and source records.

Document RAG/vector storage is intentionally not added: no document-answering requirement or approved knowledge corpus has been supplied. No new broker, microservice or autonomous agent was introduced.

## Local mode and follow-ups

Local mode makes no model-provider requests. Try:

- `Show low stock`
- `Inventory for SKU MILK-1`
- `History for "Milk" in the last 7 days`
- `Show its history` after a product-specific question
- `Show active alerts`
- `Inventory summary`

The local router uses limited English keywords. Quote product names or write `SKU` followed by its code. It is not a natural-language model. Follow-up memory retains the last query's product filter, not an unrestricted semantic summary of the conversation. Without previous product context, a pronoun follow-up asks for clarification. Each question queries fresh records; previous counts are never reused as current facts. Alert queries show all active alert types for the chosen product, not arbitrary severity/date filtering.

## Installation and configuration

The project already included LangGraph/LangChain and HTTPX. Activating the previously unused graph exposed the Python 3.12.4+ compatibility bug in Pydantic 2.5.0's v1 compatibility layer. `backend/requirements.txt` now pins **Pydantic 2.7.4**; root/CV requirements inherit it. See the upstream [2.7.4 release notes](https://pypi.org/project/pydantic/2.7.4/) for the ForwardRef fix. This is a targeted compatibility fix, not certification of the entire legacy dependency stack for production.

From the project root:

```powershell
python -m pip install -r requirements.txt
cd backend
python -m alembic upgrade head
```

Restart the backend and frontend after deploying. Migration `0005_private_chat` adds conversations and idempotent turns; no migration has been applied to the user's database during implementation.

Safe defaults in `.env.example`:

```dotenv
CHAT_PROVIDER=local
CHAT_MODEL=
OPENAI_API_KEY=
OPENROUTER_API_KEY=
CHAT_TIMEOUT_SECONDS=15
CHAT_MAX_TURNS=100
CHAT_REQUESTS_PER_MINUTE=10
```

Supported `CHAT_PROVIDER` values are `local`, `openai` and `openrouter`. Other provider names are rejected at startup until an adapter is implemented and tested. This is not an arbitrary-endpoint proxy. No new dependency or database migration is required for provider switching.

For direct OpenAI, choose a model available to your account that supports Responses structured outputs, populate `CHAT_MODEL` and `OPENAI_API_KEY`, and set `CHAT_PROVIDER=openai`. OpenRouter-shaped keys in that field are treated as unconfigured and are never sent to OpenAI.

For OpenRouter, set these values only in your ignored root `.env`:

```dotenv
CHAT_PROVIDER=openrouter
CHAT_MODEL=google/gemini-2.5-flash
OPENROUTER_API_KEY=your_new_private_key
```

The model ID is listed in [OpenRouter's model catalog](https://openrouter.ai/google/gemini-2.5-flash); that is not proof of your account's balance/access or a successful live call. Use a model/endpoint supporting structured outputs. OpenRouter does not read `OPENAI_API_KEY`; keys are never implicitly copied between providers. Revoke any key pasted in chat and insert a replacement privately. The local OpenRouter key field was left blank during implementation; existing credentials were not used or migrated.

After edits, restart the backend (or recreate the backend container). Docker forwards both keys and chat settings to the backend only. A pre-existing `backend/.env` overrides root `.env`, and process environment overrides both; resolve conflicting settings if a restart appears ineffective. `CHAT_MODEL` is ignored in local mode. No model or alternative external provider is silently selected. Failed requests fall back to local mode only.

`GET /api/v1/chat/status` reports the selected provider and configuration readiness, not a verified connection. The UI labels successful turns with the provider used at that time; saved OpenAI/local/fallback turns remain compatible. A missing key or model permits backend startup but shows local fallback, not working external AI. Invalid provider names still fail configuration validation.

The OpenAI adapter follows [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and retains Responses `store=false`. The OpenRouter adapter uses [structured Chat Completions](https://openrouter.ai/docs/guides/features/structured-outputs) with strict JSON schema and [provider routing constraints](https://openrouter.ai/docs/guides/routing/provider-selection): `require_parameters=true` and `data_collection=deny`. If no compatible endpoint meets those restrictions, the request fails and local fallback is used; the app does not weaken them automatically.

Both adapters validate the returned plan again with Pydantic, reject refusal/incomplete responses, and limit output tokens to 500. They use the existing HTTPX dependency (the repository's older pinned OpenAI SDK predates Responses). Requests use fixed HTTPS destinations, no redirect following or ambient proxy inheritance, and TLS verification remains enabled. Each question makes at most one application HTTP attempt; OpenRouter may route across compliant hosts internally. Proxy-dependent deployments need a separately reviewed configuration change. Some reasoning models may exhaust the token budget and fall back; configured does not mean every model is compatible.

Provider errors, timeouts, missing configuration and invalid plans fall back to the explicitly labeled local router. No error body, API key or provider exception text is returned to the user. Network timeout is per HTTP operation, not a strict total execution deadline; the browser has a 45-second request timeout. A timed-out request may still finish server-side: retry the same unchanged question to reuse its request ID.

## Privacy and permissions

- Every authenticated role can use read-only chat against the existing single-store dataset. There is no store-level tenancy.
- Conversations belong to their creator. Even another administrator gets 404 when requesting, sending to, or deleting someone else's conversation through this API.
- External modes send **the current question and previous query plan/product context**, not inventory record payloads, prior answers or a database dump. OpenAI mode sends this to OpenAI; OpenRouter mode sends it to OpenRouter and its selected upstream model host. A question or product filter may itself contain confidential information; review this before activation. OpenAI `store=false` and OpenRouter routing restrictions are not blanket zero-retention guarantees; review both gateway and upstream policies/account settings.
- Local PostgreSQL stores questions, answers, references and query context until the owner explicitly deletes the conversation. There is no automatic retention/purge schedule. Deletion removes application rows; database backups may still retain them.
- Agent Activity records only anonymous workflow type, completion mode and duration. Shared traces do not contain private questions, answers, product filters or conversation IDs. A completed fallback indicates a completed read workflow, not a successful provider call.
- External LangChain/LangSmith tracing is rejected for private chat, including inherited tracing contexts. Do not turn on those environment flags for this workflow.
- No passwords, URLs with camera credentials, user-account details or notification destinations are queried by the assistant tools. Do not paste secrets into chat.

## Limits and consistency

Maximum 50 conversations per user and 100 turns per conversation by default (configurable to 200). Questions are limited to 2,000 characters. Detailed query results stop at 20 records and state the full match count. Concurrent requests serialize per user using a PostgreSQL row lock; this also briefly delays changes to that user's account while a request is in flight. Inventory rows are not locked for chat.

A `(conversation_id, request_id)` uniqueness constraint makes explicit retries idempotent. Reusing an ID with different text returns 409. Chat's account rate limit uses the existing Redis limiter plus recent persisted-turn checks. Redis-down fallback is per process; global multi-worker request limits require Redis. Deleting a conversation does not reset the Redis limiter. This is not a billing-budget system; set provider-side spending limits before activation.

Source links open the current inventory/alerts/reports screens, which may differ from the saved answer. Each record reference includes its database ID; aggregate references describe the inventory query at answer time. These are live operational reads, not a transactionally frozen accounting snapshot.

## API

- `GET /api/v1/chat/status`
- `GET/POST /api/v1/chat/conversations`
- `GET/DELETE /api/v1/chat/conversations/{id}`
- `POST /api/v1/chat/conversations/{id}/turns` with `{ "request_id": "UUID", "question": "..." }`

Tests cover real graph execution, owner isolation, follow-up context, deterministic source records, duplicate IDs, role-safe read-only behavior, literal product matching, input bounds, provider contract/fallback and tracing rejection. Provider tests inject fake transports; no real provider acceptance is claimed. PostgreSQL/Redis deployment, multi-worker contention, browser interaction and real-provider acceptance remain final-integration tasks. Model accuracy still waits for Phase 7 weights/footage.
