"""A股回测系统 — Streamlit 主入口"""
from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.cache import clear_cache
from core.charting import (
    plot_portfolio_equity,
    plot_stock_kline,
    plot_trade_pnl_distribution,
    render_metrics_html,
)
from core.data import get_source
from core.data_source import AVAILABLE_SOURCES
from core.engine import SignalEngine
from core.metrics import compute_metrics, compute_trade_metrics
from rag.report_store import (
    delete_report,
    init_reports_table,
    list_reports,
    load_report as db_load_report,
    save_report as db_save_report,
)
from rag.retriever import search_examples
from rag.seed_loader import load_seed_examples
from rag.store import add_example, count_examples, init_rag, list_examples
from strategies.generator import generate_strategy
from utils.config import get_token, load_config


st.set_page_config(
    page_title="A股回测系统",
    layout="wide",
    page_icon="⟠",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root {
  --bg: #07111f;
  --bg-soft: #0b1728;
  --panel: rgba(9, 19, 34, 0.92);
  --panel-2: rgba(12, 24, 42, 0.94);
  --panel-3: rgba(16, 31, 53, 0.9);
  --line: rgba(96, 130, 189, 0.26);
  --line-strong: rgba(114, 156, 223, 0.48);
  --text: #eef4ff;
  --text-soft: #b4c3df;
  --text-faint: #7f95bc;
  --blue: #5fb8ff;
  --blue-strong: #4aa5f0;
  --teal: #2dd4bf;
  --rose: #ff6f91;
  --amber: #ffbf66;
  --success: #30d5a1;
  --danger: #ff7a99;
  --radius-xl: 28px;
  --radius-lg: 22px;
  --radius-md: 18px;
  --shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
}

html, body, [class*="css"] {
  font-family: 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Noto Sans SC', sans-serif;
  color: var(--text);
}

body {
  background:
    radial-gradient(circle at 14% 8%, rgba(69, 177, 255, 0.24), transparent 24%),
    radial-gradient(circle at 88% 7%, rgba(41, 214, 183, 0.20), transparent 22%),
    radial-gradient(circle at 78% 92%, rgba(255, 105, 148, 0.13), transparent 20%),
    linear-gradient(180deg, #07111f 0%, #091424 100%);
}

.stApp {
  background: transparent;
}

#MainMenu,
header,
.stAppToolbar,
.stDecoration,
.stDeployButton,
.stToolbarActions {
  display: none !important;
}

[data-testid="collapsedControl"] {
  display: none !important;
}

.block-container {
  max-width: 1380px;
  padding: 24px 28px 40px !important;
}

h1, h2, h3, h4, h5, h6, p, span, label, div {
  color: inherit;
}

.shell {
  position: relative;
  padding: 28px;
  border-radius: 34px;
  background: linear-gradient(180deg, rgba(8, 17, 31, 0.86), rgba(8, 16, 29, 0.96));
  border: 1px solid rgba(111, 147, 208, 0.2);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.shell::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(135deg, rgba(95, 184, 255, 0.07), transparent 30%),
    linear-gradient(315deg, rgba(45, 212, 191, 0.05), transparent 35%);
  pointer-events: none;
}

.app-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 22px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-mark {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, rgba(95, 184, 255, 0.2), rgba(95, 184, 255, 0.08));
  border: 1px solid rgba(95, 184, 255, 0.35);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.brand-copy h1 {
  margin: 0;
  font-size: 25px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.brand-copy p {
  margin: 6px 0 0;
  color: var(--text-faint);
  font-size: 13px;
}

.status-cluster {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.status-pill,
.ghost-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(16, 30, 50, 0.82);
  border: 1px solid var(--line);
  font-size: 13px;
  color: var(--text-soft);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(320px, 0.92fr);
  gap: 18px;
  margin-bottom: 18px;
}

.hero-panel,
.glass-card,
.stat-card,
.metric-strip-card,
.empty-card {
  background: linear-gradient(180deg, rgba(11, 22, 39, 0.96), rgba(10, 19, 33, 0.96));
  border: 1px solid var(--line);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
}

.hero-panel {
  padding: 26px 26px 22px;
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(17, 38, 60, 0.82);
  border: 1px solid rgba(95, 184, 255, 0.22);
  color: var(--blue);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.hero-title {
  margin: 18px 0 8px;
  font-size: 36px;
  font-weight: 800;
  line-height: 1.08;
  letter-spacing: -0.05em;
}

.hero-desc {
  margin: 0;
  max-width: 840px;
  color: var(--text-soft);
  font-size: 15px;
  line-height: 1.7;
}

.chip-row {
  margin-top: 18px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(14, 29, 49, 0.86);
  border: 1px solid rgba(96, 130, 189, 0.34);
  border-radius: 999px;
  color: var(--text-soft);
  font-size: 13px;
}

.hero-side {
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.side-title {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.side-item {
  padding: 16px 18px;
  border-radius: 20px;
  background: rgba(14, 27, 46, 0.8);
  border: 1px solid rgba(96, 130, 189, 0.22);
}

.side-item strong {
  display: block;
  font-size: 16px;
  margin-bottom: 6px;
}

.side-item span {
  display: block;
  color: var(--text-faint);
  font-size: 13px;
  line-height: 1.6;
}

.section-label {
  margin: 24px 0 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.section-label h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.section-label p {
  margin: 0;
  color: var(--text-faint);
  font-size: 14px;
}

.glass-card {
  padding: 22px;
}

.card-title {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.card-subtitle {
  margin: 0 0 18px;
  color: var(--text-faint);
  font-size: 14px;
  line-height: 1.7;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.feature {
  padding: 16px 18px;
  border-radius: 22px;
  background: rgba(14, 27, 46, 0.82);
  border: 1px solid rgba(96, 130, 189, 0.22);
}

.feature strong {
  display: block;
  margin-bottom: 8px;
  font-size: 15px;
}

.feature span {
  color: var(--text-faint);
  font-size: 13px;
  line-height: 1.7;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 14px;
  margin-top: 12px;
}

.stat-card {
  position: relative;
  padding: 18px 18px 16px;
}

.stat-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 4px;
  background: linear-gradient(90deg, rgba(95,184,255,0.95), rgba(95,184,255,0.25));
}

.stat-card.rose::before {
  background: linear-gradient(90deg, rgba(255,111,145,0.95), rgba(255,111,145,0.25));
}

.stat-card.teal::before {
  background: linear-gradient(90deg, rgba(45,212,191,0.95), rgba(45,212,191,0.25));
}

.stat-card .label {
  display: block;
  color: var(--text-faint);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.stat-card .value {
  display: block;
  margin-top: 12px;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.05em;
}

.stat-card .meta {
  display: block;
  margin-top: 6px;
  color: var(--text-faint);
  font-size: 13px;
}

.panel-note {
  margin-top: 14px;
  color: var(--text-faint);
  font-size: 13px;
}

.empty-card {
  padding: 28px;
  text-align: center;
}

.empty-card h3 {
  margin: 14px 0 8px;
  font-size: 22px;
  font-weight: 800;
}

.empty-card p {
  margin: 0;
  color: var(--text-faint);
  font-size: 14px;
}

.list-rows {
  display: grid;
  gap: 12px;
}

.row-item {
  padding: 16px 18px;
  border-radius: 20px;
  background: rgba(13, 25, 43, 0.86);
  border: 1px solid rgba(96, 130, 189, 0.2);
}

.row-item strong {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 16px;
}

.row-item span {
  display: block;
  margin-top: 6px;
  color: var(--text-faint);
  font-size: 13px;
  line-height: 1.6;
}

.helper-text {
  color: var(--text-faint);
  font-size: 12px;
  margin-top: 6px;
}

.stTextArea textarea,
.stTextInput input,
.stSelectbox [data-baseweb="select"] > div,
.stDateInput input {
  background: rgba(7, 16, 29, 0.92) !important;
  color: var(--text) !important;
  border: 1px solid rgba(96, 130, 189, 0.28) !important;
  border-radius: 22px !important;
  box-shadow: none !important;
}

.stTextArea textarea {
  min-height: 150px;
  line-height: 1.75 !important;
  padding: 16px 18px !important;
  font-size: 15px !important;
}

.stTextInput input,
.stDateInput input {
  min-height: 50px !important;
  padding: 0 16px !important;
  font-size: 15px !important;
}

.stTextArea textarea:focus,
.stTextInput input:focus,
.stDateInput input:focus,
.stSelectbox [data-baseweb="select"] > div:focus-within {
  border-color: rgba(95, 184, 255, 0.64) !important;
  box-shadow: 0 0 0 1px rgba(95, 184, 255, 0.55) !important;
}

.stTextArea label,
.stTextInput label,
.stSelectbox label,
.stDateInput label,
.stRadio label {
  color: var(--text) !important;
  font-size: 15px !important;
  font-weight: 700 !important;
}

.stButton > button {
  width: 100%;
  min-height: 50px;
  border-radius: 20px;
  border: 1px solid rgba(96, 130, 189, 0.24);
  background: rgba(15, 28, 47, 0.92);
  color: var(--text);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.01em;
  transition: 0.18s ease;
}

.stButton > button:hover {
  border-color: rgba(95, 184, 255, 0.5);
  color: #ffffff;
  transform: translateY(-1px);
}

.stButton > button[kind="primary"] {
  background: linear-gradient(180deg, #63baff, #4aa5f0);
  color: #07111f;
  border: none;
  box-shadow: 0 12px 30px rgba(74, 165, 240, 0.28);
}

.stButton > button[kind="primary"]:hover {
  background: linear-gradient(180deg, #7ac5ff, #53adf7);
}

.stTabs [data-baseweb="tab-list"] {
  gap: 10px;
  background: transparent;
  border-bottom: none;
  margin-bottom: 12px;
}

.stTabs [data-baseweb="tab"] {
  height: auto;
  padding: 12px 18px;
  border-radius: 999px;
  background: rgba(14, 27, 46, 0.86);
  border: 1px solid rgba(96, 130, 189, 0.22);
  color: var(--text-soft);
  font-size: 14px;
  font-weight: 700;
}

.stTabs [aria-selected="true"] {
  background: rgba(17, 38, 60, 0.95) !important;
  border-color: rgba(95, 184, 255, 0.4) !important;
  color: var(--blue) !important;
}

[data-testid="metric-container"] {
  background: rgba(13, 25, 43, 0.92);
  border: 1px solid rgba(96, 130, 189, 0.22);
  border-radius: 22px;
  padding: 18px;
  box-shadow: none;
}

[data-testid="metric-container"] label {
  color: var(--text-faint) !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
  color: var(--text) !important;
  font-size: 31px !important;
  font-weight: 800 !important;
  letter-spacing: -0.05em;
}

.streamlit-expanderHeader {
  border-radius: 20px !important;
  background: rgba(13, 25, 43, 0.94) !important;
  border: 1px solid rgba(96, 130, 189, 0.2) !important;
  color: var(--text) !important;
  font-size: 14px !important;
  font-weight: 700 !important;
}

.streamlit-expanderContent {
  background: rgba(10, 18, 31, 0.92) !important;
  border: 1px solid rgba(96, 130, 189, 0.16) !important;
  border-top: none !important;
  border-radius: 0 0 20px 20px !important;
}

.stDataFrame {
  border-radius: 20px !important;
  overflow: hidden;
  border: 1px solid rgba(96, 130, 189, 0.18) !important;
}

.stDataFrame [role="grid"] {
  background: rgba(9, 18, 32, 0.95) !important;
}

.stAlert {
  border-radius: 18px !important;
  border: 1px solid rgba(96, 130, 189, 0.18) !important;
  background: rgba(13, 25, 43, 0.92) !important;
}

.stCaption,
.stMarkdown p {
  color: inherit;
}

.stProgress > div > div {
  background: rgba(96, 130, 189, 0.18) !important;
  height: 8px !important;
  border-radius: 999px !important;
}

.stProgress > div > div > div > div {
  background: linear-gradient(90deg, #5fb8ff, #2dd4bf) !important;
  border-radius: 999px !important;
}

@media (max-width: 1080px) {
  .hero-grid,
  .feature-grid,
  .metric-strip {
    grid-template-columns: 1fr;
  }
}
</style>
""",
    unsafe_allow_html=True,
)


ICON_MAP = {
    "logo": "M12 3l7 4v10l-7 4-7-4V7l7-4Zm0 2.3L7 7.8v8.4l5 2.8 5-2.8V7.8l-5-2.5Zm-3.5 4.2h7v1.8h-7V9.5Zm0 3.2h7v1.8h-7v-1.8Z",
    "strategy": "M5 6h14M5 12h9M5 18h14M17 10l2 2 3-4",
    "report": "M5 18h14M7 15V9m5 6V5m5 10v-3",
    "settings": "M12 8.5A3.5 3.5 0 1 1 12 15.5A3.5 3.5 0 0 1 12 8.5Zm0-5.5v2.2m0 13.6V21m9-9h-2.2M5.2 12H3m15.16-6.16-1.55 1.55M7.39 16.61l-1.55 1.55m0-12.32 1.55 1.55m8.77 8.77 1.55 1.55",
    "spark": "M13 2 6 14h5l-1 8 7-12h-5l1-8Z",
    "shield": "M12 3l7 3v5c0 4.6-2.8 8.5-7 10-4.2-1.5-7-5.4-7-10V6l7-3Z",
    "database": "M12 4c4.4 0 8 1.3 8 3s-3.6 3-8 3-8-1.3-8-3 3.6-3 8-3Zm-8 7v3c0 1.7 3.6 3 8 3s8-1.3 8-3v-3m-16 6v3c0 1.7 3.6 3 8 3s8-1.3 8-3v-3",
    "check": "M5 12.5 9.2 16 19 6.5",
    "calendar": "M8 3v3m8-3v3M4 8h16M5 6h14a1 1 0 0 1 1 1v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a1 1 0 0 1 1-1Z",
    "arrow-up": "M12 19V5m0 0 5 5m-5-5-5 5",
    "arrow-down": "M12 5v14m0 0 5-5m-5 5-5-5",
    "trash": "M4 7h16m-11 0V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-7 0 1 12h6l1-12",
    "save": "M5 4h11l3 3v13H5V4Zm3 0v5h7V4",
    "chart": "M4 18 9 11l4 3 7-8",
    "book": "M6 5.5A2.5 2.5 0 0 1 8.5 3H19v15H8.5A2.5 2.5 0 0 0 6 20.5V5.5Zm0 0V19M10 7h5m-5 4h5",
    "cube": "M12 3 4.5 7 12 11l7.5-4L12 3Zm-7.5 5v8L12 21l7.5-5V8",
}


def icon(name: str, size: int = 18, color: str = "currentColor") -> str:
    path = ICON_MAP.get(name, "")
    return (
        f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' fill='none' "
        f"stroke='{color}' stroke-width='1.9' stroke-linecap='round' stroke-linejoin='round' "
        f"xmlns='http://www.w3.org/2000/svg'><path d=\"{path}\"/></svg>"
    )


if "page" not in st.session_state:
    st.session_state.page = "strategy"
if "api" not in st.session_state:
    st.session_state.api = get_source()
if "results" not in st.session_state:
    st.session_state.results = {}
if "current_report_id" not in st.session_state:
    st.session_state.current_report_id = None
if "show_suggestion" not in st.session_state:
    st.session_state.show_suggestion = False
if "rag_initialized" not in st.session_state:
    init_rag()
    load_seed_examples()
    st.session_state.rag_initialized = True
if "db_reports_loaded" not in st.session_state:
    init_reports_table()
    for report in list_reports(limit=200):
        report_id = report["id"]
        if report_id not in st.session_state.results:
            full = db_load_report(report_id)
            if full:
                st.session_state.results[report_id] = full
    st.session_state.db_reports_loaded = True


def _current_source_type() -> str:
    cfg = load_config()
    return cfg.get("data_source", "tushare")


def _source_needs_token() -> bool:
    return _current_source_type() == "tushare"


def _source_status_label() -> str:
    source_type = _current_source_type()
    if source_type == "tushare":
        return "已连接" if get_token() else "待配置 Token"
    return f"{source_type} 已就绪"


def _source_status_color() -> str:
    source_type = _current_source_type()
    if source_type == "tushare":
        return "#2dd4bf" if get_token() else "#ffbf66"
    return "#2dd4bf"


def resolve_stock_codes(api, description: str) -> list[str]:
    """从自然语言描述中解析标的范围。"""
    stocks = api.get_stock_basic()
    if stocks.empty:
        for src_name in ["baostock", "akshare", "ashare"]:
            try:
                from core.data_source import create_source

                alt = create_source(src_name)
                stocks = alt.get_stock_basic()
                if not stocks.empty:
                    break
            except (ImportError, ValueError, RuntimeError):
                continue

    if stocks.empty:
        return []

    desc_lower = description.lower().replace(" ", "")

    if any(key in desc_lower for key in ["中证500", "zz500", "zhongzheng500"]):
        return stocks["ts_code"].head(500).tolist()
    if any(key in desc_lower for key in ["沪深300", "hs300", "hushen300"]):
        return stocks["ts_code"].head(300).tolist()
    if any(key in desc_lower for key in ["中证1000", "zz1000"]):
        return stocks["ts_code"].head(1000).tolist()
    if any(key in desc_lower for key in ["全a股", "全a", "所有股票", "全市场"]):
        return stocks["ts_code"].tolist()
    if any(key in desc_lower for key in ["创业板", "cyb"]):
        return stocks[stocks["ts_code"].str.endswith(".SZ")].head(500).tolist()
    if any(key in desc_lower for key in ["科创板", "kcb"]):
        return stocks[stocks["ts_code"].str.startswith("688")].head(500).tolist()
    return stocks["ts_code"].head(500).tolist()


def parse_capital(description: str) -> float:
    import re

    matches = re.findall(r"(\d+\.?\d*)\s*万", description)
    if matches:
        return float(matches[0]) * 10000
    matches = re.findall(r"(\d+\.?\d*)\s*元", description)
    if matches:
        return float(matches[0])
    return 100000


def parse_shares(description: str) -> int:
    import re

    matches = re.findall(r"(\d+)\s*股", description)
    if matches:
        return int(matches[0])
    return 100


def render_shell_open() -> None:
    st.markdown("<div class='shell'>", unsafe_allow_html=True)


def render_shell_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def top_bar() -> None:
    st.markdown(
        f"""
<div class="app-topbar">
  <div class="brand">
    <div class="brand-mark">{icon("logo", 22, "#5fb8ff")}</div>
    <div class="brand-copy">
      <h1>A股回测系统</h1>
      <p>自然语言策略回测工作台 · 简体中文界面 · 更年轻的产品化视觉</p>
    </div>
  </div>
  <div class="status-cluster">
    <div class="status-pill">
      <span class="status-dot" style="background:{_source_status_color()};"></span>
      数据源状态：{_source_status_label()}
    </div>
    <div class="ghost-pill">{icon('database', 16, '#7f95bc')} 当前源：{_current_source_type()}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    pages = [
        ("策略工作台", "strategy", "strategy"),
        ("回测报告", "report", "report"),
        ("系统设置", "settings", "settings"),
    ]
    cols = st.columns(3)
    for idx, (label, page, icon_name) in enumerate(pages):
        with cols[idx]:
            clicked = st.button(
                f"{label}",
                key=f"nav_{page}",
                width="stretch",
                type="primary" if st.session_state.page == page else "secondary",
            )
            if clicked:
                st.session_state.page = page
                st.rerun()


def hero_banner(
    kicker: str,
    title: str,
    description: str,
    chips: list[str],
    side_items: list[tuple[str, str]],
) -> None:
    chip_html = "".join(
        f"<div class='chip'>{icon('check', 14, '#5fb8ff')}{item}</div>" for item in chips
    )
    side_html = "".join(
        f"<div class='side-item'><strong>{name}</strong><span>{desc}</span></div>"
        for name, desc in side_items
    )
    st.markdown(
        f"""
<div class="hero-grid">
  <div class="hero-panel">
    <div class="hero-kicker">{icon('spark', 14, '#5fb8ff')}{kicker}</div>
    <div class="hero-title">{title}</div>
    <p class="hero-desc">{description}</p>
    <div class="chip-row">{chip_html}</div>
  </div>
  <div class="hero-side">
    <p class="side-title">本次改版重点</p>
    {side_html}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def section_intro(title: str, desc: str) -> None:
    st.markdown(
        f"""
<div class="section-label">
  <div>
    <h2>{title}</h2>
    <p>{desc}</p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def glass_card(title: str, subtitle: str = "") -> None:
    subtitle_html = f"<p class='card-subtitle'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"<div class='glass-card'><h3 class='card-title'>{title}</h3>{subtitle_html}",
        unsafe_allow_html=True,
    )


def close_card() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_feature_grid(items: list[tuple[str, str]]) -> None:
    blocks = "".join(
        f"<div class='feature'><strong>{title}</strong><span>{desc}</span></div>"
        for title, desc in items
    )
    st.markdown(f"<div class='feature-grid'>{blocks}</div>", unsafe_allow_html=True)


def render_metric_strip(cards: list[dict]) -> None:
    html = ""
    for card in cards:
        tone = card.get("tone", "")
        html += (
            f"<div class='stat-card {tone}'>"
            f"<span class='label'>{card['label']}</span>"
            f"<span class='value' style='color:{card.get('color', '#eef4ff')};'>{card['value']}</span>"
            f"<span class='meta'>{card['meta']}</span>"
            f"</div>"
        )
    st.markdown(f"<div class='metric-strip'>{html}</div>", unsafe_allow_html=True)


def empty_state(title: str, desc: str) -> None:
    st.markdown(
        f"""
<div class="empty-card">
  <div>{icon('cube', 26, '#5fb8ff')}</div>
  <h3>{title}</h3>
  <p>{desc}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def render_reference_list(items: list[tuple[str, str]], title: str, subtitle: str) -> None:
    glass_card(title, subtitle)
    rows = "".join(
        f"<div class='row-item'><strong>{name}<span>{meta}</span></strong></div>" for name, meta in items
    )
    st.markdown(f"<div class='list-rows'>{rows}</div>", unsafe_allow_html=True)
    close_card()


def main() -> None:
    render_shell_open()
    top_bar()

    if st.session_state.page == "strategy":
        show_strategy_page()
    elif st.session_state.page == "report":
        show_report_page()
    else:
        show_settings_page()

    render_shell_close()


def show_strategy_page() -> None:
    hero_banner(
        kicker="策略工作台",
        title="把策略想法写成一句中文，系统负责把它变成回测结果",
        description=(
            "保留你现在这套自然语言驱动的使用方式，不新增多余筛选器。"
            "这次前端重点处理的是信息层级、排版节奏、中文表达和整体视觉一致性。"
        ),
        chips=["自然语言优先", "A股规则内置", "200只标的上限扫描", "统一深色中文界面"],
        side_items=[
            ("更清晰", "买入条件、卖出条件、日期和状态提示被重新分组，阅读压力更低。"),
            ("更年轻", "整体换成更现代的深色玻璃卡片风格，图标和按钮不再显得陈旧。"),
            ("更完整", "参考策略、说明文案、运行反馈和结果跳转都统一到了一个节奏里。"),
        ],
    )

    section_intro("策略输入", "先写策略，再运行回测。控件尽量少，但每一块信息都更清楚。")

    glass_card(
        "策略描述区",
        "所有文案改成简体中文，并将说明信息放在输入区附近，减少来回寻找。",
    )

    col_left, col_right = st.columns([1.45, 0.9], gap="large")
    with col_left:
        buy_desc = st.text_area(
            "买入条件",
            value="中证500日线级别，总资金10万元，5日均线上穿20日均线时买入100股",
            placeholder="例如：中证500日线级别，总资金10万元，5日均线上穿20日均线时买入100股",
            height=180,
        )
        st.markdown(
            "<div class='helper-text'>建议把标的范围、级别、总资金、触发条件和每笔股数写在同一句里，模型更容易正确解析。</div>",
            unsafe_allow_html=True,
        )

        sell_desc = st.text_area(
            "卖出条件",
            value="5日均线下穿20日均线时卖出全部持仓，或亏损超5%止损",
            placeholder="例如：5日均线下穿20日均线时卖出全部持仓，或亏损超5%止损",
            height=160,
        )
        st.markdown(
            "<div class='helper-text'>卖出条件尽量明确：是止损、止盈、趋势反转，还是全部清仓。</div>",
            unsafe_allow_html=True,
        )

    with col_right:
        render_feature_grid(
            [
                ("自然语言解析", "继续沿用自然语言描述策略，不额外增加复杂表单配置。"),
                ("中文提示更准确", "补充输入说明，减少用户不知道该怎么写策略的情况。"),
                ("运行反馈更直接", "扫描数量、进度、完成状态和结果页跳转会更清晰。"),
            ]
        )

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        start_date = st.text_input("起始日期", value="2024-01-01")
        end_date = st.text_input("结束日期", value="2024-12-31")
        run_btn = st.button("生成策略并开始回测", type="primary", width="stretch")
        st.markdown(
            "<div class='panel-note'>当前界面只保留必要控制项。策略范围、交易规则、资金和股数继续交给中文描述完成。</div>",
            unsafe_allow_html=True,
        )

    close_card()

    if buy_desc and sell_desc:
        similar = search_examples(buy_desc[:60], top_k=3)
        if similar:
            section_intro("相关策略参考", "系统根据你的买入描述检索相近策略，帮助你快速校验表达是否准确。")
            glass_card("参考策略", "这里只展示与当前描述最接近的内置或历史策略。")
            for item in similar:
                st.markdown(
                    f"""
<div class="row-item">
  <strong>{item['name']}<span>{item['source'] if item.get('source') else '策略库'}</span></strong>
  <span>{item['description'][:120]}...</span>
</div>
""",
                    unsafe_allow_html=True,
                )
                st.code(item["code"][:220], language="python")
            close_card()

    if run_btn:
        if _source_needs_token() and not get_token():
            st.error("当前数据源是 Tushare，请先在“系统设置”里配置 Token，或切换到无需 Token 的免费数据源。")
            return

        with st.spinner("正在拉取行情并运行回测，请稍候..."):
            api = st.session_state.api
            stock_codes = resolve_stock_codes(api, buy_desc + " " + sell_desc)
            if not stock_codes:
                st.error("无法解析标的范围。请在买入或卖出条件中明确写出“沪深300”“中证500”“全市场”等关键词。")
                return

            stock_codes = stock_codes[:200]
            st.info(f"本次将扫描 {len(stock_codes)} 只标的。")

            capital = parse_capital(buy_desc)
            shares_per_trade = parse_shares(buy_desc)

            stock_data: dict[str, pd.DataFrame] = {}
            progress = st.progress(0.0)
            for idx, code in enumerate(stock_codes):
                df = api.get_daily(code, start_date.replace("-", ""), end_date.replace("-", ""))
                if not df.empty and len(df) > 20:
                    df = df.set_index("trade_date")
                    df.index = pd.to_datetime(df.index)
                    stock_data[code] = df
                progress.progress((idx + 1) / len(stock_codes))

            engine = SignalEngine(shares_per_trade=shares_per_trade)
            strategy = generate_strategy(buy_desc, sell_desc)
            results = engine.run(strategy, stock_data)

            equity_curve = results.get("portfolio_equity")
            if equity_curve is not None and not equity_curve.empty:
                portfolio_metrics = compute_metrics(equity_curve, capital)
            else:
                portfolio_metrics = {}
            trade_metrics = compute_trade_metrics(results.get("all_trades", pd.DataFrame()))

            report_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report = {
                "id": report_id,
                "name": f"回测_{report_id}",
                "buy_desc": buy_desc,
                "sell_desc": sell_desc,
                "start_date": start_date,
                "end_date": end_date,
                "capital": capital,
                "shares_per_trade": shares_per_trade,
                "results": results,
                "portfolio_metrics": portfolio_metrics,
                "trade_metrics": trade_metrics,
                "created_at": datetime.datetime.now().isoformat(),
                "strategy_name": strategy.name,
            }
            st.session_state.results[report_id] = report
            st.session_state.current_report_id = report_id
            st.session_state.show_suggestion = False

            try:
                db_save_report(report)
            except (ValueError, RuntimeError, OSError):
                pass

            try:
                add_example(
                    name=report["name"],
                    description=f"买入：{buy_desc}；卖出：{sell_desc}",
                    code=f"# 策略类型：{strategy.name}\n# 买入：{buy_desc}\n# 卖出：{sell_desc}",
                    tags=["用户策略", strategy.name],
                    source="user",
                    score=60,
                )
            except (ValueError, RuntimeError, OSError):
                pass

            if results["total_stocks"] > 0:
                st.success(
                    f"回测完成：扫描 {results['total_stocks']} 只标的，"
                    f"共形成 {results['total_signals']} 笔交易，胜率 {results['win_rate']}%。"
                )
                st.session_state.page = "report"
                st.rerun()
            st.warning("回测已执行，但没有产生有效交易信号。你可以收紧或放宽条件后再试一次。")


def show_report_page() -> None:
    hero_banner(
        kicker="回测报告",
        title="把结果讲清楚，比把数字堆出来更重要",
        description=(
            "结果页这次重点处理了数据层级、图表样式和中文表达。"
            "先看核心指标，再看净值、分布、个股明细，避免用户一上来就迷失在细节里。"
        ),
        chips=["KPI 优先级更清晰", "图表中文化", "个股明细更聚焦", "报告管理更统一"],
        side_items=[
            ("更易读", "关键指标拆成统一卡片，减少原本看起来像调试数据的感觉。"),
            ("更专业", "图表主题与页面外壳完全统一，不再出现浅色图表穿插深色页面。"),
            ("更完整", "报告重命名、历史切换、删除和优化建议都放在一个区域处理。"),
        ],
    )

    report_ids = list(st.session_state.results.keys())
    if not report_ids:
        empty_state("还没有回测结果", "先去“策略工作台”运行一次回测，结果页才会出现报告、图表和个股明细。")
        return

    current_id = st.session_state.current_report_id
    if current_id not in st.session_state.results:
        current_id = report_ids[-1]
        st.session_state.current_report_id = current_id

    report = st.session_state.results[current_id]
    results = report["results"]

    section_intro("报告管理", "这部分负责命名、切换历史报告和处理删除操作。")
    glass_card("当前报告", "先确定你正在查看哪一份报告，再往下看绩效和明细。")

    c1, c2, c3, c4 = st.columns([2.0, 1.0, 2.0, 1.0], gap="medium")
    with c1:
        new_name = st.text_input("报告名称", value=report["name"])
    with c2:
        if st.button("保存报告", width="stretch"):
            report["name"] = new_name
            try:
                db_save_report(report)
            except (ValueError, RuntimeError, OSError):
                pass
            st.toast("报告名称已保存")
    with c3:
        selected_id = st.selectbox(
            "历史报告",
            options=report_ids,
            index=report_ids.index(current_id),
            format_func=lambda item: st.session_state.results[item]["name"],
        )
        if selected_id != current_id:
            st.session_state.current_report_id = selected_id
            st.session_state.show_suggestion = False
            st.rerun()
    with c4:
        if st.button("删除报告", width="stretch"):
            del st.session_state.results[current_id]
            try:
                delete_report(current_id)
            except (ValueError, RuntimeError, OSError):
                pass
            remaining = list(st.session_state.results.keys())
            st.session_state.current_report_id = remaining[-1] if remaining else None
            st.session_state.show_suggestion = False
            st.rerun()

    st.markdown(
        f"<div class='panel-note'>策略名称：{report.get('strategy_name', '未识别')} · "
        f"区间：{report.get('start_date', '—')} 至 {report.get('end_date', '—')} · "
        f"总资金：¥{report.get('capital', 100000):,.0f} · 每笔：{report.get('shares_per_trade', 100)} 股</div>",
        unsafe_allow_html=True,
    )
    close_card()

    metric_cards = [
        {"label": "扫描标的", "value": str(results["total_stocks"]), "meta": "形成有效交易的标的数", "tone": ""},
        {"label": "总交易", "value": str(results["total_signals"]), "meta": "回测期间总成交笔数", "tone": ""},
        {"label": "盈利笔数", "value": str(results["win_trades"]), "meta": "收益大于 0 的交易", "tone": "rose", "color": "#ff8eaa"},
        {"label": "亏损笔数", "value": str(results["loss_trades"]), "meta": "收益小于等于 0 的交易", "tone": "teal", "color": "#50e0c5"},
        {"label": "胜率", "value": f"{results['win_rate']}%", "meta": "盈利 / 总交易", "tone": "rose", "color": "#ff8eaa"},
        {"label": "平均收益", "value": f"{results['avg_pnl']}%", "meta": "单笔平均盈亏", "tone": "rose" if results["avg_pnl"] >= 0 else "teal", "color": "#ff8eaa" if results["avg_pnl"] >= 0 else "#50e0c5"},
    ]
    render_metric_strip(metric_cards)

    section_intro("策略建议与分析", "先给出结论，再展开图表和个股明细。")
    glass_card("策略优化建议", "根据当前回测结果，给出下一轮调参或改写策略时最值得优先尝试的方向。")
    suggest_cols = st.columns([4.2, 1.2], gap="large")
    with suggest_cols[1]:
        if st.button("生成优化建议", width="stretch"):
            st.session_state.show_suggestion = True
    with suggest_cols[0]:
        if st.session_state.show_suggestion:
            st.info(_generate_suggestion(results, report))
        else:
            st.markdown(
                "<div class='panel-note'>点击右侧按钮后，系统会根据胜率、平均收益和信号数量生成中文优化建议。</div>",
                unsafe_allow_html=True,
            )
    close_card()

    summary = results.get("stock_summary")
    if isinstance(summary, list):
        summary = pd.DataFrame(summary)
    if summary is None or summary.empty:
        empty_state("当前报告没有交易明细", "这次回测没有形成可展示的个股交易记录，因此只保留基本统计信息。")
        return

    tab_overview, tab_details = st.tabs(["组合概览", "个股明细"])

    with tab_overview:
        section_intro("组合概览", "把组合层面的指标、净值曲线和收益分布放在同一层里看，更容易判断策略整体是否成立。")
        portfolio_metrics = report.get("portfolio_metrics", {})
        trade_metrics = report.get("trade_metrics", {})
        if portfolio_metrics:
            st.markdown(
                render_metrics_html(portfolio_metrics, trade_metrics, report.get("capital", 100000)),
                unsafe_allow_html=True,
            )

        equity_curve = results.get("portfolio_equity")
        if equity_curve is not None and not equity_curve.empty:
            st.plotly_chart(
                plot_portfolio_equity(equity_curve),
                width="stretch",
                config={"displayModeBar": False},
            )

        all_trades_df = results.get("all_trades")
        if all_trades_df is not None and not all_trades_df.empty:
            st.plotly_chart(
                plot_trade_pnl_distribution(all_trades_df),
                width="stretch",
                config={"displayModeBar": False},
            )

    with tab_details:
        section_intro("个股明细", "默认按总盈亏排序，只展开前 50 只最值得查看的标的，避免信息过载。")

        stocks_df = st.session_state.api.get_stock_basic()
        name_map: dict[str, str] = {}
        if not stocks_df.empty:
            for _, row in stocks_df.iterrows():
                name_map[row["ts_code"]] = row.get("name", "")

        for _, row in summary.head(50).iterrows():
            code = row["ts_code"]
            stock_name = name_map.get(code, "")
            total_trades = int(row["total_trades"])
            win_rate = row["win_rate"]
            total_pnl = row["total_pnl"]
            avg_pnl = row["avg_pnl"]
            total_pnl_pct = row.get("total_pnl_pct", 0)
            pnl_color = "#ff8eaa" if total_pnl >= 0 else "#50e0c5"
            arrow = icon("arrow-up" if total_pnl >= 0 else "arrow-down", 14, pnl_color)

            with st.expander(
                f"{code} {stock_name} · {total_trades} 笔交易 · 胜率 {win_rate}% · 平均 {avg_pnl}%"
            ):
                st.markdown(
                    f"<div class='panel-note'>{arrow} 总盈亏：<span style='color:{pnl_color};font-weight:700;'>"
                    f"¥{total_pnl:+,.0f}</span> · 总收益率：<span style='color:{pnl_color};font-weight:700;'>"
                    f"{total_pnl_pct:+.2f}%</span></div>",
                    unsafe_allow_html=True,
                )

                ohlcv = results.get("stock_ohlcv", {}).get(code)
                trades = results["stock_trades"].get(code, [])
                if ohlcv is not None and trades:
                    st.plotly_chart(
                        plot_stock_kline(code, ohlcv, trades, stock_name),
                        width="stretch",
                        config={"displayModeBar": False},
                    )

                if trades:
                    table_rows = []
                    for trade in trades:
                        table_rows.append(
                            {
                                "买入日期": trade.buy_date,
                                "买入价格": f"{trade.buy_price:.2f}",
                                "卖出日期": trade.sell_date,
                                "卖出价格": f"{trade.sell_price:.2f}" if trade.sell_price else "—",
                                "收益率": f"{trade.pnl_pct:+.2f}%",
                                "盈亏额": f"¥{trade.pnl_amount:+,.0f}",
                                "持仓天数": trade.hold_days,
                                "买入信号": trade.buy_signal,
                                "卖出信号": trade.sell_signal,
                            }
                        )
                    trades_df = pd.DataFrame(table_rows)
                    st.dataframe(trades_df, width="stretch", hide_index=True)


def _generate_suggestion(results: dict, report: dict) -> str:
    win_rate = results.get("win_rate", 0)
    avg_pnl = results.get("avg_pnl", 0)
    total_signals = results.get("total_signals", 0)
    win_trades = results.get("win_trades", 0)
    loss_trades = results.get("loss_trades", 0)

    parts = [
        f"当前策略表现：胜率 {win_rate}%，平均每笔收益 {avg_pnl}%，共 {total_signals} 笔交易（盈利 {win_trades} / 亏损 {loss_trades}）。"
    ]

    if win_rate < 40:
        parts.append("胜率偏低，建议先减少噪声信号。")
        parts.append("1. 加入成交量过滤，例如“成交量大于 5 日均量”。")
        parts.append("2. 拉长均线周期，例如把 5/20 调整为 10/30，减少震荡区间的假突破。")
    elif win_rate < 55:
        parts.append("胜率处于中等水平，可以优先控制回撤。")
        parts.append("1. 补充明确止损，例如单笔亏损超过 5% 强制离场。")
        parts.append("2. 增加趋势过滤，例如只在 60 日均线向上时执行买入。")
    else:
        parts.append("胜率已经不错，下一步更值得关注收益兑现效率。")
        parts.append("1. 增加止盈条件，例如收益达到 12% 至 15% 时分批卖出。")
        parts.append("2. 测试更短的持仓周期，避免盈利回吐。")

    if avg_pnl < 0:
        parts.append("平均收益仍为负，说明策略虽然能命中部分交易，但整体过滤条件还不够严格。")
    if total_signals < 50:
        parts.append("信号数量偏少，可以适当放宽入场条件，或扩大标的范围做对比测试。")
    if report.get("capital", 100000) >= 500000 and total_signals < 20:
        parts.append("资金规模较大但信号稀少，后续可以重点关注策略容量与成交效率。")

    return "\n".join(parts)


def show_settings_page() -> None:
    hero_banner(
        kicker="系统设置",
        title="设置页不只是能用，还要看起来像正式产品的一部分",
        description=(
            "这里保留你原来的数据源、缓存和策略库能力，但重新整理了模块顺序。"
            "用户先看到当前配置，再看到缓存状态和策略库，不会像以前那样一页全是散点信息。"
        ),
        chips=["数据源配置", "连接验证", "本地缓存", "RAG 策略库"],
        side_items=[
            ("更统一", "设置页也沿用同一套玻璃卡片和中文标签，避免像后台调试页。"),
            ("更直接", "配置、验证、缓存和策略库拆成独立模块，查找动作更快。"),
            ("更细致", "提示文案改成中文场景表达，降低新用户第一次配置门槛。"),
        ],
    )

    cfg = load_config()
    current_source = cfg.get("data_source", "tushare")

    section_intro("数据源配置", "先确定当前数据源，再决定是否需要 Token 与地址。")
    glass_card("数据源", "如果使用 Tushare，需要在这里填写 Token；其他免费源可以直接启用。")

    source_keys = list(AVAILABLE_SOURCES.keys())
    source_index = source_keys.index(current_source) if current_source in source_keys else 0
    selected_source = st.selectbox(
        "选择数据源",
        options=source_keys,
        index=source_index,
        format_func=lambda item: f"{item} · {AVAILABLE_SOURCES[item]}",
    )

    token = ""
    api_url = ""
    if selected_source == "tushare":
        st.markdown(
            "<div class='panel-note'>Tushare Pro 需要先在官网注册并获取 Token。建议把 API 地址和 Token 一起保存，避免切换后丢失。</div>",
            unsafe_allow_html=True,
        )
        api_url = st.text_input("API 地址", value=cfg.get("tushare_url", "http://api.tushare.pro"))
        token = st.text_input("Token", value=cfg.get("tushare_token", ""), type="password")
    else:
        st.info(f"当前选择的是 {selected_source}，无需 Token，可直接尝试连接验证。")

    action_cols = st.columns(2, gap="medium")
    with action_cols[0]:
        if st.button("保存当前配置", width="stretch", type="primary"):
            from core.data import save_source_config

            save_source_config(selected_source, token, api_url)
            st.session_state.api = get_source()
            st.success(f"数据源已切换为 {selected_source}")
    with action_cols[1]:
        if st.button("验证连接", width="stretch"):
            api = st.session_state.api
            if api.name.lower().replace(" ", "") != selected_source:
                from core.data import create_source

                api = create_source(selected_source)
            ok, message = api.validate()
            if ok:
                st.success(f"连接验证通过：{message}")
            else:
                st.error(f"连接验证失败：{message}")
    close_card()

    section_intro("数据源说明", "把常用差异说明清楚，避免用户每次都要回文档翻。")
    render_reference_list(
        [
            ("Tushare Pro", "专业稳定，需 Token，免费版有调用频率限制。"),
            ("AkShare", "开源免费，覆盖面广，无需注册。"),
            ("Baostock", "历史数据稳定，无需 Token。"),
            ("Ashare", "极简数据源，适合快速试跑。"),
        ],
        "数据源对比",
        "这里保留简洁版说明，避免设置页变成一张过长的资料表。",
    )

    section_intro("本地缓存", "缓存状态做成指标卡后，用户能一眼看出数据规模和清理成本。")
    stats = st.session_state.api.get_stats()
    render_metric_strip(
        [
            {"label": "日线记录", "value": str(stats.get("daily_records", 0)), "meta": "本地已缓存的数据行数", "tone": "teal", "color": "#50e0c5"},
            {"label": "覆盖标的", "value": str(stats.get("stocks", 0)), "meta": "当前缓存覆盖的股票数量", "tone": "teal", "color": "#50e0c5"},
            {"label": "存储空间", "value": f"{stats.get('size_mb', 0)} MB", "meta": "SQLite 缓存体积", "tone": "teal", "color": "#50e0c5"},
            {"label": "最早数据", "value": str(stats.get("earliest", "--")), "meta": "已缓存历史起点", "tone": "", "color": "#eef4ff"},
            {"label": "当前数据源", "value": selected_source, "meta": "缓存读取将优先使用此来源", "tone": "", "color": "#eef4ff"},
            {"label": "清理动作", "value": "可手动", "meta": "必要时清空后重新拉取", "tone": "", "color": "#eef4ff"},
        ]
    )
    clear_cols = st.columns([1.2, 2.8], gap="large")
    with clear_cols[0]:
        if st.button("清空本地缓存", width="stretch"):
            clear_cache()
            st.success("缓存已清空。下次回测会重新拉取所需行情数据。")
    with clear_cols[1]:
        st.markdown(
            "<div class='panel-note'>清空缓存是破坏性操作，但只影响本地缓存数据库，不会删除报告记录和策略库内容。</div>",
            unsafe_allow_html=True,
        )

    section_intro("策略库", "RAG 策略库也纳入同一套界面语言，避免像一个附加功能。")
    glass_card("策略模板库", "内置模板可以帮助新用户了解系统更容易理解的中文策略表达方式。")
    rag_count = count_examples()
    st.markdown(
        f"<div class='panel-note'>当前策略模板数量：<span style='color:#5fb8ff;font-weight:700;'>{rag_count}</span></div>",
        unsafe_allow_html=True,
    )
    recent_examples = list_examples(limit=5, source="builtin")
    for example in recent_examples:
        st.markdown(
            f"""
<div class="row-item">
  <strong>{example['name']}<span>内置模板</span></strong>
  <span>{example['description'][:120]}...</span>
</div>
""",
            unsafe_allow_html=True,
        )
        with st.expander("查看模板代码"):
            st.code(example["code"], language="python")
    close_card()


if __name__ == "__main__":
    main()
