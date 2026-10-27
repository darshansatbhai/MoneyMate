import os
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from statement_service import (
    format_inr,
    build_statement_html,
    render_statement_image,
    KOLKATA_TZ,
)

PREVIEW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "preview")
os.makedirs(PREVIEW_DIR, exist_ok=True)

async def test_renders():
    print("Testing format_inr...")
    assert format_inr(0) == "₹0"
    assert format_inr(20) == "₹20"
    assert format_inr(1079) == "₹1,079"
    assert format_inr(100000) == "₹1,00,000"
    assert format_inr(1234567) == "₹12,34,567"
    assert format_inr(45.50) == "₹45.50"
    assert format_inr(-500) == "-₹500"
    print("[OK] format_inr passed!")

    now = datetime.now(KOLKATA_TZ)

    # 1. Test 8 entries (like reference image)
    data_8 = {
        "period": "18 Oct – 24 Oct 2024",
        "total_kharcha": format_inr(3420),
        "given": format_inr(1000),
        "received": format_inr(500),
        "pending": format_inr(500),
        "entry_count": 8,
        "generated_at": now.strftime("%d %b %Y, %I:%M %p"),
        "transactions": [
            {"amount": 450, "transaction_type": "expense", "category": "Food", "description": "Starbucks Coffee & Sandwich", "created_at": (now - timedelta(hours=1)).isoformat()},
            {"amount": 120, "transaction_type": "expense", "category": "Travel", "description": "Uber Auto to Metro", "created_at": (now - timedelta(hours=4)).isoformat()},
            {"amount": 1000, "transaction_type": "lent", "category": "Udhaar", "description": "Rahul ko udhaar diya", "created_at": (now - timedelta(days=1)).isoformat()},
            {"amount": 500, "transaction_type": "settle_received", "category": "Udhaar", "description": "Amit ne wapas diye", "created_at": (now - timedelta(days=1, hours=3)).isoformat()},
            {"amount": 850, "transaction_type": "expense", "category": "Shopping", "description": "Zudio t-shirt", "created_at": (now - timedelta(days=2)).isoformat()},
            {"amount": 350, "transaction_type": "expense", "category": "Entertainment", "description": "Movie ticket PVR", "created_at": (now - timedelta(days=3)).isoformat()},
            {"amount": 1200, "transaction_type": "expense", "category": "Bills", "description": "Electricity Bill", "created_at": (now - timedelta(days=4)).isoformat()},
            {"amount": 450, "transaction_type": "expense", "category": "Food", "description": "Dominos Pizza with friends", "created_at": (now - timedelta(days=5)).isoformat()},
        ],
        "pending_items": [
            {"person": "Rahul", "balance": 1000.0},
            {"person": "Vikram", "balance": -300.0},
        ]
    }
    html_8 = build_statement_html(data_8)
    out_8 = os.path.join(PREVIEW_DIR, "statement_8_entries.png")
    await render_statement_image(html_8, out_8)
    print(f"[OK] Rendered 8 entries to {out_8}")

    # 2. Test 1 entry
    data_1 = {
        "period": "Aaj · " + now.strftime("%d %b %Y"),
        "total_kharcha": format_inr(250),
        "given": format_inr(0),
        "received": format_inr(0),
        "pending": format_inr(0),
        "entry_count": 1,
        "generated_at": now.strftime("%d %b %Y, %I:%M %p"),
        "transactions": [
            {"amount": 250, "transaction_type": "expense", "category": "Food", "description": "Chai and snacks", "created_at": now.isoformat()},
        ],
        "pending_items": []
    }
    html_1 = build_statement_html(data_1)
    out_1 = os.path.join(PREVIEW_DIR, "statement_1_entry.png")
    await render_statement_image(html_1, out_1)
    print(f"[OK] Rendered 1 entry to {out_1}")

    # 3. Test 30 entries (overflow row) + Hindi/Devanagari text + > 1 Lakh amount
    txs_30 = []
    # Hindi descriptions and large amounts
    txs_30.append({"amount": 150000, "transaction_type": "expense", "category": "Bills", "description": "नई बाइक खरीदी (Royal Enfield)", "created_at": now.isoformat()})
    txs_30.append({"amount": 50000, "transaction_type": "lent", "category": "Udhaar", "description": "रोहित को व्यापार के लिए उधार", "created_at": (now - timedelta(hours=2)).isoformat()})
    txs_30.append({"amount": 25000, "transaction_type": "income", "category": "Other", "description": "फ्रीलांस प्रोजेक्ट का भुगतान", "created_at": (now - timedelta(hours=5)).isoformat()})
    txs_30.append({"amount": 350, "transaction_type": "expense", "category": "Food", "description": "हल्दीराम छोले भटूरे", "created_at": (now - timedelta(days=1)).isoformat()})
    txs_30.append({"amount": 1200, "transaction_type": "expense", "category": "Shopping", "description": "Super long description testing text truncation behaviour when user enters a paragraph of text in telegram", "created_at": (now - timedelta(days=1, hours=2)).isoformat()})
    
    for i in range(5, 30):
        txs_30.append({
            "amount": (i + 1) * 50,
            "transaction_type": "expense" if i % 3 != 0 else "lent",
            "category": "Food" if i % 2 == 0 else "Travel",
            "description": f"Expense entry #{i+1}",
            "created_at": (now - timedelta(days=i // 3, hours=i % 12)).isoformat()
        })

    data_30 = {
        "period": "October 2024",
        "total_kharcha": format_inr(158650),
        "given": format_inr(52450),
        "received": format_inr(25000),
        "pending": format_inr(50000),
        "entry_count": len(txs_30),
        "generated_at": now.strftime("%d %b %Y, %I:%M %p"),
        "transactions": txs_30,
        "pending_items": [
            {"person": "रोहित शर्मा", "balance": 50000.0},
            {"person": "प्रिया", "balance": 2450.0},
        ]
    }
    html_30 = build_statement_html(data_30)
    out_30 = os.path.join(PREVIEW_DIR, "statement_30_entries_hindi.png")
    await render_statement_image(html_30, out_30)
    print(f"[OK] Rendered 30 entries (with Hindi & >1 Lakh) to {out_30}")

def test_mock_renders():
    asyncio.run(test_renders())

if __name__ == "__main__":
    test_mock_renders()
