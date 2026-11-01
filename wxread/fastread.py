"""只读快照的快速取数层。

vault_cli 为了保证“最新 N 条”的严格语义，会整表解码后取堆顶，单会话 4~5 秒。
这里改成用 create_time 索引倒序取，单会话约 0.03 秒；解密、字段映射、正文格式化
仍然复用 skill 内的同一套函数，不重复实现解码。

注意：同一会话的消息可能被分片到多个 message_N.db，取数时必须合并后再排序。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import config

_scripts = config.skill_scripts()
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

try:
    import snapshot_reader as sr  # noqa: E402
except Exception:  # 初始化阶段 vendor 可能还没拉下来
    sr = None

LATEST = config.snapshot_root() / "latest.json"

_state: dict = {"snap": None, "contacts": None, "index": None, "account": None, "by_id": None}
_sender_cache: dict[str, dict[int, str]] = {}


def _sender_map(con, db: Path) -> dict[int, str]:
    key = str(db)
    if key not in _sender_cache:
        _sender_cache[key] = sr.sender_map(con)
    return _sender_cache[key]


def snapshot() -> Path:
    if not LATEST.exists():
        raise RuntimeError("还没有可用快照，先运行：python run.py refresh")
    return Path(json.loads(LATEST.read_text(encoding="utf-8"))["snapshot"])


def _ensure() -> Path:
    if sr is None:
        raise RuntimeError(
            "找不到 snapshot_reader。先运行 setup.ps1，或把 config.json 的 skill_dir 指到 yichen-wechat-local-vault。"
        )
    snap = snapshot()
    key = str(snap)
    if _state["snap"] != key:
        _state.update(
            snap=key,
            contacts=sr.contact_records(snap),
            index=None,
            account=sr.load_account_identity(snap),
            by_id=None,
        )
    return snap


def contacts() -> dict:
    _ensure()
    return _state["contacts"]


def table_index() -> dict[str, list[Path]]:
    """表名 -> 所在分片库。正常一个会话只在一处，保留列表以防分片。"""
    snap = _ensure()
    if _state["index"] is None:
        index: dict[str, list[Path]] = {}
        for db in sr.message_databases(snap):
            with sr.connect_read_only(db) as con:
                for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                    name = row[0]
                    if name.startswith("Msg_"):
                        index.setdefault(name, []).append(db)
        _state["index"] = index
    return _state["index"]


def resolve(chat_id: str) -> tuple[str, dict]:
    _ensure()
    if _state.get("by_id") is None:
        _state["by_id"] = {c.get("chat_id"): (u, c) for u, c in _state["contacts"].items()}
    hit = _state["by_id"].get(chat_id)
    if not hit:
        raise ValueError(f"chat_id 未唯一命中：{chat_id}")
    return hit


def chats_with_messages() -> list[dict]:
    """只返回本地确实存在消息表的会话，跳过几万个纯联系人。"""
    idx = table_index()
    return [c for u, c in contacts().items() if sr.message_table(u) in idx]


def _content(row, budget=None) -> str:
    text = sr.decode(row["content"], row["compression_flag"], budget)
    if not text:
        text = sr.decode(row["compressed"], row["compression_flag"], budget)
    return text


def fetch(
    chat_id: str,
    *,
    start: int | None = None,
    end: int | None = None,
    limit: int = 50,
    keyword: str | None = None,
    max_scan: int = 200_000,
) -> tuple[dict, list[dict]]:
    """按时间倒序取消息，命中 limit 即停。返回 (会话信息, 正序消息列表)。"""
    _ensure()
    username, chat = resolve(chat_id)
    table = sr.message_table(username)
    dbs = table_index().get(table)
    if not dbs:
        return chat, []

    account = _state["account"]
    cs_all = contacts()
    seen: set = set()
    results: list[dict] = []
    per_db: dict[Path, int] = {}

    for db in dbs:
        taken = 0
        with sr.connect_read_only(db) as con:
            mapping = sr.table_mapping(con, table)
            if not sr._compatible_message_mapping(mapping):
                raise RuntimeError(f"{db.name}:{table} 消息表结构不兼容")
            cols = ["rowid AS _rowid"]
            for key in ("local_type", "create_time", "sender_id", "content", "compressed", "compression_flag"):
                cols.append(f"[{mapping[key]}] AS [{key}]" if mapping[key] else f"NULL AS [{key}]")
            where, params = [], []
            if end is not None:
                where.append(f"[{mapping['create_time']}] <= ?")
                params.append(end)
            if start is not None:
                where.append(f"[{mapping['create_time']}] >= ?")
                params.append(start)
            sql = f"SELECT {','.join(cols)} FROM [{table}]"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += f" ORDER BY [{mapping['create_time']}] DESC"

            names = _sender_map(con, db)
            for row in con.execute(sql, params):
                if len(seen) >= max_scan:
                    break
                text = _content(row)
                sender_username = names.get(int(row["sender_id"]), "") if row["sender_id"] is not None else ""
                if not sender_username and ":\n" in text:
                    possible, rest = text.split(":\n", 1)
                    if possible.startswith("wxid_"):
                        sender_username, text = possible, rest
                body = sr.format_message_content(row["local_type"], text)
                if keyword and keyword.casefold() not in body.casefold():
                    continue
                timestamp = int(row["create_time"] or 0)
                direction = "unknown"
                if account and sender_username:
                    direction = "outgoing" if sender_username == account else "incoming"
                sender = cs_all.get(sender_username, {}).get("display_name") or ("我" if direction == "outgoing" else "未知成员")
                uid = (str(timestamp), db.name, row["_rowid"])
                if uid in seen:
                    continue
                seen.add(uid)
                results.append(
                    {
                        "time": sr._format_timestamp(timestamp),
                        "timestamp": timestamp,
                        "type": int(row["local_type"] or 0) & 0xFFFFFFFF,
                        "sender": sender,
                        "direction": direction,
                        "content": body,
                        "sender_username": sender_username,
                    }
                )
                taken += 1
                if taken >= limit:
                    break
        per_db[db] = taken

    # 分片必须合并后再取最新，否则会拿到旧库里的历史消息
    results.sort(key=lambda m: m["timestamp"], reverse=True)
    results = results[:limit]
    results.sort(key=lambda m: m["timestamp"])
    return chat, results


def parse_date(value: str | None, end: bool = False) -> int | None:
    return sr.parse_date(value, end)


def sender_stats(chat_id: str, start: int, end: int) -> list[dict]:
    """统计区间内每个发送者的消息数，附带 username（用于取头像）。"""
    _ensure()
    username, chat = resolve(chat_id)
    table = sr.message_table(username)
    dbs = table_index().get(table)
    if not dbs:
        return []
    total: dict[str, dict] = {}
    cs_all = contacts()
    for db in dbs:
        with sr.connect_read_only(db) as con:
            mapping = sr.table_mapping(con, table)
            if not sr._compatible_message_mapping(mapping):
                continue
            names = _sender_map(con, db)
            sql = (
                f"SELECT [{mapping['sender_id']}] AS sid, COUNT(*) AS c FROM [{table}] "
                f"WHERE [{mapping['create_time']}] >= ? AND [{mapping['create_time']}] < ? "
                f"GROUP BY [{mapping['sender_id']}]"
            )
            for sid, c in con.execute(sql, (start, end)):
                u = names.get(int(sid), "") if sid is not None else ""
                key = u or f"unknown:{sid}"
                row = total.setdefault(key, {"username": u, "count": 0})
                row["count"] += int(c)
    out = []
    for key, row in total.items():
        u = row["username"]
        name = cs_all.get(u, {}).get("display_name") or ("未知成员" if not u else u)
        out.append({"username": u, "name": name, "count": row["count"]})
    out.sort(key=lambda x: x["count"], reverse=True)
    return out
