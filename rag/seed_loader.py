"""种子策略加载 — 将 YAML 示例导入 RAG 库"""
import yaml
from pathlib import Path
from rag.store import init_rag, add_example, count_examples


def load_seed_examples():
    """加载 seed_strategies.yaml 到 RAG 存储"""
    yaml_path = Path(__file__).parent / "examples" / "seed_strategies.yaml"
    if not yaml_path.exists():
        print(f"[RAG] 种子文件不存在: {yaml_path}")
        return

    with open(yaml_path, "r", encoding="utf-8") as f:
        examples = yaml.safe_load(f)

    if not examples:
        print("[RAG] 种子文件为空")
        return

    # 检查是否已导入
    existing = count_examples()
    if existing >= len(examples):
        print(f"[RAG] 种子策略已存在 ({existing} 条)，跳过导入")
        return

    for ex in examples:
        add_example(
            name=ex["name"],
            description=ex["description"].strip(),
            code=ex["code"].strip(),
            tags=ex.get("tags", []),
            source="builtin",
            score=80,
        )

    print(f"[RAG] 导入 {len(examples)} 条种子策略")


if __name__ == "__main__":
    init_rag()
    load_seed_examples()
    print(f"[RAG] 当前策略库共 {count_examples()} 条")
