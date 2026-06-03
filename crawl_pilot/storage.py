"""
CrawlPilot - 存储后端模块

提供多种本地存储后端，包括JSON文件、CSV文件和SQLite数据库。

核心类：
    - StorageBackend: 存储后端抽象基类
    - JSONStorage: JSON文件存储
    - CSVStorage: CSV文件存储
    - SQLiteStorage: SQLite数据库存储
"""

import csv
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from crawl_pilot.utils import StorageError

logger = logging.getLogger("crawl_pilot.storage")


# ============================================================
# StorageBackend - 抽象基类
# ============================================================

class StorageBackend(ABC):
    """存储后端抽象基类。

    定义存储后端的统一接口，所有具体存储实现都必须继承此类。

    Attributes:
        output_dir: 输出目录
        field_mapping: 字段映射

    Examples:
        >>> class MyStorage(StorageBackend):
        ...     def save(self, data):
        ...         pass
        ...     def close(self):
        ...         pass
    """

    def __init__(
        self,
        output_dir: str = "./output",
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        """初始化存储后端。

        Args:
            output_dir: 输出目录
            field_mapping: 字段映射（存储字段名 -> 数据字段名）
        """
        self.output_dir = output_dir
        self.field_mapping = field_mapping or {}
        self._count = 0

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    @abstractmethod
    def save(self, data: Dict[str, Any]) -> None:
        """保存单条数据。

        Args:
            data: 数据字典
        """
        raise NotImplementedError

    @abstractmethod
    def save_many(self, data_list: List[Dict[str, Any]]) -> None:
        """批量保存数据。

        Args:
            data_list: 数据字典列表
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """关闭存储后端，释放资源。"""
        raise NotImplementedError

    @property
    def count(self) -> int:
        """获取已保存的数据条数。"""
        return self._count

    def _apply_mapping(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用字段映射。

        Args:
            data: 原始数据

        Returns:
            映射后的数据
        """
        if not self.field_mapping:
            return data
        mapped: Dict[str, Any] = {}
        for storage_key, data_key in self.field_mapping.items():
            if data_key in data:
                mapped[storage_key] = data[data_key]
        # 添加未映射的字段
        for key, value in data.items():
            if key not in mapped:
                mapped[key] = value
        return mapped

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} dir={self.output_dir} count={self._count}>"


# ============================================================
# JSONStorage - JSON文件存储
# ============================================================

class JSONStorage(StorageBackend):
    """JSON文件存储后端。

    将数据保存为JSON文件，支持增量写入。
    每次调用save()时将数据追加到内存列表中，
    close()时一次性写入文件。

    Attributes:
        output_dir: 输出目录
        filename: 输出文件名
        _data: 内存中的数据列表

    Examples:
        >>> storage = JSONStorage(output_dir="./data", filename="results.json")
        >>> storage.save({"url": "https://example.com", "title": "Example"})
        >>> storage.save({"url": "https://example.org", "title": "Example Org"})
        >>> storage.close()
    """

    def __init__(
        self,
        output_dir: str = "./output",
        filename: str = "results.json",
        field_mapping: Optional[Dict[str, str]] = None,
        indent: int = 2,
        ensure_ascii: bool = False,
    ) -> None:
        """初始化JSON存储。

        Args:
            output_dir: 输出目录
            filename: 输出文件名
            field_mapping: 字段映射
            indent: JSON缩进
            ensure_ascii: 是否确保ASCII编码
        """
        super().__init__(output_dir, field_mapping)
        self.filename = filename
        self.indent = indent
        self.ensure_ascii = ensure_ascii
        self._data: List[Dict[str, Any]] = []

    def save(self, data: Dict[str, Any]) -> None:
        """保存单条数据。

        Args:
            data: 数据字典
        """
        mapped = self._apply_mapping(data)
        self._data.append(mapped)
        self._count += 1

    def save_many(self, data_list: List[Dict[str, Any]]) -> None:
        """批量保存数据。

        Args:
            data_list: 数据字典列表
        """
        for data in data_list:
            self.save(data)

    def close(self) -> None:
        """关闭存储，将数据写入文件。"""
        if not self._data:
            logger.debug("无数据需要写入")
            return

        filepath = os.path.join(self.output_dir, self.filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    self._data,
                    f,
                    indent=self.indent,
                    ensure_ascii=self.ensure_ascii,
                )
            logger.info(f"JSON数据已保存: {filepath} ({self._count} 条)")
        except Exception as e:
            raise StorageError(f"JSON写入失败: {e}", path=filepath)

    def flush(self) -> None:
        """立即将数据写入文件（不关闭存储）。"""
        self.close()

    def get_data(self) -> List[Dict[str, Any]]:
        """获取内存中的数据。

        Returns:
            数据列表
        """
        return list(self._data)


# ============================================================
# CSVStorage - CSV文件存储
# ============================================================

class CSVStorage(StorageBackend):
    """CSV文件存储后端。

    将数据保存为CSV文件，支持增量写入。
    第一条数据写入时自动创建表头。

    Attributes:
        output_dir: 输出目录
        filename: 输出文件名
        _fieldnames: CSV列名列表

    Examples:
        >>> storage = CSVStorage(output_dir="./data", filename="results.csv")
        >>> storage.save({"url": "https://example.com", "title": "Example"})
        >>> storage.save({"url": "https://example.org", "title": "Example Org"})
        >>> storage.close()
    """

    def __init__(
        self,
        output_dir: str = "./output",
        filename: str = "results.csv",
        field_mapping: Optional[Dict[str, str]] = None,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ) -> None:
        """初始化CSV存储。

        Args:
            output_dir: 输出目录
            filename: 输出文件名
            field_mapping: 字段映射
            encoding: 文件编码
            delimiter: 分隔符
        """
        super().__init__(output_dir, field_mapping)
        self.filename = filename
        self.encoding = encoding
        self.delimiter = delimiter
        self._fieldnames: List[str] = []
        self._filepath = os.path.join(output_dir, filename)
        self._file: Optional[Any] = None
        self._writer: Optional[Any] = None

    def save(self, data: Dict[str, Any]) -> None:
        """保存单条数据。

        Args:
            data: 数据字典
        """
        mapped = self._apply_mapping(data)

        # 更新字段列表
        for key in mapped.keys():
            if key not in self._fieldnames:
                self._fieldnames.append(key)

        # 延迟打开文件
        if self._file is None:
            self._open_file()

        if self._writer:
            self._writer.writerow(mapped)
            self._file.flush()
            self._count += 1

    def save_many(self, data_list: List[Dict[str, Any]]) -> None:
        """批量保存数据。

        Args:
            data_list: 数据字典列表
        """
        for data in data_list:
            self.save(data)

    def _open_file(self) -> None:
        """打开CSV文件并创建写入器。"""
        try:
            self._file = open(self._filepath, "w", newline="", encoding=self.encoding)
            self._writer = csv.DictWriter(
                self._file,
                fieldnames=self._fieldnames,
                delimiter=self.delimiter,
                extrasaction="ignore",
            )
            self._writer.writeheader()
        except Exception as e:
            raise StorageError(f"CSV文件打开失败: {e}", path=self._filepath)

    def close(self) -> None:
        """关闭存储。"""
        if self._file:
            try:
                self._file.close()
                logger.info(
                    f"CSV数据已保存: {self._filepath} ({self._count} 条)"
                )
            except Exception as e:
                logger.error(f"CSV文件关闭失败: {e}")
            finally:
                self._file = None
                self._writer = None

    def get_fieldnames(self) -> List[str]:
        """获取CSV列名。

        Returns:
            列名列表
        """
        return list(self._fieldnames)


# ============================================================
# SQLiteStorage - SQLite数据库存储
# ============================================================

class SQLiteStorage(StorageBackend):
    """SQLite数据库存储后端。

    将数据保存到SQLite数据库中，支持增量写入和自定义表结构。

    注意：需要Python内置的sqlite3模块（Python标准库自带）。

    Attributes:
        output_dir: 输出目录
        filename: 数据库文件名
        table_name: 表名

    Examples:
        >>> storage = SQLiteStorage(output_dir="./data", filename="results.db")
        >>> storage.save({"url": "https://example.com", "title": "Example"})
        >>> storage.save({"url": "https://example.org", "title": "Example Org"})
        >>> storage.close()
    """

    def __init__(
        self,
        output_dir: str = "./output",
        filename: str = "results.db",
        table_name: str = "crawl_data",
        field_mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        """初始化SQLite存储。

        Args:
            output_dir: 输出目录
            filename: 数据库文件名
            table_name: 表名
            field_mapping: 字段映射
        """
        super().__init__(output_dir, field_mapping)
        self.filename = filename
        self.table_name = table_name
        self._db_path = os.path.join(output_dir, filename)
        self._conn: Optional[Any] = None
        self._cursor: Optional[Any] = None
        self._existing_columns: set = set()
        self._table_created = False

        self._open_connection()

    def _open_connection(self) -> None:
        """打开数据库连接。"""
        try:
            import sqlite3
            self._conn = sqlite3.connect(self._db_path)
            self._cursor = self._conn.cursor()
            logger.debug(f"SQLite数据库已连接: {self._db_path}")
        except Exception as e:
            raise StorageError(f"SQLite连接失败: {e}", path=self._db_path)

    def _ensure_table(self, data: Dict[str, Any]) -> None:
        """确保表存在，必要时添加新列。

        Args:
            data: 数据字典（用于推断列）
        """
        if self._table_created:
            # 检查是否需要添加新列
            for key in data.keys():
                if key not in self._existing_columns:
                    self._add_column(key)
            return

        try:
            # 创建表
            columns = []
            for key in data.keys():
                col_type = self._infer_type(data[key])
                columns.append(f'"{key}" {col_type}')
                self._existing_columns.add(key)

            create_sql = (
                f'CREATE TABLE IF NOT EXISTS "{self.table_name}" '
                f'({", ".join(columns)})'
            )
            self._cursor.execute(create_sql)
            self._conn.commit()
            self._table_created = True
        except Exception as e:
            raise StorageError(f"表创建失败: {e}", path=self._db_path)

    def _add_column(self, column_name: str) -> None:
        """向表中添加新列。

        Args:
            column_name: 列名
        """
        if column_name in self._existing_columns:
            return

        try:
            # SQLite的ALTER TABLE添加列需要默认值
            alter_sql = (
                f'ALTER TABLE "{self.table_name}" '
                f'ADD COLUMN "{column_name}" TEXT DEFAULT ""'
            )
            self._cursor.execute(alter_sql)
            self._conn.commit()
            self._existing_columns.add(column_name)
        except Exception as e:
            logger.debug(f"添加列失败（可能已存在）: {column_name} - {e}")

    @staticmethod
    def _infer_type(value: Any) -> str:
        """推断值的SQL类型。

        Args:
            value: Python值

        Returns:
            SQL类型字符串
        """
        if isinstance(value, int):
            return "INTEGER"
        elif isinstance(value, float):
            return "REAL"
        elif isinstance(value, bool):
            return "INTEGER"
        return "TEXT"

    def save(self, data: Dict[str, Any]) -> None:
        """保存单条数据。

        Args:
            data: 数据字典
        """
        mapped = self._apply_mapping(data)

        self._ensure_table(mapped)

        # 构建INSERT语句
        columns = list(mapped.keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join([f'"{c}"' for c in columns])
        values = [
            str(v) if not isinstance(v, (int, float, type(None))) else v
            for v in mapped.values()
        ]

        try:
            insert_sql = (
                f'INSERT INTO "{self.table_name}" ({col_names}) '
                f'VALUES ({placeholders})'
            )
            self._cursor.execute(insert_sql, values)
            self._conn.commit()
            self._count += 1
        except Exception as e:
            logger.error(f"SQLite插入失败: {e}")
            # 尝试添加缺失的列后重试
            for col in columns:
                if col not in self._existing_columns:
                    self._add_column(col)
            try:
                self._cursor.execute(insert_sql, values)
                self._conn.commit()
                self._count += 1
            except Exception as e2:
                logger.error(f"SQLite重试插入失败: {e2}")

    def save_many(self, data_list: List[Dict[str, Any]]) -> None:
        """批量保存数据。

        Args:
            data_list: 数据字典列表
        """
        for data in data_list:
            self.save(data)

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """执行自定义查询。

        Args:
            query: SQL查询语句

        Returns:
            查询结果列表（字典形式）
        """
        if not self._cursor:
            raise StorageError("数据库未连接")

        try:
            self._cursor.execute(query)
            columns = [desc[0] for desc in self._cursor.description]
            results = []
            for row in self._cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            raise StorageError(f"查询执行失败: {e}")

    def close(self) -> None:
        """关闭存储。"""
        if self._conn:
            try:
                self._conn.close()
                logger.info(
                    f"SQLite数据已保存: {self._db_path} ({self._count} 条)"
                )
            except Exception as e:
                logger.error(f"SQLite关闭失败: {e}")
            finally:
                self._conn = None
                self._cursor = None

    @property
    def row_count(self) -> int:
        """获取表中的总行数。"""
        if not self._cursor or not self._table_created:
            return 0
        try:
            self._cursor.execute(
                f'SELECT COUNT(*) FROM "{self.table_name}"'
            )
            return self._cursor.fetchone()[0]
        except Exception:
            return 0
