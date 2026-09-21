#!/bin/bash
# PhotoCurator macOS 启动器: 首次运行自动创建虚拟环境并安装依赖 (本地化安装, 无需签名)
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "首次运行: 正在安装依赖..."
  python3 -m venv .venv || { echo "需要 python3 (brew install python)"; exit 1; }
fi
./.venv/bin/pip install -q -r requirements.txt
exec ./.venv/bin/python app.py
