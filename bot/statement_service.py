import os
import re
import html
import base64
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright, Browser

from db import (
    KOLKATA_TZ,
    get_now_ist,
    get_transactions_in_range,
    get_active_udhaar_transactions,
)

logger = logging.getLogger(__name__)

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "moneymate_statement_template.html")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo-512.png")

# Cache base64 logo
_LOGO_DATA_URI: Optional[str] = None

def get_logo_data_uri() -> str:
    global _LOGO_DATA_URI
    if _LOGO_DATA_URI:
        return _LOGO_DATA_URI
    if os.path.exists(LOGO_PATH):
        try:
            with open(LOGO_PATH, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                _LOGO_DATA_URI = f"data:image/png;base64,{b64}"
                return _LOGO_DATA_URI
        except Exception as e:
            logger.warning(f"Failed to encode logo-512.png: {e}")
    return ""


def format_inr(amount: float) -> str:
    """Format a number into Indian currency representation (e.g. ₹1,00,000, ₹1,079, ₹45.50)."""
    is_neg = amount < 0
    amt = abs(amount)
    paise = round((amt - int(amt)) * 100)
    int_part = int(amt)
    s = str(int_part)
    
    if len(s) > 3:
        last_three = s[-3:]
        other_digits = s[:-3]
        parts = []
        while len(other_digits) > 2:
            parts.append(other_digits[-2:])
            other_digits = other_digits[:-2]
        if other_digits:
            parts.append(other_digits)
        parts.reverse()
        formatted_int = ",".join(parts) + "," + last_three
    else:
        formatted_int = s
        
    if paise > 0:
        res = f"₹{formatted_int}.{paise:02d}"
    else:
        res = f"₹{formatted_int}"
        
    return f"-{res}" if is_neg else res


def get_statement_date_range(range_type: str = "week") -> Tuple[str, str, str]:
    """
    Returns (start_iso, end_iso, period_label) in Asia/Kolkata timezone.
    Options:
    - 'today': Today 00:00:00 to 23:59:59
    - 'week': Last 7 days (including today)
    - 'month': Current month (1st of month to now)
    - 'prev_month': 1st of previous month to end of previous month
    """
    now = get_now_ist()
    
    if range_type == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        period_label = f"Aaj · {now.strftime('%d %b %Y')}"
    elif range_type == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        period_label = now.strftime("%B %Y")
    elif range_type == "prev_month":
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_of_prev = first_of_this_month - timedelta(days=1)
        start = last_of_prev.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = last_of_prev.replace(hour=23, minute=59, second=59, microsecond=999999)
        period_label = start.strftime("%B %Y")
    else:  # default 'week' (last 7 days)
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        if start.year == end.year:
            period_label = f"{start.strftime('%d %b')} – {end.strftime('%d %b %Y')}"
        else:
            period_label = f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"

    return start.isoformat(), end.isoformat(), period_label


def get_statement_data(user_id: str, range_type: str = "week") -> Dict[str, Any]:
    """Query database, compute totals and pending udhaar, and prepare data dict."""
    start_iso, end_iso, period_label = get_statement_date_range(range_type)
    txs = get_transactions_in_range(user_id, start_iso, end_iso)
    
    total_kharcha = 0.0
    given = 0.0
    received = 0.0
    
    for tx in txs:
        amt = float(tx.get("amount", 0.0))
        ttype = tx.get("transaction_type", "expense")
        
        if ttype == "expense":
            total_kharcha += amt
        elif ttype == "lent":
            given += amt
        elif ttype == "settle_paid":
            given += amt
        elif ttype == "settle_received":
            received += amt
        elif ttype == "borrowed":
            received += amt
            
    # Calculate overall pending udhaar for user across all active records
    all_udhaar = get_active_udhaar_transactions(user_id)
    balances: Dict[str, float] = {}
    for tx in all_udhaar:
        person = tx.get("person")
        if not person:
            continue
        person = person.title()
        amt = float(tx.get("amount", 0.0))
        ttype = tx.get("transaction_type")
        
        if person not in balances:
            balances[person] = 0.0
            
        if ttype == "lent":
            balances[person] += amt
        elif ttype == "settle_received":
            balances[person] -= amt
        elif ttype == "borrowed":
            balances[person] -= amt
        elif ttype == "settle_paid":
            balances[person] += amt

    # Net pending: total that others owe user (positive) or user owes (negative)
    net_pending = sum(bal for bal in balances.values() if bal > 0.01)
    
    # Detail list of pending people for the strip
    pending_items = []
    for person, bal in sorted(balances.items(), key=lambda x: abs(x[1]), reverse=True):
        if abs(bal) > 0.01:
            pending_items.append({"person": person, "balance": bal})
            
    now = get_now_ist()
    generated_at = now.strftime("%d %b %Y, %I:%M %p")
    
    return {
        "period": period_label,
        "total_kharcha": format_inr(total_kharcha),
        "given": format_inr(given),
        "received": format_inr(received),
        "pending": format_inr(net_pending),
        "entry_count": len(txs),
        "generated_at": generated_at,
        "transactions": txs,
        "pending_items": pending_items,
    }


ICON_OUT = '<svg viewBox="0 0 24 24" fill="none" stroke="#D8473A" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7M9 7h8v8"/></svg>'
ICON_IN = '<svg viewBox="0 0 24 24" fill="none" stroke="#1E9E5A" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 7 7 17M15 17H7V9"/></svg>'


def build_statement_html(data: Dict[str, Any]) -> str:
    """Populate moneymate_statement_template.html with statement data."""
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Template not found at {TEMPLATE_PATH}")
        
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # 1. Replace logo SVG with real logo if available
    logo_data_uri = get_logo_data_uri()
    if logo_data_uri:
        real_logo_img = f'<img src="{logo_data_uri}" style="width:44px;height:44px;border-radius:12px;object-fit:cover;filter:drop-shadow(0 6px 10px rgba(30,90,200,.18))" alt="Logo">'
        template = template.replace('<svg><use href="#logo"/></svg>', real_logo_img)

    # 2. Add Nirmala UI fallback to font-family for Devanagari support on Windows
    template = template.replace(
        "font-family:'Inter','Noto Sans Devanagari',sans-serif",
        "font-family:'Inter','Noto Sans Devanagari','Nirmala UI',sans-serif"
    )

    # Ensure .d has ellipsis truncation in CSS if not present
    if "overflow:hidden" not in template:
        template = template.replace(
            ".d{font-size:16.5px;font-weight:600;letter-spacing:-.1px}",
            ".d{font-size:16.5px;font-weight:600;letter-spacing:-.1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:530px}"
        )

    # 3. Generate Rows HTML
    txs = data.get("transactions", [])
    display_txs = txs[:10]
    overflow_count = max(0, len(txs) - 10)
    
    row_blocks = []
    for tx in display_txs:
        ttype = tx.get("transaction_type", "expense")
        is_incoming = ttype in ("income", "borrowed", "settle_received")
        
        direction = "in" if is_incoming else "out"
        sign = "+" if is_incoming else "-"
        icon_svg = ICON_IN if is_incoming else ICON_OUT
        
        # Format description
        desc_raw = tx.get("description") or tx.get("note") or tx.get("category") or "Transaction"
        # Truncate if exceptionally long
        if len(desc_raw) > 55:
            desc_raw = desc_raw[:52] + "..."
        desc = html.escape(desc_raw)
        
        cat = html.escape(tx.get("category") or "Other")
        
        # Parse created_at
        created_at_str = tx.get("created_at") or ""
        date_str = ""
        time_str = ""
        try:
            dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=KOLKATA_TZ)
            else:
                dt = dt.astimezone(KOLKATA_TZ)
            date_str = dt.strftime("%d %b")
            time_str = dt.strftime("%I:%M %p")
        except Exception:
            date_str = "—"
            time_str = "—"

        amt_str = format_inr(abs(float(tx.get("amount", 0.0))))

        row_html = (
            f'<div class="row">'
            f'<div class="ic {direction}">{icon_svg}</div>'
            f'<div><div class="d">{desc}</div>'
            f'<div class="m mono">{date_str} · {time_str} · <span>{cat}</span></div></div>'
            f'<div class="a {direction}">{sign}{amt_str}</div>'
            f'</div>'
        )
        row_blocks.append(row_html)

    if overflow_count > 0:
        row_blocks.append(
            f'<div class="row"><div></div><div class="d" style="color:var(--mut);font-weight:500;">+ {overflow_count} aur entries</div><div></div></div>'
        )

    rows_html = "\n  ".join(row_blocks) if row_blocks else '<div class="row"><div></div><div class="d">Koi transaction nahi mila</div><div></div></div>'

    # 4. Generate Pending Strip HTML (up to 2 pending items or combined)
    pending_items = data.get("pending_items", [])
    pending_strips = []
    
    # Show pending items if any exist
    if pending_items:
        # Take up to 2 distinct persons
        for item in pending_items[:2]:
            person = html.escape(item["person"])
            bal = item["balance"]
            if bal > 0.01:
                label = f"{person} se lena baaki hai"
                amt_formatted = format_inr(bal)
            else:
                label = f"{person} ko dena baaki hai"
                amt_formatted = format_inr(abs(bal))
            pending_strips.append(
                f'<div class="pend"><span>{label}</span><b>{amt_formatted} pending</b></div>'
            )
        if len(pending_items) > 2:
            remaining_count = len(pending_items) - 2
            pending_strips.append(
                f'<div class="pend" style="margin-top:6px;font-size:13px;padding:10px 18px;"><span>Aur {remaining_count} logon ka udhaar baaki hai</span><b>/owed check karein</b></div>'
            )

    pending_strip_html = "\n".join(pending_strips)

    # 5. Replace placeholders
    filled = template.replace("{{period}}", str(data.get("period", "")))
    filled = filled.replace("{{total_kharcha}}", str(data.get("total_kharcha", "₹0")))
    filled = filled.replace("{{given}}", str(data.get("given", "₹0")))
    filled = filled.replace("{{received}}", str(data.get("received", "₹0")))
    filled = filled.replace("{{pending}}", str(data.get("pending", "₹0")))
    filled = filled.replace("{{entry_count}}", str(data.get("entry_count", 0)))
    filled = filled.replace("{{generated_at}}", str(data.get("generated_at", "")))

    # Replace ROW block or {{rows_html}}
    if "<!-- ROW_START:" in filled and "<!-- ROW_END -->" in filled:
        pattern = r"<!-- ROW_START:.*?<!-- ROW_END -->(\s*<!-- Optional overflow row.*?-->)?"
        filled = re.sub(pattern, rows_html, filled, flags=re.DOTALL)
    elif "{{rows_html}}" in filled:
        filled = filled.replace("{{rows_html}}", rows_html)

    # Replace PENDING block or {{pending_strip_html}}
    if "<!-- PENDING_START:" in filled and "<!-- PENDING_END -->" in filled:
        pattern = r"<!-- PENDING_START:.*?<!-- PENDING_END -->"
        filled = re.sub(pattern, pending_strip_html, filled, flags=re.DOTALL)
    elif "{{pending_strip_html}}" in filled:
        filled = filled.replace("{{pending_strip_html}}", pending_strip_html)

    return filled


# Persistent browser singleton to optimize performance
_browser_instance: Optional[Browser] = None
_playwright_instance = None

async def get_browser() -> Browser:
    global _browser_instance, _playwright_instance
    if _browser_instance is None or not _browser_instance.is_connected():
        if _playwright_instance is None:
            _playwright_instance = await async_playwright().start()
        _browser_instance = await _playwright_instance.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
    return _browser_instance


async def render_statement_image(html_content: str, output_path: Optional[str] = None) -> bytes:
    """Render HTML to PNG at 820px width with device_scale_factor=2 for retina sharpness."""
    browser = await get_browser()
    context = await browser.new_context(
        viewport={"width": 820, "height": 800},
        device_scale_factor=2
    )
    page = await context.new_page()
    try:
        await page.set_content(html_content, wait_until="networkidle")
        # Give a small moment for embedded fonts to settle
        await page.wait_for_timeout(50)
        png_bytes = await page.screenshot(full_page=True, type="png")
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(png_bytes)
        return png_bytes
    finally:
        await context.close()


async def generate_statement_image_for_user(
    user_id: str,
    range_type: str = "week",
    output_path: Optional[str] = None
) -> Tuple[Optional[bytes], str, int]:
    """
    Generate the statement image for a user.
    Returns: (png_bytes, summary_or_error_msg, entry_count)
    If no entries found, returns (None, 'Is range me koi entry nahi mili.', 0)
    """
    data = get_statement_data(user_id, range_type)
    if data["entry_count"] == 0:
        return None, "Is range me koi entry nahi mili.", 0
        
    html_content = build_statement_html(data)
    png_bytes = await render_statement_image(html_content, output_path=output_path)
    
    period = data["period"]
    total = data["total_kharcha"]
    summary = f"📊 <b>Aapka Statement ({period})</b>\n\nTotal Kharcha: <b>{total}</b>\nEntries: <b>{data['entry_count']}</b>"
    return png_bytes, summary, data["entry_count"]
