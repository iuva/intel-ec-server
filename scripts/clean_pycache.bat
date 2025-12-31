@echo off
REM ========================================
REM Windows 递归删除 __pycache__ 文件夹脚本
REM ========================================
REM 
REM 功能：递归删除当前目录及子目录中的所有 __pycache__ 文件夹
REM 使用方法：双击运行或在命令行中执行
REM 
REM ========================================

echo ========================================
echo 开始清理 __pycache__ 文件夹...
echo ========================================
echo.

REM 设置起始目录（默认为脚本所在目录的父目录，即项目根目录）
set "START_DIR=%~dp0.."

REM 如果指定了参数，使用参数作为起始目录
if not "%~1"=="" set "START_DIR=%~1"

echo 扫描目录: %START_DIR%
echo.

REM 计数器
set /a count=0

REM 递归查找并删除所有 __pycache__ 文件夹
for /r "%START_DIR%" /d %%d in (__pycache__) do (
    if exist "%%d" (
        echo 删除: %%d
        rd /s /q "%%d" 2>nul
        if not errorlevel 1 (
            set /a count+=1
        ) else (
            echo    [警告] 删除失败: %%d
        )
    )
)

echo.
echo ========================================
echo 清理完成！
echo 共删除 %count% 个 __pycache__ 文件夹
echo ========================================
echo.
pause

