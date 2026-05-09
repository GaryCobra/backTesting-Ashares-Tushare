# core/ — AGENTS.md

## 职责

回测引擎核心模块。数据获取（多源）、缓存、技术指标计算、策略扫描、信号配对。

## 模块关系

```
            ┌──────────────────┐
            │  data_source.py   │ ← 抽象基类 + 工厂
            │  (DataSource ABC) │
            └──────┬───────────┘
                   │ create_source()
          ┌────────┼────────┬────────┐
          ▼        ▼        ▼        ▼
   tushare_source  akshare  baostock ashare
          │        │        │        │
          └────────┴────────┴────────┘
                   │
          ┌────────▼────────┐
          │    cache.py     │ ← SQLite 缓存（统一格式）
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │    engine.py    │ ← SignalEngine + Trade
          │  strategy.py    │ ← Strategy ABC
          │  indicators.py  │ ← 技术指标
          └─────────────────┘
```

## 文件职责

| 文件 | 职责 |
|------|------|
| `data_source.py` | DataSource 抽象基类 + `create_source()` 工厂 + `AVAILABLE_SOURCES` 列表 |
| `data.py` | 上层快捷接口 `get_source()` / `get_source_config()` / `save_source_config()` |
| `sources/__init__.py` | 空 |
| `sources/tushare_source.py` | Tushare Pro 数据源（免费版 50次/分，需 Token） |
| `sources/akshare_source.py` | AkShare 数据源（开源免费，无需注册） |
| `sources/baostock_source.py` | Baostock 数据源（需联网登录） |
| `sources/ashare_source.py` | Ashare 数据源（新浪/腾讯双核心，极简） |
| `sources/Ashare.py` | mpquant/Ashare 单文件库（MIT License） |
| `engine.py` | 信号扫描引擎, 逐股票买卖信号扫描, Trade/Signal 数据类, A股费率计算 |
| `strategy.py` | 策略基类 ABC, 子类实现 buy_condition(i)/sell_condition(i) |
| `indicators.py` | 纯函数: SMA/EMA/MACD/RSI/Bollinger/ATR/cross_over/cross_under |
| `cache.py` | SQLite 缓存层: 日线/股票列表/指数成分, WAL 模式, 通用格式 |
| `metrics.py` | 绩效指标（预留） |

## DataSource 接口

```python
class DataSource(ABC):
    name: str              # 显示名称
    validate() -> (bool, str)
    get_stock_basic() -> DataFrame  # ts_code,symbol,name,area,industry,market,list_date
    get_daily(code, start, end) -> DataFrame  # ts_code,trade_date,open,high,low,close,volume,amount
    get_stats() -> dict
```

所有数据源的 `get_daily()` 返回统一列格式，经 `cache.py` 统一缓存。

## 关键约束

- **engine.run() 不接收 dates 参数**（已移除）, 只接收 stock_data dict
- **Trade.close() 内置费率计算**: 佣金 0.025%(最低5元)+印花税0.1%(卖出)
- **T+1 规则**: 在 engine.py 循环内通过 buy_date 比较实现
- 策略实例按股票复用时: `strat.__class__()` 无参重建, 参数通过 init() 设置

## 变更注意事项

- 添加新数据源 → 在 `data_source.py` 的 `create_source()` 和 `AVAILABLE_SOURCES` 注册
- engine.py 的 Signal 和 Trade 是数据类, 修改字段需同步 app.py 报告页面
- cache.py 的 DB_PATH 使用 `data/backtest_cache.db`, 所有数据源共享同一缓存
- Ashare.py 文件从 https://github.com/mpquant/Ashare 下载，MIT 许可

## Python 3.14 兼容

- 不用 `connection.lastrowid`, 用 `cursor.lastrowid`
- 不用 `except Exception` 兜底（会吞 KeyboardInterrupt）
