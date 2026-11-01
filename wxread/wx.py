"""微信本地资料库 · 命令行入口

在 yichen-wechat-local-vault 之上加一层：按会话名直接查，不用记 chat_id。
所有数据只读自本机快照，不上传、不写回微信。

用法:
    python -m wxread.wx refresh            采集最新聊天快照（需微信正在运行）
    python -m wxread.wx refresh --all      全库采集（含收藏、朋友圈、媒体库，较慢）
    python -m wxread.wx chats [关键词]     列出会话
    python -m wxread.wx read "群名" [--start 2026-09-01] [--limit 100]
    python -m wxread.wx search "关键词" [--chat "群名"] [--start ...] [--end ...]
    python -m wxread.wx export "群名" [--out 路径.md] [--start ...] [--end ...]
    python -m wxread.wx status             查看当前快照
    python -m wxread.wx clean --keep 3     清理旧快照（默认只列出，加 --yes 才删）
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import config, fastread

ROOT = config.ROOT
CLI = config.skill_scripts() / "vault_cli.py"
LATEST = config.snapshot_root() / "latest.json"
SNAPSHOT_ROOT = LATEST.parent / "snapshots"


def _cfg() -> dict:
    return config.require()


def _die(msg: str, code: int = 1):
    print(f"[x] {msg}", file=sys.stderr)
    raise SystemExit(code)


def run_cli(*args: str, timeout: int = 900) -> dict:
    if not CLI.exists():
        _die(f"找不到 vault_cli.py：{CLI}。先运行 python run.py init，或把 config.skill_dir 指向 yichen-wechat-local-vault。")
    cfg = _cfg()
    proc = subprocess.run(
        [config.python_exe(), str(CLI), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        detail = (out + "\n" + (proc.stderr or "")).strip()
        _die(detail[-2000:] or f"命令失败（exit {proc.returncode}）")
    start = out.find("{")
    if start < 0:
        _die(f"返回内容不是 JSON：{out[:500]}")
    try:
        return json.loads(out[start:])
    except json.JSONDecodeError as exc:
        _die(f"解析返回失败：{exc}")


def current_snapshot() -> str:
    if not LATEST.exists():
        _die("还没有可用快照。先运行：python run.py refresh")
    data = json.loads(LATEST.read_text(encoding="utf-8"))
    snap = data.get("snapshot")
    if not snap or not Path(snap).exists():
        _die("最新快照指针已失效，请重新运行：python run.py refresh")
    return snap


def _cache_file() -> Path:
    snap = current_snapshot()
    return ROOT / ".cache" / f"chats-{Path(snap).name[:12]}.json"


def list_chats(force: bool = False) -> list[dict]:
    """会话表可能上万行，按快照缓存，避免每次查询都重扫。"""
    cache = _cache_file()
    if not force and cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass
    chats = run_cli("snapshot", "--snapshot", current_snapshot(), "chats").get("chats", [])
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(chats, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return chats


def resolve_chat(name: str) -> dict:
    chats = list_chats()
    if not chats:
        _die("快照里没有会话，可能采集范围不对。")

    if re.fullmatch(r"[0-9a-fA-F]{16,}", name):
        hit = next((c for c in chats if c.get("chat_id") == name), None)
        if hit:
            return hit
        return {"chat_id": name, "display_name": name, "kind": "unknown"}

    exact = [c for c in chats if c.get("display_name") == name]
    if len(exact) == 1:
        return exact[0]

    partial = [c for c in chats if name in (c.get("display_name") or "")]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        near = [c for c in chats if any(tok and tok in (c.get("display_name") or "") for tok in re.split(r"[\s,，]+", name) if tok)]
        if len(near) == 1:
            return near[0]
        partial = near
    if not partial:
        _die(f"没找到会话：{name}。用 python run.py chats 关键词 看看有哪些。")

    print(f"“{name}”匹配到 {len(partial)} 个会话，请写得更具体：", file=sys.stderr)
    for c in partial[:30]:
        print(f"  {c.get('display_name')}  [{c.get('kind')}]  {c.get('chat_id')}", file=sys.stderr)
    raise SystemExit(2)


def one_line(text: str, limit: int = 400) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    # 群消息正文常带 "wxid_xxx:" 或脱敏后的标识前缀，去掉更易读
    s = re.sub(r"^(?:\[内部标识已隐藏\]|wxid_[A-Za-z0-9_\-]{4,}):\s*", "", s)
    return s if len(s) <= limit else s[:limit] + " …"


def fmt_message(m: dict, show_sender: bool = True) -> str:
    t = m.get("time") or ""
    sender = m.get("sender") or ""
    direction = m.get("direction")
    who = sender
    if direction == "outgoing":
        who = f"{sender}(我)" if sender else "我"
    body = one_line(m.get("content"))
    return f"{t}  {who}：{body}" if show_sender and who else f"{t}  {body}"


def time_args(args) -> list[str]:
    out = []
    if getattr(args, "start", None):
        out += ["--start", args.start]
    if getattr(args, "end", None):
        out += ["--end", args.end]
    return out


# ---------------------------------------------------------------- commands


def cmd_refresh(args):
    cfg = _cfg()
    if not cfg.get("source_id") or not cfg.get("db_root"):
        _die("config.json 里缺少 source_id / db_root。先运行：python run.py init")
    argv = ["windows", "capture", "--source-id", cfg["source_id"], "--db-root", cfg["db_root"]]
    if args.all:
        argv += ["--scope", "all"]
    if args.seconds:
        argv += ["--seconds", str(args.seconds)]
    print("正在从本机微信采集快照（只读，不碰微信界面）…", file=sys.stderr)
    data = run_cli(*argv)

    flag = {"complete": "完成", "complete_with_index_gaps": "完成（搜索索引校验有缺口）"}.get(data.get("status"), data.get("status"))
    print(f"状态：{flag}")
    print(f"快照：{data.get('snapshot')}")
    print(f"库数：{data.get('databases')}   认证页：{data.get('authenticated_pages')}   校验：{data.get('validation')}")
    gaps = data.get("integrity_gaps") or []
    if gaps:
        print(f"完整性缺口：{json.dumps(gaps, ensure_ascii=False)}")
    if data.get("validation") != "passed":
        print("[!] 校验未通过，不要把它当最新结果使用。", file=sys.stderr)
    _print_disk_usage()


def cmd_chats(args):
    chats = list_chats()
    kw = (args.keyword or "").strip()
    rows = [c for c in chats if not kw or kw in (c.get("display_name") or "")]
    if args.group:
        rows = [c for c in rows if c.get("kind") == "group"]
    kinds = {"contact": "私聊", "group": "群聊"}
    print(f"共 {len(rows)} 个会话" + (f"（关键词：{kw}）" if kw else ""))
    shown = rows if args.all else rows[: args.limit]
    for c in shown:
        print(f"  {c.get('display_name')}\t[{kinds.get(c.get('kind'), c.get('kind'))}]\t{c.get('chat_id')}")
    if len(rows) > len(shown):
        print(f"  …还有 {len(rows) - len(shown)} 个，加 --all 显示全部，或用关键词过滤")


def cmd_read(args):
    chat = resolve_chat(args.name)
    _, msgs = fastread.fetch(
        chat["chat_id"],
        start=fastread.parse_date(args.start),
        end=fastread.parse_date(args.end, end=True),
        limit=args.limit,
    )
    print(f"# {chat.get('display_name')}  （{len(msgs)} 条，最新在后）\n")
    for m in msgs:
        print(fmt_message(m))


def cmd_search(args):
    start = fastread.parse_date(args.start)
    end = fastread.parse_date(args.end, end=True)

    if args.chat:
        chat = resolve_chat(args.chat)
        _, msgs = fastread.fetch(chat["chat_id"], start=start, end=end, limit=args.limit, keyword=args.keyword)
        print(f"# 「{args.keyword}」在 {chat.get('display_name')}：{len(msgs)} 条\n")
        for m in msgs:
            print(fmt_message(m))
        return

    targets = fastread.chats_with_messages()
    print(f"正在全库搜索「{args.keyword}」，{len(targets)} 个有聊天记录的会话…", file=sys.stderr)
    total = 0
    for i, chat in enumerate(targets, 1):
        if i % 200 == 0:
            print(f"  …{i}/{len(targets)}", file=sys.stderr)
        try:
            _, msgs = fastread.fetch(chat["chat_id"], start=start, end=end, limit=args.limit, keyword=args.keyword)
        except Exception:
            continue
        if msgs:
            print(f"\n## {chat.get('display_name')}")
            for m in msgs:
                print(fmt_message(m))
            total += len(msgs)
    print(f"\n# 合计命中 {total} 条")


def cmd_export(args):
    chat = resolve_chat(args.name)
    start = fastread.parse_date(args.start)
    end = fastread.parse_date(args.end, end=True)
    _, msgs = fastread.fetch(chat["chat_id"], start=start, end=end, limit=args.limit or 200_000)
    if not msgs:
        _die("该会话在这个时间范围内没有消息（空表或日期不对）。")

    cfg = _cfg()
    export_dir = Path(cfg.get("export_dir") or (ROOT / "exports")).expanduser()
    if args.out:
        out = Path(args.out).expanduser()
    else:
        export_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r'[\\/:*?"<>|\s]+', "_", chat.get("display_name") or chat["chat_id"])
        out = export_dir / f"{safe}_{args.start or msgs[0]['time'][:10]}_{args.end or msgs[-1]['time'][:10]}.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# {chat.get('display_name')}",
        "",
        f"- 时间范围：{msgs[0]['time']} ~ {msgs[-1]['time']}",
        f"- 消息条数：{len(msgs)}",
        f"- 来源：本机微信快照（只读导出）",
        "",
    ]
    day = None
    for m in msgs:
        d = m["time"][:10]
        if d != day:
            lines += ["", f"## {d}", ""]
            day = d
        hm = m["time"][11:16]
        body = one_line(m.get("content"), 2000)
        who = m.get("sender") or ""
        lines.append(f"- **{hm} {who}**：{body}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已导出：{out}")
    print(f"条数：{len(msgs)}")
    return out


def cmd_status(args):
    if not LATEST.exists():
        print("还没有快照。")
        _print_disk_usage()
        return
    data = json.loads(LATEST.read_text(encoding="utf-8"))
    print(f"状态：{data.get('status')}   范围：{data.get('scope')}   校验：{data.get('validation')}")
    print(f"快照：{data.get('snapshot')}")
    print(f"库数：{data.get('databases')}")
    _print_disk_usage()


def _print_disk_usage():
    if not SNAPSHOT_ROOT.exists():
        return
    dirs = [d for d in SNAPSHOT_ROOT.iterdir() if d.is_dir()]
    size = sum(f.stat().st_size for d in dirs for f in d.rglob("*") if f.is_file())
    print(f"快照目录：{len(dirs)} 个，占用 {size / 1024 / 1024 / 1024:.1f} GB")
    if len(dirs) > 4:
        print("  [!] 快照占用偏大，可运行 python run.py clean --keep 2 --yes 清理旧快照")


def cmd_clean(args):
    if not SNAPSHOT_ROOT.exists():
        print("没有快照目录。")
        return
    latest = Path(current_snapshot()).resolve() if LATEST.exists() else None
    others = [d for d in SNAPSHOT_ROOT.iterdir() if d.is_dir() and d.resolve() != latest]
    others.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    keep_others = max(args.keep - 1, 0)
    keep, drop = others[:keep_others], others[keep_others:]
    print(f"当前快照：{latest.name if latest else '无'}")
    print(f"保留 {len(keep) + (1 if latest else 0)} 个（含当前），待清理 {len(drop)} 个：")
    for d in drop:
        size_mb = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1024 / 1024
        print(f"  {d.name}  {size_mb:.0f} MB")
    if not drop:
        return
    if not args.yes:
        print("\n只是列出，没有删除。确认后加 --yes 再跑一次。")
        return
    for d in drop:
        shutil.rmtree(d, ignore_errors=True)
    print("已清理。")


# ---------------------------------------------------------------- parser


def build_parser():
    p = argparse.ArgumentParser(prog="wx.py", description="微信本地资料库快捷入口", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("refresh", help="采集最新快照")
    r.add_argument("--all", action="store_true", help="全库采集（含收藏/朋友圈/媒体库）")
    r.add_argument("--seconds", type=int, help="内存扫描上限秒数（默认 90，最多 300）")
    r.set_defaults(func=cmd_refresh)

    c = sub.add_parser("chats", help="列出会话")
    c.add_argument("keyword", nargs="?", help="按名字过滤")
    c.add_argument("--group", action="store_true", help="只看群聊")
    c.add_argument("--limit", type=int, default=30, help="显示条数，默认 30")
    c.add_argument("--all", action="store_true", help="显示全部")
    c.set_defaults(func=cmd_chats)

    rd = sub.add_parser("read", help="按会话名读取聊天记录")
    rd.add_argument("name")
    rd.add_argument("--start")
    rd.add_argument("--end")
    rd.add_argument("--limit", type=int, default=60)
    rd.set_defaults(func=cmd_read)

    s = sub.add_parser("search", help="搜索聊天记录")
    s.add_argument("keyword")
    s.add_argument("--chat", help="限定会话名；不填则全库搜索（慢）")
    s.add_argument("--start")
    s.add_argument("--end")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(func=cmd_search)

    e = sub.add_parser("export", help="导出为 Markdown")
    e.add_argument("name")
    e.add_argument("--out")
    e.add_argument("--start")
    e.add_argument("--end")
    e.add_argument("--limit", type=int)
    e.set_defaults(func=cmd_export)

    st = sub.add_parser("status", help="查看当前快照")
    st.set_defaults(func=cmd_status)

    cl = sub.add_parser("clean", help="清理旧快照")
    cl.add_argument("--keep", type=int, default=3)
    cl.add_argument("--yes", action="store_true")
    cl.set_defaults(func=cmd_clean)
    return p


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = build_parser().parse_args()
    result = args.func(args)
    if getattr(args, "cmd", "") == "export" and result:
        pass


if __name__ == "__main__":
    main()
