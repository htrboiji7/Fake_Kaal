import os
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient
from datetime import datetime, timedelta
import asyncio
import logging

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is alive"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMINS = [1849178309, 8286480139]
CHANNELS = ["Cric_Fantast07","Htr_Edits","Paisa_Looterss","KaalBomber"]

client = MongoClient(MONGO_URI) if MONGO_URI else None
users = client.kaalbomber.users if client else None

state = {}

async def joined(uid, bot):
    for c in CHANNELS:
        try:
            if (await bot.get_chat_member(f"@{c}", uid)).status in ["left","kicked"]: return False
        except: return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if context.args and users:
        try:
            ref = int(context.args[0].replace("ref_",""))
            if ref != u.id and users.find_one({"user_id":ref}) and not users.find_one({"user_id":u.id}):
                users.update_one({"user_id":ref},{"$inc":{"points":1,"referrals":1}})
                users.insert_one({"user_id":u.id,"points":1,"referrals":0})
        except: pass
    if not await joined(u.id, context.bot):
        kb = [[InlineKeyboardButton("JOIN",url=f"https://t.me/{c}")] for c in CHANNELS]
        kb.append([InlineKeyboardButton("VERIFY",callback_data="verify")])
        await update.message.reply_text("Join all channels",reply_markup=InlineKeyboardMarkup(kb))
        return
    kb = [[InlineKeyboardButton("Start 2 Hours Attack",callback_data="bomb")],
          [InlineKeyboardButton("Stats",callback_data="stats"),InlineKeyboardButton("Refer",callback_data="refer")],
          [InlineKeyboardButton("Bonus",callback_data="bonus"),InlineKeyboardButton("Top",callback_data="top")]]
    await update.message.reply_text("KaaL Bomber Ready",reply_markup=InlineKeyboardMarkup(kb))

async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = q.from_user
    d = q.data
    if d == "verify":
        await q.edit_message_text("Verified! /start" if await joined(u.id,context.bot) else "Join channels")
    elif d == "bomb":
        if users and users.find_one({"user_id":u.id},{"points":1}).get("points",0) < 1:
            await q.edit_message_text("Need 1 point")
            return
        state[u.id] = "wait_num"
        await q.edit_message_text("Send 10 digit number")
    elif d == "stats":
        p = users.find_one({"user_id":u.id},{"points":1,"referrals":1}) or {}
        await q.edit_message_text(f"Points: {p.get('points',0)}\nRefers: {p.get('referrals',0)}")
    elif d == "refer":
        bot = await context.bot.get_me()
        await q.edit_message_text(f"Your link: https://t.me/{bot.username}?start=ref_{u.id}")
    elif d == "bonus":
        doc = users.find_one({"user_id":u.id})
        if doc and doc.get("last_bonus") and (datetime.utcnow()-doc["last_bonus"])<timedelta(hours=24):
            await q.edit_message_text("Already claimed")
            return
        users.update_one({"user_id":u.id},{"$inc":{"points":2},"$set":{"last_bonus":datetime.utcnow()}},upsert=True)
        await q.edit_message_text("+2 Points")
    elif d == "top":
        txt = "Top 10\n\n"
        for i,x in enumerate(users.find().sort("points",-1).limit(10),1):
            name = f"@{x.get('username','')}" if x.get('username') else x.get('first_name','User')
            txt += f"{i}. {name} → {x.get('points',0)} pts\n"
        await q.edit_message_text(txt)

async def msg(update: Update, context):
    u = update.effective_user
    t = update.message.text.strip()
    if state.get(u.id) == "wait_num":
        if not t.isdigit() or len(t)!=10:
            await update.message.reply_text("Invalid number")
            return
        if users: users.update_one({"user_id":u.id},{"$inc":{"points":-1}})
        del state[u.id]
        m = await update.message.reply_text(f"2 HOURS ATTACK STARTED\nTarget: {t}")
        for sec,status in [(300,"Launching..."),(1020,"Bypassing..."),(2100,"Flooding..."),(3300,"Heating..."),(5100,"Hanging..."),(7200,"DESTROYED")]:
            await asyncio.sleep(sec - (sec-300 if sec>300 else 0))
            p = int(sec/72)
            bar = "█"* (p//10) + "░"*(10-p//10)
            try: await m.edit_text(f"ATTACK RUNNING\nTarget: {t}\nStatus: {status}\n{p}% {bar}")
            except: pass
        await m.edit_text(f"ATTACK COMPLETED\nTarget: {t}\nDevice Destroyed")

if __name__ == "__main__":
    Thread(target=run_flask,daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,msg))
    app.run_polling(drop_pending_updates=True)
