import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

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

Intent mapping:
- "Rahul ko 1000 diye" -> lent
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

def parse_expense_text(text: str, current_time_str: str = "") -> list[ParsedTransaction]:
    if not client:
        raise Exception("Gemini API key is missing.")
    
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
    return [ParsedTransaction(**t) for t in parsed_json.get("transactions", [])]

