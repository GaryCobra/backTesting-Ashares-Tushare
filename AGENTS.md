# A股回测系统 — AGENTS.md

## 项目定位

自然语言驱动的 A 股量化回测系统。用户用中文描述买卖条件，系统自动生成策略代码、扫描全市场信号、生成回测报告。

## 技术栈

- **前端**: Streamlit (单一 Python 文件 app.py, 无 JS 框架)
- **后端**: Python 3.14+, Pandas, NumPy
- **数据源**: 支持 4 种 — Tushare Pro / AkShare / Baostock / Ashare
- **缓存**: SQLite (两层: 数据缓存 backtest_cache.db + RAG 策略库 rag_cache.db)
- **可视化**: Streamlit 原生组件 + st.dataframe

## 目录职责

| 目录 | 职责 | 复杂度 |
|------|------|--------|
| `core/` | 回测引擎核心: 多数据源抽象层、信号扫描、策略基类、技术指标、SQLite缓存 | 高 |
| `core/sources/` | 4 种数据源实现（Tushare/AkShare/Baostock/Ashare） | 中 |
| `strategies/` | 策略实现: 内置策略类、策略生成器（RAG+关键词→策略实例） | 中 |
| `rag/` | RAG 策略库 + 回测报告持久化 | 中 |
| `utils/` | 工具: 配置管理（数据源选择/Token/URL 持久化） | 低 |
| `docs/` | 设计文档、原型、走查报告 | 低 |
| `data/` | 运行时数据存储目录（gitignore 内的缓存数据库） | 低 |

## 关键架构决策

### 1. 信号驱动，拒绝组合
每只股票独立扫描信号，互不干扰。不涉及投资组合管理、仓位分配、净值曲线。

### 2. 自然语言优先
标的范围、K线周期、总资金、每笔股数全部在文字描述中。UI 只保留起止日期。

### 3. AI 策略匹配
- 关键词匹配 → 参数提取 → 策略实例化
- 兜底用 RAG FTS5 检索
- 见 `strategies/generator.py`

### 4. A 股规则内置
- T+1 （同一股票当天买入不能当天卖出）
- 佣金万分之二点五（最低5元）
- 印花税千分之一（卖出收取）
- 见 `core/engine.py:Trade.close()`

### 5. 两层缓存
- `backtest_cache.db` — Tushare 原始数据缓存（日线、股票列表）
- `rag_cache.db` — 策略示例 + FTS5 全文索引

## Python 3.14 注意事项

- `connection.lastrowid` 已移除, 使用 `cursor.lastrowid`
- `except Exception` 会捕获 `KeyboardInterrupt`, 优先捕获具体异常
- `pip` 不在环境变量 PATH, 使用 `$HOME/.local/bin/pip`

## 编码约定

- 所有文件名、变量名、函数名: `snake_case`
- 策略类名: `PascalCase`, 继承 `core.strategy.Strategy`
- 导入顺序: 标准库 → 第三方 → 本地模块
- 类型提示: 函数参数必须标注类型
- 错误处理: 捕获具体异常, 不写 `except: pass`

## 禁止行为

- 不要在策略中调用外部 API（策略运行在扫描循环内）
- 不要给 core/engine.py 加组合/持仓管理逻辑
- 不要给 UI 加约束条件 chips 或筛选器 — 全走文字描述
- 不要使用 `@ts-ignore`, `as any`, `# type: ignore`（本 Python 项目）
- 不要在回测结果中显示 K 线图（当前设计决策）

## 测试

(当前项目无测试框架, 如需添加优先用 pytest)
