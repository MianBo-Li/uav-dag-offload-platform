# Git 使用规范

## 1. 为什么这个项目要用 Git

这个项目的目标不是只写出代码，而是完整学习一个项目从提出、分析、设计、实现到测试的过程。Git 应该用来记录这个过程，而不只是最后保存代码。

你要通过 Git 学会：

- 每个阶段如何形成可追踪的提交
- 如何用分支隔离不同任务
- 如何写清楚提交信息
- 如何在出错时回退到稳定版本
- 如何保留项目演进过程

## 2. 第一次初始化仓库

在项目根目录执行：

```powershell
git init
git add .
git commit -m "docs: initialize project proposal and requirements"
```

如果你还没有配置用户名和邮箱，先执行：

```powershell
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

## 3. 推荐分支模型

本项目建议使用简单分支模型：

- `main`：稳定主分支
- `feature/*`：功能开发分支
- `docs/*`：文档设计分支
- `experiment/*`：算法实验分支
- `fix/*`：问题修复分支

示例：

```powershell
git switch -c docs/system-design
git switch -c feature/node-management
git switch -c feature/dag-task-api
git switch -c experiment/greedy-scheduler
```

## 4. 当前阶段怎么提交

### 阶段 0：立项与需求

建议提交：

```powershell
git add docs .gitignore
git commit -m "docs: add project proposal and requirements analysis"
```

### 阶段 1：系统设计

建议分支：

```powershell
git switch -c docs/system-design
```

建议提交：

```powershell
git add docs/04_system_design.md
git commit -m "docs: add system architecture design"
```

### 阶段 2：后端骨架

建议分支：

```powershell
git switch -c feature/backend-scaffold
```

建议提交：

```powershell
git add .
git commit -m "feat: scaffold FastAPI backend application"
```

### 阶段 3：节点管理

建议分支：

```powershell
git switch -c feature/node-management
```

建议提交：

```powershell
git add .
git commit -m "feat: add node registration and heartbeat APIs"
```

### 阶段 4：DAG 任务管理

建议分支：

```powershell
git switch -c feature/dag-task-management
```

建议提交：

```powershell
git add .
git commit -m "feat: add DAG task creation and validation"
```

### 阶段 5：调度器

建议分支：

```powershell
git switch -c feature/scheduler
```

建议提交：

```powershell
git add .
git commit -m "feat: add pluggable scheduling strategies"
```

## 5. 提交信息规范

建议使用类似 Conventional Commits 的格式：

```text
类型: 简短描述
```

常用类型：

- `docs`：文档
- `feat`：新功能
- `fix`：修复问题
- `test`：测试
- `refactor`：重构
- `chore`：工程配置
- `perf`：性能优化

示例：

```text
docs: add requirements analysis
feat: add node registration API
fix: reject cyclic DAG tasks
test: add scheduler unit tests
chore: add docker compose services
```

## 6. 每次提交前检查

提交前先执行：

```powershell
git status
git diff
```

进入编码阶段后，还要执行：

```powershell
pytest
```

原则：

- 一个提交只做一类事情
- 不把临时文件、日志、虚拟环境提交进去
- 文档和代码尽量分开提交
- 提交信息要能看出这一步完成了什么

## 7. 推荐学习节奏

你可以把每个阶段都当成一次真实开发流程：

1. 开分支
2. 写文档或代码
3. 自测
4. 查看 diff
5. 提交
6. 合并回主分支

示例：

```powershell
git switch main
git switch -c docs/system-design

# 编辑 docs/04_system_design.md

git status
git diff
git add docs/04_system_design.md
git commit -m "docs: add system architecture design"

git switch main
git merge docs/system-design
```

## 8. 远程仓库建议

等项目进入代码阶段，可以创建 GitHub 仓库。

推荐仓库名：

```text
uav-dag-offload-platform
```

首次推送：

```powershell
git remote add origin https://github.com/<your-name>/uav-dag-offload-platform.git
git branch -M main
git push -u origin main
```

如果你希望项目更像正式工程，可以从第二阶段开始使用 Pull Request 方式合并分支。

