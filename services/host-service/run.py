"""Host Service 启动脚本

此脚本用于正确设置 Python 路径并启动服务
"""

import os
import sys

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

# 现在可以正常导入并启动应用
if __name__ == "__main__":
    import uvicorn
    from app.main import app

    host = os.getenv("SERVICE_HOST", "127.0.0.1")  # 默认仅本地访问
    port = int(os.getenv("SERVICE_PORT", "8003"))
    uvicorn.run(app, host=host, port=port)
