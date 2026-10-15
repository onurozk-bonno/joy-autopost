"""Make a 9:16 Reels video from a still image (slow cinematic pan + fades), using ffmpeg."""
from __future__ import annotations

import subprocess
from pathlib import Path


def make_reel(image: Path, out: Path, seconds: int = 10, direction: str = "right") -> Path:
    """Pan slowly across the image inside a 1080x1920 frame. Adds a silent audio track,
    since some Reels uploads are rejected without one."""
    # Scale so the height is 1920, then move a 1080px-wide window across it.
    x_expr = (f"(iw-1080)*(0.4+0.6*t/{seconds})" if direction == "right"
              else f"(iw-1080)*(1-0.6*t/{seconds})")
    vf = (
        "scale=-2:2112,"  # a bit taller than 1920 so we can also drift vertically
        f"crop=1080:1920:x='{x_expr}':y='(ih-1920)*(0.5-0.5*t/{seconds})',"
        f"fade=t=in:st=0:d=0.8,fade=t=out:st={seconds - 0.8}:d=0.8,format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", "30", "-t", str(seconds), "-i", str(image),
        "-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-vf", vf, "-r", "30",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out
