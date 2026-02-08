"""
内容预览模块

提供发布前预览、图片生成预览、分步确认等功能。
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    io = None

from .exceptions import BusinessError


# ============================================================================
# 预览状态
# ============================================================================

class PreviewStatus(str, Enum):
    """预览状态"""
    DRAFT = "draft"           # 草稿
    GENERATING = "generating" # 生成中
    READY = "ready"           # 就绪
    APPROVED = "approved"     # 已确认
    REJECTED = "rejected"     # 已拒绝
    PUBLISHED = "published"   # 已发布


# ============================================================================
# 图片生成状态
# ============================================================================

class ImageStatus(str, Enum):
    """图片状态"""
    PENDING = "pending"       # 等待生成
    GENERATING = "generating" # 生成中
    SUCCESS = "success"       # 成功
    FAILED = "failed"         # 失败


# ============================================================================
# 内容草稿
# ============================================================================

@dataclass
class ContentDraft:
    """内容草稿"""
    id: str
    title: str
    content: str
    tags: List[str]
    image_prompts: List[str]
    images: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: PreviewStatus = PreviewStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "image_prompts": self.image_prompts,
            "images": self.images,
            "metadata": self.metadata,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentDraft":
        """从字典创建"""
        data["status"] = PreviewStatus(data.get("status", "draft"))
        return cls(**data)


# ============================================================================
# 图片生成结果
# ============================================================================

@dataclass
class ImageGenerationResult:
    """图片生成结果"""
    id: str
    prompt: str
    status: ImageStatus
    image_url: Optional[str] = None
    image_data: Optional[bytes] = None
    error: Optional[str] = None
    generation_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "prompt": self.prompt,
            "status": self.status.value,
            "image_url": self.image_url,
            "error": self.error,
            "generation_time": self.generation_time,
            "metadata": self.metadata
        }


# ============================================================================
# 预览会话
# ============================================================================

class PreviewSession:
    """预览会话"""

    def __init__(self, draft: ContentDraft):
        """
        初始化预览会话

        Args:
            draft: 内容草稿
        """
        self.draft = draft
        self._current_step = 0
        self._history: List[Dict[str, Any]] = []
        self._approved = False

    @property
    def current_step(self) -> int:
        """当前步骤"""
        return self._current_step

    def next_step(self) -> None:
        """下一步"""
        self._current_step += 1

    def previous_step(self) -> None:
        """上一步"""
        if self._current_step > 0:
            self._current_step -= 1

    def add_history(self, action: str, data: Dict[str, Any]) -> None:
        """添加历史记录"""
        self._history.append({
            "step": self._current_step,
            "action": action,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

    def approve(self) -> None:
        """批准预览"""
        self._approved = True
        self.draft.status = PreviewStatus.APPROVED

    def reject(self) -> None:
        """拒绝预览"""
        self._approved = False
        self.draft.status = PreviewStatus.REJECTED

    def is_approved(self) -> bool:
        """是否已批准"""
        return self._approved

    def get_history(self) -> List[Dict[str, Any]]:
        """获取历史记录"""
        return self._history.copy()


# ============================================================================
# 内容预览器
# ============================================================================

class ContentPreviewer:
    """内容预览器"""

    def __init__(
        self,
        image_generator: Optional[Callable] = None,
        max_retries: int = 3
    ):
        """
        初始化内容预览器

        Args:
            image_generator: 图片生成函数
            max_retries: 最大重试次数
        """
        self.image_generator = image_generator
        self.max_retries = max_retries

        # 统计信息
        self._stats = {
            "total_previews": 0,
            "approved_previews": 0,
            "rejected_previews": 0,
            "modifications": 0,
            "image_regenerations": 0
        }

    def create_draft(
        self,
        title: str,
        content: str,
        tags: List[str],
        image_prompts: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContentDraft:
        """
        创建内容草稿

        Args:
            title: 标题
            content: 正文内容
            tags: 标签列表
            image_prompts: 图片提示词列表
            metadata: 元数据

        Returns:
            内容草稿
        """
        draft = ContentDraft(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            tags=tags,
            image_prompts=image_prompts,
            metadata=metadata or {}
        )

        self._stats["total_previews"] += 1
        return draft

    def preview_text(
        self,
        draft: ContentDraft,
        format_type: str = "markdown"
    ) -> str:
        """
        预览文本内容

        Args:
            draft: 内容草稿
            format_type: 格式类型（markdown, plain, html）

        Returns:
            格式化的预览文本
        """
        if format_type == "markdown":
            return self._format_markdown(draft)
        elif format_type == "plain":
            return self._format_plain(draft)
        elif format_type == "html":
            return self._format_html(draft)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    def _format_markdown(self, draft: ContentDraft) -> str:
        """格式化为 Markdown"""
        lines = []
        lines.append(f"# {draft.title}")
        lines.append("")
        lines.append(draft.content)
        lines.append("")
        if draft.tags:
            lines.append("**标签:** " + " ".join(f"#{tag}" for tag in draft.tags))
        lines.append("")
        lines.append(f"*草稿 ID: {draft.id}*")
        lines.append(f"*创建时间: {draft.created_at}*")
        return "\n".join(lines)

    def _format_plain(self, draft: ContentDraft) -> str:
        """格式化为纯文本"""
        lines = []
        lines.append(f"标题: {draft.title}")
        lines.append("")
        lines.append(draft.content)
        lines.append("")
        if draft.tags:
            lines.append(f"标签: {', '.join(draft.tags)}")
        lines.append("")
        lines.append(f"草稿 ID: {draft.id}")
        lines.append(f"创建时间: {draft.created_at}")
        return "\n".join(lines)

    def _format_html(self, draft: ContentDraft) -> str:
        """格式化为 HTML"""
        lines = []
        lines.append("<div class='content-preview'>")
        lines.append(f"  <h1>{self._escape_html(draft.title)}</h1>")
        lines.append("  <div class='content'>")
        lines.append(f"    {self._escape_html(draft.content).replace(chr(10), '<br>')}")
        lines.append("  </div>")
        if draft.tags:
            tags_html = " ".join(f"<span class='tag'>#{tag}</span>" for tag in draft.tags)
            lines.append(f"  <div class='tags'>{tags_html}</div>")
        lines.append(f"  <div class='meta'>草稿 ID: {draft.id} | 创建时间: {draft.created_at}</div>")
        lines.append("</div>")
        return "\n".join(lines)

    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))

    async def generate_images(
        self,
        draft: ContentDraft,
        regenerate_indices: Optional[List[int]] = None
    ) -> List[ImageGenerationResult]:
        """
        生成预览图片

        Args:
            draft: 内容草稿
            regenerate_indices: 需要重新生成的图片索引

        Returns:
            图片生成结果列表
        """
        if not self.image_generator:
            raise BusinessError(
                message="Image generator not configured",
                user_message="图片生成功能未配置"
            )

        results = []

        # 确定需要生成的图片
        if regenerate_indices is not None:
            # 只重新生成指定的图片
            prompts_to_generate = [
                (i, draft.image_prompts[i])
                for i in regenerate_indices
                if 0 <= i < len(draft.image_prompts)
            ]
        else:
            # 生成所有图片
            prompts_to_generate = list(enumerate(draft.image_prompts))

        # 生成图片
        for index, prompt in prompts_to_generate:
            result = await self._generate_single_image(prompt, index)
            results.append(result)

            # 如果失败且可以重试，则重试
            if result.status == ImageStatus.FAILED:
                for retry in range(self.max_retries):
                    result = await self._generate_single_image(prompt, index)
                    if result.status == ImageStatus.SUCCESS:
                        break

        # 更新草稿中的图片列表
        self._update_draft_images(draft, results, regenerate_indices)

        # 更新统计
        self._stats["image_regenerations"] += len(results)

        return results

    async def _generate_single_image(
        self,
        prompt: str,
        index: int
    ) -> ImageGenerationResult:
        """
        生成单张图片

        Args:
            prompt: 图片提示词
            index: 图片索引

        Returns:
            图片生成结果
        """
        result = ImageGenerationResult(
            id=str(uuid.uuid4()),
            prompt=prompt,
            status=ImageStatus.GENERATING
        )

        try:
            start_time = asyncio.get_event_loop().time()

            # 调用图片生成器
            image_data = await self.image_generator(prompt)

            # 记录生成时间
            result.generation_time = asyncio.get_event_loop().time() - start_time

            # 更新结果
            if isinstance(image_data, dict):
                result.image_url = image_data.get("url")
                result.image_data = image_data.get("data")
                result.metadata = image_data.get("metadata", {})
            elif isinstance(image_data, (bytes, str)):
                result.image_data = image_data if isinstance(image_data, bytes) else image_data.encode()
                result.image_url = f"data:image/png;base64,{image_data}"

            result.status = ImageStatus.SUCCESS

        except Exception as e:
            result.status = ImageStatus.FAILED
            result.error = str(e)

        return result

    def _update_draft_images(
        self,
        draft: ContentDraft,
        results: List[ImageGenerationResult],
        regenerate_indices: Optional[List[int]] = None
    ) -> None:
        """
        更新草稿中的图片列表

        Args:
            draft: 内容草稿
            results: 图片生成结果
            regenerate_indices: 重新生成的图片索引
        """
        if regenerate_indices is None:
            # 全部更新
            draft.images = [r.to_dict() for r in results]
        else:
            # 部分更新
            for i, result in zip(regenerate_indices, results):
                if 0 <= i < len(draft.images):
                    draft.images[i] = result.to_dict()
                else:
                    draft.images.append(result.to_dict())

        draft.updated_at = datetime.now().isoformat()

    def modify_content(
        self,
        draft: ContentDraft,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        append_tags: Optional[List[str]] = None
    ) -> ContentDraft:
        """
        修改内容

        Args:
            draft: 内容草稿
            title: 新标题（如果提供）
            content: 新内容（如果提供）
            tags: 新标签列表（如果提供，会替换原有标签）
            append_tags: 要追加的标签（如果提供）

        Returns:
            修改后的草稿
        """
        if title is not None:
            draft.title = title

        if content is not None:
            draft.content = content

        if tags is not None:
            draft.tags = tags

        if append_tags is not None:
            draft.tags = list(set(draft.tags + append_tags))

        draft.updated_at = datetime.now().isoformat()
        draft.status = PreviewStatus.DRAFT  # 重置为草稿状态

        self._stats["modifications"] += 1

        return draft

    def create_session(self, draft: ContentDraft) -> PreviewSession:
        """
        创建预览会话

        Args:
            draft: 内容草稿

        Returns:
            预览会话
        """
        return PreviewSession(draft)

    def confirm_publish(self, session: PreviewSession) -> bool:
        """
        确认发布

        Args:
            session: 预览会话

        Returns:
            是否确认发布
        """
        if session.is_approved():
            session.draft.status = PreviewStatus.PUBLISHED
            self._stats["approved_previews"] += 1
            return True
        else:
            session.draft.status = PreviewStatus.REJECTED
            self._stats["rejected_previews"] += 1
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._stats.copy()

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            "total_previews": 0,
            "approved_previews": 0,
            "rejected_previews": 0,
            "modifications": 0,
            "image_regenerations": 0
        }


# ============================================================================
# 分步确认流程
# ============================================================================

class StepByStepConfirmation:
    """分步确认流程"""

    def __init__(self, previewer: ContentPreviewer):
        """
        初始化分步确认流程

        Args:
            previewer: 内容预览器
        """
        self.previewer = previewer
        self._steps = [
            self._step_preview_text,
            self._step_preview_images,
            self._step_confirm_tags,
            self._step_final_review
        ]

    async def run(
        self,
        draft: ContentDraft,
        interactive: bool = True
    ) -> PreviewSession:
        """
        运行分步确认流程

        Args:
            draft: 内容草稿
            interactive: 是否交互式

        Returns:
            预览会话
        """
        session = self.previewer.create_session(draft)

        for step_func in self._steps:
            if not interactive:
                # 非交互模式，自动执行
                result = await step_func(session, auto_confirm=True)
            else:
                # 交互模式，等待用户确认
                result = await step_func(session, auto_confirm=False)

            session.add_history(step_func.__name__, {"result": result})

            # 如果拒绝，终止流程
            if result == "reject":
                session.reject()
                return session

            session.next_step()

        # 所有步骤通过，批准发布
        session.approve()
        return session

    async def _step_preview_text(
        self,
        session: PreviewSession,
        auto_confirm: bool = False
    ) -> str:
        """
        步骤 1: 预览文本内容

        Args:
            session: 预览会话
            auto_confirm: 是否自动确认

        Returns:
            用户决定（"approve", "reject", "modify"）
        """
        draft = session.draft

        # 生成预览
        preview = self.previewer.preview_text(draft, format_type="markdown")

        if auto_confirm:
            return "approve"

        # TODO: 在实际实现中，这里应该显示预览并等待用户输入
        # 这里简化为自动批准
        return "approve"

    async def _step_preview_images(
        self,
        session: PreviewSession,
        auto_confirm: bool = False
    ) -> str:
        """
        步骤 2: 预览图片

        Args:
            session: 预览会话
            auto_confirm: 是否自动确认

        Returns:
            用户决定
        """
        draft = session.draft

        # 如果还没有生成图片，先生成
        if not draft.images and draft.image_prompts:
            await self.previewer.generate_images(draft)

        if auto_confirm:
            return "approve"

        # TODO: 显示图片预览并等待用户确认
        return "approve"

    async def _step_confirm_tags(
        self,
        session: PreviewSession,
        auto_confirm: bool = False
    ) -> str:
        """
        步骤 3: 确认标签

        Args:
            session: 预览会话
            auto_confirm: 是否自动确认

        Returns:
            用户决定
        """
        draft = session.draft

        if auto_confirm:
            return "approve"

        # TODO: 显示标签并等待用户确认或修改
        return "approve"

    async def _step_final_review(
        self,
        session: PreviewSession,
        auto_confirm: bool = False
    ) -> str:
        """
        步骤 4: 最终审核

        Args:
            session: 预览会话
            auto_confirm: 是否自动确认

        Returns:
            用户决定
        """
        if auto_confirm:
            return "approve"

        # TODO: 显示最终摘要并等待用户确认
        return "approve"


# ============================================================================
# 便捷函数
# ============================================================================

# 默认预览器
default_previewer = ContentPreviewer()


def create_draft(
    title: str,
    content: str,
    tags: List[str],
    image_prompts: List[str]
) -> ContentDraft:
    """
    创建内容草稿（使用默认预览器）

    Args:
        title: 标题
        content: 正文内容
        tags: 标签列表
        image_prompts: 图片提示词列表

    Returns:
        内容草稿
    """
    return default_previewer.create_draft(title, content, tags, image_prompts)


def preview_text(
    draft: ContentDraft,
    format_type: str = "markdown"
) -> str:
    """
    预览文本内容（使用默认预览器）

    Args:
        draft: 内容草稿
        format_type: 格式类型

    Returns:
        格式化的预览文本
    """
    return default_previewer.preview_text(draft, format_type)


async def generate_images(
    draft: ContentDraft,
    regenerate_indices: Optional[List[int]] = None
) -> List[ImageGenerationResult]:
    """
    生成预览图片（使用默认预览器）

    Args:
        draft: 内容草稿
        regenerate_indices: 需要重新生成的图片索引

    Returns:
        图片生成结果列表
    """
    return await default_previewer.generate_images(draft, regenerate_indices)


def modify_draft(
    draft: ContentDraft,
    **kwargs
) -> ContentDraft:
    """
    修改内容草稿（使用默认预览器）

    Args:
        draft: 内容草稿
        **kwargs: 修改参数

    Returns:
        修改后的草稿
    """
    return default_previewer.modify_content(draft, **kwargs)
