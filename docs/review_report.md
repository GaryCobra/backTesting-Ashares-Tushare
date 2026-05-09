# 代码走查报告

## 概述
- **项目**: A股回测系统
- **版本**: v5 原型实现
- **审计范围**: core/*.py, strategies/*.py, utils/*.py, rag/*.py, app.py
- **审计日期**: 2026-05-10

---

## 一、严重问题（必须修复）

### 1.1 app.py 仍使用硬编码策略

**文件**: `/home/xuebin/workspace/backTesting/app.py:197`
```python
strat = MaWithVolumeStrategy()  # 应使用 generate_strategy()
```

**问题**: 新写的 `strategies/generator.py` 已实现根据用户描述匹配策略，但 app.py 没有接入，始终使用固定策略。用户无论写什么条件都跑的是均线金叉策略。

**修复**: 改用 `from strategies.generator import generate_strategy; strat = generate_strategy(buy_desc, sell_desc)`

### 1.2 引擎创建策略实例时丢失自定义参数

**文件**: `core/engine.py:74`
```python
strat = strategy.__class__()  # 丢失了用户配置的参数！
```

**问题**: `run()` 方法用 `strategy.__class__()` 创建策略新实例，但这是无参构造，所有自定义参数（如 `MaCrossStrategy(fast=10, slow=30)`）都会丢失，回退到默认值。

**修复**: 需要存储原始策略实例或参数，或改用工厂模式。

### 1.3 缺少 A 股核心规则

**文件**: `core/engine.py`

**问题**: 回测引擎未实现以下 A 股关键规则：
- **T+1**: 当天买入可以当天卖出（错误）
- **涨跌停**: 涨停无法买入，跌停无法卖出
- **交易费用**: 未计算佣金（~0.025%）和印花税（0.1%）

这些规则缺失会导致回测结果严重偏离实际。

---

## 二、中等问题（建议修复）

### 2.1 异常静默吞噬

**文件**: `core/engine.py:86-90`
```python
try:
    buy_signal = strat.buy_condition(i)
    sell_signal = strat.sell_condition(i)
except Exception:
    continue
```

**问题**: 策略中的任何异常都被静默吞噬并跳过该 K 线，调试困难。且 `except Exception` 包含 `KeyboardInterrupt` 等系统异常。

**修复**: 捕获具体异常，并记录日志。

### 2.2 `self.all_trades` 未使用

**文件**: `core/engine.py:50`
```python
self.all_trades: list[Trade] = []
```

**问题**: 定义了属性但从未使用。

### 2.3 FTS5 中文分词效果差

**文件**: `rag/retriever.py`

**问题**: `_build_fts_query` 将中文逐字拆分为 OR 查询，导致"均线"匹配到"均"或"线"的无关结果，噪声大。RAG 检索效果差会直接影响策略匹配准确性。

### 2.4 标的解析不准确

**文件**: `app.py:44-65`

**问题**: `resolve_stock_codes` 用 `api.get_stock_basic().head(N)` 取前 N 只股票，这根本不是对应指数的成分股。例如"沪深300"取的是数据库前 300 只股票，而非真正的沪深 300 成分股。

---

## 三、轻微问题（建议优化）

### 3.1 save_daily 使用 method="multi" 有兼容性风险

**文件**: `core/cache.py:97`

**问题**: `to_sql(..., method="multi")` 在某些 SQLite/Pandas 版本组合下可能失败。建议用默认逐行插入或批量 INSERT。

### 3.2 cache_stats 异常处理不完备

**文件**: `core/cache.py:154`

**问题**: 异常捕获后返回的 dict 缺少部分字段，设置页面显示可能不完整。

### 3.3 import json 未使用

**文件**: `app.py:9`

**问题**: `import json` 未被使用。

### 3.4 tushare token 全局副作用

**文件**: `core/data.py:30`

**问题**: `ts.set_token(token)` 是全局调用。如果切换 token 或使用多个实例，会有全局状态污染。

### 3.5 RAG seed_loader 计数逻辑偏差

**文件**: `rag/seed_loader.py:27`

**问题**: 判断条件 `existing >= len(examples)` 未考虑增量添加场景。如果新种子策略文件增加了新示例，而 `existing` 已达旧数量，会跳过导入。

---
**报告结束**
