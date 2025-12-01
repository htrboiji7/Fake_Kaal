import os
import logging
from threading import Thread
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Flask to keep Render alive
app = Flask(__name__)
@app.route('/')
def home():
    return "KaaL Bomber Nuclear - 24x7 Live"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMINS = [1849178309, 8286480139]
REQUIRED_CHANNELS = ["Cric_Fantast07", "Htr_Edits", "Paisa_Looterss", "KaalBomber"]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Database
users = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client["kaalbomber"]
        users = db["users"]
    except Exception as e:
        logging.error(f"MongoDB Error: {e}")

user_state = {}
attack_duration = {}

def get_user(uid):
    if not users: return {}
    doc = users.find_one({"user_id": uid})
    if not doc:
        doc = {"user_id": uid, "points": 0, "referrals": 0, "last_bonus": None, "joined_at": datetime.utcnow()}
        users.insert_one(doc)
    return doc

async def is_joined(uid, context):
    for ch in REQUIRED_CHANNELS:
        try:
            mem = await context.bot.get_chat_member(f"@{ch}", uid)
            if mem.status in ("left", "kicked"): return False
        except: return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    if context.args and users:
        try:
            ref_id = int(context.args[0].replace("ref_", ""))
            if ref_id != uid and users.find_one({"user_id": ref_id}) and not users.find_one({"user_id": uid}):
                users.update_one({"user_id": ref_id}, {"$inc": {"points": 1, "referrals": 1}})
                users.insert_one({"user_id": uid, "points": 1, "referrals": 0, "referred_by": ref_id})
        except: pass

    if not await is_joined(uid, context):
        kb = [[InlineKeyboardButton("JOIN CHANNEL", url=f"https://t.me/{ch}")] for ch in REQUIRED_CHANNELS]
        kb.append([InlineKeyboardButton("VERIFY JOINED", callback_data="verify")])
        await update.message.reply_text("Join all required channels first", reply_markup=InlineKeyboardMarkup(kb))
        return

    kb = [
        [InlineKeyboardButton("Start 2 Hours Nuclear Attack", callback_data="bomb")],
        [InlineKeyboardButton("My Stats", callback_data="stats"), InlineKeyboardButton("Refer", callback_data="refer")],
        [InlineKeyboardButton("Daily Bonus", callback_data="bonus"), InlineKeyboardButton("Top 10", callback_data="top")]
    ]
    if uid in ADMINS:
        kb.append([InlineKeyboardButton("Admin Panel", callback_data="admin")]
    await update.message.reply_text("KaaL Bomber 2 Hours Nuclear Attack Ready\nClick button → Send 10 digit number", reply_markup=InlineKeyboardMarkup(kb))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "verify":
        await q.edit_message_text("Verified! Now /start" if await is_joined(uid, context) else "Join all channels")
        return

    if q.data == "bomb":
        if get_user(uid).get("points", 0) < 1:
            await q.edit_message_text("Need at least 1 point")
            return
        user_state[uid] = "awaiting_number"
        await q.edit_message_text("Send 10 digit Indian number:")
        return

    if q.data == "stats":
        doc = get_user(uid)
        await q.edit_message_text(f"Points: {doc.get('points',0)}\nRefers: {doc.get('referrals',0)}")
        return

    if q.data == "refer":
        bot = await context.bot.get_me()
        link = f"https://t.me/{bot.username}?start=ref_{uid}"
        await q.edit_message_text(f"Total Refers: {get_user(uid).get('referrals',0)}\n\nYour Link:\n{link}")
        return

    if q.data == "top":
        if not users:
            await q.edit_message_text("Database error")
            return
        text = "Top 10 Warriors\n\n"
        for i, u in enumerate(users.find().sort("points", -1).limit(10), 1):
            name = f"@{u.get('username')}" if u.get('username') else (u.get('first_name') or "User")
            text += f"{i}. {name} → {u.get('points',0)} pts\n"
        await q.edit_message_text(text)
        return

    if q.data == "bonus":
        doc = users.find_one({"user_id": uid}) if users else {}
        if doc and doc.get("last_bonus") and (datetime.utcnow() - doc["last_bonus"]) < timedelta(hours=24):
            await q.edit_message_text("Already claimed today")
            return
        users.update_one({"user_id": uid}, {"$inc": {"points": 2}, "$set": {"last_bonus": datetime.utcnow()}}, upsert=True)
        await q.edit_message_text("+2 Points Added")
        return

    if q.data == "admin" and uid in ADMINS:
        await q.edit_message_text("/addcredits <id> <amount>\n/broadcast <message>")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    if user_state.get(uid) == "awaiting_number":
        if not text.isdigit() or len(text) != 10:
            await update.message.reply_text("Invalid 10 digit number")
            return

        users.update_one({"user_id": uid}, {"$inc": {"points": -1}})
        user_state.pop(uid, None)

        msg = await update.message.reply_text(f"2 HOURS NUCLEAR ATTACK STARTED\nTarget → {text}\nProgress → 0%")

        stages = [
            (300, "Launching Missiles..."),
            (600, "Connecting Dark Servers..."),
            (1020, "Bypassing OTP Shield..."),
            (1500, "SMS Flood Active..."),
            (2100, "Call Flood Started..."),
            (2700, "Device Heating 80°C..."),
            (3300, "Network Crashed..."),
            (3900, "Restart Loop Active..."),
            (4500, "Battery Explosion..."),
            (5100, "Hanging Phase..."),
            (5700, "Black Screen..."),
            (6600, "Final Wave..."),
            (7200, "TARGET DESTROYED")
        ]

        elapsed = 0
        for t, status in stages:
            await asyncio.sleep(t - elapsed)
            elapsed = t
            perc = int(elapsed / 72)
            bar = "█" * (perc // 10) + "░" * (10 - perc // 10)
            try:
                await msg.edit_text(f"2 HOURS ATTACK RUNNING\nTarget → {text}\nElapsed → {elapsed//60} min\nStatus → {status}\n{perc}% {bar}")
            except: pass

        await msg.edit_text(f"ATTACK COMPLETED\nTarget → {text}\nDevice → DEAD / BRICKED\nMade with Indian Power @KaalBomber")
        return

    elif text.isdigit() and len(text) == 10:
        await update.message.reply_text("Click 'Start 2 Hours Nuclear Attack' button first")

# Admin Commands
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = get_user(update.effective_user.id)
    await update.message.reply_text(f"Points: {doc.get('points',0)}")

async def addcredits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    try:
        uid = int(context.args[0])
        amt = int(context.args[1])
        users.update_one({"user_id": uid}, {"$inc": {"points": amt}})
        await update.message.reply_text("Points added")
    except:
        await update.message.reply_text("Usage: /addcredits id amount")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Usage: /broadcast message")
        return
    sent = 0
    for u in users.find({}, {"user_id": 1}):
        try:
            await context.bot.send_message(u["user_id"], msg)
            sent += 1
            await asyncio.sleep(0.05)
        except: pass
    await update.message.reply_text(f"Sent to {sent} users")

# Main
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    if not BOT_TOKEN:
        print("BOT_TOKEN missing!")
        exit()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("credit", stats_cmd))
    application.add_handler(CommandHandler("addcredits", addcredits))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("KaaL Bomber Started Successfully - Ready for Nuclear Attack!")
    application.run_polling(drop_pending_updates=True)
