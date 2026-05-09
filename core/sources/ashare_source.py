"""Ashare 数据源 — 新浪/腾讯双源，极简轻量"""
import re
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

from core.data_source import DataSource
from core.cache import get_cached_daily, save_daily, get_cached_stocks, save_stock_basic

# 将 Ashare 目录加入 path 以便 import
_src_dir = Path(__file__).parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))


def _import_ashare():
    """延迟导入 Ashare"""
    import Ashare
    return Ashare


class AshareSource(DataSource):
    """Ashare 数据源（新浪/腾讯双核心自动切换）"""

    @property
    def name(self) -> str:
        return "Ashare"

    def validate(self) -> tuple[bool, str]:
        try:
            ashare = _import_ashare()
            _ = ashare.get_price
            return True, "Ashare 导入成功"
        except ImportError:
            return False, "Ashare.py 未找到"
        except Exception as e:
            return False, f"Ashare 验证失败: {e}"

    def get_stock_basic(self) -> pd.DataFrame:
        cached = get_cached_stocks()
        if not cached.empty:
            return cached
        try:
            ashare = _import_ashare()
            df = ashare.get_price("sh000001", frequency="1d", count=1)
            if df is None:
                return pd.DataFrame()

            stocks = self._fetch_stock_list()
            if stocks.empty:
                return pd.DataFrame()

            renamed = pd.DataFrame()
            renamed["ts_code"] = stocks["code"].apply(self._symbol_to_tscode)
            renamed["symbol"] = stocks["code"]
            renamed["name"] = stocks["name"]
            renamed["area"] = ""
            renamed["industry"] = ""
            renamed["market"] = stocks["code"].apply(
                lambda x: "SZ" if str(x).startswith(("0", "3")) else "SH"
            )
            renamed["list_date"] = ""
            renamed["is_hs"] = ""

            save_stock_basic(renamed)
            return renamed
        except Exception as e:
            print(f"[Ashare] 获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        cached = get_cached_daily(code, start_date, end_date)
        if not cached.empty:
            cached_start = cached["trade_date"].min().strftime("%Y%m%d")
            cached_end = cached["trade_date"].max().strftime("%Y%m%d")
            if cached_start <= start_date and cached_end >= end_date:
                return cached.sort_values("trade_date")

        ashare_code = self._tscode_to_ashare(code)
        try:
            ashare = _import_ashare()
            # 计算所需天数（含缓冲）
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            count = (end_dt - start_dt).days + 60

            df = ashare.get_price(
                ashare_code,
                frequency="1d",
                count=count,
                end_date=end_date,
            )
            if df is None or df.empty:
                return pd.DataFrame()

            renamed = pd.DataFrame()
            renamed["trade_date"] = df.index.strftime("%Y%m%d")
            renamed["open"] = df["open"].astype(float)
            renamed["high"] = df["high"].astype(float)
            renamed["low"] = df["low"].astype(float)
            renamed["close"] = df["close"].astype(float)
            renamed["volume"] = df["volume"].astype(float)
            renamed["amount"] = 0.0  # Ashare 不提供成交额
            renamed["ts_code"] = code

            save_daily(code, renamed)
            return get_cached_daily(code, start_date, end_date).sort_values("trade_date")
        except Exception as e:
            print(f"[Ashare] 获取日线 {code} 失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def _tscode_to_ashare(code: str) -> str:
        """000001.SZ → sh000001 或 sz000001"""
        parts = code.split(".")
        if len(parts) != 2:
            return code
        market = parts[1].lower()
        symbol = parts[0]
        return f"{market}{symbol}"

    @staticmethod
    def _symbol_to_tscode(symbol) -> str:
        s = str(symbol).strip().zfill(6)
        if s.startswith(("6", "9")):
            return f"{s}.SH"
        elif s.startswith(("0", "3", "2")):
            return f"{s}.SZ"
        elif s.startswith(("4", "8")):
            return f"{s}.BJ"
        return f"{s}.SH"

    @staticmethod
    def _fetch_stock_list() -> pd.DataFrame:
        """从 Ashare 可识别的源获取股票列表"""
        import requests
        try:
            url = "http://80.push2.eastmoney.com/api/qt/clist/get"
            params = {
                "pn": "1",
                "pz": "6000",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
                "fields": "f12,f14",
                "np": "1",
                "fltt": "2",
                "invt": "2",
            }
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            items = data.get("data", {}).get("diff", [])
            records = []
            for item in items:
                code = item.get("f12", "")
                name = item.get("f14", "")
                if code and name:
                    records.append({"code": code, "name": name})
            return pd.DataFrame(records)
        except Exception as e:
            print(f"[Ashare] 东方财富股票列表拉取失败: {e}")
            return pd.DataFrame()
