"""策略基类 — 用户只需定义 buy_condition() 和 sell_condition()"""
from abc import ABC, abstractmethod


class Strategy(ABC):
    """策略基类

    子类需实现:
      - init(): 初始化指标
      - buy_condition(i): 在第 i 根K线是否买入
      - sell_condition(i): 在第 i 根K线是否卖出
    """

    name = "未命名策略"

    def __init__(self):
        self.data = None          # DataFrame: date index, OHLCV columns
        self.indicators = {}
        self.ts_code = ""         # 当前扫描的股票代码

    def init(self):
        """初始化指标（每只股票开始扫描时调用一次）"""
        pass

    @abstractmethod
    def buy_condition(self, i: int) -> bool:
        """买入条件 — 在第 i 根K线是否触发买入信号"""
        pass

    @abstractmethod
    def sell_condition(self, i: int) -> bool:
        """卖出条件 — 在第 i 根K线是否触发卖出信号"""
        pass

    @property
    def close(self):
        return self.data["close"] if self.data is not None else None

    @property
    def open(self):
        return self.data["open"] if self.data is not None else None

    @property
    def high(self):
        return self.data["high"] if self.data is not None else None

    @property
    def low(self):
        return self.data["low"] if self.data is not None else None

    @property
    def volume(self):
        return self.data["volume"] if self.data is not None else None
