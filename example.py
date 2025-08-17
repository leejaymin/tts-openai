#!/usr/bin/env python3
"""
Example script demonstrating how to use the tts_openai module programmatically.
"""

import os
from tts_openai import process_presentation, text_to_speech

def main():
    # Set your OpenAI API key
    # Replace with your actual API key or set it as an environment variable
    os.environ["OPENAI_API_KEY"] = ""


    # Example 1: Process an entire presentation
    print("Example 1: Processing an entire presentation")
    process_presentation(
        input_file="sample_presentation.txt",
        output_dir="example_output",
        voice="onyx",  # Male voice
        speed=1.25,
    )
    
    # Example 2: Convert a single text to speech
    print("\nExample 2: Converting a single text to speech")
    single_text = """
    Thank you for attending my presentation. I hope you found it informative.
    If you have any questions, please feel free to ask.
    """
    
    # Create output directory if it doesn't exist
    os.makedirs("example_output", exist_ok=True)
    
    # Convert the text to speech
    text_to_speech(
        text=single_text,
        output_file="example_output/thank_you.mp3",
        voice="onyx",  # Male voice
        speed=0.9,
    )
    
    print("\nExamples completed. Check the 'example_output' directory for the generated audio files.")

if __name__ == "__main__":
    main()