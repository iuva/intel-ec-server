@echo off
REM 本地开发启动脚本 - Windows 版本
REM 支持从 .env 文件加载环境变量
REM
REM 使用方式：
REM   start_services_local.bat check              检查环境配置
REM   start_services_local.bat all                显示所有启动命令
REM   start_services_local.bat gateway            启动网关服务 (8000)
REM   start_services_local.bat auth               启动认证服务 (8001)
REM   start_services_local.bat admin              启动管理服务 (8002)
REM   start_services_local.bat host               启动主机服务 (8003)

setlocal enabledelayedexpansion

REM ==================== 颜色定义 ====================
REM Windows 命令行不支持 ANSI 颜色，使用文本代替

REM ==================== 项目路径 ====================
set "PROJECT_ROOT=%~dp0.."
set "ENV_FILE=%PROJECT_ROOT%\.env"
set "VENV_DIR=%PROJECT_ROOT%\venv"
set "VENV_ACTIVATE=%VENV_DIR%\Scripts\activate.bat"

REM ==================== 加载 .env 文件 ====================
:load_env_file
if exist "%ENV_FILE%" (
    echo [INFO] 从 .env 文件加载环境变量...
    for /f "usebackq delims==" %%a in (`type "%ENV_FILE%" ^| findstr /v "^#"`) do (
        set "%%a"
    )
    echo [OK] 环境变量加载成功
) else (
    echo [WARNING] .env 文件不存在，使用默认环境变量
)
goto :EOF

REM ==================== 激活虚拟环境 ====================
:activate_venv
if exist "%VENV_ACTIVATE%" (
    echo [INFO] 激活虚拟环境...
    call "%VENV_ACTIVATE%"
    echo [OK] 虚拟环境激活成功
) else (
    echo [ERROR] 虚拟环境不存在
    echo 请先运行以下命令创建虚拟环境：
    echo   python -m venv venv
    echo   venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    exit /b 1
)
goto :EOF

REM ==================== 检查环境 ====================
:check_environment
echo.
echo ================================================================================
echo [CHECK] 环境检查
echo ================================================================================
echo.

echo [INFO] Python 版本检查
python --version
echo.

echo [INFO] 虚拟环境检查
if exist "%VENV_DIR%" (
    echo [OK] 虚拟环境存在
) else (
    echo [ERROR] 虚拟环境不存在
)
echo.

echo [INFO] .env 文件检查
if exist "%ENV_FILE%" (
    echo [OK] .env 文件存在
    echo 关键环境变量：
    echo   PYTHONPATH: %PYTHONPATH%
    if defined MARIADB_HOST (
        echo   MARIADB_HOST: %MARIADB_HOST%
    ) else (
        echo   MARIADB_HOST: 127.0.0.1 (默认)
    )
    if defined MARIADB_PORT (
        echo   MARIADB_PORT: %MARIADB_PORT%
    ) else (
        echo   MARIADB_PORT: 3306 (默认)
    )
) else (
    echo [WARNING] .env 文件不存在 (可选)
)
echo.

echo ================================================================================
goto :EOF

REM ==================== 显示所有启动命令 ====================
:show_all_commands
echo.
echo ================================================================================
echo [INFO] 本地开发启动指南
echo ================================================================================
echo.
echo [WARNING] 重要：必须在不同的命令行窗口中启动每个服务
echo.
echo 启动顺序（必须按此顺序）：
echo.
echo [1] 命令行窗口1 - Auth Service (8001):
echo     cd /d "%PROJECT_ROOT%"
echo     call venv\Scripts\activate.bat
echo     python -m uvicorn services.auth-service.app.main:app --host 0.0.0.0 --port 8001 --reload
echo.
echo [2] 命令行窗口2 - Admin Service (8002):
echo     cd /d "%PROJECT_ROOT%"
echo     call venv\Scripts\activate.bat
echo     python -m uvicorn services.admin-service.app.main:app --host 0.0.0.0 --port 8002 --reload
echo.
echo [3] 命令行窗口3 - Host Service (8003):
echo     cd /d "%PROJECT_ROOT%"
echo     call venv\Scripts\activate.bat
echo     python -m uvicorn services.host-service.app.main:app --host 0.0.0.0 --port 8003 --reload
echo.
echo [4] 命令行窗口4 - Gateway Service (8000) [最后启动]:
echo     cd /d "%PROJECT_ROOT%"
echo     call venv\Scripts\activate.bat
echo     python -m uvicorn services.gateway-service.app.main:app --host 0.0.0.0 --port 8000 --reload
echo.
echo ================================================================================
echo [INFO] 快速启动技巧
echo ================================================================================
echo 如果已配置 PYTHONPATH，可以用简化命令：
echo     cd /d %PROJECT_ROOT%\services\auth-service
echo     python -m uvicorn app.main:app --port 8001 --reload
echo.
goto :EOF

REM ==================== 启动服务 ====================
:start_service
set "SERVICE_NAME=%~1"
set "PORT=%~2"
set "SERVICE_DIR=%~3"

echo.
echo ================================================================================
echo [START] 启动 %SERVICE_NAME% (端口: %PORT%)
echo ================================================================================
echo.
echo 服务目录: %SERVICE_DIR%
echo 工作目录: %PROJECT_ROOT%\%SERVICE_DIR%
echo.
echo [INFO] 按 Ctrl+C 停止服务
echo.

REM 进入服务目录后启动（这样相对导入才能工作）
cd /d "%PROJECT_ROOT%\%SERVICE_DIR%"
python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT% --reload
goto :EOF

REM ==================== 主程序 ====================
:main
call :load_env_file
echo.

call :activate_venv
if errorlevel 1 exit /b 1
echo.

set "PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%"
echo [OK] PYTHONPATH 已设置为: %PYTHONPATH%
echo.

if "%~1"=="" (
    echo [WARNING] 使用方式：
    echo   %~nx0 check               检查环境配置
    echo   %~nx0 all                 显示所有启动命令
    echo   %~nx0 gateway             启动网关服务 (8000)
    echo   %~nx0 auth                启动认证服务 (8001)
    echo   %~nx0 admin               启动管理服务 (8002)
    echo   %~nx0 host                启动主机服务 (8003)
    exit /b 1
)

if /i "%~1"=="check" (
    call :check_environment
) else if /i "%~1"=="all" (
    call :show_all_commands
) else if /i "%~1"=="gateway" (
    call :start_service "Gateway Service" "8000" "services\gateway-service"
) else if /i "%~1"=="auth" (
    call :start_service "Auth Service" "8001" "services\auth-service"
) else if /i "%~1"=="admin" (
    call :start_service "Admin Service" "8002" "services\admin-service"
) else if /i "%~1"=="host" (
    call :start_service "Host Service" "8003" "services\host-service"
) else (
    echo [ERROR] 未知的命令: %~1
    echo 支持的命令: check, all, gateway, auth, admin, host
    exit /b 1
)

goto :EOF

call :main %*
