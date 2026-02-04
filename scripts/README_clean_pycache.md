# Windows 清理 __pycache__ 脚本使用说明

## 📋 脚本文件

1. **`clean_pycache.bat`** - Windows 批处理脚本（兼容性最好）
2. **`clean_pycache.ps1`** - PowerShell 脚本（功能更强大，推荐）

## 🚀 使用方法

### 方法1：使用批处理脚本（.bat）

#### 双击运行
- 直接双击 `clean_pycache.bat` 文件
- 脚本会自动扫描项目根目录并删除所有 `__pycache__` 文件夹

#### 命令行运行
```cmd
# 清理项目根目录（默认）
scripts\clean_pycache.bat

# 清理指定目录
scripts\clean_pycache.bat "C:\Your\Project\Path"
```

### 方法2：使用 PowerShell 脚本（.ps1，推荐）

#### 右键运行
1. 右键点击 `clean_pycache.ps1`
2. 选择 "使用 PowerShell 运行"

#### PowerShell 命令行运行
```powershell
# 清理项目根目录（默认）
.\scripts\clean_pycache.ps1

# 清理指定目录
.\scripts\clean_pycache.ps1 -Path "C:\Your\Project\Path"
```

#### 如果遇到执行策略限制
```powershell
# 临时允许执行脚本（仅当前会话）
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 然后运行脚本
.\scripts\clean_pycache.ps1
```

## ✨ 功能特性

### 批处理脚本（.bat）
- ✅ 递归扫描所有子目录
- ✅ 删除所有 `__pycache__` 文件夹
- ✅ 显示删除进度和统计信息
- ✅ 错误处理（删除失败时显示警告）
- ✅ 自动暂停以查看结果

### PowerShell 脚本（.ps1）
- ✅ 所有批处理脚本的功能
- ✅ 彩色输出，更易阅读
- ✅ 更详细的错误信息
- ✅ 支持参数化路径
- ✅ 更好的错误处理

## 📊 输出示例

```
========================================
开始清理 __pycache__ 文件夹...
========================================

扫描目录: C:\Projects\intel_ec_ms

删除: C:\Projects\intel_ec_ms\services\gateway-service\app\__pycache__
删除: C:\Projects\intel_ec_ms\services\auth-service\app\__pycache__
删除: C:\Projects\intel_ec_ms\services\host-service\app\__pycache__
删除: C:\Projects\intel_ec_ms\shared\common\__pycache__

========================================
清理完成！
共删除 4 个 __pycache__ 文件夹
========================================
```

## ⚠️ 注意事项

1. **备份重要数据**：虽然脚本只删除 `__pycache__` 文件夹，但建议先备份重要数据
2. **权限问题**：如果某些文件夹被锁定或需要管理员权限，删除可能会失败
3. **Git 忽略**：`__pycache__` 文件夹已在 `.gitignore` 中，不会被提交到 Git
4. **重新生成**：删除后，Python 会在下次运行时自动重新生成这些缓存文件

## 🔧 故障排查

### 批处理脚本无法运行
- 确保文件路径中没有空格或特殊字符
- 尝试以管理员身份运行

### PowerShell 脚本无法运行
- 检查执行策略：`Get-ExecutionPolicy`
- 临时允许执行：`Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`

### 某些文件夹删除失败
- 检查文件夹是否被其他程序占用
- 尝试关闭所有 Python 进程后重新运行
- 检查文件权限

## 📝 相关文件

- `.gitignore` - 已配置忽略 `__pycache__/` 文件夹
- `scripts/clean_pycache.bat` - 批处理脚本
- `scripts/clean_pycache.ps1` - PowerShell 脚本

