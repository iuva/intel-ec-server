**覆盖范围**: 浏览器插件+ EC Server + Agent + 外部接口(EK/Hardware) + 中间件(Redis/DB)  
**设计依据**: 详细设计文档 v1.3

## 1. 测试前置准备 (Prerequisites)

在执行下列用例前，请确保环境满足：

1. **数据预埋**:
   
    - sys_conf: 包含标准的 hw_temp (硬件模板) 和 case_timeout (如 10分钟)。
      
    - host_rec: 预置状态为 0(空闲), 2(占用), 6(硬件变更) 的多台主机。
    
2. **Mock 服务**:
   
    - **Intel Auth**: 模拟 /rest/user 鉴权。
      
    - **Hardware API**: 模拟 /api/v1/hardware 的增删改，且支持**延时响应**（用于测并发锁）。

---

## 2. 测试用例矩阵

### 模块一：主机全生命周期管理

覆盖章节:
- **4.1.1** (主机管理状态机)
- **5.1.3 ~ 5.1.9** (插件接口)
- **5.3.2** (注册检测), **5.3.4** (状态上报)
- **5.4.2** (后台管理)
- **7.2** (WS心跳检查任务)

| ID              | 用例名称            | 前置条件               | 操作步骤                                                     | SIT 关键验证点 (API / DB / WS / Log)                         | 优先级 |
| --------------- | ------------------- | ---------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------ |
| **SIT-HOST-01** | 新主机自动注册      | DB无该主机             | 1. Agent 启动并调用 /api/v1/<font color="#ff0000">auth/device/login</font><br>2. 传入新 mg_id、<font color="#ff0000">username、host_ip</font> | 1. **API**: 返回新生成的<font color="#ff0000"> token</font><br>2. **DB (host_rec)**: 新增记录<br> - host_state = **5** (inact:待激活)<br> - appr_state = **1** (new:新增)<br> - del_flag = 0<br> | P0     |
| **SIT-HOST-02** | 主机活跃更新        | DB有该主机             | 1. 模拟 Agent 调用 /api/v1/<font color="#ff0000">auth/device/login</font><br>2. 传入新 mg_id、<font color="#ff0000">username、host_ip</font> | 1. **API**: 返回相同的 <font color="#ff0000">token</font><br>2. **DB (host_rec)**:<br> - updated_time 更新为当前时间<br> - 不产生新记录<br> | P0     |
| <font color="#ff0000">**SIT-HOST-03**</font> | 获取VNC连接(锁定)   | Host状态=0 (空闲)      | 1. 插件调用 /api/v1/<font color="#ff0000">host/vnc/connect</font><br>2. 传入 host_id<br> | 1. **API**: 返回 VNC IP/Port/Pwd<br>2. **DB (host_rec)**:<br> - host_state 变更为 **1** (lock:已锁定)<br> - subm_time 更新为当前时间<br> | P0     |
| <font color="#ff0000">**SIT-HOST-04**</font> | 释放主机资源        | Host状态=2 (占用)      | 1. 插件调用 /api/v1/<font color="#ff0000">host/hosts/release</font> | 1. **DB (host_exec_log)**: 逻辑删除记录（del_flag = 1）<br>2. **DB (host_rec)**: host_state **保持不变**（仍为2或3）<br>3. **注意**: 释放主机只是逻辑删除执行日志，不会自动重置主机状态 | P0     |
| **SIT-HOST-05** | VNC 历史重试        | 有历史连接             | 1. 插件调用 /api/v1/<font color="#ff0000">host/hosts/retry-vnc</font> | 1. **API**: 返回该用户最近连接过的 Host 列表<br>2. **DB**: 数据源应与 host_exec_log 或历史记录一致<br> | P1     |
| <font color="#ff0000">**SIT-HOST-06**</font> | 强制下线                | Host在线且空闲（host_state=0）         | 1. 管理员 POST /api/v1/<font color="#ff0000">host/admin/host/force-offline</font> | 1. **DB (host_rec)**:<br> - host_state = **4** (offline:离线)<br> - appr_state **保持不变**<br>2. **Redis**: 频道 websocket:unicast:{id} 收到消息<br>3. **WS**: 仅目标 Agent 收到下线指令 | P1     |
| **SIT-HOST-07** | WS心跳超时离线      | 建立连接               | 1. Agent 停止发送心跳 > 60s<br>2. 等待定时任务触发           | 1. **Log**: 服务端打印心跳超时警告<br>2. **DB (host_rec)**: host_state 变更为 **4** (offline:离线)<br>3. **Network**: 服务端主动关闭 TCP 连接 | P1     |
| **SIT-HOST-08** | 已删主机防御        | Host已删               | 1. DB del_flag=1<br>2. Agent 继续发请求                      | 1. **API**: 返回错误 (Host Not Found/Banned)<br>2. **DB**: del_flag 保持为 1，不会被重置 | P2     |
| **SIT-HOST-09** | 禁用主机连接防御    | Host禁用               | 1. host_state=7<br>2. 插件强行请求连接                       | 1. **API**: /api/v1/conn 返回 "主机已禁用"<br>2. **DB**: 状态无变化 | P2     |
| **SIT-HOST-10** | 获取可用主机列表    | 存在空闲/占用/离线主机 | 1. 插件调用 /api/v1/<font color="#ff0000">host/hosts/available</font><br>2. 传入 tc_id 等参数 | 1. **API**: 返回列表包含 Host A (空闲)<br>2. **Logic**: 验证列表**不包含** Host B (占用/离线/禁用)<br>3. **Data**: 返回的 user_name 等信息与 DB 一致 | P0     |
| **SIT-HOST-11** | 管理员删除主机      | Host存在               | 1. 管理员调用 DELETE /api/v1/<font color="#ff0000">host/admin/host/{host_id}</font> | 1. **DB (host_rec)**: del_flag = **1**<br>2. **DB (host_hw_rec)**: del_flag = **1** | P1     |
| **SIT-HOST-12** | 插件用户鉴权(Intel) | 未鉴权                 | 1. 插件启动/加载<br>2. 调用 Intel 用户信息接口               | 1. **API**: 返回 User Profile (User ID/Email)<br>2. **Logic**: 验证系统能正确识别 Intel 用户身份 | P0     |

### 模块二：硬件审核与混合事务 

覆盖章节:
- **4.1.2** (硬件审核流程)
- **5.3.3** (硬件上报)
- **5.4.3** (审批管理)
- **6.1** (外部Token缓存)
- **6.5** (分布式锁)
- **Mongo-MariaDB 交互图**

| ID            | 用例名称          | 前置条件         | 操作步骤                                                  | SIT 关键验证点 (API / DB / WS / Log)                                                                                                                                                                 | 优先级 |
| ------------- | ------------- | ------------ | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| **SIT-HW-01** | 启动初始化检测(版本变更) | Agent重启/新启动  | 1. Agent 启动时调用上报接口<br>2. revision 大于 DB 中当前版本<br>     | 1. **DB (host_hw_rec)**: 新增记录, diff_state=**1** (ver_diff)<br>2. **DB (host_rec)**: host_state=**6** (hw_chg), appr_state=**2** (change)                                                        | P0  |
| **SIT-HW-02** | 被动通知检测(内容变更)  | Host运行中(无任务) | 1. HW 工具推送变更通知<br>2. revision 不变，但 dmr_config 内容变化    | 1. **DB (host_hw_rec)**: 新增记录, diff_state=**2** (item_diff)<br>2. **DB (host_rec)**: 状态变更为 **6** (hw_chg)<br>3. **UI**: 后台主机列表显示该主机为“硬件变更”待审批状态                                                 | P1  |
| **SIT-HW-03** | 24h定时检测(无变更)  | 距上次检测>24h    | 1. Agent 触发定时检测逻辑<br>2. 上报数据与当前一致                     | 1. **API**: 返回 "无变化"<br>2. **DB (host_rec)**: updated_time 更新 (表示存活)，**不新增** host_hw_rec 记录<br>3. **Log**: 记录一次定期检测完成                                                                           | P1  |
| **SIT-HW-04** | 24h定时检测(有变更)  | 距上次检测>24h    | 1. Agent 触发定时检测<br>2. 上报数据有变更                         | 1. **DB**: 同样触发 host_state=**6** <br>2. **UI**: 后台主机列表显示该主机为“硬件变更”待审批状态                                                                                                                         | P1  |
| **SIT-HW-05** | 异常类型上报        | Agent检测硬件失败  | 1. Agent 调用上报接口，type=**1**<br>2. dmr_config 可为空或包含错误码 | 1. **DB (host_hw_rec)**:<br> - diff_state=**3** (failed:异常)<br> - sync_state=**1** (wait)<br>2. **UI**: 后台主机列表显示该主机为“硬件异常”待审批状态                                                                 | P1  |
| **SIT-HW-06** | 审批同意(新增)      | 无 HardwareID | 1. 管理员调用审批同意接口<br>2. 外部接口返回新 MongoID                  | 1. **Redis**: hardware_create_lock:{host_id} 锁曾被创建<br>2. **DB (host_hw_rec)**: sync_state=**2**, hardware_id=MongoID<br>3. **DB (host_rec)**: host_state=**0**, hw_id=关联ID, hardware_id=MongoID | P0  |
| **SIT-HW-07** | 审批同意(修改)      | 有 HardwareID | 1. 管理员调用审批同意接口                                        | 1. **DB (host_hw_rec)**: sync_state=**2** (success)<br>2. **DB (host_rec)**: host_state=**0** (free)                                                                                            | P0  |
| **SIT-HW-08** | 审批拒绝          | 待审批          | 1. 管理员调用拒绝接口                                          | 1. **DB (host_rec)**: appr_state = **0** (disable)<br>2. **DB (host_hw_rec)**: sync_state = **3** (failed/rejected)                                                                             | P1  |
| **SIT-HW-09** | 分布式锁失效验证      | 并发场景         | 1. 模拟双线程并发审批同一 Host<br>2. Mock 外部 API 耗时 > 30s        | 1. **Logic**: 只能有一次成功的外部 API 调用<br>2. **DB**: 严禁生成两条 sync_state=2 的重复记录<br>3. **Redis**: 验证 Lock Key 存在且 TTL 正常<br>                                                                             | P1  |
| **SIT-HW-10** | 外部Token自动续期   | Token快过期     | 1. 设置 Redis external_api_token 1s后过期<br>2. 触发审批操作<br> | 1. **Log**: 观察到系统重新调用了 /auth/login<br>2. **Redis**: Token 值更新，TTL 重置<br>                                                                                                                        | P3  |
| **SIT-HW-11** | 超大硬件包体测试      | -            | 1. Agent 上报 5MB JSON                                  | 1. **API**: 能够接收或返回 413 (按配置)<br>2. **Logic**: JSON 比对工具无内存溢出(OOM)                                                                                                                              | P2  |

### 模块三：任务执行与监控 

覆盖章节:
- **4.1.3** (任务模块)
- **5.3.5** (结果上报)
- **5.3.7** (WS下发)
- <font color="#ff0000">**7.1** (Case超时检测)</font>
- **DB**: host_exec_log

| ID              | 用例名称                                | 前置条件    | 操作步骤                                           | SIT 关键验证点 (API / DB / WS / Log)                                                                                                                                           | 优先级 |
| --------------- | ----------------------------------- | ------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| **SIT-TASK-01** | 任务启动与下发                             | Host连接中 | 1. 触发任务执行<br>2. Agent 上报启动状态                   | 1. **WS**: 收到 type=case_param, 包含 tc_id 等<br>2. **DB (host_exec_log)**: 新增记录, case_state=**1** (start)<br>3. **DB (host_rec)**: host_state=**3** (run)                    | P0  |
| **SIT-TASK-02** | 任务成功回执                              | 任务执行中   | 1.Agent接收到EK回调 <br>2.Agent 上报成功                | 1. **DB (host_exec_log)**:<br>- case_state = **2** (success)<br>- result_msg 非空, log_url 非空<br>- end_time 更新                                                              | P0  |
| **SIT-TASK-03** | 任务失败回执                              | 任务执行中   | 1. Agent 上报失败 (含错误详情)                          | 1. **DB (host_exec_log)**:<br> - case_state = **3** (failed)<br> - err_msg 字段存入 JSON 格式错误信息                                                                               | P0  |
| <font color="#ff0000">**SIT-TASK-04**</font> | <font color="#ff0000">任务超时监控</font> | 构造超时数据  | 1. 修改 DB begin_time 为 2小时前<br>2. 等待/触发定时任务<br> | 1. **Redis**: 读取 sys_conf:case_timeout 配置<br>2. **Email**: 发送超时邮件通知<br>3. **DB (host_exec_log)**: notify_state 更新为 **1** (已通知)<br>4. **注意**: 任务超时检测只发送邮件通知，不会自动重置主机状态或发送WS终止指令 | P1  |

### 模块四：OTA 升级与配置

覆盖章节: 
- **5.2.4 (C)** (Agent更新)
- **5.3.6** (更新上报)
- **5.4.4** (OTA管理)
- **6.4** (Redis广播)

| ID             | 用例名称    | 前置条件     | 操作步骤                          | SIT 关键验证点 (API / DB / WS / Log)                                                                                                                                                               | 优先级 |
| -------------- | ------- | -------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| **SIT-OTA-01** | 强制更新广播  | 多Agent在线 | 1. Admin 下发 force_update=true | 1. **Redis**: websocket:broadcast 频道发布消息<br>2. **WS**: 所有在线 Agent 收到 upd_app 指令<br>3. **DB (host_upd)**: 新增记录, app_state=**0** (pre-upd)<br>4. **DB (host_rec)**: host_state=**8** (updating) | P0  |
| **SIT-OTA-02** | 更新中状态上报 | 收到更新指令   | 1. Agent 上报 biz_state=1       | 1. **DB (host_upd)**: app_state=**1** (updating)                                                                                                                                              | P1  |
| **SIT-OTA-03** | 更新成功    | 更新中      | 1. Agent 上报 biz_state=2       | 1. **DB (host_upd)**: app_state=**2** (success)<br>2. **DB (host_rec)**: host_state=**0** (free), agent_ver=新版本                                                                               | P2  |
| **SIT-OTA-04** | 更新失败    | 更新中      | 1. Agent 上报 biz_state=3       | 1. **DB (host_upd)**: app_state=**3** (failed)<br>2. **Log**: 记录更新失败日志                                                                                                                        | P2  |
| **SIT-OTA-05** | OTA配置查询 | -        | 1. Admin 查询 OTA 列表            | 1. **API**: 返回包含 biz_key, biz_ver, biz_url 的列表                                                                                                                                                | P2  |

### 模块五：安全与基础设施

| ID             | 用例名称       | 前置条件      | 操作步骤                       | SIT 关键验证点 (API / DB / WS / Log)                                                             | 优先级 |
| -------------- | ---------- | --------- | -------------------------- | ------------------------------------------------------------------------------------------- | --- |
| **SIT-INF-01** | 连接池健康检查    | -         | 1. 模拟 DB 连接断开<br>2. 等待 30s | 1. **Task**: 健康检查任务剔除无效连接并重连<br>2. **Log**: 记录连接池活动<br>                                     | P2  |
| **SIT-INF-02** | Redis 宕机降级 | Redis服务断开 | 1. 调用列表查询接口                | 1. **API**: 仍能返回 DB 中的数据 (降级成功)<br>2. **Log**: 记录 Redis 连接异常，系统未 Crash                      | P1  |
| **SIT-INF-03** | 维护通知邮件     | -         | 1. 调用通知接口                  | 1. **Mock Email**: 收到邮件发送请求                                                                 | P3  |
| **SIT-ADM-01** | 管理员登录校验    | -         | 1. 输入错误/正确密码               | 1. **sys_user**: 验证 user_account 与 user_pwd<br>2. **Logic**: 校验 state_flag=**0**，若为 1 则禁止登录 | P0  |
