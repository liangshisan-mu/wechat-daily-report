#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一条命令，把某个微信群某一天的消息，生成一张研究报告式长图。

用法:
    python run.py init                         初始化：找微信数据目录、探测账号、写 config.json
    python run.py refresh                      采集最新快照（微信需运行）
    python run.py chats [关键词]               列出会话
    python run.py build --group "群名" --date 2026-10-31
    python run.py build --group "群名" --date 2026-10-31 --no-refresh
    python run.py export --group "群名" --date 2026-10-31

build 需要 config.json 里配置 llm（OpenAI 兼容接口）才能自动提炼；
未配置时会导出聊天并提示你用 prompts/extract.md 交给任意 AI。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wxread import avatars, config, fastread, wx  # noqa: E402
from report import build as report_build  # noqa: E402

DEFAULT_SKILL = ROOT / "vendor" / "yichen-wechat-local-vault"


def _die(msg: str, code: int = 1):
    print(f"[x] {msg}", file=sys.stderr)
    raise SystemExit(code)


def _slug(text: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", text).strip("_") or "report"


# ---------------------------------------------------------------- init


def find_db_roots() -> list[Path]:
    """找 xwechat_files 目录（微信 4.x 的数据根）。"""
    out: list[Path] = []
    home = Path.home()
    for p in (home / "Documents" / "xwechat_files", home / "xwechat_files"):
        if p.is_dir():
            out.append(p)
    for drive in "CDEFGH":
        d = Path(f"{drive}:/")
        if not d.exists():
            continue
        try:
            for p in d.iterdir():
                if not p.is_dir():
                    continue
                if p.name == "xwechat_files":
                    out.append(p)
                elif (p / "xwechat_files").is_dir():
                    out.append(p / "xwechat_files")
        except OSError:
            continue
    seen, res = set(), []
    for p in out:
        r = str(p.resolve())
        if r not in seen:
            seen.add(r)
            res.append(p)
    return res


def find_db_storages(root: Path) -> list[Path]:
    return sorted([p for p in root.glob("*/db_storage") if p.is_dir()])


def cmd_init(args):
    auto = bool(getattr(args, "auto", False))
    print("== 初始化 ==")
    roots = find_db_roots()
    if not roots:
        _die("没找到 xwechat_files。请确认微信 4.x 已登录，并在设置里查看数据目录。")

    print("找到这些微信数据根目录：")
    for i, p in enumerate(roots, 1):
        print(f"  {i}. {p}")
    idx = 1
    if len(roots) > 1 and not auto:
        raw = input("选择哪一个（序号，回车默认 1）：").strip()
        idx = int(raw) if raw.isdigit() and 1 <= int(raw) <= len(roots) else 1
    root = roots[idx - 1]

    storages = find_db_storages(root)
    if not storages:
        _die(f"{root} 下没有 */db_storage，可能还没登录过微信。")
    print("\n找到这些账号的数据目录：")
    for i, p in enumerate(storages, 1):
        print(f"  {i}. {p.parent.name}")
    sidx = 1
    if len(storages) > 1 and not auto:
        raw = input("选择账号（序号，回车默认 1）：").strip()
        sidx = int(raw) if raw.isdigit() and 1 <= int(raw) <= len(storages) else 1
    db_root = storages[sidx - 1]

    skill_dir = DEFAULT_SKILL
    cli = skill_dir / "scripts" / "vault_cli.py"
    if not cli.exists():
        _die(f"找不到采集脚本：{cli}\n先运行 setup.ps1，或手动把 yichen-wechat-local-vault 放到 vendor/ 下。")

    print("\n正在探测微信进程与数据库（微信需保持运行）…")
    proc = subprocess.run(
        [sys.executable, str(cli), "windows", "discover", "--db-root", str(db_root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")
    print(out.strip()[-1500:])
    if proc.returncode != 0:
        _die("探测失败。确认微信正在运行，且数据目录选对了。")

    data = {}
    start = (proc.stdout or "").find("{")
    if start >= 0:
        try:
            data = json.loads(proc.stdout[start:])
        except json.JSONDecodeError:
            data = {}

    source_id = ""
    sources = data.get("sources") or data.get("processes") or []
    if isinstance(sources, list) and sources:
        first = sources[0]
        if isinstance(first, dict):
            source_id = str(first.get("source_id") or first.get("id") or "")
    source_id = source_id or str(data.get("source_id") or "")

    cfg = {
        "python": sys.executable,
        "skill_dir": str(skill_dir),
        "source_id": source_id,
        "db_root": str(db_root),
        "snapshot_dir": "",
        "export_dir": str(ROOT / "exports"),
        "llm": {
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "",
            "model": "deepseek-chat",
        },
    }
    config.save(cfg)
    print(f"\n已写入 {config.CONFIG_PATH}")
    if not source_id:
        print("[!] 没自动解析出 source_id。把上面 discover 输出里的 id 填到 config.json 的 source_id。")
    print("下一步：在 config.json 里填 llm.api_key（可选），然后运行：")
    print('  python run.py build --group "你的群名" --date 2026-10-31')


# ---------------------------------------------------------------- refresh / list


def cmd_refresh(args):
    wx.cmd_refresh(argparse.Namespace(all=args.all, seconds=args.seconds))


def cmd_chats(args):
    wx.cmd_chats(argparse.Namespace(keyword=args.keyword, group=args.group, limit=args.limit, all=args.all))


# ---------------------------------------------------------------- llm


def _extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("模型输出里没有 JSON")
    return json.loads(text[start : end + 1])


def call_llm(md_text: str) -> dict | None:
    cfg = config.load()
    llm = cfg.get("llm") or {}
    key = llm.get("api_key") or os.environ.get("WXDR_LLM_KEY", "")
    if not key:
        return None
    base = (llm.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    model = llm.get("model") or "gpt-4o-mini"
    prompt = (ROOT / "prompts" / "extract.md").read_text(encoding="utf-8")
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": md_text},
            ],
            "temperature": 0.3,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        base + "/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    print(f"正在调用模型提炼（{model}）…", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    return _extract_json(content)


# ---------------------------------------------------------------- avatars


def attach_avatars(report: dict, chat_id: str, date: str, end: str | None):
    start_ts = fastread.parse_date(date)
    end_ts = fastread.parse_date(end, end=True) if end else start_ts + 86400
    try:
        stats = fastread.sender_stats(chat_id, start_ts, end_ts)
    except Exception as exc:
        print(f"[!] 读取发言人失败，头像留空：{exc}", file=sys.stderr)
        return
    by_name: dict[str, list[dict]] = {}
    for s in stats:
        by_name.setdefault(s["name"], []).append(s)
    assets = ROOT / "report" / "assets"
    for p in report.get("people", []):
        name = (p.get("name") or "").strip()
        cands = by_name.get(name) or [s for s in stats if name and name in s["name"]]
        if not cands:
            continue
        best = max(cands, key=lambda x: x["count"])
        if not best.get("username"):
            continue
        try:
            f = avatars.download_avatar(best["username"], assets, filename=f"{best['username']}.jpg")
            if f:
                p["avatar"] = f.name
        except Exception as exc:
            print(f"[!] 头像下载失败 {name}：{exc}", file=sys.stderr)


# ---------------------------------------------------------------- build


def cmd_build(args):
    cfg = config.load()
    chat = wx.resolve_chat(args.group)
    print(f"群：{chat.get('display_name')}  ({chat.get('chat_id')})")

    if not args.no_refresh:
        print("\n[1/4] 采集最新快照…")
        wx.cmd_refresh(argparse.Namespace(all=False, seconds=None))
    else:
        print("\n[1/4] 跳过采集")

    print("\n[2/4] 导出聊天…")
    export_args = argparse.Namespace(
        name=args.group,
        out=None,
        start=args.date,
        end=args.end or (datetime.strptime(args.date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"),
        limit=args.limit,
    )
    md_path = wx.cmd_export(export_args)
    md_text = Path(md_path).read_text(encoding="utf-8")

    print("\n[3/4] 提炼内容…")
    report = call_llm(md_text)
    out_dir = ROOT / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _slug(f"{chat.get('display_name')}_{args.date}")
    data_path = out_dir / f"{slug}.json"

    if report is None:
        print(
            "未配置 llm.api_key，已停在导出这一步。\n"
            f"聊天记录：{md_path}\n"
            "把这份记录和 prompts/extract.md 一起交给任意 AI，让它输出 JSON，\n"
            f"保存为 {data_path}，再运行：\n"
            f'  python report/build.py --data "{data_path}"'
        )
        return

    attach_avatars(report, chat["chat_id"], args.date, args.end)
    data_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告数据：{data_path}")

    print("\n[4/4] 渲染与截图…")
    html_path = out_dir / f"{slug}.html"
    png_path = Path(args.out) if args.out else out_dir / f"{slug}.png"
    report_build.render(data_path, html_path, ROOT / "report" / "assets")
    report_build.screenshot(html_path, png_path)
    print(f"\n完成：{png_path}")


# ---------------------------------------------------------------- parser


def build_parser():
    p = argparse.ArgumentParser(prog="run.py", description="微信群聊 → 研究报告长图")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="初始化配置")
    i.add_argument("--auto", action="store_true", help="自动选择第一个数据目录与账号，不交互")
    i.set_defaults(func=cmd_init)

    r = sub.add_parser("refresh", help="采集最新快照")
    r.add_argument("--all", action="store_true")
    r.add_argument("--seconds", type=int)
    r.set_defaults(func=cmd_refresh)

    c = sub.add_parser("chats", help="列出会话")
    c.add_argument("keyword", nargs="?")
    c.add_argument("--group", action="store_true")
    c.add_argument("--limit", type=int, default=30)
    c.add_argument("--all", action="store_true")
    c.set_defaults(func=cmd_chats)

    b = sub.add_parser("build", help="生成报告长图")
    b.add_argument("--group", required=True, help="群名（可模糊匹配）")
    b.add_argument("--date", required=True, help="日期，如 2026-10-31")
    b.add_argument("--end", help="结束日期（默认 date+1 天，用于单日导出）")
    b.add_argument("--limit", type=int, default=5000)
    b.add_argument("--no-refresh", action="store_true", help="跳过重新采集，直接用现有快照")
    b.add_argument("--out", help="输出 PNG 路径")
    b.set_defaults(func=cmd_build)

    return p


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
