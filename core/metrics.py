"""绩效指标计算"""
import numpy as np
import pandas as pd


def compute_metrics(eq_curve: pd.Series) -> dict:
    """从净值曲线计算各项指标"""
    returns = eq_curve.pct_change().dropna()
    total_return = (eq_curve.iloc[-1] - eq_curve.iloc[0]) / eq_curve.iloc[0]

    # 年化
    days = len(eq_curve)
    years = max(days / 252, 0.01)
    annual_return = (1 + total_return) ** (1 / years) - 1

    # 最大回撤
    cummax = eq_curve.cummax()
    drawdown = (eq_curve - cummax) / cummax
    max_dd = drawdown.min()

    # 夏普
    rf = 0.02
    excess = returns - rf / 252
    sharpe = np.sqrt(252) * excess.mean() / excess.std() if excess.std() > 0 else 0

    # 波动率
    volatility = returns.std() * np.sqrt(252)

    # 卡玛比率
    calmar = annual_return / abs(max_dd) if max_dd != 0 else 0

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe,
        "volatility": volatility,
        "calmar_ratio": calmar,
    }


def format_pct(val: float) -> str:
    """格式化百分比"""
    if val >= 0:
        return f"+{val:.1f}%"
    return f"{val:.1f}%"


def format_cny(val: float) -> str:
    """格式化金额"""
    if abs(val) >= 10000:
        return f"¥{val/10000:.1f}万"
    return f"¥{val:.0f}"
