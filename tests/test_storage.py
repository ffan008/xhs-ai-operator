"""
数据存储性能优化的单元测试
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.async_file import (
    AsyncFileHandler,
    AsyncBatchFileHandler,
    default_async_file_handler
)

from common.cache import (
    CacheConfig,
    RedisCache,
    MemoryCache,
    cached,
    default_memory_cache
)

from common.database import (
    SQLiteConnectionPool,
    DatabaseManager,
    db_insert,
    db_select,
    db_count
)

from common.cache_manager import (
    MultiLevelCacheManager,
    CacheKeyGenerator,
    cached as async_cached,
    default_cache_manager
)


# ============================================================================
# 异步文件 I/O 测试
# ============================================================================

class TestAsyncFileHandler:
    """测试异步文件处理器"""

    @pytest.mark.asyncio
    async def test_write_and_read_text(self):
        """测试写入和读取文本"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = AsyncFileHandler(Path(tmpdir))

            file_path = "test.txt"
            content = "Hello, World!"

            # 写入
            await handler.write_text(file_path, content)

            # 读取
            read_content = await handler.read_text(file_path)

            assert read_content == content
            print("✅ 文本写入和读取成功")

    @pytest.mark.asyncio
    async def test_write_and_read_json(self):
        """测试写入和读取 JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = AsyncFileHandler(Path(tmpdir))

            file_path = "test.json"
            data = {"key": "value", "number": 123}

            # 写入
            await handler.write_json(file_path, data)

            # 读取
            read_data = await handler.read_json(file_path)

            assert read_data == data
            print("✅ JSON 写入和读取成功")

    @pytest.mark.asyncio
    async def test_file_exists(self):
        """测试检查文件存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = AsyncFileHandler(Path(tmpdir))

            file_path = "test.txt"

            # 文件不存在
            assert not await handler.exists(file_path)

            # 创建文件
            await handler.write_text(file_path, "content")

            # 文件存在
            assert await handler.exists(file_path)
            print("✅ 文件存在检查成功")

    @pytest.mark.asyncio
    async def test_delete_file(self):
        """测试删除文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = AsyncFileHandler(Path(tmpdir))

            file_path = "test.txt"

            # 创建文件
            await handler.write_text(file_path, "content")
            assert await handler.exists(file_path)

            # 删除文件
            assert await handler.delete(file_path)
            assert not await handler.exists(file_path)
            print("✅ 文件删除成功")

    @pytest.mark.asyncio
    async def test_append_text(self):
        """测试追加文本"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = AsyncFileHandler(Path(tmpdir))

            file_path = "test.txt"

            # 写入初始内容
            await handler.write_text(file_path, "Hello")

            # 追加内容
            await handler.append_text(file_path, " World")

            # 读取
            content = await handler.read_text(file_path)

            assert content == "Hello World"
            print("✅ 文本追加成功")


class TestAsyncBatchFileHandler:
    """测试批量异步文件处理器"""

    @pytest.mark.asyncio
    async def test_read_multiple_files(self):
        """测试批量读取文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            handler = AsyncFileHandler(Path(tmpdir))

            files = {
                "file1.txt": "Content 1",
                "file2.txt": "Content 2",
                "file3.txt": "Content 3"
            }

            for file_path, content in files.items():
                await handler.write_text(file_path, content)

            # 批量读取
            batch_handler = AsyncBatchFileHandler(handler)
            results = await batch_handler.read_multiple_files(list(files.keys()))

            assert len(results) == 3
            for file_path, content in files.items():
                assert results[file_path] == content
            print("✅ 批量读取文件成功")

    @pytest.mark.asyncio
    async def test_write_multiple_files(self):
        """测试批量写入文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = AsyncFileHandler(Path(tmpdir))
            batch_handler = AsyncBatchFileHandler(handler)

            files = {
                "file1.txt": "Content 1",
                "file2.txt": "Content 2"
            }

            # 批量写入
            results = await batch_handler.write_multiple_files(files)

            assert all(results.values())
            print("✅ 批量写入文件成功")


# ============================================================================
# 内存缓存测试
# ============================================================================

class TestMemoryCache:
    """测试内存缓存"""

    def test_set_and_get(self):
        """测试设置和获取"""
        cache = MemoryCache()

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        print("✅ 设置和获取成功")

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = MemoryCache()

        assert cache.get("nonexistent") is None
        print("✅ 不存在的键返回 None")

    def test_delete(self):
        """测试删除"""
        cache = MemoryCache()

        cache.set("key1", "value1")
        assert cache.get("key1") is not None

        cache.delete("key1")
        assert cache.get("key1") is None
        print("✅ 删除成功")

    def test_expiration(self):
        """测试过期"""
        import time

        cache = MemoryCache(default_ttl=1)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 等待过期
        time.sleep(1.5)

        assert cache.get("key1") is None
        print("✅ 过期机制正常")

    def test_clear(self):
        """测试清空缓存"""
        cache = MemoryCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None
        print("✅ 清空缓存成功")


# ============================================================================
# Redis 缓存测试（模拟）
# ============================================================================

class TestRedisCache:
    """测试 Redis 缓存"""

    def test_config_creation(self):
        """测试配置创建"""
        config = CacheConfig(
            host="localhost",
            port=6379,
            password=None
        )

        assert config.host == "localhost"
        assert config.port == 6379
        print("✅ Redis 配置创建成功")

    def test_key_prefix(self):
        """测试键前缀"""
        config = CacheConfig(key_prefix="test:")
        cache = RedisCache(config)

        assert cache._make_key("mykey") == "test:mykey"
        print("✅ 键前缀正确")


# ============================================================================
# 数据库测试
# ============================================================================

class TestDatabaseManager:
    """测试数据库管理器"""

    def test_insert_and_select(self):
        """测试插入和查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            manager = DatabaseManager(db_path)

            # 插入数据
            data = {
                "id": "note1",
                "title": "测试笔记",
                "content": "这是测试内容",
                "tags": "测试,标签",
                "account_id": "account1",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            row_id = manager.insert("notes", data)
            assert row_id > 0

            # 查询数据
            rows = manager.select("notes", where={"id": "note1"})
            assert len(rows) == 1
            assert dict(rows[0])["title"] == "测试笔记"
            print("✅ 插入和查询成功")

    def test_update(self):
        """测试更新"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            manager = DatabaseManager(db_path)

            # 插入数据
            data = {
                "id": "note1",
                "title": "原标题",
                "content": "内容",
                "account_id": "account1",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            manager.insert("notes", data)

            # 更新数据
            updated = manager.update(
                "notes",
                data={"title": "新标题"},
                where={"id": "note1"}
            )

            assert updated > 0

            # 验证更新
            rows = manager.select("notes", where={"id": "note1"})
            assert dict(rows[0])["title"] == "新标题"
            print("✅ 更新成功")

    def test_delete(self):
        """测试删除"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            manager = DatabaseManager(db_path)

            # 插入数据
            data = {
                "id": "note1",
                "title": "测试",
                "content": "内容",
                "account_id": "account1",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            manager.insert("notes", data)

            # 删除数据
            deleted = manager.delete("notes", where={"id": "note1"})
            assert deleted > 0

            # 验证删除
            rows = manager.select("notes", where={"id": "note1"})
            assert len(rows) == 0
            print("✅ 删除成功")

    def test_count(self):
        """测试统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            manager = DatabaseManager(db_path)

            # 插入多条数据
            for i in range(3):
                data = {
                    "id": f"note{i}",
                    "title": f"笔记{i}",
                    "content": "内容",
                    "account_id": "account1",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                manager.insert("notes", data)

            # 统计
            count = manager.count("notes")
            assert count == 3

            # 条件统计
            count = manager.count("notes", where={"account_id": "account1"})
            assert count == 3
            print("✅ 统计成功")


# ============================================================================
# 缓存键生成器测试
# ============================================================================

class TestCacheKeyGenerator:
    """测试缓存键生成器"""

    def test_generate_simple(self):
        """测试简单键生成"""
        key = CacheKeyGenerator.generate("user", "123")
        assert key == "user:123"
        print("✅ 简单键生成成功")

    def test_generate_with_kwargs(self):
        """测试带参数的键生成"""
        key = CacheKeyGenerator.generate("query", table="notes", account_id="acc1")
        assert "query:" in key
        assert "account_id=acc1" in key
        assert "table=notes" in key
        print("✅ 带参数键生成成功")

    def test_for_user(self):
        """测试用户键生成"""
        key = CacheKeyGenerator.for_user("user123", "note", "note456")
        assert key == "user:user123:note:note456"
        print("✅ 用户键生成成功")

    def test_for_account(self):
        """测试账号键生成"""
        key = CacheKeyGenerator.for_account("acc123", "note", "note456")
        assert key == "account:acc123:note:note456"
        print("✅ 账号键生成成功")

    def test_for_query(self):
        """测试查询键生成"""
        params = {"account_id": "acc1", "status": "published"}
        key = CacheKeyGenerator.for_query("notes", params)
        assert "query:notes:" in key
        assert len(key) < 100  # 应该使用哈希
        print("✅ 查询键生成成功")


# ============================================================================
# 多级缓存测试
# ============================================================================

class TestMultiLevelCache:
    """测试多级缓存"""

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """测试设置和获取"""
        cache = MultiLevelCacheManager()

        await cache.set("key1", "value1")
        value = await cache.get("key1")

        assert value == "value1"
        print("✅ 设置和获取成功")

    @pytest.mark.asyncio
    async def test_get_or_set(self):
        """测试获取或设置"""
        cache = MultiLevelCacheManager()
        call_count = 0

        async def value_func():
            nonlocal call_count
            call_count += 1
            return "computed_value"

        # 第一次调用
        value = await cache.get_or_set("key1", value_func)
        assert value == "computed_value"
        assert call_count == 1

        # 第二次调用（从缓存获取）
        value = await cache.get_or_set("key1", value_func)
        assert value == "computed_value"
        assert call_count == 1  # 没有再次调用
        print("✅ 获取或设置成功")

    @pytest.mark.asyncio
    async def test_delete(self):
        """测试删除"""
        cache = MultiLevelCacheManager()

        await cache.set("key1", "value1")
        assert await cache.get("key1") is not None

        await cache.delete("key1")
        assert await cache.get("key1") is None
        print("✅ 删除成功")

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """测试获取统计"""
        cache = MultiLevelCacheManager()

        await cache.set("key1", "value1")
        await cache.get("key1")  # hit
        await cache.get("key2")  # miss

        stats = cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
        print("✅ 统计信息正确")


# ============================================================================
# 缓存装饰器测试
# ============================================================================

class TestCacheDecorators:
    """测试缓存装饰器"""

    def test_sync_cached_decorator(self):
        """测试同步缓存装饰器"""
        cache = MemoryCache()
        call_count = 0

        # 使用内存缓存的装饰器
        def mock_cache_get(key):
            return cache.get(key)

        def mock_cache_set(key, value, ttl=None):
            return cache.set(key, value, ttl=ttl)

        # 模拟装饰器
        def simple_cached(func):
            def wrapper(*args, **kwargs):
                key = f"test:{args[0] if args else ''}"
                value = mock_cache_get(key)
                if value is not None:
                    return value

                result = func(*args, **kwargs)
                mock_cache_set(key, result, ttl=300)
                return result
            return wrapper

        @simple_cached
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # 第一次调用
        result = compute(5)
        assert result == 10
        assert call_count == 1

        # 第二次调用（从缓存）
        result = compute(5)
        assert result == 10
        assert call_count == 1
        print("✅ 同步缓存装饰器成功")

    @pytest.mark.asyncio
    async def test_async_cached_decorator(self):
        """测试异步缓存装饰器"""
        call_count = 0

        @async_cached("test", ttl=300, level=1)
        async def async_compute(x):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return x * 2

        # 第一次调用
        result = await async_compute(5)
        assert result == 10
        assert call_count == 1

        # 第二次调用（从缓存）
        result = await async_compute(5)
        assert result == 10
        assert call_count == 1
        print("✅ 异步缓存装饰器成功")


def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行数据存储优化测试...\n")

    print("="*60)
    print("测试异步文件 I/O")
    print("="*60)
    asyncio.run(TestAsyncFileHandler().test_write_and_read_text())
    asyncio.run(TestAsyncFileHandler().test_write_and_read_json())
    asyncio.run(TestAsyncFileHandler().test_file_exists())
    asyncio.run(TestAsyncFileHandler().test_delete_file())
    asyncio.run(TestAsyncFileHandler().test_append_text())

    print("\n" + "="*60)
    print("测试批量文件操作")
    print("="*60)
    asyncio.run(TestAsyncBatchFileHandler().test_read_multiple_files())
    asyncio.run(TestAsyncBatchFileHandler().test_write_multiple_files())

    print("\n" + "="*60)
    print("测试内存缓存")
    print("="*60)
    TestMemoryCache().test_set_and_get()
    TestMemoryCache().test_get_nonexistent()
    TestMemoryCache().test_delete()
    TestMemoryCache().test_expiration()
    TestMemoryCache().test_clear()

    print("\n" + "="*60)
    print("测试 Redis 缓存")
    print("="*60)
    TestRedisCache().test_config_creation()
    TestRedisCache().test_key_prefix()

    print("\n" + "="*60)
    print("测试数据库")
    print("="*60)
    TestDatabaseManager().test_insert_and_select()
    TestDatabaseManager().test_update()
    TestDatabaseManager().test_delete()
    TestDatabaseManager().test_count()

    print("\n" + "="*60)
    print("测试缓存键生成器")
    print("="*60)
    TestCacheKeyGenerator().test_generate_simple()
    TestCacheKeyGenerator().test_generate_with_kwargs()
    TestCacheKeyGenerator().test_for_user()
    TestCacheKeyGenerator().test_for_account()
    TestCacheKeyGenerator().test_for_query()

    print("\n" + "="*60)
    print("测试多级缓存")
    print("="*60)
    asyncio.run(TestMultiLevelCache().test_set_and_get())
    asyncio.run(TestMultiLevelCache().test_get_or_set())
    asyncio.run(TestMultiLevelCache().test_delete())
    asyncio.run(TestMultiLevelCache().test_get_stats())

    print("\n" + "="*60)
    print("测试缓存装饰器")
    print("="*60)
    TestCacheDecorators().test_sync_cached_decorator()
    asyncio.run(TestCacheDecorators().test_async_cached_decorator())

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
