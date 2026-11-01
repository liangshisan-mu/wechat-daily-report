@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   微信群聊日报 - 一键安装
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
  echo 首次运行，正在安装依赖，大约 3-5 分钟...
  echo 安装过程中请不要关闭窗口。
  echo.
  powershell -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
  if errorlevel 1 (
    echo.
    echo 安装失败，请把上面的报错截图发给作者。
    pause
    exit /b 1
  )
)

echo.
echo ========================================
echo   正在初始化：连接你的微信
echo ========================================
echo 请先确认微信电脑版已经登录，并保持窗口打开。
echo.
.\.venv\Scripts\python.exe run.py init

echo.
echo 如果上面显示“已写入 config.json”，就成功了。
echo 接下来双击“生成报告.bat”即可。
pause
