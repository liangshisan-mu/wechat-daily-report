﻿# 一键安装（Windows PowerShell）
# 用法：右键“使用 PowerShell 运行”，或在项目目录执行：
#   powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"
chcp 65001 > $null
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
Set-Location $PSScriptRoot

function Install-Req {
    param([string]$File)
    Write-Host "安装 $File ..."
    & $vpy -m pip install --index-url https://pypi.org/simple -r $File
    if ($LASTEXITCODE -ne 0) {
        Write-Host "官方源不可用，改用清华镜像重试..." -ForegroundColor Yellow
        & $vpy -m pip install --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r $File
    }
    if ($LASTEXITCODE -ne 0) {
        throw "依赖安装失败：$File"
    }
}

Write-Host "== 1/5 检查 Python ==" -ForegroundColor Cyan
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "没找到 python。请安装 Python 3.12（勾选 Add to PATH）后重试。" -ForegroundColor Red
    exit 1
}
$ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python $ver"
if ([version]$ver -lt [version]"3.10") {
    Write-Host "需要 Python 3.10+，推荐 3.12。" -ForegroundColor Red
    exit 1
}

Write-Host "== 2/5 创建虚拟环境 ==" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "创建虚拟环境失败" }
}
$vpy = ".\.venv\Scripts\python.exe"
& $vpy -m pip install --upgrade pip --index-url https://pypi.org/simple

Write-Host "== 3/5 安装依赖 ==" -ForegroundColor Cyan
Install-Req "requirements.txt"
& $vpy -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "Chromium 下载失败" }

Write-Host "== 4/5 拉取采集 skill ==" -ForegroundColor Cyan
if (-not (Test-Path "vendor\yichen-wechat-local-vault\scripts\vault_cli.py")) {
    New-Item -ItemType Directory -Force vendor | Out-Null
    if (Test-Path "vendor-tmp") { Remove-Item -Recurse -Force "vendor-tmp" }
    git clone --depth 1 https://github.com/mcncarl/yichen-skills.git vendor-tmp
    if ($LASTEXITCODE -ne 0) { throw "克隆采集 skill 失败，检查网络或 Git 是否安装" }
    Move-Item "vendor-tmp\yichen-wechat-local-vault" "vendor\yichen-wechat-local-vault"
    Remove-Item -Recurse -Force "vendor-tmp"
}
Install-Req "vendor\yichen-wechat-local-vault\references\windows-snapshot\requirements.lock"

Write-Host "== 5/5 完成 ==" -ForegroundColor Green
Write-Host ""
Write-Host "下一步（微信保持登录）："
Write-Host "  .\.venv\Scripts\python.exe run.py init"
Write-Host ""
