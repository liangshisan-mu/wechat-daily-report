"""配置加载：所有本机相关的东西都放 config.json，仓库里只留 example。"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(os.environ.get("WXDR_CONFIG", str(ROOT / "config.json")))


def load() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(
            f"缺少配置文件：{CONFIG_PATH}\n"
            "先复制 config.example.json 为 config.json，或运行：python run.py init"
        )
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


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
