import os
import io
import re
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)

from db import (
    upsert_user, save_transaction, get_active_udhaar_transactions,
    soft_delete_latest_transaction, get_month_expense_summary, get_now_ist, KOLKATA_TZ
)
from parser import parse_expense_text, ParsedTransaction
from statement_service import generate_statement_image_for_user

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for conversation
WAITING_FOR_INPUT = 1

# Simple rate limiter (in-memory)
user_message_times = {}

def check_rate_limit(user_id: int) -> bool:
    now = datetime.now().timestamp()
    if user_id not in user_message_times:
        user_message_times[user_id] = []
    
    # Keep only timestamps from the last 60 seconds
    user_message_times[user_id] = [t for t in user_message_times[user_id] if now - t < 60]
    
    if len(user_message_times[user_id]) >= 20:
        return False
        
    user_message_times[user_id].append(now)
    return True

def get_main_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Add Expense", callback_data="add_expense"),
            InlineKeyboardButton("Add Income", callback_data="add_income")
        ],
        [
            InlineKeyboardButton("Split", callback_data="split"),
            InlineKeyboardButton("Who Owes", callback_data="who_owes")
        ],
        [
            InlineKeyboardButton("Monthly Report", callback_data="report"),
            InlineKeyboardButton("📜 Statement", callback_data="stmt_menu")
        ],
        [
            InlineKeyboardButton("Undo", callback_data="undo")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_post_action_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Undo", callback_data="undo"),
            InlineKeyboardButton("Monthly Report", callback_data="report"),
            InlineKeyboardButton("📜 Statement", callback_data="stmt_range_week")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_statement_range_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📅 Aaj", callback_data="stmt_range_today"),
            InlineKeyboardButton("🗓️ Is hafte", callback_data="stmt_range_week")
        ],
        [
            InlineKeyboardButton("📊 Is mahine", callback_data="stmt_range_month"),
            InlineKeyboardButton("⏪ Pichla mahina", callback_data="stmt_range_prev_month")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    upsert_user(user.id, user.full_name)
    
    welcome_msg = (
        f"Namaste {user.mention_html()}! 🙏\n\n"
        f"Main <b>MoneyMate</b> hoon - aapka apna personal AI finance manager. 💼\n\n"
        f"Sirf mujhe text kijiye (e.g. '20 ki water bottle') aur main auto-save kar dunga!"
    )
    await update.message.reply_html(welcome_msg, reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Main Menu:", reply_markup=get_main_menu_keyboard())
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user
    
    if data == "add_expense":
        await query.edit_message_text("Kitne ka aur kya kharcha hua? (e.g. '500 dinner')")
        context.user_data['action'] = 'expense'
        return WAITING_FOR_INPUT
    elif data == "add_income":
        await query.edit_message_text("Kahan se paise aaye? (e.g. 'Salary 50000')")
        context.user_data['action'] = 'income'
        return WAITING_FOR_INPUT
    elif data == "split":
        await query.edit_message_text("Kiske sath split karna hai? (e.g. 'Rahul ko 500 diye movie ke')")
        context.user_data['action'] = 'split'
        return WAITING_FOR_INPUT
    elif data == "who_owes":
        await query.edit_message_text(await calculate_owed(user.id))
        return ConversationHandler.END
    elif data == "report":
        await send_report(query.message, user.id, user.full_name)
        return ConversationHandler.END
    elif data == "undo":
        msg = await perform_undo(user.id)
        await query.edit_message_text(msg)
        return ConversationHandler.END
    elif data == "stmt_menu":
        await query.message.reply_text("Select statement range:", reply_markup=get_statement_range_keyboard())
        return ConversationHandler.END
    elif data.startswith("stmt_range_"):
        r_type = data.replace("stmt_range_", "")
        await send_statement(query.message, user.id, range_type=r_type, as_document=False)
        return ConversationHandler.END
    elif data.startswith("stmt_doc_"):
        r_type = data.replace("stmt_doc_", "")
        await send_statement(query.message, user.id, range_type=r_type, as_document=True)
        return ConversationHandler.END

    return ConversationHandler.END

async def calculate_owed(telegram_id: int) -> str:
    db_user = upsert_user(telegram_id, "User")
    if not db_user:
        return "User not found."
    
    txs = get_active_udhaar_transactions(db_user['id'])
    balances = {}
    for tx in txs:
        person = tx.get("person")
        if not person:
            continue
            
        person = person.title()
        if person not in balances:
            balances[person] = 0
            
        amount = tx["amount"]
        intent = tx["transaction_type"]
        
        if intent == "lent":
            balances[person] += amount
        elif intent == "settle_received":
            balances[person] -= amount
        elif intent == "borrowed":
            balances[person] -= amount
        elif intent == "settle_paid":
            balances[person] += amount
            
    lines = []
    for person, bal in balances.items():
        if abs(bal) > 0.01:
            if bal > 0:
                lines.append(f"• <b>{person}</b> owes you ₹{bal:.2f}")
            else:
                lines.append(f"• You owe <b>{person}</b> ₹{abs(bal):.2f}")
                
    if not lines:
        return "You are all settled up! 🎉"
    return "🤝 <b>Pending Udhaar:</b>\n\n" + "\n".join(lines)

async def owed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await calculate_owed(update.effective_user.id)
    await update.message.reply_html(msg)

async def perform_undo(telegram_id: int) -> str:
    db_user = upsert_user(telegram_id, "User")
    if not db_user:
        return "User not found."
        
    deleted_tx = soft_delete_latest_transaction(db_user['id'])
    if not deleted_tx:
        return "Nothing to undo."
        
    amt = deleted_tx.get('amount', 0)
    cat = deleted_tx.get('category', 'Transaction')
    desc = deleted_tx.get('description', '')
    desc_str = f" ({desc})" if desc else ""
    return f"🗑️ <b>Undone:</b> ₹{amt:.2f} · {cat}{desc_str}"

async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await perform_undo(update.effective_user.id)
    await update.message.reply_html(msg)

async def send_report(message_obj, telegram_id, name):
    db_user = upsert_user(telegram_id, name)
    token = db_user.get("dashboard_token") if db_user else ""
    dashboard_url = os.getenv("DASHBOARD_BASE_URL", "https://moneymate-website.vercel.app").rstrip("/")
    
    if "moneymate-website.vercel.app" in dashboard_url:
        full_url = f"{dashboard_url}/dashboard?token={token}" if token else dashboard_url
    else:
        full_url = f"{dashboard_url}/d/{token}" if token else dashboard_url
    
    total, top_categories = get_month_expense_summary(db_user['id']) if db_user else (0.0, [])
    
    cat_text = ""
    if top_categories:
        cat_lines = [f"• {c}: ₹{a:.2f}" for c, a in top_categories]
        cat_text = "\n\n<b>Top Categories:</b>\n" + "\n".join(cat_lines)
        
    await message_obj.reply_html(
        f"📊 <b>Monthly Summary</b>\n"
        f"Total Spent: <b>₹{total:.2f}</b>"
        f"{cat_text}\n\n"
        f"🔗 <b>Dashboard Link:</b>\n{full_url}\n\n"
        f"💻 <i>Local: http://127.0.0.1:5500/dashboard.html?token={token}</i>"
    )

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_report(update.message, update.effective_user.id, update.effective_user.full_name)

async def send_statement(message_obj, telegram_id: int, range_type: str = "week", as_document: bool = False):
    wait_msg = await message_obj.reply_text("⏳ Generating statement...")
    try:
        db_user = upsert_user(telegram_id, "User")
        if not db_user:
            await wait_msg.edit_text("User account not found.")
            return

        png_bytes, summary_text, count = await generate_statement_image_for_user(db_user["id"], range_type)
        if count == 0 or png_bytes is None:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🗓️ Is hafte", callback_data="stmt_range_week"),
                    InlineKeyboardButton("📊 Is mahine", callback_data="stmt_range_month")
                ],
                [
                    InlineKeyboardButton("⏪ Pichla mahina", callback_data="stmt_range_prev_month")
                ]
            ])
            await wait_msg.edit_text(
                f"❌ <b>Is range me koi entry nahi mili.</b>\nKoi doosri range select karke dekhein:",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return

        buttons = []
        if not as_document:
            buttons.append([InlineKeyboardButton("📄 Original Document (High Quality)", callback_data=f"stmt_doc_{range_type}")])
        
        # Range switcher buttons
        range_buttons = []
        for r_key, r_label in [("today", "📅 Aaj"), ("week", "🗓️ Is hafte"), ("month", "📊 Is mahine"), ("prev_month", "⏪ Pichla")]:
            if r_key != range_type:
                range_buttons.append(InlineKeyboardButton(r_label, callback_data=f"stmt_range_{r_key}"))
        if range_buttons:
            buttons.append(range_buttons)

        reply_markup = InlineKeyboardMarkup(buttons)
        image_io = io.BytesIO(png_bytes)
        filename = f"moneymate_statement_{range_type}.png"
        image_io.name = filename

        try:
            await wait_msg.delete()
        except Exception:
            pass

        if as_document:
            await message_obj.reply_document(
                document=image_io,
                filename=filename,
                caption=summary_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            await message_obj.reply_photo(
                photo=image_io,
                caption=summary_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error generating statement: {e}", exc_info=True)
        await wait_msg.edit_text(f"❌ Statement generate karne me dikkat aayi: {e}")

async def statement_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    r_type = "week"
    if args:
        arg_lower = args[0].lower()
        if arg_lower in ("today", "aaj"):
            r_type = "today"
        elif arg_lower in ("month", "mahina"):
            r_type = "month"
        elif arg_lower in ("prev", "previous", "pichla", "prev_month"):
            r_type = "prev_month"
    await send_statement(update.message, user.id, range_type=r_type, as_document=False)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    text = update.message.text
    text_lower = text.lower().strip()
    
    if text_lower in ("monthly report", "report"):
        await send_report(update.message, user.id, user.full_name)
        return ConversationHandler.END

    # Natural language statement request detection (if message does not contain transaction digits)
    statement_keywords = ["statement", "hisaab", "hisab", "kharcha dikhao", "report image"]
    if any(kw in text_lower for kw in statement_keywords) and not re.search(r'\d+', text):
        r_type = "week"
        if "aaj" in text_lower or "today" in text_lower:
            r_type = "today"
        elif "pichla" in text_lower or "last month" in text_lower or "prev" in text_lower:
            r_type = "prev_month"
        elif "mahina" in text_lower or "month" in text_lower or "mahine" in text_lower:
            r_type = "month"
        await send_statement(update.message, user.id, range_type=r_type, as_document=False)
        return ConversationHandler.END
        
    if not check_rate_limit(user.id):
        await update.message.reply_text("You are sending messages too fast! Limit: 20 per minute.")
        return ConversationHandler.END

    if context.user_data.get('needs_clarification') and context.user_data.get('pending_text'):
        # append the clarification to the original text
        text = context.user_data['pending_text'] + " . Clarification: " + text
        context.user_data['needs_clarification'] = False
        context.user_data['pending_text'] = None

    wait_msg = await update.message.reply_text("⏳ Processing...")
    
    try:
        current_time = get_now_ist().isoformat()
        parsed_list = await asyncio.to_thread(parse_expense_text, text, current_time)
        
        if not parsed_list:
            await wait_msg.edit_text("❌ No transactions found in your message.")
            return ConversationHandler.END
            
        for parsed in parsed_list:
            if parsed.needs_clarification and parsed.question:
                context.user_data['needs_clarification'] = True
                context.user_data['pending_text'] = text
                await wait_msg.edit_text(f"🤔 {parsed.question}")
                return WAITING_FOR_INPUT
            
        db_user = upsert_user(user.id, user.full_name)
        if db_user:
            replies = []
            for parsed in parsed_list:
                tx_data = parsed.model_dump()
                tx_data['transaction_type'] = parsed.intent
                if parsed.person:
                    tx_data['person'] = parsed.person
                save_transaction(db_user['id'], tx_data)
                
                emoji = "🔴" if parsed.intent in ["expense", "lent", "settle_paid"] else "🟢"
                
                dt_str = get_now_ist().strftime("%d %b, %I:%M %p")
                if parsed.date:
                    try:
                        dt_obj = datetime.fromisoformat(parsed.date.replace("Z", "+00:00")).astimezone(KOLKATA_TZ)
                        dt_str = dt_obj.strftime("%d %b, %I:%M %p")
                    except Exception:
                        pass
                
                note_str = f" · {parsed.note}" if parsed.note else ""
                person_str = f" ({parsed.person})" if parsed.person else ""
                replies.append(f"{emoji} ₹{parsed.amount:g} · {parsed.category}{note_str}{person_str} saved - {dt_str}")
            
            reply_text = "\n".join(replies)
            if len(parsed_list) > 1:
                await wait_msg.edit_text(f"✅ Saved {len(parsed_list)} entries:\n\n{reply_text}", reply_markup=get_post_action_keyboard())
            else:
                await wait_msg.edit_text(f"✅ {reply_text}", reply_markup=get_post_action_keyboard())
        else:
            await wait_msg.edit_text("⚠️ Could not initialize user account. Please try /start first.")
        
    except Exception as e:
        logger.error(f"Error parsing: {e}")
        await wait_msg.edit_text("❌ Sorry, I couldn't understand that. Could you rephrase?")
        
    return ConversationHandler.END

def get_application():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found.")
        return None

    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", menu),
            CommandHandler("owed", owed_command),
            CommandHandler("undo", undo_command),
            CommandHandler("report", report_command),
            CommandHandler("statement", statement_command),
            CommandHandler("hisab", statement_command),
            CallbackQueryHandler(button_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
        ],
        states={
            WAITING_FOR_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
            ]
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("menu", menu),
            CommandHandler("owed", owed_command),
            CommandHandler("undo", undo_command),
            CommandHandler("report", report_command),
            CommandHandler("statement", statement_command),
            CommandHandler("hisab", statement_command),
            CallbackQueryHandler(button_handler)
        ]
    )

    application.add_handler(conv_handler)
    return application

def main():
    app = get_application()
    if app:
        logger.info("Starting bot in polling mode...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
