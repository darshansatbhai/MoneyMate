"""
MoneyMate Hinglish Financial Parsing Engine
===========================================
A robust, deterministic natural language understanding engine for Indian conversational finance.
Handles Hinglish slang, Hindi spoken numbers, split bills, debt nuances, quantity vs price,
discounts, self-transfers, investments, domestic staff salaries, subscriptions, and multi-item batch messages
without any external API dependency.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

KOLKATA_TZ = ZoneInfo("Asia/Kolkata")

# 1. Spoken Hindi number words to integers
HINDI_NUMBER_WORDS: Dict[str, int] = {
    # Mumbai / Slang Crore & Lakh
    "ek khokha": 10000000,
    "ek crore": 10000000,
    "ek cr": 10000000,
    "ek peti": 100000,
    "das lakh": 1000000,
    "dus lakh": 1000000,
    "panch lakh": 500000,
    "paanch lakh": 500000,
    "dhai lakh": 250000,
    "do lakh": 200000,
    "paune do lakh": 175000,
    "dedh lakh": 150000,
    "sawa lakh": 125000,
    "ek lakh": 100000,
    "aadha lakh": 50000,
    # Thousands
    "pachaas hazaar": 50000,
    "pachas hazaar": 50000,
    "pachaas hazar": 50000,
    "pachas hazar": 50000,
    "challis hazaar": 40000,
    "chaalis hazaar": 40000,
    "tees hazaar": 30000,
    "tees hazar": 30000,
    "bees hazaar": 20000,
    "bees hazar": 20000,
    "pandrah hazaar": 15000,
    "pandrah hazar": 15000,
    "barah hazaar": 12000,
    "barah hazar": 12000,
    "gyarah hazaar": 11000,
    "gyarah hazar": 11000,
    "dus hazaar": 10000,
    "das hazaar": 10000,
    "dus hazar": 10000,
    "das hazar": 10000,
    "nau hazaar": 9000,
    "nau hazar": 9000,
    "aath hazaar": 8000,
    "aath hazar": 8000,
    "saat hazaar": 7000,
    "saat hazar": 7000,
    "chhe hazaar": 6000,
    "che hazaar": 6000,
    "panch hazaar": 5000,
    "paanch hazaar": 5000,
    "panch hazar": 5000,
    "paanch hazar": 5000,
    "char hazaar": 4000,
    "chaar hazaar": 4000,
    "char hazar": 4000,
    "chaar hazar": 4000,
    "teen hazaar": 3000,
    "teen hazar": 3000,
    "paune teen hazaar": 2750,
    "paune teen hazar": 2750,
    "dhai hazaar": 2500,
    "dhai hazar": 2500,
    "sawa do hazaar": 2250,
    "sawa do hazar": 2250,
    "do hazaar": 2000,
    "do hazar": 2000,
    "paune do hazaar": 1750,
    "paune do hazar": 1750,
    "dedh hazaar": 1500,
    "dedh hazar": 1500,
    "sawa hazaar": 1250,
    "sawa hazar": 1250,
    "ek hazaar": 1000,
    "ek hazar": 1000,
    "hazaar": 1000,
    "hazar": 1000,
    # Hundreds & Fractions
    "nau sau": 900,
    "aath sau": 800,
    "saat sau": 700,
    "chhe sau": 600,
    "che sau": 600,
    "panch sau": 500,
    "paanch sau": 500,
    "aadha hazaar": 500,
    "aadha hazar": 500,
    "char sau": 400,
    "chaar sau": 400,
    "teen sau": 300,
    "paune teen sau": 275,
    "dhai sau": 250,
    "dhaisau": 250,
    "sawa do sau": 225,
    "do sau": 200,
    "paune do sau": 175,
    "dedh sau": 150,
    "dedhsau": 150,
    "sawa sau": 125,
    "ek sau": 100,
    "sau": 100,
    "aadha sau": 50,
}

# 2. Comprehensive Category Keyword Mapping
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Travel": [
        "petrol", "diesel", "fuel", "cng", "uber", "ola", "auto", "cab", "metro",
        "bus", "train", "flight", "ticket", "vehicle", "fare", "toll", "rapido", "ride",
        "parking", "puncture", "service", "mechanic", "fastag", "challan", "fine", "car wash", "bike wash"
    ],
    "Food": [
        "chai", "tea", "coffee", "water", "bottle", "khana", "dinner", "lunch", "breakfast",
        "nasta", "nashta", "swiggy", "zomato", "food", "cafe", "restaurant", "burger", "pizza",
        "samosa", "maggi", "maggie", "snack", "snacks", "roti", "doodh", "milk", "biryani", "dhaba",
        "canteen", "ice cream", "paneer", "fruits", "vegetables", "sabji", "momos", "dosa",
        "paratha", "chole bhature", "sweets", "mithai", "cake", "biscuit", "egg", "ande", "curd", "dahi"
    ],
    "Bills": [
        "bijli", "electricity", "light bill", "bill", "recharge", "wifi", "rent", "gas",
        "cylinder", "broadband", "emi", "maintenance", "water bill", "postpaid", "prepaid",
        "jio", "airtel", "vi", "vodafone", "tata play", "dth", "kist", "kisht", "credit card bill",
        "cc bill", "loan payment", "maid", "bai", "cook", "driver", "dhobi", "kamwali", "kaamwali",
        "fees", "tution", "coaching", "school fees", "college fees", "gym fees"
    ],
    "Shopping": [
        "shoes", "shoe", "clothes", "cloth", "kapde", "shirt", "pant", "jeans", "shopping",
        "amazon", "flipkart", "myntra", "dress", "tshirt", "watch", "pantaloons", "zara",
        "h&m", "bag", "chappal", "sandals", "kurta", "saree", "makeup", "cosmetics", "haircut",
        "saloon", "parlour", "spa", "glasses", "chashma"
    ],
    "Health": [
        "medicine", "meds", "medical", "doctor", "hospital", "gym", "pharmacy", "tablet",
        "clinic", "treatment", "dawa", "tests", "blood test", "dentist", "consultation"
    ],
    "Entertainment": [
        "movie", "cinema", "theatre", "netflix", "game", "gaming", "prime", "hotstar",
        "party", "outing", "popcorn", "concert", "show", "club", "pub", "spotify", "youtube premium"
    ],
    "Investment": [
        "sip", "mutual fund", "gold", "shares", "stock", "stocks", "fd", "fixed deposit",
        "crypto", "bitcoin", "ppf", "nps", "invest", "zerodha", "groww", "angelone"
    ],
    "Salary": [
        "salary", "stipend", "bonus", "freelance", "kamai", "earning", "wages"
    ],
    "Cashback": [
        "cashback", "reward", "coupon", "refund"
    ],
    "Other": [
        "mandir", "masjid", "gurudwara", "church", "daan", "donation", "charity",
        "shagun", "lifafa", "kanya pujan", "dakshina", "gift"
    ]
}

# 3. Domestic Staff & Service Provider Roles (Paying them is an EXPENSE, NOT a loan!)
SERVICE_ROLES = [
    "maid", "bai", "cook", "driver", "dhobi", "kamwali", "kaamwali",
    "sweeper", "safaiwala", "guard", "security", "watchman", "electrician",
    "plumber", "mechanic", "barber", "nai", "saloon", "tailor", "pandit",
    "panditji", "doctor", "tutor", "teacher", "milkman", "doodhwala", "paperwala"
]

# 4. Family Members (Receiving money from them is POCKET MONEY / GIFT INCOME)
FAMILY_MEMBERS = [
    "papa", "pitaji", "dad", "father", "mummy", "maa", "mom", "mother",
    "bhai", "brother", "didi", "sister", "chacha", "mama", "tauji", "bhabhi"
]


def normalize_hinglish_text(text: str) -> str:
    """Normalize spoken numbers, shortcuts (50k -> 50000, 1.5L -> 150000), and special characters."""
    res = text.lower()

    # Replace currency symbols with spacing
    res = res.replace("₹", " rs ")

    # Normalize spoken Hindi number words
    for phrase, val in sorted(HINDI_NUMBER_WORDS.items(), key=lambda x: len(x[0]), reverse=True):
        res = re.sub(r'\b' + phrase + r'\b', str(val), res)

    # Normalize '50k' -> 50000, '2.5k' -> 2500
    res = re.sub(r'(\d+(?:\.\d+)?)\s*k\b', lambda m: str(int(float(m.group(1)) * 1000)), res, flags=re.IGNORECASE)

    # Normalize '1.5 lakh' / '2L' / '2 lac' -> 150000 / 200000
    res = re.sub(r'(\d+(?:\.\d+)?)\s*(?:l|lakh|lac|lakhs)\b', lambda m: str(int(float(m.group(1)) * 100000)), res, flags=re.IGNORECASE)

    # Normalize '1.2 cr' / '2 crore'
    res = re.sub(r'(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)\b', lambda m: str(int(float(m.group(1)) * 10000000)), res, flags=re.IGNORECASE)

    return res


def extract_date_context(text: str, base_dt: Optional[datetime] = None) -> Tuple[str, Optional[str]]:
    """Detect relative days (kal, parso, yesterday, aaj) and compute ISO timestamp."""
    now = base_dt or datetime.now(KOLKATA_TZ)
    clean_text = text
    dt_result = None

    # Parso (2 days ago)
    if re.search(r'\b(parso|day before yesterday)\b', text, re.IGNORECASE):
        dt_result = (now - timedelta(days=2)).isoformat()
        clean_text = re.sub(r'\b(parso|day before yesterday)\b', '', clean_text, flags=re.IGNORECASE)
    # Kal / Yesterday (1 day ago)
    elif re.search(r'\b(kal|yesterday)\b', text, re.IGNORECASE):
        dt_result = (now - timedelta(days=1)).isoformat()
        clean_text = re.sub(r'\b(kal|yesterday)\b', '', clean_text, flags=re.IGNORECASE)
    # Aaj / Today
    elif re.search(r'\b(aaj|today)\b', text, re.IGNORECASE):
        dt_result = now.isoformat()
        clean_text = re.sub(r'\b(aaj|today)\b', '', clean_text, flags=re.IGNORECASE)

    return clean_text.strip(), dt_result


def detect_self_transfer(text: str) -> Optional[Dict[str, Any]]:
    """Detect self-account transfers, ATM cash withdrawals, and wallet loads (NOT an expense)."""
    low = text.lower()
    atm_keywords = [
        "atm se", "atm withdrawal", "cash nikale", "cash nikala",
        "atm se nikala", "atm se nikale", "bank se nikale", "bank se cash"
    ]
    wallet_keywords = [
        "wallet me", "paytm me dale", "paytm wallet", "gpay transfer to account",
        "self transfer", "account transfer", "apne account me"
    ]

    is_atm = any(kw in low for kw in atm_keywords)
    is_wallet = any(kw in low for kw in wallet_keywords)

    if is_atm or is_wallet:
        nums = re.findall(r'(\d+(?:\.\d+)?)', low)
        if nums:
            amount = float(nums[0])
            note = "ATM cash withdrawal" if is_atm else "Self account transfer"
            return {
                "intent": "self_transfer",
                "amount": amount,
                "category": "Transfer",
                "person": None,
                "note": note,
                "needs_clarification": False
            }
    return None


def detect_split_bill(text: str, amount: float) -> Tuple[float, str]:
    """
    Detect group expenses with split ('hum 3 log the', 'split among 4', 'hum dono ne share kiya', 'half half').
    """
    low = text.lower()

    # 'hum dono' or 'half half' or '50-50'
    if any(k in low for k in ["hum dono", "dono ne", "half half", "half-half", "50-50", "aadha aadha"]):
        per_person = round(amount / 2, 2)
        return per_person, f" (Shared equally: ₹{per_person:g} each)"

    m = re.search(r'(?:hum\s+)?(\d+)\s*(?:log|people|friends|person|members|dost)\b', low)
    if not m:
        m = re.search(r'split\s+(?:between|among|in)?\s*(\d+)', low)
    if not m:
        m = re.search(r'divided\s+(?:by|in)?\s*(\d+)', low)

    if m:
        count = int(m.group(1))
        if count > 1:
            per_person = round(amount / count, 2)
            return per_person, f" (Split among {count}: ₹{per_person:g} each)"

    return amount, ""


def detect_discount_and_tip(text: str, amount: float) -> Tuple[float, str]:
    """Detect discount reductions ('500 discount mila') or tip additions ('100 tip diya')."""
    low = text.lower()

    # Discount / Coupon / Off
    m_disc = re.search(r'(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:discount|off|kam|bachaye|chhoot|coupon)', low)
    if m_disc:
        disc = float(m_disc.group(1))
        if amount > disc:
            return round(amount - disc, 2), f" (after ₹{disc:g} discount)"

    # Tip / Bakshish
    m_tip = re.search(r'(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:tip|bakshish)', low)
    if m_tip:
        tip = float(m_tip.group(1))
        return round(amount + tip, 2), f" (including ₹{tip:g} tip)"

    return amount, ""


def extract_quantity_and_price(text: str) -> Tuple[Optional[float], str]:
    """Disambiguate quantities ('2 litre', '10 kg', '3 plate', '2 cup') from the actual price."""
    low = text.lower()
    qty_unit_pattern = r'(\d+(?:\.\d+)?)\s*(litre|ltr|l|kg|kilo|gram|gm|plate|packet|pkt|bottle|cup|cutting|glass|piece|pc|ghante|hour|hours|ande|eggs)\b'
    m_qty = re.search(qty_unit_pattern, low)

    qty_str = ""
    if m_qty:
        qty_val, unit = m_qty.group(1), m_qty.group(2)
        qty_str = f"{qty_val} {unit}"
        # Mask quantity digits so they are not picked up as the financial price
        masked = low[:m_qty.start()] + " " * (m_qty.end() - m_qty.start()) + low[m_qty.end():]
    else:
        masked = low

    nums = re.findall(r'(\d+(?:\.\d+)?)', masked)
    if nums:
        return float(nums[0]), qty_str

    return None, qty_str


def classify_category(text: str) -> str:
    """Classify text into categorized bucket using predefined keywords with word boundaries."""
    low = text.lower()
    priority_order = ["Health", "Entertainment", "Travel", "Food", "Shopping", "Investment", "Bills", "Cashback", "Salary", "Other"]
    for cat in priority_order:
        kws = CATEGORY_KEYWORDS.get(cat, [])
        for kw in kws:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, low):
                return cat
    return "Other"


def split_multi_item_message(text: str) -> List[str]:
    """Split multi-transaction sentences into individual parseable chunks."""
    # Split on commas, semicolons, plus signs, or conjunctions ('aur', 'or', 'and', 'phir', 'then', '&')
    parts = re.split(r'[,;+]|\s+(?:aur|or|and|phir|then|&)\s+', text, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def parse_single_chunk(chunk: str, base_dt: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """Parse a single transaction chunk using deterministic logic."""
    raw = chunk.strip()
    if not raw:
        return None

    # Extract date if mentioned
    clean_chunk, dt_iso = extract_date_context(raw, base_dt)
    norm = normalize_hinglish_text(clean_chunk)
    clean_punc = re.sub(r'[!?,.]', ' ', norm)

    # 1. Check Self-Transfer (ATM / Wallet)
    st = detect_self_transfer(clean_punc)
    if st:
        st["date"] = dt_iso
        return st

    # 2. Family pocket money / Gift income:
    # E.g. "Papa ne 5000 bheje", "Mummy ne 2000 diye", "Papa se 5000 mile", "got 500 from mom"
    has_fam = any(re.search(r'\b' + fam + r'\b', clean_punc) for fam in FAMILY_MEMBERS)
    if has_fam and any(w in clean_punc for w in ["diye", "bheje", "mile", "transfer", "pocket money", "got", "received", "from"]):
        nums = re.findall(r'(\d+(?:\.\d+)?)', clean_punc)
        if nums:
            amt = float(nums[0])
            fam_match = next((fam for fam in FAMILY_MEMBERS if re.search(r'\b' + fam + r'\b', clean_punc)), "Family")
            return {
                "intent": "income",
                "amount": amt,
                "category": "Other",
                "person": fam_match.capitalize(),
                "note": f"Gift / Pocket money from {fam_match.capitalize()}",
                "date": dt_iso,
                "needs_clarification": False
            }


    # 3. Domestic Staff & Service Provider Exception (EXPENSE, NOT UDHAAR!):
    # E.g. "Maid ko 2000 diye", "Cook ko 4000 salary di", "Driver ko 500 diye", "Doctor ko 500 fees di"
    is_service_role = any(re.search(r'\b' + role + r'\b', clean_punc) for role in SERVICE_ROLES)
    if is_service_role and any(w in clean_punc for w in ["ko", "diye", "diya", "salary", "fees", "pay kiya"]):
        nums = re.findall(r'(\d+(?:\.\d+)?)', clean_punc)
        if nums:
            amt = float(nums[0])
            matched_role = next((role for role in SERVICE_ROLES if re.search(r'\b' + role + r'\b', clean_punc)), "Service")
            cat = "Health" if matched_role in ["doctor"] else ("Other" if matched_role in ["pandit", "panditji"] else "Bills")
            return {
                "intent": "expense",
                "amount": amt,
                "category": cat,
                "person": None,
                "note": f"{matched_role.capitalize()} payment / fees",
                "date": dt_iso,
                "needs_clarification": False
            }

    # 4. User owes someone (Borrowed / Debt Payable):
    # E.g. "Mujhe pratham ko 7800 dena hai jo baki hai", "pratham ko 7800 dena baaki hai", "pratham ko 7800 lautana hai"
    is_dena = any(k in clean_punc for k in ["dena hai", "dena baaki", "dena baki", "dena tha", "lautana hai", "chukana hai", "owe"])
    if is_dena:
        m_owes = re.search(r'([A-Za-z]+)\s+ko\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?', clean_punc)
        if not m_owes:
            m_owes = re.search(r'(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:to\s+)?([A-Za-z]+)\s+ko', clean_punc)
            if not m_owes:
                m_owes = re.search(r'(?:dena|lautana|chukana)\s+(?:hai\s+)?([A-Za-z]+)\s+ko\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)', clean_punc)
        if m_owes:
            g1, g2 = m_owes.group(1), m_owes.group(2)
            person = g1.capitalize() if not g1.replace('.', '', 1).isdigit() else g2.capitalize()
            amt = float(g2) if not g1.replace('.', '', 1).isdigit() else float(g1)
            return {
                "intent": "borrowed",
                "amount": amt,
                "category": "Other",
                "person": person,
                "note": f"{person} ko dena baaki",
                "date": dt_iso,
                "needs_clarification": False
            }

    # 5. Someone owes user (Lent / Debt Receivable):
    # E.g. "pratham se 7800 lena hai jo baki hai", "pratham se 7800 lena baaki hai", "rahul se vasoolna hai"
    is_lena = any(k in clean_punc for k in ["lena hai", "lena baaki", "lena baki", "lena tha", "vasoolna", "aane baaki"])
    if is_lena:
        m_rec_debt = re.search(r'([A-Za-z]+)\s+(?:se|ko)\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?', clean_punc)
        if not m_rec_debt:
            m_rec_debt = re.search(r'(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*([A-Za-z]+)\s+(?:se|ko)', clean_punc)
        if m_rec_debt:
            g1, g2 = m_rec_debt.group(1), m_rec_debt.group(2)
            person = g1.capitalize() if not g1.replace('.', '', 1).isdigit() else g2.capitalize()
            amt = float(g2) if not g1.replace('.', '', 1).isdigit() else float(g1)
            return {
                "intent": "lent",
                "amount": amt,
                "category": "Other",
                "person": person,
                "note": f"{person} se lena baaki",
                "date": dt_iso,
                "needs_clarification": False
            }

    # 6. Settle Paid (I paid back someone):
    # E.g. "maine Rahul ko 300 wapis diye", "paid back 300 to Rahul", "Rahul ke 500 chukaye"
    m_spaid = re.search(r'(?:maine\s+)?([A-Za-z]+)\s+(?:ko|ke)\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:wapis|wapas|chuka|lauta)', clean_punc)
    if not m_spaid:
        m_spaid = re.search(r'paid\s+back\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:to\s+)?([A-Za-z]+)', clean_punc)
    if m_spaid:
        g1, g2 = m_spaid.group(1), m_spaid.group(2)
        person = g1.capitalize() if not g1.replace('.', '', 1).isdigit() else g2.capitalize()
        amt = float(g2) if not g1.replace('.', '', 1).isdigit() else float(g1)
        return {
            "intent": "settle_paid",
            "amount": amt,
            "category": "Other",
            "person": person,
            "note": f"{person} ko wapis diye",
            "date": dt_iso,
            "needs_clarification": False
        }

    # 7. Settle Received (Someone paid me back):
    # E.g. "Rahul ne 800 wapis diye", "received 800 from Rahul", "Rahul ne 800 lauta diye"
    m_rec = re.search(r'([A-Za-z]+)\s+ne\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:wapis|wapas|lauta)', clean_punc)
    if not m_rec:
        m_rec = re.search(r'received\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*from\s+([A-Za-z]+)', clean_punc)
    if m_rec:
        g1, g2 = m_rec.group(1), m_rec.group(2)
        person = g1.capitalize() if not g1.replace('.', '', 1).isdigit() else g2.capitalize()
        amt = float(g2) if not g1.replace('.', '', 1).isdigit() else float(g1)
        return {
            "intent": "settle_received",
            "amount": amt,
            "category": "Other",
            "person": person,
            "note": f"{person} ne wapis diye",
            "date": dt_iso,
            "needs_clarification": False
        }

    # 8. Borrowed past (I took loan from someone):
    # E.g. "Rahul se 200 liye", "borrowed 200 from Rahul", "Rahul se 500 udhar liye"
    m_bor = re.search(r'([A-Za-z]+)\s+se\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:liye|udhaar)', clean_punc)
    if not m_bor:
        m_bor = re.search(r'borrowed\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*from\s+([A-Za-z]+)', clean_punc)
    if m_bor:
        g1, g2 = m_bor.group(1), m_bor.group(2)
        person = g1.capitalize() if not g1.replace('.', '', 1).isdigit() else g2.capitalize()
        amt = float(g2) if not g1.replace('.', '', 1).isdigit() else float(g1)
        return {
            "intent": "borrowed",
            "amount": amt,
            "category": "Other",
            "person": person,
            "note": f"{person} se udhaar liye",
            "date": dt_iso,
            "needs_clarification": False
        }

    # 9. Lent past (I gave loan to someone):
    # E.g. "Rahul ko 1000 diye", "aaj 1000 Rahul ko diye"
    # Make sure recipient is not a service role!
    m_lent = re.search(r'([A-Za-z]+)\s+ko\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*(?:diye|udhaar|de diye|diya)', clean_punc)
    if not m_lent:
        m_lent = re.search(r'(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:rs|rupees)?\s*([A-Za-z]+)\s+ko\s*(?:diye|udhaar|de diye|diya)', clean_punc)
        if not m_lent:
            m_lent = re.search(r'(?:gave|lent)\s+(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:to\s+)?([A-Za-z]+)', clean_punc)
    if m_lent:
        g1, g2 = m_lent.group(1), m_lent.group(2)
        person_name = g1.lower() if not g1.replace('.', '', 1).isdigit() else g2.lower()
        amt = float(g2) if not g1.replace('.', '', 1).isdigit() else float(g1)
        # Verify not service role
        if person_name not in SERVICE_ROLES:
            return {
                "intent": "lent",
                "amount": amt,
                "category": "Other",
                "person": person_name.capitalize(),
                "note": f"{person_name.capitalize()} ko udhaar",
                "date": dt_iso,
                "needs_clarification": False
            }

    # 10. Clarification if person missing for udhaar:
    if (re.search(r'\b(diye|diya)\s+(?:rs\.?|inr)?\s*(\d+)', clean_punc) or re.search(r'(\d+)\s*(?:diye|diya)', clean_punc)) and not any(k in clean_punc for k in ["ko", "se", "ne"]):
        cat = classify_category(clean_punc)
        is_known_expense = (
            cat != "Other" or
            any(k in clean_punc for k in [
                "chai", "petrol", "bill", "khana", "coffee", "rent", "recharge", "ticket",
                "daan", "mandir", "donation", "charity", "shagun", "lifafa", "dakshina",
                "puja", "pujan", "gift", "masjid", "gurudwara"
            ])
        )
        if not is_known_expense:
            m_num = re.search(r'(\d+(?:\.\d+)?)', clean_punc)
            if m_num:
                return {
                    "intent": "lent",
                    "amount": float(m_num.group(1)),
                    "category": "Other",
                    "person": None,
                    "note": "Udhaar",
                    "date": dt_iso,
                    "needs_clarification": True,
                    "question": "Kisko diye?"
                }


    # 11. Extract Price & Quantity disambiguation
    price, qty_str = extract_quantity_and_price(clean_punc)
    if price is None:
        # Check if user mentioned bill/dinner without amount
        if any(w in clean_punc for w in ["dinner", "lunch", "bill", "kharcha", "shopping", "petrol", "food", "party"]):
            return {
                "intent": "expense",
                "amount": 0.0,
                "category": classify_category(clean_punc),
                "person": None,
                "note": raw,
                "date": dt_iso,
                "needs_clarification": True,
                "question": "Kitne rupaye ka tha?"
            }
        return None

    # 12. Split Bill Detection
    final_amount, split_note = detect_split_bill(clean_punc, price)

    # 13. Discount & Tip Detection (only if not already split)
    if not split_note:
        final_amount, adj_note = detect_discount_and_tip(clean_punc, final_amount)
    else:
        adj_note = ""

    # 14. Build clean description
    desc = re.sub(r'(\d+(?:\.\d+)?)', '', clean_punc)
    desc = re.sub(r'\b(rs|rupees|inr|spent|on|for|ka|ki|ke|bharvaya|diya|diye|purchased|bought|liya|liye|got|received|bhara|bhari|pay|paid|order|ordered)\b', '', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()
    if not desc:
        desc = classify_category(clean_punc)

    full_note = f"{qty_str + ' ' if qty_str else ''}{desc}{split_note}{adj_note}".strip()
    cat = classify_category(clean_punc)

    # 15. Determine Intent: Investment vs Income vs Expense
    if any(w in clean_punc for w in ["sip", "mutual fund", "gold", "fd", "shares", "stocks", "crypto", "invest", "zerodha", "groww"]):
        intent = "investment"
        cat = "Investment"
    elif any(w in clean_punc for w in ["refund", "cashback", "reward", "coupon"]):
        intent = "income"
        cat = "Cashback"
    elif any(w in clean_punc for w in ["salary", "income", "credited", "freelance", "kamaaye", "earning", "wages"]):
        intent = "income"
        cat = "Salary"
    else:
        intent = "expense"

    return {
        "intent": intent,
        "amount": final_amount,
        "category": cat,
        "person": None,
        "note": full_note,
        "date": dt_iso,
        "needs_clarification": False
    }


def parse_hinglish_message(text: str, current_time_str: str = "") -> List[Dict[str, Any]]:
    """
    Main entry point for Hinglish financial natural language processing.
    Handles single transactions, multi-item batch messages, spoken numbers, and split bills.
    """
    if not text or not text.strip():
        return []

    base_dt = None
    if current_time_str:
        try:
            base_dt = datetime.fromisoformat(current_time_str.replace("Z", "+00:00"))
        except Exception:
            base_dt = datetime.now(KOLKATA_TZ)
    else:
        base_dt = datetime.now(KOLKATA_TZ)

    chunks = split_multi_item_message(text)
    results = []

    for chunk in chunks:
        parsed = parse_single_chunk(chunk, base_dt)
        if parsed:
            results.append(parsed)

    return results
