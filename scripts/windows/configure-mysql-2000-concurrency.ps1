# MySQL/MariaDB 2000 并发 Windows 系统配置脚本
# 需要以管理员身份运行

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "错误: 此脚本需要管理员权限运行" -ForegroundColor Red
    Write-Host "请右键点击 PowerShell，选择'以管理员身份运行'" -ForegroundColor Yellow
    exit 1
}

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "MySQL/MariaDB 2000 并发 Windows 系统配置" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 配置 TCP/IP 参数
Write-Host "[1/4] 配置 TCP/IP 参数..." -ForegroundColor Yellow

$tcpipPath = "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"

# 设置 TCP 连接数限制
Write-Host "  设置 TcpNumConnections = 16777214" -ForegroundColor Gray
New-ItemProperty -Path $tcpipPath -Name "TcpNumConnections" -Value 16777214 -PropertyType DWORD -Force | Out-Null

# 设置最大用户端口
Write-Host "  设置 MaxUserPort = 65534" -ForegroundColor Gray
New-ItemProperty -Path $tcpipPath -Name "MaxUserPort" -Value 65534 -PropertyType DWORD -Force | Out-Null

# 设置 TIME_WAIT 延迟（30秒）
Write-Host "  设置 TcpTimedWaitDelay = 30" -ForegroundColor Gray
New-ItemProperty -Path $tcpipPath -Name "TcpTimedWaitDelay" -Value 30 -PropertyType DWORD -Force | Out-Null

Write-Host "  ✓ TCP/IP 参数配置完成" -ForegroundColor Green
Write-Host ""

# 2. 配置 Windows 防火墙规则
Write-Host "[2/4] 配置 Windows 防火墙规则..." -ForegroundColor Yellow

# 检查是否已存在 MySQL 防火墙规则
$existingRule = Get-NetFirewallRule -DisplayName "MySQL Server" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "  MySQL 防火墙规则已存在，跳过创建" -ForegroundColor Gray
} else {
    Write-Host "  创建 MySQL 防火墙规则（端口 3306）" -ForegroundColor Gray
    New-NetFirewallRule -DisplayName "MySQL Server" -Direction Inbound -LocalPort 3306 -Protocol TCP -Action Allow | Out-Null
    Write-Host "  ✓ 防火墙规则创建完成" -ForegroundColor Green
}

Write-Host ""

# 3. 优化网络参数
Write-Host "[3/4] 优化网络参数..." -ForegroundColor Yellow

Write-Host "  设置 TCP 自动调优级别为 normal" -ForegroundColor Gray
netsh int tcp set global autotuninglevel=normal | Out-Null

Write-Host "  启用 TCP Chimney Offload" -ForegroundColor Gray
netsh int tcp set global chimney=enabled | Out-Null

Write-Host "  启用 RSS (Receive Side Scaling)" -ForegroundColor Gray
netsh int tcp set global rss=enabled | Out-Null

Write-Host "  启用 NetDMA" -ForegroundColor Gray
netsh int tcp set global netdma=enabled | Out-Null

Write-Host "  ✓ 网络参数优化完成" -ForegroundColor Green
Write-Host ""

# 4. 显示当前配置
Write-Host "[4/4] 显示当前配置..." -ForegroundColor Yellow
Write-Host ""

Write-Host "TCP/IP 参数:" -ForegroundColor Cyan
$tcpNumConnections = Get-ItemProperty -Path $tcpipPath -Name "TcpNumConnections" -ErrorAction SilentlyContinue
$maxUserPort = Get-ItemProperty -Path $tcpipPath -Name "MaxUserPort" -ErrorAction SilentlyContinue
$tcpTimedWaitDelay = Get-ItemProperty -Path $tcpipPath -Name "TcpTimedWaitDelay" -ErrorAction SilentlyContinue

Write-Host "  TcpNumConnections: $($tcpNumConnections.TcpNumConnections)" -ForegroundColor Gray
Write-Host "  MaxUserPort: $($maxUserPort.MaxUserPort)" -ForegroundColor Gray
Write-Host "  TcpTimedWaitDelay: $($tcpTimedWaitDelay.TcpTimedWaitDelay) 秒" -ForegroundColor Gray
Write-Host ""

Write-Host "防火墙规则:" -ForegroundColor Cyan
Get-NetFirewallRule -DisplayName "MySQL Server" | Format-Table DisplayName, Direction, Action, Enabled -AutoSize
Write-Host ""

Write-Host "TCP 全局参数:" -ForegroundColor Cyan
netsh int tcp show global
Write-Host ""

# 5. 提示信息
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "配置完成！" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "重要提示:" -ForegroundColor Yellow
Write-Host "1. 部分配置需要重启系统才能生效" -ForegroundColor White
Write-Host "2. 请确保 MySQL/MariaDB 服务器的 max_connections 设置为 3000" -ForegroundColor White
Write-Host "3. 请确保应用程序的 DB_POOL_SIZE 和 DB_MAX_OVERFLOW 已正确配置" -ForegroundColor White
Write-Host "4. 详细配置说明请参考: docs/performance/mysql-2000-concurrency-windows-optimization.md" -ForegroundColor White
Write-Host ""
Write-Host "是否现在重启系统？(Y/N): " -ForegroundColor Yellow -NoNewline
$restart = Read-Host

if ($restart -eq "Y" -or $restart -eq "y") {
    Write-Host "系统将在 10 秒后重启..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    Restart-Computer -Force
} else {
    Write-Host "请稍后手动重启系统以使配置生效" -ForegroundColor Yellow
}

