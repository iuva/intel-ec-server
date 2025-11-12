"""
主机服务常量定义

定义主机相关的状态常量，避免在代码中使用魔法值。
"""

# ==================== 审批状态 (appr_state) ====================
# 审批状态枚举值
APPR_STATE_DISABLE = 0  # 停用
APPR_STATE_ENABLE = 1  # 启用
APPR_STATE_CHANGE = 2  # 存在改动

# ==================== 主机状态 (host_state) ====================
# 主机状态枚举值
HOST_STATE_FREE = 0  # 空闲
HOST_STATE_LOCKED = 1  # 已锁定
HOST_STATE_OCCUPIED = 2  # 已占用
HOST_STATE_RUNNING = 3  # case执行中
HOST_STATE_OFFLINE = 4  # 离线
HOST_STATE_INACTIVE = 5  # 待激活
HOST_STATE_HW_CHANGE = 6  # 存在潜在的硬件改动
HOST_STATE_DISABLED = 7  # 手动停用
HOST_STATE_UPDATING = 8  # 更新中

# ==================== 同步状态 (sync_state) ====================
# 硬件记录同步状态枚举值
SYNC_STATE_EMPTY = 0  # 空状态
SYNC_STATE_WAIT = 1  # 待同步
SYNC_STATE_SUCCESS = 2  # 通过
SYNC_STATE_FAILED = 3  # 异常
SYNC_STATE_APPROVED = 4  # 已审批（用于批量审批后的状态）

# ==================== 差异状态 (diff_state) ====================
# 硬件差异状态枚举值
DIFF_STATE_NONE = None  # 无差异
DIFF_STATE_VERSION = 1  # 版本号变化
DIFF_STATE_CONTENT = 2  # 内容更改
DIFF_STATE_FAILED = 3  # 异常

# ==================== Case 执行状态 (case_state) ====================
# Case 执行状态枚举值
CASE_STATE_FREE = 0  # 空闲
CASE_STATE_START = 1  # 启动
CASE_STATE_SUCCESS = 2  # 成功
CASE_STATE_FAILED = 3  # 失败

# ==================== TCP 状态 (tcp_state) ====================
# TCP 在线状态枚举值
TCP_STATE_CLOSE = 0  # 关闭
TCP_STATE_WAIT = 1  # 等待
TCP_STATE_LISTEN = 2  # 监听

# ==================== 删除标识 (del_flag) ====================
# 删除标识枚举值（继承自 BaseDBModel）
DEL_FLAG_USING = 0  # 使用中
DEL_FLAG_DELETED = 1  # 已删除
