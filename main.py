import asyncio
import sqlite3
import logging
import os
import sys
import time
from datetime import datetime
from threading import Thread
from flask import Flask # New Import for Web Server

from telethon import TelegramClient, events, Button, functions, types
from telethon.sessions import StringSession
from telethon.errors import (
    AlreadyInConversationError, 
    SessionPasswordNeededError, 
    FloodWaitError, 
    PhoneNumberInvalidError
)

# --- [ CONFIGURATION & SECURITY ] ---
API_ID = 30424148 
API_HASH = '55204cd683c7754c5e9eb114752172cd'
BOT_TOKEN = '8422844316:AAFDuxgi_pA-FVLAXNaFbZHmlUHYtLLaKak'

ADMIN_IDS = [8052601632, 7429081031, 5208805573] 
CHANNEL_LINK = "https://t.me/+ycSwWt2wFJ1kYjY9"

# Render par Home directory access nahi hoti kabhi-kabhi, isliye current folder use karein
DB_PATH = "xirus_master_pro.db" 

# Logging Level set to Error for Termux speed
logging.basicConfig(level=logging.ERROR)
bot = TelegramClient('xirus_core', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- [ ASSETS & STYLING ] ---
POWERED_BY = f"**[\u1d2b\u026a\u1d1b\1d1cs \u1d0d\u1d0f\u1d05\u1d22]({CHANNEL_LINK})**"

def style(text):
    if not text: return ""
    a = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    b = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
    return text.translate(str.maketrans(a, b))

# --- [ WEB SERVER FOR RENDER (KEEP ALIVE) ] ---
app = Flask('')

@app.route('/')
def home():
    return "Xirus Modz Bot is Running 24/7!"

def run_http():
    # Render automatically assigns a PORT via environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- [ CORE DATABASE ARCHITECTURE ] ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS accounts (
        phone TEXT PRIMARY KEY,
        owner_id INTEGER,
        username TEXT,
        session_str TEXT,
        reply_msg TEXT,
        status INTEGER DEFAULT 1,
        added_on TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# --- [ GLOBAL ENGINE MANAGER ] ---
active_sessions = {} 

async def start_auto_reply_engine(phone, session_str, reply_text):
    if phone in active_sessions:
        try: await active_sessions[phone].disconnect()
        except: pass

    try:
        # Loop argument remove kiya kyunki Telethon naye versions me internal loop use karta hai
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        active_sessions[phone] = client
        
        await client.connect()
        if not await client.is_user_authorized(): return

        @client.on(events.NewMessage(incoming=True))
        async def engine_handler(event):
            if not event.is_private: return
            sender = await event.get_sender()
            if not sender or sender.bot: return

            with sqlite3.connect(DB_PATH) as conn:
                data = conn.execute("SELECT status, reply_msg FROM accounts WHERE phone=?", (phone,)).fetchone()
                if data and data[0] == 1:
                    try:
                        full = await client(functions.users.GetFullUserRequest('me'))
                        if not isinstance(full.users[0].status, types.UserStatusOnline):
                            await event.reply(f"{data[1]}\n\n{POWERED_BY}", link_preview=False)
                    except FloodWaitError as f: await asyncio.sleep(f.seconds)
                    except: pass
        
        # Async task ke andar run_until_disconnected blocking ho sakta hai, isliye ise background task banaya
        # Note: Telethon background tasks ke liye hume client ko connected rakhna hota hai without blocking main loop
        # Isliye hum run_until_disconnected yahan call nahi karenge, bas client connect chhod denge.
        
    except Exception as e: 
        print(f"Error in engine for {phone}: {e}")

# --- [ KEYBOARD INTERFACE ] ---
def main_kb():
    return [[Button.text("🚀 Setup New Account", resize=True)],
            [Button.text("✅ Activate All", resize=True), Button.text("❌ Deactivate All", resize=True)],
            [Button.text("📊 My Sessions", resize=True), Button.text("🏠 Home", resize=True)]]

def admin_kb():
    return [[Button.text("👑 Master Stats", resize=True), Button.text("📢 Global Broadcast", resize=True)],
            [Button.text("🔄 Full System Restart", resize=True), Button.text("🏠 Home", resize=True)]]

# --- [ MASTER MESSAGE HANDLER ] ---
@bot.on(events.NewMessage)
async def master_router(event):
    uid = event.sender_id
    text = event.text

    if text == "/start" or text == "🏠 Home":
        welcome = f"**✨ {style('Xirus Modz Auto Massanger')} ✨**\n\n{style('Enterprise Multi-Account Logic Active.')}\n{style('Secure | Safe .')}\n{POWERED_BY}"
        await event.respond(welcome, buttons=main_kb(), link_preview=False)

    elif text == "🚀 Setup New Account":
        asyncio.create_task(run_account_setup(uid))

    elif text == "✅ Activate All":
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE accounts SET status=1 WHERE owner_id=?", (uid,))
            rows = conn.execute("SELECT phone, session_str, reply_msg FROM accounts WHERE owner_id=?", (uid,)).fetchall()
            for r in rows: asyncio.create_task(start_auto_reply_engine(r[0], r[1], r[2]))
        await event.respond(f"**✅ {style('All linked accounts are now ACTIVE')}**")

    elif text == "❌ Deactivate All":
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE accounts SET status=0 WHERE owner_id=?", (uid,))
        for p in list(active_sessions.keys()):
            try: await active_sessions[p].disconnect()
            except: pass
            del active_sessions[p]
        await event.respond(f"**❌ {style('All linked accounts are now STOPPED')}**")

    elif text == "📊 My Sessions":
        with sqlite3.connect(DB_PATH) as conn:
            accs = conn.execute("SELECT phone, status FROM accounts WHERE owner_id=?", (uid,)).fetchall()
        if not accs: return await event.respond(style("No accounts found."))
        msg = f"**📱 {style('Your Sessions')} ({len(accs)}):**\n"
        for a in accs:
            msg += f"\n{'🟢' if a[1]==1 else '🔴'} `{a[0]}`"
        await event.respond(msg)

    # --- ADMIN PRIVILEGES ---
    elif text == "/admin" and uid in ADMIN_IDS:
        await event.respond(f"**👑 {style('Admin Control Room')}**", buttons=admin_kb())

    elif text == "👑 Master Stats" and uid in ADMIN_IDS:
        with sqlite3.connect(DB_PATH) as conn:
            total = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
            users = conn.execute("SELECT phone, username, owner_id FROM accounts").fetchall()
        msg = f"**📊 {style('Global Database Stats')}**\n\n{style('Total Accounts')}: `{total}`\n{style('Live Engines')}: `{len(active_sessions)}`"
        await event.respond(msg)
        
        details = "\n".join([f"👤 {style(u[1])} | `{u[0]}` (Admin: `{u[2]}`)" for u in users])
        if len(details) > 4000: details = details[:4000] + "..."
        await event.respond(details)

    elif text == "📢 Global Broadcast" and uid in ADMIN_IDS:
        asyncio.create_task(global_broadcast(uid))

    elif text == "🔄 Full System Restart" and uid in ADMIN_IDS:
        await event.respond(style("System Rebooting..."))
        os.execl(sys.executable, sys.executable, *sys.argv)

# --- [ ADVANCED SETUP LOGIC ] ---
async def run_account_setup(uid):
    try:
        async with bot.conversation(uid, timeout=600) as conv:
            await conv.send_message(f"**📱 {style('Enter Phone Number (+91.....)')}**")
            num = (await conv.get_response()).text.strip()
            
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            
            try:
                res = await client.send_code_request(num)
            except PhoneNumberInvalidError:
                return await bot.send_message(uid, style("Invalid number! Try again."))
            
            await conv.send_message(f"**📩 {style('Enter OTP for')} `{num}`:**")
            otp = (await conv.get_response()).text.replace(" ", "")
            
            try:
                await client.sign_in(num, otp, phone_code_hash=res.phone_code_hash)
            except SessionPasswordNeededError:
                await conv.send_message(f"**🔐 {style('Two-Step Verification Password Required:')}**")
                pwd = (await conv.get_response()).text
                await client.sign_in(password=pwd)

            await conv.send_message(f"**✍️ {style('Set Stylish Message for this account:')}**")
            reply = f"**{style((await conv.get_response()).text)}**"
            
            me = await client.get_me()
            un = f"@{me.username}" if me.username else "NoUser"
            session_str = StringSession.save(client.session)
            
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute("INSERT OR REPLACE INTO accounts VALUES (?, ?, ?, ?, ?, ?, ?)", 
                            (num, uid, un, session_str, reply, 1, datetime.now().strftime("%Y-%m-%d")))
            
            asyncio.create_task(start_auto_reply_engine(num, session_str, reply))
            await bot.send_message(uid, f"**🚀 {style('Account Setup Done!')}**", buttons=main_kb())
            await client.disconnect()
            
    except AlreadyInConversationError:
        await bot.send_message(uid, style("Wait! Ek setup pehle se chal raha hai."))
    except Exception as e:
        await bot.send_message(uid, f"**❌ {style('Login Failed')}:** `{e}`")

# --- [ GLOBAL BROADCAST ENGINE ] ---
async def global_broadcast(uid):
    async with bot.conversation(uid) as conv:
        await conv.send_message(style("Enter Broadcast Message:"))
        text = (await conv.get_response()).text
        with sqlite3.connect(DB_PATH) as conn:
            sessions = conn.execute("SELECT session_str FROM accounts").fetchall()
        
        await conv.send_message(f"**🚀 {style('Broadcasting to')} `{len(sessions)}` {style('sessions')}...**")
        
        sent = 0
        for s in sessions:
            try:
                c = TelegramClient(StringSession(s[0]), API_ID, API_HASH)
                await c.connect()
                async for d in c.iter_dialogs(limit=5):
                    await c.send_message(d.id, f"**{style(text)}**\n\n{POWERED_BY}", link_preview=False)
                await c.disconnect()
                sent += 1
                await asyncio.sleep(1)
            except: continue
        await bot.send_message(uid, f"**✅ {style('Done!')} {style('Sent via')} `{sent}` {style('Accounts')}.**")

# --- [ AUTO-RECOVERY STARTUP ] ---
async def recovery_on_boot():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("SELECT phone, session_str, reply_msg FROM accounts WHERE status=1").fetchall()
    for row in rows:
        asyncio.create_task(start_auto_reply_engine(row[0], row[1], row[2]))

if __name__ == '__main__':
    print("✅ XIRUS MODZ RUNNING!")
    
    # 1. Start Web Server in Background Thread (Zaroori hai)
    keep_alive()
    
    # 2. Start Bot
    loop = asyncio.get_event_loop()
    loop.create_task(recovery_on_boot())
    bot.run_until_disconnected()
