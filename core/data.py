"""数据接口层 — 工厂 + 向后兼容

用法:
    from core.data import create_source, get_source
    source = get_source()  # 从配置读取当前选中数据源
"""
from core.data_source import create_source, AVAILABLE_SOURCES
from utils.config import load_config


def get_source():
    """从配置读取当前数据源并创建"""
    cfg = load_config()
    source_type = cfg.get("data_source", "tushare")
    return create_source(source_type)


def get_source_config() -> dict:
    """获取当前数据源配置供 UI 使用"""
    cfg = load_config()
    return {
        "data_source": cfg.get("data_source", "tushare"),
        "tushare_token": cfg.get("tushare_token", ""),
        "tushare_url": cfg.get("tushare_url", "http://api.tushare.pro"),
    }


def save_source_config(data_source: str, tushare_token: str = "", tushare_url: str = ""):
    """保存数据源配置"""
    from utils.config import save_config
    cfg = load_config()
    cfg["data_source"] = data_source
    cfg["tushare_token"] = tushare_token
    cfg["tushare_url"] = tushare_url or "http://api.tushare.pro"
    save_config(cfg)
