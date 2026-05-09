"""内置策略库 — 所有策略实现"""
from core.strategy import Strategy
from core.indicators import sma, ema, macd, rsi, bollinger, cross_over, cross_under
import numpy as np


class MaCrossStrategy(Strategy):
    """双均线金叉买入 / 死叉卖出"""
    name = "双均线金叉死叉"

    def __init__(self, fast=5, slow=20):
        super().__init__()
        self.fast = fast
        self.slow = slow
        self.ma_fast = None
        self.ma_slow = None

    def init(self):
        c = self.data["close"]
        self.ma_fast = sma(c, self.fast)
        self.ma_slow = sma(c, self.slow)

    def buy_condition(self, i: int) -> bool:
        return cross_over(self.ma_fast, self.ma_slow, i)

    def sell_condition(self, i: int) -> bool:
        return cross_under(self.ma_fast, self.ma_slow, i)


class MaWithVolumeStrategy(Strategy):
    """双均线金叉 + 成交量过滤 / 死叉或破线卖出"""
    name = "均线金叉+成交量过滤"

    def __init__(self, fast=5, slow=20, vol_mult=1.0):
        super().__init__()
        self.fast = fast
        self.slow = slow
        self.vol_mult = vol_mult
        self.ma_fast = None
        self.ma_slow = None
        self.vol_ma = None

    def init(self):
        c = self.data["close"]
        v = self.data["volume"]
        self.ma_fast = sma(c, self.fast)
        self.ma_slow = sma(c, self.slow)
        self.vol_ma = sma(v, self.fast)

    def buy_condition(self, i: int) -> bool:
        if not cross_over(self.ma_fast, self.ma_slow, i):
            return False
        if i < 1:
            return False
        vol = self.data["volume"].iloc[i]
        return vol > self.vol_ma.iloc[i] * self.vol_mult

    def sell_condition(self, i: int) -> bool:
        if cross_under(self.ma_fast, self.ma_slow, i):
            return True
        if i < 1:
            return False
        price = self.data["close"].iloc[i]
        slow_val = self.ma_slow.iloc[i]
        return price < slow_val * 0.97


class MacdStrategy(Strategy):
    """MACD 金叉买入 / 死叉卖出"""
    name = "MACD金叉死叉"

    def __init__(self, fast=12, slow=26, signal=9):
        super().__init__()
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.dif = None
        self.dea = None

    def init(self):
        close = self.data["close"]
        self.dif, self.dea, _ = macd(close, self.fast, self.slow, self.signal)

    def buy_condition(self, i: int) -> bool:
        return cross_over(self.dif, self.dea, i)

    def sell_condition(self, i: int) -> bool:
        return cross_under(self.dif, self.dea, i)


class RsiStrategy(Strategy):
    """RSI 超买超卖反转"""
    name = "RSI超买超卖"

    def __init__(self, period=14, oversold=30, overbought=70):
        super().__init__()
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.rsi_val = None

    def init(self):
        self.rsi_val = rsi(self.data["close"], self.period)

    def buy_condition(self, i: int) -> bool:
        if i < 1:
            return False
        return self.rsi_val.iloc[i - 1] <= self.oversold and self.rsi_val.iloc[i] > self.oversold

    def sell_condition(self, i: int) -> bool:
        if i < 1:
            return False
        return self.rsi_val.iloc[i - 1] >= self.overbought and self.rsi_val.iloc[i] < self.overbought


class BollingerStrategy(Strategy):
    """布林带下轨反弹买入 / 上轨回落卖出"""
    name = "布林带反弹"

    def __init__(self, period=20, std=2):
        super().__init__()
        self.period = period
        self.std = std
        self.upper = None
        self.mid = None
        self.lower = None

    def init(self):
        close = self.data["close"]
        self.upper, self.mid, self.lower = bollinger(close, self.period, self.std)

    def buy_condition(self, i: int) -> bool:
        if i < 1:
            return False
        return (self.data["close"].iloc[i - 1] <= self.lower.iloc[i - 1]
                and self.data["close"].iloc[i] > self.lower.iloc[i])

    def sell_condition(self, i: int) -> bool:
        if i < 1:
            return False
        return (self.data["close"].iloc[i - 1] >= self.upper.iloc[i - 1]
                and self.data["close"].iloc[i] < self.upper.iloc[i])


class BreakMaStrategy(Strategy):
    """放量突破均线买入 / 跌破卖出"""
    name = "放量突破均线"

    def __init__(self, period=60, vol_mult=2.0):
        super().__init__()
        self.period = period
        self.vol_mult = vol_mult
        self.ma = None
        self.vol_ma = None

    def init(self):
        close = self.data["close"]
        volume = self.data["volume"]
        self.ma = sma(close, self.period)
        self.vol_ma = sma(volume, 5)

    def buy_condition(self, i: int) -> bool:
        if i < 1:
            return False
        prev_close = self.data["close"].iloc[i - 1]
        curr_close = self.data["close"].iloc[i]
        curr_vol = self.data["volume"].iloc[i]
        below = prev_close <= self.ma.iloc[i - 1]
        above = curr_close > self.ma.iloc[i]
        vol_surge = curr_vol > self.vol_ma.iloc[i] * self.vol_mult
        return below and above and vol_surge

    def sell_condition(self, i: int) -> bool:
        return self.data["close"].iloc[i] < self.ma.iloc[i]


class ConsecutiveStrategy(Strategy):
    """连跌买入 / 连涨卖出（逆势短线）"""
    name = "连跌买入连涨卖出"

    def __init__(self, days=3):
        super().__init__()
        self.days = days

    def init(self):
        pass

    def buy_condition(self, i: int) -> bool:
        if i < self.days:
            return False
        recent = self.data["close"].iloc[i - self.days + 1:i + 1]
        return all(recent.iloc[j] < recent.iloc[j - 1] for j in range(1, len(recent)))

    def sell_condition(self, i: int) -> bool:
        if i < self.days:
            return False
        recent = self.data["close"].iloc[i - self.days + 1:i + 1]
        return all(recent.iloc[j] > recent.iloc[j - 1] for j in range(1, len(recent)))
