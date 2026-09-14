import sqlite3
import json

DB_FILE = "invoice_agent.db"


def get_connection():
    return sqlite3.connect(DB_FILE)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT,
            vendor TEXT,
            invoice_number TEXT,
            total REAL,
            status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT,
            event_type TEXT,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS human_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT,
            decision TEXT,
            reviewer TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def invoice_exists(vendor, invoice_number):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM processed_invoices
        WHERE vendor = ?
        AND invoice_number = ?
    """, (vendor, invoice_number))

    count = cursor.fetchone()[0]

    conn.close()

    return count > 0


def save_invoice(invoice_id, invoice, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO processed_invoices (
            invoice_id,
            vendor,
            invoice_number,
            total,
            status
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        invoice_id,
        invoice["vendor"],
        invoice["invoice_number"],
        invoice["total"],
        status
    ))

    conn.commit()
    conn.close()


def log_event(invoice_id, event_type, details):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO audit_log (
            invoice_id,
            event_type,
            details
        )
        VALUES (?, ?, ?)
    """, (
        invoice_id,
        event_type,
        json.dumps(details)
    ))

    conn.commit()
    conn.close()


def save_human_decision(
        invoice_id,
        decision,
        reviewer,
        notes
    ):
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO human_decisions (
                invoice_id,
                decision,
                reviewer,
                notes
            )
            VALUES (?, ?, ?, ?)
        """, (
            invoice_id,
            decision,
            reviewer,
            notes
        ))

        conn.commit()
        conn.close()

def reset_test_data():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM processed_invoices"
    )

    cursor.execute(
        "DELETE FROM audit_log"
    )

    cursor.execute(
        "DELETE FROM human_decisions"
    )

    conn.commit()
    conn.close()
