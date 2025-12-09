# Windows pip 安装 requirements.txt 编码修复脚本
# 使用方法: .\scripts\windows\install_requirements.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "安装 Python 依赖（Windows 编码修复）" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 requirements.txt 是否存在
$requirementsFile = "requirements.txt"
if (-not (Test-Path $requirementsFile)) {
    Write-Host "错误: 找不到 $requirementsFile 文件" -ForegroundColor Red
    Write-Host "请确保在项目根目录运行此脚本" -ForegroundColor Yellow
    exit 1
}

# 设置编码环境变量
Write-Host "设置 UTF-8 编码环境变量..." -ForegroundColor Yellow
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# 检查 Python 是否安装
Write-Host "检查 Python 安装..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python 版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "错误: 未找到 Python，请先安装 Python 3.8.10" -ForegroundColor Red
    exit 1
}

# 检查 pip 是否安装
Write-Host "检查 pip 安装..." -ForegroundColor Yellow
try {
    $pipVersion = pip --version 2>&1
    Write-Host "✓ $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "错误: 未找到 pip，请先安装 pip" -ForegroundColor Red
    exit 1
}

# 升级 pip
Write-Host ""
Write-Host "升级 pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ pip 升级完成" -ForegroundColor Green
} else {
    Write-Host "警告: pip 升级失败，继续安装依赖..." -ForegroundColor Yellow
}

# 安装依赖
Write-Host ""
Write-Host "安装项目依赖..." -ForegroundColor Yellow
Write-Host "这可能需要几分钟时间，请耐心等待..." -ForegroundColor Gray
Write-Host ""

pip install -r $requirementsFile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ 依赖安装成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    
    # 验证关键包
    Write-Host "验证关键包安装..." -ForegroundColor Yellow
    $packages = @("fastapi", "sqlalchemy", "pydantic", "redis")
    foreach ($package in $packages) {
        try {
            $result = python -c "import $package; print($package.__version__)" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ $package : $result" -ForegroundColor Green
            } else {
                Write-Host "  ✗ $package : 未安装" -ForegroundColor Red
            }
        } catch {
            Write-Host "  ✗ $package : 验证失败" -ForegroundColor Red
        }
    }
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "✗ 依赖安装失败" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "如果仍然遇到编码错误，请尝试以下方法：" -ForegroundColor Yellow
    Write-Host "1. 使用 chcp 65001 切换到 UTF-8 代码页" -ForegroundColor Yellow
    Write-Host "2. 查看详细文档: docs/42-windows-pip-encoding-fix.md" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "安装完成！" -ForegroundColor Green

