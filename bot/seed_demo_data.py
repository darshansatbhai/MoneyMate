import os
import sqlite3
import uuid
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "moneymate_local.db")

def seed_demo_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Find the primary user (Darshan Satbhai or any user with telegram_id 8261228319)
    cursor.execute("SELECT id, telegram_id, name FROM users WHERE telegram_id = ?", (8261228319,))
    user = cursor.fetchone()
    if not user:
        # Fallback to first user
        cursor.execute("SELECT id, telegram_id, name FROM users LIMIT 1")
        user = cursor.fetchone()

    if not user:
        print("No user found in database to seed!")
        conn.close()
        return

    user_id = user[0]
    print(f"Seeding demo data for user: {user[2]} (id={user_id}, telegram_id={user[1]})")

    # September 2026 (Previous Month) Demo Transactions
    sep_transactions = [
        {"amount": 450.0, "category": "Food", "transaction_type": "expense", "note": "Starbucks Coffee & Croissant", "person": None, "date": "2026-09-02T10:30:00+05:30"},
        {"amount": 1200.0, "category": "Travel", "transaction_type": "expense", "note": "Ola Cab to Airport", "person": None, "date": "2026-09-05T14:15:00+05:30"},
        {"amount": 2800.0, "category": "Food", "transaction_type": "expense", "note": "Barbeque Nation Dinner", "person": None, "date": "2026-09-08T19:40:00+05:30"},
        {"amount": 3000.0, "category": "Udhaar", "transaction_type": "lent", "note": "Emergency udhaar", "person": "Rahul", "date": "2026-09-12T11:00:00+05:30"},
        {"amount": 1499.0, "category": "Shopping", "transaction_type": "expense", "note": "Zara T-Shirt", "person": None, "date": "2026-09-15T16:20:00+05:30"},
        {"amount": 850.0, "category": "Entertainment", "transaction_type": "expense", "note": "PVR Cinema Movie Ticket", "person": None, "date": "2026-09-18T20:10:00+05:30"},
        {"amount": 3200.0, "category": "Bills", "transaction_type": "expense", "note": "Electricity & WiFi Bill", "person": None, "date": "2026-09-21T09:15:00+05:30"},
        {"amount": 1500.0, "category": "Udhaar", "transaction_type": "settle_received", "note": "Rahul ne wapas diye", "person": "Rahul", "date": "2026-09-24T13:30:00+05:30"},
        {"amount": 320.0, "category": "Food", "transaction_type": "expense", "note": "Subway Sub Meal", "person": None, "date": "2026-09-26T18:45:00+05:30"},
        {"amount": 2000.0, "category": "Udhaar", "transaction_type": "lent", "note": "College fees ke liye udhaar", "person": "Amit", "date": "2026-09-28T12:00:00+05:30"},
        {"amount": 650.0, "category": "Travel", "transaction_type": "expense", "note": "Metro Card Recharge & Fuel", "person": None, "date": "2026-09-30T17:15:00+05:30"},
    ]

    # Additional October 2026 (Current Month / This Week) Demo Transactions
    oct_transactions = [
        {"amount": 350.0, "category": "Food", "transaction_type": "expense", "note": "Chai & Samosa office party", "person": None, "date": "2026-10-22T16:30:00+05:30"},
        {"amount": 800.0, "category": "Travel", "transaction_type": "expense", "note": "Uber ride home", "person": None, "date": "2026-10-23T21:15:00+05:30"},
        {"amount": 2500.0, "category": "Shopping", "transaction_type": "expense", "note": "Diwali lightings & decor", "person": None, "date": "2026-10-24T18:20:00+05:30"},
        {"amount": 1200.0, "category": "Food", "transaction_type": "expense", "note": "Dinner with family", "person": None, "date": "2026-10-25T20:45:00+05:30"},
        {"amount": 500.0, "category": "Udhaar", "transaction_type": "lent", "note": "Pooja ko lunch ke paise diye", "person": "Pooja", "date": "2026-10-26T13:10:00+05:30"},
    ]

    all_txs = sep_transactions + oct_transactions
    count = 0

    for tx in all_txs:
        tx_id = str(uuid.uuid4())
        person = tx.get("person") or ""
        note = tx.get("note") or ""
        desc = f"[{person}] {note}".strip() if person else note
        
        cursor.execute(
            '''INSERT INTO transactions (id, user_id, amount, currency, category, transaction_type, person, note, description, created_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (tx_id, user_id, tx["amount"], "INR", tx["category"], tx["transaction_type"], person, note, desc, tx["date"], None)
        )
        count += 1

    conn.commit()
    conn.close()
    print(f"Successfully inserted {count} demo transactions ({len(sep_transactions)} in September, {len(oct_transactions)} in October)!")

if __name__ == "__main__":
    seed_demo_data()
