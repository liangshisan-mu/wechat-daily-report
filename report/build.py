"""把结构化报告 JSON 渲染成 HTML，并截图成长图。

用法:
    python report/build.py --data report/example.json --out out/report.png
    python report/build.py --data report.json --html-only
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = Path(__file__).resolve().parent


def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _prepare(data: dict, assets_dir: Path) -> dict:
    for p in data.get("people", []):
        av = (p.get("avatar") or "").strip()
        if av and not av.startswith("data:"):
            f = assets_dir / av
            if f.exists():
                p["avatar"] = _data_uri(f)
            else:
                p["avatar"] = ""
        if not p.get("avatar"):
            p["initial"] = (p.get("name") or "?")[:1]
    return data


def render(data_path: Path, out_html: Path, assets_dir: Path) -> Path:
    data = json.loads(data_path.read_text(encoding="utf-8"))
    data = _prepare(data, assets_dir)
    env = Environment(
        loader=FileSystemLoader(str(HERE)),
        autoescape=select_autoescape(enabled_extensions=(), default=False),
    )
    tpl = env.get_template("template.html")
    html = tpl.render(**data)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    out_html.write_text(html, encoding="utf-8")
    return out_html


def screenshot(html_path: Path, png_path: Path, width: int = 900) -> Path:
    from playwright.sync_api import sync_playwright

    png_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 1600}, device_scale_factor=2)
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.wait_for_timeout(400)
        page.screenshot(path=str(png_path), full_page=True)
        browser.close()
    return png_path


def main():
    ap = argparse.ArgumentParser(description="报告 JSON → HTML → PNG")
    ap.add_argument("--data", required=True, help="报告 JSON")
    ap.add_argument("--out", help="输出 PNG（默认 out/<data_stem>.png）")
    ap.add_argument("--html-out", help="输出 HTML（默认 out/<data_stem>.html）")
    ap.add_argument("--assets", default=str(HERE / "assets"), help="头像等素材目录")
    ap.add_argument("--html-only", action="store_true")
    args = ap.parse_args()

    data_path = Path(args.data)
    stem = data_path.stem
    out_dir = HERE.parent / "out"
    html_out = Path(args.html_out) if args.html_out else out_dir / f"{stem}.html"
    png_out = Path(args.out) if args.out else out_dir / f"{stem}.png"

    render(data_path, html_out, Path(args.assets))
    print(f"HTML: {html_out}")
    if not args.html_only:
        screenshot(html_out, png_out)
        print(f"PNG : {png_out}")


if __name__ == "__main__":
    main()
