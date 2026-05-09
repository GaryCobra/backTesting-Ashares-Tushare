"""技术指标计算函数 — 与信号模式匹配"""
import numpy as np
import pandas as pd


def sma(series, period: int):
    return series.rolling(window=period).mean()


def ema(series, period: int):
    return series.ewm(span=period, adjust=False).mean()


def macd(series, fast=12, slow=26, signal=9):
    ema_f = ema(series, fast)
    ema_s = ema(series, slow)
    dif = ema_f - ema_s
    dea = ema(dif, signal)
    bar = 2 * (dif - dea)
    return dif, dea, bar


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_g = gain.rolling(window=period).mean()
    avg_l = loss.rolling(window=period).mean().replace(0, np.nan)
    return 100 - (100 / (1 + avg_g / avg_l))


def bollinger(series, period=20, std=2):
    mid = sma(series, period)
    sd = series.rolling(period).std()
    return mid + std * sd, mid, mid - std * sd


def atr(high, low, close, period=14):
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def cross_over(s1, s2, i):
    """s1 上穿 s2"""
    if i < 1: return False
    v2 = s2 if isinstance(s2, (int, float)) else s2.iloc[i]
    p2 = s2 if isinstance(s2, (int, float)) else s2.iloc[i - 1]
    return s1.iloc[i - 1] <= p2 and s1.iloc[i] > v2


def cross_under(s1, s2, i):
    """s1 下穿 s2"""
    if i < 1: return False
    v2 = s2 if isinstance(s2, (int, float)) else s2.iloc[i]
    p2 = s2 if isinstance(s2, (int, float)) else s2.iloc[i - 1]
    return s1.iloc[i - 1] >= p2 and s1.iloc[i] < v2
