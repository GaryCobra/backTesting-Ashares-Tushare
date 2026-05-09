# rag/ — AGENTS.md

## 职责

策略示例的存储与检索（RAG 层）。用户的历史策略、内置模板都存于此。

## 文件职责

| 文件 | 职责 |
|------|------|
| `store.py` | SQLite CRUD: strategy_examples 表 + FTS5 全文索引 + 自动触发器 |
| `retriever.py` | FTS5 全文搜索, 自然语言查询→相似策略, LIKE 降级 |
| `seed_loader.py` | 从 YAML 加载种子策略到 RAG 库 |
| `examples/seed_strategies.yaml` | 8 个内置策略模板 |

## 存储结构

表 `strategy_examples`:
- id, name, description, code, tags (JSON), source (builtin/user/ai), score (0-100)

虚拟表 `strategy_examples_fts` (FTS5):
- 自动同步: INSERT/UPDATE/DELETE 触发器维护索引
- tokenizer: unicode61 (支持中文)

## 检索逻辑

```
search_examples(query, top_k=5)
  → FTS5 MATCH 查询
  → 失败降级 LIKE '%keyword%'
  → 返回按 rank 排序的结果
```

## 注意事项

- FTS5 中文分词使用 unicode61, 中文会按单字索引（效果有限）
- seed_loader.count_examples() 判断是否已导入, 跳过已存在的策略
- 种子文件修改后需手动清空表再重新导入
