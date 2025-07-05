#!/usr/bin/env python3
"""
Setup script for YouTube API configuration.

This script helps users set up their YouTube Data API v3 key and test the configuration.
"""

import os
import sys
from pathlib import Path

def print_setup_instructions():
    """Print instructions for getting a YouTube API key."""
    print("=== YouTube Data API v3 Setup Instructions ===")
    print()
    print("1. Go to the Google Cloud Console: https://console.cloud.google.com/")
    print("2. Create a new project or select an existing one")
    print("3. Enable the YouTube Data API v3:")
    print("   - Go to 'APIs & Services' > 'Library'")
    print("   - Search for 'YouTube Data API v3'")
    print("   - Click on it and press 'Enable'")
    print("4. Create an API key:")
    print("   - Go to 'APIs & Services' > 'Credentials'")
    print("   - Click 'Create Credentials' > 'API Key'")
    print("   - Copy the generated API key")
    print("5. (Optional) Restrict the API key:")
    print("   - Click on the API key to edit it")
    print("   - Under 'API restrictions', select 'YouTube Data API v3'")
    print("   - Save the changes")
    print()

def setup_api_key():
    """Help user set up their API key."""
    print("=== API Key Setup ===")
    
    # Check if API key is already set
    existing_key = os.getenv('YOUTUBE_API_KEY')
    if existing_key:
        print(f"API key is already set: {existing_key[:10]}...")
        overwrite = input("Do you want to set a new API key? (y/n): ").lower().strip()
        if overwrite not in ['y', 'yes']:
            return existing_key
    
    print("Please enter your YouTube Data API v3 key:")
    api_key = input("API Key: ").strip()
    
    if not api_key:
        print("No API key provided. Exiting.")
        return None
    
    # Suggest adding to shell profile
    print("\nTo make this permanent, add this line to your shell profile:")
    print(f"export YOUTUBE_API_KEY='{api_key}'")
    print()
    print("For bash/zsh, add it to ~/.bashrc or ~/.zshrc")
    print("Then restart your terminal or run: source ~/.bashrc")
    print()
    
    # Set for current session
    os.environ['YOUTUBE_API_KEY'] = api_key
    print("API key set for current session.")
    
    return api_key

def test_api_key():
    """Test the API key by making a simple request."""
    try:
        import requests
        
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            print("No API key found. Please set YOUTUBE_API_KEY environment variable.")
            return False
        
        print("Testing API key...")
        
        # Simple test request
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': 'test',
            'type': 'video',
            'maxResults': 1,
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            print("✅ API key is working correctly!")
            return True
        elif response.status_code == 400:
            print("❌ API key is invalid or malformed.")
            return False
        elif response.status_code == 403:
            print("❌ API key doesn't have permission for YouTube Data API v3.")
            print("Make sure you've enabled the YouTube Data API v3 in your Google Cloud project.")
            return False
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            print(response.text)
            return False
            
    except ImportError:
        print("❌ 'requests' library not found. Please install it: pip install requests")
        return False
    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False

def main():
    """Main setup function."""
    print("=== YouTube Transcriber API Setup ===")
    print()
    
    # Check if requests is available
    try:
        import requests
    except ImportError:
        print("❌ Required dependency 'requests' not found.")
        print("Please install it first: pip install requests")
        print("Or install all dependencies: pip install -r requirements.txt")
        sys.exit(1)
    
    # Show setup instructions
    show_instructions = input("Show API setup instructions? (y/n): ").lower().strip()
    if show_instructions in ['y', 'yes']:
        print_setup_instructions()
    
    # Setup API key
    api_key = setup_api_key()
    if not api_key:
        sys.exit(1)
    
    # Test the API key
    if test_api_key():
        print("\n✅ Setup complete! You can now use the YouTube URL fetcher.")
        print("Try running: python src/yt_transcriber/core/url_update.py")
    else:
        print("\n❌ Setup incomplete. Please check your API key and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main() 