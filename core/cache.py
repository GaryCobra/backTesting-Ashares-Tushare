"""SQLite 本地缓存层 — 存储所有从 Tushare 拉取的数据"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "backtest_cache.db"


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cache_daily (
            ts_code TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL,
            pre_close REAL, volume REAL, amount REAL,
            fetched_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (ts_code, trade_date)
        );

        CREATE TABLE IF NOT EXISTS cache_stock_basic (
            ts_code TEXT PRIMARY KEY,
            symbol TEXT, name TEXT, area TEXT, industry TEXT,
            market TEXT, list_date TEXT, is_hs TEXT,
            fetched_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cache_fund_basic (
            ts_code TEXT PRIMARY KEY,
            name TEXT, fund_type TEXT, mgmt_company TEXT,
            listed_date TEXT, fetched_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS cache_index_member (
            index_code TEXT NOT NULL,
            ts_code TEXT NOT NULL,
            PRIMARY KEY (index_code, ts_code)
        );

        CREATE TABLE IF NOT EXISTS cache_meta (
            api_name TEXT NOT NULL,
            ts_code TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (api_name, ts_code)
        );

        CREATE TABLE IF NOT EXISTS cache_sector (
            ts_code TEXT NOT NULL,
            sector_name TEXT NOT NULL,
            sector_type TEXT DEFAULT 'ths',
            PRIMARY KEY (ts_code, sector_name, sector_type)
        );
    """)
    conn.commit()
    conn.close()


def get_cached_daily(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取缓存的日线数据"""
    conn = _get_conn()
    df = pd.read_sql(
        "SELECT * FROM cache_daily WHERE ts_code=? AND trade_date BETWEEN ? AND ? ORDER BY trade_date",
        conn, params=(ts_code, start_date, end_date)
    )
    conn.close()
    if not df.empty:
        df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def save_daily(ts_code: str, df: pd.DataFrame):
    """批量写入日线缓存（增量）"""
    if df.empty:
        return
    conn = _get_conn()
    df = df.copy()
    if "trade_date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["trade_date"]):
        df["trade_date"] = pd.to_datetime(df["trade_date"])
    if "trade_date" in df.columns:
        df["trade_date"] = df["trade_date"].dt.strftime("%Y%m%d")
    # 只写入需要的列
    cols = [c for c in ["ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "volume", "amount"] if c in df.columns]
    if not cols:
        conn.close()
        return
    df[cols].to_sql("cache_daily", conn, if_exists="append", index=False, method="multi")
    # 更新元数据
    start = df["trade_date"].min()
    end = df["trade_date"].max()
    conn.execute(
        "INSERT OR REPLACE INTO cache_meta (api_name, ts_code, start_date, end_date, updated_at) VALUES (?, ?, ?, ?, datetime('now'))",
        ("daily", ts_code, start, end)
    )
    conn.commit()
    conn.close()


def get_cached_stocks() -> pd.DataFrame:
    """获取缓存的股票列表"""
    conn = _get_conn()
    df = pd.read_sql("SELECT * FROM cache_stock_basic", conn)
    conn.close()
    return df


def save_stock_basic(df: pd.DataFrame):
    if df.empty:
        return
    conn = _get_conn()
    df.to_sql("cache_stock_basic", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()


def get_cached_funds() -> pd.DataFrame:
    conn = _get_conn()
    df = pd.read_sql("SELECT * FROM cache_fund_basic", conn)
    conn.close()
    return df


def save_fund_basic(df: pd.DataFrame):
    if df.empty:
        return
    conn = _get_conn()
    df.to_sql("cache_fund_basic", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()


def get_cache_stats() -> dict:
    """获取缓存统计信息"""
    conn = _get_conn()
    stats = {}
    try:
        stats["daily_records"] = conn.execute("SELECT COUNT(*) FROM cache_daily").fetchone()[0]
        stats["stocks"] = conn.execute("SELECT COUNT(*) FROM cache_stock_basic").fetchone()[0]
        stats["funds"] = conn.execute("SELECT COUNT(*) FROM cache_fund_basic").fetchone()[0]
        earliest = conn.execute("SELECT MIN(trade_date) FROM cache_daily").fetchone()[0]
        latest = conn.execute("SELECT MAX(trade_date) FROM cache_daily").fetchone()[0]
        stats["earliest"] = earliest or "--"
        stats["latest"] = latest or "--"
    except Exception:
        stats = {"daily_records": 0, "stocks": 0, "funds": 0, "earliest": "--", "latest": "--"}
    conn.close()
    # 估算文件大小
    db_path = str(DB_PATH)
    try:
        stats["size_mb"] = round(Path(db_path).stat().st_size / 1024 / 1024, 1)
    except Exception:
        stats["size_mb"] = 0
    return stats


def clear_cache():
    """清空所有缓存"""
    conn = _get_conn()
    for table in ["cache_daily", "cache_stock_basic", "cache_fund_basic", "cache_index_member", "cache_meta", "cache_sector"]:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


def has_daily_data(ts_code: str) -> bool:
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) FROM cache_daily WHERE ts_code=?", (ts_code,)).fetchone()
    conn.close()
    return row and row[0] > 0
