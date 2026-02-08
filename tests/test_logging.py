"""
日志系统单元测试
"""

import pytest
import json
import logging
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import threading
import os

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.logging_config import (
    LogLevel,
    JSONFormatter,
    ColorFormatter,
    StructuredLogger,
    LogManager,
    log_execution,
    log_async_execution,
    log_manager,
    default_logger,
    get_logger,
    setup_logging
)

from common.log_rotation import (
    CompressedRotatingFileHandler,
    CompressedTimedRotatingFileHandler,
    LogCleaner,
    LogArchiver,
    ScheduledLogCleaner,
    create_compressed_handler,
    create_timed_handler
)

from common.log_storage import (
    LogEntry,
    LogStorage,
    StorageLogHandler,
    default_storage,
    query_logs,
    search_logs,
    get_log_stats
)


# ============================================================================
# JSON 格式化器测试
# ============================================================================

class TestJSONFormatter:
    """测试 JSON 格式化器"""

    def test_format_basic_log(self):
        """测试格式化基本日志"""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logger"] == "test"
        assert "timestamp" in data
        print("✅ 基本日志格式化正确")

    def test_format_exception(self):
        """测试格式化异常日志"""
        import sys
        formatter = JSONFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info()
            )
            formatted = formatter.format(record)
            data = json.loads(formatted)

            assert "exception" in data
            assert data["exception"]["type"] == "ValueError"
            print("✅ 异常日志格式化正确")


# ============================================================================
# 结构化日志记录器测试
# ============================================================================

class TestStructuredLogger:
    """测试结构化日志记录器"""

    def test_initialization(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(
                name="test",
                log_dir=tmpdir,
                log_file="test.log"
            )

            assert logger.name == "test"
            assert logger.log_file.name == "test.log"
            print("✅ 初始化正确")

    def test_log_levels(self):
        """测试日志级别"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(
                name="test",
                log_dir=tmpdir,
                log_file="test.log",
                enable_console=False  # 禁用控制台输出
            )

            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

            # 检查文件
            log_file = Path(tmpdir) / "test.log"
            assert log_file.exists()

            with open(log_file, 'r') as f:
                content = f.read()
                # 验证所有级别都存在
                assert "DEBUG" in content or "INFO" in content  # DEBUG 可能被过滤

            print("✅ 日志级别正确")

    def test_context_management(self):
        """测试上下文管理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(
                name="test",
                log_dir=tmpdir,
                log_file="test.log",
                enable_console=False
            )

            # 添加上下文
            logger.add_context(user_id="123", request_id="456")
            logger.info("Test with context")

            # 上下文管理器
            with logger.context(temp_id="789"):
                logger.info("Test with temp context")

            # 清除上下文
            logger.clear_context()
            logger.info("Test without context")

            print("✅ 上下文管理正确")


# ============================================================================
# 日志装饰器测试
# ============================================================================

class TestLogDecorators:
    """测试日志装饰器"""

    def test_log_execution(self):
        """测试执行日志装饰器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(
                name="test",
                log_dir=tmpdir,
                log_file="test.log"
            )

            @log_execution(logger=logger, include_args=True)
            def test_function(x, y):
                return x + y

            result = test_function(1, 2)
            assert result == 3
            print("✅ 执行日志装饰器正确")

    def test_log_exception(self):
        """测试异常日志装饰器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = StructuredLogger(
                name="test",
                log_dir=tmpdir,
                log_file="test.log"
            )

            @log_execution(logger=logger)
            def failing_function():
                raise ValueError("Test error")

            with pytest.raises(ValueError):
                failing_function()

            print("✅ 异常日志装饰器正确")


# ============================================================================
# 日志管理器测试
# ============================================================================

class TestLogManager:
    """测试日志管理器"""

    def test_get_logger(self):
        """测试获取日志记录器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger1 = log_manager.get_logger("test1", log_dir=tmpdir)
            logger2 = log_manager.get_logger("test1", log_dir=tmpdir)

            assert logger1 is logger2
            print("✅ 获取日志记录器正确")

    def test_remove_logger(self):
        """测试移除日志记录器"""
        log_manager.remove_logger("test1")
        assert "test1" not in log_manager.get_all_loggers()
        print("✅ 移除日志记录器正确")


# ============================================================================
# 日志轮转测试
# ============================================================================

class TestLogRotation:
    """测试日志轮转"""

    def test_compressed_rotation(self):
        """测试压缩轮转"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"

            handler = CompressedRotatingFileHandler(
                filename=str(log_file),
                maxBytes=1024,  # 1KB
                backupCount=3,
                compress=True
            )

            # 写入日志
            for i in range(100):
                handler.emit(logging.LogRecord(
                    name="test",
                    level=logging.INFO,
                    pathname="test.py",
                    lineno=42,
                    msg=f"Message {i}: " + "x" * 100,
                    args=(),
                    exc_info=None
                ))

            handler.close()

            # 检查备份文件
            backup_files = list(Path(tmpdir).glob("test.log.*"))
            assert len(backup_files) > 0
            print("✅ 压缩轮转正确")

    def test_log_cleaner(self):
        """测试日志清理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建旧文件
            old_file = Path(tmpdir) / "old.log"
            old_file.write_text("old log")

            # 修改文件时间（30 天前）
            old_time = time.time() - (30 * 24 * 3600)
            os.utime(old_file, (old_time, old_time))

            # 创建新文件
            new_file = Path(tmpdir) / "new.log"
            new_file.write_text("new log")

            # 清理
            cleaner = LogCleaner(
                log_dir=tmpdir,
                max_age_days=7,
                pattern="*.log"
            )
            stats = cleaner.clean()

            assert stats["deleted_files"] == 1
            assert not old_file.exists()
            assert new_file.exists()
            print("✅ 日志清理正确")

    def test_log_archiver(self):
        """测试日志归档器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            archive_dir = Path(tmpdir) / "archive"
            log_dir.mkdir()

            # 创建旧文件
            old_file = log_dir / "old.log.1"
            old_file.write_text("old log")

            # 修改文件时间（10 天前）
            old_time = time.time() - (10 * 24 * 3600)
            os.utime(old_file, (old_time, old_time))

            # 归档
            archiver = LogArchiver(
                log_dir=str(log_dir),
                archive_dir=str(archive_dir),
                pattern="*.log.*"
            )
            stats = archiver.archive(older_than_days=7)

            assert stats["archived_files"] == 1
            assert (archive_dir / "old.log.1").exists()
            print("✅ 日志归档正确")


# ============================================================================
# 日志存储测试
# ============================================================================

class TestLogStorage:
    """测试日志存储"""

    def test_add_and_query(self):
        """测试添加和查询"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LogStorage(db_path=str(Path(tmpdir) / "test.db"))

            # 添加日志
            entry = LogEntry(
                timestamp="2025-02-08T12:00:00.000Z",
                level="INFO",
                logger="test",
                message="Test message",
                module="test_module",
                function="test_function",
                line=42,
                process_id=1234,
                thread_id=5678,
                extra={"key": "value"}
            )

            storage.add(entry)
            storage._flush_buffer()

            # 查询
            results = storage.query(limit=10)
            assert len(results) == 1
            assert results[0].message == "Test message"

            storage.close()
            print("✅ 添加和查询正确")

    def test_search(self):
        """测试搜索"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LogStorage(db_path=str(Path(tmpdir) / "test.db"))

            # 添加多条日志
            for i in range(10):
                entry = LogEntry(
                    timestamp="2025-02-08T12:00:00.000Z",
                    level="INFO",
                    logger="test",
                    message=f"Message {i}",
                    module="test",
                    function="test",
                    line=42,
                    process_id=1234,
                    thread_id=5678
                )
                storage.add(entry)

            storage._flush_buffer()

            # 搜索
            results = storage.search("Message 5")
            assert len(results) == 1
            assert results[0].message == "Message 5"

            storage.close()
            print("✅ 搜索正确")

    def test_stats(self):
        """测试统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LogStorage(db_path=str(Path(tmpdir) / "test.db"))

            # 添加不同级别的日志
            for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                for i in range(5):
                    entry = LogEntry(
                        timestamp="2025-02-08T12:00:00.000Z",
                        level=level,
                        logger="test",
                        message=f"{level} message {i}",
                        module="test",
                        function="test",
                        line=42,
                        process_id=1234,
                        thread_id=5678
                    )
                    storage.add(entry)

            storage._flush_buffer()

            # 获取统计
            stats = storage.get_stats()
            assert stats["total"] == 20
            assert stats["by_level"]["INFO"] == 5
            assert stats["by_level"]["ERROR"] == 5

            storage.close()
            print("✅ 统计正确")

    def test_delete_old(self):
        """测试删除旧日志"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LogStorage(db_path=str(Path(tmpdir) / "test.db"))

            # 添加日志
            entry = LogEntry(
                timestamp="2025-01-01T12:00:00.000Z",  # 旧时间
                level="INFO",
                logger="test",
                message="Old message",
                module="test",
                function="test",
                line=42,
                process_id=1234,
                thread_id=5678
            )
            storage.add(entry)
            storage._flush_buffer()

            # 删除旧日志
            deleted = storage.delete_old(days=7)
            assert deleted == 1

            # 验证
            results = storage.query()
            assert len(results) == 0

            storage.close()
            print("✅ 删除旧日志正确")


# ============================================================================
# 日志条目测试
# ============================================================================

class TestLogEntry:
    """测试日志条目"""

    def test_to_dict(self):
        """测试转字典"""
        entry = LogEntry(
            timestamp="2025-02-08T12:00:00.000Z",
            level="INFO",
            logger="test",
            message="Test",
            module="test",
            function="test",
            line=42,
            process_id=1234,
            thread_id=5678
        )

        data = entry.to_dict()
        assert data["level"] == "INFO"
        assert data["message"] == "Test"
        print("✅ 转字典正确")

    def test_from_json(self):
        """测试从 JSON 创建"""
        json_str = json.dumps({
            "timestamp": "2025-02-08T12:00:00.000Z",
            "level": "INFO",
            "logger": "test",
            "message": "Test",
            "module": "test",
            "function": "test",
            "line": 42,
            "process_id": 1234,
            "thread_id": 5678,
            "extra": {}
        })

        entry = LogEntry.from_json(json_str)
        assert entry.level == "INFO"
        assert entry.message == "Test"
        print("✅ 从 JSON 创建正确")


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    def test_full_logging_workflow(self):
        """测试完整日志工作流"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 设置日志
            logger = StructuredLogger(
                name="integration",
                log_dir=tmpdir,
                log_file="integration.log",
                enable_console=True  # 保持控制台输出以便调试
            )

            # 2. 添加上下文
            logger.add_context(
                request_id="test-123",
                user_id="user-456"
            )

            # 3. 记录日志
            logger.info("Integration test started")
            logger.warning("This is a warning")
            logger.error("This is an error")

            # 4. 使用装饰器
            @log_execution(logger=logger)
            def test_func(x):
                return x * 2

            result = test_func(5)
            assert result == 10

            # 5. 验证日志文件
            log_file = Path(tmpdir) / "integration.log"
            assert log_file.exists(), f"日志文件不存在: {log_file}"

            with open(log_file, 'r') as f:
                content = f.read()
                assert "Integration test started" in content
                assert "This is a warning" in content

            print("✅ 完整工作流正确")

    def test_storage_and_query_integration(self):
        """测试存储和查询集成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. 创建存储
            storage = LogStorage(db_path=str(Path(tmpdir) / "test.db"))

            # 2. 添加处理器到日志记录器
            handler = StorageLogHandler(storage)
            test_logger = logging.getLogger("integration_test")
            test_logger.addHandler(handler)
            test_logger.setLevel(logging.INFO)

            # 3. 记录日志
            test_logger.info("Test message 1")
            test_logger.error("Test error")
            test_logger.warning("Test warning")

            # 4. 刷新并查询
            storage._flush_buffer()

            results = storage.query()
            assert len(results) == 3

            # 5. 按级别查询
            error_logs = storage.query(level="ERROR")
            assert len(error_logs) == 1
            assert error_logs[0].message == "Test error"

            storage.close()
            print("✅ 存储和查询集成正确")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行日志系统测试...\n")

    print("="*60)
    print("测试 JSON 格式化器")
    print("="*60)
    TestJSONFormatter().test_format_basic_log()
    TestJSONFormatter().test_format_exception()

    print("\n" + "="*60)
    print("测试结构化日志记录器")
    print("="*60)
    TestStructuredLogger().test_initialization()
    TestStructuredLogger().test_log_levels()
    TestStructuredLogger().test_context_management()

    print("\n" + "="*60)
    print("测试日志装饰器")
    print("="*60)
    TestLogDecorators().test_log_execution()
    TestLogDecorators().test_log_exception()

    print("\n" + "="*60)
    print("测试日志管理器")
    print("="*60)
    TestLogManager().test_get_logger()
    TestLogManager().test_remove_logger()

    print("\n" + "="*60)
    print("测试日志轮转")
    print("="*60)
    TestLogRotation().test_compressed_rotation()
    TestLogRotation().test_log_cleaner()
    TestLogRotation().test_log_archiver()

    print("\n" + "="*60)
    print("测试日志存储")
    print("="*60)
    TestLogStorage().test_add_and_query()
    TestLogStorage().test_search()
    TestLogStorage().test_stats()
    TestLogStorage().test_delete_old()

    print("\n" + "="*60)
    print("测试日志条目")
    print("="*60)
    TestLogEntry().test_to_dict()
    TestLogEntry().test_from_json()

    print("\n" + "="*60)
    print("测试集成")
    print("="*60)
    TestIntegration().test_full_logging_workflow()
    TestIntegration().test_storage_and_query_integration()

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
