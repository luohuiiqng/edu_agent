"""本地 ffmpeg：生成极简演示音视频文件并产出可供 ``deliverables`` 登记的路径。"""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from app.schemas.collaboration import deliverable_dict
from app.schemas.tool_input import ToolInput
from app.schemas.tool_output import ToolOutput
from app.tools.base_tool import BaseTool

# 仅允许固定预设，避免任意命令注入（参数以列表传入，不走 shell）
_PRESETS: dict[str, tuple[list[str], str, str]] = {
    "silent_mp4": (
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
        ],
        ".mp4",
        "video",
    ),
    "tone_wav": (
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
        ],
        ".wav",
        "audio",
    ),
}


def default_artifacts_root() -> Path:
    # backend/app/tools -> parents[2] == backend
    return Path(__file__).resolve().parents[2] / "data" / "artifacts"


class FfmpegArtifactTool(BaseTool):
    """调用本机 ffmpeg，生成短样例文件；输出路径写入 metadata.deliverable。"""

    def __init__(self, artifacts_root: Path | None = None, **kwargs) -> None:
        super().__init__(
            name="ffmpeg_artifact_tool",
            description="使用本地 ffmpeg 生成演示用音频/视频文件（预设 silent_mp4 / tone_wav）",
            **kwargs,
        )
        self._artifacts_root = artifacts_root or default_artifacts_root()

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        params = tool_input.params or {}
        preset = str(params.get("preset") or "silent_mp4").strip()
        if preset not in _PRESETS:
            return ToolOutput(
                content="",
                success=False,
                error_message=f"未知 preset，可选: {', '.join(sorted(_PRESETS))}",
                metadata={"name": self._name},
            )

        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            return ToolOutput(
                content="",
                success=False,
                error_message="未找到 ffmpeg，请安装后再试（PATH 中需可执行 ffmpeg）",
                metadata={"name": self._name},
            )

        base = params.get("filename")
        if base:
            stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(base))[
                :80
            ]
            if not stem:
                stem = "artifact"
        else:
            stem = f"artifact-{uuid.uuid4().hex[:12]}"

        argv_prefix, suffix, artifact_kind = _PRESETS[preset]
        root = Path(params.get("artifacts_root") or self._artifacts_root)
        root.mkdir(parents=True, exist_ok=True)
        out_path = root.resolve() / f"{stem}{suffix}"

        cmd = [ffmpeg_bin, *argv_prefix, str(out_path)]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ToolOutput(
                content="",
                success=False,
                error_message="ffmpeg 执行超时",
                metadata={"name": self._name},
            )

        if proc.returncode != 0:
            err_tail = (proc.stderr or proc.stdout or "")[-800:]
            return ToolOutput(
                content="",
                success=False,
                error_message=f"ffmpeg 失败 (code={proc.returncode}): {err_tail}",
                metadata={"name": self._name},
            )

        uri = out_path.as_uri()
        title = "静音样例视频" if preset == "silent_mp4" else "单音调样例音频"
        summary = f"preset={preset}, path={out_path}"
        d_meta = deliverable_dict(
            artifact_kind,  # "video" | "audio"
            title=title,
            uri=uri,
            summary=summary,
            meta={"preset": preset, "local_path": str(out_path)},
        )

        return ToolOutput(
            content=str(out_path),
            success=True,
            metadata={
                "name": self._name,
                "deliverable": d_meta,
            },
        )
