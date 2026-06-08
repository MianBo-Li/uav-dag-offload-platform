# 项目学习记录

## 1. 文档目的

本文档用于记录“面向无人机边缘计算的 DAG 任务卸载调度系统”的学习过程。

它不是单纯的开发日志，而是把每个阶段学到的工程知识沉淀下来，包括：

- 为什么要做这个功能。
- 这个功能属于项目生命周期的哪一步。
- 代码放在哪一层。
- 测试如何证明它是正确的。
- 当前实现还有哪些边界。
- 下一步应该继续学习什么。

后续每完成一个重要功能，都应继续更新本文档。

## 2. 当前项目目标

项目方向：

```text
面向无人机边缘计算的 DAG 任务卸载调度系统
```

核心场景：

多架无人机执行巡检、监测、图像采集、目标检测等任务。一个任务由多个有依赖关系的子任务组成，系统根据无人机状态、边缘节点状态、DAG 依赖关系和调度策略，决定每个子任务在无人机本地执行，还是卸载到边缘节点执行。

学习目标：

```text
项目提出 -> 需求分析 -> 系统设计 -> 数据库设计 -> API 设计
-> 后端实现 -> 自动化测试 -> Docker 部署 -> 监控与算法对比
```

第一阶段技术栈：

- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Alembic
- Redis
- pytest
- ruff

## 3. 已完成的文档阶段

### 3.1 Git 工作流

文档：

- [00_git_workflow.md](00_git_workflow.md)

学到的内容：

- Git 用来记录项目演进，而不只是“保存代码”。
- 分支用于隔离不同阶段的工作。
- Worktree 适合同时保留多个分支的工作目录。
- 学习项目不需要每个小改动都提交，应该在阶段性成果完成后再提交和 PR。

当前约定：

- 学习探索阶段：先实现、讲解、测试，不频繁提交。
- 到达清晰里程碑后：再整理、提交、推送、PR。

### 3.2 项目立项

文档：

- [01_project_proposal.md](01_project_proposal.md)

学到的内容：

- 项目立项要回答“为什么做、做什么、输入是什么、输出是什么、如何验收”。
- 本项目不是单纯 CRUD 后端，而是包含调度算法、状态流转、执行模拟和指标分析。
- 第一阶段目标不是一次性做成复杂分布式系统，而是先打通真实后端闭环。

### 3.3 学习路线

文档：

- [02_learning_roadmap.md](02_learning_roadmap.md)

学到的内容：

- 学习路线应先闭环，再增强。
- 不应一开始就引入所有复杂技术。
- 对本项目来说，最小闭环是：

```text
注册节点
-> 上报状态
-> 创建 DAG 任务
-> 校验 DAG
-> 生成调度计划
-> 模拟执行
-> 回传结果
-> 查询指标
```

### 3.4 需求分析

文档：

- [03_requirements_analysis.md](03_requirements_analysis.md)

学到的内容：

- 需求分析要区分角色、主流程、功能需求和异常场景。
- 本系统的角色包括：
  - 任务用户
  - 节点 Agent
  - 调度器
  - 系统管理员
- 第一阶段验收场景：

```text
注册 1 架无人机和 1 个边缘节点
-> 上报状态
-> 提交 5 个子任务 DAG
-> 使用贪心策略生成计划
-> Worker 执行
-> 最终任务 SUCCESS
-> 查询每个子任务执行节点、耗时和结果
```

### 3.5 系统设计

文档：

- [04_system_design.md](04_system_design.md)

学到的内容：

- 第一阶段采用模块化单体架构。
- 模块边界包括：
  - 节点管理
  - DAG 任务
  - 调度
  - 执行
  - 评估
  - 平台管理
- 调度策略应可插拔，便于后续比较不同算法。

### 3.6 数据库设计

文档：

- [05_database_design.md](05_database_design.md)

学到的内容：

- PostgreSQL 是核心事实来源。
- Redis 只保存可重建的临时状态。
- 调度计划和执行记录要分开：

```text
schedule_plan_items 表示“计划让谁执行”
execution_records 表示“实际怎么执行”
```

这个区分很重要，因为后续可以比较计划耗时和实际耗时。

### 3.7 API 设计

文档：

- [06_api_design.md](06_api_design.md)

学到的内容：

- API 设计要提前统一：
  - URL 风格
  - 请求字段
  - 响应字段
  - 错误格式
  - 分页格式
  - 状态码含义
- 常见状态码约定：

```text
201: 创建成功
400: 业务语义错误
404: 资源不存在
409: 状态冲突
422: 请求格式或参数校验失败
```

### 3.8 状态机设计

文档：

- [07_state_machine_design.md](07_state_machine_design.md)

学到的内容：

- 任务、子任务、节点、调度计划、执行记录都需要显式状态。
- 状态变化不应散落在 API 层，而应由 Service 层统一管理。
- 当前任务状态流转包括：

```text
PENDING -> SCHEDULED -> RUNNING -> SUCCESS
PENDING -> CANCELED
SCHEDULED -> CANCELED
RUNNING -> FAILED
```

### 3.9 后端骨架计划

文档：

- [08_backend_scaffold_plan.md](08_backend_scaffold_plan.md)

学到的内容：

- 后端目录要按职责分层，而不是所有代码都放在一个文件里。
- 当前采用的分层：

```text
api         HTTP 路由层
schemas     Pydantic 请求/响应模型
services    业务用例层
repositories 数据访问层
db/models   SQLAlchemy ORM 模型
domain      纯业务规则
scheduler   调度策略
tests       自动化测试
```

## 4. 环境与工具学习

### 4.1 虚拟环境

学到的内容：

- Python 虚拟环境用于隔离项目依赖，不会污染本机全局 Python。
- 项目内 `.venv` 可以和本项目绑定。
- 使用命令时，更稳定的方式是：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app tests alembic
```

原因：

直接运行 `pytest` 可能因为终端没有激活虚拟环境而找不到命令。

### 4.2 Docker 与数据库

学到的内容：

- 后端项目最终需要真实 PostgreSQL。
- 但自动化测试阶段可以先用 SQLite 内存数据库跑集成测试。
- Docker Desktop 未启动时，连接 Docker API 会失败。
- 本项目当前测试不依赖 Docker，因此可以继续学习和开发。

### 4.3 GitHub 与 PR

学到的内容：

- GitHub 上看不到项目，通常是因为本地仓库还没有推送到远程，或者远程仓库地址未绑定。
- PR 适合阶段性汇总，不适合每个小学习点都提交。
- 当前学习节奏：

```text
先学习和实现
-> 跑测试
-> 讲解
-> 到阶段节点再提交 PR
```

## 5. 后端分层学习

### 5.1 API 层

代表文件：

- [app/api/v1/endpoints/tasks.py](../app/api/v1/endpoints/tasks.py)
- [app/api/v1/endpoints/nodes.py](../app/api/v1/endpoints/nodes.py)

职责：

- 接收 HTTP 请求。
- 声明路径参数、查询参数和请求体。
- 调用 Service。
- 提交事务。
- 返回响应模型。

不应该做的事：

- 不直接写复杂业务逻辑。
- 不直接散落 SQL 查询。
- 不绕过状态机直接改状态。

### 5.2 Schema 层

代表文件：

- [app/schemas/task.py](../app/schemas/task.py)
- [app/schemas/node.py](../app/schemas/node.py)
- [app/schemas/schedule.py](../app/schemas/schedule.py)

职责：

- 定义请求体和响应体。
- 使用 Pydantic 做字段校验。
- 让非法输入在进入业务层之前被拦截。

典型例子：

```text
task_id: UUID -> 非法 UUID 返回 422
page: Query(ge=1) -> page=0 返回 422
status: TaskStatus -> 非法枚举返回 422
```

### 5.3 Service 层

代表文件：

- [app/services/task_service.py](../app/services/task_service.py)
- [app/services/node_service.py](../app/services/node_service.py)
- [app/services/scheduling_service.py](../app/services/scheduling_service.py)

职责：

- 组织完整业务用例。
- 调用 Repository 查询和保存数据。
- 调用 Domain 规则或 Scheduler 算法。
- 把底层异常转换成统一的 `AppError`。

典型例子：

```text
SchedulingService.generate_plan()
-> 读取任务
-> 检查任务状态是否允许调度
-> 读取节点快照
-> 调用 GreedyScheduler
-> 保存调度计划
-> 更新任务状态为 SCHEDULED
```

### 5.4 Repository 层

代表文件：

- [app/repositories/task_repository.py](../app/repositories/task_repository.py)
- [app/repositories/node_repository.py](../app/repositories/node_repository.py)
- [app/repositories/schedule_repository.py](../app/repositories/schedule_repository.py)

职责：

- 封装 SQLAlchemy 查询。
- 让 Service 关心“要什么数据”，而不是“SQL 怎么写”。

### 5.5 Domain 层

代表文件：

- [app/domain/dag.py](../app/domain/dag.py)
- [app/domain/state_machine.py](../app/domain/state_machine.py)
- [app/domain/enums.py](../app/domain/enums.py)

职责：

- 放最稳定的纯业务规则。
- 不依赖 FastAPI。
- 不依赖数据库 Session。
- 最适合做单元测试。

已实现规则：

- DAG 合法性校验。
- 状态机迁移校验。
- 任务、子任务、节点、调度计划枚举。

### 5.6 Scheduler 层

代表文件：

- [app/scheduler/base.py](../app/scheduler/base.py)
- [app/scheduler/greedy.py](../app/scheduler/greedy.py)

职责：

- 定义调度器输入输出合同。
- 实现调度策略。
- 不直接查数据库。

当前调度输入：

```text
SchedulableSubtask
NodeSnapshot
```

当前调度输出：

```text
SchedulePlan
SchedulePlanItem
```

## 6. 已完成的功能学习

### 6.1 健康检查

已完成：

```text
GET /api/v1/health
```

学到的内容：

- 后端服务需要最小健康检查接口。
- 后续可以扩展数据库、Redis、队列等依赖检查。

### 6.2 节点注册

已完成：

```text
POST /api/v1/nodes
GET /api/v1/nodes
GET /api/v1/nodes/{node_id}
```

学到的内容：

- 如何用 FastAPI 定义 REST 接口。
- 如何用 Pydantic 校验节点类型、CPU、内存等字段。
- 如何处理重复节点名，返回 `409 NODE_NAME_CONFLICT`。

### 6.3 节点状态上报

已完成：

```text
POST /api/v1/nodes/{node_id}/status
GET /api/v1/nodes/{node_id}/status-records
```

学到的内容：

- 节点当前状态和历史状态要分开。
- `nodes.status` 表示当前快速查询状态。
- `node_status_records` 保存每次上报历史。
- 高 CPU、高内存、高队列长度会让节点变成 `BUSY`。

### 6.4 DAG 任务创建

已完成：

```text
POST /api/v1/tasks
```

学到的内容：

- 创建 DAG 任务时必须在一个事务中保存：
  - 总任务
  - 子任务
  - 依赖关系
- DAG 校验失败时不应保存任何数据。
- 入度为 0 的子任务初始状态是 `READY`。
- 有前置依赖的子任务初始状态是 `WAITING`。

### 6.5 DAG 合法性校验

代表文件：

- [app/domain/dag.py](../app/domain/dag.py)
- [tests/domain/test_dag.py](../tests/domain/test_dag.py)

已学习：

- 空 DAG 不合法。
- 子任务 ID 不能重复。
- 依赖不能引用不存在的子任务。
- 子任务不能依赖自己。
- DAG 不能有环。

### 6.6 任务详情与子任务查询

已完成：

```text
GET /api/v1/tasks/{task_id}
GET /api/v1/tasks/{task_id}/subtasks
```

学到的内容：

- 查询详情时需要同时返回子任务和依赖关系。
- 查询子任务列表时支持：
  - 按状态过滤。
  - 分页。
  - 未知任务返回 `404 TASK_NOT_FOUND`。

### 6.7 请求校验与错误边界

已学习：

```text
422: 请求格式错误，由 FastAPI/Pydantic 处理
404: 资源不存在，由 Service 处理
409: 当前状态不允许操作，由状态机/Service 处理
400: 业务语义错误，如 DAG 有环或策略不存在
```

典型例子：

```text
GET /api/v1/tasks/not-a-uuid -> 422
GET /api/v1/tasks/{合法但不存在的 UUID} -> 404
重复取消任务 -> 409
未知调度策略 -> 400
```

### 6.8 任务取消

已完成：

```text
POST /api/v1/tasks/{task_id}/cancel
```

学到的内容：

- 取消任务是状态机问题，不只是改字段。
- `PENDING`、`SCHEDULED`、`RUNNING` 可以取消。
- 已经 `CANCELED` 的任务再次取消，应返回 `409 TASK_STATE_CONFLICT`。
- 当前阶段只取消总任务，不强行修改所有子任务状态。

### 6.9 数据库 Session 与 rollback

代表文件：

- [app/db/session.py](../app/db/session.py)
- [tests/conftest.py](../tests/conftest.py)

学到的内容：

- API 成功时：

```text
service 执行业务
-> endpoint db.commit()
-> close session
```

- API 失败时：

```text
异常抛出
-> get_db rollback()
-> close session
```

- Service 层通常 `flush`，API 层负责 `commit`。

### 6.10 贪心调度器

代表文件：

- [app/scheduler/base.py](../app/scheduler/base.py)
- [app/scheduler/greedy.py](../app/scheduler/greedy.py)
- [tests/scheduler/test_greedy_scheduler.py](../tests/scheduler/test_greedy_scheduler.py)

学到的内容：

- 调度器不直接依赖数据库。
- 调度器吃快照对象，输出内存中的计划。
- 成本模型：

```text
score = compute_duration + transfer_duration + energy_cost_weight * energy
```

- 贪心策略对每个 READY 子任务选择当前成本最低的节点。

### 6.11 本地执行约束

已完成：

```text
SubtaskExecutionConstraint
OFFLOADABLE
LOCAL_ONLY
EDGE_ONLY
```

学到的内容：

- 真实业务规则会推动数据模型变化。
- 图像采集、传感器读取等任务不能简单按成本卸载。
- 硬约束优先于成本最优：

```text
LOCAL_ONLY -> 只能选择 UAV
EDGE_ONLY -> 只能选择 EDGE
OFFLOADABLE -> UAV 和 EDGE 都可选
```

这个需求贯穿了：

```text
枚举
-> API Schema
-> ORM 模型
-> Alembic 迁移
-> TaskService 保存
-> SchedulingService 传递
-> GreedyScheduler 决策
-> 测试验证
```

### 6.12 SchedulingService

代表文件：

- [app/services/scheduling_service.py](../app/services/scheduling_service.py)
- [tests/services/test_scheduling_service.py](../tests/services/test_scheduling_service.py)

已完成：

```text
从数据库读取任务
-> 找 READY 子任务
-> 读取 ONLINE 节点和最近状态
-> 组装 SchedulableSubtask / NodeSnapshot
-> 调用 GreedyScheduler
-> 保存调度计划
-> 更新任务状态为 SCHEDULED
```

学到的内容：

- Service 层连接数据库世界和算法世界。
- 算法不关心 SQLAlchemy。
- 数据库对象要转换成调度器快照对象。

### 6.13 调度计划持久化

已完成：

```text
schedule_plans
schedule_plan_items
```

代表文件：

- [app/db/models/task.py](../app/db/models/task.py)
- [app/repositories/schedule_repository.py](../app/repositories/schedule_repository.py)
- [alembic/versions/20260531_0004_create_schedule_plan_tables.py](../alembic/versions/20260531_0004_create_schedule_plan_tables.py)

学到的内容：

- 内存计划不能作为系统事实来源。
- 调度结果必须落库，后续执行模块才能读取。
- 任务调度成功后，状态从 `PENDING` 变成 `SCHEDULED`。
- 重复调度已 `SCHEDULED` 任务应返回 `409`。

### 6.14 调度 API

已完成：

```text
POST /api/v1/tasks/{task_id}/schedule
```

代表文件：

- [app/api/v1/endpoints/tasks.py](../app/api/v1/endpoints/tasks.py)
- [app/schemas/schedule.py](../app/schemas/schedule.py)

学到的内容：

- API 层负责把 HTTP 请求转换成 Service 调用。
- API 层不写调度算法。
- 调度成功后提交事务。
- 响应返回调度计划和调度项。

当前主链路已经达到：

```text
注册节点
-> 上报节点状态
-> 创建 DAG 任务
-> 触发调度
-> 保存调度计划
-> 任务变为 SCHEDULED
```

### 6.15 调度计划查询

已完成：

```text
GET /api/v1/tasks/{task_id}/schedules
GET /api/v1/schedules/{schedule_plan_id}
```

代表文件：

- [app/api/v1/endpoints/tasks.py](../app/api/v1/endpoints/tasks.py)
- [app/api/v1/endpoints/schedules.py](../app/api/v1/endpoints/schedules.py)
- [app/repositories/schedule_repository.py](../app/repositories/schedule_repository.py)
- [app/schemas/schedule.py](../app/schemas/schedule.py)

学到的内容：

- 一个资源可以有两类查询入口：
  - 从父资源下查询列表：`/tasks/{task_id}/schedules`
  - 从资源自身查询详情：`/schedules/{schedule_plan_id}`
- 列表接口适合返回概要信息和分页字段。
- 详情接口适合返回调度计划明细。
- 查询任务下的调度计划前，应先确认任务存在。
- 查询不存在的调度计划，应返回 `404 SCHEDULE_PLAN_NOT_FOUND`。

### 6.16 模拟执行启动

已完成：

```text
POST /api/v1/tasks/{task_id}/execute
```

代表文件：

- [app/api/v1/endpoints/tasks.py](../app/api/v1/endpoints/tasks.py)
- [app/db/models/task.py](../app/db/models/task.py)
- [app/repositories/execution_repository.py](../app/repositories/execution_repository.py)
- [app/schemas/execution.py](../app/schemas/execution.py)
- [app/services/execution_service.py](../app/services/execution_service.py)
- [alembic/versions/20260531_0005_create_execution_records.py](../alembic/versions/20260531_0005_create_execution_records.py)

学到的内容：

- 调度计划表示“计划让谁执行”，执行记录表示“实际启动了一次执行尝试”。
- 启动执行前必须检查任务状态：

```text
SCHEDULED -> RUNNING
```

- 启动执行前必须检查调度计划状态：

```text
GENERATED -> APPLIED
```

- 模拟执行启动时，计划中的子任务会从可执行状态进入运行状态：

```text
READY -> DISPATCHED -> RUNNING
```

- 启动执行只负责把计划中的子任务变成运行中，不负责判断最终成功或失败。
- 成功启动后会创建 `execution_records`，并把任务状态改为 `RUNNING`。

### 6.17 执行结果回传

已完成：

```text
POST /api/v1/executions/{execution_id}/result
```

代表文件：

- [app/api/v1/endpoints/executions.py](../app/api/v1/endpoints/executions.py)
- [app/repositories/execution_repository.py](../app/repositories/execution_repository.py)
- [app/schemas/execution.py](../app/schemas/execution.py)
- [app/services/execution_service.py](../app/services/execution_service.py)
- [tests/api/test_tasks.py](../tests/api/test_tasks.py)

学到的内容：

- 执行结果回传是 Worker 或节点 Agent 向后端报告执行结果的入口。
- 回传成功时，执行记录从 `RUNNING` 变成 `SUCCESS`，对应子任务也从 `RUNNING` 变成 `SUCCESS`。
- 子任务成功后，要检查它的后继子任务是否所有前驱都已经成功；如果是，就把后继子任务从 `WAITING` 推进到 `READY`。
- 如果所有子任务都成功，总任务可以从 `RUNNING` 聚合为 `SUCCESS`。
- 回传失败、超时或取消时，对应子任务进入 `FAILED`，总任务也进入 `FAILED`。
- 重复回传不应该重复修改状态；当前实现会返回 `accepted=false`，表示这个结果没有再次被采纳。

当前主链路已经推进到：

```text
注册节点
-> 上报状态
-> 创建 DAG
-> 生成调度计划
-> 启动模拟执行
-> 回传执行结果
-> 解锁后继子任务或结束任务
-> 查询执行记录
```

### 6.18 执行记录查询

已完成：

```text
GET /api/v1/tasks/{task_id}/executions
```

代表文件：

- [app/api/v1/endpoints/tasks.py](../app/api/v1/endpoints/tasks.py)
- [app/repositories/execution_repository.py](../app/repositories/execution_repository.py)
- [app/schemas/execution.py](../app/schemas/execution.py)
- [app/services/execution_service.py](../app/services/execution_service.py)
- [tests/api/test_tasks.py](../tests/api/test_tasks.py)

学到的内容：

- 执行记录查询是典型的“读路径”：不改变状态，只读取事实。
- 列表接口需要分页，避免执行记录越来越多时一次返回过大数据。
- 状态过滤可以帮助用户只查看 `RUNNING`、`SUCCESS`、`FAILED` 等某类执行尝试。
- 查询任务下的执行记录前，仍然要先确认任务存在；未知任务返回 `404 TASK_NOT_FOUND`。
- API 层只接收分页和过滤参数，Service 层负责业务校验，Repository 层封装 SQL 查询。

### 6.19 后继子任务继续调度/执行

已完成：

```text
POST /api/v1/tasks/{task_id}/schedule
POST /api/v1/tasks/{task_id}/execute
```

这两个接口现在不仅支持第一轮调度和执行，也支持任务进入 `RUNNING` 后继续为新解锁的 `READY` 子任务生成下一轮调度计划并启动执行。

代表文件：

- [app/services/scheduling_service.py](../app/services/scheduling_service.py)
- [app/services/execution_service.py](../app/services/execution_service.py)
- [tests/api/test_tasks.py](../tests/api/test_tasks.py)

学到的内容：

- 一个 DAG 任务不会一次性把所有子任务都执行；只有前驱完成后，后继子任务才会从 `WAITING` 变成 `READY`。
- 第一轮调度发生在任务 `PENDING` 时，调度成功后任务进入 `SCHEDULED`。
- 后续调度发生在任务 `RUNNING` 时，只为当前新出现的 `READY` 子任务生成计划，任务本身继续保持 `RUNNING`。
- 启动后续执行时，任务不需要再次经历 `SCHEDULED -> RUNNING`，因为它已经处在运行中的总任务生命周期里。
- 这一步让系统从“一次性执行第一个子任务”，推进到“可以按 DAG 依赖逐层推进执行”。

### 6.20 完整 DAG 成功闭环

已完成：

```text
capture_image
-> detect_target
-> upload_report
-> task SUCCESS
```

代表文件：

- [tests/api/test_tasks.py](../tests/api/test_tasks.py)
- [app/services/execution_service.py](../app/services/execution_service.py)
- [app/services/scheduling_service.py](../app/services/scheduling_service.py)

学到的内容：

- 完整闭环测试不是只验证某一个接口，而是验证多个接口组合后的业务结果。
- 每一轮都遵循同一个节奏：

```text
查询当前 READY 子任务
-> 生成调度计划
-> 启动执行
-> 回传 SUCCESS
-> 解锁下一层子任务
```

- 当前驱子任务全部成功后，后继子任务才会变成 `READY`。
- 当最后一个子任务也成功后，Service 会聚合所有子任务状态，并把总任务从 `RUNNING` 推进到 `SUCCESS`。
- 这一步说明第一阶段的主业务链路已经可以从任务创建一直跑到任务成功完成。

### 6.21 指标统计

已完成：

```text
GET /api/v1/tasks/{task_id}/metrics
```

代表文件：

- [app/api/v1/endpoints/tasks.py](../app/api/v1/endpoints/tasks.py)
- [app/repositories/execution_repository.py](../app/repositories/execution_repository.py)
- [app/schemas/metrics.py](../app/schemas/metrics.py)
- [app/services/metrics_service.py](../app/services/metrics_service.py)
- [tests/api/test_tasks.py](../tests/api/test_tasks.py)

当前统计内容：

- 子任务总数、成功数、失败数、运行中数量。
- 执行记录总数、成功数、失败数、运行中数量。
- 成功率和失败率。
- 执行记录总耗时和平均耗时。
- UAV 本地执行次数。
- EDGE 边缘执行次数。
- 卸载执行比例。
- 任务整体 elapsed time。

学到的内容：

- 指标统计不是新事实来源，而是基于已有事实表聚合出来的读模型。
- 当前事实来源主要是：

```text
dag_tasks
dag_subtasks
execution_records
nodes
```

- `execution_records` 负责说明实际执行了几次、每次状态和耗时。
- `nodes` 负责说明执行发生在 UAV 还是 EDGE，因此可以计算本地/边缘比例。
- 没有执行记录时，成功率和失败率都返回 `0.0`，平均耗时返回 `null`，避免制造虚假的平均值。

### 6.22 Docker Compose 本地开发环境

已完成：

```text
Dockerfile
docker-compose.yml
.dockerignore
docs/10_docker_compose.md
```

代表文件：

- [Dockerfile](../Dockerfile)
- [docker-compose.yml](../docker-compose.yml)
- [.dockerignore](../.dockerignore)
- [docs/10_docker_compose.md](10_docker_compose.md)
- [README.md](../README.md)

该阶段 Compose 服务：

```text
api       FastAPI 后端服务
postgres PostgreSQL 业务数据库
redis    临时状态和缓存预留
```

学到的内容：

- Dockerfile 负责描述如何构建 API 镜像。
- docker-compose.yml 负责描述多个容器如何一起运行。
- `.dockerignore` 用来避免把 `.venv`、缓存、Git 元数据和无关目录复制进镜像。
- 容器里的 `localhost` 指向容器自己，所以 API 连接数据库时不能写 `localhost:5432`。
- Compose 内部服务之间应使用服务名通信：

```text
postgres:5432
redis:6379
```

- `depends_on` 配合 healthcheck 可以让 API 等 PostgreSQL 和 Redis 健康后再启动。
- API 容器启动时先运行 `alembic upgrade head`，再启动 `uvicorn`。

当前验证：

```text
docker compose config: passed
docker compose up --build: passed
api health check: passed
container API smoke flow: passed
pytest: 68 passed
ruff --no-cache: All checks passed
```

学到的补充内容：

- 容器启动时先等待 PostgreSQL 和 Redis healthcheck 通过。
- API 容器启动时自动执行 Alembic 迁移。
- 迁移完成后，Uvicorn 对外暴露 `8000` 端口。
- `http://localhost:8000/api/v1/health` 可以验证整个 API 容器已经可访问。
- 容器环境下已经通过 HTTP API 跑通节点、任务、调度、执行、结果回传和指标查询。

### 6.23 Prometheus 文本指标端点

已完成：

```text
GET /metrics
```

代表文件：

- [app/api/monitoring.py](../app/api/monitoring.py)
- [app/main.py](../app/main.py)
- [app/repositories/monitoring_repository.py](../app/repositories/monitoring_repository.py)
- [app/services/monitoring_service.py](../app/services/monitoring_service.py)
- [tests/api/test_monitoring.py](../tests/api/test_monitoring.py)

当前暴露的指标：

```text
uav_dag_nodes_total
uav_dag_nodes_by_type_total
uav_dag_nodes_by_status_total
uav_dag_tasks_total
uav_dag_tasks_by_status_total
uav_dag_subtasks_total
uav_dag_subtasks_by_status_total
uav_dag_schedule_plans_total
uav_dag_schedule_plans_by_status_total
uav_dag_executions_total
uav_dag_executions_by_status_total
uav_dag_execution_duration_ms_sum
uav_dag_execution_duration_ms_count
```

学到的内容：

- Prometheus 常见抓取格式是纯文本，不是 JSON。
- `/metrics` 通常放在根路径，方便 Prometheus 抓取。
- 第一版没有引入 `prometheus-client`，而是直接从数据库聚合事实表生成文本指标。
- 这些指标是当前系统状态的快照，重启 API 不会丢，因为事实来源在 PostgreSQL。
- Docker 环境下已经访问 `http://localhost:8000/metrics` 验证通过。

### 6.24 调度策略对比

已完成：

```text
local_only
random_offload
greedy
GET /api/v1/tasks/{task_id}/schedule-comparison
```

代表文件：

- [app/scheduler/estimation.py](../app/scheduler/estimation.py)
- [app/scheduler/local_only.py](../app/scheduler/local_only.py)
- [app/scheduler/random_offload.py](../app/scheduler/random_offload.py)
- [app/scheduler/greedy.py](../app/scheduler/greedy.py)
- [app/services/scheduling_service.py](../app/services/scheduling_service.py)
- [app/schemas/schedule.py](../app/schemas/schedule.py)
- [tests/scheduler/test_additional_strategies.py](../tests/scheduler/test_additional_strategies.py)
- [tests/api/test_tasks.py](../tests/api/test_tasks.py)

学到的内容：

- 策略对比应该是 dry-run，只在内存里生成计划，不落库、不修改任务状态。
- 三种策略复用同一套成本估算模块，避免“策略差异”和“估算公式差异”混在一起。
- `local_only` 只选择 UAV 节点，适合模拟完全不卸载的基线。
- `random_offload` 在可行节点里随机选择，并支持 `seed`，方便测试可重复。
- `greedy` 继续选择估算成本最低的节点。
- 对比接口会返回每个策略是否可行、失败原因、预估总耗时、预估总能耗、本地执行次数和边缘执行次数。
- Docker 环境下已经验证对比接口返回 `local_only, random_offload, greedy`，并且任务状态仍保持 `PENDING`。

### 6.25 Prometheus/Grafana 可视化

已完成：

```text
prometheus
grafana
UAV DAG Overview dashboard
```

代表文件：

- [docker-compose.yml](../docker-compose.yml)
- [monitoring/prometheus/prometheus.yml](../monitoring/prometheus/prometheus.yml)
- [monitoring/grafana/provisioning/datasources/prometheus.yml](../monitoring/grafana/provisioning/datasources/prometheus.yml)
- [monitoring/grafana/provisioning/dashboards/dashboards.yml](../monitoring/grafana/provisioning/dashboards/dashboards.yml)
- [monitoring/grafana/dashboards/uav-dag-overview.json](../monitoring/grafana/dashboards/uav-dag-overview.json)

学到的内容：

- Prometheus 负责定时抓取指标，不负责画复杂图表。
- Grafana 负责展示和组合指标图表。
- Compose 内部 Prometheus 访问 API 时使用服务名：

```text
api:8000/metrics
```

- Grafana 通过 provisioning 自动创建 Prometheus 数据源和 dashboard，避免每次手动配置。
- 当前 dashboard 展示节点数、任务数、执行记录数、执行耗时总和、任务状态分布、执行状态分布和节点类型分布。

当前验证：

```text
Prometheus target api:8000: up
Prometheus query uav_dag_tasks_total: passed
Grafana health: ok
Grafana dashboard UAV DAG Overview: provisioned
```

### 6.26 异步执行器与失败重试

已完成：

```text
RabbitMQ
Celery Worker
POST /api/v1/tasks/{task_id}/execute 自动投递 execution_id
Worker 自动回传模拟执行结果
失败后按 max_retries 决定是否重新变为 READY
```

代表文件：

- [app/api/v1/endpoints/tasks.py](../app/api/v1/endpoints/tasks.py)
- [app/schemas/execution.py](../app/schemas/execution.py)
- [app/services/execution_service.py](../app/services/execution_service.py)
- [app/services/execution_dispatcher.py](../app/services/execution_dispatcher.py)
- [app/worker/celery_app.py](../app/worker/celery_app.py)
- [app/worker/tasks.py](../app/worker/tasks.py)
- [docker-compose.yml](../docker-compose.yml)
- [tests/services/test_execution_dispatcher.py](../tests/services/test_execution_dispatcher.py)
- [tests/api/test_tasks.py](../tests/api/test_tasks.py)
- [11_async_execution_plan.md](11_async_execution_plan.md)

学到的内容：

- API 进程不应该长期执行子任务，真实系统应把执行工作交给独立 Worker。
- RabbitMQ 负责传递待执行消息，PostgreSQL 仍然是核心业务事实来源。
- API 必须先提交数据库事务，再把 execution id 投递到消息队列，避免 Worker 先消费却查不到记录。
- Worker 不直接散落修改数据库，而是复用 `ExecutionService.report_result()`，保证 API 回传和 Worker 回传遵守同一套状态规则。
- `EXECUTION_AUTO_ENQUEUE_ENABLED=false` 时，本地 pytest 不依赖 RabbitMQ；Docker 环境中开启自动投递。
- 执行失败不一定等于任务失败。只要 `retry_count < max_retries`，子任务会走：

```text
RUNNING -> FAILED -> RETRYING -> READY
```

- 重试次数用完后，子任务才会最终 `FAILED`，总任务才会进入 `FAILED`。
- `execution_records.attempt = subtask.retry_count + 1`，用于记录每一次真实执行尝试。
- 同一个 `execution_id` 的执行结果只接受一次，重复或迟到结果返回 `accepted=false`，不能再次推进状态。
- 幂等和重试不同：重试会创建新的 `execution_record`，幂等是在保护同一次执行尝试不要被重复处理。
- Celery 自动重试和业务重试不同：Celery 重试处理 Worker/数据库临时异常，业务重试处理子任务执行失败。
- Worker 只对数据库连接中断、连接池超时等临时基础设施异常调用 Celery retry，不对 `AppError` 这类业务错误重试。

该阶段验证：

```text
pytest: 91 passed
ruff --no-cache: All checks passed
docker compose config: passed
Docker async success smoke: passed
Docker async retry smoke: passed
duplicate execution result idempotency tests: passed
celery worker retry classification tests: passed
```

详细专题说明见：

```text
docs/11_async_execution_plan.md
```

### 6.27 阶段性整理与计划对齐

日期：2026-06-08

目标：

```text
不继续堆新功能，先整理当前异步执行与重试阶段。
```

为什么要做：

- 学习型项目不能只追着功能往前跑，否则很容易忘记“为什么这样设计”。
- 当前工作区已经包含 RabbitMQ / Celery、失败重试、幂等保护、Docker 和监控文档等多类改动，适合先做阶段性收束。
- `docs/02_learning_roadmap.md` 原来的“当前第一任务”还停留在早期需求分析阶段，需要和真实进度对齐。

涉及内容：

- [02_learning_roadmap.md](02_learning_roadmap.md)
- [09_learning_notes.md](09_learning_notes.md)
- [11_async_execution_plan.md](11_async_execution_plan.md)
- 当前分支：`feature/celery-retry-strategy`

学到的知识：

- 路线图不是写完就不变的文档，它应该随着项目进度校准。
- 阶段性整理本身也是工程能力：确认范围、验证测试、更新文档、明确下一步。
- 文档中如果同时存在“已完成”和“暂不实现”的旧描述，会让后续开发判断失真，应及时修正。
- `ruff` 默认会写 `.ruff_cache`，如果本地缓存目录有权限问题，可以用 `--no-cache` 跑静态检查，避免缓存权限影响验证判断。

本次验证：

```text
pytest: 91 passed
ruff --no-cache: All checks passed
docker compose config --quiet: passed
```

未在本次重复验证：

```text
docker compose up --build
Docker async success smoke
Docker async retry smoke
Prometheus / Grafana 页面级验证
```

当前边界：

- 本次只做阶段整理和文档对齐，没有新增业务代码。
- `CMDP_project` 和 `CMDP-方案整理.md` 属于另一个学习子项目，本阶段不混入主系统提交范围。

下一步：

```text
整理当前分支改动
-> 形成阶段性提交或 PR
-> 再进入并发幂等、Worker/队列监控、死信队列和告警
```

## 7. 测试学习总结

### 7.1 测试分层

当前测试分为：

```text
tests/domain      纯业务规则测试
tests/scheduler   调度算法测试
tests/services    Service 集成测试
tests/api         HTTP API 测试
```

### 7.2 不同测试解决的问题

Domain 测试：

- 验证 DAG 校验。
- 验证状态机。
- 不需要数据库。

Scheduler 测试：

- 验证调度策略。
- 不需要数据库。
- 可快速测试算法规则。

Service 测试：

- 验证数据库对象能否正确转换为业务输入。
- 验证事务内状态变化。
- 验证调度计划是否落库。

API 测试：

- 验证真实 HTTP 行为。
- 验证状态码。
- 验证请求和响应格式。
- 验证异常会不会被统一错误处理捕获。

### 7.3 当前测试状态

截至 2026-06-08：

```text
pytest: 91 passed
ruff --no-cache: All checks passed
docker compose config: passed
docker compose up --build: passed
api health check: passed
container API smoke flow: passed
GET /metrics: passed
schedule comparison smoke flow: passed
prometheus target health: up
grafana dashboard provisioning: passed
async worker success smoke flow: passed
async worker retry smoke flow: passed
execution result idempotency tests: passed
celery worker retry classification tests: passed
```

## 8. 当前开发状态

当前已经完成到：

```text
调度 API 已开放，调度计划可落库，任务可进入 SCHEDULED，可以查询调度计划列表和详情，可以启动模拟执行进入 RUNNING，可以回传执行结果推动子任务和总任务状态，可以查询任务下的执行记录，可以为后继 READY 子任务继续调度和执行，已经跑通 3 个子任务的 DAG 成功闭环，可以查询任务指标统计，已经补充 Docker Compose 本地开发环境配置、容器级启动验证、容器环境 API 冒烟流程、Prometheus 文本指标端点，可以对比 local_only、random_offload 和 greedy 三种调度策略，并且已经接入 Prometheus/Grafana 可视化。当前已经进一步接入 RabbitMQ 和 Celery Worker，支持 API 启动执行后异步投递 execution id，Worker 自动回传模拟结果，支持失败后的重试状态流转，验证了重复执行结果的幂等保护，并加入了 Worker 临时基础设施异常的 Celery 自动重试策略。
```

尚未完成：

```text
并发执行结果幂等锁
Worker 心跳和队列积压监控
任务取消后通知 Worker
RabbitMQ / Worker 指标接入 Prometheus 和 Grafana
死信队列和重试耗尽告警
```

当前建议下一步：

```text
阶段性整理、提交和 PR
```

也就是把这一阶段的大量学习开发成果整理成一次阶段性提交，而不是继续堆更多未提交改动。

## 9. 后续学习计划

### 9.1 查询调度计划

状态：已完成。

计划接口：

```text
GET /api/v1/tasks/{task_id}/schedules
GET /api/v1/schedules/{schedule_plan_id}
```

要学习：

- 嵌套路由和独立资源路由的区别。
- 列表查询和详情查询的响应结构。
- 如何验证调度计划属于某个任务。

### 9.2 模拟执行模块

状态：已完成启动执行、结果回传、执行记录列表查询、后继子任务继续调度/执行和完整 DAG 成功闭环。

计划接口：

```text
POST /api/v1/tasks/{task_id}/execute
GET /api/v1/tasks/{task_id}/executions
POST /api/v1/executions/{execution_id}/result
```

要学习：

- 执行记录和调度计划的关系。
- 子任务状态流转：

```text
READY -> DISPATCHED -> RUNNING -> SUCCESS / FAILED
```

- 如何根据依赖关系把后继子任务从 `WAITING` 推到 `READY`。
- 如何聚合所有子任务状态，更新总任务状态。
- 如何查询每一次执行尝试，区分计划、执行和结果。

### 9.3 执行结果幂等

状态：已完成第一版。

已经学到：

- 为什么真实系统会收到重复回调。
- 如何用 `execution_id` 保证重复结果不重复处理。
- 成功结果不应被后到达的失败结果覆盖。
- 重复失败不应该重复消耗 `retry_count`。

后续继续学习：

- 多 Worker 并发回传同一个 execution id 时，如何通过数据库行锁或乐观锁做更强保护。

### 9.4 指标统计

状态：已完成第一版任务指标统计，尚未完成策略对比指标。

计划接口：

```text
GET /api/v1/tasks/{task_id}/metrics
GET /api/v1/tasks/{task_id}/schedule-comparison
```

要学习：

- 总耗时。
- 子任务平均耗时。
- 成功率。
- 失败率。
- 本地执行比例。
- 卸载执行比例。
- 预估能耗和实际能耗。

### 9.5 更多调度策略

计划策略：

```text
local_only
random_offload
greedy
```

要学习：

- 策略接口统一。
- 随机策略如何固定随机种子，方便测试。
- 如何比较不同策略的耗时和能耗。
- 如何逐步引入更复杂的启发式算法。

### 9.6 Docker Compose

要学习：

- API 服务容器。
- PostgreSQL 容器。
- Redis 容器。
- 环境变量配置。
- 数据库迁移启动流程。

### 9.7 Redis

要学习：

- Redis 不保存核心业务事实。
- Redis 适合保存：
  - 最近心跳。
  - 短期锁。
  - 临时状态。
  - 后续异步队列辅助数据。

### 9.8 RabbitMQ / Celery

状态：已开始，已完成第一版异步执行、失败重试和 Celery 自动重试策略。

已经学到：

- 为什么执行模块不应该永远由 API 进程同步执行。
- 如何把 execution id 投递到 RabbitMQ。
- Celery Worker 如何消费任务并打开自己的数据库 Session。
- Worker 为什么仍然复用 Service 层，而不是自己写状态推进逻辑。
- 如何用 `simulation` 模拟成功、失败、超时和取消。
- 如何处理可重试失败和最终失败。
- 如何区分业务重试和 Celery 重试。
- 哪些异常适合自动重试，哪些业务错误不应该自动重试。
- 指数退避和最大退避时间的作用。

后续继续学习：

- 更强的并发幂等处理，例如数据库行锁或乐观锁。
- 队列积压和 Worker 健康监控。
- 任务取消和 Worker 正在执行之间的协调。
- 死信队列和重试耗尽告警。

### 9.9 MQTT

要学习：

- 节点 Agent 如何模拟真实无人机上报。
- MQTT topic 如何设计。
- 设备状态如何进入后端系统。

### 9.10 Prometheus / Grafana / OpenTelemetry

要学习：

- 监控指标。
- 日志。
- 链路追踪。
- 请求耗时。
- 调度耗时。
- 执行成功率。

### 9.11 微服务演进

当前不建议一开始拆微服务。

后续可以在模块化单体稳定后拆分：

```text
node-service
task-service
scheduler-service
executor-service
metrics-service
```

要学习：

- 服务边界。
- 数据一致性。
- 服务间通信。
- 消息队列。
- 分布式追踪。

## 10. 每次新增功能的学习记录模板

后续每完成一个功能，可以按这个格式追加记录：

```text
### 日期 - 功能名称

目标：

实现内容：

涉及文件：

学到的知识：

测试覆盖：

验证结果：

当前边界：

下一步：
```

## 11. 学习原则

这个项目后续继续遵循以下原则：

1. 先搞清楚需求，再写代码。
2. 先写能说明行为的测试，再实现。
3. 功能不要只在一层完成，要看它是否需要贯穿 API、Schema、ORM、迁移、Service、算法和测试。
4. Service 层负责组织业务流程。
5. Domain 和 Scheduler 层尽量保持纯粹，方便测试。
6. Repository 层封装数据库查询。
7. API 层保持薄，不写复杂业务。
8. 每完成一个阶段，再考虑提交和 PR。
9. 学习优先，不追求一次性写完所有功能。

## 12. 当前里程碑总结

当前系统已经从“文档设计”进入“真实后端实现”，并完成了主闭环的前半段：

```text
节点注册
-> 节点状态上报
-> DAG 任务创建
-> DAG 校验
-> 子任务状态初始化
-> 贪心调度
-> 本地执行约束
-> 调度计划落库
-> 任务进入 SCHEDULED
-> 调度 API 开放
-> 模拟执行启动
-> 执行结果回传
-> 执行记录查询
-> 后继子任务继续调度/执行
-> 完整 DAG 成功闭环
-> 指标统计
-> Docker Compose 配置
-> Docker Compose 容器级启动验证
-> 容器环境 API 冒烟流程
-> Prometheus 文本指标端点
-> 调度策略对比
-> Prometheus/Grafana 可视化
-> RabbitMQ/Celery 异步执行
-> Worker 自动回传执行结果
-> 失败模拟与子任务重试
-> Celery 自动重试策略
```

下一阶段应继续完成：

```text
并发幂等处理、Worker/队列监控、死信队列和告警
```

## 13. 后续协作与记录约定

这个项目的核心目标是学习，所以后续开发不只追求“把功能写出来”，还要同步记录每个阶段值得掌握的工程知识。

后续每次进入一个新功能前，应先对照：

- [02_learning_roadmap.md](02_learning_roadmap.md)
- 本文档第 8 节“当前开发状态”
- 本文档第 9 节“后续学习计划”

确认当前任务属于哪一个阶段，再开始实现。

每次完成重要功能后，都应在本文档追加对应学习记录，至少包括：

```text
目标：
为什么要做：
涉及层次：
关键实现：
学到的知识：
测试覆盖：
验证结果：
当前边界：
下一步：
```

后续开发节奏约定：

1. 如果当前阶段还有未整理的大量改动，优先整理、测试、提交，再继续堆新功能。
2. 如果要新增功能，先确认它是否符合当前计划，不直接跳到更复杂的后续能力。
3. 如果实现跨越 API、Schema、Service、Repository、ORM、Worker、Docker 或监控配置，学习记录要说明这些层是如何协作的。
4. 如果发现文档计划和代码现状不一致，优先更新文档，让路线图重新对齐真实进度。
5. 每次验证都要记录“跑了什么测试”以及“还有哪些没有验证”。

当前下一步仍然是：

```text
阶段性整理当前异步执行与重试成果
-> 确认测试和文档一致
-> 提交或 PR
-> 再进入并发幂等、Worker/队列监控、死信队列和告警
```
