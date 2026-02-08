"""
Redis 缓存管理器

提供高性能的缓存功能，支持多种数据类型和操作。
"""

import json
import time
import hashlib
from typing import Optional, Any, Dict, List, Union, Callable
from functools import wraps

from .exceptions import ConfigurationError


# ============================================================================
# 缓存配置
# ============================================================================

class CacheConfig:
    """缓存配置"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 3600,
        key_prefix: str = "mcp:",
        max_connections: int = 10
    ):
        """
        初始化缓存配置

        Args:
            host: Redis 主机
            port: Redis 端口
            db: 数据库编号
            password: 密码
            default_ttl: 默认过期时间（秒）
            key_prefix: 键前缀
            max_connections: 最大连接数
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.max_connections = max_connections


# ============================================================================
# Redis 缓存管理器
# ============================================================================

class RedisCache:
    """Redis 缓存管理器"""

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        初始化 Redis 缓存管理器

        Args:
            config: 缓存配置（如果为 None，使用默认配置）
        """
        self.config = config or CacheConfig()
        self._redis = None
        self._connected = False

    def connect(self) -> None:
        """连接到 Redis"""
        try:
            import redis
            self._redis = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                max_connections=self.config.max_connections,
                decode_responses=True
            )
            # 测试连接
            self._redis.ping()
            self._connected = True
        except ImportError:
            raise ConfigurationError(
                message="Redis package not installed",
                user_message="Redis 未安装，请运行: pip install redis"
            )
        except Exception as e:
            raise ConfigurationError(
                message=f"Failed to connect to Redis: {str(e)}",
                user_message="无法连接到 Redis"
            )

    def disconnect(self) -> None:
        """断开 Redis 连接"""
        if self._redis:
            self._redis.close()
            self._connected = False

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self._redis is not None

    def _make_key(self, key: str) -> str:
        """
        生成带前缀的键

        Args:
            key: 原始键

        Returns:
            带前缀的键
        """
        return f"{self.config.key_prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 键

        Returns:
            缓存值（如果存在）
        """
        if not self.is_connected():
            return None

        try:
            redis_key = self._make_key(key)
            value = self._redis.get(redis_key)

            if value is None:
                return None

            # 尝试解析 JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception:
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 键
            value: 值
            ttl: 过期时间（秒），如果为 None，使用默认 TTL

        Returns:
            是否设置成功
        """
        if not self.is_connected():
            return False

        try:
            redis_key = self._make_key(key)

            # 序列化值
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            else:
                serialized = str(value)

            # 设置过期时间
            expire_time = ttl if ttl is not None else self.config.default_ttl

            if expire_time > 0:
                return self._redis.setex(redis_key, expire_time, serialized)
            else:
                return self._redis.set(redis_key, serialized)
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存值

        Args:
            key: 键

        Returns:
            是否删除成功
        """
        if not self.is_connected():
            return False

        try:
            redis_key = self._make_key(key)
            return self._redis.delete(redis_key) > 0
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键

        Returns:
            键是否存在
        """
        if not self.is_connected():
            return False

        try:
            redis_key = self._make_key(key)
            return self._redis.exists(redis_key) > 0
        except Exception:
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """
        设置键的过期时间

        Args:
            key: 键
            ttl: 过期时间（秒）

        Returns:
            是否设置成功
        """
        if not self.is_connected():
            return False

        try:
            redis_key = self._make_key(key)
            return self._redis.expire(redis_key, ttl)
        except Exception:
            return False

    def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间

        Args:
            key: 键

        Returns:
            剩余时间（秒），-1 表示永不过期，-2 表示键不存在
        """
        if not self.is_connected():
            return -2

        try:
            redis_key = self._make_key(key)
            return self._redis.ttl(redis_key)
        except Exception:
            return -2

    def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """
        原子递增

        Args:
            key: 键
            delta: 递增量

        Returns:
            递增后的值
        """
        if not self.is_connected():
            return None

        try:
            redis_key = self._make_key(key)
            return self._redis.incrby(redis_key, delta)
        except Exception:
            return None

    def decrement(self, key: str, delta: int = 1) -> Optional[int]:
        """
        原子递减

        Args:
            key: 键
            delta: 递减量

        Returns:
            递减后的值
        """
        if not self.is_connected():
            return None

        try:
            redis_key = self._make_key(key)
            return self._redis.decrby(redis_key, delta)
        except Exception:
            return None

    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        批量获取缓存值

        Args:
            keys: 键列表

        Returns:
            键到值的映射
        """
        if not self.is_connected() or not keys:
            return {}

        try:
            redis_keys = [self._make_key(k) for k in keys]
            values = self._redis.mget(redis_keys)

            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        result[key] = value

            return result
        except Exception:
            return {}

    def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        批量设置缓存值

        Args:
            mapping: 键值映射
            ttl: 过期时间（秒）

        Returns:
            是否全部设置成功
        """
        if not self.is_connected() or not mapping:
            return False

        try:
            pipe = self._redis.pipeline()

            for key, value in mapping.items():
                redis_key = self._make_key(key)

                # 序列化值
                if isinstance(value, (dict, list)):
                    serialized = json.dumps(value)
                else:
                    serialized = str(value)

                # 设置过期时间
                expire_time = ttl if ttl is not None else self.config.default_ttl

                if expire_time > 0:
                    pipe.setex(redis_key, expire_time, serialized)
                else:
                    pipe.set(redis_key, serialized)

            pipe.execute()
            return True
        except Exception:
            return False

    def delete_many(self, keys: List[str]) -> int:
        """
        批量删除缓存值

        Args:
            keys: 键列表

        Returns:
            删除的键数量
        """
        if not self.is_connected() or not keys:
            return 0

        try:
            redis_keys = [self._make_key(k) for k in keys]
            return self._redis.delete(*redis_keys)
        except Exception:
            return 0

    def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的所有键

        Args:
            pattern: 键模式（支持通配符 *）

        Returns:
            清除的键数量
        """
        if not self.is_connected():
            return 0

        try:
            search_pattern = self._make_key(pattern)
            keys = self._redis.keys(search_pattern)

            if keys:
                return self._redis.delete(*keys)
            return 0
        except Exception:
            return 0

    def clear_all(self) -> bool:
        """
        清除所有缓存

        Returns:
            是否清除成功
        """
        if not self.is_connected():
            return False

        try:
            # 只清除带有前缀的键
            pattern = f"{self.config.key_prefix}*"
            return self.clear_pattern(pattern) > 0
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息
        """
        if not self.is_connected():
            return {"connected": False}

        try:
            info = self._redis.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "total_connections": info.get("total_connections_received", 0),
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace": info.get(f"db{self.config.db}", {})
            }
        except Exception:
            return {"connected": True}


# ============================================================================
# 内存缓存（Redis 不可用时的后备方案）
# ============================================================================

class MemoryCache:
    """内存缓存（线程安全）"""

    def __init__(self, default_ttl: int = 3600):
        """
        初始化内存缓存

        Args:
            default_ttl: 默认过期时间（秒）
        """
        import threading

        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                return None

            value, expire_time = self._cache[key]

            # 检查是否过期
            if expire_time > 0 and time.time() > expire_time:
                del self._cache[key]
                return None

            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        with self._lock:
            expire_time = ttl if ttl is not None else self.default_ttl
            if expire_time > 0:
                expire_at = time.time() + expire_time
            else:
                expire_at = -1  # 永不过期

            self._cache[key] = (value, expire_at)
            return True

    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            return key in self._cache

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()


# ============================================================================
# 缓存装饰器
# ============================================================================

def cached(
    key_func: Optional[Callable] = None,
    ttl: int = 3600,
    cache_instance: Optional[RedisCache] = None
):
    """
    缓存装饰器

    Args:
        key_func: 生成缓存键的函数
        ttl: 过期时间（秒）
        cache_instance: 缓存实例

    Returns:
        装饰器函数

    Example:
        @cached(key_func=lambda user_id: f"user:{user_id}", ttl=1800)
        def get_user(user_id: str):
            return fetch_user_from_db(user_id)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 使用函数名和参数生成键
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

            # 尝试从缓存获取
            if cache_instance:
                cached_value = cache_instance.get(cache_key)
                if cached_value is not None:
                    return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            if cache_instance:
                cache_instance.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


# ============================================================================
# 全局实例
# ============================================================================

# 默认 Redis 缓存
default_redis_cache = RedisCache()

# 默认内存缓存
default_memory_cache = MemoryCache()


# ============================================================================
# 便捷函数
# ============================================================================

def get_cache() -> Union[RedisCache, MemoryCache]:
    """获取缓存实例（优先使用 Redis）"""
    try:
        if not default_redis_cache.is_connected():
            default_redis_cache.connect()
        return default_redis_cache
    except Exception:
        return default_memory_cache


def cache_get(key: str) -> Optional[Any]:
    """获取缓存值"""
    cache = get_cache()
    return cache.get(key)


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置缓存值"""
    cache = get_cache()
    return cache.set(key, value, ttl=ttl)


def cache_delete(key: str) -> bool:
    """删除缓存值"""
    cache = get_cache()
    return cache.delete(key)


def cache_clear() -> None:
    """清空缓存"""
    cache = get_cache()
    if hasattr(cache, 'clear_all'):
        cache.clear_all()
    elif hasattr(cache, 'clear'):
        cache.clear()
