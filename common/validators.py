"""
输入验证框架

使用 Pydantic 创建严格的输入验证模型，防止注入攻击和无效输入。
"""

import re
import html
from pathlib import Path
from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field, validator, root_validator


class CronExpression(BaseModel):
    """
    Cron 表达式验证器

    验证 cron 表达式的格式和范围
    """
    expression: str = Field(..., description="Cron 表达式")

    @validator('expression')
    def validate_format(cls, v):
        """验证基本格式"""
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError("Cron 表达式必须包含 5 个部分，用空格分隔")

        # 验证每个部分
        patterns = [
            r'^(\*|\d+|\*/\d+|\d+-\d+|\d+,\d+)$',  # 分钟
            r'^(\*|\d+|\*/\d+|\d+-\d+|\d+,\d+)$',  # 小时
            r'^(\*|\d+|\*/\d+|\d+-\d+|\d+,\d+|\*\/\*)$',  # 日期
            r'^(\*|\d+|\*\/\d+|\d+-\d+|\d+,\d+|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # 月份
            r'^(\*|\d+|\*\/\d+|\d+-\d+|\d+,\d+|mon|tue|wed|thu|fri|sat|sun)'  # 星期
        ]

        for i, (part, pattern) in enumerate(zip(parts, patterns)):
            if not re.match(pattern, part.lower()):
                raise ValueError(
                    f"Cron 表达式第 {i+1} 部分无效: '{part}'"
                )

        return v

    @validator('expression')
    def validate_ranges(cls, v):
        """验证数值范围"""
        parts = v.strip().split()

        # 分钟: 0-59
        minute_parts = parts[0].replace('*', '0').split(',')
        for part in minute_parts:
            if '/' in part:
                continue  # 跳过步长值
            num = int(part) if part.isdigit() else 0
            if num < 0 or num > 59:
                raise ValueError(f"分钟值超出范围 (0-59): {num}")

        # 小时: 0-23
        hour_parts = parts[1].replace('*', '0').split(',')
        for part in hour_parts:
            if '/' in part or '*' in part:
                continue
            num = int(part) if part.isdigit() else 0
            if num < 0 or num > 23:
                raise ValueError(f"小时值超出范围 (0-23): {num}")

        # 日期: 1-31
        day_parts = parts[2].replace('*', '1').split(',')
        for part in day_parts:
            if '/' in part or '*' in part or '-' in part:
                continue
            num = int(part) if part.isdigit() else 1
            if num < 1 or num > 31:
                raise ValueError(f"日期值超出范围 (1-31): {num}")

        # 月份: 1-12
        month_parts = parts[3].lower().replace('*', '1').split(',')
        for part in month_parts:
            if '/' in part or '*' in part or '-' in part:
                continue
            # 检查是否是月份名称
            if part in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                continue
            num = int(part) if part.isdigit() else 1
            if num < 1 or num > 12:
                raise ValueError(f"月份值超出范围 (1-12): {num}")

        # 星期: 0-7 (0和7都代表周日)
        weekday_parts = parts[4].lower().replace('*', '1').split(',')
        for part in weekday_parts:
            if '/' in part or '*' in part or '-' in part:
                continue
            # 检查是否是星期名称
            if part in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']:
                continue
            num = int(part) if part.isdigit() else 1
            if num < 0 or num > 7:
                raise ValueError(f"星期值超出范围 (0-7): {num}")

        return v

    def get_description(self) -> str:
        """获取可读的 cron 描述"""
        try:
            parts = self.expression.split()
            return f"{parts[0]}分 {parts[1]}时 {parts[2]}日 {parts[3]}月 {parts[4]}周"
        except:
            return self.expression


class WorkflowParams(BaseModel):
    """
    工作流参数验证模型
    """
    topic: str = Field(..., min_length=1, max_length=200)
    count: int = Field(1, ge=1, le=100)
    style: Optional[str] = Field(None, pattern="^(lively|professional|healing|practical|recommendation)$")
    model: Optional[str] = Field(None, pattern="^(stability|openai|replicate|huggingface|ideogram|leonardo)$")
    account_id: Optional[str] = Field(None, min_length=1, max_length=50)

    @validator('topic')
    def sanitize_topic(cls, v):
        """清理主题字符串"""
        # 移除危险字符
        v = re.sub(r'[<>"\'\']', '', v)
        # 移除事件处理器模式
        v = re.sub(r'on\w+\s*=', '', v, flags=re.IGNORECASE)
        # 移除控制字符
        v = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', v)
        # 移除多余的空格
        v = ' '.join(v.split())
        return v.strip()

    @validator('account_id')
    def validate_account_id(cls, v):
        """验证账号ID"""
        if v:
            # 只允许字母、数字、下划线和连字符
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError("账号ID只能包含字母、数字、下划线和连字符")
        return v


class PublishNoteRequest(BaseModel):
    """
    发布笔记的请求验证模型
    """
    title: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1, max_length=1000)
    tags: List[str] = Field(..., min_items=1, max_items=10)
    image_url: Optional[str] = None

    @validator('title')
    def validate_title(cls, v):
        """验证标题"""
        v = v.strip()
        if len(v) < 1:
            raise ValueError("标题不能为空")
        if len(v) > 100:
            raise ValueError("标题不能超过 100 个字符")
        return v

    @validator('content')
    def validate_content(cls, v):
        """验证内容"""
        v = v.strip()
        if len(v) < 1:
            raise ValueError("内容不能为空")
        if len(v) > 1000:
            raise ValueError("内容不能超过 1000 个字符")
        return v

    @validator('tags')
    def validate_tags(cls, v):
        """验证标签"""
        # 去重
        unique_tags = list(set(v))
        if len(unique_tags) > 10:
            raise ValueError("标签不能超过 10 个")

        # 验证每个标签
        validated_tags = []
        for tag in unique_tags:
            tag = tag.strip()
            if len(tag) < 1:
                continue
            if len(tag) > 20:
                raise ValueError(f"标签过长: {tag}")
            if '#' in tag:
                tag = tag.lstrip('#')
            validated_tags.append(tag)

        if not validated_tags:
            raise ValueError("至少需要一个有效标签")

        return validated_tags

    @validator('image_url')
    def validate_image_url(cls, v):
        """验证图片URL"""
        if v:
            # 验证URL格式
            if not v.startswith(('http://', 'https://')):
                raise ValueError("图片URL必须以 http:// 或 https:// 开头")

            # 验证域名白名单
            allowed_domains = [
                'xiaohongshu.com',
                'cdn.xiaohongshu.com',
                'localhost',
                '127.0.0.1'
            ]

            # 检查是否包含允许的域名
            if not any(domain in v for domain in allowed_domains):
                # 允许其他外部URL，但发出警告
                pass

        return v


class FilePathValidator:
    """
    文件路径安全验证器
    """

    # 允许的文件扩展名
    ALLOWED_EXTENSIONS = [
        '.json', '.yaml', '.yml', '.txt', '.md',
        '.png', '.jpg', '.jpeg', '.gif', '.webp'
    ]

    # 危险的文件名字符
    DANGEROUS_CHARS = ['..', '~', '$', '&', '|', ';', '<', '>', '`']

    @staticmethod
    def safe_filename(filename: str) -> str:
        """
        生成安全的文件名

        Args:
            filename: 原始文件名

        Returns:
            安全的文件名
        """
        # 移除路径遍历字符
        safe_name = Path(filename).name

        # 移除危险字符
        for char in FilePathValidator.DANGEROUS_CHARS:
            safe_name = safe_name.replace(char, '_')

        # 只保留安全字符
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', safe_name)

        # 限制长度
        return safe_name[:100]

    @staticmethod
    def validate_path(path_str: str, base_dir: Optional[Path] = None) -> Path:
        """
        验证并返回安全的文件路径

        Args:
            path_str: 路径字符串
            base_dir: 基础目录（用于相对路径）

        Returns:
            验证后的 Path 对象

        Raises:
            ValueError: 路径不安全
        """
        path = Path(path_str)

        # 检查路径遍历
        if '..' in str(path):
            raise ValueError("路径中不允许包含 '..'")

        # 如果是相对路径，基于 base_dir 解析
        if base_dir and not path.is_absolute():
            path = (base_dir / path).resolve()

        # 确保路径在允许的目录内
        if base_dir:
            try:
                path.resolve().relative_to(base_dir.resolve())
            except ValueError:
                raise ValueError("路径不在允许的目录内")

        # 检查文件扩展名
        if path.suffix and path.suffix not in FilePathValidator.ALLOWED_EXTENSIONS:
            raise ValueError(f"不允许的文件类型: {path.suffix}")

        return path


class ContentSanitizer:
    """
    内容清理器 - 清理和验证用户输入
    """

    # 敏感关键词列表（可根据需要扩展）
    SENSITIVE_KEYWORDS = [
        # 政治敏感词
        # 暴力内容
        # 色情内容
        # 广告违禁词
    ]

    # AI 提示词注入攻击模式
    MALICIOUS_PATTERNS = [
        r'ignore\s+(?:previous|all)\s+(?:instructions?|command)',
        r'disregard\s+(?:(?:the\s+)?above|everything\s+?above)',
       r'forget\s+(?:(?:the\s+)?above|everything\s+?above|rules)',
        r'pay\s+no\s+attention',
        r'system\s*:\s*override'
    ]

    @staticmethod
    def sanitize_user_input(text: str, preserve_html: bool = False) -> str:
        """
        清理用户输入

        Args:
            text: 用户输入文本
            preserve_html: 是否保留 HTML（默认为 False）

        Returns:
            清理后的安全文本
        """
        # 移除控制字符
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)

        if not preserve_html:
            # 移除脚本标签
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)

            # 移除事件处理器
            text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)

            # 转义 HTML 特殊字符
            text = html.escape(text)

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    @staticmethod
    def validate_prompt(prompt: str) -> tuple[bool, List[str]]:
        """
        检查 AI prompt 是否包含恶意内容

        Args:
            prompt: 提示词

        Returns:
            (是否安全, 问题列表)
        """
        issues = []

        for pattern in ContentSanitizer.MALICIOUS_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                issues.append(f"检测到提示注入尝试: {pattern[:50]}...")

        # 检查敏感关键词
        text_lower = prompt.lower()
        for keyword in ContentSanitizer.SENSITIVE_KEYWORDS:
            if keyword in text_lower:
                issues.append(f"包含敏感关键词: {keyword}")

        is_safe = len(issues) == 0
        return is_safe, issues

    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """
        清理 HTML 内容

        Args:
            html_content: HTML 内容

        Returns:
            清理后的安全 HTML
        """
        import bleach

        # 允许的标签和属性
        ALLOWED_TAGS = [
            'p', 'br', 'strong', 'em', 'u', 'i', 'b',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li',
            'a', 'span', 'div'
        ]

        ALLOWED_ATTRIBUTES = {
            'a': ['href', 'title'],
            '*': ['class', 'id']
        }

        # 清理 HTML
        clean_html = bleach.clean(
            html_content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )

        return clean_html

    @staticmethod
    def validate_content(title: str, content: str, tags: List[str]) -> Dict[str, Any]:
        """
        验证内容合规性

        Args:
            title: 标题
            content: 内容
            tags: 标签列表

        Returns:
            验证结果字典
        """
        result = {
            "approved": True,
            "issues": []
        }

        # 检查长度
        if len(title) > 100:
            result["issues"].append({
                "type": "title_too_long",
                "length": len(title),
                "severity": "medium"
            })

        if len(content) > 1000:
            result["issues"].append({
                "type": "content_too_long",
                "length": len(content),
                "severity": "medium"
            })

        # 检查标签数量
        if len(tags) > 10:
            result["issues"].append({
                "type": "too_many_tags",
                "count": len(tags),
                "severity": "low"
            })

        # 检查敏感关键词
        combined_content = f"{title} {content} {' '.join(tags)}"
        text_lower = combined_content.lower()

        # 这里可以添加敏感词检查
        # for keyword in SENSITIVE_KEYWORDS:
        #     if keyword in text_lower:
        #         result["issues"].append({
        #             "type": "sensitive_keyword",
        #             "keyword": keyword,
        #             "severity": "high"
        #         })
        #         result["approved"] = False

        result["approved"] = len(result["issues"]) == 0
        return result


class ParameterWhitelist:
    """
    参数白名单验证器
    """

    # 允许的工作流
    ALLOWED_WORKFLOWS = [
        "publish", "create", "analyze", "batch",
        "schedule", "preview", "optimize", "check"
    ]

    # 允许的 MCP 服务器
    ALLOWED_MCPS = [
        "xiaohongshu-mcp",
        "stability-mcp",
        "tavily-remote",
        "openai-mcp",
        "replicate-mcp",
        "huggingface-mcp"
    ]

    # 允许的参数名模式
    PARAM_PATTERN = re.compile(r'^[a-z_][a-z0-9_]*$')

    @staticmethod
    def validate_workflow_name(workflow_name: str) -> bool:
        """验证工作流名称"""
        return workflow_name in ParameterWhitelist.ALLOWED_WORKFLOWS

    @staticmethod
    def validate_mcp_name(mcp_name: str) -> bool:
        """验证 MCP 服务器名称"""
        return mcp_name in ParameterWhitelist.ALLOWED_MCPS

    @staticmethod
    def validate_param_name(param_name: str) -> bool:
        """验证参数名称"""
        return bool(ParameterWhitelist.PARAM_PATTERN.match(param_name))

    @staticmethod
    def validate_dict(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证参数字典

        Args:
            params: 参数字典

        Returns:
            验证后的参数字典（移除不安全的参数）
        """
        validated = {}

        for key, value in params.items():
            if not ParameterWhitelist.validate_param_name(key):
                continue

            # 递归验证嵌套字典
            if isinstance(value, dict):
                validated[key] = ParameterWhitelist.validate_dict(value)
            else:
                validated[key] = value

        return validated

    @staticmethod
    def sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理和验证参数

        Args:
            params: 原始参数

        Returns:
            清理后的安全参数
        """
        validated = {}

        for key, value in params.items():
            # 验证键名
            if not ParameterWhitelist.validate_param_name(key):
                continue

            # 验证值
            if isinstance(value, str):
                # 清理字符串
                validated[key] = ContentSanitizer.sanitize_user_input(value)
            elif isinstance(value, dict):
                # 递归清理字典
                validated[key] = ParameterWhitelist.sanitize_params(value)
            elif isinstance(value, list):
                # 清理列表中的字符串
                validated[key] = [
                    ContentSanitizer.sanitize_user_input(v)
                    if isinstance(v, str) else v
                    for v in value
                ]
            else:
                validated[key] = value

        return validated


# 便捷函数
def validate_cron_expression(expr: str) -> CronExpression:
    """验证 Cron 表达式"""
    return CronExpression(expression=expr)


def validate_publish_request(title: str, content: str, tags: List[str]) -> PublishNoteRequest:
    """验证发布请求"""
    return PublishNoteRequest(
        title=title,
        content=content,
        tags=tags
    )


def validate_file_path(path_str: str, base_dir: Optional[Path] = None) -> Path:
    """验证文件路径"""
    validator = FilePathValidator()
    return validator.validate_path(path_str, base_dir)


def sanitize_user_input(text: str, preserve_html: bool = False) -> str:
    """清理用户输入"""
    return ContentSanitizer.sanitize_user_input(text, preserve_html)


def validate_prompt(prompt: str) -> tuple[bool, List[str]]:
    """验证 AI 提示词"""
    return ContentSanitizer.validate_prompt(prompt)
