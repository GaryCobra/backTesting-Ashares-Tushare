"""策略生成器 — 根据用户自然语言描述匹配并生成策略实例"""
import re
from typing import Optional

from strategies.builtin import (
    MaCrossStrategy,
    MaWithVolumeStrategy,
    MacdStrategy,
    RsiStrategy,
    BollingerStrategy,
    BreakMaStrategy,
    ConsecutiveStrategy,
    Strategy,
)
from rag.retriever import search_examples

# 关键词 → 策略类 + 参数提取规则
PATTERN_MAP = [
    {
        "class": MaCrossStrategy,
        "keywords": ["金叉", "死叉", "均线", "ma"],
        "params": lambda desc: _extract_ma_params(desc, default_fast=5, default_slow=20),
    },
    {
        "class": MaWithVolumeStrategy,
        "keywords": ["金叉", "死叉", "均线", "成交量", "放量", "ma", "vol"],
        "params": lambda desc: _extract_ma_vol_params(desc),
    },
    {
        "class": MacdStrategy,
        "keywords": ["macd", "dif", "dea", "平滑异同"],
        "params": lambda desc: _extract_macd_params(desc),
    },
    {
        "class": RsiStrategy,
        "keywords": ["rsi", "超买", "超卖", "相对强弱"],
        "params": lambda desc: _extract_rsi_params(desc),
    },
    {
        "class": BollingerStrategy,
        "keywords": ["布林", "boll", "bollinger", "带", "轨道"],
        "params": lambda _: {},
    },
    {
        "class": BreakMaStrategy,
        "keywords": ["突破", "放量", "均线", "支撑", "压力"],
        "params": lambda desc: _extract_break_ma_params(desc),
    },
    {
        "class": ConsecutiveStrategy,
        "keywords": ["连跌", "连涨", "连续", "逆势", "短线"],
        "params": lambda desc: _extract_consecutive_params(desc),
    },
]


def generate_strategy(buy_desc: str, sell_desc: str) -> Strategy:
    """根据买卖条件描述生成策略实例

    Args:
        buy_desc: 用户输入的买入条件描述
        sell_desc: 用户输入的卖出条件描述

    Returns:
        配置好的 Strategy 实例
    """
    combined = buy_desc + " " + sell_desc
    desc_lower = combined.lower().replace(" ", "")

    # 1. 关键词匹配：按关键词命中数排序
    matches = []
    for pattern in PATTERN_MAP:
        hits = sum(1 for kw in pattern["keywords"] if kw in desc_lower)
        if hits > 0:
            matches.append((hits, pattern))

    if matches:
        matches.sort(key=lambda x: x[0], reverse=True)
        best = matches[0][1]
        try:
            params = best["params"](combined)
            return best["class"](**params)
        except Exception:
            pass

    # 2. RAG 检索兜底：用最相似的内置策略
    return _rag_fallback(combined)


def _extract_ma_params(desc: str, default_fast=5, default_slow=20) -> dict:
    """从描述中提取均线参数"""
    fast = _extract_int(desc, ["快速均线", "快线", "短期均线"], default_fast)
    slow = _extract_int(desc, ["慢速均线", "慢线", "长期均线"], default_slow)

    # 尝试从描述中直接提取参数 X日/Y日
    nums = re.findall(r'(\d+)\s*日', desc)
    nums = [int(n) for n in nums if 2 <= int(n) <= 250]
    if len(nums) >= 2:
        fast, slow = min(nums[:2]), max(nums[:2])
    elif len(nums) == 1:
        if "慢" in desc or "长" in desc:
            slow = nums[0]
        else:
            fast = nums[0]

    return {"fast": fast, "slow": slow}


def _extract_ma_vol_params(desc: str) -> dict:
    base = _extract_ma_params(desc)
    vol_mult = _extract_float(desc, ["倍", "倍数", "vol"], 1.0)
    return {**base, "vol_mult": vol_mult}


def _extract_macd_params(desc: str) -> dict:
    return {
        "fast": _extract_int(desc, ["快线", "fast"], 12),
        "slow": _extract_int(desc, ["慢线", "slow"], 26),
        "signal": _extract_int(desc, ["信号", "signal"], 9),
    }


def _extract_rsi_params(desc: str) -> dict:
    period = _extract_int(desc, ["周期", "period", "rsi"], 14)
    oversold = _extract_int(desc, ["超卖", "oversold"], 30)
    overbought = _extract_int(desc, ["超买", "overbought"], 70)
    return {"period": period, "oversold": oversold, "overbought": overbought}


def _extract_break_ma_params(desc: str) -> dict:
    nums = re.findall(r'(\d+)\s*日', desc)
    period = 60
    if nums:
        period = max(int(n) for n in nums if 10 <= int(n) <= 250)
    vol_mult = _extract_float(desc, ["倍", "倍数"], 2.0)
    return {"period": period, "vol_mult": vol_mult}


def _extract_consecutive_params(desc: str) -> dict:
    days = _extract_int(desc, ["天", "日", "连"], 3)
    return {"days": max(2, min(days, 10))}


def _extract_int(desc: str, keywords: list[str], default: int) -> int:
    """从描述中提取整数参数"""
    desc_lower = desc.lower()
    # 尝试匹配 "关键词 数字" 模式
    for kw in keywords:
        m = re.search(rf'{re.escape(kw)}\D*?(\d+)', desc_lower)
        if m:
            return int(m.group(1))
    return default


def _extract_float(desc: str, keywords: list[str], default: float) -> float:
    desc_lower = desc.lower()
    for kw in keywords:
        m = re.search(rf'{re.escape(kw)}\D*?(\d+\.?\d*)', desc_lower)
        if m:
            return float(m.group(1))
    return default


def _rag_fallback(desc: str) -> Strategy:
    """RAG 检索兜底"""
    try:
        results = search_examples(desc[:100], top_k=1)
        if results:
            name = results[0]["name"]
            # 按名称匹配
            for pattern in PATTERN_MAP:
                cls_name = pattern["class"].name
                if any(kw in name for kw in [cls_name, cls_name[:4]]):
                    return pattern["class"]()
    except Exception:
        pass
    return MaWithVolumeStrategy()
