# NYC Summer Dining Recommender

Personal AI-powered dining app. See `docs/superpowers/specs/2026-04-17-nyc-summer-dining-design.md` for the design spec and `docs/superpowers/plans/2026-04-17-nyc-summer-dining.md` for the implementation plan.

## Dev

```bash
cd backend
cp .env.example .env   # fill in values
uv sync
uv run pytest
uv run uvicorn app.main:app --reload
```

Then open http://localhost:8000.

## Deploy (Fly.io)

Secrets are set **only** via `flyctl secrets set` — never committed to the repo or written to `.env` on the server.

```bash
# One-time: provision secrets (rotate values if compromised)
flyctl secrets set \
  SHARED_PASSWORD_HASH="$(uv run python -c "from app.auth import hash_password; print(hash_password('YOUR_PASSWORD'))")" \
  COOKIE_SIGNING_KEY="$(openssl rand -hex 32)" \
  COOKIE_SECURE=true \
  ANTHROPIC_API_KEY="sk-ant-..." \
  RESY_API_KEY="..." \
  RESY_AUTH_TOKEN="..."

flyctl deploy
```

Non-secret config (e.g. `DATA_DIR`, `FRONTEND_DIR`) lives in `fly.toml` under `[env]`.
