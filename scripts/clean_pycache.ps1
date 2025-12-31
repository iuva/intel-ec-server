# ========================================
# Windows PowerShell 递归删除 __pycache__ 文件夹脚本
# ========================================
# 
# 功能：递归删除指定目录及子目录中的所有 __pycache__ 文件夹
# 使用方法：
#   1. 右键点击脚本 -> "使用 PowerShell 运行"
#   2. 或在 PowerShell 中执行: .\scripts\clean_pycache.ps1
#   3. 或指定目录: .\scripts\clean_pycache.ps1 -Path "C:\Your\Project\Path"
# 
# ========================================

param(
    [string]$Path = (Split-Path -Parent $PSScriptRoot)
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "开始清理 __pycache__ 文件夹..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查目录是否存在
if (-not (Test-Path $Path)) {
    Write-Host "[错误] 目录不存在: $Path" -ForegroundColor Red
    exit 1
}

Write-Host "扫描目录: $Path" -ForegroundColor Yellow
Write-Host ""

# 查找所有 __pycache__ 文件夹
$pycacheFolders = Get-ChildItem -Path $Path -Filter "__pycache__" -Recurse -Directory -ErrorAction SilentlyContinue

if ($null -eq $pycacheFolders -or $pycacheFolders.Count -eq 0) {
    Write-Host "[信息] 未找到 __pycache__ 文件夹" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "清理完成！" -ForegroundColor Cyan
    Write-Host "共删除 0 个 __pycache__ 文件夹" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    exit 0
}

# 计数器
$count = 0
$failed = 0

# 删除每个 __pycache__ 文件夹
foreach ($folder in $pycacheFolders) {
    try {
        Write-Host "删除: $($folder.FullName)" -ForegroundColor Gray
        Remove-Item -Path $folder.FullName -Recurse -Force -ErrorAction Stop
        $count++
    }
    catch {
        Write-Host "  [警告] 删除失败: $($folder.FullName)" -ForegroundColor Yellow
        Write-Host "  错误信息: $($_.Exception.Message)" -ForegroundColor Yellow
        $failed++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "清理完成！" -ForegroundColor Cyan
Write-Host "成功删除: $count 个 __pycache__ 文件夹" -ForegroundColor Green
if ($failed -gt 0) {
    Write-Host "删除失败: $failed 个文件夹" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 如果是在交互式环境中运行，暂停以查看结果
if ($Host.Name -eq "ConsoleHost") {
    Write-Host "按任意键退出..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

