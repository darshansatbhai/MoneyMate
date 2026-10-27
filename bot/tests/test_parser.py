import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from parser import parse_expense_text, ParsedTransaction

def parse_single(text: str) -> ParsedTransaction:
    res = parse_expense_text(text)
    return res[0] if isinstance(res, list) else res

def test_expense_basic():
    res = parse_single("20 ki water bottle")
    assert res.intent == "expense"
    assert res.amount == 20
    assert res.category == "Food"

def test_expense_english():
    res = parse_single("spent 500 on dinner")
    assert res.intent == "expense"
    assert res.amount == 500
    assert res.category == "Food"

def test_lent():
    res = parse_single("aaj 1000 Rahul ko diye")
    assert res.intent == "lent"
    assert res.amount == 1000
    assert res.person.lower() == "rahul"

def test_settle_received():
    res = parse_single("Rahul ne 800 wapis diye")
    assert res.intent == "settle_received"
    assert res.amount == 800
    assert res.person.lower() == "rahul"

def test_settle_paid():
    res = parse_single("maine Rahul ko 300 wapis diye")
    assert res.intent == "settle_paid"
    assert res.amount == 300
    assert res.person.lower() == "rahul"

def test_borrowed():
    res = parse_single("Rahul se 200 liye")
    assert res.intent == "borrowed"
    assert res.amount == 200
    assert res.person.lower() == "rahul"

def test_income():
    res = parse_single("salary aayi 50000")
    assert res.intent == "income"
    assert res.amount == 50000

def test_travel():
    res = parse_single("uber 300")
    assert res.intent == "expense"
    assert res.amount == 300
    assert res.category == "Travel"

def test_shopping():
    res = parse_single("shopping ki pantaloons se 2500")
    assert res.intent == "expense"
    assert res.amount == 2500
    assert res.category == "Shopping"

def test_bills():
    res = parse_single("bijli bill 1200")
    assert res.intent == "expense"
    assert res.amount == 1200
    assert res.category == "Bills"

def test_health():
    res = parse_single("medical fees 500")
    assert res.intent == "expense"
    assert res.amount == 500
    assert res.category == "Health"

def test_entertainment():
    res = parse_single("movie 300")
    assert res.intent == "expense"
    assert res.amount == 300
    assert res.category == "Entertainment"

def test_needs_clarification():
    res = parse_single("dinner ka bill diya")
    assert res.intent == "expense"
    assert res.needs_clarification is True
    assert res.question is not None

def test_needs_clarification_person():
    res = parse_single("diye 500")
    assert res.intent == "lent"
    assert res.needs_clarification is True
    assert res.question is not None

def test_complex():
    res = parse_single("got 500 from mom")
    assert res.intent in ["income", "borrowed"]
    assert res.amount == 500
