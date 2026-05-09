"""A股回测系统 — Streamlit 主入口
匹配 v5 原型：
  - 策略页：买入条件 + 卖出条件 + 日期范围
  - 结果页：报告保存/历史 + AI优化建议 + 可展开标的列表
  - 设置页：Tushare Token/URL + 缓存
"""
import streamlit as st
import pandas as pd
import datetime

from utils.config import load_config, save_config, get_token, get_api_url
from core.data import get_source, get_source_config, save_source_config
from core.data_source import AVAILABLE_SOURCES
from core.cache import get_cache_stats, clear_cache
from core.engine import SignalEngine
from strategies.generator import generate_strategy
from rag.store import add_example, list_examples, count_examples, init_rag
from rag.retriever import search_examples
from rag.seed_loader import load_seed_examples
from rag.report_store import (
    init_reports_table, save_report as db_save_report,
    load_report as db_load_report, list_reports, delete_report,
)

st.set_page_config(page_title="A股回测系统", layout="wide", page_icon="📊")

# ── 初始化 ──
if "page" not in st.session_state:
    st.session_state.page = "strategy"
if "api" not in st.session_state:
    st.session_state.api = get_source()
if "results" not in st.session_state:
    st.session_state.results = {}
if "current_report_id" not in st.session_state:
    st.session_state.current_report_id = None
if "rag_initialized" not in st.session_state:
    init_rag()
    load_seed_examples()
    st.session_state.rag_initialized = True
if "db_reports_loaded" not in st.session_state:
    init_reports_table()
    for r in list_reports(limit=200):
        rid = r["id"]
        if rid not in st.session_state.results:
            full = db_load_report(rid)
            if full:
                st.session_state.results[rid] = full
    st.session_state.db_reports_loaded = True


# ════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════

def resolve_stock_codes(api, description: str) -> list:
    """从自然语言描述中解析标的范围
    简单策略：用关键词匹配预定义范围，未来可升级为 AI 解析
    """
    stocks = api.get_stock_basic()
    if stocks.empty:
        return []
    desc_lower = description.lower().replace(" ", "")

    # 关键词匹配
    if any(k in desc_lower for k in ["中证500", "zz500", "zhongzheng500"]):
        # 取前 500 只
        return stocks["ts_code"].head(500).tolist()
    elif any(k in desc_lower for k in ["沪深300", "hs300", "hushen300"]):
        return stocks["ts_code"].head(300).tolist()
    elif any(k in desc_lower for k in ["中证1000", "zz1000"]):
        return stocks["ts_code"].head(1000).tolist()
    elif any(k in desc_lower for k in ["全a股", "全A", "所有股票", "全市场"]):
        return stocks["ts_code"].tolist()
    else:
        # 默认中证500
        return stocks["ts_code"].head(500).tolist()


def parse_capital(description: str) -> float:
    """从描述中提取总资金（简单方式）"""
    import re
    matches = re.findall(r'(\d+\.?\d*)\s*万', description)
    if matches:
        return float(matches[0]) * 10000
    matches = re.findall(r'(\d+\.?\d*)\s*元', description)
    if matches:
        return float(matches[0])
    return 100000  # 默认 10 万


def parse_shares(description: str) -> int:
    """从描述中提取每笔股数"""
    import re
    matches = re.findall(r'(\d+)\s*股', description)
    if matches:
        return int(matches[0])
    return 100  # 默认 100 股


# ════════════════════════════════════════════
# 页面路由
# ════════════════════════════════════════════

def main():
    # 顶栏
    cols = st.columns([1, 3, 1])
    with cols[0]:
        st.markdown("### 📊 回测系统")
    with cols[1]:
        btns = st.columns(3)
        labels = ["📝 策略", "📈 结果", "⚙️ 设置"]
        for i, (label, page) in enumerate(zip(labels, ["strategy", "report", "settings"])):
            with btns[i]:
                if st.button(label, use_container_width=True,
                             type="primary" if st.session_state.page == page else "secondary"):
                    st.session_state.page = page
                    st.rerun()
    with cols[2]:
        status = "● 已连接" if get_token() else "○ 未配置"
        color = "#26a69a" if get_token() else "#787b86"
        st.markdown(f"<span style='color:{color};font-size:12px;'>{status}</span>",
                    unsafe_allow_html=True)

    st.markdown("---")

    if st.session_state.page == "strategy":
        show_strategy_page()
    elif st.session_state.page == "report":
        show_report_page()
    elif st.session_state.page == "settings":
        show_settings_page()


# ════════════════════════════════════════════
# 策略页面
# ════════════════════════════════════════════
def show_strategy_page():
    st.markdown("## 策略回测")
    st.markdown("用自然语言完整描述策略，AI 自动生成代码并扫描全市场")

    buy_desc = st.text_area(
        "📈 买入条件",
        value="中证500日线级别，总资金10万元，5日均线上穿20日均线时买入100股",
        height=100,
        placeholder="例：中证500日线级别，总资金10万，5日均线上穿20日均线时买入100股",
    )

    sell_desc = st.text_area(
        "📉 卖出条件",
        value="5日均线下穿20日均线时卖出全部持仓，或亏损超5%止损",
        height=80,
        placeholder="例：5日均线下穿20日均线时卖出，或亏损超5%止损",
    )

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.text_input("起始日期", value="2024-01-01")
    with col2:
        end_date = st.text_input("结束日期", value="2024-12-31")

    col_left, col_center, col_right = st.columns([2, 3, 2])
    with col_center:
        run_btn = st.button("🤖 生成策略并回测", type="primary", use_container_width=True)

    # 显示 RAG 检索的相似策略参考
    if buy_desc and sell_desc:
        similar = search_examples(buy_desc[:50], top_k=2)
        if similar:
            with st.expander("📚 相关策略参考", expanded=False):
                for s in similar:
                    st.markdown(f"**{s['name']}** — {s['description'][:60]}...")
                    st.code(s['code'][:200], language="python")

    if run_btn:
        if not get_token():
            st.error("请先在设置页面配置 Tushare Token")
            return

        with st.spinner("正在拉取数据并运行回测..."):
            api = st.session_state.api

            # 解析标的范围
            stock_codes = resolve_stock_codes(api, buy_desc + " " + sell_desc)
            if not stock_codes:
                st.error("无法解析标的范围，请在条件描述中注明（如：沪深300、中证500、全A股）")
                return

            # 限制最多 200 只
            stock_codes = stock_codes[:200]
            st.info(f"📊 扫描 {len(stock_codes)} 只标的")

            # 解析资金和股数
            capital = parse_capital(buy_desc)
            shares_per_trade = parse_shares(buy_desc)

            # 拉取日线数据
            stock_data = {}
            progress = st.progress(0)
            for idx, code in enumerate(stock_codes):
                df = api.get_daily(code, start_date.replace("-", ""), end_date.replace("-", ""))
                if not df.empty and len(df) > 20:
                    df = df.set_index("trade_date")
                    stock_data[code] = df
                progress.progress((idx + 1) / len(stock_codes))

            # 运行回测
            engine = SignalEngine(shares_per_trade=shares_per_trade)
            strat = generate_strategy(buy_desc, sell_desc)
            results = engine.run(strat, stock_data)

            # 保存到 session
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
                "created_at": datetime.datetime.now().isoformat(),
            }
            # 补充策略名称
            report["strategy_name"] = strat.name

            st.session_state.results[report_id] = report
            st.session_state.current_report_id = report_id

            # 持久化到 SQLite
            try:
                db_save_report(report)
            except Exception:
                pass

            # 保存到 RAG
            try:
                add_example(
                    name=report["name"],
                    description=f"买入: {buy_desc}  卖出: {sell_desc}",
                    code=f"# 策略类型: {strat.name}\n# 买入: {buy_desc}\n# 卖出: {sell_desc}",
                    tags=["用户策略", strat.name],
                    source="user",
                    score=60,
                )
            except Exception:
                pass

            summary = results
            if summary["total_stocks"] > 0:
                st.success(f"✅ 回测完成！扫描 {summary['total_stocks']} 只标的，"
                           f"产生 {summary['total_signals']} 笔交易，胜率 {summary['win_rate']}%")
                st.session_state.page = "report"
                st.rerun()
            else:
                st.warning("回测完成，但未产生任何交易信号，请调整条件后重试")


# ════════════════════════════════════════════
# 结果页面
# ════════════════════════════════════════════
def show_report_page():
    # 报告选择
    report_ids = list(st.session_state.results.keys())
    if not report_ids:
        st.info("📭 还没有回测结果，先去「策略」页面运行一次吧")
        return

    current_id = st.session_state.current_report_id
    if current_id not in st.session_state.results and report_ids:
        current_id = report_ids[-1]
        st.session_state.current_report_id = current_id

    # 顶栏：报告名称/保存/历史/删除
    c1, c2, c3, c4 = st.columns([2, 1, 2, 1])
    with c1:
        report_names = {rid: st.session_state.results[rid]["name"] for rid in report_ids}
        selected_name = report_names.get(current_id, "未命名")
        new_name = st.text_input("报告名称", value=selected_name, label_visibility="collapsed")
    with c2:
        if st.button("💾 保存", use_container_width=True):
            if current_id and current_id in st.session_state.results:
                report = st.session_state.results[current_id]
                report["name"] = new_name
                try:
                    db_save_report(report)
                except Exception:
                    pass
            st.toast("已保存")

    with c3:
        selected_id = st.selectbox(
            "历史报告",
            options=report_ids,
            format_func=lambda x: st.session_state.results[x]["name"],
            index=report_ids.index(current_id) if current_id in report_ids else 0,
            label_visibility="collapsed",
        )
        if selected_id != current_id:
            st.session_state.current_report_id = selected_id
            st.rerun()
    with c4:
        if st.button("🗑️ 删除", use_container_width=True, type="secondary"):
            if current_id and current_id in st.session_state.results:
                del st.session_state.results[current_id]
                try:
                    delete_report(current_id)
                except Exception:
                    pass
                remaining = [k for k in st.session_state.results if k in st.session_state.results]
                st.session_state.current_report_id = remaining[-1] if remaining else None
                st.rerun()

    report = st.session_state.results[current_id]
    r = report["results"]

    # 概要栏
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("扫描标的", r["total_stocks"])
    c2.metric("总信号", r["total_signals"])
    c3.metric("盈利", r["win_trades"])
    c4.metric("亏损", r["loss_trades"])
    c5.metric("胜率", f"{r['win_rate']}%")
    c6.metric("平均收益", f"{r['avg_pnl']}%")

    st.markdown(f"<div style='font-size:11px;color:#787b86;margin:-10px 0 14px 0;'>"
                f"总资金 ¥{report.get('capital', 100000):,.0f} · 每笔 {report.get('shares_per_trade', 100)} 股 · "
                f"{report['start_date']} ~ {report['end_date']}</div>",
                unsafe_allow_html=True)

    st.markdown("---")

    # AI 优化建议
    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown("#### 🤖 AI 策略优化建议")
        with col2:
            if st.button("生成优化建议", use_container_width=True):
                st.session_state.show_suggestion = True

        if st.session_state.get("show_suggestion"):
            st.info(_generate_suggestion(r, report))
        else:
            st.caption("点击「生成优化建议」根据回测结果分析策略改进方向")

    st.markdown("---")

    # 标的列表
    summary = r["stock_summary"]
    if summary.empty:
        st.warning("没有产生任何交易信号")
        return

    st.markdown(f"### 📋 触发信号的标的 — 共 {len(summary)} 只")

    stocks_df = st.session_state.api.get_stock_basic()
    name_map = {}
    if not stocks_df.empty:
        for _, row in stocks_df.iterrows():
            name_map[row["ts_code"]] = row.get("name", "")

    for _, row in summary.head(50).iterrows():
        code = row["ts_code"]
        total = int(row["total_trades"])
        win_rate = row["win_rate"]
        total_pnl = row["total_pnl"]
        avg_pnl = row["avg_pnl"]

        pnl_color = "green" if total_pnl >= 0 else "red"
        pnl_icon = "📈" if total_pnl >= 0 else "📉"
        stock_name = name_map.get(code, "")

        with st.expander(
            f"{pnl_icon} {code}  {stock_name}  —  {total} 笔交易  ·  "
            f"胜率 {win_rate}%  ·  收益 {avg_pnl}%"
        ):
            trades = r["stock_trades"].get(code, [])
            if trades:
                data = []
                for t in trades:
                    data.append({
                        "方向": "🟢 买入" if t.buy_date else "",
                        "买入日": t.buy_date,
                        "买入价": f"{t.buy_price:.2f}",
                        "卖出日": t.sell_date,
                        "卖出价": f"{t.sell_price:.2f}" if t.sell_price else "—",
                        "盈亏%": f"{t.pnl_pct:+.2f}%",
                        "盈亏额": f"¥{t.pnl_amount:+.0f}",
                        "持仓天": t.hold_days,
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)

                total_pnl_all = sum(t.pnl_amount for t in trades)
                wins = sum(1 for t in trades if t.pnl_pct > 0)
                color = "#ef5350" if total_pnl_all >= 0 else "#26a69a"
                st.markdown(
                    f"**汇总**：{len(trades)} 笔  ·  盈利 {wins} 笔  ·  "
                    f"总盈亏: <span style='color:{color}'>¥{total_pnl_all:+,.0f}</span>",
                    unsafe_allow_html=True,
                )


def _generate_suggestion(results: dict, report: dict) -> str:
    """根据回测结果生成优化建议（简易版）"""
    win_rate = results.get("win_rate", 0)
    avg_pnl = results.get("avg_pnl", 0)
    total_signals = results.get("total_signals", 0)
    win_trades = results.get("win_trades", 0)
    loss_trades = results.get("loss_trades", 0)

    parts = [f"**当前策略表现**：胜率 {win_rate}%，平均每笔收益 {avg_pnl}%，共 {total_signals} 笔交易（盈利 {win_trades} / 亏损 {loss_trades}）。"]

    if win_rate < 40:
        parts.append("胜率较低，建议：")
        parts.append("- 加入成交量过滤（成交量 > 5日均量），减少假突破信号")
        parts.append("- 增加买入条件中的均线周期（如 10日/30日），过滤震荡行情")
    elif win_rate < 55:
        parts.append("胜率中等，可以考虑：")
        parts.append("- 加入止损条件（如 -5% 止损），控制单笔亏损")
        parts.append("- 增加趋势过滤（如 60日均线方向），顺势交易")
    else:
        parts.append("胜率不错，可进一步优化：")
        parts.append("- 加入止盈条件（如 +15% 止盈），锁定利润")
        parts.append("- 尝试调整持仓周期，减少持仓天数")

    if avg_pnl < 0:
        parts.append("平均亏损，建议增加更严格的买入过滤条件。")

    if total_signals < 50:
        parts.append("信号数量偏少，可适当放宽买入条件或扩大标的范围。")

    return "\n".join(parts)


# ════════════════════════════════════════════
# 设置页面
# ════════════════════════════════════════════
def show_settings_page():
    st.markdown("## 设置")

    cfg = load_config()
    current_source = cfg.get("data_source", "tushare")

    # ── 数据源选择 ──
    with st.container():
        st.markdown("#### 🔌 数据源")

        source_keys = list(AVAILABLE_SOURCES.keys())
        source_labels = [AVAILABLE_SOURCES[k] for k in source_keys]
        idx = source_keys.index(current_source) if current_source in source_keys else 0

        selected_source = st.selectbox(
            "选择数据源",
            options=source_keys,
            format_func=lambda x: f"{x} — {AVAILABLE_SOURCES[x]}",
            index=idx,
            label_visibility="collapsed",
        )

        token = ""
        api_url = ""
        if selected_source == "tushare":
            st.caption("Tushare Pro 需要注册 https://tushare.pro 获取 Token")
            api_url = st.text_input("API 地址", value=cfg.get("tushare_url", "http://api.tushare.pro"))
            token = st.text_input("Token", value=cfg.get("tushare_token", ""), type="password")
        else:
            st.info(f"「{selected_source}」无需 Token，即开即用")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 保存", use_container_width=True):
                save_source_config(selected_source, token, api_url)
                st.session_state.api = get_source()
                st.success(f"已切换到 {selected_source}")
        with col2:
            if st.button("✅ 验证连接", use_container_width=True):
                cfg2 = load_config()
                old_api = st.session_state.api
                if old_api.name.lower().replace(" ", "") != selected_source:
                    from core.data import create_source
                    old_api = create_source(selected_source)
                ok, msg = old_api.validate()
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ {msg}")

    # ── 数据源说明 ──
    st.markdown("---")
    with st.expander("📖 数据源说明"):
        st.markdown("""
| 数据源 | 是否需要注册 | 频率限制 | 数据范围 | 特点 |
|--------|------------|---------|---------|------|
| **Tushare Pro** | 需要 Token | 免费版 50次/分, 8000次/天 | A股全量 | 专业稳定，收费版无限制 |
| **AkShare** | 无需 | 无硬性限制 | A股 + 多市场 | 开源，数据源丰富 |
| **Baostock** | 无需 | 无硬性限制 | A股 | 需登录，历史悠久 |
| **Ashare** | 无需 | 无硬性限制 | A股实时 | 极简，新浪/腾讯双源自动切换 |
        """)

    st.markdown("---")
    with st.container():
        st.markdown("#### 📦 本地缓存")
        stats = st.session_state.api.get_stats()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("日线记录", stats.get("daily_records", 0))
        c2.metric("覆盖标的", stats.get("stocks", 0))
        c3.metric("存储空间", f"{stats.get('size_mb', 0)} MB")
        c4.metric("最早数据", stats.get("earliest", "--"))

        if st.button("🗑️ 清空缓存", type="secondary"):
            clear_cache()
            st.success("缓存已清空")

    st.markdown("---")
    with st.container():
        st.markdown("#### 📚 策略数据库（RAG）")
        rag_count = count_examples()
        recent = list_examples(limit=5, source="builtin")

        col_a, col_b = st.columns(2)
        col_a.metric("策略模板数", rag_count)

        with st.expander("查看内置策略模板"):
            for ex in recent:
                st.markdown(f"**{ex['name']}** — {ex['description'][:80]}...")
                if st.button(f"📋 复制代码", key=f"copy_{ex['id']}"):
                    st.code(ex["code"], language="python")


if __name__ == "__main__":
    main()
