#!/usr/bin/env bash
# 一键安装（macOS / Linux）
set -e
cd "$(dirname "$0")"

echo "== 1/4 创建虚拟环境 =="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium

echo "== 2/4 拉取采集 skill =="
mkdir -p vendor
if [ ! -f "vendor/yichen-wechat-local-vault/scripts/vault_cli.py" ]; then
  git clone --depth 1 https://github.com/mcncarl/yichen-skills.git vendor-tmp
  mv vendor-tmp/yichen-wechat-local-vault vendor/yichen-wechat-local-vault
  rm -rf vendor-tmp
fi

echo "== 3/4 安装采集依赖 =="
pip install -r vendor/yichen-wechat-local-vault/references/windows-snapshot/requirements.lock || true

echo "== 4/4 完成 =="
echo
echo "下一步（微信保持登录）："
echo "  source .venv/bin/activate && python run.py init"
