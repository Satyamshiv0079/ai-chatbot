import sqlite3
import json
import os
import uuid
from datetime import datetime
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), 'history.db')

class ConversationState:
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates standard tables for sessions, messages, and orders with full constraints."""
        with self._get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    current_intent TEXT,
                    slots TEXT,
                    pending_slot TEXT DEFAULT NULL,
                    pending_intent TEXT DEFAULT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    user_text TEXT,
                    bot_response TEXT,
                    intent TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id) ON DELETE CASCADE
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    status TEXT,
                    eta TEXT,
                    details TEXT,
                    user_email TEXT DEFAULT NULL
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE,
                    password_hash TEXT,
                    first_name TEXT,
                    last_name TEXT
                )
            ''')
            
            # Check if columns exist (for migration if db was already created without them)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(sessions)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'pending_slot' not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN pending_slot TEXT DEFAULT NULL")
            if 'pending_intent' not in columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN pending_intent TEXT DEFAULT NULL")

            cursor.execute("PRAGMA table_info(orders)")
            order_columns = [row[1] for row in cursor.fetchall()]
            if 'details' not in order_columns:
                conn.execute("ALTER TABLE orders ADD COLUMN details TEXT DEFAULT '{}'")
            if 'user_email' not in order_columns:
                conn.execute("ALTER TABLE orders ADD COLUMN user_email TEXT DEFAULT NULL")
                
            conn.commit()
            
        self._seed_orders()

    def _seed_orders(self):
        """Seeds initial mock order database if empty."""
        initial_orders = [
            ("12345", "Shipped", "Tomorrow by 8 PM", "{}"),
            ("67890", "Processing", "3-5 business days", "{}"),
            ("11111", "Delivered", "Already delivered", "{}")
        ]
        with self._get_conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            if count == 0:
                conn.executemany(
                    "INSERT INTO orders (order_id, status, eta, details) VALUES (?, ?, ?, ?)",
                    initial_orders
                )
                conn.commit()

    def get_order(self, order_id):
        """Fetches order from database. If not found, dynamically generates a plausible entry for recruiters!"""
        with self._get_conn() as conn:
            order = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            if order:
                order_dict = dict(order)
                if order_dict.get("details"):
                    try:
                        order_dict["details"] = json.loads(order_dict["details"])
                    except:
                        pass
                return order_dict
                
        # Recruiter dynamic fallback: generate on the fly
        import random
        statuses = ["Shipped", "Processing", "In Transit", "Delivered"]
        etas = ["Tomorrow by 5 PM", "In 2-3 business days", "By Friday next week", "Delivered yesterday"]
        
        status = random.choice(statuses)
        eta = random.choice(etas)
        
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO orders (order_id, status, eta, details, user_email) VALUES (?, ?, ?, ?, NULL)",
                (order_id, status, eta, "{}")
            )
            conn.commit()
            
        return {"order_id": order_id, "status": status, "eta": eta, "details": {}}

    def create_order(self, order_id, status, eta, details, user_email=None):
        """Creates a new order from checkout."""
        details_json = json.dumps(details) if isinstance(details, dict) else details
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO orders (order_id, status, eta, details, user_email) VALUES (?, ?, ?, ?, ?)",
                (order_id, status, eta, details_json, user_email)
            )
            conn.commit()
        return {"order_id": order_id, "status": status, "eta": eta}

    def get_user_orders(self, user_email):
        with self._get_conn() as conn:
            orders = conn.execute("SELECT * FROM orders WHERE user_email = ? ORDER BY order_id DESC", (user_email,)).fetchall()
            result = []
            for order in orders:
                order_dict = dict(order)
                if order_dict.get("details"):
                    try:
                        order_dict["details"] = json.loads(order_dict["details"])
                    except:
                        pass
                result.append(order_dict)
            return result
            
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, email, password, first_name, last_name):
        with self._get_conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO users (email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?)",
                    (email, self.hash_password(password), first_name, last_name)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def verify_user(self, email, password):
        with self._get_conn() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ? AND password_hash = ?", (email, self.hash_password(password))).fetchone()
            if user:
                return dict(user)
            return None
            
    def get_user_by_email(self, email):
        with self._get_conn() as conn:
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if user:
                return dict(user)
            return None

    def list_sessions(self):
        """Lists all session IDs and their creation times from SQLite."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT session_id, created_at, current_intent FROM sessions ORDER BY created_at DESC"
            ).fetchall()
            
            sessions_list = []
            for row in rows:
                # Fetch first user query as the title if available
                last_msg = conn.execute(
                    "SELECT user_text FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT 1",
                    (row["session_id"],)
                ).fetchone()
                
                title = last_msg["user_text"] if last_msg else "New Conversation"
                if len(title) > 25:
                    title = title[:22] + "..."
                    
                try:
                    dt = datetime.fromisoformat(row["created_at"])
                    time_str = dt.strftime("%I:%M %p").lower()
                except Exception:
                    time_str = "12:00 am"
                    
                sessions_list.append({
                    "id": row["session_id"],
                    "title": title,
                    "timestamp": time_str
                })
        return sessions_list

    def create_session(self):
        """Creates a new unique session and persists it in SQLite with FSM states."""
        session_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        slots_json = json.dumps({})
        
        with self._get_conn() as conn:
            conn.execute(
                'INSERT INTO sessions (session_id, created_at, slots, pending_slot, pending_intent) VALUES (?, ?, ?, NULL, NULL)',
                (session_id, created_at, slots_json)
            )
            conn.commit()
        return session_id

    def get_session(self, session_id):
        """Fetches active slots, FSM pending states, and all messages from SQLite dynamically."""
        with self._get_conn() as conn:
            session_row = conn.execute(
                'SELECT * FROM sessions WHERE session_id = ?',
                (session_id,)
            ).fetchone()
            
            if not session_row:
                return None
                
            message_rows = conn.execute(
                'SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC',
                (session_id,)
            ).fetchall()
            
        history = []
        for row in message_rows:
            history.append({
                "user": row["user_text"],
                "bot": row["bot_response"],
                "intent": row["intent"],
                "timestamp": row["timestamp"]
            })
            
        return {
            "session_id": session_row["session_id"],
            "created_at": session_row["created_at"],
            "current_intent": session_row["current_intent"],
            "slots": json.loads(session_row["slots"] or '{}'),
            "pending_slot": session_row["pending_slot"],
            "pending_intent": session_row["pending_intent"],
            "history": history
        }

    def set_pending_state(self, session_id, slot_name, intent_name):
        """Sets a pending slot and intent in SQLite to hold dialogue state across turns."""
        with self._get_conn() as conn:
            conn.execute(
                'UPDATE sessions SET pending_slot = ?, pending_intent = ? WHERE session_id = ?',
                (slot_name, intent_name, session_id)
            )
            conn.commit()

    def clear_pending_state(self, session_id):
        """Resets the pending dialogue state to NULL once resolved."""
        with self._get_conn() as conn:
            conn.execute(
                'UPDATE sessions SET pending_slot = NULL, pending_intent = NULL WHERE session_id = ?',
                (session_id,)
            )
            conn.commit()

    def update_session(self, session_id, intent, entities, user_text, bot_response):
        """Appends slots and logs conversations in SQLite, ensuring auto-creation if session was lost."""
        session = self.get_session(session_id)
        if not session:
            created_at = datetime.now().isoformat()
            slots_json = json.dumps(entities)
            with self._get_conn() as conn:
                conn.execute(
                    'INSERT INTO sessions (session_id, created_at, current_intent, slots, pending_slot, pending_intent) VALUES (?, ?, ?, ?, NULL, NULL)',
                    (session_id, created_at, intent, slots_json)
                )
                conn.commit()
        else:
            updated_slots = {**session["slots"], **entities}
            slots_json = json.dumps(updated_slots)
            with self._get_conn() as conn:
                conn.execute(
                    'UPDATE sessions SET current_intent = ?, slots = ? WHERE session_id = ?',
                    (intent, slots_json, session_id)
                )
                conn.commit()
                
        timestamp = datetime.now().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                'INSERT INTO messages (session_id, user_text, bot_response, intent, timestamp) VALUES (?, ?, ?, ?, ?)',
                (session_id, user_text, bot_response, intent, timestamp)
            )
            conn.commit()

    def get_slot(self, session_id, slot_name):
        """Retrieves a slot value by session ID directly from the SQLite slots JSON string."""
        session = self.get_session(session_id)
        if session:
            return session["slots"].get(slot_name)
        return None

    def clear_session(self, session_id):
        """Clears all records for a session, relying on database CASCADE deletes."""
        with self._get_conn() as conn:
            conn.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            conn.commit()

    def delete_session(self, session_id):
        """Alias for clear_session to match naming conventions."""
        self.clear_session(session_id)

    def clear_all_sessions(self):
        """Deletes all sessions (and cascade deletes messages)."""
        with self._get_conn() as conn:
            conn.execute('DELETE FROM sessions')
            conn.commit()

    def get_stats(self):
        """Returns session, message, intent, and order statistics."""
        with self._get_conn() as conn:
            total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            total_messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            
            intent_dist = conn.execute("SELECT intent, COUNT(*) as count FROM messages GROUP BY intent").fetchall()
            intent_distribution = {row['intent']: row['count'] for row in intent_dist if row['intent']}
            
            order_status = conn.execute("SELECT status, COUNT(*) as count FROM orders GROUP BY status").fetchall()
            order_status_breakdown = {row['status']: row['count'] for row in order_status if row['status']}
            
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "intent_distribution": intent_distribution,
            "order_status_breakdown": order_status_breakdown
        }

    def get_all_orders(self):
        """Returns all orders in the database."""
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM orders ORDER BY order_id DESC").fetchall()
            result = []
            for row in rows:
                order_dict = dict(row)
                if order_dict.get("details"):
                    try:
                        order_dict["details"] = json.loads(order_dict["details"])
                    except:
                        pass
                result.append(order_dict)
            return result