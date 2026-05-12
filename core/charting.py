"""Plotly 图表主题 — 统一深色中文界面风格"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


BG = "#0b1728"
PANEL = "rgba(11, 22, 39, 0.96)"
GRID = "rgba(96, 130, 189, 0.16)"
TEXT = "#eef4ff"
TEXT_SOFT = "#b4c3df"
TEXT_FAINT = "#7f95bc"
BLUE = "#5fb8ff"
BLUE_FILL = "rgba(95, 184, 255, 0.16)"
ROSE = "#ff6f91"
ROSE_FILL = "rgba(255, 111, 145, 0.18)"
TEAL = "#2dd4bf"
TEAL_FILL = "rgba(45, 212, 191, 0.16)"
AMBER = "#ffbf66"


def _base_layout(title: str = "", height: int = 420) -> dict:
    return {
        "title": {
            "text": title,
            "font": {"size": 18, "color": TEXT},
            "x": 0.02,
            "xanchor": "left",
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": PANEL,
        "height": height,
        "margin": {"l": 24, "r": 20, "t": 48, "b": 24},
        "font": {"family": "Manrope, Noto Sans SC, sans-serif", "color": TEXT_SOFT},
        "hoverlabel": {
            "bgcolor": "#12243d",
            "bordercolor": "rgba(95, 184, 255, 0.35)",
            "font": {"color": TEXT, "size": 12},
        },
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1.0,
            "font": {"color": TEXT_SOFT, "size": 12},
        },
    }


def _style_axes(fig: go.Figure, row: int | None = None, col: int | None = None) -> None:
    kwargs = {}
    if row is not None and col is not None:
        kwargs = {"row": row, "col": col}
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=GRID,
        tickfont={"color": TEXT_FAINT},
        **kwargs,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        linecolor=GRID,
        tickfont={"color": TEXT_FAINT},
        **kwargs,
    )


def plot_stock_kline(ts_code: str, df: pd.DataFrame, trades: list, stock_name: str = "") -> go.Figure:
    """绘制个股 K 线、买卖信号和成交量。"""
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.72, 0.28],
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="K线",
            increasing_line_color=ROSE,
            decreasing_line_color=TEAL,
            increasing_fillcolor=ROSE,
            decreasing_fillcolor=TEAL,
        ),
        row=1,
        col=1,
    )

    buy_dates = [trade.buy_date for trade in trades]
    buy_prices = [trade.buy_price for trade in trades]
    fig.add_trace(
        go.Scatter(
            x=buy_dates,
            y=buy_prices,
            mode="markers",
            marker={
                "symbol": "triangle-up",
                "size": 12,
                "color": BLUE,
                "line": {"width": 1, "color": "#ffffff"},
            },
            name="买入",
            hovertemplate="买入日期：%{x}<br>买入价格：¥%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    closed_trades = [trade for trade in trades if trade.status == "closed"]
    sell_dates = [trade.sell_date for trade in closed_trades]
    sell_prices = [trade.sell_price for trade in closed_trades]
    fig.add_trace(
        go.Scatter(
            x=sell_dates,
            y=sell_prices,
            mode="markers",
            marker={
                "symbol": "triangle-down",
                "size": 12,
                "color": AMBER,
                "line": {"width": 1, "color": "#ffffff"},
            },
            name="卖出",
            hovertemplate="卖出日期：%{x}<br>卖出价格：¥%{y:.2f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    connector_x: list = []
    connector_y: list = []
    for trade in closed_trades:
        connector_x.extend([trade.buy_date, trade.sell_date, None])
        connector_y.extend([trade.buy_price, trade.sell_price, None])
    if connector_x:
        fig.add_trace(
            go.Scatter(
                x=connector_x,
                y=connector_y,
                mode="lines",
                line={"color": "rgba(255,191,102,0.75)", "width": 1, "dash": "dot"},
                hoverinfo="skip",
                showlegend=False,
            ),
            row=1,
            col=1,
        )

    volume_colors = [ROSE if row["close"] >= row["open"] else TEAL for _, row in df.iterrows()]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["volume"],
            marker_color=volume_colors,
            marker_opacity=0.78,
            name="成交量",
            hovertemplate="日期：%{x}<br>成交量：%{y:,.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    title = f"{ts_code} · {stock_name}" if stock_name else ts_code
    fig.update_layout(**_base_layout(title=title, height=560))
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="价格", row=1, col=1, side="right", title_font={"color": TEXT_SOFT})
    fig.update_yaxes(title_text="成交量", row=2, col=1, side="right", title_font={"color": TEXT_SOFT})
    _style_axes(fig, row=1, col=1)
    _style_axes(fig, row=2, col=1)
    return fig


def plot_portfolio_equity(equity_curve: pd.Series) -> go.Figure:
    """绘制组合累计盈亏与回撤。"""
    if equity_curve.empty:
        fig = go.Figure()
        fig.update_layout(**_base_layout(title="组合净值", height=320))
        fig.add_annotation(text="暂无净值数据", x=0.5, y=0.5, showarrow=False, font={"size": 15, "color": TEXT_SOFT})
        return fig

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=("组合累计盈亏", "回撤"),
    )

    final_pnl = equity_curve.iloc[-1]
    line_color = ROSE if final_pnl >= 0 else TEAL
    fill_color = ROSE_FILL if final_pnl >= 0 else TEAL_FILL

    fig.add_trace(
        go.Scatter(
            x=equity_curve.index,
            y=equity_curve.values,
            mode="lines",
            name="累计盈亏",
            line={"color": line_color, "width": 2.6},
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate="日期：%{x}<br>累计盈亏：¥%{y:+,.0f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.18)", row=1, col=1)

    cummax = equity_curve.cummax()
    drawdown_pct = ((equity_curve - cummax) / cummax.replace(0, np.nan) * 100).fillna(0)
    fig.add_trace(
        go.Scatter(
            x=drawdown_pct.index,
            y=drawdown_pct.values,
            mode="lines",
            name="回撤",
            line={"color": BLUE, "width": 1.8},
            fill="tozeroy",
            fillcolor=BLUE_FILL,
            hovertemplate="日期：%{x}<br>回撤：%{y:.2f}%<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.15)", row=2, col=1)

    fig.update_layout(**_base_layout(title="组合净值与回撤", height=450))
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title_text="盈亏（元）", row=1, col=1, side="right", title_font={"color": TEXT_SOFT})
    fig.update_yaxes(title_text="回撤", ticksuffix="%", row=2, col=1, side="right", title_font={"color": TEXT_SOFT})
    _style_axes(fig, row=1, col=1)
    _style_axes(fig, row=2, col=1)
    fig.update_annotations(font={"size": 13, "color": TEXT_SOFT})
    return fig


def plot_trade_pnl_distribution(all_trades_df: pd.DataFrame) -> go.Figure:
    """绘制每笔交易收益率分布。"""
    if all_trades_df.empty:
        fig = go.Figure()
        fig.update_layout(**_base_layout(title="单笔收益分布", height=300))
        fig.add_annotation(text="暂无交易数据", x=0.5, y=0.5, showarrow=False, font={"size": 15, "color": TEXT_SOFT})
        return fig

    df = all_trades_df.copy()
    df["color"] = df["pnl_pct"].apply(lambda value: ROSE if value >= 0 else TEAL)
    df["label"] = df["pnl_pct"].apply(lambda value: f"{value:+.1f}%")
    df["tooltip"] = df.apply(
        lambda row: (
            f"标的：{row['ts_code']}<br>"
            f"区间：{row['buy_date']} → {row['sell_date']}<br>"
            f"盈亏额：¥{row['pnl_amount']:+,.0f}"
        ),
        axis=1,
    )

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["pnl_pct"],
            marker_color=df["color"],
            marker_opacity=0.82,
            text=df["label"],
            textposition="outside",
            textfont={"size": 10, "color": TEXT_SOFT},
            customdata=df["tooltip"],
            hovertemplate="%{customdata}<br>收益率：%{y:+.2f}%<extra></extra>",
            name="单笔收益率",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.16)")
    fig.update_layout(**_base_layout(title="单笔交易收益率分布", height=320))
    fig.update_layout(
        xaxis_showticklabels=False,
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="收益率", ticksuffix="%", side="right", title_font={"color": TEXT_SOFT})
    _style_axes(fig)
    return fig


def render_metrics_html(portfolio_metrics: dict, trade_metrics: dict, capital: float = 100000) -> str:
    """渲染组合和交易指标卡。"""

    def _pv(key: str, fmt: str = ".2f") -> str:
        value = portfolio_metrics.get(key, 0)
        if isinstance(value, (int, float)):
            return format(value, fmt)
        return str(value)

    def _tv(key: str, fmt: str = ".2f") -> str:
        value = trade_metrics.get(key, 0)
        if isinstance(value, (int, float)):
            return format(value, fmt)
        return str(value)

    total_return = portfolio_metrics.get("total_return", 0)
    return_color = ROSE if total_return >= 0 else TEAL
    return_sign = "+" if total_return >= 0 else ""
    max_drawdown = portfolio_metrics.get("max_drawdown", 0)
    max_drawdown_color = TEAL if max_drawdown < 0 else TEXT

    card_style = (
        "background:linear-gradient(180deg, rgba(12,24,42,0.96), rgba(10,19,33,0.96));"
        "border:1px solid rgba(96,130,189,0.2);border-radius:22px;padding:18px 18px 16px;"
    )
    label_style = (
        f"font-size:12px;color:{TEXT_FAINT};font-weight:700;letter-spacing:0.06em;text-transform:uppercase;"
    )
    value_style = "font-size:28px;font-weight:800;letter-spacing:-0.05em;margin-top:10px;"
    meta_style = f"font-size:13px;color:{TEXT_FAINT};margin-top:6px;line-height:1.6;"

    return f"""
<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:14px 0 4px;">
  <div style="{card_style}">
    <div style="{label_style}">总收益率</div>
    <div style="{value_style}color:{return_color};">{return_sign}{_pv('total_return', '.2%')}</div>
    <div style="{meta_style}">以初始资金 ¥{capital:,.0f} 为基准计算</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">年化收益</div>
    <div style="{value_style}color:{return_color};">{return_sign}{_pv('annual_return', '.2%')}</div>
    <div style="{meta_style}">用于判断长期可持续性</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">最大回撤</div>
    <div style="{value_style}color:{max_drawdown_color};">{_pv('max_drawdown', '.2%')}</div>
    <div style="{meta_style}">持续 {_pv('max_drawdown_duration', '.0f')} 天</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">夏普比率</div>
    <div style="{value_style}color:{TEXT};">{_pv('sharpe_ratio', '.2f')}</div>
    <div style="{meta_style}">风险调整后收益能力</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">卡玛比率</div>
    <div style="{value_style}color:{TEXT};">{_pv('calmar_ratio', '.2f')}</div>
    <div style="{meta_style}">收益与回撤效率比</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">索提诺比率</div>
    <div style="{value_style}color:{TEXT};">{_pv('sortino_ratio', '.2f')}</div>
    <div style="{meta_style}">对下行风险更敏感</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">波动率</div>
    <div style="{value_style}color:{TEXT};">{_pv('volatility', '.2%')}</div>
    <div style="{meta_style}">波动越高，净值越不平滑</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">正收益日占比</div>
    <div style="{value_style}color:{TEXT};">{_pv('win_day_ratio', '.0%')}</div>
    <div style="{meta_style}">反映组合日度稳定性</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">总交易数</div>
    <div style="{value_style}color:{TEXT};">{_tv('total_trades', '.0f')}</div>
    <div style="{meta_style}">闭环完成的总交易笔数</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">交易胜率</div>
    <div style="{value_style}color:{TEXT};">{_tv('win_rate', '.1f')}%</div>
    <div style="{meta_style}">盈利笔数 / 总交易数</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">盈亏比</div>
    <div style="{value_style}color:{TEXT};">{_tv('profit_factor', '.2f')}</div>
    <div style="{meta_style}">平均盈利 {_tv('avg_win_pnl', '.1f')}% · 平均亏损 {_tv('avg_loss_pnl', '.1f')}%</div>
  </div>
  <div style="{card_style}">
    <div style="{label_style}">平均持仓</div>
    <div style="{value_style}color:{TEXT};">{_tv('avg_hold_days', '.1f')} 天</div>
    <div style="{meta_style}">最大连续亏损 {_tv('max_consecutive_losses', '.0f')} 次</div>
  </div>
</div>
"""
