@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo 还没安装，请先双击“一键安装.bat”。
  pause
  exit /b 1
)

echo ========================================
echo   微信群聊日报 - 生成报告
echo ========================================
echo.
set /p GROUP=请输入群名（不用写全，能匹配到就行）：
set /p DATE=请输入日期（例如 2026-10-31）：

if "%GROUP%"=="" (
  echo 群名不能为空。
  pause
  exit /b 1
)
if "%DATE%"=="" (
  echo 日期不能为空。
  pause
  exit /b 1
)

echo.
echo 正在处理，请稍等。第一次会采集快照，约 20 秒...
echo.
.\.venv\Scripts\python.exe run.py build --group "%GROUP%" --date %DATE%

echo.
echo 完成。图片在 out 文件夹里。
pause
