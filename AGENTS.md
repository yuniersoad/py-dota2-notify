# AGENTS.md

## Package manager & runner

All commands must be run through `uv`. Never use `python` or `pip` directly.

```bash
uv run pytest           # run all tests
uv run pytest tests/web/test_notifications.py  # single file
uv run app              # start the web server (port 8000)
uv run match-notify     # start the match polling worker
uv run data-sync        # start the Cosmos DB → Redis sync worker
```

## Three independent services

The repo is a single Python package (`src/dota2_notify`) with three entry points defined in `pyproject.toml`:

| Script | Module | Role |
|---|---|---|
| `app` | `dota2_notify.app.main:main` | FastAPI web server |
| `match-notify` | `dota2_notify.notify.main:run` | Steam match feed poller + Telegram notifier |
| `data-sync` | `dota2_notify.sync.main:run` | Cosmos DB change feed → Redis sync |

Each service has its own `config.py` with its own required env vars. **Do not assume a setting in one service config exists in another.**

## Environment variables

Config uses `pydantic-settings` with double-underscore as the namespace separator (e.g. `REDIS__HOST`, `TELEGRAM__BOTTOKEN`). Copy `.env.example` to `.env` — the app reads `.env` automatically.

`get_settings()` is `@cache`-decorated. In tests, always override it via `app.dependency_overrides[get_settings]`; never patch the cached instance directly.

## Dependency injection pattern

The three app-level singletons are stored on `app.state` and exposed via functions in `src/dota2_notify/web/dependencies.py`:

```python
get_user_service(request)   # → app.state.user_service  (CosmosDbUserService)
get_steam_client(request)   # → app.state.steam_client  (SteamClient)
get_redis_client(request)   # → app.state.redis_client  (redis.asyncio.Redis)
```

When writing tests that build a standalone `FastAPI()` app, **override all three** that the router under test depends on, or the test will raise `AttributeError: 'State' object has no attribute '...'`.

## Testing conventions

- Framework: `pytest` + `pytest-asyncio`. Async tests need `@pytest.mark.asyncio`.
- HTTP mocking: `pytest-httpx` (`httpx_mock` fixture) — used for `SteamClient` and `TelegramClient` tests.
- Web tests use `fastapi.testclient.TestClient` with a manually constructed `FastAPI()` app and `app.dependency_overrides`.
- No real external services are needed to run the test suite.
- Tests live under `tests/` mirroring `src/dota2_notify/` (e.g. `tests/web/`, `tests/clients/`).

## Redis key conventions

| Key pattern | Type | Owner | Purpose |
|---|---|---|---|
| `{account_id}` (bare integer string) | Set | `data-sync` / `match-notify` | Maps Dota account ID → set of user IDs to notify |
| `steam:player_summaries:{steam_id}` | String (JSON) | `SteamClient` | 1-hour cache of Steam player summary |
| `steam:friend_list:{steam_id}` | String (JSON) | `SteamClient` | 1-hour cache of Steam friend list |
| `telegram_verified:{account_id}` | Pub/Sub channel | `app` (notifications) | Signals browser WebSocket when Telegram verification completes |

Redis DB index is always `0` across all services.

## Telegram verification flow

1. Browser opens `WS /notifications/ws` → server subscribes to `telegram_verified:{account_id}`.
2. User clicks Telegram deep link / sends `/start <token>` to the bot.
3. `POST /notifications/telegram-webhook/74ad1s_{secret}` validates the token, writes `telegram_chat_id` to Cosmos DB, then publishes to the Redis channel.
4. WebSocket handler receives the pub/sub message, sends `{"connected": true}` to the browser, browser reloads.
5. Fallback: `GET /notifications/is_telegram_connected` (Cosmos DB point-read) is kept and the JS falls back to 5-second polling if the WebSocket fails or is unsupported.

## Cosmos DB structure

Three containers (all in the same database):

| Container env var | Contents |
|---|---|
| `COSMOSDB__CONTAINERNAME` | `User` documents (users + friends) |
| `COSMOSDB__TOKENCONTAINERNAME` | `UserTelegramVerifyToken` docs (TTL: 7 days) |
| `COSMOSDB__METADATACONTAINERNAME` | Metadata (e.g. last Steam match sequence number) |

`CosmosDbUserService.connect()` must be awaited before use — it resolves the container clients.

## CI / Deployment

- Branch `master` triggers all three GitHub Actions workflows simultaneously.
- Each workflow builds a separate Docker image (`Dockerfile`, `Dockerfile.notify`, `Dockerfile.sync`) and deploys to Azure Container Apps (`dota2notify2`, `data-sync`, `match-notify` in resource group `dota2notify`).
- There is no staging environment — merging to `master` deploys directly to production.
- `OPENAPI__PATH` is set to empty string in production to disable the OpenAPI docs endpoint.
