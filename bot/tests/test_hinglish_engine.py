"""
Tests for MoneyMate Hinglish Financial Engine
============================================
Comprehensive test suite validating deterministic NLP for Indian conversational finance.
"""

import os
import sys
import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from hinglish_engine import (
    parse_hinglish_message,
    normalize_hinglish_text,
    detect_split_bill,
    detect_discount_and_tip,
    extract_quantity_and_price,
    classify_category,
    detect_self_transfer,
    KOLKATA_TZ
)

def test_hindi_spoken_numbers():
    res = parse_hinglish_message("dedh sau ki coffee")[0]
    assert res["amount"] == 150
    assert res["category"] == "Food"
    assert res["intent"] == "expense"

    res = parse_hinglish_message("dhai hazaar ka restaurant bill")[0]
    assert res["amount"] == 2500
    assert res["category"] == "Food"

    res = parse_hinglish_message("sawa sau ka recharge")[0]
    assert res["amount"] == 125
    assert res["category"] == "Bills"

    res = parse_hinglish_message("ek lakh car service")[0]
    assert res["amount"] == 100000
    assert res["category"] == "Travel"

def test_slang_k_l_notation():
    res = parse_hinglish_message("50k salary aayi")[0]
    assert res["amount"] == 50000
    assert res["intent"] == "income"
    assert res["category"] == "Salary"

    res = parse_hinglish_message("2.5k petrol bharwaya")[0]
    assert res["amount"] == 2500
    assert res["category"] == "Travel"

def test_split_bill_detection():
    # 4 people
    res = parse_hinglish_message("Dinner 1200 hum 4 log the")[0]
    assert res["amount"] == 300
    assert "Split among 4" in res["note"]

    # 2 people sharing
    res = parse_hinglish_message("Auto 120 hum dono ne share kiya")[0]
    assert res["amount"] == 60
    assert "Shared equally" in res["note"]

    # Split among 3
    res = parse_hinglish_message("Goa hotel 9000 split among 3")[0]
    assert res["amount"] == 3000

def test_discount_and_tip():
    # Discount
    res = parse_hinglish_message("2000 ke shoes 400 discount mila")[0]
    assert res["amount"] == 1600
    assert res["category"] == "Shopping"
    assert "discount" in res["note"]

    # Tip
    res = parse_hinglish_message("500 dinner 50 tip di")[0]
    assert res["amount"] == 550
    assert "tip" in res["note"]

def test_quantity_vs_price():
    # 2 litre petrol 210 rs -> price 210, not 2
    res = parse_hinglish_message("2 litre petrol 210 rs")[0]
    assert res["amount"] == 210
    assert "2 litre" in res["note"]
    assert res["category"] == "Travel"

    # 5 kg aata 220
    res = parse_hinglish_message("5 kg aata 220 ka")[0]
    assert res["amount"] == 220
    assert "5 kg" in res["note"]

    # 2 plate momos 120
    res = parse_hinglish_message("2 plate momos 120")[0]
    assert res["amount"] == 120
    assert "2 plate" in res["note"]

def test_domestic_staff_salary_not_udhaar():
    # Maid ko 2500 diye -> Expense, NOT Udhaar lent!
    res = parse_hinglish_message("Maid ko 2500 diye")[0]
    assert res["intent"] == "expense"
    assert res["amount"] == 2500
    assert res["category"] == "Bills"
    assert res["person"] is None

    # Cook ko 4000 salary di
    res = parse_hinglish_message("Cook ko 4000 salary di")[0]
    assert res["intent"] == "expense"
    assert res["amount"] == 4000

    # Driver ko 500 diye
    res = parse_hinglish_message("Driver ko 500 diye")[0]
    assert res["intent"] == "expense"
    assert res["amount"] == 500

def test_family_gift_and_pocket_money():
    # Papa ne 5000 bheje -> Income
    res = parse_hinglish_message("Papa ne 5000 bheje")[0]
    assert res["intent"] == "income"
    assert res["amount"] == 5000
    assert res["person"].lower() == "papa"

    # Mummy ne 2000 diye -> Income
    res = parse_hinglish_message("Mummy ne 2000 diye")[0]
    assert res["intent"] == "income"
    assert res["amount"] == 2000
    assert res["person"].lower() == "mummy"

def test_self_transfer_atm():
    # ATM cash withdrawal -> self_transfer
    res = parse_hinglish_message("ATM se 2000 nikale")[0]
    assert res["intent"] == "self_transfer"
    assert res["amount"] == 2000
    assert res["category"] == "Transfer"

    # Wallet load
    res = parse_hinglish_message("Paytm wallet me 1000 dale")[0]
    assert res["intent"] == "self_transfer"
    assert res["amount"] == 1000

def test_emi_and_loans():
    res = parse_hinglish_message("Bike ki emi 3200 bhari")[0]
    assert res["intent"] == "expense"
    assert res["amount"] == 3200
    assert res["category"] == "Bills"

    res = parse_hinglish_message("Credit card bill 8500 pay kiya")[0]
    assert res["intent"] == "expense"
    assert res["amount"] == 8500
    assert res["category"] == "Bills"

def test_subscriptions():
    res = parse_hinglish_message("Netflix recharge 649")[0]
    assert res["intent"] == "expense"
    assert res["amount"] == 649
    assert res["category"] == "Entertainment"

    res = parse_hinglish_message("Spotify premium 119")[0]
    assert res["intent"] == "expense"
    assert res["amount"] == 119
    assert res["category"] == "Entertainment"

def test_rituals_and_donations():
    res = parse_hinglish_message("Mandir me daan 101 diya")[0]
    assert res["intent"] == "expense"
    assert res["amount"] == 101
    assert res["category"] == "Other"

    res = parse_hinglish_message("Shagun ka lifafa 501 diya")[0]
    assert res["intent"] == "expense"
    assert res["amount"] == 501

def test_investments():
    res = parse_hinglish_message("Groww SIP 2000 kata")[0]
    assert res["intent"] == "investment"
    assert res["amount"] == 2000
    assert res["category"] == "Investment"

    res = parse_hinglish_message("Gold 5000 ka kharida")[0]
    assert res["intent"] == "investment"
    assert res["amount"] == 5000

def test_multi_item_batch():
    batch = parse_hinglish_message("100 petrol, 20 chai aur 350 lunch")
    assert len(batch) == 3
    assert batch[0]["amount"] == 100
    assert batch[0]["category"] == "Travel"
    assert batch[1]["amount"] == 20
    assert batch[1]["category"] == "Food"
    assert batch[2]["amount"] == 350
    assert batch[2]["category"] == "Food"

def test_udhaar_dena_vs_lena():
    # User owes someone (Borrowed / Liability):
    res = parse_hinglish_message("Mujhe pratham ko 7800 dena hai jo baki hai !")[0]
    assert res["intent"] == "borrowed"
    assert res["amount"] == 7800
    assert res["person"].lower() == "pratham"

    # Someone owes user (Lent / Asset):
    res = parse_hinglish_message("pratham se 7800 lena hai jo baki hai !")[0]
    assert res["intent"] == "lent"
    assert res["amount"] == 7800
    assert res["person"].lower() == "pratham"

    # Settle paid
    res = parse_hinglish_message("maine Rahul ko 300 wapis diye")[0]
    assert res["intent"] == "settle_paid"
    assert res["amount"] == 300
    assert res["person"].lower() == "rahul"

    # Settle received
    res = parse_hinglish_message("Rahul ne 800 wapis diye")[0]
    assert res["intent"] == "settle_received"
    assert res["amount"] == 800
    assert res["person"].lower() == "rahul"

def test_relative_date_resolution():
    ref_time = datetime(2026, 10, 27, 12, 0, 0, tzinfo=KOLKATA_TZ)
    ref_iso = ref_time.isoformat()

    # Kal (1 day ago)
    res = parse_hinglish_message("kal 200 ka petrol", current_time_str=ref_iso)[0]
    assert res["amount"] == 200
    assert res["date"] is not None
    dt = datetime.fromisoformat(res["date"])
    assert (ref_time.date() - dt.date()).days == 1

    # Parso (2 days ago)
    res = parse_hinglish_message("parso 500 dinner", current_time_str=ref_iso)[0]
    assert res["amount"] == 500
    assert res["date"] is not None
    dt = datetime.fromisoformat(res["date"])
    assert (ref_time.date() - dt.date()).days == 2
