"""AkShare 数据源 — 开源免费，无需注册"""
import re
import pandas as pd
from core.data_source import DataSource
from core.cache import get_cached_daily, save_daily, has_cached_range, get_cached_stocks, save_stock_basic


class AkshareSource(DataSource):
    """AkShare 数据源"""

    @property
    def name(self) -> str:
        return "AkShare"

    def validate(self) -> tuple[bool, str]:
        try:
            import akshare as ak
            _ = ak.__version__
            return True, "AkShare 导入成功"
        except ImportError:
            return False, "未安装 akshare，请执行 pip install akshare"
        except Exception as e:
            return False, f"AkShare 验证失败: {e}"

    def get_stock_basic(self) -> pd.DataFrame:
        cached = get_cached_stocks()
        if not cached.empty:
            return cached
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            if df.empty:
                return pd.DataFrame()

            renamed = pd.DataFrame()
            renamed["ts_code"] = df["code"].apply(self._symbol_to_tscode)
            renamed["symbol"] = df["code"].astype(str).str.strip()
            renamed["name"] = df["name"].astype(str).str.strip()
            renamed["area"] = ""
            renamed["industry"] = ""
            renamed["market"] = df["code"].astype(str).apply(
                lambda x: "SZ" if x.strip().startswith(("0", "3")) else "SH"
            )
            renamed["list_date"] = ""
            renamed["is_hs"] = ""

            save_stock_basic(renamed)
            return renamed
        except Exception as e:
            print(f"[AkShare] 获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        if has_cached_range(code, start_date, end_date):
            return get_cached_daily(code, start_date, end_date).sort_values("trade_date")

        symbol = self._tscode_to_symbol(code)
        try:
            import akshare as ak
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            if df.empty:
                return pd.DataFrame()

            renamed = pd.DataFrame()
            renamed["trade_date"] = pd.to_datetime(df["日期"]).dt.strftime("%Y%m%d")
            renamed["open"] = df["开盘"].astype(float)
            renamed["high"] = df["最高"].astype(float)
            renamed["low"] = df["最低"].astype(float)
            renamed["close"] = df["收盘"].astype(float)
            renamed["volume"] = df["成交量"].astype(float)
            renamed["amount"] = df["成交额"].astype(float)
            renamed["ts_code"] = code

            save_daily(code, renamed)
            return get_cached_daily(code, start_date, end_date).sort_values("trade_date")
        except Exception as e:
            print(f"[AkShare] 获取日线 {code} 失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def _tscode_to_symbol(code: str) -> str:
        """000001.SZ → 000001"""
        return code.split(".")[0]

    @staticmethod
    def _symbol_to_tscode(symbol) -> str:
        """000001 → 000001.SZ 或 600519.SH"""
        s = str(symbol).strip().zfill(6)
        if s.startswith(("6", "9")):
            return f"{s}.SH"
        elif s.startswith(("0", "3", "2")):
            return f"{s}.SZ"
        elif s.startswith(("4", "8")):
            return f"{s}.BJ"
        return f"{s}.SH"
