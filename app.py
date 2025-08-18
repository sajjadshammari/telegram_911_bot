import os
import sqlite3
import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN")  # اختياري: لو تستخدمين بوت
STRING_SESSION = os.getenv("TELETHON_SESSION")  # اختياري: جلسة مستخدم محفوظة

if not API_ID or not API_HASH:
    raise RuntimeError("❌ لازم توفّرين API_ID و API_HASH.")

DB_PATH = "monitor.db"

def get_channels():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    print("telethon_bot.py,conn = sqlite3.connect(monitor.db, timeout=10)")
    conn.execute("PRAGMA journal_mode=WAL;")
    c = conn.cursor()
    c.execute("SELECT link, display_name FROM telegram_channels")
    rows = c.fetchall()
    conn.close()

    channels = []
    for row in rows:
        link = row[0]  # ✅ استخدمي العمود link
        if link:
            link = link.strip()
            if link.startswith("http") and "t.me/" in link:
                link = link.split("t.me/", 1)[1]
            if not link.startswith('@'):
                link = '@' + link
            channels.append(link)
    return channels

def run_bot():
    channels = get_channels()
    if not channels:
        print("❌ لا توجد قنوات صالحة في جدول telegram_channels.")
        return
    else:
        print(channels)

    # بناء العميل بدون تفاعل
    if BOT_TOKEN:
        client = TelegramClient("bot_session", API_ID, API_HASH)
        client.start(bot_token=BOT_TOKEN)
    elif STRING_SESSION:
        client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
        client.start()  # جلسة محفوظة، ما يطلب رقم
    else:
        raise RuntimeError("❌ وفّري BOT_TOKEN أو TELETHON_SESSION حتى ما يطلب رقم.")

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        conn = sqlite3.connect(DB_PATH, timeout=10)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS telegram_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            message TEXT,
            date TEXT
        )""")
        channel_title = getattr(event.chat, "title", None) or (
            '@' + getattr(event.chat, 'username', 'Unknown')
            if getattr(event.chat, 'username', None) else "Unknown"
        )
        c.execute("INSERT INTO telegram_messages (channel, message, date) VALUES (?, ?, ?)",
                  (channel_title, event.message.message or "", datetime.datetime.now().isoformat()))
        print("Message:", (event.message.message or "")[:120].replace("\n", " "))
        conn.commit()
        conn.close()

    print("✅ bot started (non-interactive)")
    client.run_until_disconnected()

if __name__ == '__main__':
    run_bot()
