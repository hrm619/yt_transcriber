#!/usr/bin/env python3
"""
Migration script to reorganize yt_transcriber codebase structure.
This script will:
1. Create new folder structure
2. Move files to appropriate locations
3. Update code references to new paths
4. Create necessary configuration files
"""

import os
import shutil
import sys
from pathlib import Path
import re

def create_directory_structure():
    """Create the new directory structure."""
    print("Creating new directory structure...")
    
    directories = [
        "app",
        "src/yt_transcriber/core",
        "data/raw/audio",
        "data/raw/temp",
        "data/processed/transcripts", 
        "data/processed/summaries",
        "data/archive/backups",
        "data/archive/old",
        "docs/technical",
        "scripts",
        "config",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Created: {directory}/")

def move_core_files():
    """Move and rename core application files."""
    print("\nMoving core application files...")
    
    # Move main pipeline file
    if Path("yt_whisper_pipeline.py").exists():
        shutil.move("yt_whisper_pipeline.py", "app/pipeline.py")
        print("  ✓ Moved: yt_whisper_pipeline.py → app/pipeline.py")
    
    # Move batch processor
    if Path("process_videos.py").exists():
        shutil.move("process_videos.py", "app/batch_processor.py")
        print("  ✓ Moved: process_videos.py → app/batch_processor.py")
    
    # Create __init__.py files
    Path("app/__init__.py").touch()
    Path("src/yt_transcriber/__init__.py").touch()
    Path("src/yt_transcriber/core/__init__.py").touch()
    print("  ✓ Created: __init__.py files")

def move_data_directories():
    """Move data directories to new structure."""
    print("\nMoving data directories...")
    
    # Move downloads to data/raw/audio
    if Path("downloads").exists():
        if Path("data/raw/audio").exists():
            shutil.rmtree("data/raw/audio")
        shutil.move("downloads", "data/raw/audio")
        print("  ✓ Moved: downloads/ → data/raw/audio/")
    
    # Move chunks to data/raw/temp
    if Path("chunks").exists():
        if Path("data/raw/temp").exists():
            shutil.rmtree("data/raw/temp")
        shutil.move("chunks", "data/raw/temp")
        print("  ✓ Moved: chunks/ → data/raw/temp/")
    
    # Move transcripts to data/processed/transcripts
    if Path("transcripts").exists():
        if Path("data/processed/transcripts").exists():
            shutil.rmtree("data/processed/transcripts")
        shutil.move("transcripts", "data/processed/transcripts")
        print("  ✓ Moved: transcripts/ → data/processed/transcripts/")
    
    # Move summaries to data/processed/summaries
    if Path("summaries").exists():
        if Path("data/processed/summaries").exists():
            shutil.rmtree("data/processed/summaries")
        shutil.move("summaries", "data/processed/summaries")
        print("  ✓ Moved: summaries/ → data/processed/summaries/")

def move_archive_data():
    """Move archive and backup data."""
    print("\nMoving archive and backup data...")
    
    # Move backup directory
    if Path("backup").exists():
        if Path("data/archive/backups").exists():
            shutil.rmtree("data/archive/backups")
        shutil.move("backup", "data/archive/backups")
        print("  ✓ Moved: backup/ → data/archive/backups/")
    
    # Move archive directory
    if Path("archive").exists():
        if Path("data/archive/old").exists():
            shutil.rmtree("data/archive/old")
        shutil.move("archive", "data/archive/old")
        print("  ✓ Moved: archive/ → data/archive/old/")
    
    # Move raw data directories to archive
    for dir_name in ["transcripts_raw", "summaries_raw"]:
        if Path(dir_name).exists():
            target = Path("data/archive") / dir_name
            if target.exists():
                shutil.rmtree(target)
            shutil.move(dir_name, target)
            print(f"  ✓ Moved: {dir_name}/ → data/archive/{dir_name}/")

def move_documentation():
    """Move documentation files."""
    print("\nMoving documentation files...")
    
    # Keep README.md in root
    if Path("README.md").exists():
        print("  ✓ Kept: README.md (in root)")
    
    # Move technical documentation
    if Path("yt_chunker.md").exists():
        shutil.move("yt_chunker.md", "docs/technical/chunking_strategy.md")
        print("  ✓ Moved: yt_chunker.md → docs/technical/chunking_strategy.md")

def move_logs_and_outputs():
    """Move log files and outputs."""
    print("\nMoving logs and output files...")
    
    # Move new_outputs content to logs
    if Path("new_outputs").exists():
        for file in Path("new_outputs").iterdir():
            if file.is_file():
                shutil.move(str(file), f"logs/{file.name}")
                print(f"  ✓ Moved: new_outputs/{file.name} → logs/{file.name}")
        Path("new_outputs").rmdir()
        print("  ✓ Removed: new_outputs/")

def create_config_files():
    """Create configuration files."""
    print("\nCreating configuration files...")
    
    # Check for existing urls.txt and prompt.txt in root
    if Path("urls.txt").exists():
        shutil.move("urls.txt", "config/urls.txt")
        print("  ✓ Moved: urls.txt → config/urls.txt")
    else:
        # Create empty urls.txt
        Path("config/urls.txt").write_text("# Add YouTube URLs here, one per line\n")
        print("  ✓ Created: config/urls.txt")
    
    if Path("prompt.txt").exists():
        shutil.move("prompt.txt", "config/prompt.txt")
        print("  ✓ Moved: prompt.txt → config/prompt.txt")
    else:
        # Create default prompt.txt
        Path("config/prompt.txt").write_text("Summarize the transcript in 3 key takeaways.")
        print("  ✓ Created: config/prompt.txt")

def update_pipeline_code():
    """Update the pipeline code to use new paths."""
    print("\nUpdating pipeline code...")
    
    pipeline_file = Path("app/pipeline.py")
    if pipeline_file.exists():
        content = pipeline_file.read_text()
        
        # Update directory paths
        content = re.sub(r'DOWNLOAD_DIR\s*=\s*Path\("downloads"\)', 
                        'DOWNLOAD_DIR = Path("data/raw/audio")', content)
        content = re.sub(r'TRANSCRIPT_DIR\s*=\s*Path\("transcripts"\)', 
                        'TRANSCRIPT_DIR = Path("data/processed/transcripts")', content)
        content = re.sub(r'SUMMARY_DIR\s*=\s*Path\("summaries"\)', 
                        'SUMMARY_DIR = Path("data/processed/summaries")', content)
        content = re.sub(r'CHUNKS_DIR\s*=\s*Path\("chunks"\)', 
                        'CHUNKS_DIR = Path("data/raw/temp")', content)
        
        pipeline_file.write_text(content)
        print("  ✓ Updated: app/pipeline.py directory paths")

def update_batch_processor_code():
    """Update the batch processor code to use new paths."""
    print("\nUpdating batch processor code...")
    
    batch_file = Path("app/batch_processor.py")
    if batch_file.exists():
        content = batch_file.read_text()
        
        # Update file paths
        content = re.sub(r'urls_file = Path\("urls\.txt"\)', 
                        'urls_file = Path("config/urls.txt")', content)
        content = re.sub(r'prompt_file = Path\("prompt\.txt"\)', 
                        'prompt_file = Path("config/prompt.txt")', content)
        
        # Update the command to run the pipeline
        content = re.sub(r'"python", "yt_whisper_pipeline\.py"', 
                        '"python", "app/pipeline.py"', content)
        
        batch_file.write_text(content)
        print("  ✓ Updated: app/batch_processor.py file paths")

def create_utility_scripts():
    """Create utility scripts."""
    print("\nCreating utility scripts...")
    
    # Create cleanup script
    cleanup_script = """#!/usr/bin/env python3
\"\"\"
Cleanup script for temporary files in yt_transcriber.
This script removes temporary chunk files and other cleanup tasks.
\"\"\"

import shutil
from pathlib import Path

def cleanup_temp_files():
    \"\"\"Remove temporary chunk files.\"\"\"
    temp_dir = Path("data/raw/temp")
    if temp_dir.exists():
        for file in temp_dir.glob("*_chunk*.m4a"):
            file.unlink()
            print(f"Removed: {file}")
        print("✓ Temporary chunk files cleaned up")

def cleanup_empty_dirs():
    \"\"\"Remove empty directories.\"\"\"
    for root, dirs, files in os.walk("data", topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                print(f"Removed empty directory: {dir_path}")

if __name__ == "__main__":
    import os
    cleanup_temp_files()
    cleanup_empty_dirs()
    print("✅ Cleanup completed")
"""
    
    Path("scripts/cleanup_temp.py").write_text(cleanup_script)
    print("  ✓ Created: scripts/cleanup_temp.py")

def create_app_config():
    """Create app configuration file."""
    print("\nCreating app configuration...")
    
    config_content = '''#!/usr/bin/env python3
"""
Configuration settings for yt_transcriber application.
"""

from pathlib import Path

# Directory paths
DOWNLOAD_DIR = Path("data/raw/audio")
TRANSCRIPT_DIR = Path("data/processed/transcripts")
SUMMARY_DIR = Path("data/processed/summaries")
CHUNKS_DIR = Path("data/raw/temp")

# Audio settings
AUDIO_FORMAT = "m4a"

# API settings
WHISPER_MODEL = "whisper-1"
GPT_MODEL = "gpt-4o"

# Ensure directories exist
for folder in (DOWNLOAD_DIR, TRANSCRIPT_DIR, SUMMARY_DIR, CHUNKS_DIR):
    folder.mkdir(parents=True, exist_ok=True)
'''
    
    Path("app/config.py").write_text(config_content)
    print("  ✓ Created: app/config.py")

def update_tests():
    """Update test file paths."""
    print("\nUpdating test files...")
    
    test_file = Path("tests/test_pipeline_and_process.py")
    if test_file.exists():
        content = test_file.read_text()
        
        # Update import statements
        content = re.sub(r'import yt_whisper_pipeline as pipeline', 
                        'import sys\nsys.path.append("app")\nimport pipeline', content)
        content = re.sub(r'import process_videos', 
                        'import sys\nsys.path.append("app")\nimport batch_processor as process_videos', content)
        
        test_file.write_text(content)
        print("  ✓ Updated: tests/test_pipeline_and_process.py")

def create_main_entry_points():
    """Create main entry point scripts in root."""
    print("\nCreating main entry points...")
    
    # Create main pipeline entry point
    pipeline_entry = '''#!/usr/bin/env python3
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
'''
    
    Path("run_pipeline.py").write_text(pipeline_entry)
    print("  ✓ Created: run_pipeline.py")
    
    # Create batch processor entry point
    batch_entry = '''#!/usr/bin/env python3
"""
Main entry point for yt_transcriber batch processor.
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from batch_processor import main

if __name__ == "__main__":
    main()
'''
    
    Path("run_batch.py").write_text(batch_entry)
    print("  ✓ Created: run_batch.py")

def update_readme():
    """Update README with new structure."""
    print("\nUpdating README...")
    
    readme_file = Path("README.md")
    if readme_file.exists():
        content = readme_file.read_text()
        
        # Update usage examples
        content = re.sub(r'python yt_whisper_pipeline\.py', 
                        'python run_pipeline.py', content)
        content = re.sub(r'python process_videos\.py', 
                        'python run_batch.py', content)
        
        # Update directory structure section
        new_structure = """## Directory Structure

- `app/`: Main application code
  - `pipeline.py`: Core YouTube → Whisper → GPT pipeline
  - `batch_processor.py`: Batch processing for multiple videos
  - `config.py`: Configuration settings
- `data/`: All data storage
  - `raw/audio/`: Downloaded audio files
  - `raw/temp/`: Temporary chunk files
  - `processed/transcripts/`: Whisper transcripts
  - `processed/summaries/`: GPT-generated summaries
  - `archive/`: Archive and backup data
- `config/`: Configuration files
  - `urls.txt`: Input YouTube URLs
  - `prompt.txt`: GPT prompts
- `tests/`: Test files
- `docs/`: Documentation
- `scripts/`: Utility scripts
- `logs/`: Log files"""
        
        content = re.sub(r'## Directory Structure.*?## Configuration', 
                        new_structure + '\n\n## Configuration', content, flags=re.DOTALL)
        
        readme_file.write_text(content)
        print("  ✓ Updated: README.md")

def main():
    """Main migration function."""
    print("🚀 Starting yt_transcriber codebase migration...")
    print("=" * 50)
    
    # Confirm with user
    response = input("This will reorganize your entire codebase. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        return
    
    try:
        create_directory_structure()
        move_core_files()
        move_data_directories()
        move_archive_data()
        move_documentation()
        move_logs_and_outputs()
        create_config_files()
        update_pipeline_code()
        update_batch_processor_code()
        create_utility_scripts()
        create_app_config()
        update_tests()
        create_main_entry_points()
        update_readme()
        
        print("\n" + "=" * 50)
        print("✅ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Test the new structure with: python run_pipeline.py --help")
        print("2. Run batch processing with: python run_batch.py")
        print("3. Clean up temporary files with: python scripts/cleanup_temp.py")
        print("4. Update any external scripts that reference the old file paths")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Please check the error and run the script again.")
        sys.exit(1)

if __name__ == "__main__":
    main()