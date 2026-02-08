"""
API 客户端单元测试
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# 添加父目录到路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.api_client import (
    CircuitState,
    CircuitBreakerConfig,
    CircuitBreaker,
    RetryConfig,
    calculate_delay,
    RequestCache,
    RequestDeduplicator,
    APIConfig,
    APIClient
)
from common.cache import MemoryCache
from common.exceptions import BusinessError


# ============================================================================
# 熔断器测试
# ============================================================================

class TestCircuitBreaker:
    """测试熔断器"""

    def test_initial_state(self):
        """测试初始状态"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=60.0
        )
        breaker = CircuitBreaker("test", config)

        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker._failure_count == 0
        assert breaker._success_count == 0
        print("✅ 熔断器初始状态正确")

    def test_record_success(self):
        """测试记录成功"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)

        # 记录多次成功
        for _ in range(5):
            breaker._record_success()

        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker._failure_count == 0
        print("✅ 记录成功正常")

    def test_open_on_failures(self):
        """测试失败后打开"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            rolling_window=5
        )
        breaker = CircuitBreaker("test", config)

        # 记录失败
        for _ in range(3):
            breaker._record_failure()

        # 应该打开
        assert breaker.get_state() == CircuitState.OPEN
        print("✅ 失败后熔断器打开")

    def test_half_open_after_timeout(self):
        """测试超时后半开"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout=0.1  # 100ms
        )
        breaker = CircuitBreaker("test", config)

        # 触发打开
        for _ in range(3):
            breaker._record_failure()

        assert breaker.get_state() == CircuitState.OPEN

        # 等待超时
        time.sleep(0.15)

        # 应该转为半开
        assert breaker.get_state() == CircuitState.HALF_OPEN
        print("✅ 超时后转为半开状态")

    def test_close_after_successes(self):
        """测试半开后成功关闭"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=0.1
        )
        breaker = CircuitBreaker("test", config)

        # 触发打开
        for _ in range(3):
            breaker._record_failure()

        # 等待超时
        time.sleep(0.15)

        # 半开状态，记录成功
        assert breaker.get_state() == CircuitState.HALF_OPEN
        breaker._record_success()
        breaker._record_success()

        # 应该关闭
        assert breaker.get_state() == CircuitState.CLOSED
        print("✅ 半开后成功关闭")

    def test_get_stats(self):
        """测试获取统计"""
        config = CircuitBreakerConfig(failure_threshold=5, rolling_window=10)
        breaker = CircuitBreaker("test", config)

        # 记录一些操作
        breaker._record_success()
        breaker._record_success()
        breaker._record_failure()
        breaker._record_success()

        stats = breaker.get_stats()

        assert stats["name"] == "test"
        assert stats["failure_count"] == 1
        assert stats["recent_successes"] == 3
        assert stats["recent_failures"] == 1
        print("✅ 统计信息正确")

    def test_reset(self):
        """测试重置"""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test", config)

        # 触发打开
        for _ in range(3):
            breaker._record_failure()

        assert breaker.get_state() == CircuitState.OPEN

        # 重置
        breaker.reset()

        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker._failure_count == 0
        print("✅ 重置功能正常")


# ============================================================================
# 重试策略测试
# ============================================================================

class TestRetryStrategy:
    """测试重试策略"""

    def test_calculate_delay_exponential(self):
        """测试指数退避"""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=False
        )

        # 第1次：1秒
        delay1 = calculate_delay(1, config)
        assert delay1 == 1.0

        # 第2次：2秒
        delay2 = calculate_delay(2, config)
        assert delay2 == 2.0

        # 第3次：4秒
        delay3 = calculate_delay(3, config)
        assert delay3 == 4.0

        # 第4次：8秒
        delay4 = calculate_delay(4, config)
        assert delay4 == 8.0

        print("✅ 指数退避计算正确")

    def test_calculate_delay_max(self):
        """测试最大延迟限制"""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=False
        )

        # 第10次：1024秒，但应该限制为10秒
        delay = calculate_delay(10, config)
        assert delay == 10.0

        print("✅ 最大延迟限制正确")

    def test_calculate_delay_jitter(self):
        """测试随机抖动"""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=60.0,
            jitter=True
        )

        delays = [calculate_delay(1, config) for _ in range(10)]

        # 应该有一些变化
        assert len(set(delays)) > 1
        # 所有延迟应该在合理范围内
        assert all(0.75 <= d <= 1.5 for d in delays)

        print("✅ 随机抖动正常")


# ============================================================================
# 请求缓存测试
# ============================================================================

class TestRequestCache:
    """测试请求缓存"""

    def test_make_cache_key(self):
        """测试生成缓存键"""
        cache = RequestCache(MemoryCache())

        # GET 请求应该生成键
        key1 = cache._make_cache_key("GET", "https://api.example.com/users", {"page": "1"})
        assert key1 is not None
        assert key1.startswith("api_cache:")

        # 相同请求生成相同键
        key2 = cache._make_cache_key("GET", "https://api.example.com/users", {"page": "1"})
        assert key1 == key2

        # 不同参数生成不同键
        key3 = cache._make_cache_key("GET", "https://api.example.com/users", {"page": "2"})
        assert key1 != key3

        print("✅ 缓存键生成正确")

    def test_make_cache_key_post(self):
        """测试 POST 请求不缓存"""
        cache = RequestCache(MemoryCache())

        key = cache._make_cache_key("POST", "https://api.example.com/users")
        assert key is None

        print("✅ POST 请求不生成缓存键")

    def test_cache_get_set(self):
        """测试缓存读写"""
        cache = RequestCache(MemoryCache())

        response = {"data": "test", "status_code": 200}

        # 设置缓存
        cache.set("GET", "https://api.example.com/test", response, ttl=60)

        # 获取缓存
        cached = cache.get("GET", "https://api.example.com/test")
        assert cached == response

        print("✅ 缓存读写正常")

    def test_cache_invalidate(self):
        """测试缓存失效"""
        cache = RequestCache(MemoryCache())

        response = {"data": "test"}

        # 设置缓存
        cache.set("GET", "https://api.example.com/test", response)

        # 验证存在
        assert cache.get("GET", "https://api.example.com/test") is not None

        # 失效
        cache.invalidate(url="https://api.example.com/test")

        # 验证已清除
        assert cache.get("GET", "https://api.example.com/test") is None

        print("✅ 缓存失效正常")


# ============================================================================
# 请求去重测试
# ============================================================================

class TestRequestDeduplicator:
    """测试请求去重"""

    @pytest.mark.asyncio
    async def test_acquire_first_request(self):
        """测试首次请求获取锁"""
        dedup = RequestDeduplicator(ttl=10)

        should_proceed, wait_event = await dedup.acquire(
            "GET", "https://api.example.com/test"
        )

        assert should_proceed is True
        assert wait_event is None

        # 清理
        await dedup.release("GET", "https://api.example.com/test")

        print("✅ 首次请求获取锁成功")

    @pytest.mark.asyncio
    async def test_acquire_duplicate_request(self):
        """测试重复请求等待"""
        dedup = RequestDeduplicator(ttl=10)

        # 首次请求
        should_proceed1, wait_event1 = await dedup.acquire(
            "GET", "https://api.example.com/test"
        )
        assert should_proceed1 is True
        assert wait_event1 is None

        # 重复请求
        should_proceed2, wait_event2 = await dedup.acquire(
            "GET", "https://api.example.com/test"
        )
        assert should_proceed2 is False
        assert wait_event2 is not None

        # 清理
        await dedup.release("GET", "https://api.example.com/test")

        print("✅ 重复请求等待正常")

    @pytest.mark.asyncio
    async def test_release_and_notify(self):
        """测试释放和通知"""
        dedup = RequestDeduplicator(ttl=10)

        # 首次请求
        await dedup.acquire("GET", "https://api.example.com/test")

        # 重复请求
        should_proceed, wait_event = await dedup.acquire("GET", "https://api.example.com/test")
        assert should_proceed is False
        assert wait_event is not None

        # 释放（后台任务）
        async def release_after_delay():
            await asyncio.sleep(0.1)
            await dedup.release("GET", "https://api.example.com/test")

        asyncio.create_task(release_after_delay())

        # 等待事件
        await wait_event.wait()
        assert wait_event.is_set()

        print("✅ 释放和通知正常")


# ============================================================================
# API 客户端测试
# ============================================================================

class TestAPIClient:
    """测试 API 客户端"""

    def test_initial_config(self):
        """测试初始配置"""
        config = APIConfig(
            base_url="https://api.example.com",
            timeout=30.0,
            max_connections=100
        )

        client = APIClient(config, name="test")

        assert client.config.base_url == "https://api.example.com"
        assert client.config.timeout == 30.0
        assert client.name == "test"
        print("✅ 客户端配置正确")

    def test_stats_initialization(self):
        """测试统计初始化"""
        client = APIClient(name="test")

        stats = client.get_stats()

        assert stats["name"] == "test"
        assert stats["stats"]["total_requests"] == 0
        assert stats["stats"]["successful_requests"] == 0
        assert stats["stats"]["failed_requests"] == 0
        print("✅ 统计初始化正确")

    def test_reset_stats(self):
        """测试重置统计"""
        client = APIClient(name="test")

        # 模拟一些请求
        client._stats["total_requests"] = 10
        client._stats["successful_requests"] = 8
        client._stats["failed_requests"] = 2

        # 重置
        client.reset_stats()

        stats = client.get_stats()
        assert stats["stats"]["total_requests"] == 0
        assert stats["stats"]["successful_requests"] == 0
        print("✅ 统计重置正确")

    def test_reset_circuit_breaker(self):
        """测试重置熔断器"""
        client = APIClient(name="test")

        # 触发熔断器
        for _ in range(5):
            client._circuit_breaker._record_failure()

        assert client._circuit_breaker.get_state() == CircuitState.OPEN

        # 重置
        client.reset_circuit_breaker()

        assert client._circuit_breaker.get_state() == CircuitState.CLOSED
        print("✅ 熔断器重置正确")

    def test_invalidate_cache(self):
        """测试缓存失效"""
        client = APIClient(name="test", config=APIConfig(enable_cache=True))

        # 添加缓存
        if client._cache:
            client._cache.set("GET", "https://test.com", {"data": "test"})

            # 失效
            client.invalidate_cache(url="https://test.com")

            print("✅ 缓存失效调用成功")

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_exception(self):
        """测试熔断器打开时抛出异常"""
        config = APIConfig(
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=2
            )
        )
        client = APIClient(config, name="test")

        # 触发熔断器
        for _ in range(2):
            client._circuit_breaker._record_failure()

        # 应该抛出异常
        with pytest.raises(BusinessError) as exc_info:
            await client.get("https://api.example.com/test")

        assert "Circuit breaker is open" in str(exc_info.value)
        print("✅ 熔断器打开异常正确")


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_cache_flow(self):
        """测试缓存流程"""
        config = APIConfig(enable_cache=True, cache_ttl=60)
        client = APIClient(config, name="test")

        # 模拟响应
        mock_response = {"data": "test", "status_code": 200}

        # 设置缓存
        if client._cache:
            client._cache.set("GET", "https://test.com/api", mock_response)

            # 获取缓存
            cached = client._cache.get("GET", "https://test.com/api")
            assert cached == mock_response

        print("✅ 缓存流程正常")

    @pytest.mark.asyncio
    async def test_dedup_flow(self):
        """测试去重流程"""
        config = APIConfig(enable_dedup=True, dedup_ttl=10)
        client = APIClient(config, name="test")

        if client._deduplicator:
            # 首次请求
            should_proceed1, _ = await client._deduplicator.acquire(
                "GET", "https://test.com/api"
            )
            assert should_proceed1 is True

            # 重复请求
            should_proceed2, wait_event = await client._deduplicator.acquire(
                "GET", "https://test.com/api"
            )
            assert should_proceed2 is False
            assert wait_event is not None

            # 清理
            await client._deduplicator.release("GET", "https://test.com/api")

        print("✅ 去重流程正常")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行 API 调用优化测试...\n")

    print("="*60)
    print("测试熔断器")
    print("="*60)
    TestCircuitBreaker().test_initial_state()
    TestCircuitBreaker().test_record_success()
    TestCircuitBreaker().test_open_on_failures()
    TestCircuitBreaker().test_half_open_after_timeout()
    TestCircuitBreaker().test_close_after_successes()
    TestCircuitBreaker().test_get_stats()
    TestCircuitBreaker().test_reset()

    print("\n" + "="*60)
    print("测试重试策略")
    print("="*60)
    TestRetryStrategy().test_calculate_delay_exponential()
    TestRetryStrategy().test_calculate_delay_max()
    TestRetryStrategy().test_calculate_delay_jitter()

    print("\n" + "="*60)
    print("测试请求缓存")
    print("="*60)
    TestRequestCache().test_make_cache_key()
    TestRequestCache().test_make_cache_key_post()
    TestRequestCache().test_cache_get_set()
    TestRequestCache().test_cache_invalidate()

    print("\n" + "="*60)
    print("测试请求去重")
    print("="*60)
    asyncio.run(TestRequestDeduplicator().test_acquire_first_request())
    asyncio.run(TestRequestDeduplicator().test_acquire_duplicate_request())
    asyncio.run(TestRequestDeduplicator().test_release_and_notify())

    print("\n" + "="*60)
    print("测试 API 客户端")
    print("="*60)
    TestAPIClient().test_initial_config()
    TestAPIClient().test_stats_initialization()
    TestAPIClient().test_reset_stats()
    TestAPIClient().test_reset_circuit_breaker()
    TestAPIClient().test_invalidate_cache()
    asyncio.run(TestAPIClient().test_circuit_breaker_open_exception())

    print("\n" + "="*60)
    print("测试集成")
    print("="*60)
    asyncio.run(TestIntegration().test_cache_flow())
    asyncio.run(TestIntegration().test_dedup_flow())

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
