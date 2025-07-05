#!/usr/bin/env python3
"""
Main entry point for yt_transcriber batch processor.
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.batch_processor import main

if __name__ == "__main__":
    main()
