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
