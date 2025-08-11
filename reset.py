import sqlite3
from datetime import datetime

def reset_news_codes():
    conn = sqlite3.connect("monitor.db")
    c = conn.cursor()

    # تصفير كل الأخبار في الجدول
    c.execute("DELETE FROM news_codes")
    conn.commit()
    conn.close()

    print("✅ تم تصفير جدول الأخبار news_codes في:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    reset_news_codes()
