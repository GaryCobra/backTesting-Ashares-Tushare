# A股回测系统

自然语言驱动的 A 股量化回测系统。输入买卖条件，自动生成策略代码，扫描全市场信号。

GitHub: https://github.com/GaryCobra/backTesting-Ashares-Tushare

## 目录结构

```
backTesting/
├── app.py                  # Streamlit 主入口（策略/结果/设置三页）
├── README.md               # 本文件
├── AGENTS.md               # AI 开发指引（架构/约定/约束）
├── core/                   # 核心回测引擎 ⭐
│   ├── data_source.py      # 数据源抽象基类 + 工厂（支持切换）
│   ├── data.py             # 快捷接口 get_source() / save_source_config()
│   ├── sources/            # 多数据源实现
│   │   ├── tushare_source.py   # Tushare Pro（需 Token）
│   │   ├── akshare_source.py   # AkShare（开源免费）
│   │   ├── baostock_source.py  # Baostock（免费）
│   │   ├── ashare_source.py    # Ashare（新浪/腾讯双源）
│   │   └── Ashare.py           # mpquant/Ashare 库（MIT）
│   ├── engine.py           # 信号扫描引擎（T+1/佣金/印花税 已内置）
│   ├── strategy.py         # 策略基类（buy_condition / sell_condition）
│   ├── indicators.py       # 技术指标（SMA, EMA, MACD, RSI, Bollinger, ATR）
│   ├── cache.py            # SQLite 本地缓存层（WAL 模式）
│   └── metrics.py          # 绩效指标（预留）
├── strategies/             # 策略实现
│   ├── builtin.py          # 7 个内置策略（均线/MACD/RSI/布林/放量突破/连涨跌）
│   ├── generator.py        # 策略生成器（关键词→参数提取→策略实例）
│   └── AGENTS.md
├── rag/                    # RAG 策略数据库 + 报告持久化
│   ├── store.py            # SQLite + FTS5 策略存储
│   ├── retriever.py        # 自然语言检索相似策略
│   ├── seed_loader.py      # 种子策略加载
│   ├── report_store.py     # 回测报告 SQLite 持久化
│   ├── examples/           # 8 个内置策略模板
│   └── AGENTS.md
├── utils/                  # 工具
│   └── config.py           # 数据源选择 / Token / URL 配置持久化
├── data/                   # 运行时数据存储（gitignore）
├── docs/                   # 设计文档
│   ├── prototypes/v5.html  # v5 原型
│   └── review_report.md    # 代码走查报告
└── AGENTS.md               # 各子模块 AI 知识库
```

## 设计理念

- **信号驱动**：每只股票独立计算买卖信号，互不干扰
- **拒绝组合**：不涉及投资组合管理、仓位分配，只有条件 → 信号 → 交易
- **自然语言优先**：标的范围、K线周期、总资金、每笔股数全部写进文字描述
- **A 股规则内置**：T+1、佣金万分之二点五（最低5元）、印花税千分之一
- **多数据源支持**：Tushare Pro / AkShare / Baostock / Ashare 自由切换
- **双层缓存**：数据缓存（backtest_cache.db）+ RAG 策略库（rag_cache.db）

## 使用方式

```bash
cd backTesting
streamlit run app.py --server.port 8899
```

1. **策略页面** — 输入买卖条件（含标的、资金、股数、周期） + 起止日期 → 运行回测
2. **结果页面** — 概览统计 → AI 优化建议 → 可展开的逐股交易明细 → 保存/加载/删除历史报告
3. **设置页面** — 选择数据源、配置 Token、查看缓存、内置策略模板

### 描述示例

```
📈 买入：中证500日线级别，总资金10万元，5日均线上穿20日均线时买入100股
📉 卖出：5日均线下穿20日均线时卖出全部持仓，或亏损超5%止损
```

## 策略匹配流程

```
用户文字描述 → generator.py 关键词匹配 + 参数提取
               → 7 个内置策略中选择最佳匹配
               → RAG 检索兜底
               → 策略实例化 → SignalEngine.run()
```

## 数据源

| 数据源 | 注册 | 频率 | 特点 |
|--------|------|------|------|
| **Tushare Pro** | 需 Token tushare.pro | 免费 50次/分 | 专业稳定，付费无限制 |
| **AkShare** | 无需 | 无硬性限制 | 开源，多市场丰富 |
| **Baostock** | 无需 | 无硬性限制 | 经典可靠 |
| **Ashare** | 无需 | 无硬性限制 | 新浪/腾讯双源自动切换 |

所有数据源统一缓存到本地 SQLite，切换后已有缓存数据仍然可用。

## 依赖安装

```bash
pip install --break-system-packages streamlit pandas plotly tushare numpy pyyaml akshare baostock
```
