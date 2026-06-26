# Docker Compose 本地开发环境

## 1. 目标

本阶段的目标是把当前后端系统整理成可一键启动的本地开发环境。

当前 Compose 包含五个服务：

```text
api       FastAPI 后端服务
postgres 业务事实数据库
redis    临时状态和缓存预留
prometheus 指标抓取和查询
grafana    指标可视化
```

当前主流程仍然以 PostgreSQL 为事实来源。Redis 已经作为依赖预留，但还不是主业务链路的必需组件。

## 2. 服务职责

### 2.1 api

`api` 服务运行 FastAPI 应用。

启动命令：

```text
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

含义：

- 容器启动后先执行数据库迁移。
- 迁移完成后启动 HTTP API。
- API 对宿主机暴露 `8000` 端口。

访问地址：

```text
http://localhost:8000/api/v1/health
```

### 2.2 postgres

`postgres` 服务保存核心业务数据：

- 节点。
- 节点状态记录。
- DAG 任务。
- 子任务。
- 依赖关系。
- 调度计划。
- 执行记录。

本地端口：

```text
localhost:5432
```

容器内连接地址：

```text
postgres:5432
```

### 2.3 redis

`redis` 服务用于后续临时状态和缓存能力，例如：

- 最近心跳。
- 短期锁。
- 临时执行状态。
- 后续异步队列辅助数据。

本地端口：

```text
localhost:6379
```

容器内连接地址：

```text
redis:6379
```

### 2.4 prometheus

`prometheus` 服务定时抓取 API 暴露的 `/metrics`。

访问地址：

```text
http://localhost:9090
```

抓取目标：

```text
api:8000/metrics
```

配置文件：

```text
monitoring/prometheus/prometheus.yml
```

### 2.5 grafana

`grafana` 服务用于查看 Prometheus 中的指标。

访问地址：

```text
http://localhost:3000
```

默认账号：

```text
admin / admin
```

当前已经通过 provisioning 自动配置：

- Prometheus 数据源。
- `UAV DAG Overview` 仪表盘。

## 3. localhost 和服务名的区别

本机直接运行应用时，`.env` 可以写：

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/uav_dag
REDIS_URL=redis://localhost:6379/0
```

因为应用进程运行在你的电脑上，`localhost` 指向你的电脑。

在 Docker Compose 中，`api` 运行在容器里。此时容器里的 `localhost` 指向 `api` 容器自己，而不是 PostgreSQL 或 Redis。

因此 Compose 里要写：

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/uav_dag
REDIS_URL=redis://redis:6379/0
```

这里的 `postgres` 和 `redis` 是 Compose 服务名，Docker 会自动把服务名解析成对应容器地址。

## 4. 常用命令

启动：

```powershell
docker compose up --build
```

后台启动：

```powershell
docker compose up --build -d
```

查看日志：

```powershell
docker compose logs -f api
```

停止：

```powershell
docker compose down
```

停止并删除数据库卷：

```powershell
docker compose down -v
```

注意：`docker compose down -v` 会删除 PostgreSQL 数据卷，本地数据会丢失。

## 5. 当前验证结果

Docker Desktop 启动后，已经执行：

```powershell
docker compose up --build
```

当前服务状态：

```text
api       Up, port 8000
postgres Up, healthy, port 5432
redis    Up, healthy, port 6379
prometheus Up, port 9090
grafana    Up, port 3000
```

API 容器启动日志显示 Alembic 已经完成数据库迁移：

```text
20260521_0001 create node tables
20260524_0002 create dag task tables
20260526_0003 add subtask execution constraint
20260531_0004 create schedule plan tables
20260531_0005 create execution records
```

健康检查通过：

```text
http://localhost:8000/api/v1/health
```

返回：

```json
{
  "status": "ok",
  "service": "uav-dag-offload-platform",
  "version": "0.1.0"
}
```

Prometheus 文本指标接口通过：

```text
http://localhost:8000/metrics
```

示例指标：

```text
uav_dag_nodes_total 2
uav_dag_tasks_total 1
uav_dag_executions_total 3
uav_dag_executions_by_status_total{status="SUCCESS"} 3
uav_dag_execution_duration_ms_sum 2700
```

Prometheus 抓取验证通过：

```text
target: api:8000
job: uav-dag-api
health: up
query: uav_dag_tasks_total
```

Grafana 验证通过：

```text
GET /api/health: ok
dashboard: UAV DAG Overview
url: http://localhost:3000/d/uav-dag-overview/uav-dag-overview
```

容器环境 API 冒烟流程也已通过：

```text
注册 UAV 节点
-> 注册 EDGE 节点
-> 上报节点状态
-> 创建 3 个子任务 DAG
-> 三轮调度
-> 三轮执行
-> 三次回传 SUCCESS
-> 查询任务指标
```

最终结果：

```json
{
  "task_status": "SUCCESS",
  "execution_count": 3,
  "success_rate": 1.0,
  "local_execution_count": 1,
  "edge_execution_count": 2,
  "offload_rate": 0.6667
}
```

## 6. Celery / RabbitMQ 异步执行补充

当前 Compose 已经补充异步执行链路：

```text
rabbitmq  消息队列，API 把 execution_id 投递到这里
worker    Celery Worker，从 RabbitMQ 消费 execution_id 并模拟执行
```

访问地址：

```text
RabbitMQ AMQP: localhost:5672
RabbitMQ UI:   http://localhost:15672
默认账号:      guest / guest
```

Worker 启动命令：

```text
celery -A app.worker.celery_app:celery_app worker --loglevel=INFO --concurrency=1
```

Docker 环境中开启了自动投递：

```text
EXECUTION_AUTO_ENQUEUE_ENABLED=true
```

Worker 临时异常重试配置：

```text
CELERY_EXECUTION_MAX_RETRIES=3
CELERY_EXECUTION_RETRY_BACKOFF_SECONDS=5
CELERY_EXECUTION_RETRY_BACKOFF_MAX_SECONDS=60
```

队列监控配置：

```text
RABBITMQ_QUEUE_MONITORING_ENABLED=true
RABBITMQ_MANAGEMENT_URL=http://rabbitmq:15672/api
RABBITMQ_MANAGEMENT_USERNAME=guest
RABBITMQ_MANAGEMENT_PASSWORD=guest
RABBITMQ_MANAGEMENT_VHOST=/
RABBITMQ_MANAGEMENT_TIMEOUT_SECONDS=1
```

因此在 Docker 环境里调用：

```text
POST /api/v1/tasks/{task_id}/execute
```

API 会先创建 `execution_records`，提交数据库事务，然后把 execution id 投递给 RabbitMQ。Worker 消费消息后会调用同一套 `ExecutionService.report_result()`，把子任务推进到 `SUCCESS`。

当前异步冒烟验证已经通过：

```text
queued_count: 1
subtask_status: SUCCESS
task_status: SUCCESS
```

当前 `/metrics` 会额外暴露 Worker 和队列指标：

```text
uav_dag_worker_auto_enqueue_enabled
uav_dag_worker_retry_max_retries
uav_dag_queue_monitor_available{queue="uav_dag_execution"}
uav_dag_queue_monitor_available{queue="uav_dag_execution.dlq"}
uav_dag_queue_messages{queue="uav_dag_execution"}
uav_dag_queue_messages{queue="uav_dag_execution.dlq"}
uav_dag_queue_messages_ready{queue="uav_dag_execution"}
uav_dag_queue_messages_ready{queue="uav_dag_execution.dlq"}
uav_dag_queue_messages_unacknowledged{queue="uav_dag_execution"}
uav_dag_queue_messages_unacknowledged{queue="uav_dag_execution.dlq"}
uav_dag_queue_consumers{queue="uav_dag_execution"}
uav_dag_queue_consumers{queue="uav_dag_execution.dlq"}
```

Grafana dashboard 已增加：

```text
Queue Messages
Queue Consumers
Worker Alerts
DLQ Ready Messages
```

更详细的学习记录见：

```text
docs/11_async_execution_plan.md
```

DLQ 查询接口：

```text
GET /api/v1/dead-letter-queue
GET /api/v1/dead-letter-queue/messages?limit=10&truncate=4096
```

`/messages` 当前使用 RabbitMQ Management API 的 `ack_requeue_true` 模式，只用于安全查看消息，不会确认、删除或重放 DLQ 消息。

DLQ 真实流转验证脚本：

```text
.\.venv\Scripts\python.exe scripts\verify_dlq_flow.py
```

脚本会声明临时 probe queue，发布探针消息，再用 `reject_requeue_false` 触发死信流转，最后用 `ack_requeue_true` 从 `uav_dag_execution.dlq` 安全查看探针消息。

成功时关键字段应为：

```text
main_queue_dead_letter_configured = true
published = true
rejected = true
found_in_dlq = true
```

2026-06-24 Docker 实跑结果：

```text
main_queue_dead_letter_configured = true
published = true
rejected = true
found_in_dlq = true
dlq_message_count = 3
```

验证后 API 和 metrics 也能看到 DLQ：

```text
GET /api/v1/dead-letter-queue
-> messages_ready = 2

GET /api/v1/dead-letter-queue/messages?limit=5&truncate=2048
-> x-first-death-reason = rejected

/metrics
-> uav_dag_queue_messages_ready{queue="uav_dag_execution.dlq"} 2
```

## 7. RabbitMQ DLQ 配置补充

Compose 已显式配置 Celery 主执行队列和死信路由参数：

```text
CELERY_TASK_DEFAULT_QUEUE=uav_dag_execution
CELERY_TASK_DEFAULT_EXCHANGE=uav_dag_execution
CELERY_TASK_DEFAULT_ROUTING_KEY=uav_dag_execution
CELERY_TASK_DEAD_LETTER_EXCHANGE=uav_dag_execution.dlx
CELERY_TASK_DEAD_LETTER_ROUTING_KEY=uav_dag_execution.dead
CELERY_TASK_DEAD_LETTER_QUEUE=uav_dag_execution.dlq
```

当前代码会让 Celery 主队列声明带上：

```text
x-dead-letter-exchange = uav_dag_execution.dlx
x-dead-letter-routing-key = uav_dag_execution.dead
```

Worker 启动时还会尽力声明：

```text
dead-letter exchange = uav_dag_execution.dlx
dead-letter queue    = uav_dag_execution.dlq
routing key          = uav_dag_execution.dead
```

Worker 命令通过 `--queues=${CELERY_TASK_DEFAULT_QUEUE}` 限制只消费主执行队列，避免误消费 DLQ。

当前边界：

- 这只是 DLQ 拓扑配置第一版。
- `/metrics` 已经能观察主执行队列和 DLQ 的消息数、ready 数、unacked 数和消费者数。
- 已经实现 DLQ 查询 API 第一版和 DLQ 流转验证脚本，并完成 Docker/RabbitMQ 容器级实跑。
- 还没有实现 DLQ 消费者或消息重放。
