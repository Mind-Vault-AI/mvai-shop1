# MindVault-AI Payments - Copilot Instructions

## Architecture Snapshot
- `main.py` hosts the entire FastAPI app; keeping new logic co-located or extracting into helpers under `app/` keeps routing readable.
- Startup loads `mindvaultai_bundles_psp.json` into memory once and reuses it via `find_bundle_by_amount`; honor this pattern to avoid disk reads per request.
- SQLite (`wallet.db`) is opened globally with `check_same_thread=False`; reuse the module-level `conn/cur` rather than creating new connections.
- Idempotency + crediting are centralized in `credit_user`, so any new payment surface should funnel through it to avoid duplicated logic.

## Runtime & Configuration
- Environment variables: `PORT` (default 8788), `DB_PATH` (defaults to `./wallet.db`), `JSON_PATH` (defaults to `../mindvaultai_bundles_psp.json`). Always wire new scripts/tests to respect these so deployments can override paths.
- `.env` is loaded via `python-dotenv`; mirror keys there when running locally.
- The JSON catalog must contain `bundles` entries with `price_eur`, `credits`, `bonus_lots`. If you relocate the file, update `JSON_PATH` instead of hard-coding new paths.

## Request Flow Patterns
- `/webhook/crypto` receives a typed `CryptoWebhook`; mimic this Pydantic model style for any new body that needs validation.
- `/webhook/mollie` and `/webhook/paypal` accept raw JSON (`Request`) because payload shapes vary. They both extract `event_id`, `user_id`, `amount` then call `credit_user`; keep this 3-step pattern (verify, map, credit).
- `find_bundle_by_amount` uses a +/- 0.01 EUR tolerance; reuse/extend this helper when matching GAAP rounding issues instead of manual comparisons.

## Data & Idempotency Guarantees
- Tables: `users(id, credits, lots_bonus)` and `processed_events(event_id, created_at)`. Any schema migration must preserve these names or update every query string.
- `processed_events` is the sole idempotency gate. Always insert the event before crediting and roll back on failure; otherwise duplicate webhooks will double-credit.
- `credit_user` performs `INSERT OR IGNORE` for users, then atomic `UPDATE`. New credit types should expand this function rather than bypassing it.

## Developer Workflow
- Run API locally with `uvicorn main:app --reload --port ${PORT:-8788}` after `pip install -r requirements.txt` (FastAPI + uvicorn + dotenv + pydantic only).
- Tests use pytest (`tests/test_basic.py` currently trivial). Add scenario tests there; no other harnesses exist.
- SQLite file is created on first boot; delete `wallet.db` when you need a clean slate while iterating.

## Extension Tips
- Security TODOs are marked at each webhook (signature / provider verification). Keep TODO comments visible and sandwich new code there so reviewers can spot pending work.
- When adding providers, prefer new `/webhook/<provider>` handlers that normalize into `{event_id,user_id,amount}` and call `credit_user`.
- If you need background jobs (e.g., reconciliation) place them in new modules but import them inside `main.py` to avoid circular imports in FastAPI startup.
