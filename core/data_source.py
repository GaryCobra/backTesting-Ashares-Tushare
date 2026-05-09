"""数据源抽象层 — ABC + 工厂

用法:
    from core.data_source import create_source
    source = create_source("tushare")
    df = source.get_daily("000001.SZ", "20240101", "20241231")
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional


class DataSource(ABC):
    """统一数据源接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """显示名称，如 'Tushare'"""

    @abstractmethod
    def validate(self) -> tuple[bool, str]:
        """验证连接是否正常"""

    @abstractmethod
    def get_stock_basic(self) -> pd.DataFrame:
        """获取股票基础信息

        Returns:
            DataFrame with columns: ts_code, symbol, name, area, industry, market, list_date
        """

    @abstractmethod
    def get_daily(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取日线数据

        Args:
            code: 股票代码 (如 "000001.SZ", "600519.SH")
            start_date: 起始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            DataFrame with columns: ts_code, trade_date, open, high, low, close, volume, amount
            按 trade_date 升序排列
        """

    def get_stats(self) -> dict:
        """缓存统计（可选覆盖）"""
        return {"daily_records": 0, "stocks": 0, "size_mb": 0, "earliest": "--"}


def create_source(source_type: str) -> DataSource:
    """工厂 — 根据名称创建数据源实例"""
    if source_type == "tushare":
        from core.sources.tushare_source import TushareSource
        return TushareSource()
    elif source_type == "akshare":
        from core.sources.akshare_source import AkshareSource
        return AkshareSource()
    elif source_type == "baostock":
        from core.sources.baostock_source import BaostockSource
        return BaostockSource()
    elif source_type == "ashare":
        from core.sources.ashare_source import AshareSource
        return AshareSource()
    else:
        msg = f"未知数据源: {source_type}，可选: tushare, akshare, baostock, ashare"
        raise ValueError(msg)


AVAILABLE_SOURCES = {
    "tushare": "Tushare Pro（需 Token，免费版 50 次/分）",
    "akshare": "AkShare（开源免费，无需注册）",
    "baostock": "Baostock（开源免费，需联网）",
    "ashare": "Ashare（新浪/腾讯双源，极简轻量）",
}
