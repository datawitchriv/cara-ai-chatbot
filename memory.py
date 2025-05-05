import sqlite3

def init_db():
    conn = sqlite3.connect("cara_memory.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            topic TEXT,
            fact TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def remember_fact(user, topic, fact):
    conn = sqlite3.connect("cara_memory.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO user_memory (user, topic, fact)
        VALUES (?, ?, ?)
    """, (user, topic, fact))
    conn.commit()
    conn.close()

def recall_facts(user):
    conn = sqlite3.connect("cara_memory.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic, fact FROM user_memory
        WHERE user = ?
        ORDER BY timestamp DESC
        LIMIT 5
    """, (user,))
    facts = cursor.fetchall()
    conn.close()
    return facts
