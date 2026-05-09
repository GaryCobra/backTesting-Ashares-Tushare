"""配置管理 — 数据源 Token/URL/选择 持久化"""
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".backtest"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "data_source": "tushare",
    "tushare_token": "",
    "tushare_url": "http://api.tushare.pro",
    "tokens": [],
}


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    _ensure_dir()
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    with open(CONFIG_FILE, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)


def get_token() -> str:
    return load_config().get("tushare_token", "")


def get_api_url() -> str:
    return load_config().get("tushare_url", "http://api.tushare.pro")
