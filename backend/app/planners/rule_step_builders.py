"""RulePlanner 使用的步骤清单构建 — 与路由规则解耦，便于单测与复用。"""

from __future__ import annotations

from typing import Any

FFMPEG_ROUTE_HINTS = (
    "ffmpeg",
    "导出视频",
    "视频样例",
    "生成短视频",
    "静音视频",
    "本地视频",
)


def ffmpeg_pack_step() -> dict[str, Any]:
    return {
        "step_name": "ffmpeg_pack",
        "action": "tool",
        "agent_role": "制品打包",
        "tool_name": "ffmpeg_artifact_tool",
        "tool_input": {"preset": "silent_mp4"},
    }


def parallel_pillar_steps(user_message: str) -> list[Any]:
    u = user_message.strip()
    return [
        {
            "parallel": [
                {
                    "step_name": "infra_line",
                    "action": "model",
                    "agent_role": "基础设施",
                    "prompt": (
                        "你是基础设施与平台代理（部署、网络、环境、CI/CD、可观测性）。\n"
                        f"需求：\n{u}\n"
                        "请输出：环境划分、关键依赖、发布与回滚注意点（条目）。"
                    ),
                },
                {
                    "step_name": "business_line",
                    "action": "model",
                    "agent_role": "业务模块",
                    "prompt": (
                        "你是业务与产品实现代理（领域模型、流程、权限与规则）。\n"
                        f"需求：\n{u}\n"
                        "请输出：核心用例、实体与状态、协作边界（条目）。"
                    ),
                },
                {
                    "step_name": "data_line",
                    "action": "model",
                    "agent_role": "数据模块",
                    "prompt": (
                        "你是数据与存储代理（模型、一致性、迁移）。\n"
                        f"需求：\n{u}\n"
                        "请输出：主数据与事务边界、存储与备份要点（条目）。"
                    ),
                },
            ]
        },
        {
            "step_name": "merge_pillar",
            "action": "model",
            "agent_role": "协调代理",
            "prompt_template": (
                "三线（基建/业务/数据）并行产出如下，请合并为整体交付视图："
                "对齐术语、标出跨线依赖。\n\n"
                "## 基础设施\n{infra_line}\n\n"
                "## 业务\n{business_line}\n\n"
                "## 数据\n{data_line}\n\n"
                "请输出：统一里程碑 + 风险登记表（Markdown）。"
            ),
            "use_step_result_keys": ["infra_line", "business_line", "data_line"],
        },
    ]


def parallel_pillar_steps_with_ffmpeg(user_message: str) -> list[Any]:
    steps = list(parallel_pillar_steps(user_message))
    steps.append(ffmpeg_pack_step())
    return steps


def parallel_module_steps(user_message: str) -> list[Any]:
    u = user_message.strip()
    return [
        {
            "parallel": [
                {
                    "step_name": "backend_module",
                    "action": "model",
                    "agent_role": "后端模块",
                    "prompt": (
                        "你是后端开发代理，只关注服务端与数据。\n"
                        f"需求说明：\n{u}\n"
                        "请输出：API 草案、核心数据模型、关键边界条件（条目列表，简明）。"
                    ),
                },
                {
                    "step_name": "frontend_module",
                    "action": "model",
                    "agent_role": "前端模块",
                    "prompt": (
                        "你是前端开发代理，只关注界面与交互。\n"
                        f"需求说明：\n{u}\n"
                        "请输出：页面/路由拆分、组件层级、状态与接口对接注意点（条目列表，简明）。"
                    ),
                },
                {
                    "step_name": "quality_module",
                    "action": "model",
                    "agent_role": "测试与质量模块",
                    "prompt": (
                        "你是测试与质量代理。\n"
                        f"需求说明：\n{u}\n"
                        "请输出：验收场景、关键用例、风险与监控点（条目列表，简明）。"
                    ),
                },
            ]
        },
        {
            "step_name": "merge_coordination",
            "action": "model",
            "agent_role": "协调代理",
            "prompt_template": (
                "你是项目协调代理。以下三个模块并行产出，请合并成一份可执行的交付说明："
                "统一术语、消除冲突、标注前后端接口契约与优先级。\n\n"
                "## 后端模块产出\n{backend_module}\n\n"
                "## 前端模块产出\n{frontend_module}\n\n"
                "## 测试与质量产出\n{quality_module}\n\n"
                "请输出：整合后的里程碑清单 + 接口对齐表（Markdown）。"
            ),
            "use_step_result_keys": [
                "backend_module",
                "frontend_module",
                "quality_module",
            ],
        },
    ]


def parallel_module_steps_with_ffmpeg(user_message: str) -> list[Any]:
    steps = list(parallel_module_steps(user_message))
    steps.append(ffmpeg_pack_step())
    return steps


def research_team_steps(user_message: str) -> list[dict[str, Any]]:
    return [
        {
            "step_name": "decompose",
            "action": "model",
            "agent_role": "拆解员",
            "prompt": (
                "你是课题拆解员。用户课题如下：\n"
                f"{user_message}\n"
                "请列出 3～5 个子问题或研究要点（条目即可，简明）。"
            ),
        },
        {
            "step_name": "research_notes",
            "action": "model",
            "agent_role": "调研员",
            "prompt_template": (
                "你是调研员。以下是拆解后的要点：\n{step_output}\n"
                "请补充关键事实、术语定义与可查证方向（简明条目，不必编造来源）。"
            ),
            "use_step_result": "decompose",
        },
        {
            "step_name": "writeup",
            "action": "model",
            "agent_role": "撰稿员",
            "prompt_template": (
                "你是撰稿员。在下列调研草稿基础上，输出一篇简短综述，"
                "分段：背景 / 要点 / 结论 / 后续可做；面向终端用户阅读。\n---\n"
                "{step_output}\n---"
            ),
            "use_step_result": "research_notes",
        },
    ]


def research_team_ffmpeg_steps(user_message: str) -> list[dict[str, Any]]:
    steps = list(research_team_steps(user_message))
    steps.append(ffmpeg_pack_step())
    return steps
