# 后端骨架搭建计划

## 1. 文档目的

本文档用于规划第一阶段 FastAPI 后端工程骨架的搭建方式，明确目录结构、依赖选择、配置管理、数据库初始化、模块分层、测试结构和实现顺序。

本文档承接：

- `docs/03_requirements_analysis.md`
- `docs/04_system_design.md`
- `docs/05_database_design.md`
- `docs/06_api_design.md`
- `docs/07_state_machine_design.md`

本阶段只规划后端骨架，不实现完整业务闭环。后续真正创建代码时，应优先保证工程结构清晰、能启动、能测试、能迁移数据库。

## 2. 阶段目标

后端骨架阶段的目标是建立一个可持续开发的最小工程框架：

1. 创建 FastAPI 应用入口。
2. 建立清晰的模块分层。
3. 接入配置管理。
4. 接入 SQLAlchemy 2.0。
5. 初始化 Alembic。
6. 预留 PostgreSQL 和 Redis 连接。
7. 建立 pytest 测试结构。
8. 提供健康检查接口。
9. 为后续节点管理、DAG 任务、调度器、执行器实现打基础。

本阶段不追求一次性完成全部业务 API，而是先让项目“能跑、能测、能迁移、能扩展”。

## 3. 技术栈

第一阶段后端技术栈：

| 类型 | 技术 |
| --- | --- |
| Web 框架 | `FastAPI` |
| ASGI Server | `Uvicorn` |
| 数据库 | `PostgreSQL` |
| ORM | `SQLAlchemy 2.0` |
| 数据库迁移 | `Alembic` |
| 配置管理 | `pydantic-settings` |
| 数据校验 | `Pydantic v2` |
| 缓存/临时状态 | `Redis` |
| 测试 | `pytest` |
| HTTP 测试 | `httpx` |

后续阶段再引入：

- `Celery`
- `RabbitMQ`
- `MQTT`
- `Prometheus`
- `OpenTelemetry`

## 4. 推荐目录结构

建议第一阶段使用以下目录结构：

```text
.
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py
│   │           ├── nodes.py
│   │           ├── tasks.py
│   │           ├── schedules.py
│   │           ├── executions.py
│   │           └── metrics.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── errors.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── session.py
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── node.py
│   │       ├── task.py
│   │       ├── schedule.py
│   │       ├── execution.py
│   │       └── metric.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── enums.py
│   │   ├── state_machine.py
│   │   └── dag.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── node.py
│   │   ├── task.py
│   │   ├── schedule.py
│   │   ├── execution.py
│   │   └── metric.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── node_repository.py
│   │   ├── task_repository.py
│   │   ├── schedule_repository.py
│   │   └── execution_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── node_service.py
│   │   ├── task_service.py
│   │   ├── scheduling_service.py
│   │   ├── execution_service.py
│   │   └── metrics_service.py
│   └── scheduler/
│       ├── __init__.py
│       ├── base.py
│       ├── local_only.py
│       ├── random_offload.py
│       └── greedy.py
├── alembic/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── api/
│   ├── domain/
│   ├── services/
│   └── integration/
├── alembic.ini
├── pyproject.toml
├── .env.example
└── README.md
```

说明：

- `api` 只负责 HTTP 输入输出。
- `schemas` 定义 Pydantic 请求和响应模型。
- `services` 编排业务用例和状态迁移。
- `repositories` 封装数据库读写。
- `domain` 放纯业务逻辑，例如 DAG 校验、状态机、枚举。
- `scheduler` 放调度策略实现，策略之间保持同一接口。
- `db/models` 放 SQLAlchemy ORM 模型。

## 5. Python 依赖建议

建议使用 `pyproject.toml` 管理依赖。第一阶段依赖可分为运行依赖和开发依赖。

### 5.1 运行依赖

```text
fastapi
uvicorn[standard]
pydantic-settings
sqlalchemy
alembic
psycopg[binary]
redis
python-dotenv
```

### 5.2 开发依赖

```text
pytest
pytest-asyncio
httpx
ruff
mypy
```

### 5.3 版本策略

建议第一阶段先固定大版本：

- `fastapi`
- `pydantic >= 2`
- `sqlalchemy >= 2`
- `psycopg >= 3`

等主闭环稳定后，再进一步锁定完整版本。

## 6. 配置管理方案

配置入口建议放在：

```text
app/core/config.py
```

使用 `pydantic-settings` 定义 `Settings`：

```text
APP_NAME
APP_ENV
APP_DEBUG
DATABASE_URL
REDIS_URL
API_V1_PREFIX
HEARTBEAT_TIMEOUT_SECONDS
DEFAULT_SCHEDULER_STRATEGY
```

建议提供 `.env.example`：

```text
APP_NAME=uav-dag-offload-platform
APP_ENV=local
APP_DEBUG=true
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/uav_dag
REDIS_URL=redis://localhost:6379/0
HEARTBEAT_TIMEOUT_SECONDS=30
DEFAULT_SCHEDULER_STRATEGY=greedy
```

注意：

- `.env` 不提交 Git。
- `.env.example` 提交 Git。
- 测试环境可以使用独立 `DATABASE_URL` 或 SQLite 临时库，但最终集成测试应覆盖 PostgreSQL。

## 7. FastAPI 应用入口

应用入口：

```text
app/main.py
```

职责：

1. 创建 `FastAPI` 实例。
2. 注册 `/api/v1` 路由。
3. 注册异常处理器。
4. 注册启动和关闭生命周期事件。
5. 提供 OpenAPI 元数据。

建议第一阶段应用名称：

```text
UAV DAG Offload Platform
```

第一阶段必须实现的接口：

```text
GET /api/v1/health
```

响应：

```json
{
  "status": "ok",
  "service": "uav-dag-offload-platform",
  "version": "0.1.0"
}
```

## 8. API 路由分层

API v1 总路由：

```text
app/api/v1/router.py
```

聚合以下 endpoint：

```text
health
nodes
tasks
schedules
executions
metrics
```

本阶段只需要真正接通 `health`。其他 endpoint 可以先创建空文件或在后续功能分支中补齐。

建议后续功能分支顺序：

1. `feature/node-management`
2. `feature/dag-task-management`
3. `feature/scheduler`
4. `feature/execution-simulator`
5. `feature/metrics-query`

## 9. SQLAlchemy 2.0 设计

### 9.1 Base 定义

建议在 `app/db/base.py` 定义：

- Declarative Base
- 通用 `id`
- 通用 `created_at`
- 通用 `updated_at`

也可以先只定义 `Base`，避免过早抽象。

### 9.2 Session 管理

建议在 `app/db/session.py` 定义：

- `engine`
- `SessionLocal`
- `get_db()` 依赖

第一阶段建议使用同步 SQLAlchemy：

- FastAPI 路由使用普通 `def` 或 `async def` 均可。
- 数据库操作先用同步 Session，减少学习复杂度。
- 后续如果需要高并发，再评估异步 SQLAlchemy。

### 9.3 ORM 模型文件

模型按业务分文件：

```text
node.py
task.py
schedule.py
execution.py
metric.py
```

对应数据库设计：

- `nodes`
- `node_status_records`
- `dag_tasks`
- `dag_subtasks`
- `dag_dependencies`
- `schedule_plans`
- `schedule_plan_items`
- `execution_records`
- `task_metrics`

### 9.4 `metadata` 字段注意

数据库字段可以叫 `metadata`，但 SQLAlchemy ORM 属性不要直接命名为 `metadata`。

建议：

```text
metadata_ = mapped_column("metadata", JSONB)
```

## 10. Alembic 初始化计划

Alembic 用于管理数据库迁移。

### 10.1 初始化目标

后端骨架阶段应完成：

1. 生成 `alembic.ini`。
2. 生成 `alembic/` 目录。
3. 配置 Alembic 读取项目 `DATABASE_URL`。
4. 配置 `target_metadata = Base.metadata`。
5. 创建第一版空迁移或核心表迁移计划。

### 10.2 初始迁移建议

如果本阶段只搭骨架：

- 可以先初始化 Alembic，不创建完整表。
- 下一阶段 `feature/backend-scaffold` 或 `feature/node-management` 再创建第一版表。

如果想一次建核心表：

- 按 `docs/05_database_design.md` 的建表顺序创建初始迁移。

推荐第一阶段选择：

```text
先初始化 Alembic，再在数据库模型实现分支创建核心表迁移。
```

原因是骨架阶段关注工程结构，避免一次 PR 过大。

## 11. Redis 接入计划

Redis 第一阶段只做连接预留，不强依赖主流程。

建议放在：

```text
app/core/redis.py
```

后续用途：

- 保存最近心跳缓存。
- 保存短期任务锁。
- 支持后续异步执行状态。
- 支持限流或幂等键。

骨架阶段只需要：

- 配置 `REDIS_URL`。
- 能在健康检查扩展时连接 Redis。

## 12. 领域层设计

领域层放不依赖 FastAPI 和数据库框架的纯业务逻辑。

建议文件：

```text
app/domain/enums.py
app/domain/state_machine.py
app/domain/dag.py
```

### 12.1 枚举

定义以下枚举：

- `NodeType`
- `NodeStatus`
- `TaskStatus`
- `SubtaskStatus`
- `SchedulePlanStatus`
- `ExecutionStatus`
- `SchedulerStrategyName`

### 12.2 状态机

根据 `docs/07_state_machine_design.md` 实现：

- 合法状态迁移表。
- `can_transition()`。
- `ensure_transition_allowed()`。

### 12.3 DAG 校验

根据 `docs/03_requirements_analysis.md` 实现纯函数：

- 子任务 ID 不重复。
- 依赖引用存在。
- 不存在环。
- 至少一个入口子任务。
- 至少一个出口子任务。

骨架阶段只规划这些文件，不要求立刻实现完整逻辑。

## 13. Schema 设计

Schema 放在：

```text
app/schemas/
```

按 `docs/06_api_design.md` 命名：

- `NodeCreate`
- `NodeRead`
- `NodeStatusCreate`
- `DagTaskCreate`
- `DagTaskRead`
- `SubtaskCreate`
- `DependencyCreate`
- `ScheduleRequest`
- `SchedulePlanRead`
- `ExecutionStartRequest`
- `ExecutionRecordRead`
- `TaskMetricsRead`
- `ErrorResponse`
- `PaginatedResponse`

骨架阶段建议先实现：

- `HealthResponse`
- `ErrorResponse`

其他 Schema 在对应功能分支补齐。

## 14. Service 与 Repository 分层

### 14.1 Repository

Repository 只负责数据访问：

- 创建记录。
- 查询记录。
- 更新记录。
- 封装常用查询条件。

Repository 不负责业务状态判断。

### 14.2 Service

Service 负责编排业务逻辑：

- 参数语义校验。
- 调用 Repository。
- 状态机校验。
- 事务边界控制。
- 组织返回结果。

### 14.3 分层规则

推荐依赖方向：

```text
api -> service -> repository -> db
service -> domain
scheduler -> domain
```

不推荐：

```text
repository -> service
domain -> db
domain -> fastapi
```

## 15. 调度器骨架计划

调度器放在：

```text
app/scheduler/
```

建议定义统一接口：

```text
SchedulerStrategy
  - name
  - generate_plan(task_graph, node_snapshot, options)
```

第一阶段策略：

- `local_only`
- `random_offload`
- `greedy`

骨架阶段只需要创建模块边界和接口计划，不必实现策略细节。

## 16. 测试结构

测试目录：

```text
tests/
├── conftest.py
├── api/
│   └── test_health.py
├── domain/
│   ├── test_dag_validation.py
│   └── test_state_machine.py
├── services/
└── integration/
```

骨架阶段最小测试：

1. `GET /api/v1/health` 返回 `200`。
2. `HealthResponse` 字段完整。
3. 应用可以被 TestClient 创建。

后续功能阶段测试：

1. DAG 合法性校验。
2. 状态机合法迁移和非法迁移。
3. 节点注册 API。
4. 节点状态上报 API。
5. DAG 任务创建 API。
6. 调度策略单元测试。
7. 模拟执行集成测试。

## 17. 第一阶段实现顺序

建议按以下顺序实现后端：

1. 创建 Python 项目骨架和 `pyproject.toml`。
2. 创建 FastAPI 应用入口。
3. 创建配置管理。
4. 创建健康检查接口。
5. 创建 pytest 和 TestClient 测试。
6. 接入 SQLAlchemy Session。
7. 初始化 Alembic。
8. 定义领域枚举。
9. 实现状态机纯函数。
10. 实现 DAG 校验纯函数。
11. 实现 ORM 模型。
12. 创建第一版数据库迁移。
13. 实现节点管理。
14. 实现 DAG 任务管理。
15. 实现调度器。
16. 实现模拟执行器。
17. 实现结果和指标查询。

## 18. Git 分支建议

后端代码阶段建议使用以下分支：

```text
feature/backend-scaffold
feature/node-management
feature/dag-task-management
feature/scheduler
feature/execution-simulator
feature/metrics-query
```

每个分支只做一个清晰目标，避免一个 PR 同时包含太多概念。

## 19. 本阶段不做的内容

后端骨架计划阶段不做：

- 不实现完整节点注册业务。
- 不实现完整 DAG 创建 API。
- 不实现调度算法。
- 不实现模拟 Worker。
- 不写 Docker Compose。
- 不接入 Celery / RabbitMQ / MQTT。
- 不接入 Prometheus / Grafana / OpenTelemetry。
- 不实现认证和权限。

这些能力放到后续功能和工程化阶段。

## 20. 最小验收标准

当真正进入 `feature/backend-scaffold` 实现时，骨架阶段应满足：

1. 可以安装依赖。
2. 可以启动 FastAPI。
3. 可以访问 `/api/v1/health`。
4. 可以运行 pytest。
5. 项目目录结构与本文档一致。
6. 配置可以从环境变量读取。
7. Alembic 已初始化或有明确初始化步骤。
8. 后续模块有清晰落点。

## 21. 当前结论

后端骨架阶段的关键是搭好工程地基，而不是急着堆业务代码。建议先用 FastAPI、Pydantic Settings、SQLAlchemy 2.0、Alembic 和 pytest 建立一个可运行、可测试、可迁移的基础工程。

完成本文档后，下一步应创建 `feature/backend-scaffold` 分支，开始真正搭建 FastAPI 项目骨架。
