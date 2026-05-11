"""绩效指标计算 — 支持组合级和单股票级回测分析"""
import numpy as np
import pandas as pd


def compute_metrics(eq_curve: pd.Series, capital: float | None = None) -> dict:
    """从净值/盈亏曲线计算各项指标。

    支持：
    - 净值曲线（从 1.0 开始正数）— 直接计算收益率
    - 累计盈亏曲线（从 0 开始，可正可负）— 需传入 capital 做参考基数

    Args:
        eq_curve: 每日净值或累计盈亏 Series
        capital: 初始资金（累计盈亏曲线必传，净值曲线可选）

    Returns:
        指标 dict
    """
    if eq_curve.empty:
        return _empty_metrics()

    eq = eq_curve.copy()
    starting_val = eq.iloc[0]

    # ── 归一化：确保起点为正 1.0 ──
    is_pnl_curve = abs(starting_val) < 1e-6 or starting_val < 0
    if is_pnl_curve:
        # 累计盈亏曲线：用 capital 做参考基数
        ref = capital if capital is not None and capital > 0 else 100000.0
        eq = eq / ref + 1.0
    elif abs(starting_val - 1.0) > 0.001 and starting_val > 0:
        # 非标净值曲线：缩放到起点 1.0
        eq = eq / starting_val

    starting_val = eq.iloc[0]

    returns = eq.pct_change().dropna()
    # 过滤极端值
    returns = returns[np.abs(returns) < 100]
    if returns.empty:
        return _empty_metrics()

    total_return = (eq.iloc[-1] - starting_val) / starting_val

    # 年化
    days = len(eq)
    years = max(days / 252, 0.01)
    annual_return = (1 + total_return) ** (1 / years) - 1
    annual_return = np.nan_to_num(annual_return, nan=0.0, posinf=0.0, neginf=0.0)

    # 最大回撤
    cummax = eq.cummax()
    cummax = cummax.replace(0, np.nan)
    drawdown = ((eq - cummax) / cummax).fillna(0)
    max_dd = drawdown.min() if not drawdown.empty else 0.0
    max_dd_duration = _max_drawdown_duration(drawdown)

    # 夏普
    rf = 0.02
    excess = returns - rf / 252
    std = excess.std() if len(excess) > 1 else 0
    sharpe = np.sqrt(252) * excess.mean() / std if std > 0 else 0.0

    # 波动率
    volatility = returns.std() * np.sqrt(252) if not returns.empty else 0.0

    # 卡玛比率
    calmar = annual_return / abs(max_dd) if abs(max_dd) > 1e-10 else 0.0

    # 索提诺比率
    downside = returns[returns < 0]
    downside_std = downside.std() * np.sqrt(252) if len(downside) > 1 else 0.001
    sortino = (annual_return - rf) / downside_std if downside_std > 0 else 0.0

    # 正收益比例
    positive_days = (returns > 0).sum()
    win_day_ratio = positive_days / len(returns) if len(returns) > 0 else 0.0

    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "max_drawdown": max_dd,
        "max_drawdown_duration": max_dd_duration,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "volatility": volatility,
        "calmar_ratio": calmar,
        "win_day_ratio": win_day_ratio,
    }


def compute_trade_metrics(all_trades_df: pd.DataFrame) -> dict:
    """从交易明细 DataFrame 计算交易层面的指标

    all_trades_df 字段: ts_code, buy_date, buy_price, shares, sell_date,
                        sell_price, pnl_pct, pnl_amount, hold_days, ...
    """
    if all_trades_df.empty:
        return {
            "total_trades": 0, "win_trades": 0, "loss_trades": 0,
            "win_rate": 0, "avg_pnl": 0, "avg_win": 0, "avg_loss": 0,
            "profit_factor": 0, "avg_hold_days": 0, "total_pnl": 0,
            "max_consecutive_losses": 0,
        }

    total_trades = len(all_trades_df)
    winners = all_trades_df[all_trades_df["pnl_pct"] > 0]
    losers = all_trades_df[all_trades_df["pnl_pct"] <= 0]
    win_trades = len(winners)
    loss_trades = len(losers)

    total_pnl = all_trades_df["pnl_amount"].sum()
    avg_pnl = all_trades_df["pnl_pct"].mean()
    avg_win = winners["pnl_pct"].mean() if win_trades > 0 else 0
    avg_loss = abs(losers["pnl_pct"].mean()) if loss_trades > 0 else 0

    # 盈亏比
    profit_factor = avg_win / avg_loss if avg_loss > 0 else 0

    # 平均持仓天数
    avg_hold_days = all_trades_df["hold_days"].mean()

    # 最大连续亏损
    max_consecutive_losses = _max_consecutive_losses(all_trades_df)

    return {
        "total_trades": total_trades,
        "win_trades": win_trades,
        "loss_trades": loss_trades,
        "win_rate": round(win_trades / total_trades * 100, 1) if total_trades > 0 else 0,
        "avg_pnl": round(avg_pnl, 2),
        "avg_win_pnl": round(avg_win, 2),
        "avg_loss_pnl": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_hold_days": round(avg_hold_days, 1),
        "total_pnl": round(total_pnl, 2),
        "max_consecutive_losses": max_consecutive_losses,
    }


def compute_equity_curve_metrics(eq_curve: pd.Series) -> dict:
    """从净值曲线计算组合级指标（兼容旧接口）"""
    return compute_metrics(eq_curve)


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


def _empty_metrics() -> dict:
    """空曲线的指标默认值"""
    return {
        "total_return": 0.0, "annual_return": 0.0,
        "max_drawdown": 0.0, "max_drawdown_duration": 0,
        "sharpe_ratio": 0.0, "sortino_ratio": 0.0,
        "volatility": 0.0, "calmar_ratio": 0.0, "win_day_ratio": 0.0,
    }


def _max_drawdown_duration(drawdown: pd.Series) -> int:
    """计算最大回撤持续天数"""
    if drawdown.empty or drawdown.min() >= 0:
        return 0
    dd_min_idx = drawdown.idxmin()
    loc = drawdown.index.get_loc(dd_min_idx)
    # 统一转为 datetime 计算天数
    try:
        idx_end = pd.to_datetime(drawdown.index[-1])
        idx_min = pd.to_datetime(dd_min_idx)
    except Exception:
        return 0
    recovery = (drawdown.iloc[loc:] >= 0)
    recovered = recovery[recovery].index
    if len(recovered) > 0:
        try:
            end_dt = pd.to_datetime(recovered[0])
        except Exception:
            end_dt = idx_end
    else:
        end_dt = idx_end
    duration = (end_dt - idx_min).days
    return max(duration, 0)


def _max_consecutive_losses(trades_df: pd.DataFrame) -> int:
    """计算最大连续亏损次数"""
    losses = (trades_df["pnl_pct"] <= 0).astype(int)
    if losses.empty:
        return 0
    groups = (losses != losses.shift()).cumsum()
    consecutive = losses.groupby(groups).sum()
    return int(consecutive.max()) if not consecutive.empty else 0
