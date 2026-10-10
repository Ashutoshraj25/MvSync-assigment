"""
database.py - SQLite Persistent Storage & Historical Review-Monitoring Workflow
"""

import sqlite3
import os
import datetime
from typing import Dict, Any, List, Tuple
import pandas as pd


DB_FILE = "moveinsync_reviews.db"


def get_connection(db_path: str = DB_FILE) -> sqlite3.Connection:
    """Get connection to SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_FILE) -> None:
    """Initialize database tables for reviews and snapshot logs."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS snapshots (
        snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_timestamp TEXT NOT NULL,
        package_id TEXT NOT NULL,
        country TEXT NOT NULL,
        language TEXT NOT NULL,
        requested_limit TEXT,
        total_reviews INTEGER NOT NULL,
        avg_rating REAL NOT NULL,
        negative_share REAL NOT NULL,
        date_range TEXT,
        error_log TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        review_id TEXT PRIMARY KEY,
        snapshot_id INTEGER,
        user_name TEXT,
        rating INTEGER NOT NULL,
        review_text TEXT,
        review_date TEXT,
        app_version TEXT,
        helpful_votes INTEGER,
        developer_response TEXT,
        developer_response_date TEXT,
        primary_category TEXT,
        secondary_categories TEXT,
        sentiment TEXT,
        problem_type TEXT,
        severity TEXT,
        confidence REAL,
        classification_method TEXT,
        created_at TEXT,
        FOREIGN KEY (snapshot_id) REFERENCES snapshots (snapshot_id)
    )
    """)

    conn.commit()
    conn.close()


def save_snapshot(df: pd.DataFrame, metadata: Dict[str, Any], db_path: str = DB_FILE) -> int:
    """
    Save a snapshot run and upsert collected reviews into SQLite database.

    Returns:
        snapshot_id (int)
    """
    init_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insert snapshot metadata
    cursor.execute("""
    INSERT INTO snapshots (
        snapshot_timestamp, package_id, country, language, requested_limit,
        total_reviews, avg_rating, negative_share, date_range, error_log
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now_str,
        metadata.get("package_id", "com.moveinsync.ets"),
        metadata.get("selected_country", "in"),
        metadata.get("selected_language", "en"),
        str(metadata.get("requested_limit", "1000")),
        len(df),
        float(df["rating"].mean()) if not df.empty else 0.0,
        float((df["rating"] <= 2).sum() / len(df) * 100) if not df.empty else 0.0,
        metadata.get("date_range", "N/A"),
        " | ".join(metadata.get("errors", ["None"])) if metadata.get("errors") else "None"
    ))

    snapshot_id = cursor.lastrowid

    # Upsert reviews
    for _, row in df.iterrows():
        r_id = str(row.get("review_id"))
        rev_date = str(row.get("review_date"))
        reply_date = str(row.get("developer_response_date")) if pd.notna(row.get("developer_response_date")) else ""

        cursor.execute("""
        INSERT INTO reviews (
            review_id, snapshot_id, user_name, rating, review_text, review_date,
            app_version, helpful_votes, developer_response, developer_response_date,
            primary_category, secondary_categories, sentiment, problem_type, severity,
            confidence, classification_method, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(review_id) DO UPDATE SET
            rating=excluded.rating,
            review_text=excluded.review_text,
            app_version=excluded.app_version,
            primary_category=excluded.primary_category,
            secondary_categories=excluded.secondary_categories,
            sentiment=excluded.sentiment,
            problem_type=excluded.problem_type,
            severity=excluded.severity,
            confidence=excluded.confidence
        """, (
            r_id,
            snapshot_id,
            str(row.get("user_name", "")),
            int(row.get("rating", 0)),
            str(row.get("review_text", "")),
            rev_date,
            str(row.get("app_version", "Unknown")),
            int(row.get("helpful_votes", 0)),
            str(row.get("developer_response", "")) if pd.notna(row.get("developer_response")) else "",
            reply_date,
            str(row.get("primary_category", "Other or unclear")),
            str(row.get("secondary_categories", "None")),
            str(row.get("sentiment", "Neutral")),
            str(row.get("problem_type", "Unclear")),
            str(row.get("severity", "Medium")),
            float(row.get("confidence", 0.85)),
            str(row.get("classification_method", "Deterministic Keyword Rules (Regex)")),
            now_str
        ))

    conn.commit()
    conn.close()
    return snapshot_id


def get_snapshots_list(db_path: str = DB_FILE) -> pd.DataFrame:
    """Fetch list of all past snapshots."""
    init_db(db_path)
    conn = get_connection(db_path)
    df = pd.read_sql_query("SELECT * FROM snapshots ORDER BY snapshot_id DESC", conn)
    conn.close()
    return df


def get_latest_reviews(db_path: str = DB_FILE) -> pd.DataFrame:
    """Fetch all reviews from SQLite database."""
    init_db(db_path)
    conn = get_connection(db_path)
    df = pd.read_sql_query("SELECT * FROM reviews ORDER BY review_date DESC", conn)
    conn.close()
    return df


def compare_snapshots(snapshot_id_old: int, snapshot_id_new: int, db_path: str = DB_FILE) -> Dict[str, Any]:
    """Compare two historical snapshots to analyze rating shifts and emerging complaints."""
    init_db(db_path)
    conn = get_connection(db_path)

    df_old = pd.read_sql_query("SELECT * FROM reviews WHERE snapshot_id = ?", conn, params=(snapshot_id_old,))
    df_new = pd.read_sql_query("SELECT * FROM reviews WHERE snapshot_id = ?", conn, params=(snapshot_id_new,))
    conn.close()

    if df_old.empty or df_new.empty:
        return {"error": "One or both snapshot IDs contain no reviews."}

    avg_old = df_old["rating"].mean()
    avg_new = df_new["rating"].mean()
    neg_old = (df_old["rating"] <= 2).mean() * 100
    neg_new = (df_new["rating"] <= 2).mean() * 100

    cats_old = df_old["primary_category"].value_counts(normalize=True) * 100
    cats_new = df_new["primary_category"].value_counts(normalize=True) * 100

    diff_dict = {}
    all_cats = set(cats_old.index).union(set(cats_new.index))
    for c in all_cats:
        o_val = cats_old.get(c, 0.0)
        n_val = cats_new.get(c, 0.0)
        diff_dict[c] = {
            "Old Period (%)": round(o_val, 2),
            "New Period (%)": round(n_val, 2),
            "Delta Shift (%)": round(n_val - o_val, 2)
        }

    return {
        "old_snapshot_id": snapshot_id_old,
        "new_snapshot_id": snapshot_id_new,
        "avg_rating_old": round(avg_old, 2),
        "avg_rating_new": round(avg_new, 2),
        "avg_rating_delta": round(avg_new - avg_old, 2),
        "negative_share_old": round(neg_old, 2),
        "negative_share_new": round(neg_new, 2),
        "negative_share_delta": round(neg_new - neg_old, 2),
        "category_shifts_df": pd.DataFrame(diff_dict).T.sort_values(by="Delta Shift (%)", ascending=False)
    }
