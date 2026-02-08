"""
SQLite 数据库访问层

提供高性能的数据库访问接口，支持异步操作和连接池。
"""

import sqlite3
import asyncio
import json
import threading
from typing import Optional, Dict, Any, List, Union, Tuple
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

from .exceptions import DatabaseError, DatabaseConnectionError, DatabaseQueryError


# ============================================================================
# 数据库连接池
# ============================================================================

class SQLiteConnectionPool:
    """SQLite 连接池（线程安全）"""

    def __init__(
        self,
        db_path: Union[str, Path],
        max_connections: int = 5,
        check_same_thread: bool = False
    ):
        """
        初始化连接池

        Args:
            db_path: 数据库文件路径
            max_connections: 最大连接数
            check_same_thread: 是否检查同线程
        """
        self.db_path = Path(db_path)
        self.max_connections = max_connections
        self.check_same_thread = check_same_thread

        # 连接池
        self._connections: List[sqlite3.Connection] = []
        self._available = threading.Semaphore(max_connections)
        self._lock = threading.Lock()

        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_database()

    def _init_database(self) -> None:
        """初始化数据库（创建表）"""
        with self.get_connection() as conn:
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")

            # 创建示例表（根据需要扩展）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,
                    account_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    published_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    cron_expression TEXT NOT NULL,
                    workflow_config TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    account_id TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    status TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            """)

            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_account_id ON notes(account_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON schedules(enabled)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)")

            conn.commit()

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接（上下文管理器）

        Returns:
            数据库连接
        """
        self._available.acquire()

        conn = None
        try:
            with self._lock:
                if self._connections:
                    conn = self._connections.pop()
                else:
                    # 创建新连接
                    conn = sqlite3.connect(
                        self.db_path,
                        check_same_thread=self.check_same_thread
                    )
                    conn.row_factory = sqlite3.Row  # 返回字典形式的结果

            yield conn

        except Exception:
            # 发生错误时关闭连接
            if conn:
                conn.close()
            raise

        finally:
            # 归还连接
            if conn:
                with self._lock:
                    self._connections.append(conn)
            self._available.release()

    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        commit: bool = True
    ) -> sqlite3.Cursor:
        """
        执行 SQL 语句

        Args:
            sql: SQL 语句
            params: 参数
            commit: 是否提交

        Returns:
            游标对象

        Raises:
            DatabaseQueryError: 查询失败
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                if commit:
                    conn.commit()

                return cursor
        except Exception as e:
            raise DatabaseQueryError(
                message=f"Query failed: {sql}",
                query=sql[:200]
            ) from e

    def execute_many(
        self,
        sql: str,
        params_list: List[Tuple],
        commit: bool = True
    ) -> sqlite3.Cursor:
        """
        批量执行 SQL 语句

        Args:
            sql: SQL 语句
            params_list: 参数列表
            commit: 是否提交

        Returns:
            游标对象
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(sql, params_list)

                if commit:
                    conn.commit()

                return cursor
        except Exception as e:
            raise DatabaseQueryError(
                message=f"Batch query failed: {sql}",
                query=sql[:200]
            ) from e

    def fetch_one(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> Optional[sqlite3.Row]:
        """
        获取单行结果

        Args:
            sql: SQL 语句
            params: 参数

        Returns:
            行数据（如果存在）
        """
        cursor = self.execute(sql, params, commit=False)
        return cursor.fetchone()

    def fetch_all(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> List[sqlite3.Row]:
        """
        获取所有结果

        Args:
            sql: SQL 语句
            params: 参数

        Returns:
            行数据列表
        """
        cursor = self.execute(sql, params, commit=False)
        return cursor.fetchall()

    def close(self) -> None:
        """关闭所有连接"""
        with self._lock:
            for conn in self._connections:
                conn.close()
            self._connections.clear()


# ============================================================================
# 数据库管理器
# ============================================================================

class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径（如果为 None，使用默认路径）
        """
        if db_path is None:
            db_path = Path("data/database.sqlite")
        else:
            db_path = Path(db_path)

        self.pool = SQLiteConnectionPool(db_path)

    def execute(self, sql: str, params: Optional[Tuple] = None) -> sqlite3.Cursor:
        """执行 SQL 语句"""
        return self.pool.execute(sql, params)

    def fetch_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[sqlite3.Row]:
        """获取单行结果"""
        return self.pool.fetch_one(sql, params)

    def fetch_all(self, sql: str, params: Optional[Tuple] = None) -> List[sqlite3.Row]:
        """获取所有结果"""
        return self.pool.fetch_all(sql, params)

    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """
        插入数据

        Args:
            table: 表名
            data: 数据字典

        Returns:
            插入的行 ID
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        cursor = self.execute(sql, tuple(data.values()))
        return cursor.lastrowid

    def update(
        self,
        table: str,
        data: Dict[str, Any],
        where: Dict[str, Any]
    ) -> int:
        """
        更新数据

        Args:
            table: 表名
            data: 要更新的数据
            where: WHERE 条件

        Returns:
            影响的行数
        """
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])

        sql = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

        params = tuple(data.values()) + tuple(where.values())
        cursor = self.execute(sql, params)

        return cursor.rowcount

    def delete(self, table: str, where: Dict[str, Any]) -> int:
        """
        删除数据

        Args:
            table: 表名
            where: WHERE 条件

        Returns:
            影响的行数
        """
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
        sql = f"DELETE FROM {table} WHERE {where_clause}"

        cursor = self.execute(sql, tuple(where.values()))
        return cursor.rowcount

    def select(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[sqlite3.Row]:
        """
        查询数据

        Args:
            table: 表名
            where: WHERE 条件
            order_by: 排序字段
            limit: 限制行数

        Returns:
            行数据列表
        """
        sql = f"SELECT * FROM {table}"

        params = ()
        if where:
            where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
            sql += f" WHERE {where_clause}"
            params = tuple(where.values())

        if order_by:
            sql += f" ORDER BY {order_by}"

        if limit:
            sql += f" LIMIT {limit}"

        return self.fetch_all(sql, params)

    def count(self, table: str, where: Optional[Dict[str, Any]] = None) -> int:
        """
        统计行数

        Args:
            table: 表名
            where: WHERE 条件

        Returns:
            行数
        """
        sql = f"SELECT COUNT(*) as count FROM {table}"

        params = ()
        if where:
            where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
            sql += f" WHERE {where_clause}"
            params = tuple(where.values())

        row = self.fetch_one(sql, params)
        return row['count'] if row else 0

    def exists(self, table: str, where: Dict[str, Any]) -> bool:
        """
        检查数据是否存在

        Args:
            table: 表名
            where: WHERE 条件

        Returns:
            是否存在
        """
        return self.count(table, where) > 0

    def close(self) -> None:
        """关闭数据库连接"""
        self.pool.close()


# ============================================================================
# 异步数据库包装器
# ============================================================================

class AsyncDatabaseWrapper:
    """异步数据库包装器（在线程池中执行同步操作）"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化异步数据库包装器

        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self._executor = None

    async def _get_executor(self):
        """获取线程池执行器"""
        if self._executor is None:
            import concurrent.futures
            self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        return self._executor

    async def execute(self, sql: str, params: Optional[Tuple] = None) -> Any:
        """异步执行 SQL 语句"""
        executor = await self._get_executor()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            self.db_manager.execute,
            sql,
            params
        )

    async def fetch_one(self, sql: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """异步获取单行结果"""
        executor = await self._get_executor()
        loop = asyncio.get_event_loop()
        row = await loop.run_in_executor(
            executor,
            self.db_manager.fetch_one,
            sql,
            params
        )
        return dict(row) if row else None

    async def fetch_all(self, sql: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """异步获取所有结果"""
        executor = await self._get_executor()
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(
            executor,
            self.db_manager.fetch_all,
            sql,
            params
        )
        return [dict(row) for row in rows]

    async def insert(self, table: str, data: Dict[str, Any]) -> int:
        """异步插入数据"""
        executor = await self._get_executor()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            self.db_manager.insert,
            table,
            data
        )

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        where: Dict[str, Any]
    ) -> int:
        """异步更新数据"""
        executor = await self._get_executor()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            self.db_manager.update,
            table,
            data,
            where
        )

    async def delete(self, table: str, where: Dict[str, Any]) -> int:
        """异步删除数据"""
        executor = await self._get_executor()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            self.db_manager.delete,
            table,
            where
        )

    async def select(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """异步查询数据"""
        executor = await self._get_executor()
        loop = asyncio.get_event_loop()
        rows = await loop.run_in_executor(
            executor,
            self.db_manager.select,
            table,
            where,
            order_by,
            limit
        )
        return [dict(row) for row in rows]

    async def count(self, table: str, where: Optional[Dict[str, Any]] = None) -> int:
        """异步统计行数"""
        executor = await self._get_executor()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            self.db_manager.count,
            table,
            where
        )

    async def exists(self, table: str, where: Dict[str, Any]) -> bool:
        """异步检查数据是否存在"""
        executor = await self._get_executor()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            executor,
            self.db_manager.exists,
            table,
            where
        )


# ============================================================================
# 全局实例
# ============================================================================

# 默认数据库管理器
default_db_manager = DatabaseManager()

# 默认异步数据库包装器
default_async_db = AsyncDatabaseWrapper(default_db_manager)


# ============================================================================
# 便捷函数
# ============================================================================

def db_insert(table: str, data: Dict[str, Any]) -> int:
    """插入数据"""
    return default_db_manager.insert(table, data)


def db_update(table: str, data: Dict[str, Any], where: Dict[str, Any]) -> int:
    """更新数据"""
    return default_db_manager.update(table, data, where)


def db_delete(table: str, where: Dict[str, Any]) -> int:
    """删除数据"""
    return default_db_manager.delete(table, where)


def db_select(
    table: str,
    where: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None
) -> List[sqlite3.Row]:
    """查询数据"""
    return default_db_manager.select(table, where, order_by, limit)


def db_count(table: str, where: Optional[Dict[str, Any]] = None) -> int:
    """统计行数"""
    return default_db_manager.count(table, where)


def db_exists(table: str, where: Dict[str, Any]) -> bool:
    """检查数据是否存在"""
    return default_db_manager.exists(table, where)
