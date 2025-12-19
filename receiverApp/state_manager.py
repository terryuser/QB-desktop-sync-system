import sqlite3
import uuid
from typing import List, Optional, Tuple
from datetime import datetime

DB_PATH = "qbwc.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        ticket TEXT PRIMARY KEY,
        username TEXT,
        company_file TEXT,
        created_at TIMESTAMP,
        last_accessed TIMESTAMP,
        is_active BOOLEAN,
        interactive_mode BOOLEAN DEFAULT 0,
        interactive_url TEXT,
        interactive_status TEXT
    )''')
    # Tasks/Queue table - Updated to support username queuing independent of ticket
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        ticket TEXT,
        request_xml TEXT,
        response_xml TEXT,
        status TEXT, -- 'pending', 'processing', 'sent', 'done', 'error'
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY(ticket) REFERENCES sessions(ticket)
    )''')
    conn.commit()
    conn.close()

class StateManager:
    def __init__(self):
        init_db()

    def get_db(self):
        return get_db()

    def create_session(self, username: str, company_file: str) -> str:
        ticket = str(uuid.uuid4())
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO sessions (ticket, username, company_file, created_at, last_accessed, is_active) VALUES (?, ?, ?, ?, ?, ?)",
            (ticket, username, company_file, datetime.now(), datetime.now(), True)
        )
        # Also assign any orphaned pending tasks for this user to this queue? 
        # Actually better to just pick them up in get_next_pending_task
        conn.commit()
        conn.close()
        return ticket

    def get_session(self, ticket: str):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM sessions WHERE ticket = ?", (ticket,))
        row = c.fetchone()
        conn.close()
        return row

    def update_session_activity(self, ticket: str):
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE sessions SET last_accessed = ? WHERE ticket = ?", (datetime.now(), ticket))
        conn.commit()
        conn.close()

    def close_session(self, ticket: str):
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE sessions SET is_active = 0 WHERE ticket = ?", (ticket,))
        conn.commit()
        conn.close()

    def queue_task_for_user(self, username: str, request_xml: str) -> int:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO tasks (username, request_xml, status, created_at) VALUES (?, ?, ?, ?)",
            (username, request_xml, 'pending', datetime.now())
        )
        task_id = c.lastrowid
        conn.commit()
        conn.close()
        return task_id

    def get_next_pending_task(self, ticket: str) -> Optional[Tuple[int, str]]:
        conn = get_db()
        c = conn.cursor()
        
        # 1. Get username for this ticket
        c.execute("SELECT username FROM sessions WHERE ticket = ?", (ticket,))
        row = c.fetchone()
        if not row:
            conn.close()
            return None
        
        username = row['username']

        # 2. Find oldest pending task for this user
        c.execute("SELECT id, request_xml FROM tasks WHERE username = ? AND status = 'pending' ORDER BY id ASC LIMIT 1", (username,))
        task_row = c.fetchone()
        
        if task_row:
            # Claim it
            task_id = task_row['id']
            # We can mark it as 'sent' or 'processing'. Standard flow: 'sent'
            # Update the ticket ID on it so we know who took it
            c.execute("UPDATE tasks SET status = 'sent', ticket = ?, updated_at = ? WHERE id = ?", (ticket, datetime.now(), task_id))
            conn.commit()
            conn.close()
            return task_id, task_row['request_xml']
        
        conn.close()
        return None

    def mark_task_sent(self, task_id: int):
        # Redundant if we do it in get_next_pending_task, but harmless
        pass

    def complete_task(self, ticket: str, response_xml: str):
        conn = get_db()
        c = conn.cursor()
        # Find the most recent 'sent' task for this ticket
        c.execute("SELECT id FROM tasks WHERE ticket = ? AND status = 'sent' ORDER BY updated_at DESC LIMIT 1", (ticket,))
        row = c.fetchone()
        if row:
            task_id = row['id']
            c.execute("UPDATE tasks SET status = 'done', response_xml = ?, updated_at = ? WHERE id = ?", (response_xml, datetime.now(), task_id))
            conn.commit()
        conn.close()

    def get_progress(self, ticket: str) -> int:
        # Progress calculation is tricky with persistent queue. 
        # Just return 100 if no pending tasks for valid session.
        return 100 

    # Interactive Mode Support
    def set_interactive_mode(self, ticket: str, url: str):
         conn = get_db()
         c = conn.cursor()
         c.execute("UPDATE sessions SET interactive_mode = 1, interactive_url = ?, interactive_status = 'pending' WHERE ticket = ?", (url, ticket))
         conn.commit()
         conn.close()

    def check_interactive_done(self, ticket: str) -> str:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT interactive_status FROM sessions WHERE ticket = ?", (ticket,))
        row = c.fetchone()
        conn.close()
        return row['interactive_status'] if row else ""
