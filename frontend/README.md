# IntelliStock frontend

The IntelliStock operations console is a React 19 and TanStack Start application backed by the FastAPI service in `../backend`.

## Run locally

```powershell
Copy-Item .env.example .env
npm ci
npm run dev
```

The default frontend URL is `http://localhost:3000`. Configure API and WebSocket endpoints in `.env`:

```env
VITE_API_URL=http://127.0.0.1:8000/api/v1
VITE_WS_URL=ws://127.0.0.1:8000/ws/inventory
```

## Checks

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```

Production builds emit a self-hostable Node server in `.output/server/index.mjs`; the included Dockerfile packages that output in its `production` stage.
