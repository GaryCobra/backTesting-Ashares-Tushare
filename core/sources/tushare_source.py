"""Tushare Pro 数据源"""
import pandas as pd
import time
from core.data_source import DataSource
from core.cache import (
    init_db, get_cached_daily, save_daily, has_cached_range,
    get_cached_stocks, save_stock_basic,
    get_cache_stats,
)
from utils.config import get_token, get_api_url


class TushareSource(DataSource):
    """Tushare Pro 数据源（免费版 50 次/分，8000 次/天）"""

    @property
    def name(self) -> str:
        return "Tushare Pro"

    def __init__(self):
        self._pro = None
        self._last_call = 0
        self._min_interval = 0.3
        init_db()

    def _get_pro(self):
        if self._pro is None:
            import tushare as ts
            token = get_token()
            if token:
                ts.set_token(token)
            self._pro = ts.pro_api()
        return self._pro

    def _rate_limit(self):
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()

    def validate(self) -> tuple[bool, str]:
        token = get_token()
        if not token:
            return False, "未配置 Token，请在设置页配置"
        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            df = pro.stock_basic(limit=1)
            if df is not None and not df.empty:
                return True, "Tushare 连接成功"
            return False, "Tushare Token 无效"
        except Exception as e:
            return False, f"Tushare 连接失败: {e}"

    def get_stock_basic(self) -> pd.DataFrame:
        cached = get_cached_stocks()
        if not cached.empty:
            return cached
        self._rate_limit()
        try:
            pro = self._get_pro()
            df = pro.stock_basic(
                list_status='L',
                fields='ts_code,symbol,name,area,industry,market,list_date,is_hs'
            )
            if df is not None and not df.empty:
                save_stock_basic(df)
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            print(f"[Tushare] 获取股票列表失败: {e}")
            return pd.DataFrame()

    def get_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        if has_cached_range(code, start_date, end_date):
            return get_cached_daily(code, start_date, end_date).sort_values("trade_date")

        self._rate_limit()
        try:
            pro = self._get_pro()
            df = pro.daily(
                ts_code=code,
                start_date=start_date,
                end_date=end_date,
                fields='ts_code,trade_date,open,high,low,close,pre_close,volume,amount'
            )
            if df is not None and not df.empty:
                save_daily(code, df)
                return get_cached_daily(code, start_date, end_date).sort_values("trade_date")
            return pd.DataFrame()
        except Exception as e:
            print(f"[Tushare] 获取日线 {code} 失败: {e}")
            return cached

    def get_stats(self) -> dict:
        return get_cache_stats()
