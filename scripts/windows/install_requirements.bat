@echo off
REM Windows pip 安装 requirements.txt 编码修复脚本
REM 使用方法: scripts\windows\install_requirements.bat

chcp 65001 >nul
echo ========================================
echo 安装 Python 依赖（Windows 编码修复）
echo ========================================
echo.

REM 检查 requirements.txt 是否存在
if not exist "requirements.txt" (
    echo 错误: 找不到 requirements.txt 文件
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

REM 设置编码环境变量
echo 设置 UTF-8 编码环境变量...
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM 检查 Python 是否安装
echo 检查 Python 安装...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8.10
    pause
    exit /b 1
)
python --version

REM 检查 pip 是否安装
echo 检查 pip 安装...
pip --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 pip，请先安装 pip
    pause
    exit /b 1
)
pip --version

REM 升级 pip
echo.
echo 升级 pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo 警告: pip 升级失败，继续安装依赖...
)

REM 安装依赖
echo.
echo 安装项目依赖...
echo 这可能需要几分钟时间，请耐心等待...
echo.

pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ========================================
    echo 依赖安装失败
    echo ========================================
    echo.
    echo 如果仍然遇到编码错误，请尝试以下方法：
    echo 1. 查看详细文档: docs\42-windows-pip-encoding-fix.md
    echo 2. 使用 PowerShell 脚本: scripts\windows\install_requirements.ps1
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo 依赖安装成功！
    echo ========================================
    echo.
    echo 验证关键包安装...
    python -c "import fastapi; print('  fastapi:', fastapi.__version__)" 2>nul
    python -c "import sqlalchemy; print('  sqlalchemy:', sqlalchemy.__version__)" 2>nul
    python -c "import pydantic; print('  pydantic:', pydantic.__version__)" 2>nul
    python -c "import redis; print('  redis:', redis.__version__)" 2>nul
    echo.
    echo 安装完成！
)

pause

