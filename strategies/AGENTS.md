# strategies/ — AGENTS.md

## 职责

策略实现和生成。提供内置策略类 + 根据用户自然语言描述自动匹配策略。

## 文件职责

| 文件 | 职责 |
|------|------|
| `builtin.py` | 内置策略类: MaCross, MaWithVolume, Macd, Rsi, Bollinger, BreakMa, Consecutive |
| `generator.py` | 策略生成器: 关键词匹配+参数提取 → 策略实例, RAG 检索兜底 |

## 策略生成流程

```
用户描述 → generator.generate_strategy(buy_desc, sell_desc)
           ↓
        1. 关键词匹配 (PATTERN_MAP)
        2. 参数提取 (正则, 如 "5日"→fast=5)
        3. 实例化策略类
        4. RAG 检索兜底 (关键词未命中时)
```

## 添加新策略的步骤

1. 在 `builtin.py` 添加新类, 继承 `core.strategy.Strategy`
2. 实现 `init()`, `buy_condition(i)`, `sell_condition(i)`
3. 在 `generator.py` 的 PATTERN_MAP 添加映射规则
4. 在 `rag/examples/seed_strategies.yaml` 添加示例

## 策略类命名约定

- 类名 `PascalCase`, 描述买卖逻辑
- `name` 属性设置中文名（用于界面显示）
- `__init__` 只接收参数, 不访问数据
- `init()` 访问 `self.data` 初始化指标

## 约束

- 策略方法内不能调外部 API
- buy_condition/sell_condition 是纯计算函数, 不能有副作用
- 同一策略实例会被多只股票复用（每次 init() 重新初始化）
