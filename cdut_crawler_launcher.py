""" 计划任务启动器 - 绕过 Task Scheduler 中文路径问题 """
import os
import subprocess
import sys

# 项目目录，可通过环境变量 CRAWLER_PROJECT_DIR 覆盖
PROJECT_DIR = os.environ.get(
    "CRAWLER_PROJECT_DIR",
    r"你的项目路径"  # ← 修改为你的项目实际路径
)
result = subprocess.run([sys.executable, "main.py"], cwd=PROJECT_DIR)
sys.exit(result.returncode)
