import os
import uuid
import sqlite3
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

def get_now_ist() -> datetime:
    return datetime.now(KOLKATA_TZ)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY and SUPABASE_URL != "your_supabase_project_url":
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client: {e}")
        supabase = None

# Local SQLite fallback setup
DB_FILE = os.path.join(os.path.dirname(__file__), "moneymate_local.db")

def init_local_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            dashboard_token TEXT,
            created_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            amount REAL,
            currency TEXT,
            category TEXT,
            transaction_type TEXT,
            person TEXT,
            note TEXT,
            description TEXT,
            created_at TEXT,
            deleted_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_local_db()

def upsert_user(telegram_id: int, name: str) -> dict:
    """Upsert user into Supabase or fallback to local SQLite."""
    # 1. Try Supabase
    if supabase:
        try:
            result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
            if result.data:
                user = result.data[0]
                if not user.get("dashboard_token"):
                    token = str(uuid.uuid4())
                    res = supabase.table("users").update({"dashboard_token": token}).eq("id", user["id"]).execute()
                    if res.data:
                        return res.data[0]
                return user
            
            new_user = {
                "telegram_id": telegram_id,
                "name": name,
                "dashboard_token": str(uuid.uuid4())
            }
            res = supabase.table("users").insert(new_user).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase upsert_user failed ({e}), using local SQLite.")

    # 2. Local SQLite fallback
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, telegram_id, name, dashboard_token, created_at FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    if row:
        user = {"id": row[0], "telegram_id": row[1], "name": row[2], "dashboard_token": row[3], "created_at": row[4]}
        conn.close()
        return user
    
    user_id = str(uuid.uuid4())
    token = str(uuid.uuid4())
    now_str = get_now_ist().isoformat()
    cursor.execute(
        "INSERT INTO users (id, telegram_id, name, dashboard_token, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, telegram_id, name, token, now_str)
    )
    conn.commit()
    conn.close()
    return {"id": user_id, "telegram_id": telegram_id, "name": name, "dashboard_token": token, "created_at": now_str}

def save_transaction(user_id: str, tx_data: dict) -> dict:
    """Save transaction into Supabase or fallback to local SQLite."""
    note = tx_data.get("note", "") or ""
    person = tx_data.get("person", "") or ""
    desc = f"[{person}] {note}".strip() if person else note
    now_str = tx_data.get("date") or get_now_ist().isoformat()
    
    new_tx = {
        "user_id": user_id,
        "amount": float(tx_data.get("amount", 0.0)),
        "currency": "INR",
        "category": tx_data.get("category", "Other") or "Other",
        "transaction_type": tx_data.get("transaction_type", "expense"),
        "description": desc,
        "created_at": now_str
    }

    if supabase:
        try:
            res = supabase.table("transactions").insert(new_tx).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase save_transaction failed ({e}), using local SQLite.")

    # Local SQLite fallback
    tx_id = str(uuid.uuid4())
    new_tx["id"] = tx_id
    new_tx["person"] = person
    new_tx["note"] = note
    new_tx["deleted_at"] = None
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO transactions (id, user_id, amount, currency, category, transaction_type, person, note, description, created_at, deleted_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (tx_id, user_id, new_tx["amount"], new_tx["currency"], new_tx["category"], new_tx["transaction_type"], person, note, desc, now_str, None)
    )
    conn.commit()
    conn.close()
    return new_tx

def get_active_udhaar_transactions(user_id: str) -> list:
    """Get non-deleted udhaar transactions for a user."""
    if supabase:
        try:
            res = supabase.table("transactions").select("*").eq("user_id", user_id).is_("deleted_at", "null").execute()
            if res.data:
                return res.data
        except Exception as e:
            logger.warning(f"Supabase fetch udhaar failed ({e}), checking local SQLite.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT id, user_id, amount, currency, category, transaction_type, person, note, description, created_at, deleted_at
           FROM transactions
           WHERE user_id = ? AND deleted_at IS NULL''',
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    txs = []
    for r in rows:
        person = r[6]
        desc = r[8] or ""
        if not person and desc.startswith("[") and "]" in desc:
            person = desc[1:desc.index("]")]
        txs.append({
            "id": r[0], "user_id": r[1], "amount": r[2], "currency": r[3],
            "category": r[4], "transaction_type": r[5], "person": person,
            "note": r[7], "description": desc, "created_at": r[9], "deleted_at": r[10]
        })
    return txs

def soft_delete_latest_transaction(user_id: str) -> dict:
    """Soft delete the user's latest transaction (set deleted_at)."""
    now_iso = get_now_ist().isoformat()
    if supabase:
        try:
            res = supabase.table("transactions").select("*").eq("user_id", user_id).is_("deleted_at", "null").order("created_at", desc=True).limit(1).execute()
            if res.data:
                tx = res.data[0]
                supabase.table("transactions").update({"deleted_at": now_iso}).eq("id", tx['id']).execute()
                return tx
        except Exception as e:
            logger.warning(f"Supabase soft_delete failed ({e}), checking local SQLite.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT id, amount, category, description, transaction_type
           FROM transactions
           WHERE user_id = ? AND deleted_at IS NULL
           ORDER BY created_at DESC LIMIT 1''',
        (user_id,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None

    tx_id = row[0]
    cursor.execute("UPDATE transactions SET deleted_at = ? WHERE id = ?", (now_iso, tx_id))
    conn.commit()
    conn.close()
    return {"id": row[0], "amount": row[1], "category": row[2], "description": row[3], "transaction_type": row[4]}

def get_month_expense_summary(user_id: str) -> tuple[float, list[tuple[str, float]]]:
    """Calculate total spent and top 3 categories for the current month."""
    now = get_now_ist()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    txs = []
    if supabase:
        try:
            res = supabase.table("transactions").select("*").eq("user_id", user_id).eq("transaction_type", "expense").is_("deleted_at", "null").gte("created_at", start_of_month).execute()
            if res.data:
                txs = res.data
        except Exception as e:
            logger.warning(f"Supabase get_month_expense_summary failed ({e}), checking local SQLite.")

    if not txs:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT amount, category FROM transactions
               WHERE user_id = ? AND transaction_type = 'expense' AND deleted_at IS NULL AND created_at >= ?''',
            (user_id, start_of_month)
        )
        rows = cursor.fetchall()
        conn.close()
        txs = [{"amount": r[0], "category": r[1]} for r in rows]

    total = sum(float(tx['amount']) for tx in txs)
    cat_totals = {}
    for tx in txs:
        cat = tx.get('category') or 'Other'
        cat_totals[cat] = cat_totals.get(cat, 0.0) + float(tx['amount'])
        
    top_categories = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:3]
    return total, top_categories

def get_transactions_in_range(user_id: str, start_iso: str, end_iso: str) -> list[dict]:
    """Get active transactions in a date range, newest first."""
    if supabase:
        try:
            res = (
                supabase.table("transactions")
                .select("*")
                .eq("user_id", user_id)
                .is_("deleted_at", "null")
                .gte("created_at", start_iso)
                .lte("created_at", end_iso)
                .order("created_at", desc=True)
                .execute()
            )
            if res.data:
                return res.data
        except Exception as e:
            logger.warning(f"Supabase get_transactions_in_range failed ({e}), checking local SQLite.")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT id, user_id, amount, currency, category, transaction_type, person, note, description, created_at, deleted_at
           FROM transactions
           WHERE user_id = ? AND deleted_at IS NULL AND created_at >= ? AND created_at <= ?
           ORDER BY created_at DESC''',
        (user_id, start_iso, end_iso)
    )
    rows = cursor.fetchall()
    conn.close()

    txs = []
    for r in rows:
        person = r[6]
        desc = r[8] or ""
        if not person and desc.startswith("[") and "]" in desc:
            person = desc[1:desc.index("]")]
        txs.append({
            "id": r[0], "user_id": r[1], "amount": float(r[2]), "currency": r[3],
            "category": r[4], "transaction_type": r[5], "person": person,
            "note": r[7], "description": desc, "created_at": r[9], "deleted_at": r[10]
        })
    return txs

