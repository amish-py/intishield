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

        # Cases table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT UNIQUE NOT NULL,
                secret_token TEXT NOT NULL,
                email TEXT NOT NULL,
                protection_mode TEXT DEFAULT 'face_biometric',
                total_items INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        """)

        # Fingerprints & Face Descriptors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS protected_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                file_name TEXT,
                face_descriptor TEXT,
                protection_mode TEXT DEFAULT 'face_biometric',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
            )
        """)

        # Auto-migration for existing databases
        cursor.execute("PRAGMA table_info(cases)")
        case_cols = [c[1] for c in cursor.fetchall()]
        if "protection_mode" not in case_cols:
            cursor.execute("ALTER TABLE cases ADD COLUMN protection_mode TEXT DEFAULT 'face_biometric'")

        cursor.execute("PRAGMA table_info(protected_fingerprints)")
        fp_cols = [c[1] for c in cursor.fetchall()]
        if "protection_mode" not in fp_cols:
            cursor.execute("ALTER TABLE protected_fingerprints ADD COLUMN protection_mode TEXT DEFAULT 'face_biometric'")
        if "face_descriptor" not in fp_cols:
            cursor.execute("ALTER TABLE protected_fingerprints ADD COLUMN face_descriptor TEXT")

        # Partners table
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

        # Niscord Platform Posts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS niscord_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT UNIQUE NOT NULL,
                author TEXT NOT NULL,
                caption TEXT,
                image_data TEXT NOT NULL,
                phash TEXT NOT NULL,
                face_descriptor TEXT,
                status TEXT DEFAULT 'active',
                takedown_case_id TEXT,
                takedown_reason TEXT,
                takedown_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("PRAGMA table_info(niscord_posts)")
        np_cols = [c[1] for c in cursor.fetchall()]
        if "face_descriptor" not in np_cols:
            cursor.execute("ALTER TABLE niscord_posts ADD COLUMN face_descriptor TEXT")
        if "takedown_reason" not in np_cols:
            cursor.execute("ALTER TABLE niscord_posts ADD COLUMN takedown_reason TEXT")

        conn.commit()