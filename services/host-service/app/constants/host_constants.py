"""
Host service constants definition

Defines host-related state constants to avoid using magic values in code.
"""

# ==================== Approval State (appr_state) ====================
# Approval state enumeration values
APPR_STATE_DISABLE = 0  # Disabled
APPR_STATE_ENABLE = 1  # Enabled
APPR_STATE_CHANGE = 2  # Has changes

# ==================== Host State (host_state) ====================
# Host state enumeration values
HOST_STATE_FREE = 0  # Free
HOST_STATE_LOCKED = 1  # Locked
HOST_STATE_OCCUPIED = 2  # Occupied
HOST_STATE_RUNNING = 3  # Case executing
HOST_STATE_OFFLINE = 4  # Offline
HOST_STATE_INACTIVE = 5  # Pending activation
HOST_STATE_HW_CHANGE = 6  # Has potential hardware changes
HOST_STATE_DISABLED = 7  # Manually disabled
HOST_STATE_UPDATING = 8  # Updating

# ==================== Sync State (sync_state) ====================
# Hardware record sync state enumeration values
SYNC_STATE_EMPTY = 0  # Empty state
SYNC_STATE_WAIT = 1  # Pending sync
SYNC_STATE_SUCCESS = 2  # Passed
SYNC_STATE_FAILED = 3  # Exception
SYNC_STATE_APPROVED = 4  # Approved (used for state after batch approval)

# ==================== Diff State (diff_state) ====================
# Hardware diff state enumeration values
DIFF_STATE_NONE = None  # No diff
DIFF_STATE_VERSION = 1  # Version changed
DIFF_STATE_CONTENT = 2  # Content changed
DIFF_STATE_FAILED = 3  # Exception

# ==================== Case Execution State (case_state) ====================
# Case execution state enumeration values
CASE_STATE_FREE = 0  # Free
CASE_STATE_START = 1  # Started
CASE_STATE_SUCCESS = 2  # Success
CASE_STATE_FAILED = 3  # Failed

# ==================== TCP State (tcp_state) ====================
# TCP online state enumeration values
TCP_STATE_CLOSE = 0  # Closed
TCP_STATE_WAIT = 1  # Waiting
TCP_STATE_LISTEN = 2  # Listening

# ==================== Delete Flag (del_flag) ====================
# Delete flag enumeration values (inherited from BaseDBModel)
DEL_FLAG_USING = 0  # In use
DEL_FLAG_DELETED = 1  # Deleted
