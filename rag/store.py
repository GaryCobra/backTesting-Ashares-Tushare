"""策略示例存储 — SQLite 持久化

Schema:
  strategy_examples:
    - id          INTEGER PRIMARY KEY
    - name        TEXT      策略名称（如 "双均线金叉"）
    - description TEXT      自然语言描述（用户输入的买卖条件）
    - code        TEXT      对应的 Python 策略代码
    - tags        TEXT      JSON 数组标签（如 ["均线", "趋势"]）
    - source      TEXT      来源（builtin / user / ai）
    - score       REAL      评分（0-100）
    - created_at  TEXT      创建时间
    - updated_at  TEXT      更新时间

  strategy_examples_fts:     FTS5 全文索引（自动维护）
"""
import sqlite3
import json
import datetime
from pathlib import Path

RAG_DB_PATH = Path(__file__).parent.parent / "data" / "rag_cache.db"


# ── Schema ──
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS strategy_examples (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    code        TEXT NOT NULL,
    tags        TEXT DEFAULT '[]',
    source      TEXT DEFAULT 'builtin',
    score       REAL DEFAULT 50,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE VIRTUAL TABLE IF NOT EXISTS strategy_examples_fts
USING fts5(
    name, description, code, tags,
    content='strategy_examples',
    content_rowid='id',
    tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS strategy_examples_ai AFTER INSERT ON strategy_examples BEGIN
    INSERT INTO strategy_examples_fts(rowid, name, description, code, tags)
    VALUES (new.id, new.name, new.description, new.code, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS strategy_examples_ad AFTER DELETE ON strategy_examples BEGIN
    INSERT INTO strategy_examples_fts(strategy_examples_fts, rowid, name, description, code, tags)
    VALUES ('delete', old.id, old.name, old.description, old.code, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS strategy_examples_au AFTER UPDATE ON strategy_examples BEGIN
    INSERT INTO strategy_examples_fts(strategy_examples_fts, rowid, name, description, code, tags)
    VALUES ('delete', old.id, old.name, old.description, old.code, old.tags);
    INSERT INTO strategy_examples_fts(rowid, name, description, code, tags)
    VALUES (new.id, new.name, new.description, new.code, new.tags);
END;
"""


def _get_conn():
    RAG_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(RAG_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_rag():
    """初始化 RAG 库（幂等）"""
    conn = _get_conn()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


# ── CRUD ──

def add_example(name: str, description: str, code: str,
                tags: list[str] = None, source: str = "user",
                score: float = 50) -> int:
    """添加策略示例，返回 ID"""
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO strategy_examples (name, description, code, tags, source, score) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, description, code, json.dumps(tags or [], ensure_ascii=False), source, score)
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def delete_example(rid: int):
    conn = _get_conn()
    conn.execute("DELETE FROM strategy_examples WHERE id=?", (rid,))
    conn.commit()
    conn.close()


def update_example(rid: int, **kwargs):
    """更新字段（name/description/code/tags/source/score）"""
    allowed = {"name", "description", "code", "tags", "source", "score"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = datetime.datetime.now().isoformat()
    set_clause = ", ".join(f"{k}=?" for k in updates)
    vals = [json.dumps(v, ensure_ascii=False) if k == "tags" else v for v in updates.values()]
    conn = _get_conn()
    conn.execute(f"UPDATE strategy_examples SET {set_clause} WHERE id=?", (*vals, rid))
    conn.commit()
    conn.close()


def get_example(rid: int) -> dict:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM strategy_examples WHERE id=?", (rid,)).fetchone()
    conn.close()
    return _row_to_dict(row) if row else {}


def list_examples(limit: int = 50, source: str = None) -> list[dict]:
    conn = _get_conn()
    if source:
        rows = conn.execute(
            "SELECT * FROM strategy_examples WHERE source=? ORDER BY score DESC, id DESC LIMIT ?",
            (source, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM strategy_examples ORDER BY score DESC, id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def count_examples() -> int:
    conn = _get_conn()
    cnt = conn.execute("SELECT COUNT(*) FROM strategy_examples").fetchone()[0]
    conn.close()
    return cnt


def _row_to_dict(row) -> dict:
    d = dict(row)
    if "tags" in d and isinstance(d["tags"], str):
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
    return d
