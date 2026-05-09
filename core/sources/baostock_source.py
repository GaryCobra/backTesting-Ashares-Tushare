"""Baostock 数据源 — 开源免费，需联网"""
import re
import pandas as pd
from core.data_source import DataSource
from core.cache import get_cached_daily, save_daily, has_cached_range, get_cached_stocks, save_stock_basic


class BaostockSource(DataSource):
    """Baostock 数据源"""

    @property
    def name(self) -> str:
        return "Baostock"

    def _login(self):
        import baostock as bs
        lg = bs.login()
        if lg.error_code != "0":
            raise ConnectionError(f"Baostock 登录失败: {lg.error_msg}")

    def _logout(self):
        import baostock as bs
        bs.logout()

    def validate(self) -> tuple[bool, str]:
        try:
            import baostock as bs
            lg = bs.login()
            bs.logout()
            if lg.error_code == "0":
                return True, "Baostock 连接成功"
            return False, f"Baostock 登录失败: {lg.error_msg}"
        except ImportError:
            return False, "未安装 baostock，请执行 pip install baostock"
        except Exception as e:
            return False, f"Baostock 验证失败: {e}"

    def get_stock_basic(self) -> pd.DataFrame:
        cached = get_cached_stocks()
        if not cached.empty:
            return cached
        try:
            self._login()
            import baostock as bs
            rs = bs.query_stock_basic()
            rows = []
            while rs.next():
                r = rs.get_row_data()
                rows.append(r)
            self._logout()

            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=[
                "code", "code_name", "ipoDate", "outDate", "type", "status"
            ])
            df = df[df["status"] == "1"].copy()

            renamed = pd.DataFrame()
            renamed["ts_code"] = df["code"].apply(self._baostock_to_tscode)
            renamed["symbol"] = df["code"].apply(lambda x: x.split(".")[1])
            renamed["name"] = df["code_name"]
            renamed["area"] = ""
            renamed["industry"] = ""
            renamed["market"] = df["code"].apply(
                lambda x: "SH" if x.startswith("sh") else "SZ"
            )
            renamed["list_date"] = df["ipoDate"]
            renamed["is_hs"] = ""

            save_stock_basic(renamed)
            return renamed
        except Exception as e:
            print(f"[Baostock] 获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        if has_cached_range(code, start_date, end_date):
            return get_cached_daily(code, start_date, end_date).sort_values("trade_date")

        bs_code = self._tscode_to_baostock(code)
        try:
            self._login()
            import baostock as bs
            # Baostock requires YYYY-MM-DD format
            bs_start = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            bs_end = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
            rs = bs.query_history_k_data_plus(
                bs_code,
                fields="date,open,high,low,close,volume,amount",
                start_date=bs_start,
                end_date=bs_end,
                frequency="d",
                adjustflag="2",
            )
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            self._logout()

            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows, columns=[
                "trade_date", "open", "high", "low", "close", "volume", "amount"
            ])
            df = df[df["trade_date"] != ""].copy()
            for col in ["open", "high", "low", "close", "volume", "amount"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["ts_code"] = code

            save_daily(code, df)
            return get_cached_daily(code, start_date, end_date).sort_values("trade_date")
        except Exception as e:
            print(f"[Baostock] 获取日线 {code} 失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def _tscode_to_baostock(code: str) -> str:
        """000001.SZ → sz.000001"""
        parts = code.split(".")
        if len(parts) == 2:
            return f"{parts[1].lower()}.{parts[0]}"
        return code

    @staticmethod
    def _baostock_to_tscode(code: str) -> str:
        """sz.000001 → 000001.SZ"""
        parts = code.split(".")
        if len(parts) == 2:
            return f"{parts[1]}.{parts[0].upper()}"
        return code
