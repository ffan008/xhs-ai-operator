"""
数据分析模块

提供高性能的数据分析功能，支持向量化计算、增量分析、分页查询等。
"""

import asyncio
import hashlib
import json
from typing import (
    Optional, Dict, Any, List, Union, Callable, Awaitable,
    Tuple, Iterable, TYPE_CHECKING
)
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

if TYPE_CHECKING:
    import pandas as pd
    import numpy as np

try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None  # type: ignore
    np = None  # type: ignore

from .cache import RedisCache, MemoryCache
from .database import DatabaseManager
from .exceptions import BusinessError


# ============================================================================
# 聚合类型
# ============================================================================

class AggregationType(str, Enum):
    """聚合类型"""
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    STD = "std"          # 标准差
    VAR = "var"          # 方差
    QUANTILE = "quantile"  # 分位数


# ============================================================================
# 分页配置
# ============================================================================

@dataclass
class PaginationConfig:
    """分页配置"""
    page: int = 1
    page_size: int = 100
    max_page_size: int = 1000

    def __post_init__(self):
        """验证并修正参数"""
        if self.page < 1:
            self.page = 1
        if self.page_size < 1:
            self.page_size = 100
        if self.page_size > self.max_page_size:
            self.page_size = self.max_page_size

    @property
    def offset(self) -> int:
        """获取偏移量"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """获取限制数量"""
        return self.page_size


# ============================================================================
# 分页结果
# ============================================================================

@dataclass
class PaginatedResult:
    """分页结果"""
    data: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    @classmethod
    def from_data(
        cls,
        data: List[Dict[str, Any]],
        total: int,
        pagination: PaginationConfig
    ) -> "PaginatedResult":
        """
        从数据创建分页结果

        Args:
            data: 当前页数据
            total: 总数据量
            pagination: 分页配置

        Returns:
            分页结果
        """
        total_pages = (total + pagination.page_size - 1) // pagination.page_size

        return cls(
            data=data,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_prev=pagination.page > 1
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "data": self.data,
            "pagination": {
                "total": self.total,
                "page": self.page,
                "page_size": self.page_size,
                "total_pages": self.total_pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev
            }
        }


# ============================================================================
# 增量分析状态
# ============================================================================

@dataclass
class IncrementalState:
    """增量分析状态"""
    last_id: Optional[str] = None
    last_timestamp: Optional[str] = None
    checksum: Optional[str] = None
    processed_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "last_id": self.last_id,
            "last_timestamp": self.last_timestamp,
            "checksum": self.checksum,
            "processed_count": self.processed_count,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncrementalState":
        """从字典创建"""
        return cls(**data)


# ============================================================================
# 数据分析器
# ============================================================================

class DataAnalyzer:
    """数据分析器"""

    def __init__(
        self,
        db: Optional[DatabaseManager] = None,
        cache: Optional[Union[RedisCache, MemoryCache]] = None
    ):
        """
        初始化数据分析器

        Args:
            db: 数据库管理器
            cache: 缓存实例
        """
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required. Install with: pip install pandas numpy")

        self.db = db or DatabaseManager()
        self.cache = cache or MemoryCache()

        # 分析统计
        self._stats = {
            "total_analyses": 0,
            "cached_analyses": 0,
            "incremental_analyses": 0,
            "total_records_processed": 0
        }

    def _load_data(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> "pd.DataFrame":
        """
        从数据库加载数据到 DataFrame

        Args:
            table: 表名
            where: 查询条件
            columns: 列名列表
            limit: 限制数量

        Returns:
            DataFrame
        """
        rows = self.db.select(
            table,
            where=where,
            limit=limit
        )

        if not rows:
            return pd.DataFrame()

        # 转换为 DataFrame
        df = pd.DataFrame([dict(row) for row in rows])

        # 选择列
        if columns:
            available_cols = [c for c in columns if c in df.columns]
            df = df[available_cols] if available_cols else df

        return df

    def _make_cache_key(
        self,
        operation: str,
        table: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成缓存键"""
        key_parts = [operation, table]

        if params:
            params_str = json.dumps(params, sort_keys=True)
            key_parts.append(params_str)

        key_string = ":".join(key_parts)
        hash_value = hashlib.md5(key_string.encode()).hexdigest()

        return f"analytics:{hash_value}"

    # ========================================================================
    # 基础聚合
    # ========================================================================

    def aggregate(
        self,
        table: str,
        group_by: Optional[List[str]] = None,
        aggregations: Optional[Dict[str, List[AggregationType]]] = None,
        where: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> Union[Dict[str, Any], "pd.DataFrame"]:
        """
        聚合分析

        Args:
            table: 表名
            group_by: 分组字段
            aggregations: 聚合定义 {列名: [聚合类型, ...]}
            where: 查询条件
            use_cache: 是否使用缓存

        Returns:
            聚合结果
        """
        self._stats["total_analyses"] += 1

        # 检查缓存
        if use_cache:
            cache_key = self._make_cache_key(
                "aggregate",
                table,
                {"group_by": group_by, "aggregations": aggregations, "where": where}
            )
            cached = self.cache.get(cache_key)
            if cached:
                self._stats["cached_analyses"] += 1
                return cached

        # 加载数据
        df = self._load_data(table, where)

        if df.empty:
            return {} if group_by else {}

        # 执行聚合
        if group_by:
            result = self._group_and_aggregate(df, group_by, aggregations)
        else:
            result = self._aggregate_all(df, aggregations)

        # 缓存结果
        if use_cache:
            self.cache.set(cache_key, result, ttl=300)

        return result

    def _group_and_aggregate(
        self,
        df: "pd.DataFrame",
        group_by: List[str],
        aggregations: Optional[Dict[str, List[AggregationType]]] = None
    ) -> "pd.DataFrame":
        """
        分组聚合

        Args:
            df: DataFrame
            group_by: 分组字段
            aggregations: 聚合定义

        Returns:
            聚合结果 DataFrame
        """
        # 确保分组列存在
        available_groups = [g for g in group_by if g in df.columns]
        if not available_groups:
            return pd.DataFrame()

        grouped = df.groupby(available_groups, dropna=False)

        if not aggregations:
            # 默认计数
            result = grouped.size().reset_index(name="count")
            return result

        # 构建聚合字典
        agg_dict = {}
        for col, agg_types in aggregations.items():
            if col not in df.columns:
                continue

            agg_funcs = []
            for agg_type in agg_types:
                if agg_type == AggregationType.COUNT:
                    agg_funcs.append("count")
                elif agg_type == AggregationType.SUM:
                    agg_funcs.append("sum")
                elif agg_type == AggregationType.MEAN:
                    agg_funcs.append("mean")
                elif agg_type == AggregationType.MEDIAN:
                    agg_funcs.append("median")
                elif agg_type == AggregationType.MIN:
                    agg_funcs.append("min")
                elif agg_type == AggregationType.MAX:
                    agg_funcs.append("max")
                elif agg_type == AggregationType.STD:
                    agg_funcs.append("std")
                elif agg_type == AggregationType.VAR:
                    agg_funcs.append("var")

            if agg_funcs:
                agg_dict[col] = agg_funcs

        if not agg_dict:
            return pd.DataFrame()

        # 执行聚合
        result = grouped.agg(agg_dict).reset_index()

        # 扁平化列名
        if isinstance(result.columns, pd.MultiIndex):
            result.columns = ["_".join(col).strip() for col in result.columns.values]

        return result

    def _aggregate_all(
        self,
        df: "pd.DataFrame",
        aggregations: Optional[Dict[str, List[AggregationType]]] = None
    ) -> Dict[str, Any]:
        """
        全局聚合

        Args:
            df: DataFrame
            aggregations: 聚合定义

        Returns:
            聚合结果字典
        """
        if not aggregations:
            # 默认统计
            return {
                "count": len(df),
                "columns": list(df.columns)
            }

        result = {}

        for col, agg_types in aggregations.items():
            if col not in df.columns:
                continue

            series = df[col]

            for agg_type in agg_types:
                key = f"{col}_{agg_type.value}"

                try:
                    if agg_type == AggregationType.COUNT:
                        result[key] = series.count()
                    elif agg_type == AggregationType.SUM:
                        result[key] = series.sum()
                    elif agg_type == AggregationType.MEAN:
                        result[key] = series.mean()
                    elif agg_type == AggregationType.MEDIAN:
                        result[key] = series.median()
                    elif agg_type == AggregationType.MIN:
                        result[key] = series.min()
                    elif agg_type == AggregationType.MAX:
                        result[key] = series.max()
                    elif agg_type == AggregationType.STD:
                        result[key] = series.std()
                    elif agg_type == AggregationType.VAR:
                        result[key] = series.var()
                    elif agg_type == AggregationType.QUANTILE:
                        result[key] = series.quantile(0.5)
                except Exception:
                    result[key] = None

        return result

    # ========================================================================
    # 向量化计算
    # ========================================================================

    def calculate(
        self,
        table: str,
        expressions: Dict[str, str],
        where: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> "pd.DataFrame":
        """
        向量化计算

        Args:
            table: 表名
            expressions: 计算表达式 {新列名: 表达式}
            where: 查询条件
            use_cache: 是否使用缓存

        Returns:
            计算后的 DataFrame

        示例:
            analyzer.calculate("notes", {
                "engagement_rate": "likes_count / views_count * 100",
                "score": "likes_count * 0.5 + comments_count * 0.3 + collects_count * 0.2"
            })
        """
        self._stats["total_analyses"] += 1

        # 加载数据
        df = self._load_data(table, where)

        if df.empty:
            return df

        # 向量化计算
        for col_name, expr in expressions.items():
            try:
                # 安全评估表达式
                df[col_name] = df.eval(expr)
            except Exception as e:
                raise BusinessError(
                    message=f"Failed to evaluate expression: {expr}",
                    user_message=f"计算表达式失败: {expr}"
                )

        return df

    def filter(
        self,
        table: str,
        filters: Dict[str, Any],
        where: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> "pd.DataFrame":
        """
        向量化过滤

        Args:
            table: 表名
            filters: 过滤条件（支持表达式）
            where: 数据库查询条件
            use_cache: 是否使用缓存

        Returns:
            过滤后的 DataFrame

        示例:
            analyzer.filter("notes", {
                "engagement_rate": "> 10",
                "likes_count": [">", 100],
                "title": ["contains", "测试"]
            })
        """
        self._stats["total_analyses"] += 1

        # 加载数据
        df = self._load_data(table, where)

        if df.empty:
            return df

        # 应用过滤
        mask = pd.Series([True] * len(df), index=df.index)

        for col, condition in filters.items():
            if col not in df.columns:
                continue

            series = df[col]

            if isinstance(condition, str):
                # 表达式过滤
                try:
                    mask &= series.eval(condition)
                except Exception:
                    pass
            elif isinstance(condition, list) and len(condition) == 2:
                op, value = condition

                if op == ">":
                    mask &= series > value
                elif op == ">=":
                    mask &= series >= value
                elif op == "<":
                    mask &= series < value
                elif op == "<=":
                    mask &= series <= value
                elif op == "==":
                    mask &= series == value
                elif op == "!=":
                    mask &= series != value
                elif op == "in":
                    mask &= series.isin(value)
                elif op == "contains":
                    mask &= series.astype(str).str.contains(str(value), na=False)
                elif op == "startswith":
                    mask &= series.astype(str).str.startswith(str(value), na=False)
                elif op == "endswith":
                    mask &= series.astype(str).str.endswith(str(value), na=False)

        return df[mask].reset_index(drop=True)

    # ========================================================================
    # 分页查询
    # ========================================================================

    def paginate(
        self,
        table: str,
        pagination: PaginationConfig,
        where: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> PaginatedResult:
        """
        分页查询

        Args:
            table: 表名
            pagination: 分页配置
            where: 查询条件
            order_by: 排序字段
            order_desc: 是否降序

        Returns:
            分页结果
        """
        # 获取总数
        total = self.db.count(table, where=where)

        # 构建排序字符串
        order_by_str = None
        if order_by:
            order_by_str = f"{order_by} DESC" if order_desc else f"{order_by} ASC"

        # 获取当前页数据
        rows = self.db.select(
            table,
            where=where,
            limit=pagination.limit,
            offset=pagination.offset,
            order_by=order_by_str
        )

        data = [dict(row) for row in rows] if rows else []

        return PaginatedResult.from_data(data, total, pagination)

    # ========================================================================
    # 增量分析
    # ========================================================================

    def incremental_analyze(
        self,
        table: str,
        analyze_func: Callable[["pd.DataFrame"], Dict[str, Any]],
        state_key: str,
        id_column: str = "id",
        timestamp_column: str = "created_at",
        where: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], IncrementalState]:
        """
        增量分析

        Args:
            table: 表名
            analyze_func: 分析函数
            state_key: 状态键（用于保存增量状态）
            id_column: ID 列名
            timestamp_column: 时间戳列名
            where: 额外查询条件

        Returns:
            (分析结果, 新状态)
        """
        self._stats["total_analyses"] += 1
        self._stats["incremental_analyses"] += 1

        # 加载上一次的状态
        state = self._load_incremental_state(state_key)

        # 构建查询条件（只获取新数据）
        query_where = where.copy() if where else {}

        if state.last_id and id_column in self.db.get_table_columns(table):
            # 使用 ID 过滤
            query_where[f"{id_column} >"] = state.last_id

        elif state.last_timestamp and timestamp_column:
            # 使用时间戳过滤
            query_where[f"{timestamp_column} >"] = state.last_timestamp

        # 加载新数据
        df = self._load_data(table, query_where)

        if df.empty:
            return {}, state

        # 执行分析
        result = analyze_func(df)

        # 更新状态
        new_state = IncrementalState(
            last_id=df[id_column].max() if id_column in df.columns else None,
            last_timestamp=df[timestamp_column].max() if timestamp_column in df.columns else None,
            processed_count=state.processed_count + len(df),
            metadata=result.get("metadata", {})
        )

        # 保存状态
        self._save_incremental_state(state_key, new_state)

        # 更新统计
        self._stats["total_records_processed"] += len(df)

        return result, new_state

    def _load_incremental_state(self, key: str) -> IncrementalState:
        """加载增量状态"""
        cache_key = f"incremental_state:{key}"
        data = self.cache.get(cache_key)

        if data:
            return IncrementalState.from_dict(data)

        return IncrementalState()

    def _save_incremental_state(self, key: str, state: IncrementalState) -> None:
        """保存增量状态"""
        cache_key = f"incremental_state:{key}"
        self.cache.set(cache_key, state.to_dict(), ttl=86400 * 7)  # 7天

    def reset_incremental_state(self, key: str) -> None:
        """重置增量状态"""
        cache_key = f"incremental_state:{key}"
        self.cache.delete(cache_key)

    # ========================================================================
    # 时间序列分析
    # ========================================================================

    def time_series_analysis(
        self,
        table: str,
        date_column: str,
        metrics: List[str],
        group_by: str = "day",
        where: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> "pd.DataFrame":
        """
        时间序列分析

        Args:
            table: 表名
            date_column: 日期列名
            metrics: 指标列名列表
            group_by: 分组粒度 (day, week, month, hour)
            where: 查询条件
            use_cache: 是否使用缓存

        Returns:
            时间序列 DataFrame
        """
        self._stats["total_analyses"] += 1

        # 加载数据
        df = self._load_data(table, where)

        if df.empty or date_column not in df.columns:
            return pd.DataFrame()

        # 转换日期列
        df[date_column] = pd.to_datetime(df[date_column])

        # 按时间分组
        if group_by == "hour":
            df["time_group"] = df[date_column].dt.floor("H")
        elif group_by == "day":
            df["time_group"] = df[date_column].dt.floor("D")
        elif group_by == "week":
            df["time_group"] = df[date_column].dt.to_period("W").apply(lambda r: r.start_time)
        elif group_by == "month":
            df["time_group"] = df[date_column].dt.to_period("M").apply(lambda r: r.start_time)
        else:
            df["time_group"] = df[date_column].dt.floor("D")

        # 聚合指标
        result_df = df.groupby("time_group")

        aggregations = {}
        for metric in metrics:
            if metric in df.columns:
                aggregations[metric] = ["sum", "count", "mean"]

        if aggregations:
            result = result_df.agg(aggregations).reset_index()
            # 扁平化列名
            if isinstance(result.columns, pd.MultiIndex):
                result.columns = ["_".join(col).strip("_") for col in result.columns.values]
        else:
            result = result_df.size().reset_index(name="count")

        return result

    # ========================================================================
    # 统计信息
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_analyses": 0,
            "cached_analyses": 0,
            "incremental_analyses": 0,
            "total_records_processed": 0
        }


# ============================================================================
# 便捷函数
# ============================================================================

# 默认分析器
default_analyzer = DataAnalyzer()


def analyze_aggregate(
    table: str,
    group_by: Optional[List[str]] = None,
    aggregations: Optional[Dict[str, List[AggregationType]]] = None,
    where: Optional[Dict[str, Any]] = None
) -> Union[Dict[str, Any], "pd.DataFrame"]:
    """
    聚合分析（使用默认分析器）

    Args:
        table: 表名
        group_by: 分组字段
        aggregations: 聚合定义
        where: 查询条件

    Returns:
        聚合结果
    """
    return default_analyzer.aggregate(table, group_by, aggregations, where)


def analyze_paginate(
    table: str,
    page: int = 1,
    page_size: int = 100,
    where: Optional[Dict[str, Any]] = None
) -> PaginatedResult:
    """
    分页查询（使用默认分析器）

    Args:
        table: 表名
        page: 页码
        page_size: 每页大小
        where: 查询条件

    Returns:
        分页结果
    """
    pagination = PaginationConfig(page=page, page_size=page_size)
    return default_analyzer.paginate(table, pagination, where)


def analyze_time_series(
    table: str,
    date_column: str,
    metrics: List[str],
    group_by: str = "day",
    where: Optional[Dict[str, Any]] = None
) -> "pd.DataFrame":
    """
    时间序列分析（使用默认分析器）

    Args:
        table: 表名
        date_column: 日期列名
        metrics: 指标列表
        group_by: 分组粒度
        where: 查询条件

    Returns:
        时间序列 DataFrame
    """
    return default_analyzer.time_series_analysis(
        table, date_column, metrics, group_by, where
    )
