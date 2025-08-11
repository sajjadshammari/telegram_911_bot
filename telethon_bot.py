from telethon import TelegramClient, events
import sqlite3
import datetime
from dotenv import load_dotenv
import os
load_dotenv()  # تحميل محتويات ملف .env

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

def run_bot():
    # نقرأ القنوات من الجدول
    conn = sqlite3.connect("monitor.db", timeout=10)
    print("telethon_bot.py,conn = sqlite3.connect(monitor.db, timeout=10)")
    conn.execute("PRAGMA journal_mode=WAL;")

    c = conn.cursor()
    c.execute("SELECT link, display_name FROM telegram_channels")
    rows = c.fetchall()
    conn.close()

    channels = []
    for row in rows:
        link = row[1]
        
        if link:
            link = link.strip()
            if not link.startswith('@'):
                link = '@' + link
            channels.append(link)

    if not channels:
        print("❌ لا توجد قنوات صالحة في جدول telegram_channels.")
        return
    else:
         print(channels)

    client = TelegramClient('session', api_id, api_hash)

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        conn = sqlite3.connect('monitor.db')
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS telegram_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            message TEXT,
            date TEXT
        )""")
        c.execute("INSERT INTO telegram_messages (channel, message, date) VALUES (?, ?, ?)",
                  (event.chat.title, event.message.message, datetime.datetime.now().isoformat()))
        print("Message:", event.message.message)
        conn.commit()
        conn.close()

    print("✅ bot started")
    client.start()
    client.run_until_disconnected()

# فقط إذا شغلته مباشرة من الملف نفسه
if __name__ == '__main__':
    run_bot()
