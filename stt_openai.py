#!/usr/bin/env python3
import os
import argparse
from pathlib import Path
import json
import openai
from typing import Optional


def _normalize_transcription_result(result, response_format: str) -> str:
    """
    Normalize various possible return types from openai.audio.transcriptions.create
    into a string for output. For text format, prefer .text when available.
    """
    # text format usually returns an object with .text
    if response_format == "text":
        if hasattr(result, "text"):
            return result.text
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return str(result)

    # srt/vtt typically return raw string content
    if response_format in ("srt", "vtt"):
        if isinstance(result, str):
            return result
        if hasattr(result, "text") and isinstance(result.text, str):
            return result.text
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return str(result)

    # verbose_json should be JSON-like
    if response_format in ("verbose_json", "json"):
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            # last resort stringification
            return str(result)

    # default fallback
    return str(result)


def transcribe_audio(
    audio_path: str,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    response_format: str = "text",
    temperature: float = 0.0,
) -> str:
    """
    Transcribe an audio file using OpenAI Whisper API (whisper-1).

    Args:
        audio_path: Path to the audio file (e.g., mp3, wav, m4a, webm)
        language: Optional BCP-47 language code, e.g. "ko", "en"
        prompt: Optional hint text for domain-specific terms
        response_format: "text" | "srt" | "vtt" | "verbose_json" | "json"
        temperature: Decoding temperature (default: 0.0)

    Returns:
        String result of the transcription depending on response_format
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    kwargs = {
        "model": "whisper-1",
        "temperature": temperature,
        "response_format": response_format,
    }
    if language:
        kwargs["language"] = language
    if prompt:
        kwargs["prompt"] = prompt

    with open(audio_path, "rb") as f:
        result = openai.audio.transcriptions.create(
            file=f,
            **kwargs,
        )

    return _normalize_transcription_result(result, response_format)


def _infer_default_output_path(input_path: str, response_format: str) -> str:
    stem = Path(input_path).with_suffix("")
    if response_format == "text":
        return f"{stem}.txt"
    if response_format == "srt":
        return f"{stem}.srt"
    if response_format == "vtt":
        return f"{stem}.vtt"
    # verbose_json / json
    return f"{stem}.json"


def transcribe_to_file(
    audio_path: str,
    output_path: Optional[str] = None,
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    response_format: str = "text",
    temperature: float = 0.0,
) -> str:
    """
    Transcribe audio and save to a file. Returns the output file path.
    """
    text = transcribe_audio(
        audio_path=audio_path,
        language=language,
        prompt=prompt,
        response_format=response_format,
        temperature=temperature,
    )
    if not output_path:
        output_path = _infer_default_output_path(audio_path, response_format)

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return str(out_path)


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio to text using OpenAI Whisper (whisper-1)",
    )
    parser.add_argument("audio", help="Path to the input audio file (mp3|wav|m4a|webm)")
    parser.add_argument("--language", default=None, help="Language code (e.g., 'ko', 'en')")
    parser.add_argument("--prompt", default=None, help="Optional domain-specific hint text")
    parser.add_argument(
        "--response-format",
        default="text",
        choices=["text", "srt", "vtt", "verbose_json", "json"],
        help="Output format (default: text)",
    )
    parser.add_argument("--temperature", type=float, default=0.0, help="Decoding temperature (default: 0.0)")
    parser.add_argument("--output", default=None, help="Output file path. If omitted, prints to stdout")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")

    args = parser.parse_args()

    # API key selection aligned with tts_openai.py
    if args.api_key:
        openai.api_key = args.api_key
        os.environ["OPENAI_API_KEY"] = args.api_key
    elif "OPENAI_API_KEY" in os.environ:
        openai.api_key = os.environ["OPENAI_API_KEY"]
    else:
        print(
            "Error: OpenAI API key not provided. Use --api-key or set OPENAI_API_KEY environment variable.")
        return 1

    try:
        if args.output:
            out = transcribe_to_file(
                audio_path=args.audio,
                output_path=args.output,
                language=args.language,
                prompt=args.prompt,
                response_format=args.response_format,
                temperature=args.temperature,
            )
            print(f"Saved transcription to {out}")
        else:
            text = transcribe_audio(
                audio_path=args.audio,
                language=args.language,
                prompt=args.prompt,
                response_format=args.response_format,
                temperature=args.temperature,
            )
            print(text)
        return 0
    except Exception as e:
        print(f"Error during transcription: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())