"""
日志存储和查询模块

提供集中日志存储和查询功能。
"""

import json
import sqlite3
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
import re


# ============================================================================
# 日志条目
# ============================================================================

@dataclass
class LogEntry:
    """日志条目"""
    timestamp: str
    level: str
    logger: str
    message: str
    module: str
    function: str
    line: int
    process_id: int
    thread_id: int
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """从字典创建"""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'LogEntry':
        """从 JSON 字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)


# ============================================================================
# 日志存储器
# ============================================================================

class LogStorage:
    """日志存储器"""

    def __init__(
        self,
        db_path: str = "logs/logs.db",
        buffer_size: int = 1000,
        flush_interval: float = 5.0
    ):
        """
        初始化日志存储器

        Args:
            db_path: 数据库路径
            buffer_size: 缓冲区大小
            flush_interval: 刷新间隔（秒）
        """
        self.db_path = Path(db_path)
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval

        # 缓冲区
        self._buffer: List[LogEntry] = []
        self._buffer_lock = threading.Lock()

        # 数据库连接
        self._conn: Optional[sqlite3.Connection] = None
        self._conn_lock = threading.Lock()

        # 自动刷新线程
        self._auto_flush = True
        self._flush_thread: Optional[threading.Thread] = None

        # 初始化数据库
        self._init_db()

        # 启动自动刷新
        self._start_auto_flush()

    def _init_db(self) -> None:
        """初始化数据库"""
        # 创建数据库目录
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 连接数据库
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False
        )

        # 创建表
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                logger TEXT NOT NULL,
                message TEXT NOT NULL,
                module TEXT,
                function TEXT,
                line INTEGER,
                process_id INTEGER,
                thread_id INTEGER,
                extra TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON logs(timestamp)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_level
            ON logs(level)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_logger
            ON logs(logger)
        """)

        self._conn.commit()

    def add(self, entry: LogEntry) -> None:
        """
        添加日志条目

        Args:
            entry: 日志条目
        """
        with self._buffer_lock:
            self._buffer.append(entry)

            # 缓冲区满时刷新
            if len(self._buffer) >= self.buffer_size:
                self._flush_buffer()

    def add_from_json(self, json_str: str) -> None:
        """
        从 JSON 字符串添加日志

        Args:
            json_str: JSON 字符串
        """
        try:
            entry = LogEntry.from_json(json_str)
            self.add(entry)
        except Exception as e:
            print(f"解析日志失败: {e}")

    def _flush_buffer(self) -> None:
        """刷新缓冲区到数据库"""
        with self._buffer_lock:
            if not self._buffer:
                return

            entries = self._buffer.copy()
            self._buffer.clear()

        with self._conn_lock:
            try:
                cursor = self._conn.cursor()

                for entry in entries:
                    cursor.execute("""
                        INSERT INTO logs (
                            timestamp, level, logger, message,
                            module, function, line,
                            process_id, thread_id, extra
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.timestamp,
                        entry.level,
                        entry.logger,
                        entry.message,
                        entry.module,
                        entry.function,
                        entry.line,
                        entry.process_id,
                        entry.thread_id,
                        json.dumps(entry.extra, ensure_ascii=False)
                    ))

                self._conn.commit()

            except Exception as e:
                print(f"刷新日志失败: {e}")

    def _start_auto_flush(self) -> None:
        """启动自动刷新线程"""
        def flush_loop():
            while self._auto_flush:
                time.sleep(self.flush_interval)
                self._flush_buffer()

        self._flush_thread = threading.Thread(target=flush_loop, daemon=True)
        self._flush_thread.start()

    def stop_auto_flush(self) -> None:
        """停止自动刷新"""
        self._auto_flush = False
        if self._flush_thread:
            self._flush_thread.join(timeout=10)
        # 最后刷新一次
        self._flush_buffer()

    def query(
        self,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        message_pattern: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[LogEntry]:
        """
        查询日志

        Args:
            level: 日志级别
            logger_name: 日志记录器名称
            start_time: 开始时间
            end_time: 结束时间
            message_pattern: 消息模式（正则表达式）
            limit: 返回数量
            offset: 偏移量

        Returns:
            日志条目列表
        """
        with self._conn_lock:
            try:
                # 刷新缓冲区
                self._flush_buffer()

                # 构建查询
                query = "SELECT * FROM logs WHERE 1=1"
                params = []

                if level:
                    query += " AND level = ?"
                    params.append(level)

                if logger_name:
                    query += " AND logger = ?"
                    params.append(logger_name)

                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time)

                if message_pattern:
                    query += " AND message REGEXP ?"
                    params.append(message_pattern)

                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                # 执行查询
                cursor = self._conn.cursor()
                cursor.execute(query, params)

                # 构建结果
                entries = []
                for row in cursor.fetchall():
                    entry = LogEntry(
                        timestamp=row[1],
                        level=row[2],
                        logger=row[3],
                        message=row[4],
                        module=row[5] or "",
                        function=row[6] or "",
                        line=row[7] or 0,
                        process_id=row[8] or 0,
                        thread_id=row[9] or 0,
                        extra=json.loads(row[10]) if row[10] else {}
                    )
                    entries.append(entry)

                return entries

            except Exception as e:
                print(f"查询日志失败: {e}")
                return []

    def search(
        self,
        keyword: str,
        limit: int = 100
    ) -> List[LogEntry]:
        """
        搜索日志

        Args:
            keyword: 关键词
            limit: 返回数量

        Returns:
            日志条目列表
        """
        with self._conn_lock:
            try:
                self._flush_buffer()

                cursor = self._conn.cursor()

                # 在消息和额外字段中搜索
                cursor.execute("""
                    SELECT * FROM logs
                    WHERE message LIKE ?
                       OR extra LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (f"%{keyword}%", f"%{keyword}%", limit))

                entries = []
                for row in cursor.fetchall():
                    entry = LogEntry(
                        timestamp=row[1],
                        level=row[2],
                        logger=row[3],
                        message=row[4],
                        module=row[5] or "",
                        function=row[6] or "",
                        line=row[7] or 0,
                        process_id=row[8] or 0,
                        thread_id=row[9] or 0,
                        extra=json.loads(row[10]) if row[10] else {}
                    )
                    entries.append(entry)

                return entries

            except Exception as e:
                print(f"搜索日志失败: {e}")
                return []

    def get_stats(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取日志统计

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            统计信息
        """
        with self._conn_lock:
            try:
                self._flush_buffer()

                cursor = self._conn.cursor()

                # 构建时间条件
                time_filter = ""
                params = []

                if start_time or end_time:
                    time_filter = "WHERE "
                    if start_time:
                        time_filter += "timestamp >= ?"
                        params.append(start_time)
                    if end_time:
                        if start_time:
                            time_filter += " AND "
                        time_filter += "timestamp <= ?"
                        params.append(end_time)

                # 总数
                cursor.execute(f"SELECT COUNT(*) FROM logs {time_filter}", params)
                total = cursor.fetchone()[0]

                # 按级别统计
                cursor.execute(f"""
                    SELECT level, COUNT(*) as count
                    FROM logs {time_filter}
                    GROUP BY level
                """, params)

                level_counts = {row[0]: row[1] for row in cursor.fetchall()}

                # 按日志记录器统计
                cursor.execute(f"""
                    SELECT logger, COUNT(*) as count
                    FROM logs {time_filter}
                    GROUP BY logger
                    ORDER BY count DESC
                    LIMIT 10
                """, params)

                logger_counts = {row[0]: row[1] for row in cursor.fetchall()}

                return {
                    "total": total,
                    "by_level": level_counts,
                    "by_logger": logger_counts
                }

            except Exception as e:
                print(f"获取统计失败: {e}")
                return {
                    "total": 0,
                    "by_level": {},
                    "by_logger": {}
                }

    def delete_old(self, days: int = 30) -> int:
        """
        删除旧日志

        Args:
            days: 保留天数

        Returns:
            删除的条目数
        """
        with self._conn_lock:
            try:
                cursor = self._conn.cursor()

                # 计算截止时间
                cutoff = datetime.now() - timedelta(days=days)

                # 删除
                cursor.execute("""
                    DELETE FROM logs
                    WHERE timestamp < ?
                """, (cutoff.strftime("%Y-%m-%dT%H:%M:%S"),))

                self._conn.commit()

                return cursor.rowcount

            except Exception as e:
                print(f"删除旧日志失败: {e}")
                return 0

    def close(self) -> None:
        """关闭存储器"""
        self.stop_auto_flush()

        if self._conn:
            self._conn.close()
            self._conn = None


# ============================================================================
# 日志处理器适配器
# ============================================================================

class StorageLogHandler(logging.Handler):
    """日志存储处理器"""

    def __init__(self, storage: LogStorage):
        """
        初始化处理器

        Args:
            storage: 日志存储器
        """
        super().__init__()
        self.storage = storage

    def emit(self, record: logging.LogRecord) -> None:
        """
        发送日志记录

        Args:
            record: 日志记录
        """
        try:
            # 构建日志条目
            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created).strftime(
                    "%Y-%m-%dT%H:%M:%S.%fZ"
                ),
                level=record.levelname,
                logger=record.name,
                message=record.getMessage(),
                module=record.module,
                function=record.funcName,
                line=record.lineno,
                process_id=record.process,
                thread_id=record.thread,
                extra=getattr(record, 'extra', {})
            )

            # 添加到存储
            self.storage.add(entry)

        except Exception as e:
            print(f"存储日志失败: {e}")


# ============================================================================
# 默认实例
# ============================================================================

# 默认日志存储
default_storage = LogStorage()


# ============================================================================
# 便捷函数
# ============================================================================

def query_logs(
    level: Optional[str] = None,
    logger_name: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    message_pattern: Optional[str] = None,
    limit: int = 100
) -> List[LogEntry]:
    """
    查询日志（使用默认存储）

    Args:
        level: 日志级别
        logger_name: 日志记录器名称
        start_time: 开始时间
        end_time: 结束时间
        message_pattern: 消息模式
        limit: 返回数量

    Returns:
        日志条目列表
    """
    return default_storage.query(
        level=level,
        logger_name=logger_name,
        start_time=start_time,
        end_time=end_time,
        message_pattern=message_pattern,
        limit=limit
    )


def search_logs(keyword: str, limit: int = 100) -> List[LogEntry]:
    """
    搜索日志（使用默认存储）

    Args:
        keyword: 关键词
        limit: 返回数量

    Returns:
        日志条目列表
    """
    return default_storage.search(keyword, limit)


def get_log_stats(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    获取日志统计（使用默认存储）

    Args:
        start_time: 开始时间
        end_time: 结束时间

    Returns:
        统计信息
    """
    return default_storage.get_stats(start_time, end_time)


# 导出
__all__ = [
    'LogEntry',
    'LogStorage',
    'StorageLogHandler',
    'default_storage',
    'query_logs',
    'search_logs',
    'get_log_stats'
]
