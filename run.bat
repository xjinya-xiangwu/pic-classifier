@echo off
rem PhotoCurator Windows 启动器 (开发/调试用, 目标平台为 macOS)
cd /d %~dp0
if not exist .venv (
  echo 首次运行: 正在安装依赖...
  python -m venv .venv || exit /b 1
)
.venv\Scripts\pip install -q -r requirements.txt
.venv\Scripts\python app.py
pause
