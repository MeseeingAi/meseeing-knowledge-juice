#!/usr/bin/env python3
"""
storyboard_factory.py  — 短视频脚本工厂 · 独立运行版
======================================================
功能：接收一段文字描述，自动生成 JSON 格式的分镜板
用法：
    python storyboard_factory.py "一款能自动识别200种鸟类的AI相机"
    python storyboard_factory.py "描述文本" --style cyberpunk

核心引擎来源：VideoEngine/prompt_engine.py（脱敏精简版）
License: Apache 2.0
"""

import json
import sys
import os
import argparse
from typing import List, Optional
from dataclasses import dataclass, field


# ════════════════════════════════════════════════════
#  数据类
# ════════════════════════════════════════════════════

@dataclass
class Shot:
    """一个镜头"""
    shot_id: int
    description: str          # 场景描述（人类可读）
    prompt: str               # 视频生成模型用的 prompt
    duration: int = 5
    camera_motion: Optional[str] = None  # 镜头运动类型
    style: str = "cinematic"


@dataclass
class Storyboard:
    """分镜板 —— 一系列镜头的集合"""
    title: str
    shots: List[Shot] = field(default_factory=list)
    style_global: str = "cinematic"

    def to_json(self, indent: int = 2) -> str:
        """输出格式化的 JSON 字符串"""
        return json.dumps({
            "title": self.title,
            "style": self.style_global,
            "shots": [
                {
                    "shot_id": s.shot_id,
                    "description": s.description,
                    "prompt": s.prompt,
                    "duration": s.duration,
                    "camera_motion": s.camera_motion,
                    "style": s.style,
                }
                for s in self.shots
            ],
        }, ensure_ascii=False, indent=indent)


# ════════════════════════════════════════════════════
#  PromptEngine — 叙事到镜头的转换器
# ════════════════════════════════════════════════════

class PromptEngine:
    """
    Prompt 工程引擎

    核心逻辑：风格模板（前缀/后缀）+ 镜头运动词库 → 拼装出专业 prompt。

    【设计意图】
    视频生成模型（如 Kling、Runway）对 prompt 质量非常敏感。
    直接写 "a bird" 效果远不如
    "Cinematic, film grain, 4K, professional lighting, a bird on a branch,
     camera slowly zooming in, masterpiece, trending on artstation"。

    本引擎就是自动做好这件事。
    """

    # ── 风格模板库 ──────────────────────────────
    # 每种风格分为 prefix（引导词）和 suffix（质量收尾词）
    STYLE_TEMPLATES = {
        "cinematic": {
            "prefix": "Cinematic, film grain, 4K, professional lighting, shallow depth of field",
            "suffix": "masterpiece, highest quality, trending on artstation",
        },
        "anime": {
            "prefix": "Anime style, Studio Ghibli inspired, cel shaded, vibrant colors",
            "suffix": "high quality anime, detailed background, beautiful composition",
        },
        "dark_fantasy": {
            "prefix": "Dark fantasy, moody atmosphere, dramatic lighting, volumetric fog",
            "suffix": "epic, cinematic, dark aesthetic, highly detailed",
        },
        "cyberpunk": {
            "prefix": "Cyberpunk, neon lights, rain, futuristic city, high contrast",
            "suffix": "synthwave aesthetic, blade runner style, detailed",
        },
        "realistic": {
            "prefix": "Photorealistic, natural lighting, 8K, highly detailed texture",
            "suffix": "real world, authentic, sharp focus",
        },
    }

    # ── 镜头运动词库 ────────────────────────────
    # 每种运动对应一段自然语言描述，用于注入到 prompt 中
    CAMERA_MOTIONS = {
        "push_in":     "dolly zoom in, camera slowly moving forward",
        "pull_out":    "camera slowly pulling back, revealing the scene",
        "pan_left":    "panning left, following the subject",
        "pan_right":   "panning right, revealing the environment",
        "track_left":  "tracking shot moving left",
        "track_right": "tracking shot moving right",
        "crane_up":    "crane shot rising up",
        "crane_down":  "crane shot descending",
        "aerial":      "aerial view, drone shot, birds eye view",
        "handheld":    "handheld camera, slight shake, documentary style",
        "static":      "static shot, tripod mounted, stable composition",
    }

    def __init__(self, default_style: str = "cinematic"):
        self.default_style = default_style

    def build_prompt(
        self,
        scene_description: str,
        style: Optional[str] = None,
        camera_motion: Optional[str] = None,
    ) -> str:
        """
        从自然语言描述构建高质量视频 prompt。

        流程：
            1. 选择风格模板（默认 cinematic）
            2. 如果指定了镜头运动，查词库得到自然语言描述
            3. 按「前缀 + 场景描述 + 运动描述 + 后缀」拼接

        示例：
            >>> engine = PromptEngine()
            >>> engine.build_prompt("一只白鹭飞过湖面", style="cinematic", camera_motion="pan_right")
            'Cinematic, film grain, 4K, ..., 一只白鹭飞过湖面, panning right, ..., masterpiece, ...'
        """
        style = style or self.default_style
        template = self.STYLE_TEMPLATES.get(style, self.STYLE_TEMPLATES["cinematic"])

        # 收集所有有效的片段
        parts = [template["prefix"], scene_description]

        if camera_motion:
            motion_desc = self.CAMERA_MOTIONS.get(camera_motion, camera_motion)
            parts.append(motion_desc)

        parts.append(template["suffix"])

        return ", ".join(p for p in parts if p)

    def story_to_storyboard(
        self,
        title: str,
        shots_data: List[dict],
        global_style: str = "cinematic",
    ) -> Storyboard:
        """
        从结构化镜头数据生成完整分镜板。

        shots_data 每项格式：
            {
                "description": "场景描述",
                "duration": 5,
                "camera_motion": "push_in",
                "style": "可选，覆盖全局风格",
            }
        """
        shots = []
        for i, s in enumerate(shots_data):
            style = s.get("style", global_style)
            prompt = self.build_prompt(
                scene_description=s["description"],
                style=style,
                camera_motion=s.get("camera_motion"),
            )
            shots.append(Shot(
                shot_id=i + 1,
                description=s["description"],
                prompt=prompt,
                duration=s.get("duration", 5),
                camera_motion=s.get("camera_motion"),
                style=style,
            ))

        return Storyboard(title=title, shots=shots, style_global=global_style)

    def single_shot(self, description: str, **kwargs) -> Shot:
        """快速创建一个单镜头（适合快速测试）"""
        prompt = self.build_prompt(description, **kwargs)
        return Shot(
            shot_id=1,
            description=description,
            prompt=prompt,
            duration=kwargs.get("duration", 5),
            camera_motion=kwargs.get("camera_motion"),
            style=kwargs.get("style", self.default_style),
        )


# ════════════════════════════════════════════════════
#  演示分镜板生成器
# ════════════════════════════════════════════════════

def build_demo_storyboard(product_description: str, style: str = "cinematic") -> Storyboard:
    """
    根据产品描述，生成一个 6 镜头的演示分镜板。

    这里手动设计了广告片的叙事节奏：
        镜头1：开篇定场（环境建立）
        镜头2：问题引入（用户痛点）
        镜头3：产品亮相（特写展示）
        镜头4：功能演示（使用场景）
        镜头5：用户体验（情感反应）
        镜头6：品牌收尾（升华/Slogan）

    🔮 未来版本：接入 LLM 自动拆解分镜，无需手动设计叙事模板。
    """
    engine = PromptEngine(default_style=style)

    # 为演示目的，将输入描述拆成 6 个叙事镜头
    shots_data = [
        {
            "description": f"开阔的自然环境，暗示{product_description}的使用场景，阳光透过树叶洒下",
            "duration": 5,
            "camera_motion": "aerial",
            "style": style,
        },
        {
            "description": "近景：一位自然爱好者正在仰望树梢，似乎在寻找什么，表情专注",
            "duration": 4,
            "camera_motion": "push_in",
            "style": style,
        },
        {
            "description": f"特写：{product_description}出现在画面中，精致的外观设计，科技感十足",
            "duration": 5,
            "camera_motion": "track_right",
            "style": style,
        },
        {
            "description": "主观视角：通过设备屏幕看到一只鸟落在枝头，界面自动显示鸟类名称和特征信息",
            "duration": 6,
            "camera_motion": "push_in",
            "style": style,
        },
        {
            "description": "人物面部表情：用户看到识别结果后露出惊喜和满足的微笑",
            "duration": 4,
            "camera_motion": "pull_out",
            "style": style,
        },
        {
            "description": f"远景：用户手持{product_description}站在美丽的自然风景中，人与科技和谐共存，品牌Slogan浮现",
            "duration": 6,
            "camera_motion": "crane_up",
            "style": style,
        },
    ]

    # 从产品描述中提取关键词作为标题
    title_text = product_description[:20] + ("..." if len(product_description) > 20 else "")

    return engine.story_to_storyboard(
        title=f"{title_text} - 品牌广告",
        shots_data=shots_data,
        global_style=style,
    )


# ════════════════════════════════════════════════════
#  LLM 增强入口（预留 — 仅用于模型增强分镜）
# ════════════════════════════════════════════════════

def _llm_enhance_storyboard(description: str, api_key: str) -> dict:
    """
    使用 LLM 自动拆解分镜（未来功能，当前为占位）

    目前演示版使用规则模板手动分镜。
    当该函数启用后，将调用 GPT-4 等模型自动分析叙事结构，
    生成更动态、更贴合具体内容的分镜方案。
    """
    # 占位：避免 IDE 报 unused import 警告
    _ = api_key
    raise NotImplementedError(
        "LLM 自动分镜功能尚在开发中。"
        "当前使用内置规则模板进行分镜。"
        "如需参与内测，请配置 OPENAI_API_KEY 环境变量。"
    )


# ════════════════════════════════════════════════════
#  主入口
# ════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="🎬 短视频脚本工厂 — 输入产品描述，自动生成分镜板",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python storyboard_factory.py "一款能自动识别200种鸟类的AI相机"
  python storyboard_factory.py "智能翻译耳机" --style cyberpunk
  python storyboard_factory.py "无线充电宝" --style realistic

输出: JSON 格式的分镜板 stdout，可直接 pipe 到文件:
  python storyboard_factory.py "产品名" > storyboard.json
        """,
    )
    parser.add_argument(
        "description",
        type=str,
        help="产品/服务描述，例如：'一款能自动识别200种鸟类的AI相机'",
    )
    parser.add_argument(
        "--style",
        type=str,
        default="cinematic",
        choices=list(PromptEngine.STYLE_TEMPLATES.keys()),
        help=f"视频风格，可选: {', '.join(PromptEngine.STYLE_TEMPLATES.keys())}（默认: cinematic）",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="使用 LLM 增强分镜（开发中，目前不可用）",
    )

    args = parser.parse_args()

    # LLM 模式（预留）
    if args.llm:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print(
                '{"error": "LLM 模式需要设置 OPENAI_API_KEY 环境变量"}',
                file=sys.stderr,
            )
            sys.exit(1)
        # 未来：_llm_enhance_storyboard(args.description, api_key)
        print(
            '{"error": "LLM 自动分镜功能尚在开发中，当前使用规则模板"}',
            file=sys.stderr,
        )
        # fall through 到规则模板

    # 使用规则模板生成演示分镜板
    storyboard = build_demo_storyboard(args.description, style=args.style)
    print(storyboard.to_json())


if __name__ == "__main__":
    main()
