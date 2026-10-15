"""Make a 9:16 Reels video from a still image (slow cinematic pan + fades), using ffmpeg.

Optional extras: a sequential text overlay (--text) and original generated music (--music).
Music is synthesised with numpy only, so there is no copyrighted material.
"""
from __future__ import annotations

import subprocess
import tempfile
import wave
from pathlib import Path

W, H = 1080, 1920
FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF",
    "/Library/Fonts", "/System/Library/Fonts/Supplemental", "~/Library/Fonts",
    "/opt/homebrew/share/fonts", "/usr/local/share/fonts",
]
FONT_FILES = {"italic": "DejaVuSerif-Italic.ttf", "bold": "DejaVuSerif-BoldItalic.ttf"}
FONT_NAMES = {"italic": "DejaVu Serif:style=Italic", "bold": "DejaVu Serif:style=Bold Italic"}

LINE_SIZE, EMPHASIS_SIZE = 46, 72
LINE_STARTS = (0.5, 2.3, 4.1)   # seconds; further lines continue every 1.8 s
EMPHASIS_START = 6.0
FADE = 0.8
MAX_TEXT_W = int(W * 0.84)       # keeps a ~86 px margin on both sides
BOX_Y, BOX_H = 0.10, 0.28        # fractions of frame height


# --------------------------------------------------------------------- text layout
def find_font(kind: str) -> str | None:
    for d in FONT_DIRS:
        p = Path(d).expanduser() / FONT_FILES[kind]
        if p.exists():
            return str(p)
    return None


def _measurer(kind: str):
    """Return f(text, size) -> pixel width. Uses Pillow with the real font when possible."""
    path = find_font(kind)
    try:
        from PIL import ImageFont
        if path:
            cache: dict[int, object] = {}

            def measure(text: str, size: int) -> float:
                f = cache.setdefault(size, ImageFont.truetype(path, size))
                return f.getlength(text)
            return measure
    except ImportError:
        pass
    return lambda text, size: 0.55 * size * len(text)  # conservative estimate


def wrap_text(text: str, size: int, measure, max_w: int) -> list[str]:
    """Greedy word wrap by measured width."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and measure(trial, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [""]


def layout_text(lines: list[str], emphasis: str | None, box_h: float) -> list[dict]:
    """Wrap and, if needed, shrink fonts so every piece fits inside the width and the dark box.

    Returns a list of items: {text, kind, size, y, start} (one per visual line).
    """
    m_it, m_bd = _measurer("italic"), _measurer("bold")
    blocks = [(t, "italic", LINE_SIZE, LINE_STARTS[i] if i < len(LINE_STARTS) else LINE_STARTS[-1] + 1.8 * (i - 2))
              for i, t in enumerate(l for l in lines if l.strip())]
    if emphasis and emphasis.strip():
        blocks.append((emphasis, "bold", EMPHASIS_SIZE, EMPHASIS_START))
    if not blocks:
        return []

    pad = 24
    for scale in [s / 100 for s in range(100, 39, -4)]:
        items, y = [], pad
        for text, kind, base, start in blocks:
            size = max(16, int(base * scale))
            vis = wrap_text(text, size, m_bd if kind == "bold" else m_it, MAX_TEXT_W)
            lh = int(size * 1.25)
            for v in vis:
                items.append({"text": v, "kind": kind, "size": size, "y": y, "start": start})
                y += lh
            y += int(size * 0.5)  # gap between blocks
        if y - int(blocks[-1][2] * scale * 0.5) + pad <= box_h:
            return items
    return items  # smallest scale; best effort


def _esc_path(p: str) -> str:
    return p.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def text_filters(items: list[dict], tmpdir: Path, box_top: float) -> list[str]:
    """drawtext filters with textfile= (safe for Turkish characters and apostrophes)."""
    out = []
    for i, it in enumerate(items):
        tf = tmpdir / f"line{i}.txt"
        tf.write_text(it["text"], encoding="utf-8")
        font = find_font(it["kind"])
        font_opt = f"fontfile='{_esc_path(font)}'" if font else f"font='{FONT_NAMES[it['kind']]}'"
        s = it["start"]
        alpha = f"if(lt(t,{s}),0,if(lt(t,{s + FADE}),(t-{s})/{FADE},1))"
        out.append(
            f"drawtext={font_opt}:textfile='{_esc_path(str(tf))}':fontsize={it['size']}:"
            f"fontcolor=white:shadowcolor=black@0.6:shadowx=2:shadowy=2:"
            f"x=(w-text_w)/2:y={int(box_top + it['y'])}:alpha='{alpha}'"
        )
    return out


# --------------------------------------------------------------------- ffmpeg commands
def build_video_cmd(image: Path, out: Path, seconds: int, direction: str,
                    lines: list[str] | None, emphasis: str | None, tmpdir: Path) -> list[str]:
    x_expr = (f"(iw-{W})*(0.4+0.6*t/{seconds})" if direction == "right"
              else f"(iw-{W})*(1-0.6*t/{seconds})")
    chain = [
        "scale=-2:2112",  # a bit taller than 1920 so we can also drift vertically
        f"crop={W}:{H}:x='{x_expr}':y='(ih-{H})*(0.5-0.5*t/{seconds})'",
    ]
    items = layout_text(lines or [], emphasis, H * BOX_H)
    if items:
        chain.append(f"drawbox=x=0:y=ih*{BOX_Y}:w=iw:h=ih*{BOX_H}:color=black@0.28:t=fill")
        chain += text_filters(items, tmpdir, H * BOX_Y)
    chain += [f"fade=t=in:st=0:d={FADE}", f"fade=t=out:st={seconds - FADE}:d={FADE}", "format=yuv420p"]
    return [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", "30", "-t", str(seconds), "-i", str(image),
        "-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", ",".join(chain), "-r", "30",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
        str(out),
    ]


def build_mux_cmd(video: Path, wav: Path, out: Path) -> list[str]:
    return ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav),
            "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", str(out)]


def make_reel(image: Path, out: Path, seconds: int = 10, direction: str = "right",
              lines: list[str] | None = None, emphasis: str | None = None,
              music: bool = False) -> Path:
    """Pan slowly across the image inside a 1080x1920 frame. Always has an audio track
    (silent unless music=True), since some Reels uploads are rejected without one."""
    image, out = Path(image), Path(out)
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        target = tmp / "video.mp4" if music else out
        subprocess.run(build_video_cmd(image, target, seconds, direction, lines, emphasis, tmp), check=True)
        if music:
            wav = tmp / "music.wav"
            write_wav(wav, make_music(seconds))
            subprocess.run(build_mux_cmd(target, wav, out), check=True)
    return out


# --------------------------------------------------------------------- music (numpy only)
SR = 44100
# Am - F - C - G, 2.5 s per chord (MIDI notes: bass, then 3 pad voices)
CHORDS = [(45, [57, 60, 64]), (41, [57, 60, 65]), (48, [55, 60, 64]), (43, [55, 59, 62])]
PENTA = [69, 72, 74, 76, 79, 81]  # A minor pentatonic: A4 C5 D5 E5 G5 A5
CHORD_SECONDS = 2.5


def _hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def make_music(seconds: float, seed: int = 7):
    """Return a (n, 2) float array in [-0.6, 0.6]: pad + pluck melody + delay reverb."""
    import numpy as np

    n = int(seconds * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    left, right = np.zeros(n), np.zeros(n)

    # Pad: detuned sines with soft attack, overlapping chords
    for k in range(int(np.ceil(seconds / CHORD_SECONDS))):
        bass, notes = CHORDS[k % len(CHORDS)]
        t0 = k * CHORD_SECONDS
        i0, i1 = int(t0 * SR), min(n, int((t0 + CHORD_SECONDS + 0.8) * SR))
        if i0 >= n:
            break
        tt = t[i0:i1] - t0
        env = np.minimum(1, tt / 0.9) * np.minimum(1, np.maximum(0, (CHORD_SECONDS + 0.8 - tt) / 0.8))
        for j, m in enumerate([bass] + notes):
            amp = 0.5 if j == 0 else 0.22
            for detune, pan in ((-0.07, 0.0), (0.07, 1.0)):
                f = _hz(m + detune)
                v = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)
                v *= amp * env
                left[i0:i1] += v * (1 - 0.4 * pan)
                right[i0:i1] += v * (0.6 + 0.4 * pan)

    # Pluck melody: eighth-note grid (0.625 s), some rests, decaying harmonic tone
    step = CHORD_SECONDS / 4
    idx = 2
    for k in range(int(seconds / step)):
        if k % 4 in (1,) or rng.random() < 0.25:
            continue
        idx = int(np.clip(idx + rng.integers(-2, 3), 0, len(PENTA) - 1))
        f = _hz(PENTA[idx])
        i0 = int(k * step * SR)
        i1 = min(n, i0 + int(1.6 * SR))
        tt = t[i0:i1] - t[i0]
        env = np.exp(-tt * 3.2) * np.minimum(1, tt / 0.005)
        v = (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 6)) * 0.35 * env
        pan = 0.3 + 0.4 * rng.random()
        left[i0:i1] += v * (1 - pan)
        right[i0:i1] += v * pan

    mix = np.stack([left, right], axis=1)

    # Simple delay-reverb: feedback comb taps, slightly different per channel
    wet = np.zeros_like(mix)
    for ch, delays in enumerate(((0.23, 0.37, 0.53), (0.29, 0.41, 0.61))):
        for d, g in zip(delays, (0.35, 0.28, 0.2)):
            ds = int(d * SR)
            for rep in range(1, 4):
                off = ds * rep
                if off >= n:
                    break
                wet[off:, ch] += mix[: n - off, ch] * (g ** rep) * 1.6
    mix = mix + wet

    # Fades and normalisation to peak 0.6
    fin, fout = int(1.0 * SR), int(1.2 * SR)
    env = np.ones(n)
    env[:fin] = np.linspace(0, 1, fin)
    env[-fout:] *= np.linspace(1, 0, fout)
    mix *= env[:, None]
    peak = float(np.max(np.abs(mix))) or 1.0
    return mix * (0.6 / peak)


def write_wav(path: Path, data) -> None:
    import numpy as np

    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
