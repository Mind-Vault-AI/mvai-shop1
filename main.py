
import os, json, sqlite3
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", "8788"))
DB_PATH = os.getenv("DB_PATH", "./wallet.db")
JSON_PATH = os.getenv("JSON_PATH", "../mindvaultai_bundles_psp.json")

app = FastAPI()

# DB setup
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  credits INTEGER NOT NULL DEFAULT 0,
  lots_bonus INTEGER NOT NULL DEFAULT 0
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS processed_events (
  event_id TEXT PRIMARY KEY,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
conn.commit()

with open(JSON_PATH, "r", encoding="utf-8") as f:
    pricing = json.load(f)

def find_bundle_by_amount(amount: float, tol: float = 0.01):
    for b in pricing["bundles"]:
        if abs(b["price_eur"] - amount) <= tol:
            return b
    return None

def credit_user(user_id: str, bundle: dict, event_id: str):
    # idempotency
    cur.execute("SELECT event_id FROM processed_events WHERE event_id = ?", (event_id,))
    if cur.fetchone():
        return {"status": "ignored", "reason": "duplicate_event"}
    cur.execute("INSERT INTO processed_events (event_id) VALUES (?)", (event_id,))

    # ensure user
    cur.execute("INSERT OR IGNORE INTO users (id, credits, lots_bonus) VALUES (?, 0, 0)", (user_id,))

    cur.execute("UPDATE users SET credits = credits + ?, lots_bonus = lots_bonus + ? WHERE id = ?", (bundle["credits"], bundle["bonus_lots"], user_id))
    conn.commit()

    cur.execute("SELECT id, credits, lots_bonus FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    return {"status": "ok", "user": {"id": user[0], "credits": user[1], "lots_bonus": user[2]}, "bundle": bundle}

class CryptoWebhook(BaseModel):
    eventId: str
    userId: str
    amount: float
    currency: str | None = "EUR"
    txId: str | None = None

@app.post("/webhook/crypto")
async def webhook_crypto(payload: CryptoWebhook):
    # TODO: verify on-chain tx signature / RPC
    b = find_bundle_by_amount(payload.amount)
    if not b:
        raise HTTPException(status_code=400, detail="no matching bundle")
    result = credit_user(payload.userId, b, payload.eventId)
    return {"ok": True, "result": result}

@app.post("/webhook/mollie")
async def webhook_mollie(req: Request):
    body = await req.json()
    # TODO: verify with Mollie API + signature, fetch payment by id and confirm status paid
    event_id = body.get("id")
    metadata = body.get("metadata", {}) or {}
    user_id = metadata.get("userId")
    amount = float(((body.get("amount") or {}).get("value")) or 0)
    b = find_bundle_by_amount(amount)
    if not (event_id and user_id and b):
        raise HTTPException(status_code=400, detail="invalid webhook payload")
    result = credit_user(user_id, b, event_id)
    return {"ok": True, "result": result}

@app.post("/webhook/paypal")
async def webhook_paypal(req: Request):
    body = await req.json()
    # TODO: verify with PayPal webhook signature headers
    event_id = body.get("id")
    resource = body.get("resource") or {}
    user_id = resource.get("custom_id")
    amount = float(((resource.get("amount") or {}).get("value")) or 0)
    b = find_bundle_by_amount(amount)
    if not (event_id and user_id and b):
        raise HTTPException(status_code=400, detail="invalid webhook payload")
    result = credit_user(user_id, b, event_id)
    return {"ok": True, "result": result}

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    cur.execute("SELECT id, credits, lots_bonus FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        return {}
    return {"id": row[0], "credits": row[1], "lots_bonus": row[2]}
