import os
import sys
import sqlite3
import datetime
import threading
import asyncio
from dotenv import load_dotenv

from flask import Flask, render_template, jsonify, request

# Telethon
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors.rpcerrorlist import FloodWaitError, PhoneCodeExpiredError

# ---------------------------
# تحميل المتغيّرات
# ---------------------------
load_dotenv()
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN")  # بديل عن جلسة مستخدم
STRING_SESSION = os.getenv("TELETHON_SESSION")  # جلسة مستخدم جاهزة
PORT = int(os.getenv("PORT", "5000"))

if not API_ID or not API_HASH:
    raise RuntimeError("❌ لازم توفّرين API_ID و API_HASH ببيئة التشغيل.")

# ---------------------------
# إعداد قاعدة البيانات
# ---------------------------
DB_PATH = "monitor.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # تسريع وتحسين الثبات
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-20000;")  # ~20MB
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS telegram_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT,
            message TEXT,
            date TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS telegram_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT,
            display_name TEXT
        )
    """)
    conn.commit()
    conn.close()

def normalize_channel(link: str) -> str:
    link = (link or "").strip()
    if not link:
        return ""
    # قبول "@user", "user", "https://t.me/user"
    if link.startswith("http"):
        # سحب الـ handle من رابط t.me
        if "t.me/" in link:
            link = link.split("t.me/", 1)[1]
    if not link.startswith('@'):
        link = '@' + link
    return link

# ---------------------------
# عميل Telethon بالخلفية
# ---------------------------
client = None
client_started_event = threading.Event()

def build_client() -> TelegramClient:
    """
    إنشاء عميل Telethon بدون أي تفاعل:
    - إذا BOT_TOKEN موجود -> نستخدمه كبوت
    - إذا STRING_SESSION موجود -> نستخدم جلسة المستخدم المحفوظة
    """
    global client
    if BOT_TOKEN:
        client = TelegramClient("bot_session", API_ID, API_HASH)
    elif STRING_SESSION:
        client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    else:
        raise RuntimeError(
            "❌ لازم توفّرين BOT_TOKEN أو TELETHON_SESSION حتى ما يطلب رقم/كود عند التشغيل."
        )
    return client

async def telethon_main():
    """
    تشغيل العميل، الاشتراك برسائل القنوات الموجودة بجدول telegram_channels،
    وحفظ الرسائل في SQLite.
    """
    global client
    try:
        if BOT_TOKEN:
            await client.start(bot_token=BOT_TOKEN)
        else:
            # جلسة مستخدم محفوظة، ما تحتاج تفاعل
            await client.start()

        print("✅ Telethon connected")

        # قراءة القنوات من القاعدة
        conn = get_db_connection()
        rows = conn.execute("SELECT link, display_name FROM telegram_channels").fetchall()
        conn.close()

        channels = []
        for row in rows:
            link = row["link"]  # ✅ استخدم link الصحيح
            norm = normalize_channel(link)
            if norm:
                channels.append(norm)

        if not channels:
            print("⚠️ ماكو قنوات حالياً بالجدول telegram_channels. راح أشتغل بدون استلام رسائل.")
        else:
            print("🟢 راح أراقب القنوات:", channels)

        @client.on(events.NewMessage(chats=channels if channels else None))
        async def handler(event):
            try:
                channel_title = None
                try:
                    if event.chat and getattr(event.chat, "title", None):
                        channel_title = event.chat.title
                    elif event.chat and getattr(event.chat, "username", None):
                        channel_title = '@' + event.chat.username
                except Exception:
                    pass
                channel_title = channel_title or "Unknown"

                msg_text = event.message.message or ""
                now_iso = datetime.datetime.now().isoformat()

                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO telegram_messages (channel, message, date) VALUES (?, ?, ?)",
                    (channel_title, msg_text, now_iso)
                )
                conn.commit()
                conn.close()
                print("💬", channel_title, "|", msg_text[:120].replace("\n", " "))
            except sqlite3.OperationalError as e:
                print("SQLite OperationalError:", e)
            except Exception as e:
                print("Handler exception:", e)

        # منع الانقطاع: انتظر للانفصال
        await client.run_until_disconnected()

    except FloodWaitError as e:
        print(f"⏳ Flood wait: لازم تنتظر {e.seconds} ثانية.")
    except PhoneCodeExpiredError:
        print("❌ جلسة منتهية/غير صالحة. لو تستخدمين StringSession، أعيدي توليدها.")
    except Exception as e:
        print("❌ Telethon fatal error:", repr(e))

def start_telethon_in_background():
    """
    تشغيل telethon_main في Thread مستقل مع حلقة asyncio خاصة به.
    يضمن التشغيل مرة واحدة فقط.
    """
    if client_started_event.is_set():
        return

    def runner():
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        try:
            build_client()
            loop.run_until_complete(telethon_main())
        finally:
            loop.close()

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    client_started_event.set()
    print("🟢 Telethon background thread started")

# ---------------------------
# Flask App
# ---------------------------
app = Flask(__name__)

@app.route("/")
def index():
    # صفحة بسيطة (إذا عندك templates/index.html خليه، وإلا رجّع JSON)
    return jsonify({"status": "ok", "message": "Telegram monitor is running."})

@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/get_messages/telegram")
def get_messages():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT channel, message, date FROM telegram_messages ORDER BY date DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return jsonify([ (r["channel"], r["message"], r["date"]) for r in rows ])

@app.route("/clear_messages/telegram", methods=["POST"])
def clear_messages():
    conn = get_db_connection()
    conn.execute("DELETE FROM telegram_messages")
    conn.commit()
    conn.close()
    return jsonify({"status": "cleared"})

@app.route("/get_channels/telegram")
def get_channels():
    conn = get_db_connection()
    rows = conn.execute("SELECT link, display_name FROM telegram_channels").fetchall()
    conn.close()
    return jsonify([ f"{r['display_name']} | {r['link']}" for r in rows ])

@app.route("/save_channels/telegram", methods=["POST"])
def save_channels():
    data = request.get_json(force=True, silent=True) or {}
    channels = data.get("channels", [])

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM telegram_channels")
    for ch in channels:
        if '|' in ch:
            left, right = map(str.strip, ch.split('|', 1))
            # نعتبر أن اليسار هو الاسم الظاهر، اليمين هو الرابط
            display_name = left or 'غير معروف'
            link = normalize_channel(right)
        else:
            display_name = 'غير معروف'
            link = normalize_channel(ch)
        if link:
            cur.execute(
                "INSERT INTO telegram_channels (link, display_name) VALUES (?, ?)",
                (link, display_name)
            )
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# ---------------------------
# تشغيل التطبيق
# ---------------------------
def main():
    init_db()
    # في التطوير المحلي، Flask يعيد التشغيل؛ نتفادى تشغيل الخيط مرتين.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or os.environ.get("FLASK_ENV") != "development":
        start_telethon_in_background()

    host = "0.0.0.0"
    # على Render، gunicorn يمرر PORT؛ لو تشغل بايثون مباشر، رح نستخدم PORT الافتراضي
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=PORT, debug=debug)

if __name__ == "__main__":
    main()
