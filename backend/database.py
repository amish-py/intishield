import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "intishield.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        # Check for legacy schema and migrate cleanly
        cursor.execute("PRAGMA table_info(protected_fingerprints)")
        cols = {row[1] for row in cursor.fetchall()}
        if "secret_token" in cols:
            cursor.execute("DROP TABLE IF EXISTS protected_fingerprints")
            cursor.execute("DROP TABLE IF EXISTS cases")

        # 1. Cases table (Default status: 'pending')
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT UNIQUE NOT NULL,
                secret_token TEXT NOT NULL,
                email TEXT NOT NULL,
                total_items INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)

        # 2. Fingerprints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS protected_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                file_name TEXT,
                hash_type TEXT DEFAULT 'dhash',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
            )
        """)

        # 3. Platform Partner Applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform_name TEXT NOT NULL,
                website_url TEXT,
                store_url TEXT,
                contact_email TEXT NOT NULL,
                tier TEXT DEFAULT 'Approved Participant',
                has_hash_tech INTEGER DEFAULT 0,
                agreed_zero_retention INTEGER DEFAULT 0,
                agreed_immediate_action INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_case_id ON cases(case_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fp_case ON protected_fingerprints(case_id)")
        conn.commit()