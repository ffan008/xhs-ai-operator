"""
异步文件 I/O 模块

提供异步文件操作接口，避免阻塞事件循环。
"""

import asyncio
import aiofiles
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from .exceptions import FileError


# ============================================================================
# 异步文件操作
# ============================================================================

class AsyncFileHandler:
    """异步文件处理器"""

    def __init__(self, base_path: Optional[Path] = None):
        """
        初始化异步文件处理器

        Args:
            base_path: 基础路径（如果为 None，使用当前目录）
        """
        self.base_path = base_path or Path.cwd()

    async def read_text(
        self,
        file_path: Union[str, Path],
        encoding: str = 'utf-8'
    ) -> str:
        """
        异步读取文本文件

        Args:
            file_path: 文件路径
            encoding: 文件编码

        Returns:
            文件内容

        Raises:
            FileError: 文件读取失败
        """
        try:
            full_path = self._resolve_path(file_path)
            async with aiofiles.open(full_path, mode='r', encoding=encoding) as f:
                return await f.read()
        except Exception as e:
            raise FileError(
                message=f"Failed to read file: {file_path}",
                file_path=str(file_path),
                operation="read"
            ) from e

    async def write_text(
        self,
        file_path: Union[str, Path],
        content: str,
        encoding: str = 'utf-8',
        make_parents: bool = True
    ) -> None:
        """
        异步写入文本文件

        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 文件编码
            make_parents: 是否创建父目录

        Raises:
            FileError: 文件写入失败
        """
        try:
            full_path = self._resolve_path(file_path)

            # 创建父目录
            if make_parents:
                full_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            async with aiofiles.open(full_path, mode='w', encoding=encoding) as f:
                await f.write(content)
        except Exception as e:
            raise FileError(
                message=f"Failed to write file: {file_path}",
                file_path=str(file_path),
                operation="write"
            ) from e

    async def read_bytes(self, file_path: Union[str, Path]) -> bytes:
        """
        异步读取二进制文件

        Args:
            file_path: 文件路径

        Returns:
            文件内容

        Raises:
            FileError: 文件读取失败
        """
        try:
            full_path = self._resolve_path(file_path)
            async with aiofiles.open(full_path, mode='rb') as f:
                return await f.read()
        except Exception as e:
            raise FileError(
                message=f"Failed to read file: {file_path}",
                file_path=str(file_path),
                operation="read"
            ) from e

    async def write_bytes(
        self,
        file_path: Union[str, Path],
        content: bytes,
        make_parents: bool = True
    ) -> None:
        """
        异步写入二进制文件

        Args:
            file_path: 文件路径
            content: 文件内容
            make_parents: 是否创建父目录

        Raises:
            FileError: 文件写入失败
        """
        try:
            full_path = self._resolve_path(file_path)

            # 创建父目录
            if make_parents:
                full_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            async with aiofiles.open(full_path, mode='wb') as f:
                await f.write(content)
        except Exception as e:
            raise FileError(
                message=f"Failed to write file: {file_path}",
                file_path=str(file_path),
                operation="write"
            ) from e

    async def read_json(
        self,
        file_path: Union[str, Path],
        encoding: str = 'utf-8'
    ) -> Dict[str, Any]:
        """
        异步读取 JSON 文件

        Args:
            file_path: 文件路径
            encoding: 文件编码

        Returns:
            JSON 数据

        Raises:
            FileError: 文件读取或解析失败
        """
        try:
            content = await self.read_text(file_path, encoding)
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise FileError(
                message=f"Invalid JSON in file: {file_path}",
                file_path=str(file_path),
                operation="read"
            ) from e

    async def write_json(
        self,
        file_path: Union[str, Path],
        data: Dict[str, Any],
        encoding: str = 'utf-8',
        indent: int = 2,
        ensure_ascii: bool = False
    ) -> None:
        """
        异步写入 JSON 文件

        Args:
            file_path: 文件路径
            data: JSON 数据
            encoding: 文件编码
            indent: 缩进空格数
            ensure_ascii: 是否确保 ASCII 编码

        Raises:
            FileError: 文件写入失败
        """
        try:
            content = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
            await self.write_text(file_path, content, encoding)
        except Exception as e:
            raise FileError(
                message=f"Failed to write JSON file: {file_path}",
                file_path=str(file_path),
                operation="write"
            ) from e

    async def append_text(
        self,
        file_path: Union[str, Path],
        content: str,
        encoding: str = 'utf-8'
    ) -> None:
        """
        异步追加文本到文件

        Args:
            file_path: 文件路径
            content: 要追加的内容
            encoding: 文件编码

        Raises:
            FileError: 文件写入失败
        """
        try:
            full_path = self._resolve_path(file_path)
            async with aiofiles.open(full_path, mode='a', encoding=encoding) as f:
                await f.write(content)
        except Exception as e:
            raise FileError(
                message=f"Failed to append to file: {file_path}",
                file_path=str(file_path),
                operation="append"
            ) from e

    async def exists(self, file_path: Union[str, Path]) -> bool:
        """
        检查文件是否存在

        Args:
            file_path: 文件路径

        Returns:
            文件是否存在
        """
        full_path = self._resolve_path(file_path)
        return full_path.exists()

    async def delete(self, file_path: Union[str, Path]) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径

        Returns:
            是否删除成功
        """
        try:
            full_path = self._resolve_path(file_path)
            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False

    async def list_files(
        self,
        directory: Union[str, Path],
        pattern: str = "*",
        recursive: bool = False
    ) -> List[Path]:
        """
        列出目录中的文件

        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            recursive: 是否递归列出

        Returns:
            文件路径列表
        """
        full_path = self._resolve_path(directory)

        if recursive:
            return list(full_path.rglob(pattern))
        else:
            return list(full_path.glob(pattern))

    def _resolve_path(self, file_path: Union[str, Path]) -> Path:
        """
        解析文件路径

        Args:
            file_path: 文件路径

        Returns:
            解析后的绝对路径
        """
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self.base_path / path


# ============================================================================
# 批量文件操作
# ============================================================================

class AsyncBatchFileHandler:
    """批量异步文件处理器"""

    def __init__(self, file_handler: Optional[AsyncFileHandler] = None):
        """
        初始化批量文件处理器

        Args:
            file_handler: 文件处理器（如果为 None，创建新的）
        """
        self.file_handler = file_handler or AsyncFileHandler()

    async def read_multiple_files(
        self,
        file_paths: List[Union[str, Path]]
    ) -> Dict[str, str]:
        """
        并发读取多个文件

        Args:
            file_paths: 文件路径列表

        Returns:
            文件路径到内容的映射
        """
        tasks = {
            str(path): asyncio.create_task(self.file_handler.read_text(path))
            for path in file_paths
        }

        results = {}
        for path_str, task in tasks.items():
            try:
                results[path_str] = await task
            except Exception:
                results[path_str] = None

        return results

    async def write_multiple_files(
        self,
        file_data: Dict[Union[str, Path], str]
    ) -> Dict[str, bool]:
        """
        并发写入多个文件

        Args:
            file_data: 文件路径到内容的映射

        Returns:
            文件路径到成功状态的映射
        """
        tasks = {
            str(path): asyncio.create_task(self.file_handler.write_text(path, content))
            for path, content in file_data.items()
        }

        results = {}
        for path_str, task in tasks.items():
            try:
                await task
                results[path_str] = True
            except Exception:
                results[path_str] = False

        return results

    async def batch_read_json(
        self,
        file_paths: List[Union[str, Path]]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量读取 JSON 文件

        Args:
            file_paths: 文件路径列表

        Returns:
            文件路径到 JSON 数据的映射
        """
        tasks = {
            str(path): asyncio.create_task(self.file_handler.read_json(path))
            for path in file_paths
        }

        results = {}
        for path_str, task in tasks.items():
            try:
                results[path_str] = await task
            except Exception:
                results[path_str] = None

        return results


# ============================================================================
# 全局实例
# ============================================================================

# 默认异步文件处理器
default_async_file_handler = AsyncFileHandler()

# 默认批量文件处理器
default_batch_file_handler = AsyncBatchFileHandler()


# ============================================================================
# 便捷函数
# ============================================================================

async def read_file(file_path: Union[str, Path]) -> str:
    """异步读取文件"""
    return await default_async_file_handler.read_text(file_path)


async def write_file(file_path: Union[str, Path], content: str) -> None:
    """异步写入文件"""
    await default_async_file_handler.write_text(file_path, content)


async def read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """异步读取 JSON 文件"""
    return await default_async_file_handler.read_json(file_path)


async def write_json(file_path: Union[str, Path], data: Dict[str, Any]) -> None:
    """异步写入 JSON 文件"""
    await default_async_file_handler.write_json(file_path, data)


async def file_exists(file_path: Union[str, Path]) -> bool:
    """检查文件是否存在"""
    return await default_async_file_handler.exists(file_path)


async def delete_file(file_path: Union[str, Path]) -> bool:
    """删除文件"""
    return await default_async_file_handler.delete(file_path)
