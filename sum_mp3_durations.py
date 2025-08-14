#!/usr/bin/env python3
"""
Sum durations of all MP3 files in a directory and print each file's duration.

Usage:
  python sum_mp3_durations.py            # scans ./output by default
  python sum_mp3_durations.py --dir output

Requires: mutagen
Optional fallback: ffprobe (from ffmpeg) for files mutagen can't parse
"""
import argparse
from pathlib import Path
import sys
import shutil
import subprocess
from typing import Tuple

try:
    from mutagen import File as MutagenFile
except Exception:
    MutagenFile = None


def format_seconds(seconds: float) -> str:
    if seconds is None:
        return "unknown"
    total_ms = int(round(seconds * 1000))
    hrs, rem = divmod(total_ms, 3600_000)
    mins, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{ms:03d}"
    return f"{mins:02d}:{secs:02d}.{ms:03d}"


def _duration_via_mutagen(path: Path) -> float:
    if MutagenFile is None:
        raise RuntimeError(
            "mutagen is not available. Please install it (pip install mutagen)."
        )
    audio = MutagenFile(str(path))
    length = None
    try:
        if audio is not None and hasattr(audio, "info") and audio.info is not None:
            length = getattr(audio.info, "length", None)
    except Exception:
        length = None
    return float(length) if length else 0.0


def _duration_via_ffprobe(path: Path) -> float:
    """Try to get duration using ffprobe. Returns 0.0 if unavailable/failed."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return 0.0
    # Try stream duration first
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
        if out:
            try:
                val = float(out.splitlines()[0])
                if val > 0:
                    return val
            except ValueError:
                pass
    except Exception:
        pass
    # Fallback to format duration
    cmd2 = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        out = subprocess.check_output(cmd2, stderr=subprocess.STDOUT, text=True).strip()
        if out:
            try:
                val = float(out.splitlines()[0])
                return val if val > 0 else 0.0
            except ValueError:
                return 0.0
    except Exception:
        return 0.0


def get_mp3_duration_seconds(path: Path) -> Tuple[float, str]:
    """
    Returns (seconds, source), where source indicates which method was used: 'mutagen', 'ffprobe', or 'unknown'.
    """
    # First try mutagen
    dur = 0.0
    source = "mutagen"
    try:
        dur = _duration_via_mutagen(path)
    except Exception:
        dur = 0.0
    # Fallback to ffprobe when mutagen fails or returns 0
    if dur <= 0.0005:
        ff_dur = _duration_via_ffprobe(path)
        if ff_dur > 0.0005:
            return ff_dur, "ffprobe"
        # keep 0 duration
        return 0.0, "unknown"
    return dur, source


def main():
    parser = argparse.ArgumentParser(description="Sum durations of MP3 files in a directory")
    parser.add_argument("--dir", dest="directory", default="output", help="Directory containing .mp3 files (default: output)")
    parser.add_argument("--pattern", default="*.mp3", help="Glob pattern to match files (default: *.mp3)")
    args = parser.parse_args()

    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        print(f"Error: directory not found: {directory}")
        sys.exit(1)

    files = sorted(directory.glob(args.pattern))
    if not files:
        print(f"No files matched pattern '{args.pattern}' in {directory}")
        sys.exit(0)

    total_seconds = 0.0
    print(f"Scanning {len(files)} file(s) in {directory} matching '{args.pattern}':")

    for f in files:
        try:
            dur, source = get_mp3_duration_seconds(f)
            total_seconds += dur
            extra = f" (via {source})" if source != "mutagen" else ""
            print(f"- {f.name}: {format_seconds(dur)}{extra}")
        except Exception as e:
            print(f"- {f.name}: error reading duration ({e})")

    print("\nTotal duration:")
    print(f"= {format_seconds(total_seconds)} ({total_seconds:.3f} seconds)")

    # Helpful hint if everything came back 0
    if total_seconds <= 0.0005:
        print("Note: All durations are zero or unknown. If files are playable, try installing ffmpeg to enable the ffprobe fallback: 'brew install ffmpeg' or see https://ffmpeg.org/download.html")


if __name__ == "__main__":
    main()
