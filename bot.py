import os
import logging
from threading import Thread
from datetime import datetime, timedelta
from flask import Flask
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMINS = [1849178309, 8286480139]
REQUIRED_CHANNELS = ["Cric_Fantast07","Htr_Edits","Paisa_Looterss","KaalBomber"]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

client = None
users = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        users = client["kaalbomber"]["users"]
    except:
        pass

user_state = {}

def get_user_doc(uid):
    if not users:
        return {}
    doc = users.find_one({"user_id": uid})
    if not doc:
        doc = {"user_id": uid, "points": 0, "referrals": 0, "last_bonus": None, "joined_at": datetime.utcnow()}
        users.insert_one(doc)
    return doc

def update_user_info(user):
    if users:
        users.update_one({"user_id": user.id}, {"$set": {"username": user.username, "first_name": user.first_name}}, upsert=True)

async def is_joined_all(uid, context):
    for ch in REQUIRED_CHANNELS:
        try:
            mem = await context.bot.get_chat_member(f"@{ch}", uid)
            if mem.status in ("left", "kicked"):
                return False
        except:
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    update_user_info(user)
    if context.args and users:
        try:
            ref_id = int(context.args[0].replace("ref_", ""))
            if ref_id != uid and users.find_one({"user_id": ref_id}) and not users.find_one({"user_id": uid}):
                users.update_one({"user_id": ref_id}, {"$inc": {"points": 1, "referrals": 1}})
                users.insert_one({"user_id": uid, "points": 1, "referrals": 0, "referred_by": ref_id, "joined_at": datetime.utcnow()})
        except:
            pass
    if not await is_joined_all(uid, context):
        keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{ch}")] for ch in REQUIRED_CHANNELS]
        keyboard.append([InlineKeyboardButton("Verify Joined", callback_data="verify")])
        await update.message.reply_text("Join all channels to use the bot", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    keyboard = [
        [InlineKeyboardButton("Start 2 Hours Attack", callback_data="bomb")],
        [InlineKeyboardButton("Refer", callback_data="refer"), InlineKeyboardButton("My Stats", callback_data="stats")],
        [InlineKeyboardButton("Buy Points", callback_data="buy_points"), InlineKeyboardButton("Daily Bonus", callback_data="bonus")],
        [InlineKeyboardButton("Top 10", callback_data="top")]
    ]
    if uid in ADMINS:
        keyboard.append([InlineKeyboardButton("Admin Panel", callback_data="admin")])
    await update.message.reply_text("KaaL Bomber - 2 Hours Nuclear Attack\n\nSend 10 digit number after clicking button", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    update_user_info(query.from_user)
    if query.data == "verify":
        if await is_joined_all(uid, context):
            await query.edit_message_text("Verified Successfully! /start")
        else:
            await query.edit_message_text("Join all channels first")
        return
    if query.data == "bomb":
        if get_user_doc(uid).get("points", 0) < 1:
            await query.edit_message_text("You need at least 1 point")
            return
        user_state[uid] = "awaiting_number"
        await query.edit_message_text("Send 10 digit number:")
        return
    if query.data == "refer":
        bot = await context.bot.get_me()
        link = f"https://t.me/{bot.username}?start=ref_{uid}"
        await query.edit_message_text(f"Refers: {get_user_doc(uid).get('referrals', 0)}\n\nYour Link:\n{link}")
        return
    if query.data == "stats":
        doc = get_user_doc(uid)
        await query.edit_message_text(f"Points: {doc.get('points', 0)}")
        return
    if query.data == "top":
        if not users:
            await query.edit_message_text("DB Error")
            return
        top_users = users.find().sort("points", -1).limit(10)
        text = "Top 10 Users\n\n"
        for i, u in enumerate(top_users, 1):
            name = f"@{u.get('username', '')}" if u.get('username') else u.get('first_name', 'User')
            text += f"{i}. {name} → {u.get('points', 0)} pts\n"
        await query.edit_message_text(text)
        return
    if query.data == "bonus":
        doc = users.find_one({"user_id": uid}) if users else {}
        if doc and doc.get("last_bonus") and (datetime.utcnow() - doc["last_bonus"]) < timedelta(hours=24):
            await query.edit_message_text("Already claimed today")
            return
        users.update_one({"user_id": uid}, {"$inc": {"points": 2}, "$set": {"last_bonus": datetime.utcnow()}}, upsert=True)
        await query.edit_message_text("+2 Points Added")
        return
    if query.data == "buy_points":
        await query.message.reply_text("Contact @Undefeatable_Vikash77")
        return
    if query.data == "admin" and uid in ADMINS:
        await query.edit_message_text("/addcredits <id> <amount>")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    if user_state.get(uid) == "awaiting_number":
        if not text.isdigit() or len(text) != 10:
            await update.message.reply_text("Invalid number")
            return
        try:
            users.update_one({"user_id": uid}, {"$inc": {"points": -1}})
        except:
            pass
        user_state.pop(uid, None)
        msg = await update.message.reply_text(f"2 HOURS ATTACK STARTED\nTarget: {text}\nProgress: 0%")
        stages = [(300,"Launching..."),(600,"Dark Servers..."),(1020,"Bypassing..."),(1500,"SMS Flood..."),(2100,"Call Flood..."),(2700,"Heating Device..."),(3300,"Network Down..."),(3900,"Restart Loop..."),(4500,"Battery Dead..."),(5100,"Hanging..."),(5700,"Black Screen..."),(6600,"Final Wave..."),(7200,"TARGET DESTROYED")]
        elapsed = 0
        for t, status in stages:
            await asyncio.sleep(t - elapsed)
            elapsed = t
            perc = int(elapsed/72)
            bar = "█"*(perc//10) + "░"*(10-perc//10)
            try:
                await msg.edit_text(f"2 HOURS ATTACK RUNNING\nTarget: {text}\nElapsed: {elapsed//60}m\nStatus: {status}\n{perc}% {bar}")
            except:
                pass
        await msg.edit_text(f"ATTACK COMPLETED\nTarget: {text}\nDevice: DEAD / BRICKED\nMade with Indian Power")
        return
    elif text.isdigit() and len(text) == 10:
        await update.message.reply_text("Click button first")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = get_user_doc(update.effective_user.id)
    await update.message.reply_text(f"Points: {doc.get('points', 0)}")

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = await context.bot.get_me()
    link = f"https://t.me/{bot.username}?start=ref_{update.effective_user.id}"
    await update.message.reply_text(f"Your Link:\n{link}")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not users:
        await update.message.reply_text("DB Error")
        return
    top_users = users.find().sort("points", -1).limit(10)
    text = "Top 10 Users\n\n"
    for i, u in enumerate(top_users, 1):
        name = f"@{u.get('username', '')}" if u.get('username') else u.get('first_name', 'User')
        text += f"{i}. {name} → {u.get('points', 0)} pts\n"
    await update.message.reply_text(text)

async def addcredits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    try:
        uid = int(context.args[0])
        amt = int(context.args[1])
        users.update_one({"user_id": uid}, {"$inc": {"points": amt}})
        await update.message.reply_text("Done")
    except:
        await update.message.reply_text("Usage: /addcredits id amount")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    if not BOT_TOKEN:
        exit()
    application = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("refer", refer))
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("addcredits", addcredits))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.run_polling(drop_pending_updates=True, poll_interval=1.0, timeout=30, read_timeout=40, write_timeout=40, connect_timeout=40, pool_timeout=40)