"""
日志轮转模块

提供高级日志轮转功能，包括压缩、归档等。
"""

import os
import gzip
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Callable, Any
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import threading
import time


# ============================================================================
# 压缩轮转文件处理器
# ============================================================================

class CompressedRotatingFileHandler(RotatingFileHandler):
    """支持压缩的轮转文件处理器"""

    def __init__(
        self,
        filename: str,
        mode: str = 'a',
        maxBytes: int = 0,
        backupCount: int = 0,
        encoding: Optional[str] = None,
        delay: bool = False,
        compress: bool = True,
        compress_level: int = 6
    ):
        """
        初始化压缩轮转文件处理器

        Args:
            filename: 文件名
            mode: 文件模式
            maxBytes: 最大字节数
            backupCount: 备份文件数
            encoding: 编码
            delay: 延迟打开
            compress: 是否压缩
            compress_level: 压缩级别 (0-9)
        """
        super().__init__(
            filename,
            mode=mode,
            maxBytes=maxBytes,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay
        )
        self.compress = compress
        self.compress_level = compress_level

    def doRollover(self) -> None:
        """执行轮转"""
        if self.stream:
            self.stream.close()
            self.stream = None

        # 轮转文件
        if self.backupCount > 0:
            # 删除最旧的备份
            if os.path.exists(f"{self.baseFilename}.{self.backupCount}"):
                os.remove(f"{self.baseFilename}.{self.backupCount}")

            # 重命名现有备份
            for i in range(self.backupCount - 1, 0, -1):
                src = f"{self.baseFilename}.{i}"
                dst = f"{self.baseFilename}.{i + 1}"

                if os.path.exists(src):
                    # 压缩
                    if self.compress and i == 1:
                        self._compress_file(src, f"{src}.gz")
                        os.remove(src)
                    elif os.path.exists(f"{src}.gz"):
                        # 已压缩文件
                        shutil.move(f"{src}.gz", f"{dst}.gz")
                    else:
                        shutil.move(src, dst)

            # 轮转当前文件
            if os.path.exists(self.baseFilename):
                dest = f"{self.baseFilename}.1"
                shutil.move(self.baseFilename, dest)

                if self.compress:
                    self._compress_file(dest, f"{dest}.gz")
                    os.remove(dest)

        # 打开新文件
        if not self.delay:
            self.stream = open(self.baseFilename, self.mode, encoding=self.encoding)

    def _compress_file(self, src: str, dst: str) -> None:
        """
        压缩文件

        Args:
            src: 源文件
            dst: 目标文件
        """
        with open(src, 'rb') as f_in:
            with gzip.open(dst, 'wb', compresslevel=self.compress_level) as f_out:
                shutil.copyfileobj(f_in, f_out)


# ============================================================================
# 定时压缩轮转处理器
# ============================================================================

class CompressedTimedRotatingFileHandler(TimedRotatingFileHandler):
    """支持压缩的定时轮转文件处理器"""

    def __init__(
        self,
        filename: str,
        when: str = 'h',
        interval: int = 1,
        backupCount: int = 0,
        encoding: Optional[str] = None,
        delay: bool = False,
        utc: bool = False,
        atTime: Optional[Any] = None,
        compress: bool = True,
        compress_level: int = 6
    ):
        """
        初始化定时压缩轮转文件处理器

        Args:
            filename: 文件名
            when: 轮转时间单位
            interval: 间隔
            backupCount: 备份文件数
            encoding: 编码
            delay: 延迟打开
            utc: 是否使用 UTC
            atTime: 轮转时间
            compress: 是否压缩
            compress_level: 压缩级别
        """
        super().__init__(
            filename,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=atTime
        )
        self.compress = compress
        self.compress_level = compress_level

    def doRollover(self) -> None:
        """执行轮转"""
        if self.stream:
            self.stream.close()
            self.stream = None

        # 获取新文件名和时间
        currentTime = int(time.time())
        dstNow = self.computeRollover(currentTime)

        # 轮转
        if os.path.exists(self.baseFilename):
            # 确定新文件名
            dfn = self.rotation_filename(self.baseFilename + "." + self.extFmt)

            # 压缩旧文件
            if os.path.exists(dfn):
                os.remove(dfn)

            shutil.move(self.baseFilename, dfn)

            # 压缩
            if self.compress:
                self._compress_file(dfn, f"{dfn}.gz")
                os.remove(dfn)

        # 打开新文件
        if not self.delay:
            self.stream = open(self.baseFilename, self.mode, encoding=self.encoding)

        # 删除过期备份
        if self.backupCount > 0:
            self._delete_expired_backups()

    def _compress_file(self, src: str, dst: str) -> None:
        """压缩文件"""
        with open(src, 'rb') as f_in:
            with gzip.open(dst, 'wb', compresslevel=self.compress_level) as f_out:
                shutil.copyfileobj(f_in, f_out)

    def _delete_expired_backups(self) -> None:
        """删除过期备份"""
        # 获取所有备份文件
        backups = []

        base_name = Path(self.baseFilename).name
        log_dir = Path(self.baseFilename).parent

        for file in log_dir.glob(f"{base_name}.*"):
            if file.is_file():
                backups.append((file.stat().st_mtime, file))

        # 按时间排序
        backups.sort(reverse=True)

        # 删除超过备份数量的文件
        for mtime, file in backups[self.backupCount:]:
            try:
                if file.suffix == '.gz':
                    file.unlink()
                elif file.suffix not in ['.log', '.tmp']:
                    file.unlink()
            except Exception as e:
                print(f"删除备份文件失败: {file}, 错误: {e}")


# ============================================================================
# 日志清理器
# ============================================================================

class LogCleaner:
    """日志清理器"""

    def __init__(
        self,
        log_dir: str,
        max_age_days: int = 30,
        max_size_mb: Optional[int] = None,
        pattern: str = "*.log*"
    ):
        """
        初始化日志清理器

        Args:
            log_dir: 日志目录
            max_age_days: 最大保留天数
            max_size_mb: 最大总大小 (MB)
            pattern: 文件匹配模式
        """
        self.log_dir = Path(log_dir)
        self.max_age_days = max_age_days
        self.max_size_mb = max_size_mb
        self.pattern = pattern
        self._lock = threading.Lock()

    def clean(self) -> dict:
        """
        执行清理

        Returns:
            清理统计
        """
        with self._lock:
            stats = {
                "deleted_files": 0,
                "freed_space_mb": 0.0,
                "errors": []
            }

            if not self.log_dir.exists():
                return stats

            current_time = time.time()
            max_age_seconds = self.max_age_days * 24 * 3600

            # 获取所有日志文件
            log_files = list(self.log_dir.glob(self.pattern))
            files_to_delete = []

            # 按年龄清理
            for file in log_files:
                if file.is_file():
                    file_age = current_time - file.stat().st_mtime

                    if file_age > max_age_seconds:
                        files_to_delete.append(file)

            # 按总大小清理
            if self.max_size_mb:
                total_size = sum(
                    f.stat().st_size for f in log_files if f.is_file()
                )
                max_size_bytes = self.max_size_mb * 1024 * 1024

                if total_size > max_size_bytes:
                    # 按修改时间排序，删除最旧的
                    sorted_files = sorted(
                        [f for f in log_files if f.is_file()],
                        key=lambda f: f.stat().st_mtime
                    )

                    size_to_free = total_size - max_size_bytes
                    size_freed = 0

                    for file in sorted_files:
                        if size_freed < size_to_free and file not in files_to_delete:
                            files_to_delete.append(file)
                            size_freed += file.stat().st_size

            # 删除文件
            for file in files_to_delete:
                try:
                    file_size = file.stat().st_size
                    file.unlink()
                    stats["deleted_files"] += 1
                    stats["freed_space_mb"] += file_size / (1024 * 1024)
                except Exception as e:
                    stats["errors"].append(f"删除 {file} 失败: {str(e)}")

            stats["freed_space_mb"] = round(stats["freed_space_mb"], 2)

            return stats

    def get_stats(self) -> dict:
        """
        获取日志统计信息

        Returns:
            统计信息
        """
        if not self.log_dir.exists():
            return {
                "total_files": 0,
                "total_size_mb": 0.0,
                "oldest_file": None,
                "newest_file": None
            }

        log_files = list(self.log_dir.glob(self.pattern))
        log_files = [f for f in log_files if f.is_file()]

        if not log_files:
            return {
                "total_files": 0,
                "total_size_mb": 0.0,
                "oldest_file": None,
                "newest_file": None
            }

        total_size = sum(f.stat().st_size for f in log_files)
        sorted_files = sorted(log_files, key=lambda f: f.stat().st_mtime)

        return {
            "total_files": len(log_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_file": {
                "name": sorted_files[0].name,
                "age_days": (time.time() - sorted_files[0].stat().st_mtime) / (24 * 3600)
            },
            "newest_file": {
                "name": sorted_files[-1].name,
                "age_days": (time.time() - sorted_files[-1].stat().st_mtime) / (24 * 3600)
            }
        }


# ============================================================================
# 日志归档器
# ============================================================================

class LogArchiver:
    """日志归档器"""

    def __init__(
        self,
        log_dir: str,
        archive_dir: str,
        pattern: str = "*.log.*"
    ):
        """
        初始化日志归档器

        Args:
            log_dir: 日志目录
            archive_dir: 归档目录
            pattern: 文件匹配模式
        """
        self.log_dir = Path(log_dir)
        self.archive_dir = Path(archive_dir)
        self.pattern = pattern
        self._lock = threading.Lock()

    def archive(self, older_than_days: int = 7) -> dict:
        """
        归档日志文件

        Args:
            older_than_days: 归档超过指定天数的日志

        Returns:
            归档统计
        """
        with self._lock:
            stats = {
                "archived_files": 0,
                "archived_size_mb": 0.0,
                "errors": []
            }

            if not self.log_dir.exists():
                return stats

            # 创建归档目录
            self.archive_dir.mkdir(parents=True, exist_ok=True)

            # 获取要归档的文件
            current_time = time.time()
            max_age_seconds = older_than_days * 24 * 3600

            log_files = list(self.log_dir.glob(self.pattern))
            files_to_archive = []

            for file in log_files:
                if file.is_file():
                    file_age = current_time - file.stat().st_mtime
                    if file_age > max_age_seconds:
                        files_to_archive.append(file)

            # 归档文件
            for file in files_to_archive:
                try:
                    # 目标路径
                    dest_path = self.archive_dir / file.name

                    # 移动文件
                    shutil.move(str(file), str(dest_path))

                    file_size = dest_path.stat().st_size
                    stats["archived_files"] += 1
                    stats["archived_size_mb"] += file_size / (1024 * 1024)

                except Exception as e:
                    stats["errors"].append(f"归档 {file} 失败: {str(e)}")

            stats["archived_size_mb"] = round(stats["archived_size_mb"], 2)

            return stats

    def get_archive_stats(self) -> dict:
        """
        获取归档统计信息

        Returns:
            统计信息
        """
        if not self.archive_dir.exists():
            return {
                "total_files": 0,
                "total_size_mb": 0.0
            }

        archive_files = list(self.archive_dir.glob("*.*"))
        archive_files = [f for f in archive_files if f.is_file()]

        total_size = sum(f.stat().st_size for f in archive_files)

        return {
            "total_files": len(archive_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }


# ============================================================================
# 定时清理任务
# ============================================================================

class ScheduledLogCleaner:
    """定时日志清理器"""

    def __init__(
        self,
        cleaner: LogCleaner,
        interval_hours: int = 24
    ):
        """
        初始化定时清理器

        Args:
            cleaner: 日志清理器
            interval_hours: 清理间隔（小时）
        """
        self.cleaner = cleaner
        self.interval_hours = interval_hours
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """启动定时清理"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止定时清理"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        """运行循环"""
        while self._running:
            try:
                # 执行清理
                stats = self.cleaner.clean()
                print(f"日志清理完成: {stats}")

                # 等待下次清理
                for _ in range(self.interval_hours * 3600):
                    if not self._running:
                        break
                    time.sleep(1)

            except Exception as e:
                print(f"日志清理异常: {e}")
                time.sleep(60)  # 异常后等待 1 分钟


# ============================================================================
# 便捷函数
# ============================================================================

def create_compressed_handler(
    log_file: str,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    compress_level: int = 6
) -> CompressedRotatingFileHandler:
    """
    创建压缩轮转处理器

    Args:
        log_file: 日志文件
        max_bytes: 最大字节数
        backup_count: 备份文件数
        compress_level: 压缩级别

    Returns:
        处理器
    """
    return CompressedRotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        compress=True,
        compress_level=compress_level
    )


def create_timed_handler(
    log_file: str,
    when: str = 'midnight',
    interval: int = 1,
    backup_count: int = 30,
    compress: bool = True
) -> CompressedTimedRotatingFileHandler:
    """
    创建定时轮转处理器

    Args:
        log_file: 日志文件
        when: 轮转时间 (S/M/H/D/midnight)
        interval: 间隔
        backup_count: 备份文件数
        compress: 是否压缩

    Returns:
        处理器
    """
    return CompressedTimedRotatingFileHandler(
        filename=log_file,
        when=when,
        interval=interval,
        backupCount=backup_count,
        compress=compress
    )


# 导出
__all__ = [
    'CompressedRotatingFileHandler',
    'CompressedTimedRotatingFileHandler',
    'LogCleaner',
    'LogArchiver',
    'ScheduledLogCleaner',
    'create_compressed_handler',
    'create_timed_handler'
]
