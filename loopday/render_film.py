"""Render the same 3D stage used by the viewer to an offline, captioned MP4."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from contextlib import contextmanager
import ctypes as ct
from ctypes.util import find_library
from functools import lru_cache
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Iterator
from wave import Error as WaveError

from .film import build_teaser, subtitles
from .film_audio import render_audio
from .film_depth import RasterBuffer
from .film_stage import build_bundle, source_label


WEB = Path(__file__).resolve().parent.parent / "web"


class JavaScriptCore:
    """Use the system renderer runtime on macOS without a browser or HTTP server."""

    def __init__(self):
        library = find_library("JavaScriptCore")
        if not library:
            raise RuntimeError("JavaScriptCore was unavailable.")
        self.lib = ct.CDLL(library)
        pointer = ct.c_void_p
        self._api("JSGlobalContextCreate", pointer, pointer)
        self._api("JSGlobalContextRelease", None, pointer)
        self._api("JSStringCreateWithUTF8CString", pointer, ct.c_char_p)
        self._api("JSStringRelease", None, pointer)
        self._api("JSEvaluateScript", pointer, pointer, pointer, pointer, pointer, ct.c_int, ct.POINTER(pointer))
        self._api("JSValueToStringCopy", pointer, pointer, pointer, ct.POINTER(pointer))
        self._api("JSStringGetMaximumUTF8CStringSize", ct.c_size_t, pointer)
        self._api("JSStringGetUTF8CString", ct.c_size_t, pointer, ct.c_char_p, ct.c_size_t)
        self.context = self.lib.JSGlobalContextCreate(None)
        if not self.context:
            raise RuntimeError("Could not start JavaScriptCore.")

    def _api(self, name: str, result, *parameters) -> None:
        method = getattr(self.lib, name)
        method.restype = result
        method.argtypes = parameters

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.lib.JSGlobalContextRelease(self.context)

    def evaluate(self, script: str) -> str:
        command = self.lib.JSStringCreateWithUTF8CString(script.encode("utf-8"))
        error = ct.c_void_p()
        try:
            shared = self.lib.JSEvaluateScript(self.context, command, None, None, 1, ct.byref(error))
        finally:
            self.lib.JSStringRelease(command)
        value = self.lib.JSValueToStringCopy(self.context, error.value or shared, None)
        try:
            size = self.lib.JSStringGetMaximumUTF8CStringSize(value)
            buffer = ct.create_string_buffer(size)
            self.lib.JSStringGetUTF8CString(value, buffer, size)
            result = buffer.value.decode("utf-8")
        finally:
            self.lib.JSStringRelease(value)
        if error.value:
            raise RuntimeError(result)
        return result


@contextmanager
def _projector(bundle: dict) -> Iterator:
    module = (WEB / "renderer.js").read_text(encoding="utf-8")
    module = re.sub(r"^export ", "", module, flags=re.MULTILINE)
    init = module + "\nconst bundle = " + json.dumps({"art": bundle["art"], "stages": bundle["stages"]}) + ";"
    try:
        engine = JavaScriptCore()
    except RuntimeError:
        engine = None
    if engine:
        with engine:
            engine.evaluate(init)
            yield lambda shot, progress, width, height: json.loads(
                engine.evaluate(f"JSON.stringify(projectScene(bundle.art,bundle.stages[{shot}],{progress},{width},{height}))")
            )
        return

    node = shutil.which("node")
    if not node:
        raise RuntimeError("To render locally, use macOS JavaScriptCore or install Node.js.")
    script = init + """
      require('readline').createInterface({ input: process.stdin }).on('line', input => {
        const [index, progress, width, height] = JSON.parse(input);
        const result = projectScene(bundle.art, bundle.stages[index], progress, width, height);
        process.stdout.write(JSON.stringify(result) + '\\n');
      });
    """
    with tempfile.TemporaryDirectory(prefix="loopday-js-") as folder:
        source = Path(folder) / "project.cjs"
        source.write_text(script, encoding="utf-8")
        with subprocess.Popen(
            [node, str(source)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8",
        ) as process:
            def project(shot, progress, width, height):
                process.stdin.write(json.dumps([shot, progress, width, height]) + "\n")
                process.stdin.flush()
                raw = process.stdout.readline()
                if not raw:
                    raise RuntimeError("Node.js exited while projecting the scene.")
                return json.loads(raw)

            try:
                yield project
            finally:
                process.stdin.close()


def _font_paths(serif: bool) -> tuple[str, ...]:
    if serif:
        return (
            "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        )
    return (
        "/System/Library/Fonts/Avenir Next.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )


@lru_cache(maxsize=16)
def _font(size: int, serif: bool = False):
    from PIL import ImageFont

    path = next((value for value in _font_paths(serif) if Path(value).is_file()), None)
    if path:
        return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


@lru_cache(maxsize=32)
def _sky(width: int, height: int, colors: tuple):
    from PIL import Image, ImageColor

    stops = tuple(ImageColor.getrgb(color) for color in colors)
    pixels = []
    for line in range(height):
        phase = line / max(1, height - 1)
        if phase < .65:
            a, b, factor = stops[0], stops[1], phase / .65
        else:
            a, b, factor = stops[1], stops[2], (phase - .65) / .35
        pixels.append(tuple(round(x + (y - x) * factor) for x, y in zip(a, b)))
    gradient = Image.new("RGB", (1, height))
    gradient.putdata(pixels)
    return gradient.resize((width, height))


def _lines(text: str, font, width: float) -> list[str]:
    lines = []
    active = ""
    for word in text.split():
        candidate = (active + " " + word).strip()
        if not active or font.getlength(candidate) <= width:
            active = candidate
            continue
        lines.append(active)
        if len(lines) == 3:
            lines[-1] += "…"
            return lines
        active = word
    if active:
        lines.append(active)
    return lines


def _ease(value: float) -> float:
    value = min(1., max(0., value))
    return value * value * (3 - 2 * value)


@lru_cache(maxsize=8)
def _vignette(width: int, height: int):
    from PIL import Image

    sample = Image.new("L", (120, 80))
    short, long = min(width, height), max(width, height)
    outer = long * .62
    inner = short * .31
    sample.putdata([
        round(92 * _ease((math.hypot((x / 119 - .53) * width, (y / 79 - .47) * height) - inner) / (outer - inner)))
        for y in range(80) for x in range(120)
    ])
    return sample.resize((width, height), Image.Resampling.BILINEAR)


def paint(projected: dict, stage: dict, shot: dict, progress: float, width: int, height: int, mode: str,
          raster: RasterBuffer | None = None):
    """Rasterize shared projected faces, then add timed title and subtitle overlays."""
    from PIL import ImageDraw

    sky = _sky(width, height, tuple(projected["sky"]))
    image = raster.draw(sky, projected["faces"]) if raster else None
    if image is None:
        image = sky.copy()
        draw = ImageDraw.Draw(image, "RGBA")
        for color, polygon in projected["faces"]:
            draw.polygon([tuple(point[:2]) for point in polygon], fill=color)
    image.paste((9, 15, 28), (0, 0, width, height), _vignette(width, height))
    draw = ImageDraw.Draw(image, "RGBA")
    flurry = stage.get("flurry", 0)
    if flurry:
        unit = height / 720
        for index in range(math.ceil(136 * flurry)):
            gust = (395 if stage["storm"] else 65) + index % 7 * 12
            x = (index * 163.397 * unit + progress * gust) % width
            y = (index * 52.613 * unit + progress * (105 + index % 4 * 18)) % height
            size = max(1, (1 + index % 9 * .30) * unit)
            draw.rectangle((x, y, x + size * (1.55 if stage["storm"] else 1), y + size),
                           fill=(218, 235, 244, 168 if index % 4 == 0 else 105))
    if shot["title"]:
        opacity = _ease(progress / .15) * _ease((1 - progress) / .20)
        horizon = round(height * .62)
        for y in range(horizon, height):
            shade = round(opacity * 208 * ((y - horizon) / (height - horizon)))
            draw.line((0, y, width, y), fill=(16, 22, 28, shade))
        draw.text((width / 2, height * (.79 if shot["caption"] else .889)), shot["title"], anchor="ms",
                  font=_font(round(min(height * .077, width * .107)), True),
                  fill=(248, 238, 224, round(255 * opacity)))
    if shot.get("hook"):
        font = _font(round(min(width * .083, height * .081)), True)
        title = _lines(shot["hook"], font, width * .85)
        if len(title) == 1:
            title = [shot["hook"]]
        for index, line in enumerate(title):
            draw.text((width / 2, height * (.14 + index * .062)), line, anchor="mm", font=font,
                      fill="#fff0dc", stroke_width=2, stroke_fill="#18232b")
    if shot.get("eyebrow"):
        font = _font(round(min(width * .059, height * .036)))
        draw.text((width / 2, height * .823), shot["eyebrow"], font=font, anchor="ms",
                  fill="#ffebcd", stroke_width=3, stroke_fill="#16222b")
    if shot["caption"]:
        size = max(13, round(height * .038))
        font = _font(size)
        lines = _lines(shot["caption"], font, width * .77)
        baseline, line_height = height * .91, size * 1.32
        for index, line in enumerate(lines):
            y = baseline - (len(lines) - 1 - index) * line_height
            length = font.getlength(line)
            draw.rectangle((width / 2 - length / 2 - 13, y - size, width / 2 + length / 2 + 13, y + size * .31),
                           fill=(12, 21, 28, 209))
            draw.text((width / 2, y), line, anchor="ms", font=font, fill="#fffcf3")
        if shot["speaker"]:
            draw.text((width / 2, baseline - len(lines) * line_height - size * .14), shot["speaker"],
                      anchor="ms", font=_font(round(size * .74)), fill="#ffe2b8",
                      stroke_width=2, stroke_fill="#131b24")
    if mode:
        size = max(10, round(height * .023))
        label = _font(size)
        draw.rectangle((12, 12, 30 + label.getlength(mode), size + 24), fill=(15, 22, 29, 185))
        draw.text((21, 19), mode, anchor="lt", font=label, fill="#f4ead9")
    return image


def _ffmpeg() -> str:
    native = shutil.which("ffmpeg")
    if native:
        return native
    try:
        import imageio_ffmpeg
    except ImportError as error:
        raise RuntimeError("Rendering an MP4 needs ffmpeg or the imageio-ffmpeg Python package.") from error
    return imageio_ffmpeg.get_ffmpeg_exe()


def render(
    bundle: dict, out: Path, *, width: int = 1280, height: int = 720, fps: int = 24,
    start: float = 0, duration: float | None = None, still: bool = False, voice_dir: Path | None = None,
) -> None:
    film, stages = bundle["film"], bundle["stages"]
    shots = film["shots"]
    seconds = film["duration_ms"] / 1_000
    if not math.isfinite(start) or not 0 <= start < seconds:
        raise ValueError(f"Start must be inside the cut (0–{seconds:.2f} seconds).")
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise ValueError("Duration must be greater than zero.")
    if voice_dir is not None and not voice_dir.is_dir():
        raise ValueError("Voice directory does not exist.")
    if not 160 <= width <= 2560 or not 90 <= height <= 1440 or width % 2 or height % 2 or not 6 <= fps <= 60:
        raise ValueError("Use an even frame size between 160×90 and 2560×1440, and a frame rate between 6 and 60.")
    if width < height:
        stages = [{**stage, "fov": max(stage["fov"], 42 if stage["camera"] in {"clock", "insert"} else 54)}
                  for stage in stages]
        bundle = {**bundle, "stages": stages}
    starts = [shot["start_ms"] for shot in shots]
    mode = source_label(film["source"], still=still)
    out.parent.mkdir(parents=True, exist_ok=True)
    raster = RasterBuffer(width, height)

    with _projector(bundle) as project:
        def picture(timestamp: float):
            clock = timestamp * 1_000
            shot = shots[max(0, bisect_right(starts, clock) - 1)]
            stage = stages[shot["event_index"]]
            progress = min(1., (clock - shot["start_ms"]) / shot["duration_ms"])
            screen = project(shot["event_index"], progress, width, height)
            return paint(screen, stage, shot, progress, width, height, mode, raster)

        if still:
            picture(start).save(out)
            return
        span = min(seconds - start, duration) if duration is not None else seconds - start
        frames = math.ceil(span * fps)
        with tempfile.TemporaryDirectory(prefix="loopday-video-", dir=out.parent) as folder:
            audio = Path(folder) / "score.wav"
            video = Path(folder) / "cut.mp4"
            render_audio(film, audio, start_seconds=start, seconds=span, voice_dir=voice_dir)
            command = [
                _ffmpeg(), "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{width}x{height}", "-framerate", str(fps), "-i", "pipe:0", "-i", str(audio),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "112k", "-movflags", "+faststart", str(video),
            ]
            with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
                try:
                    for index in range(frames):
                        process.stdin.write(picture(start + index / fps).tobytes())
                finally:
                    process.stdin.close()
                if process.wait():
                    raise RuntimeError("ffmpeg failed to encode the cut.")
            video.replace(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=Path("runs/preflight/run.json"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--start", type=float, default=0, help="Start at this many seconds into the film")
    parser.add_argument("--duration", type=float, help="Render up to this many seconds")
    parser.add_argument("--seconds", type=float, default=94, help="Target length of the complete edit")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--teaser", action="store_true", help="Use the paired mornings and piano beat for a short promo cut")
    parser.add_argument("--captions", type=Path, help="Write companion subtitles to an .srt or .vtt file")
    parser.add_argument("--voice-dir", type=Path, help="Mix optional licensed speech recordings named by event ID (.wav)")
    args = parser.parse_args()
    if args.out.suffix.lower() not in {".png", ".mp4"}:
        parser.error("Use an .mp4 filename for a clip or a .png filename for a still.")
    try:
        run = json.loads(args.run.read_text(encoding="utf-8"))
        bundle = build_bundle(run, seconds=args.seconds)
        if args.teaser:
            bundle["film"] = build_teaser(bundle["film"], bundle["run"]["events"])
        render(bundle, args.out, width=args.width, height=args.height, fps=args.fps, start=args.start,
               duration=args.duration, still=args.out.suffix.lower() == ".png", voice_dir=args.voice_dir)
        if args.captions:
            if args.captions.suffix.lower() not in {".srt", ".vtt"}:
                raise ValueError("Use .srt or .vtt for the subtitle file.")
            if args.start or args.duration is not None or args.out.suffix.lower() != ".mp4":
                raise ValueError("Companion subtitles require the full film or teaser export.")
            args.captions.parent.mkdir(parents=True, exist_ok=True)
            args.captions.write_text(subtitles(bundle["film"], vtt=args.captions.suffix.lower() == ".vtt"), encoding="utf-8")
    except (ImportError, OSError, ValueError, RuntimeError, WaveError) as error:
        parser.error(str(error))
    print(args.out)


if __name__ == "__main__":
    main()
