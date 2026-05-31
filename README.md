# UAV DAG Offload Platform

面向无人机边缘计算的 DAG 任务卸载调度系统。

## Development

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
pytest
```

Health check:

```text
GET /api/v1/health
```

Prometheus-style metrics:

```text
GET /metrics
```

## Docker Compose

Start the local stack after Docker Desktop is running:

```powershell
docker compose up --build
```

Services:

```text
api        http://localhost:8000
worker     Celery execution worker
postgres   localhost:5432
redis      localhost:6379
rabbitmq   localhost:5672
rabbitmq UI http://localhost:15672
prometheus http://localhost:9090
grafana    http://localhost:3000
```

Grafana default login:

```text
admin / admin
```

RabbitMQ default login:

```text
guest / guest
```

See [docs/10_docker_compose.md](docs/10_docker_compose.md) for the learning notes and command reference.
See [docs/11_async_execution_plan.md](docs/11_async_execution_plan.md) for the Celery/RabbitMQ learning notes.
