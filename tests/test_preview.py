"""
内容预览模块单元测试
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

# 添加父目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.preview import (
    PreviewStatus,
    ImageStatus,
    ContentDraft,
    ImageGenerationResult,
    PreviewSession,
    ContentPreviewer,
    StepByStepConfirmation
)
from common.exceptions import BusinessError


# ============================================================================
# 内容草稿测试
# ============================================================================

class TestContentDraft:
    """测试内容草稿"""

    def test_create_draft(self):
        """测试创建草稿"""
        draft = ContentDraft(
            id="draft1",
            title="测试标题",
            content="测试内容",
            tags=["标签1", "标签2"],
            image_prompts=["提示词1", "提示词2"]
        )

        assert draft.id == "draft1"
        assert draft.title == "测试标题"
        assert draft.content == "测试内容"
        assert len(draft.tags) == 2
        assert len(draft.image_prompts) == 2
        assert draft.status == PreviewStatus.DRAFT
        print("✅ 创建草稿成功")

    def test_to_dict(self):
        """测试转换为字典"""
        draft = ContentDraft(
            id="draft1",
            title="测试标题",
            content="测试内容",
            tags=["标签1"],
            image_prompts=["提示词"]
        )

        draft_dict = draft.to_dict()

        assert draft_dict["id"] == "draft1"
        assert draft_dict["title"] == "测试标题"
        assert draft_dict["status"] == "draft"
        print("✅ 转字典成功")

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "id": "draft1",
            "title": "测试标题",
            "content": "测试内容",
            "tags": ["标签1"],
            "image_prompts": ["提示词"],
            "status": "draft",
            "created_at": "2025-02-07T12:00:00",
            "updated_at": "2025-02-07T12:00:00"
        }

        draft = ContentDraft.from_dict(data)

        assert draft.id == "draft1"
        assert draft.title == "测试标题"
        assert draft.status == PreviewStatus.DRAFT
        print("✅ 从字典创建成功")


# ============================================================================
# 图片生成结果测试
# ============================================================================

class TestImageGenerationResult:
    """测试图片生成结果"""

    def test_success_result(self):
        """测试成功结果"""
        result = ImageGenerationResult(
            id="img1",
            prompt="测试提示词",
            status=ImageStatus.SUCCESS,
            image_url="https://example.com/image.png"
        )

        assert result.id == "img1"
        assert result.status == ImageStatus.SUCCESS
        assert result.image_url == "https://example.com/image.png"
        print("✅ 成功结果正确")

    def test_failed_result(self):
        """测试失败结果"""
        result = ImageGenerationResult(
            id="img1",
            prompt="测试提示词",
            status=ImageStatus.FAILED,
            error="生成失败"
        )

        assert result.status == ImageStatus.FAILED
        assert result.error == "生成失败"
        print("✅ 失败结果正确")


# ============================================================================
# 预览会话测试
# ============================================================================

class TestPreviewSession:
    """测试预览会话"""

    def test_initialization(self):
        """测试初始化"""
        draft = ContentDraft(
            id="draft1",
            title="测试",
            content="内容",
            tags=[],
            image_prompts=[]
        )

        session = PreviewSession(draft)

        assert session.draft == draft
        assert session.current_step == 0
        assert session.is_approved() is False
        print("✅ 会话初始化正确")

    def test_step_navigation(self):
        """测试步骤导航"""
        draft = ContentDraft(
            id="draft1",
            title="测试",
            content="内容",
            tags=[],
            image_prompts=[]
        )

        session = PreviewSession(draft)

        # 前进
        session.next_step()
        assert session.current_step == 1

        session.next_step()
        assert session.current_step == 2

        # 后退
        session.previous_step()
        assert session.current_step == 1

        # 不能小于 0
        session.previous_step()
        assert session.current_step == 0

        print("✅ 步骤导航正确")

    def test_approve_reject(self):
        """测试批准和拒绝"""
        draft = ContentDraft(
            id="draft1",
            title="测试",
            content="内容",
            tags=[],
            image_prompts=[]
        )

        session = PreviewSession(draft)

        # 批准
        session.approve()
        assert session.is_approved() is True
        assert session.draft.status == PreviewStatus.APPROVED

        # 重置
        session._approved = False

        # 拒绝
        session.reject()
        assert session.is_approved() is False
        assert session.draft.status == PreviewStatus.REJECTED

        print("✅ 批准和拒绝正确")

    def test_history(self):
        """测试历史记录"""
        draft = ContentDraft(
            id="draft1",
            title="测试",
            content="内容",
            tags=[],
            image_prompts=[]
        )

        session = PreviewSession(draft)

        session.add_history("action1", {"key": "value1"})
        session.add_history("action2", {"key": "value2"})

        history = session.get_history()

        assert len(history) == 2
        assert history[0]["action"] == "action1"
        assert history[1]["action"] == "action2"
        assert "timestamp" in history[0]

        print("✅ 历史记录正确")


# ============================================================================
# 内容预览器测试
# ============================================================================

class TestContentPreviewer:
    """测试内容预览器"""

    def test_create_draft(self):
        """测试创建草稿"""
        previewer = ContentPreviewer()

        draft = previewer.create_draft(
            title="测试标题",
            content="测试内容",
            tags=["标签1", "标签2"],
            image_prompts=["提示词1"]
        )

        assert draft.id is not None
        assert draft.title == "测试标题"
        assert len(draft.tags) == 2
        assert draft.status == PreviewStatus.DRAFT

        # 检查统计
        stats = previewer.get_stats()
        assert stats["total_previews"] == 1

        print("✅ 创建草稿成功")

    def test_preview_text_markdown(self):
        """测试 Markdown 预览"""
        previewer = ContentPreviewer()

        draft = previewer.create_draft(
            title="测试标题",
            content="这是测试内容",
            tags=["Python", "测试"],
            image_prompts=[]
        )

        preview = previewer.preview_text(draft, format_type="markdown")

        assert "# 测试标题" in preview
        assert "这是测试内容" in preview
        assert "#Python" in preview
        assert "#测试" in preview
        assert "草稿 ID:" in preview

        print("✅ Markdown 预览正确")

    def test_preview_text_plain(self):
        """测试纯文本预览"""
        previewer = ContentPreviewer()

        draft = previewer.create_draft(
            title="测试标题",
            content="这是测试内容",
            tags=["标签1"],
            image_prompts=[]
        )

        preview = previewer.preview_text(draft, format_type="plain")

        assert "标题: 测试标题" in preview
        assert "这是测试内容" in preview
        assert "标签: 标签1" in preview

        print("✅ 纯文本预览正确")

    def test_preview_text_html(self):
        """测试 HTML 预览"""
        previewer = ContentPreviewer()

        draft = previewer.create_draft(
            title="测试标题",
            content="测试内容",
            tags=["标签1"],
            image_prompts=[]
        )

        preview = previewer.preview_text(draft, format_type="html")

        assert "<h1>测试标题</h1>" in preview
        assert "测试内容" in preview
        assert "<span class='tag'>#标签1</span>" in preview

        print("✅ HTML 预览正确")

    def test_html_escaping(self):
        """测试 HTML 转义"""
        previewer = ContentPreviewer()

        draft = previewer.create_draft(
            title="<script>alert('test')</script>",
            content="内容",
            tags=[],
            image_prompts=[]
        )

        preview = previewer.preview_text(draft, format_type="html")

        assert "<script>" not in preview
        assert "&lt;script&gt;" in preview

        print("✅ HTML 转义正确")

    def test_modify_content(self):
        """测试修改内容"""
        previewer = ContentPreviewer()

        # 测试修改标题
        draft1 = previewer.create_draft("原标题", "原内容", ["标签1"], [])
        modified1 = previewer.modify_content(draft1, title="新标题")
        assert modified1.title == "新标题"
        assert modified1.content == "原内容"

        # 测试修改内容
        draft2 = previewer.create_draft("标题", "原内容", ["标签1"], [])
        modified2 = previewer.modify_content(draft2, content="新内容")
        assert modified2.content == "新内容"

        # 测试修改标签（替换）
        draft3 = previewer.create_draft("标题", "内容", ["标签1"], [])
        modified3 = previewer.modify_content(draft3, tags=["标签A", "标签B"])
        assert modified3.tags == ["标签A", "标签B"]

        # 测试追加标签
        draft4 = previewer.create_draft("标题", "内容", ["标签1"], [])
        modified4 = previewer.modify_content(draft4, append_tags=["标签2"])
        assert "标签1" in modified4.tags
        assert "标签2" in modified4.tags

        # 检查统计
        stats = previewer.get_stats()
        assert stats["modifications"] == 4

        print("✅ 修改内容正确")

    def test_create_session(self):
        """测试创建会话"""
        previewer = ContentPreviewer()

        draft = previewer.create_draft(
            title="测试",
            content="内容",
            tags=[],
            image_prompts=[]
        )

        session = previewer.create_session(draft)

        assert session.draft == draft
        assert session.current_step == 0

        print("✅ 创建会话正确")

    def test_confirm_publish(self):
        """测试确认发布"""
        previewer = ContentPreviewer()

        draft = previewer.create_draft(
            title="测试",
            content="内容",
            tags=[],
            image_prompts=[]
        )

        session = previewer.create_session(draft)

        # 批准
        session.approve()
        result = previewer.confirm_publish(session)
        assert result is True
        assert session.draft.status == PreviewStatus.PUBLISHED

        # 检查统计
        stats = previewer.get_stats()
        assert stats["approved_previews"] == 1

        # 拒绝
        session2 = previewer.create_session(draft)
        session2.reject()
        result2 = previewer.confirm_publish(session2)
        assert result2 is False
        assert session2.draft.status == PreviewStatus.REJECTED

        print("✅ 确认发布正确")

    @pytest.mark.asyncio
    async def test_generate_images_no_generator(self):
        """测试无图片生成器"""
        previewer = ContentPreviewer(image_generator=None)

        draft = previewer.create_draft(
            title="测试",
            content="内容",
            tags=[],
            image_prompts=["提示词1", "提示词2"]
        )

        # 应该抛出错误
        with pytest.raises(BusinessError):
            await previewer.generate_images(draft)

        print("✅ 无生成器错误正确")

    @pytest.mark.asyncio
    async def test_generate_images_with_mock(self):
        """测试模拟图片生成"""
        # 模拟图片生成器
        async def mock_generator(prompt):
            await asyncio.sleep(0.01)
            return {
                "url": f"https://example.com/{prompt}.png",
                "data": b"fake_image_data"
            }

        previewer = ContentPreviewer(image_generator=mock_generator)

        draft = previewer.create_draft(
            title="测试",
            content="内容",
            tags=[],
            image_prompts=["提示词1", "提示词2"]
        )

        results = await previewer.generate_images(draft)

        assert len(results) == 2
        assert results[0].status == ImageStatus.SUCCESS
        assert results[0].image_url == "https://example.com/提示词1.png"
        assert results[1].image_url == "https://example.com/提示词2.png"

        # 检查草稿已更新
        assert len(draft.images) == 2

        print("✅ 模拟图片生成正确")

    def test_stats(self):
        """测试统计信息"""
        previewer = ContentPreviewer()

        # 初始统计
        stats = previewer.get_stats()
        assert stats["total_previews"] == 0
        assert stats["modifications"] == 0

        # 创建草稿
        previewer.create_draft("标题", "内容", [], [])

        stats = previewer.get_stats()
        assert stats["total_previews"] == 1

        # 重置统计
        previewer.reset_stats()
        stats = previewer.get_stats()
        assert stats["total_previews"] == 0

        print("✅ 统计信息正确")


# ============================================================================
# 分步确认流程测试
# ============================================================================

class TestStepByStepConfirmation:
    """测试分步确认流程"""

    def test_initialization(self):
        """测试初始化"""
        previewer = ContentPreviewer()
        confirmation = StepByStepConfirmation(previewer)

        assert confirmation.previewer == previewer
        assert len(confirmation._steps) == 4

        print("✅ 初始化正确")

    @pytest.mark.asyncio
    async def test_auto_confirm_flow(self):
        """测试自动确认流程"""
        previewer = ContentPreviewer()

        draft = previewer.create_draft(
            title="测试标题",
            content="测试内容",
            tags=["标签1"],
            image_prompts=[]
        )

        confirmation = StepByStepConfirmation(previewer)

        # 自动确认模式
        session = await confirmation.run(draft, interactive=False)

        assert session.is_approved() is True
        assert session.current_step == 4

        print("✅ 自动确认流程正确")

    @pytest.mark.asyncio
    async def test_steps_count(self):
        """测试步骤数量"""
        previewer = ContentPreviewer()
        confirmation = StepByStepConfirmation(previewer)

        # 验证步骤
        assert len(confirmation._steps) == 4
        assert confirmation._step_preview_text in confirmation._steps
        assert confirmation._step_preview_images in confirmation._steps
        assert confirmation._step_confirm_tags in confirmation._steps
        assert confirmation._step_final_review in confirmation._steps

        print("✅ 步骤数量正确")


# ============================================================================
# 集成测试
# ============================================================================

class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_preview_flow(self):
        """测试完整预览流程"""
        # 模拟图片生成器
        async def mock_generator(prompt):
            return {"url": f"https://example.com/{prompt}.png"}

        previewer = ContentPreviewer(image_generator=mock_generator)

        # 创建草稿
        draft = previewer.create_draft(
            title="春天来了",
            content="春天来了，樱花盛开，美好的一天！",
            tags=["春天", "樱花"],
            image_prompts=["春天樱花盛开", "美好春光"]
        )

        # 预览文本
        text_preview = previewer.preview_text(draft, format_type="markdown")
        assert "春天来了" in text_preview

        # 生成图片
        image_results = await previewer.generate_images(draft)
        assert len(image_results) == 2
        assert all(r.status == ImageStatus.SUCCESS for r in image_results)

        # 创建会话
        session = previewer.create_session(draft)

        # 批准
        session.approve()
        assert previewer.confirm_publish(session) is True

        print("✅ 完整预览流程正确")


# ============================================================================
# 运行所有测试
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行内容预览功能测试...\n")

    print("="*60)
    print("测试内容草稿")
    print("="*60)
    TestContentDraft().test_create_draft()
    TestContentDraft().test_to_dict()
    TestContentDraft().test_from_dict()

    print("\n" + "="*60)
    print("测试图片生成结果")
    print("="*60)
    TestImageGenerationResult().test_success_result()
    TestImageGenerationResult().test_failed_result()

    print("\n" + "="*60)
    print("测试预览会话")
    print("="*60)
    TestPreviewSession().test_initialization()
    TestPreviewSession().test_step_navigation()
    TestPreviewSession().test_approve_reject()
    TestPreviewSession().test_history()

    print("\n" + "="*60)
    print("测试内容预览器")
    print("="*60)
    TestContentPreviewer().test_create_draft()
    TestContentPreviewer().test_preview_text_markdown()
    TestContentPreviewer().test_preview_text_plain()
    TestContentPreviewer().test_preview_text_html()
    TestContentPreviewer().test_html_escaping()
    TestContentPreviewer().test_modify_content()
    TestContentPreviewer().test_create_session()
    TestContentPreviewer().test_confirm_publish()
    TestContentPreviewer().test_stats()

    print("\n" + "="*60)
    print("测试分步确认流程")
    print("="*60)
    TestStepByStepConfirmation().test_initialization()
    TestStepByStepConfirmation().test_steps_count()

    print("\n" + "="*60)
    print("测试集成")
    print("="*60)
    asyncio.run(TestIntegration().test_full_preview_flow())

    print("\n" + "="*60)
    print("✅ 所有测试通过!")
    print("="*60)


if __name__ == "__main__":
    run_all_tests()
