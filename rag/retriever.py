"""检索层 — 自然语言描述 → 相似策略示例

用法:
  from rag.retriever import search_examples
  results = search_examples("5日均线上穿20日均线时买入")
  best = results[0]  # 最匹配的策略
"""
import json
import sqlite3
from pathlib import Path
from typing import Optional

RAG_DB_PATH = Path(__file__).parent.parent / "data" / "rag_cache.db"


def _get_conn():
    conn = sqlite3.connect(str(RAG_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def search_examples(query: str, top_k: int = 5,
                    source: Optional[str] = None,
                    min_score: float = 0) -> list[dict]:
    """FTS5 全文搜索 — 用自然语言查询匹配策略示例

    Args:
        query: 自然语言查询（如 "金叉买入 死叉卖出"）
        top_k: 返回 TOP N 条
        source: 过滤来源（builtin / user / ai）
        min_score: 最低评分过滤

    Returns:
        [{id, name, description, code, tags, source, score, rank}, ...]
    """
    conn = _get_conn()

    # FTS5 查询：将空格转为 OR 或 AND
    # unicode61 tokenchars 支持中文分词
    fts_query = _build_fts_query(query)

    sql = """
        SELECT e.*, rank
        FROM strategy_examples_fts f
        JOIN strategy_examples e ON f.rowid = e.id
        WHERE strategy_examples_fts MATCH ?
    """
    params = [fts_query]

    if source:
        sql += " AND e.source = ?"
        params.append(source)
    if min_score > 0:
        sql += " AND e.score >= ?"
        params.append(min_score)

    sql += " ORDER BY rank LIMIT ?"
    params.append(top_k)

    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        # FTS 语法错误降级为 LIKE
        rows = _fallback_search(conn, query, top_k, source, min_score)

    conn.close()
    results = [_row_to_dict(r) for r in rows]
    # 添加来源显示
    for r in results:
        r["match_type"] = "fts" if "rank" in r else "keyword"
    return results


def _build_fts_query(query: str) -> str:
    """将自然语言转为 FTS5 查询

    策略：用引号包裹每个词做前缀搜索，词之间 OR
    """
    import re
    # 移除特殊字符
    cleaned = re.sub(r'[^\w\u4e00-\u9fff\s]', ' ', query)
    tokens = cleaned.split()
    # 中文按字拆（FTS5 unicode61 对中文按单个字符索引）
    # 简单方式：每个词作为独立 term，用 OR 连接
    parts = []
    for t in tokens:
        if len(t) == 0:
            continue
        parts.append(f'"{t}"')
    if not parts:
        return query
    return " OR ".join(parts)


def _fallback_search(conn, query: str, top_k: int,
                     source: Optional[str] = None,
                     min_score: float = 0) -> list:
    """FTS 失败时的 LIKE 降级"""
    sql = """
        SELECT * FROM strategy_examples
        WHERE (description LIKE ? OR name LIKE ?)
    """
    like_q = f"%{query}%"
    params = [like_q, like_q]
    if source:
        sql += " AND source = ?"
        params.append(source)
    if min_score > 0:
        sql += " AND score >= ?"
        params.append(min_score)
    sql += " ORDER BY score DESC, id DESC LIMIT ?"
    params.append(top_k)
    return conn.execute(sql, params).fetchall()


def get_recommended_examples(top_k: int = 3) -> list[dict]:
    """获取默认推荐策略（按评分降序）"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM strategy_examples WHERE source='builtin' ORDER BY score DESC LIMIT ?",
        (top_k,)
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row) -> dict:
    d = dict(row)
    if "tags" in d and isinstance(d["tags"], str):
        try:
            d["tags"] = json.loads(d["tags"])
        except (json.JSONDecodeError, TypeError):
            d["tags"] = []
    return d
