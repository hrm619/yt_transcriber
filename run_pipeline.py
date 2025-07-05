#!/usr/bin/env python3
"""
Main entry point for yt_transcriber pipeline.
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from pipeline import main

if __name__ == "__main__":
    main()
