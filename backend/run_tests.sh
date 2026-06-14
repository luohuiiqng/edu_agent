#!/bin/bash
cd "$(dirname "$0")"
# 设置Python路径，确保能找到app模块
export PYTHONPATH=$PYTHONPATH:.
source .venv/bin/activate
# 运行我们修改的测试文件
pytest app/test/test_chat_agent.py app/test/test_sequential_workflow.py -v