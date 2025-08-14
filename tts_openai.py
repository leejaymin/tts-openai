import os
import argparse
from pathlib import Path
import openai
import re  # 추가: 정규식 모듈을 상단으로 이동


def split_text_by_slides(text):
    """
    Split the input text into sections based on slide indicators.
    Only split on lines that look like slide headers, e.g., 'Slide 2: Title'.
    If no such headers exist, fallback to splitting by lines containing only '---'.
    """
    # 'Slide <number>:' 로 시작하는 헤더 줄만 구분자로 사용 (대소문자 무시)
    header_re = re.compile(r'(?im)^\s*Slide\s+\d+\s*:.*$')
    headers = list(header_re.finditer(text))

    if headers:
        slides = []
        for idx, m in enumerate(headers):
            start = m.end()
            end = headers[idx + 1].start() if idx + 1 < len(headers) else len(text)
            content = text[start:end].strip()
            slides.append(content if content else "")
        # 빈 슬라이드는 유지하여 인덱스가 실제 슬라이드 번호와 최대한 일치하도록 함
        return slides

    # 대체: 줄 전체가 --- 인 곳에서 분할
    parts = re.split(r'(?m)^\s*---\s*$', text)
    return [p.strip() for p in parts if p.strip()]


def _response_to_bytes(resp):
    """
    OpenAI audio.speech.create 응답을 끝까지 읽어 bytes로 변환합니다.
    SDK/전송 방식에 따라 read/iter_bytes/content 등이 다를 수 있어 방어적으로 처리합니다.
    """
    if hasattr(resp, "read") and callable(getattr(resp, "read")):
        return resp.read()
    if hasattr(resp, "iter_bytes") and callable(getattr(resp, "iter_bytes")):
        return b"".join(chunk for chunk in resp.iter_bytes() if chunk)
    if hasattr(resp, "content"):
        return resp.content
    if isinstance(resp, (bytes, bytearray, memoryview)):
        return bytes(resp)
    try:
        return bytes(resp)
    except Exception as e:
        raise TypeError(f"Unsupported response type for audio content: {type(resp)}") from e


def text_to_speech(text, output_file, voice="alloy"):
    """
    Convert text to speech using OpenAI's API.

    Args:
        text (str): The text to convert to speech
        output_file (str): Path to save the audio file
        voice (str): The voice to use (default: alloy, which is a male voice)
                     Options: alloy, echo, fable, onyx, nova, shimmer
    """
    try:
        response = openai.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text
        )

        if hasattr(response, "iter_bytes") and callable(getattr(response, "iter_bytes")):
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "wb") as f:
                for chunk in response.iter_bytes():
                    if chunk:
                        f.write(chunk)
        else:
            audio_bytes = _response_to_bytes(response)
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "wb") as f:
                f.write(audio_bytes)

        print(f"Audio saved to {output_file}")
        return True

    except Exception as e:
        print(f"Error generating speech: {e}")
        return False


def _parse_slides_option(slides_opt: str, total: int):
    """
    '--slides' 옵션 문자열을 파싱하여 1-based 인덱스 집합을 반환.
    예) "1,3-5,7" -> {1,3,4,5,7}
    범위를 벗어난 값은 무시하고 경고 출력.
    """
    if not slides_opt:
        return set(range(1, total + 1))

    selected = set()
    invalid_tokens = []

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
                    if 1 <= i <= total:
                        selected.add(i)
                    else:
                        invalid_tokens.append(str(i))
            except ValueError:
                invalid_tokens.append(token)
        else:
            try:
                idx = int(token)
                if 1 <= idx <= total:
                    selected.add(idx)
                else:
                    invalid_tokens.append(token)
            except ValueError:
                invalid_tokens.append(token)

    if not selected:
        print("Warning: 선택된 슬라이드가 없습니다. 전체 슬라이드를 처리합니다.")
        return set(range(1, total + 1))

    if invalid_tokens:
        print(f"Warning: 잘못된 슬라이드 지정 무시됨: {', '.join(invalid_tokens)}")

    return selected


def process_presentation(input_file, output_dir, voice="onyx", slides_opt: str = None):
    """
    Process a presentation script and convert each slide to speech.

    Args:
        input_file (str): Path to the input text file
        output_dir (str): Directory to save the audio files
        voice (str): The voice to use (default: onyx, which is a male voice)
        slides_opt (str): 특정 슬라이드만 처리하기 위한 선택 문자열 (예: "1,3-5")
                          None이면 전체 슬라이드 처리
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    slides = split_text_by_slides(text)
    if not slides:
        print("No slides found in the input text.")
        return

    total = len(slides)
    print(f"Found {total} slides in the presentation.")

    selected_indices = sorted(_parse_slides_option(slides_opt, total))
    print(f"Processing slides: {', '.join(str(i) for i in selected_indices)}")

    for i in selected_indices:
        slide_text = slides[i - 1]
        if not slide_text.strip():
            continue
        output_file = output_path / f"slide_{i:02d}.mp3"
        print(f"Processing slide {i}...")
        text_to_speech(slide_text, str(output_file), voice)


def main():
    parser = argparse.ArgumentParser(description="Convert presentation slides to speech using OpenAI's API")
    parser.add_argument("input_file", help="Path to the input text file containing the presentation script")
    parser.add_argument("--output-dir", default="output", help="Directory to save the audio files (default: 'output')")
    parser.add_argument("--voice", default="onyx", help="Voice to use (default: 'onyx' - male voice). Options: alloy, echo, fable, onyx, nova, shimmer")
    parser.add_argument("--api-key", help="OpenAI API key (alternatively, set OPENAI_API_KEY environment variable)")
    parser.add_argument("--slides", help='처리할 슬라이드 지정 (예: "1", "2,4", "3-5", "1,3-4,7"). 지정하지 않으면 전체 처리.', default=None)

    args = parser.parse_args()

    if args.api_key:
        openai.api_key = args.api_key
        os.environ["OPENAI_API_KEY"] = args.api_key
    elif "OPENAI_API_KEY" in os.environ:
        openai.api_key = os.environ["OPENAI_API_KEY"]
    else:
        print("Error: OpenAI API key not provided. Please provide it using --api-key or set the OPENAI_API_KEY environment variable.")
        return

    process_presentation(args.input_file, args.output_dir, args.voice, slides_opt=args.slides)


if __name__ == "__main__":
    main()