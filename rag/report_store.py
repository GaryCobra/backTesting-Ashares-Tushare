"""回测报告持久化 — SQLite 存储

Schema:
  backtest_reports:
    - id              TEXT PRIMARY KEY   (YYYYMMDD_HHMMSS)
    - name            TEXT NOT NULL      报告名称
    - buy_desc        TEXT               买入条件描述
    - sell_desc       TEXT               卖出条件描述
    - start_date      TEXT               起始日期
    - end_date        TEXT               结束日期
    - capital         REAL               总资金
    - shares_per_trade INTEGER           每笔股数
    - strategy_name   TEXT               匹配的策略名称
    - summary_json    TEXT               概览统计 JSON (标量)
    - trades_json     TEXT               逐笔交易 JSON (完整明细)
    - created_at      TEXT               创建时间
    - updated_at      TEXT               更新时间
"""
import sqlite3
import json
import datetime
from pathlib import Path
from typing import Optional

RAG_DB_PATH = Path(__file__).parent.parent / "data" / "rag_cache.db"


def _get_conn():
    RAG_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(RAG_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_reports_table():
    """创建回测报告表（幂等）"""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backtest_reports (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            buy_desc        TEXT,
            sell_desc       TEXT,
            start_date      TEXT,
            end_date        TEXT,
            capital         REAL DEFAULT 100000,
            shares_per_trade INTEGER DEFAULT 100,
            strategy_name   TEXT DEFAULT '',
            summary_json    TEXT,
            trades_json     TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def save_report(report: dict) -> str:
    """保存回测报告

    Args:
        report: {
            id, name, buy_desc, sell_desc, start_date, end_date,
            capital, shares_per_trade, strategy_name,
            results: {...}  # SignalEngine.run() 的输出
        }
    Returns:
        report_id
    """
    results = report.get("results", {})
    report_id = report.get("id") or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 提取概览统计（标量 + 可序列化的小表）
    summary = {
        "total_stocks": results.get("total_stocks", 0),
        "total_signals": results.get("total_signals", 0),
        "win_trades": results.get("win_trades", 0),
        "loss_trades": results.get("loss_trades", 0),
        "win_rate": results.get("win_rate", 0),
        "avg_pnl": results.get("avg_pnl", 0),
    }

    # 提取逐笔交易明细
    trades_data = []
    stock_trades = results.get("stock_trades", {})
    for ts_code, trades in stock_trades.items():
        for t in trades:
            trades_data.append({
                "ts_code": ts_code,
                "buy_date": t.buy_date,
                "buy_price": round(t.buy_price, 3),
                "sell_date": t.sell_date,
                "sell_price": round(t.sell_price, 3),
                "pnl_pct": round(t.pnl_pct, 2),
                "pnl_amount": round(t.pnl_amount, 2),
                "hold_days": t.hold_days,
                "shares": t.shares,
                "buy_signal": t.buy_signal,
                "sell_signal": t.sell_signal,
                "status": t.status,
            })

    conn = _get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO backtest_reports
            (id, name, buy_desc, sell_desc, start_date, end_date,
             capital, shares_per_trade, strategy_name,
             summary_json, trades_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        report_id,
        report.get("name", f"回测_{report_id}"),
        report.get("buy_desc", ""),
        report.get("sell_desc", ""),
        report.get("start_date", ""),
        report.get("end_date", ""),
        report.get("capital", 100000),
        report.get("shares_per_trade", 100),
        report.get("strategy_name", ""),
        json.dumps(summary, ensure_ascii=False),
        json.dumps(trades_data, ensure_ascii=False),
    ))
    conn.commit()
    conn.close()
    return report_id


def load_report(report_id: str) -> Optional[dict]:
    """加载单条回测报告（完整重建 results）"""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM backtest_reports WHERE id=?", (report_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_report(row)


def list_reports(limit: int = 50) -> list[dict]:
    """列出所有报告摘要（不含交易明细）"""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, name, buy_desc, sell_desc, start_date, end_date, "
        "capital, shares_per_trade, strategy_name, summary_json, created_at "
        "FROM backtest_reports ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("summary_json"):
            try:
                d["summary"] = json.loads(d["summary_json"])
            except (json.JSONDecodeError, TypeError):
                d["summary"] = {}
        result.append(d)
    return result


def delete_report(report_id: str):
    conn = _get_conn()
    conn.execute("DELETE FROM backtest_reports WHERE id=?", (report_id,))
    conn.commit()
    conn.close()


def _row_to_report(row) -> dict:
    d = dict(row)

    # 解析 summary
    summary = {}
    if d.get("summary_json"):
        try:
            summary = json.loads(d["summary_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    # 解析 trades
    all_trades_list = []
    if d.get("trades_json"):
        try:
            all_trades_list = json.loads(d["trades_json"])
        except (json.JSONDecodeError, TypeError):
            pass

    # 重建 stock_trades dict
    stock_trades = {}
    for t in all_trades_list:
        code = t["ts_code"]
        if code not in stock_trades:
            stock_trades[code] = []
        stock_trades[code].append(t)

    # 重建 results 结构
    results = {
        "total_stocks": summary.get("total_stocks", 0),
        "total_signals": summary.get("total_signals", 0),
        "win_trades": summary.get("win_trades", 0),
        "loss_trades": summary.get("loss_trades", 0),
        "win_rate": summary.get("win_rate", 0),
        "avg_pnl": summary.get("avg_pnl", 0),
        "stock_trades": stock_trades,
        "stock_summary": [],  # 需要时从 trades 重新计算
        "all_trades": all_trades_list,
    }

    return {
        "id": d["id"],
        "name": d["name"],
        "buy_desc": d.get("buy_desc", ""),
        "sell_desc": d.get("sell_desc", ""),
        "start_date": d.get("start_date", ""),
        "end_date": d.get("end_date", ""),
        "capital": d.get("capital", 100000),
        "shares_per_trade": d.get("shares_per_trade", 100),
        "strategy_name": d.get("strategy_name", ""),
        "results": results,
        "created_at": d.get("created_at", ""),
    }
