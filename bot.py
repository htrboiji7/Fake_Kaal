import os, logging, asyncio
from threading import Thread
from datetime import datetime, timedelta
from flask import Flask, send_file
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from io import BytesIO

app = Flask(__name__)
@app.route('/') 
def home(): return "Ultra Advanced KaaL Bomber Running"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMINS = [1849178309, 8286480139]
CHANNELS = ["Cric_Fantast07","Htr_Edits","Paisa_Looterss","KaalBomber"]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

db = None
if MONGO_URI:
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
        db = client.kaalbomber
        users = db.users
        attacks = db.attacks
        banned = db.banned
    except: pass

user_state = {}
attack_mode = {}

def get_user(uid):
    if not db: return {}
    doc = users.find_one({"user_id": uid})
    if not doc:
        doc = {"user_id": uid, "points": 0, "referrals": 0, "last_bonus": None, "joined_at": datetime.utcnow()}
        users.insert_one(doc)
    return doc

async def is_joined(uid, context):
    for ch in CHANNELS:
        try:
            m = await context.bot.get_chat_member(f"@{ch}", uid)
            if m.status in ("left", "kicked"): return False
        except: return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if context.args and db:
        try:
            ref = int(context.args[0].replace("ref_",""))
            if ref != u.id and users.find_one({"user_id": ref}) and not users.find_one({"user_id": u.id}):
                users.update_one({"user_id": ref}, {"$inc": {"points": 1, "referrals": 1}})
                users.insert_one({"user_id": u.id, "points": 1, "referrals": 0, "referred_by": ref})
        except: pass
    
    if not await is_joined(u.id, context):
        kb = [[InlineKeyboardButton("JOIN", url=f"https://t.me/{c}")] for c in CHANNELS]
        kb.append([InlineKeyboardButton("VERIFY", callback_data="verify")])
        await update.message.reply_text("Join all channels first", reply_markup=InlineKeyboardMarkup(kb))
        return
    
    kb = [
        [InlineKeyboardButton("30 Min Attack", callback_data="mode_30"), InlineKeyboardButton("1 Hour Attack", callback_data="mode_60")],
        [InlineKeyboardButton("2 Hours Attack", callback_data="mode_120"), InlineKeyboardButton("4 Hours Attack", callback_data="mode_240")],
        [InlineKeyboardButton("My Stats", callback_data="stats"), InlineKeyboardButton("History", callback_data="history")],
        [InlineKeyboardButton("Refer", callback_data="refer"), InlineKeyboardButton("Daily Bonus", callback_data="bonus")],
        [InlineKeyboardButton("Top 10", callback_data="top")]
    ]
    if u.id in ADM: kb.append([InlineKeyboardButton("Admin Panel", callback_data="admin")])
    await update.message.reply_text("Ultra Advanced KaaL Bomber Ready", reply_markup=InlineKeyboardMarkup(kb))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if data == "verify":
        await q.edit_message_text("Verified! /start" if await is_joined(uid, context) else "Join all channels")
        return

    if data.startswith("mode_"):
        mins = int(data.split("_")[1])
        if get_user(uid).get("points",0) < 1:
            await q.edit_message_text("Need 1 point")
            return
        attack_mode[uid] = mins
        user_state[uid] = "awaiting_number"
        await q.edit_message_text(f"Selected {mins} min attack\nSend 10 digit number")
        return

    if data == "history":
        hist = list(attacks.find({"user_id": uid}).sort("time", -1).limit(5))
        if not hist:
            await q.edit_message_text("No attack history")
            return
        txt = "Last 5 Attacks\n\n"
        for a in hist:
            txt += f"{a['target']} → {a['duration']} min ({a['time'].strftime('%d/%m %H:%M')})\n"
        await q.edit_message_text(txt)
        return

    if data == "stats":
        doc = get_user(uid)
        await q.edit_message_text(f"Points: {doc.get('points',0)}\nRefers: {doc.get('referrals',0)}")
        return

    if data == "top":
        text = "Top 10 Warriors\n\n"
        for i, u in enumerate(users.find().sort("points", -1).limit(10), 1):
            name = f"@{u.get('username')}" if u.get('username') else (u.get('first_name') or "User")
            text += f"{i}. {name} → {u.get('points',0)} pts\n"
        await q.edit_message_text(text)
        return

    if data == "bonus":
        doc = users.find_one({"user_id": uid})
        if doc and doc.get("last_bonus") and (datetime.utcnow() - doc["last_bonus"]) < timedelta(hours=24):
            await q.edit_message_text("Already claimed today")
            return
        users.update_one({"user_id": uid}, {"$inc": {"points": 2}, "$set": {"last_bonus": datetime.utcnow()}}, upsert=True)
        await q.edit_message_text("+2 Points Added")
        return

    if data == "admin" and uid in ADM:
        await q.edit_message_text("/broadcast text\n/ban id\n/unban id\n/addcredits id amount")
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    if banned.find_one({"user_id": uid}):
        await update.message.reply_text("You are banned")
        return

    if user_state.get(uid) == "awaiting_number":
        if not text.isdigit() or len(text) != 10:
            await update.message.reply_text("Invalid number")
            return
        mins = attack_mode.get(uid, 120)
        users.update_one({"user_id": uid}, {"$inc": {"points": -1}})
        user_state.pop(uid, None)
        attack_mode.pop(uid, None)

        msg = await update.message.reply_text(f"{mins} MIN ATTACK STARTED\nTarget → {text}")
        attacks.insert_one({"user_id": uid, "target": text, "duration": mins, "time": datetime.utcnow()})

        total_sec = mins * 60
        stages = 12
        elapsed = 0
        for sec, status in stages:
            await asyncio.sleep(sec - elapsed)
            elapsed = sec
            perc = int(elapsed / total_sec * 100)
            bar = "█"*(perc//10) + "░"*(10-perc//10)
            try:
                await msg.edit_text(f"{mins} MIN ATTACK RUNNING\nTarget → {text}\nStatus → {status}\n{perc}% {bar}")
            except: pass

        pdf_buffer = BytesIO()
        pdf_buffer.write(f"KaaL Bomber Attack Report\n\nTarget: {text}\nDuration: {mins} minutes\nTime: {datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC')}\nStatus: SUCCESSFULLY DESTROYED".encode())
        pdf_buffer.seek(0)
        await msg.edit_text("ATTACK COMPLETED - Device Destroyed")
        await update.message.reply_document(InputFile(pdf_buffer, filename=f"Attack_Report_{text}.txt"), caption="Your Attack Report")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADM: return
    message = " ".join(context.args)
    if not message: 
        await update.message.reply_text("Usage: /broadcast text")
        return
    sent = 0
    for u in users.find({}, {"user_id": 1}):
        try:
            await context.bot.send_message(u["user_id"], message)
            sent += 1
            await asyncio.sleep(0.05)
        except: pass
    await update.message.reply_text(f"Broadcast sent to {sent} users")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADM: return
    try:
        uid = int(context.args[0])
        banned.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)
        await update.message.reply_text("User banned")
    except: await update.message.reply_text("Usage: /ban id")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADM: return
    try:
        uid = int(context.args[0])
        banned.delete_one({"user_id": uid})
        await update.message.reply_text("User unbanned")
    except: await update.message.reply_text("Usage: /unban id")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    if not BOT_TOKEN: exit()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling(drop_pending_updates=True)
