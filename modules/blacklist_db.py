"""
Mock Database for Stolen & Flagged Documents / Watchlist.
Module 2 Integration: SQLite local database for instant, offline verification.
"""

import os
import sqlite3
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "blacklist.db")

DEFAULT_BLACKLIST_DOCS = [
    ("N88294012", "USA", "Interpol SLTD (Stolen and Lost Travel Documents) database hit", "2024-01-15", "CRITICAL"),
    ("L98321098", "GBR", "Reported stolen in transit - London Heathrow", "2023-11-20", "CRITICAL"),
    ("C01239842", "DEU", "Counterfeit blank book reported by German Federal Police", "2024-03-02", "CRITICAL"),
    ("F55490123", "FRA", "Fraudulent identity theft alert issued by Prefecture de Police", "2023-08-14", "HIGH"),
    ("A99887766", "AUS", "Revoked passport - Judicial travel restriction active", "2024-05-10", "HIGH"),
    ("X12345678", "CAN", "Forged identity document seized during border inspection", "2024-02-18", "CRITICAL"),
    ("Z99001122", "IND", "Duplicate serial number detected in passport issuance audit", "2023-09-30", "HIGH"),
]

DEFAULT_WATCHLIST_PERSONS = [
    ("CONNOR, SARAH", "USA", "1965-02-28", "Active federal warrant for identity fraud", "CRITICAL"),
    ("BOND, JAMES", "GBR", "1968-04-13", "Restricted surveillance watchlist (SIMULATED)", "LOW"),
    ("SCHMIDT, HANS", "DEU", "1980-07-22", "Financial sanctions list & cross-border cash smuggling", "HIGH"),
    ("DUBOIS, JEAN", "FRA", "1975-11-05", "Europol Red Notice - fraudulent documentation syndicate", "CRITICAL"),
    ("MILLER, DAVID", "USA", "1988-11-14", "Pre-flagged for secondary security screening", "MEDIUM"),
]


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(force_reset: bool = False):
    """Initializes the SQLite schema and seeds with mock blacklist data."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if force_reset:
        cursor.execute("DROP TABLE IF EXISTS blacklist_documents")
        cursor.execute("DROP TABLE IF EXISTS watchlist_persons")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist_documents (
            doc_number TEXT PRIMARY KEY,
            country TEXT NOT NULL,
            reason TEXT NOT NULL,
            flagged_date TEXT NOT NULL,
            severity TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlist_persons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            nationality TEXT,
            dob TEXT,
            reason TEXT NOT NULL,
            risk_level TEXT NOT NULL
        )
    """)

    # Seed initial documents if empty
    cursor.execute("SELECT COUNT(*) FROM blacklist_documents")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO blacklist_documents (doc_number, country, reason, flagged_date, severity)
            VALUES (?, ?, ?, ?, ?)
        """, DEFAULT_BLACKLIST_DOCS)

    # Seed initial persons if empty
    cursor.execute("SELECT COUNT(*) FROM watchlist_persons")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO watchlist_persons (name, nationality, dob, reason, risk_level)
            VALUES (?, ?, ?, ?, ?)
        """, DEFAULT_WATCHLIST_PERSONS)

    conn.commit()
    conn.close()


def check_document(doc_number: str, country: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Checks if a document number exists in the blacklist."""
    if not doc_number:
        return None
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    clean_number = doc_number.replace("<", "").strip().upper()
    query = "SELECT * FROM blacklist_documents WHERE UPPER(doc_number) = ?"
    params = [clean_number]

    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "is_blacklisted": True,
            "doc_number": row["doc_number"],
            "country": row["country"],
            "reason": row["reason"],
            "flagged_date": row["flagged_date"],
            "severity": row["severity"]
        }
    return None


def check_person(name: str, dob: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Checks if a person name (surname, given names) matches the watchlist."""
    if not name:
        return None
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    clean_name = name.replace("<", " ").strip().upper()
    
    # Try exact match or token containment
    cursor.execute("SELECT * FROM watchlist_persons")
    rows = cursor.fetchall()
    conn.close()

    clean_tokens = set([t for t in clean_name.replace(",", " ").split() if len(t) > 2])

    for row in rows:
        row_name = row["name"].upper()
        row_tokens = set([t for t in row_name.replace(",", " ").split() if len(t) > 2])
        # If all tokens of the watchlist name are found in the query name or vice-versa
        if row_name in clean_name or clean_name in row_name or (row_tokens and row_tokens.issubset(clean_tokens)):
            return {
                "is_watchlisted": True,
                "name": row["name"],
                "nationality": row["nationality"],
                "dob": row["dob"],
                "reason": row["reason"],
                "risk_level": row["risk_level"]
            }
    return None


def add_blacklist_document(doc_number: str, country: str, reason: str, severity: str = "HIGH") -> bool:
    """Adds a document to the blacklist database."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO blacklist_documents (doc_number, country, reason, flagged_date, severity)
            VALUES (?, ?, ?, ?, ?)
        """, (doc_number.strip().upper(), country.strip().upper(), reason.strip(), today, severity.upper()))
        conn.commit()
        return True
    finally:
        conn.close()


def get_all_blacklist() -> List[Dict[str, Any]]:
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blacklist_documents ORDER BY flagged_date DESC")
    docs = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM watchlist_persons ORDER BY risk_level DESC")
    persons = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"documents": docs, "persons": persons}


# Initialize DB upon module load
init_db()
