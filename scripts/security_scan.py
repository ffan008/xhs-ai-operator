#!/usr/bin/env python3
"""
安全扫描脚本 - 检测代码中的敏感信息

扫描代码库中的:
- 硬编码的 API 密钥
- 密码和令牌
- 敏感配置信息
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple
from datetime import datetime


class SecurityScanner:
    """安全扫描器"""

    # 敏感信息模式
    PATTERNS = [
        # API 密钥
        (r'STABILITY_API_KEY\s*=\s*["\']sk-[a-zA-Z0-9]{40,}["\']', "Stability AI API Key"),
        (r'OPENAI_API_KEY\s*=\s*["\']sk-[a-zA-Z0-9]{40,}["\']', "OpenAI API Key"),
        (r'REPLICATE_API_TOKEN\s*=\s*["\']r8_[a-zA-Z0-9]{40,}["\']', "Replicate API Token"),
        (r'HUGGINGFACE_API_KEY\s*=\s*["\']hf_[a-zA-Z0-9]{30,}["\']', "Hugging Face API Key"),

        # 通用密钥模式
        (r'api[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9+/=_]{20,}["\']', "API Key"),
        (r'token["\']?\s*[:=]\s*["\'][a-zA-Z0-9+/=_]{20,}["\']', "Auth Token"),
        (r'secret["\']?\s*[:=]\s*["\'][a-zA-Z0-9+/=_]{20,}["\']', "Secret"),
        (r'password["\']?\s*[:=]\s*["\'][^"\']{8,}["\']', "Password"),

        # URL 中的密钥
        (r'https?://[^\s]*api[a-zA-Z0-9]*[-.][^\s]*sk-[a-zA-Z0-9]+', "URL with API Key"),
        (r'Bearer\s+[a-zA-Z0-9+/=_]{20,}', "Bearer Token"),

        # IP 地址 (可能是内网地址)
        (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', "IP Address"),
    ]

    # 忽略的文件和目录
    IGNORE_PATTERNS = [
        "venv/",
        "ENV/",
        "env/",
        ".git/",
        "__pycache__/",
        "node_modules/",
        "*.egg-info/",
        "*.pyc",
        ".env.example",
        ".env.template",
        "SECURITY_SETUP.md",
        "OPTIMIZATION_PLAN.md",
    ]

    def __init__(self, base_dir: Path):
        """
        初始化扫描器

        Args:
            base_dir: 要扫描的根目录
        """
        self.base_dir = base_dir
        self.issues = []

    def scan(self) -> List[Tuple[str, int, str]]:
        """
        扫描代码库

        Returns:
            发现的问题列表 [(文件, 行号, 描述)]
        """
        print(f"🔍 扫描目录: {self.base_dir}")

        # 收集要扫描的文件
        files = self._collect_files()

        print(f"📄 找到 {len(files)} 个文件，开始扫描...\n")

        # 扫描每个文件
        for file_path in files:
            self._scan_file(file_path)

        return self.issues

    def _collect_files(self) -> List[Path]:
        """收集要扫描的文件"""
        files = []

        # 要扫描的文件扩展名
        extensions = [
            '.py', '.json', '.yaml', '.yml', '.md',
            '.txt', '.sh', '.env*', '.conf'
        ]

        for ext in extensions:
            files.extend(self.base_dir.rglob(f"*{ext}"))

        # 过滤忽略的文件
        filtered_files = []
        for file_path in files:
            if self._should_ignore(file_path):
                continue
            filtered_files.append(file_path)

        return filtered_files

    def _should_ignore(self, file_path: Path) -> bool:
        """检查文件是否应该被忽略"""
        # 检查忽略模式
        for pattern in self.IGNORE_PATTERNS:
            if pattern in str(file_path):
                return True

        # 检查是否是符号链接
        if file_path.is_symlink():
            return True

        return False

    def _scan_file(self, file_path: Path) -> None:
        """扫描单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    self._scan_line(file_path, line_num, line)
        except Exception as e:
            # 如果无法解码，尝试忽略错误
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    for line_num, line in enumerate(f, 1):
                        self._scan_line(file_path, line_num, line)
            except:
                pass

    def _scan_line(self, file_path: Path, line_num: int, line: str) -> None:
        """扫描单行"""
        for pattern, description in self.PATTERNS:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                # 只报告文件在 src/ 或 scripts/ 或配置文件中的问题
                if self._is_source_file(file_path):
                    self.issues.append((
                        str(file_path.relative_to(self.base_dir)),
                        line_num,
                        f"{description}: {match.group()[:50]}..."
                    ))

    def _is_source_file(self, file_path: Path) -> bool:
        """检查是否是源代码或配置文件"""
        # 检查是否在关键目录中
        critical_dirs = [
            "src/", "scripts/", "xhs-operator/",
            "integration-mcp/", "scheduler-mcp/",
            "analytics-mcp/"
        ]

        for dir_name in critical_dirs:
            if dir_name in str(file_path):
                return True

        # 检查文件扩展名
        if file_path.suffix in ['.py', '.json', '.yaml', '.yml', '.sh']:
            return True

        return False

    def generate_report(self) -> str:
        """生成扫描报告"""
        if not self.issues:
            return "✅ 未发现安全问题"

        report = []
        report.append(f"⚠️  发现 {len(self.issues)} 个潜在安全问题:\n")

        # 按文件分组
        by_file = {}
        for file_path, line_num, description in self.issues:
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append((line_num, description))

        # 生成报告
        for file_path, issues in sorted(by_file.items()):
            report.append(f"\n📁 {file_path}")
            for line_num, description in issues:
                report.append(f"   行 {line_num}: {description}")

        return "\n".join(report)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="安全扫描脚本")
    parser.add_argument("--dir", type=Path, default=Path.cwd(), help="扫描目录")
    parser.add_argument("--fix", action="store_true", help="自动修复（TODO）")
    parser.add_argument("--output", type=Path, help="输出报告到文件")

    args = parser.parse_args()

    # 执行扫描
    scanner = SecurityScanner(args.dir)
    issues = scanner.scan()

    # 生成报告
    report = scanner.generate_report()

    # 输出报告
    print(report)

    # 保存到文件
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report)
        print(f"\n📄 报告已保存到: {args.output}")

    # 返回退出码
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
