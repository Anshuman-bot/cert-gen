import sqlite3
import os
import json
import hashlib
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "certify_pro.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        organization TEXT NOT NULL,
        event_date TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        template_id TEXT NOT NULL DEFAULT 'modern_tech',
        signatory1_name TEXT NOT NULL,
        signatory1_title TEXT NOT NULL,
        signatory2_name TEXT NOT NULL,
        signatory2_title TEXT NOT NULL,
        citation_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Templates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS templates (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        primary_color TEXT NOT NULL,
        secondary_color TEXT NOT NULL,
        accent_color TEXT NOT NULL,
        bg_style TEXT NOT NULL,
        badge_text TEXT NOT NULL,
        font_theme TEXT NOT NULL,
        is_default INTEGER DEFAULT 0
    )
    """)

    # Batches table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        total_records INTEGER DEFAULT 0,
        clean_records INTEGER DEFAULT 0,
        flagged_records INTEGER DEFAULT 0,
        duplicate_records INTEGER DEFAULT 0,
        status TEXT DEFAULT 'PENDING_REVIEW',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (event_id) REFERENCES events (id)
    )
    """)

    # Participants table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_id INTEGER,
        event_id INTEGER NOT NULL,
        original_name TEXT NOT NULL,
        clean_name TEXT NOT NULL,
        original_email TEXT,
        clean_email TEXT,
        college TEXT,
        department TEXT,
        roll_number TEXT,
        role TEXT DEFAULT 'Participant',
        validation_status TEXT DEFAULT 'CLEAN',
        validation_issues TEXT DEFAULT '[]',
        confidence_score INTEGER DEFAULT 100,
        is_approved INTEGER DEFAULT 1,
        certificate_id TEXT,
        cert_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (batch_id) REFERENCES batches (id),
        FOREIGN KEY (event_id) REFERENCES events (id)
    )
    """)

    # Certificates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id TEXT PRIMARY KEY,
        participant_id INTEGER NOT NULL,
        event_id INTEGER NOT NULL,
        cert_hash TEXT NOT NULL,
        participant_name TEXT NOT NULL,
        event_name TEXT NOT NULL,
        organization TEXT NOT NULL,
        role TEXT NOT NULL,
        issue_date TEXT NOT NULL,
        qr_code_path TEXT,
        png_path TEXT,
        pdf_path TEXT,
        status TEXT DEFAULT 'ACTIVE',
        view_count INTEGER DEFAULT 0,
        last_verified_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (participant_id) REFERENCES participants (id),
        FOREIGN KEY (event_id) REFERENCES events (id)
    )
    """)

    # Verification logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verification_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        certificate_id TEXT NOT NULL,
        status_result TEXT NOT NULL,
        ip_address TEXT,
        user_agent TEXT,
        verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Email logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS email_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        certificate_id TEXT NOT NULL,
        recipient_email TEXT NOT NULL,
        recipient_name TEXT NOT NULL,
        event_name TEXT NOT NULL,
        status TEXT DEFAULT 'SENT',
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()

    # Pre-populate default templates if empty
    cursor.execute("SELECT COUNT(*) FROM templates")
    if cursor.fetchone()[0] == 0:
        templates = [
            (
                "modern_tech",
                "Cyber Tech & Hackathon",
                "Technical",
                "Deep sapphire & cyan accents with sleek geometric styling, best for Hackathons and Coding Contests",
                "#0f172a", "#0284c7", "#38bdf8", "dark_tech", "CERTIFICATE OF EXCELLENCE", "modern", 1
            ),
            (
                "royal_academic",
                "Imperial Academic Merit",
                "Academic",
                "Regal ivory parchment with gold foil borders and classic typography for Conferences & Symposia",
                "#1e293b", "#b45309", "#d97706", "ivory_gold", "CERTIFICATE OF ACHIEVEMENT", "serif", 0
            ),
            (
                "sleek_minimal",
                "Clean Emerald Workshop",
                "Workshop",
                "Ultra-clean minimalist layout with fresh emerald gradients for Bootcamps and Seminars",
                "#064e3b", "#059669", "#10b981", "clean_white", "CERTIFICATE OF PARTICIPATION", "sans", 0
            ),
            (
                "prestige_sports",
                "Crimson Athletic & Cultural",
                "Sports & Cultural",
                "Bold crimson and bronze ribbon accents for Sports meets, Arts festivals and Stage competitions",
                "#881337", "#e11d48", "#f43f5e", "crimson_ribbon", "CERTIFICATE OF HONOR", "bold", 0
            )
        ]
        cursor.executemany("""
        INSERT INTO templates (id, name, category, description, primary_color, secondary_color, accent_color, bg_style, badge_text, font_theme, is_default)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, templates)
        conn.commit()

    # Pre-populate sample event if empty
    cursor.execute("SELECT COUNT(*) FROM events")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO events (name, organization, event_date, category, description, template_id, signatory1_name, signatory1_title, signatory2_name, signatory2_title, citation_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "National Hackathon 2026: AI & Cloud Horizon",
            "Apex Institute of Technology & Engineering",
            "2026-10-15",
            "Technical",
            "Annual 36-hour flagship national level collegiate hackathon with over 500+ participants.",
            "modern_tech",
            "Dr. Rajesh V. Sharma",
            "Convener & Head of CS",
            "Prof. Ananya Sen",
            "Dean of Academic Affairs",
            "has demonstrated exceptional technical innovation, teamwork, and problem-solving skills in"
        ))
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
