"""
统一缓存管理器

提供多级缓存功能和智能缓存策略。
"""

import time
import json
import hashlib
import asyncio
from typing import Optional, Any, Dict, List, Callable, TypeVar, Union
from functools import wraps
from pathlib import Path

from .cache import RedisCache, MemoryCache, CacheConfig
from .async_file import AsyncFileHandler
from .database import DatabaseManager


# ============================================================================
# 缓存级别
# ============================================================================

class CacheLevel:
    """缓存级别"""

    L1_MEMORY = 1  # 内存缓存（最快）
    L2_REDIS = 2  # Redis 缓存（快）
    L3_DATABASE = 3  # 数据库（慢）
    L4_FILE = 4  # 文件系统（最慢）


# ============================================================================
# 多级缓存管理器
# ============================================================================

class MultiLevelCacheManager:
    """多级缓存管理器"""

    def __init__(
        self,
        redis_config: Optional[CacheConfig] = None,
        file_handler: Optional[AsyncFileHandler] = None,
        db_manager: Optional[DatabaseManager] = None
    ):
        """
        初始化多级缓存管理器

        Args:
            redis_config: Redis 配置
            file_handler: 文件处理器
            db_manager: 数据库管理器
        """
        # L1: 内存缓存
        self.memory_cache = MemoryCache(default_ttl=300)  # 5分钟

        # L2: Redis 缓存
        self.redis_cache = RedisCache(redis_config) if redis_config else None

        # L3: 数据库
        self.db_manager = db_manager

        # L4: 文件系统
        self.file_handler = file_handler or AsyncFileHandler()

        # 缓存统计
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }

    async def get(self, key: str, level: int = CacheLevel.L1_MEMORY) -> Optional[Any]:
        """
        获取缓存值（自动回溯到更低级别）

        Args:
            key: 键
            level: 起始缓存级别

        Returns:
            缓存值
        """
        # L1: 内存缓存
        if level <= CacheLevel.L1_MEMORY:
            value = self.memory_cache.get(key)
            if value is not None:
                self._stats["hits"] += 1
                return value

        # L2: Redis 缓存
        if level <= CacheLevel.L2_REDIS and self.redis_cache:
            if self.redis_cache.is_connected():
                value = self.redis_cache.get(key)
                if value is not None:
                    # 回填 L1
                    self.memory_cache.set(key, value, ttl=300)
                    self._stats["hits"] += 1
                    return value

        # L3: 数据库
        if level <= CacheLevel.L3_DATABASE and self.db_manager:
            try:
                # 尝试从数据库获取
                parts = key.split(":")
                if len(parts) >= 2:
                    table = parts[0]
                    record_id = parts[1]

                    # 查询数据库
                    rows = self.db_manager.select(
                        table,
                        where={"id": record_id},
                        limit=1
                    )

                    if rows:
                        value = dict(rows[0])

                        # 回填 L2 和 L1
                        if self.redis_cache and self.redis_cache.is_connected():
                            self.redis_cache.set(key, value, ttl=3600)
                        self.memory_cache.set(key, value, ttl=300)

                        self._stats["hits"] += 1
                        return value
            except Exception:
                pass

        # L4: 文件系统
        if level <= CacheLevel.L4_FILE:
            try:
                file_path = Path("cache") / f"{key}.json"
                if await self.file_handler.exists(file_path):
                    value = await self.file_handler.read_json(file_path)

                    # 回填上级缓存
                    if self.redis_cache and self.redis_cache.is_connected():
                        self.redis_cache.set(key, value, ttl=3600)
                    self.memory_cache.set(key, value, ttl=300)

                    self._stats["hits"] += 1
                    return value
            except Exception:
                pass

        self._stats["misses"] += 1
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        level: int = CacheLevel.L1_MEMORY
    ) -> bool:
        """
        设置缓存值（写入指定级别及更高级别）

        Args:
            key: 键
            value: 值
            ttl: 过期时间（秒）
            level: 写入级别

        Returns:
            是否成功
        """
        success = True

        # L1: 内存缓存
        if level >= CacheLevel.L1_MEMORY:
            if not self.memory_cache.set(key, value, ttl=ttl):
                success = False

        # L2: Redis 缓存
        if level >= CacheLevel.L2_REDIS and self.redis_cache:
            if self.redis_cache.is_connected():
                if not self.redis_cache.set(key, value, ttl=ttl):
                    success = False

        # L3: 数据库（特殊处理）
        if level >= CacheLevel.L3_DATABASE and self.db_manager:
            # 数据库写入需要特殊处理，跳过
            pass

        # L4: 文件系统
        if level >= CacheLevel.L4_FILE:
            try:
                cache_dir = Path("cache")
                cache_dir.mkdir(parents=True, exist_ok=True)
                file_path = cache_dir / f"{key}.json"
                await self.file_handler.write_json(file_path, value)
            except Exception:
                success = False

        if success:
            self._stats["sets"] += 1

        return success

    async def delete(self, key: str, level: int = CacheLevel.L1_MEMORY) -> bool:
        """
        删除缓存值（从指定级别及更高级别删除）

        Args:
            key: 键
            level: 删除级别

        Returns:
            是否成功
        """
        success = True

        # L1: 内存缓存
        if level >= CacheLevel.L1_MEMORY:
            self.memory_cache.delete(key)

        # L2: Redis 缓存
        if level >= CacheLevel.L2_REDIS and self.redis_cache:
            if self.redis_cache.is_connected():
                self.redis_cache.delete(key)

        # L4: 文件系统
        if level >= CacheLevel.L4_FILE:
            try:
                file_path = Path("cache") / f"{key}.json"
                await self.file_handler.delete(file_path)
            except Exception:
                pass

        self._stats["deletes"] += 1
        return success

    async def get_or_set(
        self,
        key: str,
        value_func: Callable,
        ttl: Optional[int] = None,
        level: int = CacheLevel.L1_MEMORY
    ) -> Any:
        """
        获取缓存值，如果不存在则设置

        Args:
            key: 键
            value_func: 值生成函数
            ttl: 过期时间
            level: 缓存级别

        Returns:
            缓存值
        """
        # 尝试获取
        value = await self.get(key, level=level)
        if value is not None:
            return value

        # 生成新值
        if asyncio.iscoroutinefunction(value_func):
            value = await value_func()
        else:
            value = value_func()

        # 设置缓存
        await self.set(key, value, ttl=ttl, level=level)

        return value

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0

        return {
            **self._stats,
            "total": total,
            "hit_rate": hit_rate,
            "miss_rate": 1 - hit_rate
        }

    async def clear_level(self, level: int) -> None:
        """
        清空指定级别的缓存

        Args:
            level: 缓存级别
        """
        if level >= CacheLevel.L1_MEMORY:
            self.memory_cache.clear()

        if level >= CacheLevel.L2_REDIS and self.redis_cache:
            if self.redis_cache.is_connected():
                self.redis_cache.clear_all()

        if level >= CacheLevel.L4_FILE:
            import shutil
            cache_dir = Path("cache")
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 缓存键生成器
# ============================================================================

class CacheKeyGenerator:
    """缓存键生成器"""

    @staticmethod
    def generate(prefix: str, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            prefix: 键前缀
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存键
        """
        parts = [prefix]

        # 添加位置参数
        if args:
            parts.extend(str(arg) for arg in args)

        # 添加关键字参数（排序确保一致性）
        if kwargs:
            sorted_items = sorted(kwargs.items())
            parts.extend(f"{k}={v}" for k, v in sorted_items)

        key = ":".join(parts)

        # 如果键太长，使用哈希
        if len(key) > 200:
            key_hash = hashlib.md5(key.encode()).hexdigest()[:16]
            return f"{prefix}:{key_hash}"

        return key

    @staticmethod
    def for_user(user_id: str, resource: str, resource_id: Optional[str] = None) -> str:
        """生成用户相关的缓存键"""
        if resource_id:
            return f"user:{user_id}:{resource}:{resource_id}"
        return f"user:{user_id}:{resource}"

    @staticmethod
    def for_account(account_id: str, resource: str, resource_id: Optional[str] = None) -> str:
        """生成账号相关的缓存键"""
        if resource_id:
            return f"account:{account_id}:{resource}:{resource_id}"
        return f"account:{account_id}:{resource}"

    @staticmethod
    def for_query(table: str, params: Dict[str, Any]) -> str:
        """生成查询相关的缓存键"""
        # 对参数排序确保一致性
        sorted_params = sorted(params.items())
        params_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        return f"query:{table}:{hashlib.md5(params_str.encode()).hexdigest()[:16]}"


# ============================================================================
# 全局实例
# ============================================================================

# 默认多级缓存管理器
default_cache_manager = MultiLevelCacheManager()


# ============================================================================
# 缓存装饰器
# ============================================================================

T = TypeVar('T')


def cached(
    prefix: str,
    ttl: int = 3600,
    level: int = CacheLevel.L1_MEMORY,
    key_generator: Optional[Callable] = None
):
    """
    缓存装饰器（异步）

    Args:
        prefix: 键前缀
        ttl: 过期时间（秒）
        level: 缓存级别
        key_generator: 键生成函数

    Returns:
        装饰器函数

    Example:
        @cached("user", ttl=1800)
        async def get_user(user_id: str):
            return await fetch_user_from_db(user_id)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # 生成缓存键
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = CacheKeyGenerator.generate(prefix, *args, **kwargs)

            # 尝试从缓存获取
            value = await default_cache_manager.get(cache_key, level=level)
            if value is not None:
                return value

            # 执行函数
            result = await func(*args, **kwargs)

            # 存入缓存
            await default_cache_manager.set(cache_key, result, ttl=ttl, level=level)

            return result

        return wrapper

    return decorator


# ============================================================================
# 便捷函数
# ============================================================================

async def cache_get(key: str) -> Optional[Any]:
    """获取缓存值"""
    return await default_cache_manager.get(key)


async def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置缓存值"""
    return await default_cache_manager.set(key, value, ttl=ttl)


async def cache_delete(key: str) -> bool:
    """删除缓存值"""
    return await default_cache_manager.delete(key)


async def cache_get_stats() -> Dict[str, Any]:
    """获取缓存统计"""
    return default_cache_manager.get_stats()
