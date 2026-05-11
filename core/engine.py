"""信号回测引擎 — 逐股票扫描买卖信号"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# A 股交易费率
COMMISSION_RATE = 0.00025   # 佣金万分之二点五
STAMP_TAX_RATE = 0.001      # 印花税千分之一（卖出收取）
MIN_COMMISSION = 5.0        # 最低佣金 5 元


class Signal:
    def __init__(self, ts_code: str, direction: str, date: str, price: float, signal_type: str = ""):
        self.ts_code = ts_code
        self.direction = direction
        self.date = date
        self.price = price
        self.signal_type = signal_type

    def __repr__(self):
        return f"{self.direction.upper()} {self.ts_code} @ {self.date} {self.price}"


class Trade:
    def __init__(self, ts_code: str, buy_signal: Signal, shares: int = 100):
        self.ts_code = ts_code
        self.buy_date = buy_signal.date
        self.buy_price = buy_signal.price
        self.shares = shares
        self.sell_date = ""
        self.sell_price = 0.0
        self.pnl_pct = 0.0
        self.pnl_amount = 0.0
        self.hold_days = 0
        self.buy_signal = buy_signal.signal_type
        self.sell_signal = ""
        self.status = "holding"

    def close(self, sell_signal: Signal):
        self.sell_date = sell_signal.date
        self.sell_price = sell_signal.price
        # 毛收益
        gross = (self.sell_price - self.buy_price) * self.shares
        # 交易费用
        buy_fee = max(self.buy_price * self.shares * COMMISSION_RATE, MIN_COMMISSION)
        sell_fee = max(self.sell_price * self.shares * COMMISSION_RATE, MIN_COMMISSION)
        sell_tax = self.sell_price * self.shares * STAMP_TAX_RATE
        total_cost = gross - buy_fee - sell_fee - sell_tax
        total_invested = self.buy_price * self.shares + buy_fee
        self.pnl_amount = round(total_cost, 2)
        self.pnl_pct = round(total_cost / total_invested * 100, 2) if total_invested > 0 else 0
        days = (pd.to_datetime(sell_signal.date) - pd.to_datetime(self.buy_date)).days
        self.hold_days = max(days, 0)
        self.sell_signal = sell_signal.signal_type
        self.status = "closed"


class SignalEngine:
    def __init__(self, shares_per_trade: int = 100):
        self.shares_per_trade = shares_per_trade

    def run(self, strategy, stock_data: dict) -> dict:
        stock_trades = {}
        stock_summary_rows = []
        stock_equity: dict[str, pd.Series] = {}
        stock_ohlcv: dict[str, pd.DataFrame] = {}

        for ts_code, df in stock_data.items():
            if df.empty or len(df) < 20:
                continue

            strat = strategy.__class__()
            strat.data = df
            strat.ts_code = ts_code
            strat.init()
            trades = []
            current_trade = None
            buy_date = None

            for i in range(len(df)):
                close_val = df.iloc[i]["close"]
                if close_val is None or (isinstance(close_val, float) and pd.isna(close_val)):
                    continue
                date = df.index[i].strftime("%Y-%m-%d") if hasattr(df.index[i], "strftime") else str(df.index[i])
                price = float(close_val)

                try:
                    buy_signal = strat.buy_condition(i)
                    sell_signal = strat.sell_condition(i)
                except (IndexError, KeyError, ValueError) as e:
                    logger.warning("策略异常 %s @ %s[%d]: %s", ts_code, date, i, e)
                    continue

                can_buy = buy_signal and current_trade is None
                can_sell = sell_signal and current_trade is not None

                # T+1: 当天买入不能当天卖出
                if can_sell and buy_date == date:
                    can_sell = False

                if can_buy:
                    sig = Signal(ts_code, "buy", date, price, "买入")
                    current_trade = Trade(ts_code, sig, self.shares_per_trade)
                    buy_date = date
                elif can_sell:
                    sig = Signal(ts_code, "sell", date, price, "卖出")
                    current_trade.close(sig)
                    trades.append(current_trade)
                    current_trade = None
                    buy_date = None

            if current_trade is not None:
                last_price = float(df.iloc[-1]["close"])
                last_date = df.index[-1].strftime("%Y-%m-%d") if hasattr(df.index[-1], "strftime") else str(df.index[-1])
                sig = Signal(ts_code, "sell", last_date, last_price, "期末平仓")
                current_trade.close(sig)
                trades.append(current_trade)

            if trades:
                stock_trades[ts_code] = trades
                # 计算净值曲线
                equity_curve = _compute_equity_curve(df, trades)
                stock_equity[ts_code] = equity_curve
                # 保存 OHLCV 数据供图表使用
                stock_ohlcv[ts_code] = df
                pnls = [t.pnl_pct for t in trades]
                wins = [t for t in trades if t.pnl_pct > 0]
                total_pnl = sum(t.pnl_amount for t in trades)
                total_invested = sum(t.buy_price * t.shares for t in trades)
                total_pnl_pct = round(total_pnl / total_invested * 100, 2) if total_invested > 0 else 0
                stock_summary_rows.append({
                    "ts_code": ts_code,
                    "total_trades": len(trades),
                    "win_trades": len(wins),
                    "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
                    "total_pnl": round(total_pnl, 2),
                    "avg_pnl": round(np.mean(pnls), 2) if pnls else 0,
                    "total_pnl_pct": total_pnl_pct,
                })

        all_trades_df = pd.DataFrame([{
            "ts_code": t.ts_code,
            "buy_date": t.buy_date,
            "buy_price": round(t.buy_price, 3),
            "shares": t.shares,
            "sell_date": t.sell_date,
            "sell_price": round(t.sell_price, 3),
            "pnl_pct": round(t.pnl_pct, 2),
            "pnl_amount": round(t.pnl_amount, 2),
            "hold_days": t.hold_days,
            "buy_signal": t.buy_signal,
            "sell_signal": t.sell_signal,
        } for trades in stock_trades.values() for t in trades])

        stock_summary_df = pd.DataFrame(stock_summary_rows).sort_values("total_pnl", ascending=False) if stock_summary_rows else pd.DataFrame()

        total_trades = len(all_trades_df) if not all_trades_df.empty else 0
        win_trades = len(all_trades_df[all_trades_df["pnl_pct"] > 0]) if not all_trades_df.empty else 0

        # 组合净值曲线 = 所有股票净值之和（按日期对齐）
        portfolio_equity = _aggregate_portfolio_equity(stock_equity)

        return {
            "stock_trades": stock_trades,
            "stock_summary": stock_summary_df,
            "all_trades": all_trades_df,
            "stock_equity": stock_equity,
            "stock_ohlcv": stock_ohlcv,
            "portfolio_equity": portfolio_equity,
            "total_stocks": len(stock_trades),
            "total_signals": total_trades,
            "win_trades": win_trades,
            "loss_trades": total_trades - win_trades,
            "win_rate": round(win_trades / total_trades * 100, 1) if total_trades > 0 else 0,
            "avg_pnl": round(all_trades_df["pnl_pct"].mean(), 2) if not all_trades_df.empty else 0,
        }


def _compute_equity_curve(df: pd.DataFrame, trades: list) -> pd.Series:
    """计算单只股票的每日累计盈亏净值曲线。

    跟踪每天的现金+持仓价值：
    - 不持仓时：净值 = 已实现盈亏之和
    - 持仓时：净值 = 已实现盈亏 + 持仓市值 - 持仓成本
    """
    # 使用与 engine.run() 中一致的日期格式
    # run() 中: date = df.index[i].strftime("%Y-%m-%d") if hasattr(..., "strftime") else str(df.index[i])
    if hasattr(df.index, "strftime"):
        date_strs = df.index.strftime("%Y-%m-%d")
    else:
        date_strs = [str(d) for d in df.index]  # 保持原始格式（如 "20240102"）
    equity = pd.Series(0.0, index=df.index, dtype=float)

    trade_idx = 0
    realized_pnl = 0.0
    active_trade = None
    entry_cost = 0.0  # 买入成本（不含手续费）

    for i in range(len(df)):
        date_str = date_strs[i]
        close = float(df.iloc[i]["close"])

        # 先处理平仓（可能和开仓同一天）
        if active_trade is not None and active_trade.status == "closed" and active_trade.sell_date == date_str:
            realized_pnl += active_trade.pnl_amount
            active_trade = None

        # 再处理开仓
        if active_trade is None and trade_idx < len(trades):
            t = trades[trade_idx]
            if t.buy_date == date_str:
                active_trade = t
                entry_cost = t.buy_price * t.shares
                trade_idx += 1

        # 计算当日净值
        if active_trade is not None:
            current_value = close * active_trade.shares
            equity.iloc[i] = realized_pnl + (current_value - entry_cost)
        else:
            equity.iloc[i] = realized_pnl

    return equity


def _aggregate_portfolio_equity(stock_equity: dict[str, pd.Series]) -> pd.Series:
    """将所有股票的净值曲线聚合为组合净值曲线。"""
    if not stock_equity:
        return pd.Series(dtype=float)
    # 按日期索引对齐后求和
    result = sum(stock_equity.values())
    return result
