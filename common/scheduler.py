"""
基于 Redis 的分布式任务调度器

支持多实例部署、任务持久化和集群调度。
"""

import asyncio
import json
import time
import uuid
import threading
from typing import Optional, Dict, Any, List, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

from .cache import RedisCache, CacheConfig
from .exceptions import BusinessError


# ============================================================================
# 任务状态
# ============================================================================

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 执行中
    SUCCESS = "success"  # 执行成功
    FAILED = "failed"    # 执行失败
    CANCELLED = "cancelled"  # 已取消
    RETRY = "retry"      # 重试中


# ============================================================================
# 任务定义
# ============================================================================

@dataclass
class ScheduledTask:
    """定时任务"""
    id: str
    name: str
    cron_expression: str
    workflow_config: Dict[str, Any]
    enabled: bool = True
    next_run: Optional[str] = None
    last_run: Optional[str] = None
    run_count: int = 0
    failure_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        """从字典创建"""
        return cls(**data)


# ============================================================================
# Redis 任务存储
# ============================================================================

class RedisTaskStore:
    """Redis 任务存储后端"""

    def __init__(self, redis_cache: RedisCache):
        """
        初始化任务存储

        Args:
            redis_cache: Redis 缓存实例
        """
        self.redis = redis_cache
        self.key_prefix = "scheduler:"

    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self.key_prefix}{key}"

    async def add_task(self, task: ScheduledTask) -> bool:
        """
        添加任务

        Args:
            task: 定时任务

        Returns:
            是否添加成功
        """
        try:
            key = self._make_key(f"task:{task.id}")
            return self.redis.set(key, task.to_dict(), ttl=86400 * 30)  # 30天过期
        except Exception:
            return False

    async def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """
        获取任务

        Args:
            task_id: 任务 ID

        Returns:
            定时任务（如果存在）
        """
        try:
            key = self._make_key(f"task:{task_id}")
            data = self.redis.get(key)
            if data:
                return ScheduledTask.from_dict(data)
            return None
        except Exception:
            return None

    async def update_task(self, task: ScheduledTask) -> bool:
        """
        更新任务

        Args:
            task: 定时任务

        Returns:
            是否更新成功
        """
        return await self.add_task(task)  # 复用添加逻辑

    async def delete_task(self, task_id: str) -> bool:
        """
        删除任务

        Args:
            task_id: 任务 ID

        Returns:
            是否删除成功
        """
        try:
            key = self._make_key(f"task:{task_id}")
            return self.redis.delete(key)
        except Exception:
            return False

    async def list_tasks(
        self,
        enabled_only: bool = True
    ) -> List[ScheduledTask]:
        """
        列出所有任务

        Args:
            enabled_only: 是否只返回启用的任务

        Returns:
            任务列表
        """
        try:
            # 使用模式匹配获取所有任务键
            pattern = self._make_key("task:*")
            keys = self.redis._redis.keys(pattern)

            tasks = []
            for key in keys:
                data = self.redis.get(key)
                if data:
                    task = ScheduledTask.from_dict(data)
                    if not enabled_only or task.enabled:
                        tasks.append(task)

            return tasks
        except Exception:
            return []

    async def get_pending_tasks(self, limit: int = 10) -> List[ScheduledTask]:
        """
        获取待执行的任务

        Args:
            limit: 最大数量

        Returns:
            待执行的任务列表
        """
        try:
            pattern = self._make_key("task:*")
            keys = self.redis._redis.keys(pattern)

            pending_tasks = []
            now = datetime.now()

            for key in keys:
                data = self.redis.get(key)
                if data:
                    task = ScheduledTask.from_dict(data)
                    if task.enabled and task.next_run:
                        next_run_time = datetime.fromisoformat(task.next_run)
                        if next_run_time <= now:
                            pending_tasks.append(task)
                            if len(pending_tasks) >= limit:
                                break

            # 按照 next_run 排序
            pending_tasks.sort(key=lambda t: t.next_run or "")

            return pending_tasks
        except Exception:
            return []

    async def acquire_task_lock(
        self,
        task_id: str,
        instance_id: str,
        ttl: int = 300
    ) -> bool:
        """
        获取任务锁（用于防止并发执行）

        Args:
            task_id: 任务 ID
            instance_id: 实例 ID
            ttl: 锁的过期时间（秒）

        Returns:
            是否获取成功
        """
        try:
            lock_key = self._make_key(f"lock:{task_id}")
            lock_value = f"{instance_id}:{time.time()}"

            # 使用 SET NX EX 原子操作
            return self.redis._redis.set(lock_key, lock_value, nx=True, ex=ttl)
        except Exception:
            return False

    async def release_task_lock(self, task_id: str, instance_id: str) -> bool:
        """
        释放任务锁

        Args:
            task_id: 任务 ID
            instance_id: 实例 ID

        Returns:
            是否释放成功
        """
        try:
            lock_key = self._make_key(f"lock:{task_id}")
            current_value = self.redis._redis.get(lock_key)

            if current_value and current_value.startswith(instance_id):
                return self.redis._redis.delete(lock_key) > 0
            return False
        except Exception:
            return False


# ============================================================================
# 任务执行器
# ============================================================================

class TaskExecutor:
    """任务执行器"""

    def __init__(
        self,
        instance_id: Optional[str] = None,
        max_concurrent: int = 5
    ):
        """
        初始化任务执行器

        Args:
            instance_id: 实例 ID（如果为 None，自动生成）
            max_concurrent: 最大并发数
        """
        self.instance_id = instance_id or str(uuid.uuid4())
        self.max_concurrent = max_concurrent

        # 运行状态
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_task(
        self,
        task: ScheduledTask,
        workflow_func: Callable[[Dict[str, Any]], Awaitable[Any]]
    ) -> Dict[str, Any]:
        """
        执行任务

        Args:
            task: 定时任务
            workflow_func: 工作流执行函数

        Returns:
            执行结果
        """
        result = {
            "task_id": task.id,
            "instance_id": self.instance_id,
            "started_at": datetime.now().isoformat(),
            "status": TaskStatus.RUNNING
        }

        try:
            # 获取信号量（控制并发）
            await self._semaphore.acquire()

            # 记录任务
            self._running_tasks[task.id] = asyncio.current_task()

            # 执行工作流
            output = await workflow_func(task.workflow_config)

            result.update({
                "status": TaskStatus.SUCCESS,
                "completed_at": datetime.now().isoformat(),
                "output": output
            })

        except Exception as e:
            result.update({
                "status": TaskStatus.FAILED,
                "completed_at": datetime.now().isoformat(),
                "error": str(e)
            })

        finally:
            # 清理任务
            if task.id in self._running_tasks:
                del self._running_tasks[task.id]

            # 释放信号量
            self._semaphore.release()

        return result

    def get_running_tasks(self) -> List[str]:
        """获取正在运行的任务 ID 列表"""
        return list(self._running_tasks.keys())

    def get_stats(self) -> Dict[str, Any]:
        """获取执行器统计信息"""
        return {
            "instance_id": self.instance_id,
            "max_concurrent": self.max_concurrent,
            "running_tasks": len(self._running_tasks),
            "available_slots": self._semaphore._value
        }


# ============================================================================
# 分布式调度器
# ============================================================================

class DistributedScheduler:
    """分布式调度器"""

    def __init__(
        self,
        redis_cache: Optional[RedisCache] = None,
        executor: Optional[TaskExecutor] = None,
        tick_interval: float = 1.0
    ):
        """
        初始化分布式调度器

        Args:
            redis_cache: Redis 缓存实例
            executor: 任务执行器
            tick_interval: 调度间隔（秒）
        """
        self.redis_cache = redis_cache or RedisCache()
        self.task_store = RedisTaskStore(self.redis_cache)
        self.executor = executor or TaskExecutor()
        self.tick_interval = tick_interval

        # 工作流注册表
        self._workflows: Dict[str, Callable] = {}

        # 运行状态
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

    def register_workflow(
        self,
        name: str,
        func: Callable[[Dict[str, Any]], Awaitable[Any]]
    ) -> None:
        """
        注册工作流

        Args:
            name: 工作流名称
            func: 工作流执行函数
        """
        self._workflows[name] = func

    async def add_task(
        self,
        name: str,
        cron_expression: str,
        workflow_config: Dict[str, Any],
        enabled: bool = True
    ) -> str:
        """
        添加定时任务

        Args:
            name: 任务名称
            cron_expression: Cron 表达式
            workflow_config: 工作流配置
            enabled: 是否启用

        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())
        now = datetime.now()

        # 计算下次执行时间
        from common.validators import CronExpression
        cron = CronExpression(expression=cron_expression)
        next_run = self._calculate_next_run(cron)

        task = ScheduledTask(
            id=task_id,
            name=name,
            cron_expression=cron_expression,
            workflow_config=workflow_config,
            enabled=enabled,
            next_run=next_run.isoformat() if next_run else None,
            created_at=now.isoformat(),
            updated_at=now.isoformat()
        )

        await self.task_store.add_task(task)
        return task_id

    async def remove_task(self, task_id: str) -> bool:
        """
        移除任务

        Args:
            task_id: 任务 ID

        Returns:
            是否移除成功
        """
        return await self.task_store.delete_task(task_id)

    async def enable_task(self, task_id: str) -> bool:
        """
        启用任务

        Args:
            task_id: 任务 ID

        Returns:
            是否启用成功
        """
        task = await self.task_store.get_task(task_id)
        if task:
            task.enabled = True
            task.updated_at = datetime.now().isoformat()
            return await self.task_store.update_task(task)
        return False

    async def disable_task(self, task_id: str) -> bool:
        """
        禁用任务

        Args:
            task_id: 任务 ID

        Returns:
            是否禁用成功
        """
        task = await self.task_store.get_task(task_id)
        if task:
            task.enabled = False
            task.updated_at = datetime.now().isoformat()
            return await self.task_store.update_task(task)
        return False

    async def list_tasks(self, enabled_only: bool = False) -> List[ScheduledTask]:
        """
        列出所有任务

        Args:
            enabled_only: 是否只返回启用的任务

        Returns:
            任务列表
        """
        return await self.task_store.list_tasks(enabled_only=enabled_only)

    def _calculate_next_run(self, cron_expression) -> Optional[datetime]:
        """
        计算下次运行时间

        Args:
            cron_expression: Cron 表达式验证器

        Returns:
            下次运行时间
        """
        # 简化版本：返回下一分钟的整点
        # 实际实现应使用 croniter 库精确计算
        now = datetime.now()
        next_minute = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        return next_minute

    async def _schedule_task(self, task: ScheduledTask) -> Optional[Dict[str, Any]]:
        """
        调度单个任务

        Args:
            task: 定时任务

        Returns:
            执行结果
        """
        # 尝试获取锁（防止多实例并发执行）
        lock_acquired = await self.task_store.acquire_task_lock(
            task.id,
            self.executor.instance_id,
            ttl=300
        )

        if not lock_acquired:
            # 其他实例正在处理
            return None

        try:
            # 更新任务状态
            task.last_run = datetime.now().isoformat()
            task.run_count += 1
            await self.task_store.update_task(task)

            # 获取工作流函数
            workflow_name = task.workflow_config.get("workflow", task.name)
            workflow_func = self._workflows.get(workflow_name)

            if not workflow_func:
                result = {
                    "status": TaskStatus.FAILED,
                    "error": f"Workflow not found: {workflow_name}"
                }
            else:
                # 执行任务
                result = await self.executor.execute_task(task, workflow_func)

            # 更新任务状态和计算下次运行时间
            if result["status"] == TaskStatus.SUCCESS:
                # 成功：计算下次运行时间
                task.next_run = self._calculate_next_run(None).isoformat()
            elif result["status"] == TaskStatus.FAILED:
                # 失败：增加失败计数
                task.failure_count += 1

                # 如果失败次数过多，禁用任务
                if task.failure_count >= 3:
                    task.enabled = False

            await self.task_store.update_task(task)

            return result

        finally:
            # 释放锁
            await self.task_store.release_task_lock(task.id, self.executor.instance_id)

    async def _scheduler_loop(self):
        """调度循环"""
        while self._running:
            try:
                # 获取待执行的任务
                pending_tasks = await self.task_store.get_pending_tasks(limit=10)

                for task in pending_tasks:
                    if not self._running:
                        break

                    # 异步调度任务
                    asyncio.create_task(self._schedule_task(task))

                # 等待下次调度
                await asyncio.sleep(self.tick_interval)

            except Exception as e:
                # 记录错误但继续运行
                print(f"Scheduler error: {e}")
                await asyncio.sleep(self.tick_interval)

    async def start(self):
        """启动调度器"""
        if self._running:
            return

        self._running = True

        # 连接到 Redis
        if not self.redis_cache.is_connected():
            self.redis_cache.connect()

        # 启动调度循环
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        """停止调度器"""
        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # 等待正在运行的任务完成
        while self.executor.get_running_tasks():
            await asyncio.sleep(0.1)

    def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        return {
            "running": self._running,
            "executor_stats": self.executor.get_stats(),
            "registered_workflows": list(self._workflows.keys())
        }


# ============================================================================
# 全局实例
# ============================================================================

# 默认分布式调度器
default_scheduler = DistributedScheduler()
