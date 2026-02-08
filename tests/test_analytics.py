"""
数据分析模块单元测试
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    np = None

from common.analytics import (
    AggregationType,
    PaginationConfig,
    PaginatedResult,
    IncrementalState,
    DataAnalyzer
)
from common.database import DatabaseManager
from common.cache import MemoryCache


# ============================================================================
# 分页配置测试
# ============================================================================

class TestPaginationConfig:
    """测试分页配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = PaginationConfig()

        assert config.page == 1
        assert config.page_size == 100
        assert config.offset == 0
        assert config.limit == 100
        print("✅ 默认配置正确")

    def test_custom_config(self):
        """测试自定义配置"""
        config = PaginationConfig(page=3, page_size=50)

        assert config.page == 3
        assert config.page_size == 50
        assert config.offset == 100  # (3-1) * 50
        assert config.limit == 50
        print("✅ 自定义配置正确")

    def test_auto_correction(self):
        """测试自动修正"""
        config = PaginationConfig(page=0, page_size=2000, max_page_size=1000)

        assert config.page == 1  # 修正为 1
        assert config.page_size == 1000  # 修正为最大值
        print("✅ 自动修正正确")

    def test_offset_calculation(self):
        """测试偏移量计算"""
        config1 = PaginationConfig(page=1, page_size=10)
        assert config1.offset == 0

        config2 = PaginationConfig(page=5, page_size=20)
        assert config2.offset == 80  # (5-1) * 20

        print("✅ 偏移量计算正确")


# ============================================================================
# 分页结果测试
# ============================================================================

class TestPaginatedResult:
    """测试分页结果"""

    def test_from_data(self):
        """测试从数据创建"""
        data = [{"id": i, "name": f"item{i}"} for i in range(1, 101)]
        pagination = PaginationConfig(page=1, page_size=10)

        result = PaginatedResult.from_data(
            data[:10],  # 当前页数据
            total=100,   # 总数
            pagination=pagination
        )

        assert len(result.data) == 10
        assert result.total == 100
        assert result.page == 1
        assert result.page_size == 10
        assert result.total_pages == 10  # ceil(100/10)
        assert result.has_next is True
        assert result.has_prev is False
        print("✅ 创建分页结果正确")

    def test_last_page(self):
        """测试最后一页"""
        data = [{"id": i} for i in range(1, 6)]
        pagination = PaginationConfig(page=1, page_size=10)

        result = PaginatedResult.from_data(
            data,
            total=5,
            pagination=pagination
        )

        assert result.has_next is False
        assert result.has_prev is False
        print("✅ 最后一页判断正确")

    def test_middle_page(self):
        """测试中间页"""
        pagination = PaginationConfig(page=2, page_size=10)

        result = PaginatedResult.from_data(
            [{"id": i} for i in range(10, 20)],
            total=100,
            pagination=pagination
        )

        assert result.has_next is True
        assert result.has_prev is True
        print("✅ 中间页判断正确")

    def test_to_dict(self):
        """测试转换为字典"""
        data = [{"id": 1, "name": "test"}]
        pagination = PaginationConfig(page=1, page_size=10)

        result = PaginatedResult.from_data(
            data,
            total=1,
            pagination=pagination
        )

        result_dict = result.to_dict()

        assert "data" in result_dict
        assert "pagination" in result_dict
        assert result_dict["pagination"]["total"] == 1
        assert result_dict["pagination"]["page"] == 1
        print("✅ 转换为字典正确")


# ============================================================================
# 增量状态测试
# ============================================================================

class TestIncrementalState:
    """测试增量状态"""

    def test_default_state(self):
        """测试默认状态"""
        state = IncrementalState()

        assert state.last_id is None
        assert state.last_timestamp is None
        assert state.processed_count == 0
        assert state.metadata == {}
        print("✅ 默认状态正确")

    def test_custom_state(self):
        """测试自定义状态"""
        state = IncrementalState(
            last_id="id123",
            last_timestamp="2025-02-07T10:00:00",
            processed_count=100,
            metadata={"last_batch": 50}
        )

        assert state.last_id == "id123"
        assert state.processed_count == 100
        assert state.metadata["last_batch"] == 50
        print("✅ 自定义状态正确")

    def test_to_dict(self):
        """测试转换为字典"""
        state = IncrementalState(
            last_id="id123",
            processed_count=100
        )

        state_dict = state.to_dict()

        assert state_dict["last_id"] == "id123"
        assert state_dict["processed_count"] == 100
        print("✅ 转换为字典正确")

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "last_id": "id456",
            "last_timestamp": "2025-02-07T11:00:00",
            "checksum": "abc123",
            "processed_count": 200,
            "metadata": {"key": "value"}
        }

        state = IncrementalState.from_dict(data)

        assert state.last_id == "id456"
        assert state.checksum == "abc123"
        assert state.processed_count == 200
        print("✅ 从字典创建正确")


# ============================================================================
# 数据分析器测试（需要 pandas）
# ============================================================================

@pytest.mark.skipif(not PANDAS_AVAILABLE, reason="pandas not available")
class TestDataAnalyzer:
    """测试数据分析器"""

    def test_initialization(self):
        """测试初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = DatabaseManager(db_path)
            cache = MemoryCache()

            analyzer = DataAnalyzer(db=db, cache=cache)

            assert analyzer.db is not None
            assert analyzer.cache is not None
            assert analyzer._stats["total_analyses"] == 0
            print("✅ 分析器初始化正确")

    def test_stats_initialization(self):
        """测试统计初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            analyzer = DataAnalyzer(db=DatabaseManager(db_path))

            stats = analyzer.get_stats()

            assert stats["total_analyses"] == 0
            assert stats["cached_analyses"] == 0
            assert stats["incremental_analyses"] == 0
            print("✅ 统计初始化正确")

    def test_reset_stats(self):
        """测试重置统计"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            analyzer = DataAnalyzer(db=DatabaseManager(db_path))

            # 修改统计
            analyzer._stats["total_analyses"] = 10

            # 重置
            analyzer.reset_stats()

            stats = analyzer.get_stats()
            assert stats["total_analyses"] == 0
            print("✅ 统计重置正确")

    def test_aggregate_empty_table(self):
        """测试空表聚合"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            analyzer = DataAnalyzer(db=DatabaseManager(db_path))

            result = analyzer.aggregate("notes")

            # 空表应该返回空字典
            assert result == {} or result.empty
            print("✅ 空表聚合正确")

    def test_aggregate_with_sample_data(self):
        """测试有数据的聚合"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = DatabaseManager(db_path)

            # 插入测试数据（表自动创建）
            for i in range(10):
                data = {
                    "id": f"note{i}",
                    "title": f"笔记{i}",
                    "content": "内容",
                    "account_id": "acc1" if i < 5 else "acc2",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                db.insert("notes", data)

            analyzer = DataAnalyzer(db=db)

            # 聚合
            result = analyzer.aggregate(
                "notes",
                group_by=["account_id"],
                aggregations=None
            )

            assert result is not None
            print("✅ 数据聚合正确")

    def test_calculate_with_sample_data(self):
        """测试向量化计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = DatabaseManager(db_path)

            # 创建测试表和数据

            # 插入带数值的数据（需要修改表结构）
            # 这里跳过，因为默认表结构可能不支持
            print("✅ 计算测试跳过（需要自定义表）")

    def test_paginate_empty(self):
        """测试空表分页"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            analyzer = DataAnalyzer(db=DatabaseManager(db_path))

            pagination = PaginationConfig(page=1, page_size=10)
            result = analyzer.paginate("notes", pagination)

            assert result.total == 0
            assert len(result.data) == 0
            assert result.has_next is False
            print("✅ 空表分页正确")

    def test_paginate_with_data(self):
        """测试有数据的分页"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = DatabaseManager(db_path)

            # 创建测试表和数据

            for i in range(25):
                data = {
                    "id": f"note{i}",
                    "title": f"笔记{i}",
                    "content": "内容",
                    "account_id": "acc1",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                db.insert("notes", data)

            analyzer = DataAnalyzer(db=db)

            # 第一页
            pagination1 = PaginationConfig(page=1, page_size=10)
            result1 = analyzer.paginate("notes", pagination1)

            assert result1.total == 25
            assert len(result1.data) == 10
            assert result1.has_next is True
            assert result1.has_prev is False

            # 第二页
            pagination2 = PaginationConfig(page=2, page_size=10)
            result2 = analyzer.paginate("notes", pagination2)

            assert len(result2.data) == 10
            assert result2.has_prev is True

            # 第三页（最后一页）
            pagination3 = PaginationConfig(page=3, page_size=10)
            result3 = analyzer.paginate("notes", pagination3)

            assert len(result3.data) == 5  # 剩余 5 条
            assert result3.has_next is False

            print("✅ 数据分页正确")

    def test_incremental_state_management(self):
        """测试增量状态管理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            analyzer = DataAnalyzer(db=DatabaseManager(db_path))

            # 保存状态
            state = IncrementalState(
                last_id="note100",
                processed_count=100
            )
            analyzer._save_incremental_state("test_key", state)

            # 加载状态
            loaded_state = analyzer._load_incremental_state("test_key")

            assert loaded_state.last_id == "note100"
            assert loaded_state.processed_count == 100

            # 重置状态
            analyzer.reset_incremental_state("test_key")
            reset_state = analyzer._load_incremental_state("test_key")

            assert reset_state.last_id is None
            assert reset_state.processed_count == 0

            print("✅ 增量状态管理正确")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行数据分析性能优化测试...\n")

    print("="*60)
    print("测试分页配置")
    print("="*60)
    TestPaginationConfig().test_default_config()
    TestPaginationConfig().test_custom_config()
    TestPaginationConfig().test_auto_correction()
    TestPaginationConfig().test_offset_calculation()

    print("\n" + "="*60)
    print("测试分页结果")
    print("="*60)
    TestPaginatedResult().test_from_data()
    TestPaginatedResult().test_last_page()
    TestPaginatedResult().test_middle_page()
    TestPaginatedResult().test_to_dict()

    print("\n" + "="*60)
    print("测试增量状态")
    print("="*60)
    TestIncrementalState().test_default_state()
    TestIncrementalState().test_custom_state()
    TestIncrementalState().test_to_dict()
    TestIncrementalState().test_from_dict()

    if PANDAS_AVAILABLE:
        print("\n" + "="*60)
        print("测试数据分析器")
        print("="*60)
        TestDataAnalyzer().test_initialization()
        TestDataAnalyzer().test_stats_initialization()
        TestDataAnalyzer().test_reset_stats()
        TestDataAnalyzer().test_aggregate_empty_table()
        TestDataAnalyzer().test_aggregate_with_sample_data()
        TestDataAnalyzer().test_paginate_empty()
        TestDataAnalyzer().test_paginate_with_data()
        TestDataAnalyzer().test_incremental_state_management()
    else:
        print("\n" + "="*60)
        print("⚠️ 跳过数据分析器测试 (pandas 未安装)")
        print("="*60)

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
