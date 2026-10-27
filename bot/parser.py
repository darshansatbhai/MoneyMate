import os
import re
import json
import logging
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

class ParsedTransaction(BaseModel):
    intent: str = Field(description="One of: expense, income, lent, borrowed, settle_received, settle_paid")
    amount: float = Field(description="The numeric amount of the transaction")
    category: str = Field(description="Category: Food, Travel, Bills, Shopping, Health, Entertainment, Other")
    person: Optional[str] = Field(None, description="Person involved if it is an udhaar/settlement transaction")
    note: Optional[str] = Field(None, description="Short description of the transaction")
    date: Optional[str] = Field(None, description="ISO 8601 timestamp (YYYY-MM-DDTHH:MM:SS) if the user mentions a specific date like yesterday, kal, or a specific day. Null if today/no date mentioned.")
    needs_clarification: bool = Field(False, description="True if vital info is missing (like amount)")
    question: Optional[str] = Field(None, description="Question to ask if clarification is needed")

class ParsedTransactionList(BaseModel):
    transactions: list[ParsedTransaction] = Field(description="List of extracted transactions")

SYSTEM_INSTRUCTION = """
You are a highly intelligent financial parsing assistant. Extract ALL transaction details from the user's message.
Respond strictly in JSON matching the schema, returning a list of transactions. Use the provided "Current Time Context" to resolve relative dates like "kal", "parso", "yesterday", or specific dates to absolute ISO 8601 timestamps.

Categories: Food, Travel, Bills, Shopping, Health, Entertainment, Other

- "Rahul ko 1000 diye" -> lent
- "Mujhe Rahul ko 1000 dena hai jo baki hai" / "Rahul ko 1000 dena hai" -> borrowed (User owes Rahul)
- "Rahul se 1000 lena hai jo baki hai" / "Rahul se 1000 lena hai" -> lent (Rahul owes user)
- "Rahul ne 800 wapis diye" -> settle_received
- "maine Rahul ko 300 wapis diye" -> settle_paid
- "Rahul se 200 liye" -> borrowed
- Buying something, paying for service -> expense
- Salary, getting money (not a loan) -> income

Examples:
1. "20 ki water bottle"
   {"transactions": [{"intent": "expense", "amount": 20, "category": "Food", "note": "water bottle", "needs_clarification": false, "date": null}]}
2. "kal uber 300 or aaj khana 200" (Context: 2024-10-08)
   {"transactions": [
     {"intent": "expense", "amount": 300, "category": "Travel", "note": "uber", "needs_clarification": false, "date": "2024-10-07T12:00:00"},
     {"intent": "expense", "amount": 200, "category": "Food", "note": "khana", "needs_clarification": false, "date": "2024-10-08T12:00:00"}
   ]}
3. "mere pass total philhal 1120 rs hai . okay usme se 620 online hai and baki 500 cash hai"
   {"transactions": [{"intent": "income", "amount": 1120, "category": "Other", "note": "initial balance", "needs_clarification": false, "date": null}]}
4. "diye 500"
   {"transactions": [{"intent": "lent", "amount": 500, "category": "Other", "needs_clarification": true, "question": "Kisko diye?", "date": null}]}
5. "1st ko 100 ka petrol, 2nd ko 200 ki coffee" (Context: Oct 2024)
   {"transactions": [
     {"intent": "expense", "amount": 100, "category": "Travel", "note": "petrol", "needs_clarification": false, "date": "2024-10-01T12:00:00"},
     {"intent": "expense", "amount": 200, "category": "Food", "note": "coffee", "needs_clarification": false, "date": "2024-10-02T12:00:00"}
   ]}
6. "dinner ka bill diya"
   {"transactions": [{"intent": "expense", "amount": 0, "category": "Food", "note": "dinner", "needs_clarification": true, "question": "Kitne ka bill tha?", "date": null}]}
"""

CATEGORY_KEYWORDS = {
    "Travel": ["petrol", "diesel", "fuel", "cng", "uber", "ola", "auto", "cab", "metro", "bus", "train", "flight", "ticket", "vehicle", "fare", "toll", "rapido", "ride"],
    "Food": ["chai", "tea", "coffee", "water", "bottle", "khana", "dinner", "lunch", "breakfast", "nasta", "nashta", "swiggy", "zomato", "food", "cafe", "restaurant", "burger", "pizza", "samosa", "maggi", "snack", "snacks", "roti", "doodh", "milk", "biryani", "dhaba", "canteen"],
    "Bills": ["bijli", "electricity", "light bill", "bill", "recharge", "wifi", "rent", "gas", "cylinder", "broadband", "emi", "maintenance", "water bill"],
    "Shopping": ["shoes", "shoe", "clothes", "cloth", "kapde", "shirt", "pant", "jeans", "shopping", "amazon", "flipkart", "myntra", "dress", "tshirt", "watch", "pantaloons", "zara", "h&m"],
    "Health": ["medicine", "meds", "medical", "doctor", "hospital", "gym", "pharmacy", "tablet", "clinic", "fees", "treatment", "medicine", "dawa"],
    "Entertainment": ["movie", "cinema", "theatre", "netflix", "game", "gaming", "prime", "hotstar", "ticket", "party", "outing", "popcorn"],
}

def guess_category(text: str) -> str:
    text_low = text.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in text_low for kw in kws):
            return cat
    return "Other"

def fallback_regex_parser(text: str, current_time_str: str = "") -> list[ParsedTransaction]:
    """Smart offline regex fallback that handles standard Hinglish/English transactions."""
    raw = text.strip()
    low = raw.lower()

    clean = re.sub(r'[!?,.]', ' ', low)

    # 1. User owes someone: 'Mujhe pratham ko 7800 dena hai jo baki hai', 'pratham ko 7800 dena baaki hai'
    # Keywords: dena hai, dena baaki, dena baki, dena tha, lautana hai, chukana hai
    is_dena = any(k in clean for k in ["dena hai", "dena baaki", "dena baki", "dena tha", "lautana hai", "chukana hai", "owe"])
    if is_dena:
        m_owes = re.search(r'([A-Za-z]+)\s+ko\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?', clean)
        if not m_owes:
            m_owes = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:to\s+)?([A-Za-z]+)\s+ko', clean)
            if m_owes:
                amt, person = float(m_owes.group(1)), m_owes.group(2).capitalize()
                return [ParsedTransaction(intent="borrowed", amount=amt, category="Other", person=person, note=f"{person} ko dena baaki")]
        else:
            person, amt = m_owes.group(1).capitalize(), float(m_owes.group(2))
            return [ParsedTransaction(intent="borrowed", amount=amt, category="Other", person=person, note=f"{person} ko dena baaki")]

    # 2. Someone owes user: 'pratham se 7800 lena hai jo baki hai', 'pratham se 7800 lena baaki hai'
    # Keywords: lena hai, lena baaki, lena baki, lena tha, vasoolna
    is_lena = any(k in clean for k in ["lena hai", "lena baaki", "lena baki", "lena tha", "vasoolna"])
    if is_lena:
        m_rec_debt = re.search(r'([A-Za-z]+)\s+(?:se|ko)\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?', clean)
        if not m_rec_debt:
            m_rec_debt = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*([A-Za-z]+)\s+(?:se|ko)', clean)
            if m_rec_debt:
                amt, person = float(m_rec_debt.group(1)), m_rec_debt.group(2).capitalize()
                return [ParsedTransaction(intent="lent", amount=amt, category="Other", person=person, note=f"{person} se lena baaki")]
        else:
            person, amt = m_rec_debt.group(1).capitalize(), float(m_rec_debt.group(2))
            return [ParsedTransaction(intent="lent", amount=amt, category="Other", person=person, note=f"{person} se lena baaki")]

    # 3. Settle Paid: 'maine Rahul ko 300 wapis diye' / 'paid back 300 to Rahul'
    m_spaid = re.search(r'maine\s+([A-Za-z]+)\s+ko\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:wapis|wapas|chuka)', clean)
    if not m_spaid:
        m_spaid = re.search(r'paid\s+back\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:to\s+)?([A-Za-z]+)', clean)
        if m_spaid:
            amt, person = float(m_spaid.group(1)), m_spaid.group(2).capitalize()
            return [ParsedTransaction(intent="settle_paid", amount=amt, category="Other", person=person, note=f"{person} ko wapis diye")]
    else:
        person, amt = m_spaid.group(1).capitalize(), float(m_spaid.group(2))
        return [ParsedTransaction(intent="settle_paid", amount=amt, category="Other", person=person, note=f"{person} ko wapis diye")]

    # 4. Settle Received: 'Rahul ne 800 wapis diye' / 'received 800 from Rahul'
    m_rec = re.search(r'([A-Za-z]+)\s+ne\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:wapis|wapas|diye)', clean)
    if not m_rec:
        m_rec = re.search(r'received\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*from\s+([A-Za-z]+)', clean)
        if m_rec:
            amt, person = float(m_rec.group(1)), m_rec.group(2).capitalize()
            return [ParsedTransaction(intent="settle_received", amount=amt, category="Other", person=person, note=f"{person} ne wapis diye")]
    else:
        person, amt = m_rec.group(1).capitalize(), float(m_rec.group(2))
        return [ParsedTransaction(intent="settle_received", amount=amt, category="Other", person=person, note=f"{person} ne wapis diye")]

    # 5. Borrowed: 'Rahul se 200 liye' / 'borrowed 200 from Rahul'
    m_bor = re.search(r'([A-Za-z]+)\s+se\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:liye|udhaar)', clean)
    if not m_bor:
        m_bor = re.search(r'borrowed\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*from\s+([A-Za-z]+)', clean)
        if m_bor:
            amt, person = float(m_bor.group(1)), m_bor.group(2).capitalize()
            return [ParsedTransaction(intent="borrowed", amount=amt, category="Other", person=person, note=f"{person} se udhaar liye")]
    else:
        person, amt = m_bor.group(1).capitalize(), float(m_bor.group(2))
        return [ParsedTransaction(intent="borrowed", amount=amt, category="Other", person=person, note=f"{person} se udhaar liye")]

    # 6. Lent: 'Rahul ko 1000 diye' / 'aaj 1000 Rahul ko diye' / 'gave 1000 to Rahul'
    m_lent = re.search(r'([A-Za-z]+)\s+ko\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:diye|udhaar|de diye|diya)', clean)
    if not m_lent:
        m_lent = re.search(r'(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*([A-Za-z]+)\s+ko\s*(?:diye|udhaar|de diye|diya)', clean)
        if not m_lent:
            m_lent = re.search(r'(?:gave|lent)\s+(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:to\s+)?([A-Za-z]+)', clean)
            if m_lent:
                amt, person = float(m_lent.group(1)), m_lent.group(2).capitalize()
                return [ParsedTransaction(intent="lent", amount=amt, category="Other", person=person, note=f"{person} ko udhaar")]
        else:
            amt, person = float(m_lent.group(1)), m_lent.group(2).capitalize()
            return [ParsedTransaction(intent="lent", amount=amt, category="Other", person=person, note=f"{person} ko udhaar")]
    else:
        person, amt = m_lent.group(1).capitalize(), float(m_lent.group(2))
        return [ParsedTransaction(intent="lent", amount=amt, category="Other", person=person, note=f"{person} ko udhaar")]

    # 7. Clarification for Lent if person missing: 'diye 500'
    if (re.search(r'\b(diye|diya)\s+(?:₹|rs\.?|inr)?\s*(\d+)', clean) or re.search(r'(\d+)\s*(?:diye|diya)', clean)) and not any(k in clean for k in ["ko", "se", "ne"]):
        m_num = re.search(r'(\d+(?:\.\d+)?)', clean)
        if m_num:
            return [ParsedTransaction(intent="lent", amount=float(m_num.group(1)), category="Other", needs_clarification=True, question="Kisko diye?")]

    # 6. Extract Amount
    all_nums = re.findall(r'(\d+(?:\.\d+)?)', low)
    if not all_nums:
        # Check if item mentioned without amount
        if any(w in low for w in ["dinner", "lunch", "bill", "kharcha", "shopping", "petrol", "food", "party"]):
            return [ParsedTransaction(intent="expense", amount=0.0, category=guess_category(low), note=raw, needs_clarification=True, question="Kitne rupaye ka tha?")]
        return []

    amount = float(all_nums[0])

    # Clean description
    desc = re.sub(r'(\d+(?:\.\d+)?)', '', low)
    desc = re.sub(r'\b(rs|rupees|inr|spent|on|for|ka|ki|ke|bharvaya|diya|diye|purchased|bought|liya|liye|got)\b', '', desc)
    desc = re.sub(r'[₹/,\-]', '', desc).strip()
    if not desc:
        desc = guess_category(low)

    cat = guess_category(low)
    intent = "income" if any(w in low for w in ["salary", "income", "credited", "freelance", "kamaaye", "got", "received"]) else "expense"
    
    return [ParsedTransaction(intent=intent, amount=amount, category=cat, note=desc, needs_clarification=False)]


def parse_expense_text(text: str, current_time_str: str = "") -> list[ParsedTransaction]:
    """Parse natural expense text via Gemini AI, with instant fallback to smart regex parser."""
    # 1. Try Gemini if client is initialized
    if client:
        try:
            prompt = f"Current Time Context (Resolve dates relative to this): {current_time_str}\n\nUser Message: {text}"
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=ParsedTransactionList,
                    temperature=0.0
                ),
            )
            parsed_json = json.loads(response.text)
            txs = [ParsedTransaction(**t) for t in parsed_json.get("transactions", [])]
            if txs:
                return txs
        except Exception as e:
            logger.warning(f"Gemini API request failed ({e}). Seamlessly engaging smart regex fallback parser...")

    # 2. Smart Regex Fallback (100% resilient offline / quota exceeded)
    fallback_txs = fallback_regex_parser(text, current_time_str)
    if fallback_txs:
        return fallback_txs

    return []
