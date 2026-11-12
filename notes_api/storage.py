import sqlite3
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS note_tags (
            note_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (note_id, tag_id),
            FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def _normalize_tags(tags: Optional[List[str]]) -> List[str]:
    if not tags:
        return []
    out = []
    seen = set()
    for t in tags:
        if not isinstance(t, str):
            continue
        name = t.strip().lower()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _ensure_tags(conn: sqlite3.Connection, tags: List[str]) -> List[int]:
    ids = []
    for name in tags:
        conn.execute("INSERT OR IGNORE INTO tags(name) VALUES (?)", (name,))
        row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
        ids.append(row["id"])
    return ids


def _set_note_tags(conn: sqlite3.Connection, note_id: int, tags: List[str]) -> None:
    conn.execute("DELETE FROM note_tags WHERE note_id = ?", (note_id,))
    tag_ids = _ensure_tags(conn, tags)
    for tid in tag_ids:
        conn.execute(
            "INSERT OR IGNORE INTO note_tags(note_id, tag_id) VALUES (?, ?)",
            (note_id, tid),
        )


def _get_tags_for_note(conn: sqlite3.Connection, note_id: int) -> List[str]:
    rows = conn.execute(
        """
        SELECT t.name FROM tags t
        JOIN note_tags nt ON nt.tag_id = t.id
        WHERE nt.note_id = ?
        ORDER BY t.name ASC
        """,
        (note_id,),
    ).fetchall()
    return [r["name"] for r in rows]


def _row_to_note(conn: sqlite3.Connection, row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "tags": _get_tags_for_note(conn, row["id"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_note(conn: sqlite3.Connection, title: str, content: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    now = _utc_now()
    tags_norm = _normalize_tags(tags)
    cur = conn.execute(
        "INSERT INTO notes(title, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (title, content, now, now),
    )
    note_id = cur.lastrowid
    _set_note_tags(conn, note_id, tags_norm)
    conn.commit()
    return get_note(conn, note_id)


def get_note(conn: sqlite3.Connection, note_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not row:
        return None
    return _row_to_note(conn, row)


def list_notes(conn: sqlite3.Connection, q: Optional[str] = None, tag: Optional[str] = None) -> List[Dict[str, Any]]:
    params = []
    joins = ""
    where = []
    if tag:
        joins += " JOIN note_tags nt ON nt.note_id = n.id JOIN tags t ON t.id = nt.tag_id"
        where.append("t.name = ?")
        params.append(tag.strip().lower())
    if q:
        like = f"%{q.strip()}%"
        where.append("(n.title LIKE ? OR n.content LIKE ?)")
        params.extend([like, like])
    sql = "SELECT DISTINCT n.* FROM notes n" + joins
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY n.id DESC"
    rows = conn.execute(sql, params).fetchall()
    return [_row_to_note(conn, r) for r in rows]


def update_note(conn: sqlite3.Connection, note_id: int, title: str, content: str, tags: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    existing = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not existing:
        return None
    now = _utc_now()
    conn.execute(
        "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ?",
        (title, content, now, note_id),
    )
    _set_note_tags(conn, note_id, _normalize_tags(tags))
    conn.commit()
    return get_note(conn, note_id)


def delete_note(conn: sqlite3.Connection, note_id: int) -> bool:
    cur = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    return cur.rowcount > 0


def list_tags(conn: sqlite3.Connection) -> List[str]:
    rows = conn.execute("SELECT name FROM tags ORDER BY name ASC").fetchall()
    return [r["name"] for r in rows]
