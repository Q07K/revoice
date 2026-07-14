"""Render a finished cover (audio) into a YouTube-ready mp4 via ffmpeg.

Three visual styles — a static cover image, an animated waveform (showwaves),
or a scrolling spectrum (showspectrum) — in 16:9 or 9:16, with a title/subtitle
lower-third burned in via libass. libass (not drawtext) is used for text because
it does proper CJK layout and per-glyph fontconfig fallback; drawtext against the
Noto CJK .ttc collection renders only a partial glyph subset on this platform.
"""

import logging
from pathlib import Path

from app.engines.base import EngineError, VideoSpec, run_command

logger = logging.getLogger(__name__)

_RESOLUTIONS = {"16:9": (1920, 1080), "9:16": (1080, 1920)}
_FONT_NAME = "Noto Sans CJK KR"


def _ffmpeg_path(path: Path) -> str:
    """Escape a path for use inside a filtergraph option value."""
    return str(path).replace("\\", "\\\\").replace(":", r"\:")


def _ass_text(text: str) -> str:
    """Make user text safe for an ASS Dialogue line: strip override braces and
    collapse newlines (libass wraps to the margins on its own)."""
    return (
        text.replace("\\", "")
        .replace("{", "(")
        .replace("}", ")")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


class FfmpegVideoRenderer:
    def render(self, spec: VideoSpec) -> Path:
        width, height = _RESOLUTIONS.get(spec.aspect, _RESOLUTIONS["16:9"])
        spec.output_path.parent.mkdir(parents=True, exist_ok=True)
        work_dir = spec.output_path.parent

        if spec.visual == "image":
            inputs, video_chain, audio_map = self._image_source(spec, width, height)
        elif spec.visual == "spectrum":
            inputs, video_chain, audio_map = self._spectrum_source(spec, width, height)
        else:  # "wave" (default)
            inputs, video_chain, audio_map = self._wave_source(spec, width, height)

        ass_path = self._build_ass(spec, work_dir, width, height)
        overlay = f",ass={_ffmpeg_path(ass_path)}" if ass_path is not None else ""

        filter_complex = f"{video_chain}{overlay}[vout]"
        command = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", audio_map,
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            str(spec.output_path),
        ]
        run_command(command)
        if not spec.output_path.exists():
            raise EngineError("영상 렌더링 결과가 생성되지 않았어요. 백엔드 로그를 확인하세요.")
        return spec.output_path

    def _image_source(
        self, spec: VideoSpec, width: int, height: int
    ) -> tuple[list[str], str, str]:
        scale_crop = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1"
        )
        if spec.image_path is not None and spec.image_path.exists():
            inputs = ["-loop", "1", "-framerate", "30", "-i", str(spec.image_path),
                      "-i", str(spec.audio_path)]
        else:
            inputs = ["-f", "lavfi", "-i", f"color=c=0x14242b:s={width}x{height}:r=30",
                      "-i", str(spec.audio_path)]
        return inputs, f"[0:v]{scale_crop}", "1:a"

    def _wave_source(
        self, spec: VideoSpec, width: int, height: int
    ) -> tuple[list[str], str, str]:
        inputs = ["-i", str(spec.audio_path)]
        chain = f"[0:a]showwaves=s={width}x{height}:mode=cline:rate=30:colors=0x7fd0d8|0x2f8f99"
        return inputs, chain, "0:a"

    def _spectrum_source(
        self, spec: VideoSpec, width: int, height: int
    ) -> tuple[list[str], str, str]:
        inputs = ["-i", str(spec.audio_path)]
        chain = (
            f"[0:a]showspectrum=s={width}x{height}:mode=combined:"
            f"color=intensity:scale=cbrt:slide=scroll:fps=30"
        )
        return inputs, chain, "0:a"

    def _build_ass(
        self, spec: VideoSpec, work_dir: Path, width: int, height: int
    ) -> Path | None:
        title = _ass_text(spec.title)
        subtitle = _ass_text(spec.subtitle)
        if not title and not subtitle:
            return None

        base = min(width, height)
        title_fs = int(base * 0.05)
        sub_fs = int(base * 0.030)
        outline = max(2, base // 360)
        margin_l = int(width * 0.07)
        margin_r = int(width * 0.05)
        sub_margin_v = int(height * 0.05)
        # keep the title stacked above the subtitle box
        title_margin_v = sub_margin_v + int(sub_fs * 2.2)

        events = []
        if title:
            events.append(
                f"Dialogue: 0,0:00:00.00,9:59:00.00,Title,,0,0,0,,{title}"
            )
        if subtitle:
            events.append(
                f"Dialogue: 0,0:00:00.00,9:59:00.00,Sub,,0,0,0,,{subtitle}"
            )

        # Colours are ASS &HAABBGGRR (AA=00 opaque). White title with a black
        # outline; dark-teal subtitle text on an opaque teal box (BorderStyle 3).
        ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,{_FONT_NAME},{title_fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,{outline},2,1,{margin_l},{margin_r},{title_margin_v},1
Style: Sub,{_FONT_NAME},{sub_fs},&H00332F0C,&H00332F0C,&H00D8D07F,&H00D8D07F,1,0,0,0,100,100,0,0,3,{max(6, outline * 2)},0,1,{margin_l},{margin_r},{sub_margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
{chr(10).join(events)}
"""
        ass_path = work_dir / "overlay.ass"
        ass_path.write_text(ass, encoding="utf-8")
        return ass_path
