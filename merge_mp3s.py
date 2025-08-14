#!/usr/bin/env python3
"""
Merge MP3 files generated per slide into a single MP3.

Usage examples:
  python merge_mp3s.py                           # merge all *.mp3 in ./output into ./output/merged_slides.mp3
  python merge_mp3s.py --dir output --slides 1,3-5,8 --out output/my_merged.mp3
  python merge_mp3s.py --dir output --overwrite  # overwrite existing output file if present

Notes:
- Files are read in filename order by default. If --slides is provided, only files whose
  names match 'slide_{number}.mp3' will be considered, and they will be ordered by the slide number.
- Requires ffmpeg to be installed and available on PATH. The script first attempts a stream copy
  (no re-encoding). If that fails (e.g., due to mismatched parameters), it falls back to re-encoding.
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set


def _parse_slides_option(slides_opt: Optional[str], max_upper_bound_hint: Optional[int] = None) -> Set[int]:
    """
    Parse a slides selection string like "1,3-5,7" into a set of 1-based indices.
    If slides_opt is falsy, returns an empty set to indicate "no filtering".

    This version is independent from tts_openai.py to avoid importing openai at runtime.
    """
    if not slides_opt:
        return set()

    selected: Set[int] = set()
    invalid_tokens: List[str] = []

    for token in slides_opt.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            try:
                start_s, end_s = token.split("-", 1)
                start = int(start_s.strip())
                end = int(end_s.strip())
                if start > end:
                    start, end = end, start
                for i in range(start, end + 1):
                    if i >= 1:
                        selected.add(i)
                    else:
                        invalid_tokens.append(str(i))
            except ValueError:
                invalid_tokens.append(token)
        else:
            try:
                idx = int(token)
                if idx >= 1:
                    selected.add(idx)
                else:
                    invalid_tokens.append(token)
            except ValueError:
                invalid_tokens.append(token)

    if invalid_tokens:
        print(f"Warning: invalid slide tokens ignored: {', '.join(invalid_tokens)}")

    # Best-effort diagnostic if provided
    if max_upper_bound_hint is not None and any(i > max_upper_bound_hint for i in selected):
        print(
            f"Warning: some selected slides exceed available upper bound {max_upper_bound_hint}. They will be ignored."
        )

    return selected


def _extract_slide_num(path: Path) -> Optional[int]:
    """Return the integer N for filenames like 'slide_N.mp3' (with any leading zeros)."""
    m = re.match(r"^slide_(\d+)\.mp3$", path.name, re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _collect_files(directory: Path, pattern: str, slides_filter: Set[int]) -> List[Path]:
    """
    Collect files from directory by pattern. If slides_filter is empty, return all
    files sorted by filename. If slides_filter is non-empty, return only files whose
    names match 'slide_{num}.mp3' and whose number is in slides_filter, sorted by that number.
    """
    files = sorted(directory.glob(pattern))

    if not slides_filter:
        return files

    # Filter strictly by slide number from the filename
    by_num = []
    for f in files:
        num = _extract_slide_num(f)
        if num is not None and num in slides_filter:
            by_num.append((num, f))

    by_num.sort(key=lambda t: t[0])
    return [f for _, f in by_num]


def _write_ffmpeg_concat_list(inputs: Sequence[Path]) -> Path:
    """
    Write a temporary file list for ffmpeg concat demuxer.
    Each line has the form: file '/absolute/path'
    Returns the path to the temp file.
    """
    tmp = tempfile.NamedTemporaryFile(prefix="ffconcat_", suffix=".txt", delete=False, mode="w", encoding="utf-8")
    try:
        for p in inputs:
            # Use absolute path; keep quoting simple for typical POSIX paths
            abspath = str(p.resolve())
            tmp.write(f"file '{abspath}'\n")
    finally:
        tmp.flush()
        tmp.close()
    return Path(tmp.name)


def _run_ffmpeg_concat(inputs: Sequence[Path], output: Path, overwrite: bool) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("Error: ffmpeg not found on PATH. Please install ffmpeg (https://ffmpeg.org/download.html).")
        return False

    if len(inputs) == 1:
        # Fast-path: single file -> copy
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            if output.exists() and not overwrite:
                print(f"Error: output already exists: {output}. Use --overwrite to replace it.")
                return False
            shutil.copyfile(str(inputs[0]), str(output))
            return True
        except Exception as e:
            print(f"Error copying single input to output: {e}")
            return False

    list_file = _write_ffmpeg_concat_list(inputs)
    overwrite_flag = "-y" if overwrite else "-n"

    try:
        # Attempt stream copy (no re-encode)
        cmd_copy = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            overwrite_flag,
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output),
        ]
        output.parent.mkdir(parents=True, exist_ok=True)
        print(f"Merging {len(inputs)} files (stream copy)...")
        res = subprocess.run(cmd_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and output.exists() and output.stat().st_size > 0:
            return True

        # Fallback to re-encoding
        cmd_reencode = [
            ffmpeg,
            "-hide_banner",
            "-loglevel", "error",
            overwrite_flag,
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            str(output),
        ]
        print("Stream copy failed or produced empty output. Retrying with re-encode...")
        res2 = subprocess.run(cmd_reencode, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res2.returncode == 0 and output.exists() and output.stat().st_size > 0:
            return True

        # If still failing, show a concise error
        print("Error: ffmpeg failed to merge files.")
        if res.stderr:
            print("- copy stderr:")
            print(res.stderr.strip())
        if res2.stderr:
            print("- reencode stderr:")
            print(res2.stderr.strip())
        return False

    finally:
        try:
            list_file.unlink(missing_ok=True)
        except Exception:
            pass


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Merge slide MP3 files into a single MP3")
    parser.add_argument("--dir", dest="directory", default="output", help="Directory containing .mp3 files (default: output)")
    parser.add_argument("--pattern", default="*.mp3", help="Glob pattern to match files (default: *.mp3)")
    parser.add_argument("--slides", default=None, help="Slide selection like '1', '2,4', '3-5', '1,3-4,7'. If omitted, merge all files.")
    parser.add_argument("--out", dest="output", default=None, help="Output MP3 path (default: <dir>/merged_slides.mp3)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output file if it already exists")

    args = parser.parse_args(args=list(argv) if argv is not None else None)

    directory = Path(args.directory)
    if not directory.exists() or not directory.is_dir():
        print(f"Error: directory not found: {directory}")
        return 1

    slides_filter = _parse_slides_option(args.slides)

    files = _collect_files(directory, args.pattern, slides_filter)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = directory / "merged_slides.mp3"

    # Exclude the output file itself if it already exists in the input list
    try:
        out_resolved = output_path.resolve()
        files = [f for f in files if f.resolve() != out_resolved]
    except Exception:
        files = [f for f in files if str(f) != str(output_path)]

    if not files:
        if slides_filter:
            print(
                "No files matched the slide selection in the specified directory.\n"
                "- Ensure files are named like 'slide_01.mp3', 'slide_02.mp3', ... and exist in the directory."
            )
        else:
            print(f"No files matched pattern '{args.pattern}' in {directory}")
        return 2

    print("Files to merge (in order):")
    for f in files:
        print(f"- {f.name}")

    ok = _run_ffmpeg_concat(files, output_path, overwrite=args.overwrite)
    if not ok:
        return 3

    print(f"Merged MP3 saved to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())