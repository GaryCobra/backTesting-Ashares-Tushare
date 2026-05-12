"""Streamlit UI smoke tests for app.py."""
from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
from streamlit.testing.v1 import AppTest


APP_PATH = "/home/xuebin/workspace/backTesting/app.py"


def build_report() -> dict:
    index = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"])
    stock_ohlcv = pd.DataFrame(
        {
            "open": [10.0, 10.5, 11.0, 10.8],
            "high": [10.6, 11.2, 11.4, 11.0],
            "low": [9.9, 10.2, 10.7, 10.4],
            "close": [10.4, 11.0, 10.9, 10.6],
            "volume": [1000, 1200, 900, 1500],
        },
        index=index,
    )
    trade = SimpleNamespace(
        ts_code="000001.SZ",
        buy_date="2024-01-02",
        buy_price=10.4,
        sell_date="2024-01-05",
        sell_price=10.6,
        pnl_pct=1.92,
        pnl_amount=20.0,
        hold_days=3,
        buy_signal="买入",
        sell_signal="卖出",
        status="closed",
        shares=100,
    )
    summary = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "total_trades": 1,
                "win_rate": 100.0,
                "total_pnl": 20.0,
                "avg_pnl": 1.92,
                "total_pnl_pct": 1.92,
            }
        ]
    )
    all_trades = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "buy_date": "2024-01-02",
                "buy_price": 10.4,
                "shares": 100,
                "sell_date": "2024-01-05",
                "sell_price": 10.6,
                "pnl_pct": 1.92,
                "pnl_amount": 20.0,
                "hold_days": 3,
                "buy_signal": "买入",
                "sell_signal": "卖出",
            }
        ]
    )
    return {
        "id": "test_report",
        "name": "测试报告",
        "buy_desc": "测试买入",
        "sell_desc": "测试卖出",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "capital": 100000,
        "shares_per_trade": 100,
        "strategy_name": "测试策略",
        "portfolio_metrics": {
            "total_return": 0.012,
            "annual_return": 0.15,
            "max_drawdown": -0.03,
            "max_drawdown_duration": 5,
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.6,
            "volatility": 0.18,
            "calmar_ratio": 1.8,
            "win_day_ratio": 0.6,
        },
        "trade_metrics": {
            "total_trades": 1,
            "win_rate": 100.0,
            "profit_factor": 1.0,
            "avg_win_pnl": 1.92,
            "avg_loss_pnl": 0.0,
            "avg_hold_days": 3.0,
            "max_consecutive_losses": 0,
        },
        "results": {
            "total_stocks": 1,
            "total_signals": 1,
            "win_trades": 1,
            "loss_trades": 0,
            "win_rate": 100.0,
            "avg_pnl": 1.92,
            "stock_summary": summary,
            "all_trades": all_trades,
            "stock_trades": {"000001.SZ": [trade]},
            "stock_ohlcv": {"000001.SZ": stock_ohlcv},
            "portfolio_equity": pd.Series([0, 35, 22, 20], index=index),
        },
    }


def test_strategy_page_renders() -> None:
    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception
    assert [button.label for button in at.button[:4]] == ["策略工作台", "回测报告", "系统设置", "生成策略并开始回测"]
    assert [field.label for field in at.text_input] == ["起始日期", "结束日期"]
    assert [field.label for field in at.text_area] == ["买入条件", "卖出条件"]


def test_settings_page_renders() -> None:
    at = AppTest.from_file(APP_PATH)
    at.session_state["page"] = "settings"
    at.run()
    assert not at.exception
    assert len(at.selectbox) == 1
    assert at.selectbox[0].label == "选择数据源"
    assert [button.label for button in at.button[:5]] == ["策略工作台", "回测报告", "系统设置", "保存当前配置", "验证连接"]


def test_report_page_renders_with_report_data() -> None:
    at = AppTest.from_file(APP_PATH)
    report = build_report()
    at.session_state["page"] = "report"
    at.session_state["results"] = {"test_report": report}
    at.session_state["current_report_id"] = "test_report"
    at.run()
    assert not at.exception
    assert len(at.expander) == 1
    assert "000001.SZ" in at.expander[0].label
    assert len(at.dataframe) == 1
    assert at.text_input[0].label == "报告名称"
