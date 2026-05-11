"""Plotly 交互图表 — K线、净值曲线、回撤图"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_stock_kline(
    ts_code: str,
    df: pd.DataFrame,
    trades: list,
    stock_name: str = "",
) -> go.Figure:
    """绘制个股K线图 + 买卖信号标记 + 成交量

    Args:
        ts_code: 股票代码
        df: OHLCV DataFrame, index 为日期
        trades: Trade 对象列表
        stock_name: 股票名称（可选）

    Returns:
        Plotly Figure
    """
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.72, 0.28],
    )

    # ── K 线 ──
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K线",
            increasing_line_color="#ef5350",
            decreasing_line_color="#26a69a",
            increasing_fillcolor="#ef5350",
            decreasing_fillcolor="#26a69a",
        ),
        row=1, col=1,
    )

    # ── 买入标记（绿色三角向上） ──
    buy_dates = [t.buy_date for t in trades]
    buy_prices = [t.buy_price for t in trades]
    fig.add_trace(
        go.Scatter(
            x=buy_dates,
            y=buy_prices,
            mode="markers",
            marker=dict(
                symbol="triangle-up",
                size=14,
                color="#26a69a",
                line=dict(width=1, color="white"),
            ),
            name="买入",
            hovertemplate="买入 %{x}<br>¥%{y:.2f}<extra></extra>",
        ),
        row=1, col=1,
    )

    # ── 卖出标记（红色三角向下） ──
    closed_trades = [t for t in trades if t.status == "closed"]
    sell_dates = [t.sell_date for t in closed_trades]
    sell_prices = [t.sell_price for t in closed_trades]
    fig.add_trace(
        go.Scatter(
            x=sell_dates,
            y=sell_prices,
            mode="markers",
            marker=dict(
                symbol="triangle-down",
                size=14,
                color="#ef5350",
                line=dict(width=1, color="white"),
            ),
            name="卖出",
            hovertemplate="卖出 %{x}<br>¥%{y:.2f}<extra></extra>",
        ),
        row=1, col=1,
    )

    # ── 连线：同一笔交易的买入到卖出（合并为一条 trace，用 None 分隔） ──
    connector_x: list = []
    connector_y: list = []
    for t in closed_trades:
        connector_x.extend([t.buy_date, t.sell_date, None])
        connector_y.extend([t.buy_price, t.sell_price, None])
    if connector_x:
        fig.add_trace(
            go.Scatter(
                x=connector_x,
                y=connector_y,
                mode="lines",
                line=dict(
                    color="#FF8C00",
                    width=1,
                    dash="dot",
                ),
                showlegend=False,
                hoverinfo="skip",
            ),
            row=1, col=1,
        )

    # ── 成交量（根据涨跌着色） ──
    volume_colors = []
    for i in range(len(df)):
        if df.iloc[i]["close"] >= df.iloc[i]["open"]:
            volume_colors.append("#ef5350")
        else:
            volume_colors.append("#26a69a")

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["volume"],
            marker_color=volume_colors,
            marker_opacity=0.7,
            name="成交量",
            hovertemplate="成交量: %{y:,.0f}<extra></extra>",
        ),
        row=2, col=1,
    )

    # ── 布局 ──
    title = f"{ts_code}  {stock_name}" if stock_name else ts_code
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        height=520,
        margin=dict(l=40, r=16, t=50, b=16),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    fig.update_xaxes(title_text="", row=2, col=1)
    fig.update_yaxes(title_text="价格", row=1, col=1, side="right")
    fig.update_yaxes(title_text="成交量", row=2, col=1, side="right")

    return fig


def plot_portfolio_equity(
    equity_curve: pd.Series,
) -> go.Figure:
    """绘制组合净值曲线 + 回撤子图

    Args:
        equity_curve: 每日累计盈亏 Series, index 为日期

    Returns:
        Plotly Figure
    """
    if equity_curve.empty:
        fig = go.Figure()
        fig.add_annotation(text="无净值数据", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=400)
        return fig

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.7, 0.3],
        subplot_titles=("累计盈亏", "回撤"),
    )

    # ── 净值曲线 ──
    final_pnl = equity_curve.iloc[-1]
    line_color = "#1976D2" if final_pnl >= 0 else "#D32F2F"
    fill_color = "rgba(25,118,210,0.08)" if final_pnl >= 0 else "rgba(211,47,47,0.08)"

    fig.add_trace(
        go.Scatter(
            x=equity_curve.index,
            y=equity_curve.values,
            mode="lines",
            name="累计盈亏",
            line=dict(color=line_color, width=2),
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate="%{x}<br>盈亏: ¥%{y:+,.0f}<extra></extra>",
        ),
        row=1, col=1,
    )

    # 零轴参考线
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5, row=1, col=1)

    # ── 回撤图 ──
    cummax = equity_curve.cummax()
    dd_pct = ((equity_curve - cummax) / cummax.replace(0, np.nan) * 100).fillna(0)

    fig.add_trace(
        go.Scatter(
            x=dd_pct.index,
            y=dd_pct.values,
            mode="lines",
            name="回撤",
            line=dict(color="#ef5350", width=1.5),
            fill="tozeroy",
            fillcolor="rgba(239,83,80,0.15)",
            hovertemplate="%{x}<br>回撤: %{y:.2f}%<extra></extra>",
        ),
        row=2, col=1,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.3, row=2, col=1)
    fig.update_yaxes(ticksuffix="%", row=2, col=1)

    # ── 布局 ──
    fig.update_layout(
        height=420,
        hovermode="x unified",
        margin=dict(l=40, r=16, t=40, b=16),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(title_text="盈亏 (元)", row=1, col=1, side="right")
    fig.update_yaxes(title_text="回撤", row=2, col=1, side="right")

    return fig


def plot_trade_pnl_distribution(all_trades_df: pd.DataFrame) -> go.Figure:
    """绘制每笔交易盈亏分布柱状图

    Args:
        all_trades_df: 所有交易的 DataFrame

    Returns:
        Plotly Figure
    """
    if all_trades_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="无交易数据", x=0.5, y=0.5, showarrow=False)
        return fig

    df = all_trades_df.copy()
    df["color"] = df["pnl_pct"].apply(
        lambda x: "#ef5350" if x >= 0 else "#26a69a",
    )
    df["tooltip"] = df.apply(
        lambda r: f"{r['ts_code']} {r['buy_date']}~{r['sell_date']}<br>盈亏: {r['pnl_pct']:+.2f}%",
        axis=1,
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["pnl_pct"],
            marker_color=df["color"],
            marker_opacity=0.75,
            text=df["pnl_pct"].apply(lambda x: f"{x:+.1f}%"),
            textposition="outside",
            textfont=dict(size=9),
            hovertemplate="%{customdata}<br>盈亏: %{y:+.2f}%<extra></extra>",
            customdata=df[["ts_code", "buy_date", "sell_date", "pnl_amount"]],
            name="交易盈亏",
        ),
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        title="每笔交易收益率",
        height=300,
        margin=dict(l=40, r=16, t=40, b=16),
        hovermode="x unified",
        xaxis_showticklabels=False,
        yaxis_ticksuffix="%",
    )
    return fig


def render_metrics_html(
    portfolio_metrics: dict,
    trade_metrics: dict,
    capital: float = 100000,
) -> str:
    """生成指标面板的 HTML（用于 st.markdown 渲染）

    Args:
        portfolio_metrics: compute_metrics() 返回值
        trade_metrics: compute_trade_metrics() 返回值
        capital: 总资金

    Returns:
        HTML 字符串
    """
    def _v(key, fmt=".2f"):
        val = portfolio_metrics.get(key, 0)
        if isinstance(val, (int, float)):
            return f"{val:{fmt}}"
        return str(val)

    def _tv(key, fmt=".2f"):
        val = trade_metrics.get(key, 0)
        if isinstance(val, (int, float)):
            return f"{val:{fmt}}"
        return str(val)

    total_return = portfolio_metrics.get("total_return", 0)
    return_color = "#ef5350" if total_return >= 0 else "#26a69a"
    return_sign = "+" if total_return >= 0 else ""

    max_dd = portfolio_metrics.get("max_drawdown", 0)
    dd_color = "#26a69a" if max_dd >= 0 else "#ef5350"

    html = f"""
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0;">
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">总收益率</div>
        <div style="font-size:22px;font-weight:700;color:{return_color};margin-top:4px;">{return_sign}{_v('total_return', '.2%')}</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">年化收益</div>
        <div style="font-size:22px;font-weight:700;color:{return_color};margin-top:4px;">{return_sign}{_v('annual_return', '.2%')}</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">最大回撤</div>
        <div style="font-size:22px;font-weight:700;color:{dd_color};margin-top:4px;">{_v('max_drawdown', '.2%')}</div>
        <div style="font-size:11px;color:#8A8886;">持续 {_v('max_drawdown_duration', '.0f')} 天</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">夏普比率</div>
        <div style="font-size:22px;font-weight:700;color:#201F1E;margin-top:4px;">{_v('sharpe_ratio', '.2f')}</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">卡玛比率</div>
        <div style="font-size:22px;font-weight:700;color:#201F1E;margin-top:4px;">{_v('calmar_ratio', '.2f')}</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">索提诺比率</div>
        <div style="font-size:22px;font-weight:700;color:#201F1E;margin-top:4px;">{_v('sortino_ratio', '.2f')}</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">波动率</div>
        <div style="font-size:22px;font-weight:700;color:#201F1E;margin-top:4px;">{_v('volatility', '.2%')}</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">正收益日占比</div>
        <div style="font-size:22px;font-weight:700;color:#201F1E;margin-top:4px;">{_v('win_day_ratio', '.0%')}</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">总交易</div>
        <div style="font-size:22px;font-weight:700;color:#201F1E;margin-top:4px;">{_tv('total_trades', '.0f')}</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">胜率</div>
        <div style="font-size:22px;font-weight:700;color:#201F1E;margin-top:4px;">{_tv('win_rate', '.1f')}%</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">盈亏比</div>
        <div style="font-size:22px;font-weight:700;color:#201F1E;margin-top:4px;">{_tv('profit_factor', '.2f')}</div>
        <div style="font-size:11px;color:#8A8886;">均盈 {_tv('avg_win_pnl', '.1f')}% / 均亏 {_tv('avg_loss_pnl', '.1f')}%</div>
      </div>
      <div style="background:white;border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size:11px;color:#8A8886;text-transform:uppercase;letter-spacing:0.3px;">平均持仓</div>
        <div style="font-size:22px;font-weight:700;color:#201F1E;margin-top:4px;">{_tv('avg_hold_days', '.1f')} 天</div>
        <div style="font-size:11px;color:#8A8886;">最大连亏 {_tv('max_consecutive_losses', '.0f')} 次</div>
      </div>
    </div>
    """
    return html
