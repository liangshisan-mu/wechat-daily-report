"""从快照的联系人库里取头像地址并下载。

头像地址来自 contact 表的 small_head_url / big_head_url，是微信公开 CDN 链接；
这里只做“按 username 精确取”，不做人脸识别、不猜人。
"""

from __future__ import annotations

import sqlite3
import urllib.request
from pathlib import Path

from . import config


def _contact_db() -> Path:
    return config.snapshot_root() / "latest.json"


def _snapshot() -> Path:
    import json

    latest = config.snapshot_root() / "latest.json"
    if not latest.exists():
        raise RuntimeError("还没有可用快照，先运行：python run.py refresh")
    return Path(json.loads(latest.read_text(encoding="utf-8"))["snapshot"])


def head_url(username: str) -> str | None:
    snap = _snapshot()
    db = snap / "contact" / "contact.db"
    if not db.exists():
        return None
    con = sqlite3.connect("file:" + str(db).replace("\\", "/") + "?mode=ro", uri=True)
    try:
        row = con.execute(
            "SELECT small_head_url, big_head_url FROM contact WHERE username=?",
            (username,),
        ).fetchone()
    finally:
        con.close()
    if not row:
        return None
    return row[0] or row[1] or None


def download_avatar(username: str, out_dir: Path, filename: str | None = None) -> Path | None:
    url = head_url(username)
    if not url:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / (filename or f"{username}.jpg")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        out.write_bytes(resp.read())
    return out
