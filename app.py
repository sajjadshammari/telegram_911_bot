from flask import Flask, render_template, jsonify, request
import sqlite3
import subprocess
import sys
import os  # ✅ ضروري حتى يشتغل الشرط الصح

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect("monitor.db", timeout=10)
    print("app.py,conn = sqlite3.connect(monitor.db, timeout=10)")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_messages/telegram")
def get_messages():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT channel, message, date FROM telegram_messages ORDER BY date DESC LIMIT 50")
    messages = c.fetchall()
    conn.close()
    return jsonify([tuple(msg) for msg in messages])

@app.route("/clear_messages/telegram", methods=["POST"])
def clear_messages():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM telegram_messages")
    conn.commit()
    conn.close()
    return jsonify({"status": "cleared"})

@app.route("/get_channels/telegram")
def get_channels():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT link, display_name FROM telegram_channels")
    channels = [f"{row['display_name']} | {row['link']}" for row in c.fetchall()]
    conn.close()
    return jsonify(channels)

@app.route("/save_channels/telegram", methods=["POST"])
def save_channels():
    data = request.get_json()
    channels = data.get("channels", [])

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("DELETE FROM telegram_channels")
    for ch in channels:
        if '|' in ch:
            link, display_name = map(str.strip, ch.split('|', 1))
        else:
            link = ch.strip()
            display_name = 'غير معروف'
        c.execute(
            "INSERT INTO telegram_channels (link, display_name) VALUES (?, ?)",
            (link, display_name)
        )

    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

if __name__ == "__main__":
    # ✅ نشغل telethon_bot.py فقط مرة واحدة
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        python_exe = sys.executable
        subprocess.Popen([python_exe, "telethon_bot.py"])
        print("🟢 telethon_bot.py started")

    # 📌 على Render لازم نستخدم PORT من env
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
