import shutil
import tempfile
from pathlib import Path

from app.schemas.tool_input import ToolInput
from app.tools.ffmpeg_artifact_tool import FfmpegArtifactTool


def _run() -> None:
    bad = FfmpegArtifactTool().run(ToolInput(params={"preset": "unknown"}))
    assert not bad.success

    if not shutil.which("ffmpeg"):
        print("ffmpeg not in PATH, skip ffmpeg execution checks")
        print("ffmpeg artifact tool tests passed")
        return

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tool = FfmpegArtifactTool(artifacts_root=root)
        wav = tool.run(ToolInput(params={"preset": "tone_wav", "filename": "beep"}))
        assert wav.success, wav.error_message
        p = Path(str(wav.content))
        assert p.exists()
        assert wav.metadata.get("deliverable")

        mp4 = tool.run(ToolInput(params={"preset": "silent_mp4", "filename": "demo"}))
        assert mp4.success, mp4.error_message
        assert Path(str(mp4.content)).exists()

    print("ffmpeg artifact tool tests passed")


_run()
