#!/usr/bin/env python3
"""
Batch-process multiple YouTube videos through the pipeline.
Reads URLs from a text file and processes each one.
"""

import re
import sys
from pathlib import Path

from .config import YT_COOKIES_FROM_BROWSER
from .pipeline import (
    download_audio,
    extract_video_id,
    gpt_action,
    transcribe,
)


def extract_urls_from_file(file_path: str) -> list[str]:
    """Extract unique YouTube URLs from a text file, preserving order."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    url_pattern = r"https://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+"
    urls = re.findall(url_pattern, content)

    unique_urls: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


def read_prompt_from_file(file_path: str) -> str:
    """Read a GPT prompt from a text file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def main() -> None:
    """Process all URLs from config/urls.txt through the pipeline."""
    urls_file = Path("config/urls.txt")
    prompt_file = Path("config/prompt.txt")

    if not urls_file.exists():
        print(f"Error: {urls_file} not found.")
        sys.exit(1)

    if not prompt_file.exists():
        print(f"Error: {prompt_file} not found. Using default prompt.")
        prompt = "Summarize the transcript"
    else:
        prompt = read_prompt_from_file(str(prompt_file))

    urls = extract_urls_from_file(str(urls_file))

    if not urls:
        print("No YouTube URLs found in the input file.")
        sys.exit(1)

    print(f"Found {len(urls)} unique YouTube URLs.")
    print(f"Using prompt: {prompt}")
    print()

    for i, url in enumerate(urls, 1):
        video_id = extract_video_id(url)
        print(f"Processing video {i}/{len(urls)}: {url} (ID: {video_id})")

        try:
            audio = download_audio(
                url,
                cookies_from_browser=YT_COOKIES_FROM_BROWSER,
            )
            transcript_path = transcribe(audio, video_id)
            gpt_action(transcript_path, prompt, video_id)
            print(f"Successfully processed: {url}")
        except Exception as e:
            print(f"Error processing {url}: {e}")

        print("-" * 80)

    print("All videos processed.")


if __name__ == "__main__":
    main()
