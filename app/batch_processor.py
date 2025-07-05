#!/usr/bin/env python3
"""
Process multiple YouTube videos using yt_whisper_pipeline.py
This script extracts URLs from a text file and runs each through the pipeline.
"""

import re
import subprocess
import sys
import hashlib
from pathlib import Path

# Function to extract URLs from text file
def extract_urls_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all YouTube URLs in the file
    url_pattern = r'https://www\.youtube\.com/watch\?v=[a-zA-Z0-9_-]+'
    urls = re.findall(url_pattern, content)
    
    # Remove duplicates while preserving order
    unique_urls = []
    seen = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    return unique_urls

# Function to extract YouTube video ID from URL
def extract_video_id(url):
    match = re.search(r'v=([a-zA-Z0-9_-]+)', url)
    return match.group(1) if match else None

# Function to read prompt from text file
def read_prompt_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

def main():
    # Paths to input files
    urls_file = Path("config/urls.txt")
    prompt_file = Path("config/prompt.txt")
    
    if not urls_file.exists():
        print(f"Error: {urls_file} not found.")
        sys.exit(1)
    
    if not prompt_file.exists():
        print(f"Error: {prompt_file} not found. Using default prompt.")
        prompt = "Summarize the transcript"
    else:
        prompt = read_prompt_from_file(prompt_file)
    
    # Extract URLs (now removing duplicates)
    urls = extract_urls_from_file(urls_file)
    
    if not urls:
        print("No YouTube URLs found in the input file.")
        sys.exit(1)
    
    print(f"Found {len(urls)} unique YouTube URLs.")
    print(f"Using prompt: {prompt}")
    print()
    
    # Process each URL
    for i, url in enumerate(urls, 1):
        video_id = extract_video_id(url)
        if not video_id:
            print(f"⚠️ Could not extract video ID from URL: {url}. Skipping.")
            continue
            
        print(f"Processing video {i}/{len(urls)}: {url} (ID: {video_id})")
        
        # Build the command to run yt_whisper_pipeline.py
        cmd = [
            "python", "app/pipeline.py",
            url,
            "--prompt", prompt,
            "--cookies-from-browser", "chrome"  # Change this if needed
        ]
        
        try:
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Successfully processed: {url}")
            else:
                print(f"❌ Error processing: {url}")
                print(f"Error: {result.stderr}")
            
            print("-" * 80)
            
        except Exception as e:
            print(f"❌ Exception while processing {url}: {e}")
            print("-" * 80)
    
    print("All videos processed.")

if __name__ == "__main__":
    main() 