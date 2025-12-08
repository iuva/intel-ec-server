@echo off
REM tests/performance/http/windows/run_load_test.bat
REM Windows 压测执行脚本

set HOST_URL=http://localhost:8003
set TEST_ENV=local
set RESULTS_DIR=results

REM 创建结果目录
if not exist %RESULTS_DIR% mkdir %RESULTS_DIR%

echo ========================================
echo Windows 压测脚本
echo ========================================
echo 目标服务: %HOST_URL%
echo 测试环境: %TEST_ENV%
echo 结果目录: %RESULTS_DIR%
echo ========================================

echo.
echo 执行 k6 压测...
set K6_HOST_URL=%HOST_URL%
set K6_ENV=%TEST_ENV%
k6 run tests/performance/http/windows/k6_load_test_windows.js --out json=%RESULTS_DIR%/k6_results.json --out csv=%RESULTS_DIR%/k6_results.csv

echo.
echo ========================================
echo 压测完成！
echo 结果文件保存在: %RESULTS_DIR%
echo ========================================
pause

