# NYC Summer Dining Recommender — Design Spec

**Status**: Design approved by user, pending implementation plan
**Date**: 2026-04-17
**Owner**: Eli
**Authors**: Eli + Claude (brainstorming session)

## Summary

A personal AI-powered dining recommender for Eli's summer living in NYC. A form-based web app, seeded from publication lists (Eater, Infatuation, NYT), backed by a Python/FastAPI + SQLite server, with on-demand Resy availability checks. Shared-password access for a small group of friends, each of whom can leave per-restaurant notes.

The app ranks filtered shortlists using Claude (Anthropic SDK) based on structured filters *and* a free-form preferences text field. Results stream into the UI progressively.

## Goals

1. One click to find "where should I eat tonight in the East Village that fits my vibe" with a ranked answer and reasons.
2. One more click to check Resy availability for a specific restaurant without leaving the app.
3. A growing, trusted dataset of NYC restaurants enriched from reputable publications.
4. Personal notes ("tried / loved / want to try") shared among a small group of friends.
5. Reliable enough to use in the wild; well-tested enough to evolve confidently.

## Non-goals (v1)

- Collaborative lists / named playlists shared between friends.
- Calendar integration, reminders, notifications.
- Photo uploads, menu parsing, wine list parsing.
- Auto-location from phone GPS.
- Real user accounts with email/password.
- Non-NYC support.

## Users

- **Primary**: Eli, living in NYC for summer 2026. Expected usage: multiple searches per week, on mobile while out.
- **Secondary**: a small group of friends (~3-6) with access via shared password. They see the same dataset, leave their own notes.
- **No public / unauthenticated access.**

## Scope

This spec covers a v1 end-to-end system: seeded dataset → filter + AI ranking → streamed results → availability check → personal notes → admin data maintenance. It is intended to be built and deployed before summer usage starts.

## Architecture overview

### Stack

| Layer | Choice | Rationale |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Best ecosystem for scraping + async APIs. Pydantic models double as schemas. |
| Database | SQLite | Dataset is <500 rows. Single-node app. Easy backups. Zero ops. |
| Frontend | Static HTML/CSS/vanilla JS | Matches existing Claude/dining neighbors (ai-travel-recommender). No build step. |
| LLM | Anthropic SDK, `claude-haiku-4-5-20251001` | Plenty smart for shortlist ranking; ~4-5x cheaper than Sonnet at this scale. Easy to upgrade to Sonnet later if quality isn't enough. |
| Hosting | Fly.io, auto-stop single small machine + persistent volume | ~$0-2/mo with auto-stop (scale-to-zero when idle). ~2-5s cold start on first request after idle; fine for casual use. |
| Dep mgmt | `uv` | Faster install, simpler lockfile than Poetry. |

### Repo layout

```
dining/
  backend/
    app/
      __init__.py
      main.py              # FastAPI app entrypoint
      auth.py              # shared-password middleware + name picker
      db.py                # SQLite connection + session
      models.py            # Pydantic models (API + domain)
      routes/
        search.py          # POST /api/search (SSE streaming)
        availability.py    # GET /api/availability
        admin.py           # admin routes (gated)
        notes.py           # personal notes CRUD
      services/
        ranker.py          # Claude-powered shortlist ranker
        resy_client.py     # Resy API wrapper (protocol + impls)
        llm_client.py      # Anthropic wrapper (protocol + impls)
        fields_extractor.py# LLM-based blurb -> structured fields
        merger.py          # dedup + merge logic
        shortlist.py       # SQL filter builder
    scrapers/
      __init__.py
      eater_essentials.py
      infatuation_hit_list.py
      nyt_100_best.py
      common.py
      run_all.py           # re-seed orchestration
    migrations/
      0001_init.sql
      ...
    tests/
      unit/
      integration/
      fixtures/
        html/
        resy/
        llm/
    pyproject.toml
  frontend/
    index.html
    admin.html
    login.html
    css/
    js/
      app.js
      admin.js
      stream.js            # SSE reader
  data/
    seed/                  # committed JSON outputs from scrapers
    restaurants.db         # gitignored
  docs/
    superpowers/specs/     # this file lives here
  Dockerfile              # copies both backend/ and frontend/
  fly.toml
  .github/
    workflows/ci.yml
  README.md
  .gitignore
  Makefile
```

## Data model

Six tables. SQLite. Pydantic models mirror them one-to-one for API use.

### `restaurants`
| Column | Type | Notes |
|---|---|---|
| id | TEXT PK | slug, e.g. `lilia-williamsburg` |
| name | TEXT | canonical name |
| address | TEXT | |
| neighborhood | TEXT | e.g. "Williamsburg" |
| borough | TEXT | Manhattan / Brooklyn / Queens / Bronx / Staten Island |
| latitude | REAL | nullable |
| longitude | REAL | nullable |
| price_tier | INTEGER | 1..4 ($ .. $$$$) |
| booking_platform | TEXT | 'resy' \| 'opentable' \| 'tock' \| 'walk_in' \| 'other' |
| booking_url | TEXT | nullable |
| resy_venue_id | TEXT | nullable, required for availability checks |
| website_url | TEXT | nullable |
| description | TEXT | short AI-synthesized summary |
| status | TEXT | 'open' \| 'closed' (soft delete) \| 'needs_review' (auto-flagged for admin) |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

### `restaurant_sources` (many per restaurant)
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| restaurant_id | TEXT FK | |
| publication | TEXT | 'eater_nyc', 'infatuation', 'nyt_100', ... |
| list_name | TEXT | e.g. "Best New Restaurants 2025" |
| source_url | TEXT | |
| blurb | TEXT | original quote/excerpt |
| source_date | DATE | |

### `tags`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT UNIQUE | e.g. `italian`, `outdoor`, `rooftop`, `counter-only`, `natural-wine`, `tasting-menu`, `late-night`, `pasta` |
| kind | TEXT | 'cuisine' \| 'vibe' \| 'feature' — for UI grouping only, flexibility preserved |

### `restaurant_tags` (many-to-many)
| Column | Type | Notes |
|---|---|---|
| restaurant_id | TEXT FK | |
| tag_id | INTEGER FK | |
| PK | (restaurant_id, tag_id) | |

### `users`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| display_name | TEXT UNIQUE | chosen after password login, stamped on notes |
| created_at | TIMESTAMP | |

### `personal_notes`
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| user_id | INTEGER FK | |
| restaurant_id | TEXT FK | |
| status | TEXT | 'want_to_try' \| 'tried' \| 'loved' \| 'skip' |
| rating | INTEGER | nullable, 1..5 |
| note | TEXT | nullable |
| visited_date | DATE | nullable |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

UNIQUE (user_id, restaurant_id) — one note per (user, restaurant).

### Design decisions locked in
- Per-friend notes (not shared). Each user has their own `personal_notes` row per restaurant.
- Cuisines are tags (with `kind='cuisine'`), not a dedicated column. Keeps schema flat; simpler queries.
- Soft-delete via `restaurants.status='closed'` preserves notes/history.

## Seeding strategy

### Phase 1: Bootstrap (one-time, pre-summer)

Goal: ~150-200 quality restaurants with structured data, in a few hours of work.

**Source strategy**: Claude-assisted structured extraction, not HTML scraping for content. For well-structured maps/lists we pull the raw page, but the *content extraction* (pulling name, neighborhood, price tier, tags, blurb) goes through Claude with a strict JSON schema and grounded in the source text.

**Starter publications** (in priority order):
1. Eater NYC's "38 Essential Restaurants"
2. Eater NYC's "Where to Eat Right Now" map
3. The Infatuation's "The NYC Hit List"
4. The Infatuation's "Best New Restaurants NYC"
5. NYT Food's "100 Best Restaurants in NYC" (most recent annual)
6. New York Magazine's "Where to Eat" lists
7. Optional: friends' recs via a Google Form dumped to JSON

**Seeder module pattern**: each publication gets a module that emits a JSON file matching a shared `SeedRestaurant` Pydantic schema.

```
backend/scrapers/
  eater_essentials.py       # -> seed/eater_essentials.json
  infatuation_hit_list.py   # -> seed/infatuation_hit_list.json
  nyt_100_best.py           # -> seed/nyt_100_best.json
  common.py                 # SeedRestaurant schema, HTTP helpers
  merge.py                  # dedupe across sources -> seed/restaurants.json
  import.py                 # load seed/restaurants.json into SQLite
  run_all.py                # orchestrate pipeline
```

**Raw JSON outputs are committed to git.** Gives reproducibility, audit trail, clean diffs, and testable files.

### Phase 2: Ongoing additions (during summer)

`/admin` page with four flows (detailed in "Admin" section).

### Deduplication

`merge.py` dedupes across source JSONs by a cascade:

1. Normalize `name` (lowercase, strip punctuation, strip common suffixes: "Restaurant", "NYC", "Brooklyn").
2. Normalize `neighborhood`.
3. Exact match on `(name_norm, neighborhood_norm)` → merge.
4. Fuzzy match (Levenshtein <= 2 on name) + same borough → merge.
5. Ambiguous (fuzzy match, different neighborhoods) → LLM tiebreaker: "Are these the same restaurant?" with both records.
6. When merging: union `tags`, append `sources`, pick most detailed `description`, keep the median `price_tier`.

### Accepted trade-offs

- **No Google Places verification** (per user choice). Risk: some entries may be stale or closed. Mitigations:
  - Publications from 2024+ only.
  - "Mark as closed" is one click in admin.
  - On any availability check, if Resy returns "venue not found", flag the restaurant for review.

### Edge cases explicitly handled

| Case | Handling |
|---|---|
| Same restaurant, 3 sources, 3 spellings | Merger normalizes + fuzzy-matches → one row, three sources |
| Closed restaurant still on 2024 list | Ships in seed. Flagged on first Resy check that 404s, or manually. |
| Two sources disagree on price ($, $$$) | Store all in sources; canonical `price_tier` = median rounded. |
| Restaurant not on Resy | `booking_platform` is `'walk_in'` or `'other'`. UI shows booking_url or "walk-in" chip. No availability button. |
| Blurb contains a LLM-unfriendly emoji or non-ASCII | Strip/normalize before sending to Claude; preserve original in DB. |

## Query flow

Two distinct request paths: **search** (filter → AI rank → render) and **availability** (check one restaurant).

### Search flow

**Frontend form inputs:**

*Hard filters* (exclusionary in SQL):
- Neighborhood: multi-select, grouped by borough.
- Price ceiling: radio 1..4.
- Party size: integer (used for availability later; not used in search filter).

*Soft filters* (influence ranking, not a strict exclude):
- Cuisine: multi-select from `tags` where `kind='cuisine'`.
- Vibe chips: multi-select from curated vibe tag set (`outdoor`, `date-night`, `group`, `counter-only`, `late-night`, `tasting-menu`, `natural-wine`, `casual`, `nice`).

*Free-form preferences text*: optional. Passed verbatim to Claude.

*Date + time*: optional. If provided, enables per-card "Check availability" button.

*Status filter*:
- Include tried? (default: yes)
- Include skip? (default: no)
- Only want-to-try? (default: no)

### Backend pipeline (`POST /api/search`)

1. **SQL shortlist**: apply hard filters → typically 10-40 candidates. Ordered by source count desc, recency desc.
2. **Pre-trim to 25**: if >25, trim by a score combining source count, "want_to_try" bumps for the logged-in user, recency.
3. **Claude ranking call** (streaming): send shortlist rows + soft filters + preferences text + user's friend notes. Ask for top 5-8 ranked IDs with one-sentence reasons.
4. **Stream back** via SSE:
   - First event: all candidate static data + ranked IDs (UI renders skeleton cards in order).
   - Subsequent events: one blurb-complete event per card (UI fills in "why this one").
   - Final event: `done`.

### Prompting

System prompt (static, prompt-cached):

> You are a helpful NYC dining expert helping a friend pick where to eat. Given a shortlist of restaurants, soft preferences, and a free-form preferences note, return a ranked top N with a one-sentence reason for each pick. Use only the data provided; do not invent details. Output format: a sequence of `<card id="SLUG">one-sentence reason</card>` tags in ranked order.

User message (per query):

- Filters (hard + soft, formatted as bullet list).
- Preferences text (as-is).
- Shortlist JSON: `[{id, name, neighborhood, cuisine_tags, vibe_tags, price_tier, description, sources: [{publication, list_name, blurb}], personal_notes: [{display_name, status, rating, note}]}, ...]`.
- "Return top N=min(8, shortlist.length)."

### Streaming format

Backend streams as SSE events. Parsing `<card id="X">reason</card>` tags is simple and incremental (no partial-JSON parsing). One event per completed `</card>` tag.

### Claude call spec

- Model: `claude-haiku-4-5-20251001` (Haiku 4.5). Confirm latest at impl time.
- Max tokens: 1500.
- Temperature: 0.3 (lightly creative reasons, stable ranking).
- Prompt caching: system prompt cached. Shortlist+preferences not cached (varies per query).
- If ranking quality ever feels off, swap to Sonnet is a one-line config change. Keep a flag `LLM_MODEL` env var so we can switch without redeploying code.

### Frontend result cards

Each card shows:
- Name, neighborhood, cuisine tags, price tier.
- AI "why this one" blurb (streamed in).
- Source chips ("Eater 38", "Infatuation Hit List", ...) with tooltip showing original blurb on hover.
- Personal-note indicator ("Sarah: loved, 8/2024") if any friend has one.
- Primary action: "Book on Resy" / "Book on OpenTable" / "Walk-in OK" / other link.
- Secondary action: "Check availability" — only if date+time+party are set AND `booking_platform='resy'` AND `resy_venue_id` is set.
- Kebab menu: mark as tried / want-to-try / skip, add or edit a note.

### Availability flow

**`GET /api/availability?restaurant_id=X&party=Y&date=Z&time=T`**

1. Lookup restaurant.
2. If `booking_platform != 'resy'` → 400 with `use_booking_url`.
3. If `resy_venue_id IS NULL` → 400 with `no_venue_id` (prompt admin to fill in).
4. Call Resy unofficial API (`api.resy.com/4/find`) with `venue_id`, party size, day, time filter.
5. Normalize response → up to 5 slot options within ±2 hours of target.
6. Return slots with Resy deep-links, OR empty array.

**Frontend** displays slots inline on the card: *"Available: 7:30, 8:00, 9:45 →"* each linking to Resy's booking page.

### Error handling

| Failure | Behavior |
|---|---|
| Resy API unreachable / 5xx | Card shows: "Availability check failed — book directly on Resy" with a link. |
| Resy returns no slots | "No slots within ±2hr for party of N. Try another time or book directly on Resy." |
| Resy says venue-not-found | Flag restaurant for review (set `status='needs_review'`). Fall back to generic Resy search URL. |
| Resy schema drift (unexpected JSON) | Log with full raw response, return 500 with `scraper_error`. Nightly contract test catches this. |
| Claude timeout / error | Fall back to unranked shortlist sorted by source count. UI still shows cards, just without AI blurbs. Toast: "AI ranking unavailable, showing by popularity." |
| Claude returns malformed output (missing `<card>` tags) | Parse what we can, fill rest with empty reasons. Log event. |
| No results after filters | Offer relaxation suggestions: "Try dropping the $$ cap?" (inspect filters, propose the one most likely binding). |
| Empty preferences text | Skip that input to Claude; prompt still valid. |
| User hits rate limit (anti-abuse) | 429 with retry-after. Shared password limits blast radius. |

## Admin & data maintenance

`/admin` (behind shared password, same gate as main app) has four flows.

### 1. Add restaurant by URL

- Paste a URL: Resy, OpenTable, Infatuation review, Eater map entry, Google Maps, or plain restaurant website.
- Backend fetches page server-side (avoid CORS, handle bot-challenge with a proper User-Agent).
- Claude extracts structured fields from page text. If URL is Resy, also extract `venue_id` from JSON embedded on page.
- Returns pre-filled form. User reviews, edits, saves.
- Handles "friend just texted me" case fast.

### 2. Add by name

- Type "Nami Nori West Village" → backend:
  - Queries Resy's unofficial search endpoint for the name + NYC location to get candidate `venue_id`s.
  - Calls Claude with the name + any web-lookup context available → pre-filled form.
- User reviews form, picks the right Resy venue if multiple, saves.

### 3. Edit / remove / close

- Search existing restaurants (name-autocomplete).
- Filter by status: "all / open / closed / needs_review". Default shows everything with needs_review at top.
- Edit any field, retag, change booking info, change description.
- "Mark as closed" flips `status='closed'` (soft delete; notes retained, hidden from default main search).
- "Resolve review" flips `status='needs_review'` back to `status='open'` after admin confirms the restaurant is fine.
- Hard delete with confirm ("are you sure?") — rare; notes cascade.

### 4. Re-run seeders

- Button per seeder: "Re-seed Eater Essentials".
- Runs seeder → produces new JSON → diff against current DB: {new, updated blurbs, removed}.
- Preview diff → user confirms → apply.
- Never auto-applies.

### Personal notes (on main app, not admin)

- On any result card: "I went / want to try / pass" picker + 1..5 rating + optional text.
- Notes are per-user (stamped with logged-in `display_name`).
- Shown on cards: "Eli: loved, 7/2026" for each friend with a note.

## Auth

- Single `SHARED_PASSWORD_HASH` env var (bcrypt).
- `/login` page: enter password → on success, user is prompted to pick a name from existing `users` OR type a new one. On submit, creates a signed cookie containing `{user_id, display_name}`. Cookie TTL: 30 days, HttpOnly, Secure, SameSite=Lax.
- Middleware gates all routes except `/login`, `/healthz`, static assets.
- No email, no password reset (shared password; rotate by redeploying with new hash).
- Rate limit: 10 login attempts / IP / hour.

## Testing

### Principles
- Well-tested code is non-negotiable. Err on the side of more tests and more edge-case coverage.
- Every external dependency (Claude, Resy, publications' HTML) is abstracted behind a protocol with a `Fake*` impl used in tests.
- Coverage target: 85%+ on `backend/app/` and `backend/scrapers/`.

### Unit tests (`backend/tests/unit/`)

- **Scrapers**: per-publication test with HTML fixture. Assert parsed output matches snapshot.
- **Resy scraper**: VCR-style recorded fixtures. Tests:
  - Happy path slot normalization.
  - Empty slots.
  - 5xx errors.
  - Venue-not-found.
  - Schema drift (add extra unknown fields, assert parser doesn't break).
  - Correct handling of party size / date / time filter.
- **LLM field extractor**: mocked Claude → canned JSON. Assert prompt contains source text + blurb, and that malformed LLM output is rejected by Pydantic.
- **Merge/dedup**: exhaustive cases (see "Deduplication" above), plus:
  - Three-way merge preserves all three sources.
  - Merging where one is closed → closed wins.
  - Tag union is deduplicated.
  - Price-tier median when sources disagree.
- **SQL shortlist builder**: given filter inputs, assert generated SQL and run against seeded test DB.
- **Availability normalizer**: slot list correctly filtered to ±2hr, limited to 5, sorted.
- **Auth middleware**: unauth → 401; auth with bad cookie → 401; auth with valid cookie → passes.

### Integration tests (`backend/tests/integration/`)

- `POST /api/search`: seeded test DB + mocked Claude stream. Assert SSE events arrive in order, contain expected IDs and blurbs.
- `GET /api/availability`: mocked Resy. Each error branch returns correct status + body.
- `POST /admin/add-by-url`: mocked page fetch + mocked Claude. Assert pre-fill form payload shape.
- `POST /admin/add-by-name`: mocked Resy search + mocked Claude. Assert `venue_id` is attached in response.
- Personal notes CRUD: create / update / delete; verify isolation between users.
- Re-seed diff preview: seed DB, re-run scraper with mutated fixture, assert diff shape.

### E2E (`tests/e2e/`)

- Playwright smoke test: login → fill search form → see streamed results → click "Check availability" → see mocked slots. One test, runs in CI.

### Contract tests (nightly, not blocking CI)

- Real Claude API call with a known prompt, assert response parses.
- Real Resy API call against a known venue, assert slot schema still matches.

## Observability & ops

- **Logging**: structured JSON via `structlog`. Request ID propagated into logs.
- **Error log**: tailed via `fly logs`. No Sentry/Datadog in v1.
- **Health check**: `GET /healthz` returns 200 if DB is reachable.
- **Backups**: nightly cron inside the container gzips `restaurants.db` and uploads to Backblaze B2 (14-day retention).
- **Secrets**: `fly secrets set` for `ANTHROPIC_API_KEY`, `SHARED_PASSWORD_HASH`, `COOKIE_SIGNING_KEY`, `B2_*`.

## Deployment

- `Dockerfile` (multi-stage): build frontend (none needed, static), then Python image with app + migrations.
- `fly.toml`: single machine with `auto_stop_machines = "stop"` and `min_machines_running = 0` (scale to zero when idle). Persistent volume mounted at `/data` for SQLite + backups. First request after idle takes ~2-5s to wake the machine; subsequent requests are instant.
- `migrations/` runs on startup (idempotent; tracked via `schema_versions` table).
- CI (GitHub Actions): on every PR, run ruff + pyright + unit + integration tests.
- Deploy: manual `fly deploy` from local. No auto-deploy on main.

## Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Resy unofficial API changes/breaks | Availability check broken | Nightly contract test alerts; graceful fallback to "book on Resy" link; clean protocol boundary means easy to swap in a patch. |
| Publication HTML changes break scrapers | Re-seed fails for that publication | HTML fixtures + re-record on drift; seeders run on-demand, not ambient; failure doesn't break live app. |
| Claude cost overrun | $ | Haiku 4.5 model (not Sonnet); prompt caching on system prompt; small shortlist inputs; hard cap of 8 results per ranking call. At expected volume, <$1/mo. |
| DB file corruption | Data loss | Nightly backups; DB is git-trackable by file size; can rebuild from `seed/*.json` + notes export. |
| Shared password leak | Unknown friend of friend has access | Rotate password by redeploying new hash; no real harm since no sensitive data; rate-limited login. |
| Stale/closed restaurants | Bad recommendations | Admin "mark closed" is one click; Resy 404 auto-flags; recent publications only. |
| Scope creep during summer | v1 delayed, never shipped | v1 scope locked in this doc; new ideas go to a `docs/superpowers/specs/v2-ideas.md` backlog. |
| Fly cold-start delay on first request | ~2-5s lag on first query after idle | Accepted trade for ~$0-2/mo hosting. If lag becomes annoying, set `min_machines_running = 1` to keep warm at ~$3-5/mo. |
| Haiku ranking quality worse than Sonnet | Less tasteful "why this one" blurbs | `LLM_MODEL` env var allows instant swap to Sonnet; no redeploy of code. |

## Implementation order (rough)

A full plan will be produced by the writing-plans skill. Rough phases for sizing:

1. **Foundation**: repo setup, Dockerfile, fly.toml, CI skeleton, migration runner, bare FastAPI + static frontend.
2. **Auth**: login page, shared password, name picker, cookie middleware, user table.
3. **Data model + seed loader**: migrations, Pydantic models, `import.py`, one fixture seed committed.
4. **First scraper**: Eater 38 Essential, with tests.
5. **Search API (non-streaming)**: SQL shortlist, Claude ranking (non-streaming first), return JSON.
6. **Search UI**: form, result cards, source chips.
7. **Streaming**: convert search to SSE + `<card>` tag parsing.
8. **Availability endpoint + Resy client + fake**: unit tests with fixtures, integration test with FakeResy.
9. **Availability UI**: button on card, inline slot display.
10. **Admin page**: add-by-URL first (most used), then by-name, then edit/remove, then re-seed diff.
11. **Personal notes**: CRUD + UI integration on cards.
12. **Remaining scrapers**: Infatuation, NYT, etc.
13. **Backups + observability + contract tests**.

## Open questions for implementation time (not blocking this spec)

- Exact pricing/rate limits for Anthropic prompt caching at `claude-sonnet-4-6` time of build.
- Whether Resy's unofficial API requires a rotating `x-resy-auth-token` header in 2026; if so, how to obtain.
- Which NY Mag "Where to Eat" list format is current.
- Whether a simple in-memory rate limiter suffices or we need a Redis-backed one.

## Appendix: decisions locked in during brainstorming

| Decision | Chosen | Alternative(s) considered |
|---|---|---|
| End product | AI-powered recommender | Guide / tracker / web app with just filters |
| Data sources | Curated list + LLM knowledge + APIs | Only curated / only LLM |
| Interface | Form + filters + AI summary | Chat / CLI / MCP via Claude.ai |
| Starting list | Seed from publications | Import existing list / go tabula rasa |
| Query types | Neighborhood+filters + reservation-aware | Occasion/vibe, summer-specific |
| Reservation depth | Hybrid — links by default, live scrape on demand | Links only / always scrape / static tags |
| Approach tier | B — full-stack with on-demand scraping | A (static) / C (+ chat concierge) |
| Stack | Python+FastAPI + SQLite + Fly.io | Node+Next.js |
| Users | Shared password, friends included | Just me / real auth |
| Notes model | Per-user | Shared |
| Cuisine model | Tags | Dedicated column |
| Google Places verification | Skip | Use / manual |
| Streaming AI blurbs | Yes | All-at-once |
| Resy venue_id lookup | Auto by name | Require URL paste |
| Auth mechanism | Shared password + name picker | Magic link |
| LLM model | Haiku 4.5 (cheap) | Sonnet 4.6 (smarter, ~5x cost) |
| Fly.io scaling | auto-stop (scale to zero when idle) | always-on machine (~$3-5/mo) |
