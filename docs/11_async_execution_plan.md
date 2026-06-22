# 11. 异步执行器设计与学习记录

## 1. 为什么要做异步执行

当前系统已经完成了同步模拟执行闭环：

```text
提交 DAG 任务
-> 生成调度计划
-> 启动执行记录
-> 手动回传执行结果
-> 推进子任务和总任务状态
```

这个闭环适合第一阶段学习，因为它能快速看清业务状态流转。但真实后端系统里，API 进程通常不应该长期执行子任务：

- API 的职责是接收请求、校验参数、启动业务流程并快速返回。
- 子任务执行可能耗时很久，不应该占用 HTTP 请求线程。
- 执行过程可能失败、重试、超时，需要独立的 worker 处理。
- 多个 worker 可以横向扩展，更接近真实边缘计算平台。

因此下一阶段引入：

```text
FastAPI -> RabbitMQ -> Celery Worker -> PostgreSQL
```

## 2. 各组件职责

### 2.1 FastAPI

负责：

- 接收 `POST /api/v1/tasks/{task_id}/execute` 请求。
- 调用 `ExecutionService.start_execution()` 创建执行记录。
- 提交数据库事务。
- 在配置开启时，把 execution id 投递给 Celery。

代表文件：

- [tasks.py](../app/api/v1/endpoints/tasks.py)
- [execution_service.py](../app/services/execution_service.py)
- [execution_dispatcher.py](../app/services/execution_dispatcher.py)

### 2.2 RabbitMQ

负责：

- 存放待执行的异步消息。
- 让 API 和 Worker 解耦。
- API 投递消息后可以返回，Worker 稍后消费消息。

RabbitMQ 不保存核心业务事实。核心事实仍然在 PostgreSQL。

### 2.3 Celery Worker

负责：

- 从 RabbitMQ 消费 execution id。
- 打开自己的数据库 Session。
- 调用 `ExecutionService.report_result()` 回传模拟执行结果。
- 提交数据库事务。

代表文件：

- [celery_app.py](../app/worker/celery_app.py)
- [tasks.py](../app/worker/tasks.py)

### 2.4 PostgreSQL

负责保存核心事实：

- DAG 任务。
- 子任务状态。
- 调度计划。
- 执行记录。
- 执行结果。

如果 RabbitMQ 或 Worker 重启，系统仍然可以通过数据库查询当前任务状态。

## 3. 当前最小实现

本阶段先实现最小异步闭环：

```text
POST /api/v1/tasks/{task_id}/execute
-> 创建 execution_records，状态为 RUNNING
-> API commit
-> 投递 execution_id 到 RabbitMQ
-> Worker 消费 execution_id
-> Worker 调用 ExecutionService.report_result(..., SUCCESS)
-> 子任务状态变为 SUCCESS
-> 依赖后继子任务解锁为 READY
```

当前 Worker 只是模拟成功执行，不做真实计算。

## 4. 为什么要先 commit 再投递消息

这是异步系统里非常重要的一步。

如果 API 在数据库事务提交前就把消息发给 RabbitMQ，可能出现：

```text
API 创建 execution_record，但还没 commit
-> Worker 已经拿到 execution_id
-> Worker 查询数据库
-> 查不到这条 execution_record
```

所以当前 API 顺序是：

```text
ExecutionService.start_execution()
-> db.commit()
-> ExecutionDispatcher.enqueue_started_executions()
```

这保证 Worker 消费消息时，数据库里已经能查到执行记录。

## 5. 为什么保留手动回传接口

即使有 Celery Worker，仍然保留：

```text
POST /api/v1/executions/{execution_id}/result
```

原因：

- 便于学习和调试状态机。
- 后续真实无人机 Agent 或边缘节点也可能通过这个接口回传结果。
- Worker 本质上也是调用同一套业务服务，不另写一套状态逻辑。

这体现了一个重要设计原则：

```text
状态推进逻辑放在 Service 层复用，而不是散落在 API 和 Worker 各自实现。
```

## 6. 配置开关

本地 pytest 默认不依赖 RabbitMQ：

```text
EXECUTION_AUTO_ENQUEUE_ENABLED=false
```

Docker Compose 环境中开启自动投递：

```text
EXECUTION_AUTO_ENQUEUE_ENABLED=true
```

这样做的好处：

- 普通单元测试和 API 测试不需要启动消息队列。
- Docker 集成环境可以验证真实异步链路。
- 学习时可以清楚区分“业务逻辑测试”和“基础设施连通性测试”。

## 7. 当前边界

当前版本已经实现：

- RabbitMQ / Celery 最小异步执行闭环。
- 失败模拟和业务重试。
- 执行结果幂等保护。
- 执行结果回传前对 `execution_records` 使用数据库行锁。
- Celery Worker 临时基础设施异常自动重试。
- RabbitMQ 队列监控指标。
- 任务取消时同步取消非终态子任务和运行中的执行记录。
- Worker 迟到结果回传时返回 `accepted=false`，不覆盖已取消事实。
- Worker 执行任务时刷新数据库心跳，并在 `/metrics` 暴露 Worker 在线数量。
- API 投递 Celery 后保存 `celery_task_id`，取消任务时尝试安全 revoke。

当前版本暂不实现：

- 超时检测。
- 独立周期性 Worker 心跳。
- 强制终止正在执行的 Celery Worker 子进程。
- 死信队列和重试耗尽告警。
- outbox pattern。

这些是后续真实化阶段继续学习的内容。

## 8. 下一步学习重点

RabbitMQ / Celery 的执行、幂等、队列监控、取消协调、Worker 心跳第一版和安全 revoke 学习目标已经完成。后续可以继续推进：

1. 独立周期性 Worker 心跳。
2. Worker 周期性检查执行记录是否已取消。
3. 死信队列和 Celery 重试耗尽后的告警。
4. outbox pattern，避免数据库提交成功但消息投递失败。

## 9. 失败模拟与重试

当前已经支持在启动执行时传入模拟结果：

```json
{
  "schedule_plan_id": "00000000-0000-0000-0000-000000000001",
  "simulation": {
    "result_status": "FAILED",
    "duration_ms": 800,
    "failure_reason": "camera unavailable"
  }
}
```

`simulation.result_status` 只能是终态：

```text
SUCCESS
FAILED
TIMEOUT
CANCELED
```

不能传 `RUNNING`，因为 `RUNNING` 是执行中的状态，不是执行结果。

### 9.1 重试规则

子任务有两个字段：

```text
retry_count  已经使用过的重试次数
max_retries  最多允许重试多少次
```

第一次执行不是重试，所以：

```text
初始 retry_count = 0
第一次 execution attempt = 1
```

如果第一次执行失败，并且：

```text
retry_count < max_retries
```

则系统不会立刻把总任务标记为失败，而是执行状态流转：

```text
RUNNING -> FAILED -> RETRYING -> READY
```

然后：

```text
retry_count += 1
task.status 保持 RUNNING
subtask.status 回到 READY
```

这样调度器下一轮还能重新调度这个子任务。

如果重试次数已经用完，则状态流转为：

```text
subtask.status = FAILED
task.status = FAILED
```

### 9.2 execution attempt 和 retry_count 的关系

每次启动执行记录时：

```text
execution_record.attempt = subtask.retry_count + 1
```

例如：

```text
第一次执行: retry_count = 0, attempt = 1
第一次失败后允许重试: retry_count = 1, subtask 回到 READY
第二次执行: retry_count = 1, attempt = 2
```

这个设计的含义是：

- `execution_records` 保存每一次真实尝试。
- `dag_subtasks.retry_count` 保存当前子任务已经消耗的重试预算。
- 子任务是否最终失败，要结合 `retry_count` 和 `max_retries` 判断。

### 9.3 为什么 Worker 仍然调用 Service

Celery Worker 没有自己改数据库状态，而是调用：

```text
ExecutionService.report_result()
```

这非常重要。因为无论结果来自：

- 手动 API 回传。
- Celery Worker 模拟执行。
- 未来真实无人机 Agent 回传。

最终都走同一套状态机和重试规则。这样业务规则只有一份，不会出现 API 和 Worker 行为不一致。

## 10. 执行结果幂等

异步系统里必须考虑重复消息和乱序结果。

常见原因包括：

- Worker 执行成功后，结果回传请求超时，调用方再次发送。
- RabbitMQ 或 Worker 在异常恢复后重复投递同一条消息。
- 成功结果已经处理完，但一个较晚到达的失败结果又回来了。

因此同一个 `execution_id` 的结果只能被接受一次。

当前规则是：

```text
只有 execution_record.status == RUNNING 时，结果才会被接受。
如果 execution_record 已经是 SUCCESS / FAILED / TIMEOUT / CANCELED，
再次回传只返回 accepted=false，不再推进子任务和总任务状态。
```

代表代码：

```text
ExecutionService.report_result()
```

这条规则保护了三个关键场景：

```text
第一次 SUCCESS -> accepted=true
重复 SUCCESS -> accepted=false，原 duration/output 不被覆盖

第一次 SUCCESS -> accepted=true
后到 FAILED -> accepted=false，成功结果不被失败覆盖

第一次 FAILED 且允许重试 -> subtask 回到 READY，retry_count += 1
重复 FAILED -> accepted=false，retry_count 不会再次增加
```

幂等处理和重试处理要区分开：

- 重试是“新的执行尝试”，会生成新的 `execution_record`，`attempt` 增加。
- 幂等是“同一次执行尝试的重复结果”，不能生成新的业务推进。

当前测试覆盖：

```text
重复成功结果不会覆盖原成功记录
成功后迟到失败不会覆盖成功状态
重复失败不会重复消耗 retry_count
ExecutionRepository.get_by_id_for_update() 在 PostgreSQL 方言下生成 FOR UPDATE
ExecutionService.report_result() 使用带锁读取入口
```

### 10.1 为什么还需要数据库行锁

普通幂等检查解决的是“第二次结果到达时，记录已经不是 `RUNNING`”的情况：

```text
第一次结果已提交
-> 第二次结果读取到 SUCCESS / FAILED
-> accepted=false
```

但多 Worker 并发时可能出现更危险的时序：

```text
Worker A 读取 execution_record.status = RUNNING
Worker B 同时读取 execution_record.status = RUNNING
Worker A 推进状态并提交
Worker B 也尝试推进同一条记录
```

因此当前在 `ExecutionService.report_result()` 中改为通过：

```text
ExecutionRepository.get_by_id_for_update()
```

读取执行记录。它在 PostgreSQL 下会生成：

```sql
SELECT ...
FROM execution_records
WHERE execution_records.id = ...
FOR UPDATE
```

含义是：

- 同一个 `execution_id` 的结果处理会围绕同一行串行化。
- 后到的 Worker 必须等先到的事务提交或回滚。
- 等待结束后，后到 Worker 再读取状态，如果已经不是 `RUNNING`，就返回 `accepted=false`。

测试环境使用 SQLite，SQLite 不真正支持 PostgreSQL 风格的行级锁，所以测试分成两类：

- Repository 测试：用 PostgreSQL 方言编译 SQL，确认会生成 `FOR UPDATE`。
- Service 测试：确认 `report_result()` 确实调用带锁读取入口。

## 11. Celery 自动重试策略

前面已经实现了业务重试：

```text
子任务执行失败
-> 根据 retry_count / max_retries 判断是否重新变为 READY
-> 之后由调度器重新生成计划并创建新的 execution_record
```

Celery 自动重试解决的是另一个问题：

```text
Worker 本次没有能力完成结果处理
-> 例如数据库连接临时中断、连接池超时
-> Celery 稍后重新执行同一条消息
```

这两类重试必须区分：

```text
业务重试：任务真的执行失败了，系统要不要再跑一次子任务。
Celery 重试：Worker/数据库/网络临时故障，本次消息处理没有完成。
```

当前策略：

```text
OperationalError -> retry
SQLAlchemy TimeoutError -> retry
DBAPIError(connection_invalidated=True) -> retry
AppError -> no retry
ValueError -> no retry
```

不重试 `AppError` 的原因是它通常代表业务语义问题，例如：

```text
EXECUTION_NOT_FOUND
EXECUTION_STATE_CONFLICT
TASK_STATE_CONFLICT
```

这些错误重复消费消息也不会自然恢复，应该暴露出来，而不是在队列里反复重试。

### 11.1 指数退避

当前使用指数退避：

```text
第 1 次 retry countdown = 5 秒
第 2 次 retry countdown = 10 秒
第 3 次 retry countdown = 20 秒
最大不超过 60 秒
```

对应配置：

```text
CELERY_EXECUTION_MAX_RETRIES=3
CELERY_EXECUTION_RETRY_BACKOFF_SECONDS=5
CELERY_EXECUTION_RETRY_BACKOFF_MAX_SECONDS=60
```

### 11.2 消息确认策略

当前 Celery 配置中开启：

```text
task_acks_late=True
task_reject_on_worker_lost=True
worker_prefetch_multiplier=1
```

含义：

- `task_acks_late=True`：Worker 完成任务后再确认消息。
- `task_reject_on_worker_lost=True`：Worker 异常退出时，消息可以重新回到队列。
- `worker_prefetch_multiplier=1`：每个 Worker 进程一次只预取少量任务，便于观察和控制。

这些设置会增加重复投递的可能性，所以前面做的执行结果幂等非常重要。

### 11.3 当前边界

当前版本还没有实现：

- 死信队列。
- 重试耗尽后的告警。
- 重试次数写入业务表。
- 不同异常类型的不同重试策略。
- Worker 心跳。

## 12. Worker/队列监控

当前系统已经把 RabbitMQ 队列状态接入 `/metrics`。

配置项：

```text
RABBITMQ_QUEUE_MONITORING_ENABLED
RABBITMQ_MANAGEMENT_URL
RABBITMQ_MANAGEMENT_USERNAME
RABBITMQ_MANAGEMENT_PASSWORD
RABBITMQ_MANAGEMENT_VHOST
RABBITMQ_MANAGEMENT_TIMEOUT_SECONDS
```

本地默认关闭：

```text
RABBITMQ_QUEUE_MONITORING_ENABLED=false
```

Docker 环境开启：

```text
RABBITMQ_QUEUE_MONITORING_ENABLED=true
RABBITMQ_MANAGEMENT_URL=http://rabbitmq:15672/api
```

这样做的原因是：

- 本地单元测试和 API 测试不应该强依赖 RabbitMQ。
- Docker 环境中 RabbitMQ Management API 可用，可以读取真实队列状态。
- RabbitMQ 不可达时，`/metrics` 仍然应该返回业务指标，而不是让 Prometheus 抓取失败。

当前新增指标：

```text
uav_dag_worker_auto_enqueue_enabled
uav_dag_worker_retry_max_retries
uav_dag_worker_retry_backoff_seconds
uav_dag_worker_retry_backoff_max_seconds
uav_dag_queue_monitor_enabled{queue="uav_dag_execution"}
uav_dag_queue_monitor_available{queue="uav_dag_execution"}
uav_dag_queue_messages{queue="uav_dag_execution"}
uav_dag_queue_messages_ready{queue="uav_dag_execution"}
uav_dag_queue_messages_unacknowledged{queue="uav_dag_execution"}
uav_dag_queue_consumers{queue="uav_dag_execution"}
```

指标含义：

- `messages`：队列中总消息数。
- `messages_ready`：等待 Worker 消费的消息数。
- `messages_unacknowledged`：已被 Worker 取走但尚未确认的消息数。
- `consumers`：当前连接到队列的消费者数量，通常可以用来判断 Worker 是否在线消费。

Grafana dashboard 已增加：

```text
Queue Messages
Queue Consumers
```

当前边界：

- 这不是完整 Worker 心跳，只是 RabbitMQ 队列和消费者视角。
- 还没有记录 Worker 自身最后心跳时间。
- 没有接入 RabbitMQ 官方 exporter，因此指标粒度仍然较粗。

## 13. 任务取消与 Worker 迟到结果

异步执行引入后，取消任务会遇到一个典型竞态：

```text
用户取消任务
-> 数据库把 task 标记为 CANCELED
-> Worker 仍然可能已经拿到 execution_id 并继续回传 SUCCESS
```

如果只取消总任务，不处理子任务和执行记录，迟到的 Worker 结果可能再次推动状态，造成“用户已经取消，但子任务又成功”的矛盾。

当前版本采用数据库事实优先的做法：

```text
cancel task
-> task.status = CANCELED
-> 先锁定并取消 RUNNING execution_record
-> 重新读取子任务状态
-> 非终态 subtask.status = CANCELED
-> late result callback sees execution_record is not RUNNING
-> accepted = false
```

这说明异步系统里的取消至少要协调三类事实：

- `dag_tasks`：用户看到的总体任务状态。
- `subtasks`：调度器后续是否还能继续调度。
- `execution_records`：Worker 回传结果是否还能被接受。

当前版本已经能在保存 `celery_task_id` 后发出安全 revoke 请求。也就是说，尚未开始执行的 Celery 消息有机会被撤销；已经进入 Worker 代码的任务仍可能完成自己的模拟执行，数据库侧继续用 `accepted=false` 拒绝迟到结果。

后续如果要更接近真实系统，可以继续学习：

- Worker 定期检查执行记录是否已取消。
- 结合 Worker 心跳判断正在执行的任务是否失联。

## 14. Worker 心跳第一版

RabbitMQ 队列监控只能说明队列上有多少 consumer，但不能回答：

```text
具体哪个 Worker 最近还活着？
它最后一次上报是什么时候？
它当前是空闲还是正在执行某个 execution_id？
```

因此当前版本新增 `worker_heartbeats` 表，把 Worker 心跳作为数据库里的业务事实保存。

当前实现方式：

```text
execute_subtask starts
-> report worker heartbeat as BUSY with current_execution_id
-> ExecutionService.report_result(...)
-> report worker heartbeat as ONLINE
```

Prometheus 新增指标：

```text
uav_dag_worker_heartbeat_timeout_seconds
uav_dag_workers_total
uav_dag_workers_online
uav_dag_worker_latest_seen_timestamp
uav_dag_workers_by_status_total{status="ONLINE|BUSY"}
```

在线判定：

```text
last_seen_at >= now - WORKER_HEARTBEAT_TIMEOUT_SECONDS
```

当前边界：

- 这还不是独立周期性心跳，只有 Worker 执行任务时才会刷新。
- 如果 Worker 长时间空闲，它不会主动刷新 `last_seen_at`。
- 心跳失败只记录日志，不阻断真正的执行结果回传。
- `celery_task_id` 已写入执行记录，当前 revoke 基于 `execution_records.celery_task_id`，心跳表仍只记录当前执行中的 `execution_id`。

后续增强：

- 增加 Celery boot/shutdown/task prerun/task postrun 信号级心跳。
- 增加周期性 heartbeat task 或 Worker 内部定时上报。
- 把心跳和主动撤销 Worker 任务联动起来。

## 15. Celery task id 与安全 revoke

任务取消协调第一版只做到了数据库事实层面：

```text
task -> CANCELED
subtask -> CANCELED
execution_record -> CANCELED
late worker result -> accepted=false
```

这能保证数据库不会被迟到结果覆盖，但还不能向 Celery 发出撤销请求。

当前版本新增 `execution_records.celery_task_id`：

```text
ExecutionService.start_execution()
-> 创建 execution_record
-> commit
-> ExecutionDispatcher.enqueue_started_executions()
-> Celery 返回 AsyncResult.id
-> 回写 execution_records.celery_task_id
```

这样取消任务时，系统可以知道对应的 Celery 消息 id：

```text
TaskService.cancel_task()
-> 锁定 RUNNING execution_record
-> execution_record.status = CANCELED
-> 如果 celery_task_id 存在
-> celery_app.control.revoke(celery_task_id, terminate=False)
```

这里使用 `terminate=False` 是一个有意选择：

- 可以撤销尚未开始执行的 Celery 消息。
- 不会强杀 Worker 子进程，避免破坏共享资源或中断数据库事务。
- 对已经开始执行的任务只是尽力而为，仍然需要数据库侧 `accepted=false` 兜底。

当前边界：

- revoke 失败只记录日志，不阻断任务取消。
- 已经运行中的 Python 代码不会因为 `terminate=False` 立刻停止。
- 要更接近真实停止，需要 Worker 在执行过程中周期性检查 execution_record 是否已取消。
- 未来若要强制终止，可以评估 `terminate=True`，但要先理解它对资源清理和任务一致性的风险。
