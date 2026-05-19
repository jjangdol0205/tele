import sqlite3
import datetime
import os

DB_FILE = 'messages.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            channel_name TEXT,
            content TEXT,
            link TEXT,
            is_summarized INTEGER DEFAULT 0,
            media_path TEXT
        )
    ''')
    
    # 만약 기존 DB에 media_path 컬럼이 없다면 추가 (마이그레이션)
    try:
        c.execute('ALTER TABLE messages ADD COLUMN media_path TEXT')
    except sqlite3.OperationalError:
        pass # 이미 존재함
        
    conn.commit()
    conn.close()

def save_message(channel_name, content, link, media_path=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO messages (channel_name, content, link, media_path)
        VALUES (?, ?, ?, ?)
    ''', (channel_name, content, link, media_path))
    conn.commit()
    conn.close()

def get_unsummarized_messages():
    """요약되지 않은 메시지 목록을 가져옵니다."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT id, channel_name, content, link, media_path
        FROM messages
        WHERE is_summarized = 0
    ''')
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_as_summarized(message_ids):
    """지정된 메시지들을 요약 완료 상태로 변경합니다."""
    if not message_ids:
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    placeholders = ','.join('?' for _ in message_ids)
    c.execute(f'''
        UPDATE messages
        SET is_summarized = 1
        WHERE id IN ({placeholders})
    ''', message_ids)
    conn.commit()
    conn.close()

def get_recent_messages(limit=50):
    """최근 메시지 목록을 가져옵니다."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('''
        SELECT id, channel_name, content, link, media_path
        FROM messages
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
