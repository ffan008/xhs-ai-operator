"""
API 客户端模块

提供高性能的 HTTP 客户端，支持连接池、重试、超时、熔断等功能。
"""

import asyncio
import time
import hashlib
import json
from typing import (
    Optional, Dict, Any, List, Callable, Awaitable, Union,
    Tuple
)
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from .cache import RedisCache, MemoryCache
from .exceptions import BusinessError


# ============================================================================
# 熔断器状态
# ============================================================================

class CircuitState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"       # 关闭（正常）
    OPEN = "open"          # 开启（熔断）
    HALF_OPEN = "half_open"  # 半开（试探）


# ============================================================================
# 熔断器
# ============================================================================

@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5          # 失败阈值
    success_threshold: int = 2          # 成功阈值（半开状态）
    timeout: float = 60.0               # 熔断超时（秒）
    rolling_window: int = 10            # 滚动窗口大小


class CircuitBreaker:
    """熔断器"""

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        初始化熔断器

        Args:
            name: 熔断器名称
            config: 熔断器配置
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # 状态
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._opened_at: Optional[float] = None

        # 滚动窗口（记录最近的请求结果）
        self._rolling_window: deque[bool] = deque(maxlen=self.config.rolling_window)

    def _can_attempt(self) -> bool:
        """是否可以尝试请求"""
        now = time.time()

        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            # 检查是否超时
            if self._opened_at and (now - self._opened_at) >= self.config.timeout:
                # 转为半开状态
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            return True

        return False

    def _record_success(self) -> None:
        """记录成功"""
        self._rolling_window.append(True)
        self._last_failure_time = None

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            # 达到成功阈值，恢复关闭状态
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0

    def _record_failure(self) -> None:
        """记录失败"""
        self._rolling_window.append(False)
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # 半开状态失败，重新打开
            self._state = CircuitState.OPEN
            self._opened_at = time.time()
            self._success_count = 0
        else:
            # 检查是否需要打开熔断器
            recent_failures = sum(1 for r in self._rolling_window if not r)
            if recent_failures >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                self._opened_at = time.time()

    def get_state(self) -> CircuitState:
        """获取当前状态"""
        # 检查是否需要从 OPEN 转为 HALF_OPEN
        if self._state == CircuitState.OPEN and self._can_attempt():
            pass  # _can_attempt 已经处理了状态转换

        return self._state

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        recent_failures = sum(1 for r in self._rolling_window if not r)
        recent_successes = sum(1 for r in self._rolling_window if r)

        return {
            "name": self.name,
            "state": self.get_state().value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "recent_failures": recent_failures,
            "recent_successes": recent_successes,
            "opened_at": datetime.fromtimestamp(self._opened_at).isoformat() if self._opened_at else None,
            "last_failure_time": datetime.fromtimestamp(self._last_failure_time).isoformat() if self._last_failure_time else None
        }

    def reset(self) -> None:
        """重置熔断器"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._opened_at = None
        self._rolling_window.clear()


# ============================================================================
# 重试策略
# ============================================================================

@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3                    # 最大尝试次数
    base_delay: float = 1.0                  # 基础延迟（秒）
    max_delay: float = 60.0                  # 最大延迟（秒）
    exponential_base: float = 2.0            # 指数基数
    jitter: bool = True                      # 添加随机抖动
    retryable_status_codes: List[int] = field(default_factory=lambda: [
        408,  # Request Timeout
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504   # Gateway Timeout
    ])
    retryable_exceptions: List[str] = field(default_factory=lambda: [
        "TimeoutException",
        "ConnectError",
        "ConnectTimeout"
    ])


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    计算重试延迟（指数退避）

    Args:
        attempt: 当前尝试次数
        config: 重试配置

    Returns:
        延迟时间（秒）
    """
    # 指数退避
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))

    # 限制最大延迟
    delay = min(delay, config.max_delay)

    # 添加随机抖动（±25%）
    if config.jitter:
        import random
        delay = delay * (0.75 + random.random() * 0.5)

    return delay


# ============================================================================
# 请求缓存
# ============================================================================

class RequestCache:
    """请求缓存"""

    def __init__(self, cache: Optional[Union[RedisCache, MemoryCache]] = None):
        """
        初始化请求缓存

        Args:
            cache: 缓存实例
        """
        self.cache = cache or MemoryCache()

    def _make_cache_key(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成缓存键

        Args:
            method: HTTP 方法
            url: 请求 URL
            params: 查询参数
            json_data: JSON 数据

        Returns:
            缓存键
        """
        # 只缓存 GET 请求
        if method.upper() != "GET":
            return None

        # 生成唯一键
        key_parts = [method.upper(), url]

        if params:
            params_str = json.dumps(params, sort_keys=True)
            key_parts.append(params_str)

        if json_data:
            json_str = json.dumps(json_data, sort_keys=True)
            key_parts.append(json_str)

        key_string = ":".join(key_parts)
        hash_value = hashlib.md5(key_string.encode()).hexdigest()

        return f"api_cache:{hash_value}"

    def get(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取缓存的响应

        Args:
            method: HTTP 方法
            url: 请求 URL
            params: 查询参数
            json_data: JSON 数据

        Returns:
            缓存的响应（如果存在）
        """
        cache_key = self._make_cache_key(method, url, params, json_data)

        if not cache_key:
            return None

        return self.cache.get(cache_key)

    def set(
        self,
        method: str,
        url: str,
        response: Dict[str, Any],
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        ttl: int = 300
    ) -> None:
        """
        缓存响应

        Args:
            method: HTTP 方法
            url: 请求 URL
            response: 响应数据
            params: 查询参数
            json_data: JSON 数据
            ttl: 缓存时间（秒）
        """
        cache_key = self._make_cache_key(method, url, params, json_data)

        if not cache_key:
            return

        self.cache.set(cache_key, response, ttl=ttl)

    def invalidate(
        self,
        url: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> None:
        """
        使缓存失效

        Args:
            url: 指定 URL
            pattern: URL 模式
        """
        if isinstance(self.cache, RedisCache):
            if pattern:
                self.cache.clear_pattern(f"api_cache:*{pattern}*")
            elif url:
                # 使该 URL 的所有缓存失效
                self.cache.clear_pattern(f"api_cache:*{hashlib.md5(url.encode()).hexdigest()}*")
        else:
            # 内存缓存：清空所有
            self.cache.clear()


# ============================================================================
# 请求去重
# ============================================================================

class RequestDeduplicator:
    """请求去重器"""

    def __init__(self, ttl: int = 10):
        """
        初始化去重器

        Args:
            ttl: 请求记录保留时间（秒）
        """
        self.cache = MemoryCache(default_ttl=ttl)
        self._pending: Dict[str, asyncio.Event] = {}

    def _make_key(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成请求键"""
        key_parts = [method.upper(), url]

        if params:
            params_str = json.dumps(params, sort_keys=True)
            key_parts.append(params_str)

        if json_data:
            json_str = json.dumps(json_data, sort_keys=True)
            key_parts.append(json_str)

        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def acquire(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[asyncio.Event]]:
        """
        获取请求锁

        Args:
            method: HTTP 方法
            url: 请求 URL
            params: 查询参数
            json_data: JSON 数据

        Returns:
            (是否继续执行, 等待事件)
        """
        key = self._make_key(method, url, params, json_data)

        # 检查是否已有相同请求在进行
        if key in self._pending:
            return False, self._pending[key]

        # 记录新请求
        self._pending[key] = asyncio.Event()
        return True, None

    async def release(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        释放请求锁

        Args:
            method: HTTP 方法
            url: 请求 URL
            params: 查询参数
            json_data: JSON 数据
        """
        key = self._make_key(method, url, params, json_data)

        if key in self._pending:
            # 通知等待者
            self._pending[key].set()
            # 延迟删除（避免快速重复请求）
            await asyncio.sleep(0.1)
            del self._pending[key]


# ============================================================================
# API 客户端配置
# ============================================================================

@dataclass
class APIConfig:
    """API 客户端配置"""
    base_url: str = ""
    timeout: float = 30.0                   # 请求超时（秒）
    connect_timeout: float = 10.0           # 连接超时（秒）
    max_connections: int = 100              # 最大连接数
    max_keepalive_connections: int = 20     # 最大保持连接数
    keepalive_expiry: float = 5.0           # 保持连接过期时间（秒）

    # 重试配置
    retry_config: Optional[RetryConfig] = None

    # 熔断器配置
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None

    # 缓存配置
    enable_cache: bool = True               # 是否启用缓存
    cache_ttl: int = 300                    # 缓存时间（秒）

    # 去重配置
    enable_dedup: bool = True               # 是否启用去重
    dedup_ttl: int = 10                     # 去重时间（秒）

    # 其他
    verify_ssl: bool = True                 # 验证 SSL
    follow_redirects: bool = True           # 跟随重定向
    max_redirects: int = 10                 # 最大重定向次数


# ============================================================================
# API 客户端
# ============================================================================

class APIClient:
    """API 客户端"""

    def __init__(
        self,
        config: Optional[APIConfig] = None,
        name: str = "default"
    ):
        """
        初始化 API 客户端

        Args:
            config: 客户端配置
            name: 客户端名称
        """
        self.config = config or APIConfig()
        self.name = name

        # HTTPX 客户端
        self._client: Optional[httpx.AsyncClient] = None

        # 熔断器
        self._circuit_breaker = CircuitBreaker(
            name=name,
            config=self.config.circuit_breaker_config
        )

        # 请求缓存
        self._cache = RequestCache() if self.config.enable_cache else None

        # 请求去重
        self._deduplicator = RequestDeduplicator(
            ttl=self.config.dedup_ttl
        ) if self.config.enable_dedup else None

        # 统计信息
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_requests": 0,
            "retry_requests": 0,
            "circuit_breaker_trips": 0
        }

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if not HTTPX_AVAILABLE:
            raise ImportError("httpx is required. Install with: pip install httpx")

        if self._client is None:
            limits = httpx.Limits(
                max_connections=self.config.max_connections,
                max_keepalive_connections=self.config.max_keepalive_connections,
                keepalive_expiry=self.config.keepalive_expiry
            )

            timeout = httpx.Timeout(
                timeout=self.config.timeout,
                connect=self.config.connect_timeout
            )

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=timeout,
                limits=limits,
                verify=self.config.verify_ssl,
                follow_redirects=self.config.follow_redirects,
                max_redirects=self.config.max_redirects
            )

        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        use_cache: Optional[bool] = None,
        use_dedup: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求

        Args:
            method: HTTP 方法
            url: 请求 URL
            params: 查询参数
            json_data: JSON 数据
            data: 表单数据
            headers: 请求头
            cookies: Cookies
            use_cache: 是否使用缓存
            use_dedup: 是否使用去重

        Returns:
            响应数据

        Raises:
            BusinessError: 请求失败
        """
        # 统计
        self._stats["total_requests"] += 1

        # 检查熔断器
        if not self._circuit_breaker._can_attempt():
            self._stats["circuit_breaker_trips"] += 1
            raise BusinessError(
                message=f"Circuit breaker is open for {self.name}",
                user_message="服务暂时不可用，请稍后重试"
            )

        # 使用缓存
        if use_cache is None:
            use_cache = self.config.enable_cache and method.upper() == "GET"

        if use_cache and self._cache:
            cached = self._cache.get(method, url, params, json_data)
            if cached:
                self._stats["cached_requests"] += 1
                return cached

        # 请求去重
        if use_dedup is None:
            use_dedup = self.config.enable_dedup

        if use_dedup and self._deduplicator:
            should_proceed, wait_event = await self._deduplicator.acquire(
                method, url, params, json_data
            )

            if not should_proceed and wait_event:
                # 等待相同请求完成
                await wait_event.wait()

                # 尝试从缓存获取
                if self._cache:
                    cached = self._cache.get(method, url, params, json_data)
                    if cached:
                        return cached

        # 执行请求（带重试）
        retry_config = self.config.retry_config or RetryConfig()
        last_error = None

        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                response = await self._execute_request(
                    method, url, params, json_data, data, headers, cookies
                )

                # 记录成功
                self._circuit_breaker._record_success()
                self._stats["successful_requests"] += 1

                # 缓存响应
                if use_cache and self._cache:
                    self._cache.set(
                        method, url, response,
                        params, json_data,
                        ttl=self.config.cache_ttl
                    )

                # 释放去重锁
                if use_dedup and self._deduplicator:
                    await self._deduplicator.release(method, url, params, json_data)

                return response

            except Exception as e:
                last_error = e

                # 检查是否应该重试
                should_retry = (
                    attempt < retry_config.max_attempts and
                    self._should_retry(e, response if 'response' in locals() else None, retry_config)
                )

                if should_retry:
                    self._stats["retry_requests"] += 1
                    delay = calculate_delay(attempt, retry_config)
                    await asyncio.sleep(delay)
                    continue

                # 不重试，记录失败
                break

        # 所有尝试都失败
        self._circuit_breaker._record_failure()
        self._stats["failed_requests"] += 1

        # 释放去重锁
        if use_dedup and self._deduplicator:
            await self._deduplicator.release(method, url, params, json_data)

        raise BusinessError(
            message=f"Request failed after {retry_config.max_attempts} attempts: {last_error}",
            user_message="请求失败，请稍后重试"
        )

    async def _execute_request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        执行单次 HTTP 请求

        Args:
            method: HTTP 方法
            url: 请求 URL
            params: 查询参数
            json_data: JSON 数据
            data: 表单数据
            headers: 请求头
            cookies: Cookies

        Returns:
            响应数据

        Raises:
            httpx.HTTPError: HTTP 错误
        """
        client = await self._get_client()

        response = await client.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            content=data,
            headers=headers,
            cookies=cookies
        )

        # 尝试解析 JSON
        try:
            response_data = response.json()
        except Exception:
            response_data = {
                "status_code": response.status_code,
                "text": response.text,
                "headers": dict(response.headers)
            }
        else:
            if isinstance(response_data, dict):
                response_data["status_code"] = response.status_code

        # 检查状态码
        if response.status_code >= 400:
            response.raise_for_status()

        return response_data

    def _should_retry(
        self,
        error: Exception,
        response: Optional[Dict[str, Any]],
        config: RetryConfig
    ) -> bool:
        """
        判断是否应该重试

        Args:
            error: 错误
            response: 响应
            config: 重试配置

        Returns:
            是否应该重试
        """
        # 检查异常类型
        error_type = type(error).__name__
        if error_type in config.retryable_exceptions:
            return True

        # 检查状态码
        if response and "status_code" in response:
            status_code = response["status_code"]
            if status_code in config.retryable_status_codes:
                return True

        return False

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """发送 GET 请求"""
        return await self.request(
            "GET", url, params=params, headers=headers, use_cache=use_cache
        )

    async def post(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """发送 POST 请求"""
        return await self.request(
            "POST", url, json_data=json_data, data=data, headers=headers
        )

    async def put(
        self,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """发送 PUT 请求"""
        return await self.request(
            "PUT", url, json_data=json_data, headers=headers
        )

    async def delete(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """发送 DELETE 请求"""
        return await self.request(
            "DELETE", url, params=params, headers=headers
        )

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "stats": self._stats.copy(),
            "circuit_breaker": self._circuit_breaker.get_stats()
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_requests": 0,
            "retry_requests": 0,
            "circuit_breaker_trips": 0
        }

    def reset_circuit_breaker(self) -> None:
        """重置熔断器"""
        self._circuit_breaker.reset()

    def invalidate_cache(self, url: Optional[str] = None) -> None:
        """使缓存失效"""
        if self._cache:
            self._cache.invalidate(url=url)


# ============================================================================
# 便捷函数
# ============================================================================

# 默认客户端
default_api_client = APIClient()


async def api_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    发送 GET 请求（使用默认客户端）

    Args:
        url: 请求 URL
        params: 查询参数
        headers: 请求头
        use_cache: 是否使用缓存

    Returns:
        响应数据
    """
    return await default_api_client.get(url, params, headers, use_cache)


async def api_post(
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    发送 POST 请求（使用默认客户端）

    Args:
        url: 请求 URL
        json_data: JSON 数据
        headers: 请求头

    Returns:
        响应数据
    """
    return await default_api_client.post(url, json_data, headers=headers)
