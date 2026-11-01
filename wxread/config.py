"""配置加载：所有本机相关的东西都放 config.json，仓库里只留 example。"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("WXDR_CONFIG", str(ROOT / "config.json")))


DEFAULTS = {
    "python": "",
    "skill_dir": "vendor/yichen-wechat-local-vault",
    "source_id": "",
    "db_root": "",
    "snapshot_dir": "",
    "export_dir": "exports",
    "llm": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "model": "deepseek-chat",
    },
}


def load() -> dict:
    """容错加载：init 之前也能 import 本包。"""
    if not CONFIG_PATH.exists():
        return json.loads(json.dumps(DEFAULTS))
    cfg = json.loads(json.dumps(DEFAULTS))
    cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    return cfg


def require() -> dict:
    """需要真实配置的命令用这个。"""
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"缺少配置文件：{CONFIG_PATH}\n"
            "先运行：python run.py init"
        )
    return load()


def save(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass


def snapshot_root() -> Path:
    """快照根目录。默认按 yichen-wechat-local-vault 的约定放在 LOCALAPPDATA。"""
    cfg = load()
    custom = cfg.get("snapshot_dir")
    if custom:
        return Path(custom).expanduser()
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "YichenWeChatVault" / "windows-live"


def skill_scripts() -> Path:
    """第三方采集 skill 的 scripts 目录。"""
    cfg = load()
    p = Path(cfg.get("skill_dir", "vendor/yichen-wechat-local-vault")).expanduser()
    if not p.is_absolute():
        p = ROOT / p
    return p / "scripts"


def python_exe() -> str:
    """采集 CLI 用的 Python。默认当前解释器。"""
    return load().get("python") or os.environ.get("WXDR_PYTHON", "python")
