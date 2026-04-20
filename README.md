# NYC Summer Dining Recommender

Personal AI-powered dining app. See `docs/superpowers/specs/2026-04-17-nyc-summer-dining-design.md` for the design spec and `docs/superpowers/plans/2026-04-17-nyc-summer-dining.md` for the implementation plan.

## Dev

```bash
cd backend
uv sync
uv run pytest
uv run uvicorn app.main:app --reload
```

Then open http://localhost:8000.
