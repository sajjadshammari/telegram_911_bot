import sqlite3

conn = sqlite3.connect("monitor.db")
c = conn.cursor()

# حذف الجداول إذا كانت موجودة مسبقاً
c.execute("DROP TABLE IF EXISTS telegram_messages")
c.execute("DROP TABLE IF EXISTS telegram_channels")


# إنشاء جدول رسائل التليكرام
c.execute("""
CREATE TABLE telegram_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT,
    message TEXT,
    date TEXT
)
""")



# إنشاء جدول قنوات التليكرام
c.execute("""
CREATE TABLE telegram_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT,
    display_name TEXT
)
""")



conn.commit()
conn.close()

print("✅ تم حذف وإنشاء الجداول بنجاح!")
