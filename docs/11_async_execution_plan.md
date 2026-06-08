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
- Celery Worker 临时基础设施异常自动重试。

当前版本暂不实现：

- 超时检测。
- Worker 心跳。
- 任务取消后通知 Worker。
- 多 worker 并发下的幂等锁。
- RabbitMQ 消息积压指标。
- 死信队列和重试耗尽告警。
- outbox pattern。

这些是后续真实化阶段继续学习的内容。

## 8. 下一步学习重点

RabbitMQ / Celery 的第一版学习目标已经完成。后续可以继续推进：

1. 多 Worker 并发下的执行结果幂等锁。
2. Worker 心跳和 RabbitMQ 队列积压监控。
3. 任务取消和 Worker 正在执行之间的协调。
4. 死信队列和 Celery 重试耗尽后的告警。
5. outbox pattern，避免数据库提交成功但消息投递失败。

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
```

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
- Worker 心跳和队列积压监控。
