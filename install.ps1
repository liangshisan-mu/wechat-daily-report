# 一行安装脚本（Windows）
# 用法：
#   irm https://raw.githubusercontent.com/l18028092047-crypto/wechat-daily-report/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$repo = "l18028092047-crypto/wechat-daily-report"
$dest = Join-Path $env:USERPROFILE "wechat-daily-report"

Write-Host ""
Write-Host "== 微信群聊日报 · 一键安装 ==" -ForegroundColor Cyan
Write-Host "安装位置：$dest"
Write-Host ""

if (-not (Test-Path $dest)) {
    $zip = Join-Path $env:TEMP "wechat-daily-report.zip"
    $tmp = Join-Path $env:TEMP "wechat-daily-report-main"
    if (Test-Path $tmp) { Remove-Item -Recurse -Force $tmp }
    if (Test-Path $zip) { Remove-Item -Force $zip }

    Write-Host "正在下载项目..." -ForegroundColor Cyan
    Invoke-WebRequest "https://github.com/$repo/archive/refs/heads/main.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath $env:TEMP -Force
    Move-Item $tmp $dest
    Remove-Item $zip
} else {
    Write-Host "目录已存在，跳过下载。" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "正在安装依赖（3-5 分钟）..." -ForegroundColor Cyan
& powershell -ExecutionPolicy Bypass -File (Join-Path $dest "setup.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "依赖安装失败，请检查上面的报错。"
}

Write-Host ""
Write-Host "正在连接微信（请保持微信登录）..." -ForegroundColor Cyan
$py = Join-Path $dest ".venv\Scripts\python.exe"
& $py (Join-Path $dest "run.py") init --auto

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "安装完成！" -ForegroundColor Green
Write-Host "下一步：双击 $dest\生成报告.bat" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
