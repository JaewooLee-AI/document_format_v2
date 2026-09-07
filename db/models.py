"""SQLite 스키마 생성 및 CRUD. documents(업로드/편집 문서 메타데이터+필드값), llm_settings(LLM 키/모델)."""
import json
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "app.db")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_key TEXT UNIQUE NOT NULL,
                doc_type TEXT NOT NULL,
                original_filename TEXT,
                original_format TEXT,
                uploaded_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_file_path TEXT,
                field_data TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_settings (
                provider TEXT PRIMARY KEY,
                api_key TEXT,
                model TEXT,
                is_default INTEGER NOT NULL DEFAULT 0,
                last_tested_at TEXT,
                last_test_ok INTEGER
            )
        """)
    conn.close()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def key_exists(doc_key: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM documents WHERE doc_key = ?", (doc_key,)).fetchone()
    conn.close()
    return row is not None


def insert_document(doc_key, doc_type, original_filename, original_format, source_file_path, field_data: dict) -> int:
    conn = get_connection()
    ts = now_iso()
    with conn:
        cur = conn.execute(
            """INSERT INTO documents
               (doc_key, doc_type, original_filename, original_format, uploaded_at, updated_at,
                source_file_path, field_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_key, doc_type, original_filename, original_format, ts, ts,
             source_file_path, json.dumps(field_data, ensure_ascii=False)),
        )
        doc_id = cur.lastrowid
    conn.close()
    return doc_id


def update_field_data(doc_id: int, field_data: dict):
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE documents SET field_data = ?, updated_at = ? WHERE id = ?",
            (json.dumps(field_data, ensure_ascii=False), now_iso(), doc_id),
        )
    conn.close()


def get_document(doc_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["field_data"] = json.loads(d["field_data"])
    return d


def list_documents(doc_type: str = None, search: str = None) -> list:
    conn = get_connection()
    query = "SELECT id, doc_key, doc_type, original_filename, original_format, uploaded_at, updated_at FROM documents"
    clauses, params = [], []
    if doc_type:
        clauses.append("doc_type = ?")
        params.append(doc_type)
    if search:
        clauses.append("doc_key LIKE ?")
        params.append(f"%{search}%")
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def next_available_key(base_key: str) -> str:
    if not key_exists(base_key):
        return base_key
    i = 2
    while key_exists(f"{base_key}_{i}"):
        i += 1
    return f"{base_key}_{i}"


# -- LLM 설정 -----------------------------------------------------------
def get_llm_settings() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM llm_settings").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_llm_setting(provider: str) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM llm_settings WHERE provider = ?", (provider,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_default_provider() -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM llm_settings WHERE is_default = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_llm_setting(provider: str, api_key: str = None, model: str = None):
    conn = get_connection()
    with conn:
        existing = conn.execute("SELECT provider FROM llm_settings WHERE provider = ?", (provider,)).fetchone()
        if existing:
            fields, params = [], []
            if api_key is not None:
                fields.append("api_key = ?")
                params.append(api_key)
            if model is not None:
                fields.append("model = ?")
                params.append(model)
            if fields:
                params.append(provider)
                conn.execute(f"UPDATE llm_settings SET {', '.join(fields)} WHERE provider = ?", params)
        else:
            conn.execute(
                "INSERT INTO llm_settings (provider, api_key, model, is_default) VALUES (?, ?, ?, 0)",
                (provider, api_key or "", model or ""),
            )
    conn.close()


def set_test_result(provider: str, ok: bool):
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE llm_settings SET last_tested_at = ?, last_test_ok = ? WHERE provider = ?",
            (now_iso(), 1 if ok else 0, provider),
        )
    conn.close()


def set_default_provider(provider: str):
    conn = get_connection()
    with conn:
        conn.execute("UPDATE llm_settings SET is_default = 0")
        conn.execute("UPDATE llm_settings SET is_default = 1 WHERE provider = ?", (provider,))
    conn.close()
