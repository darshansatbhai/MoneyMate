import os
import sys
import pytest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from statement_service import format_inr, get_statement_date_range, build_statement_html, KOLKATA_TZ

def test_format_inr():
    assert format_inr(0) == "₹0"
    assert format_inr(25) == "₹25"
    assert format_inr(1079) == "₹1,079"
    assert format_inr(100000) == "₹1,00,000"
    assert format_inr(1234567) == "₹12,34,567"
    assert format_inr(99.99) == "₹99.99"
    assert format_inr(-1500) == "-₹1,500"

def test_get_statement_date_range():
    start, end, label = get_statement_date_range("today")
    assert "Aaj" in label
    assert start < end

    start_w, end_w, label_w = get_statement_date_range("week")
    assert start_w < end_w

    start_m, end_m, label_m = get_statement_date_range("month")
    assert start_m < end_m

def test_build_statement_html():
    now = datetime.now(KOLKATA_TZ)
    sample_data = {
        "period": "Test Period",
        "total_kharcha": "₹1,500",
        "given": "₹500",
        "received": "₹200",
        "pending": "₹300",
        "entry_count": 2,
        "generated_at": now.strftime("%d %b %Y, %I:%M %p"),
        "transactions": [
            {"amount": 1000, "transaction_type": "expense", "category": "Food", "description": "Dinner", "created_at": now.isoformat()},
            {"amount": 500, "transaction_type": "lent", "category": "Udhaar", "description": "Rahul ko diya", "created_at": now.isoformat()}
        ],
        "pending_items": [
            {"person": "Rahul", "balance": 500.0}
        ]
    }
    html = build_statement_html(sample_data)
    assert "Test Period" in html
    assert "₹1,500" in html
    assert "Dinner" in html
    assert "Rahul se lena baaki hai" in html
    assert "₹500 pending" in html
