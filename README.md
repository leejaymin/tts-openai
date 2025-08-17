# OpenAI Text-to-Speech for Presentations

This tool converts presentation scripts into speech using OpenAI's Text-to-Speech API. It's designed to process presentation scripts where each slide's content is clearly marked, and convert them into separate audio files for each slide.

## Features

- Converts English text to natural-sounding speech using OpenAI's TTS API
- Uses a male voice by default (customizable)
- Automatically splits presentation scripts by slides
- Saves each slide as a separate audio file
- Customizable output directory and voice options
- Optional speech speed control via ffmpeg (pitch-preserving)

## Requirements

- Python 3.7+
- OpenAI API key
- Required Python packages:
  - openai
- Optional (for speed control):
  - ffmpeg (adds pitch-preserving speed change using atempo)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/TTS-openAI.git
   cd TTS-openAI
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

   Or install the OpenAI package directly:
   ```
   pip install openai>=1.0.0
   ```

3. Set up your OpenAI API key:
   - Option 1: Set it as an environment variable:
     ```
     export OPENAI_API_KEY="your-api-key"
     ```
   - Option 2: Pass it as a command-line argument (see Usage section)

## Usage

### Command-line Usage

#### Basic Usage

```
python tts_openai.py sample_presentation.txt
```

This will:
1. Read the presentation script from `sample_presentation.txt`
2. Split it into slides
3. Convert each slide to speech using the default male voice (onyx)
4. Save the audio files in the `output` directory

#### Advanced Usage

```
python tts_openai.py sample_presentation.txt --output-dir my_audio_files --voice alloy --api-key "your-api-key"
```

#### Control Speech Speed (requires ffmpeg)

```
python tts_openai.py sample_presentation.txt --speed 1.25
```

- `--speed` sets a playback speed multiplier, preserving pitch via ffmpeg's atempo filter.
- Examples: `0.8` (slower), `1.0` (default), `1.25`, `1.5`, `2.0`.
- If ffmpeg is not installed, the script prints a warning and skips speed adjustment.

### Programmatic Usage

You can also use the functions from the `tts_openai.py` module in your own Python scripts. See `example.py` for a complete example:

```python
from tts_openai import process_presentation, text_to_speech

# Process an entire presentation (25% faster)
process_presentation(
    input_file="sample_presentation.txt",
    output_dir="example_output",
    voice="onyx",
    speed=1.25,
)

# Convert a single text to speech (10% slower)
text_to_speech(
    text="Thank you for attending my presentation.",
    output_file="example_output/thank_you.mp3",
    voice="onyx",
    speed=0.9,
)
```

To run the example:

```
python example.py
```

Note: Remember to set your OpenAI API key before running the example.

### Command-line Options

- `input_file`: Path to the input text file containing the presentation script (required)
- `--output-dir`: Directory to save the audio files (default: 'output')
- `--voice`: Voice to use (default: 'onyx' - male voice)
  - Available voices: alloy, echo, fable, onyx, nova, shimmer
- `--api-key`: OpenAI API key (alternatively, set the OPENAI_API_KEY environment variable)
- `--speed`: Playback speed multiplier (default: `1.0`). Requires ffmpeg for pitch-preserving change.

## Input Format

The script expects the input text file to have clear markers for each slide. For example:

```
Slide 1: Introduction
This is the content for slide 1.

Slide 2: Methods
This is the content for slide 2.
```

Alternatively, you can separate slides with "---" markers:

```
Introduction
This is the content for slide 1.
---
Methods
This is the content for slide 2.
```

## Output

The script will create audio files named `slide_01.mp3`, `slide_02.mp3`, etc., in the specified output directory.

## Utilities

### Sum MP3 durations in output directory
You can list each MP3 duration and the total duration with the helper script:

```
python sum_mp3_durations.py --dir output
```

- Default directory is `output` if `--dir` is omitted.
- Requires dependency: `mutagen` (already listed in requirements.txt). Install with:
  ```
  pip install -r requirements.txt
  ```
- If durations print as 00:00.000 but the files are playable, install ffmpeg to enable the ffprobe fallback used by the script:
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - Windows (Chocolatey): `choco install ffmpeg` or download from https://ffmpeg.org/download.html

Example output:
```
Scanning 14 file(s) in output matching '*.mp3':
- slide_01.mp3: 00:32.415
- slide_02.mp3: 00:45.120
...

Total duration:
= 11:23.765 (683.765 seconds)
```

## License

[MIT License](LICENSE)

## Speech-to-Text (Whisper)

Transcribe audio files to text using OpenAI Whisper (`whisper-1`).

### CLI Usage

- Basic (prints to stdout):

```
python stt_openai.py /absolute/path/to/audio.mp3 --language ko
```

- Save to a file:

```
python stt_openai.py /absolute/path/to/audio.mp3 --language ko --output output.txt
```

- Get SRT subtitles:

```
python stt_openai.py /absolute/path/to/audio.mp3 --language ko --response-format srt --output output.srt
```

- Supported `--response-format` values: `text` (default), `srt`, `vtt`, `verbose_json`, `json`

Make sure your OpenAI API key is available via environment variable:

```
export OPENAI_API_KEY="your-api-key"
```
