#!/usr/bin/env python3
"""
FINN.no Deal Finder Pro - Launcher Script
Run this script to start the application

Usage:
    python run.py          # Normal mode (live scraping)
    python run.py --demo   # Demo mode (simulated data)
"""

import sys
import os

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    try:
        import customtkinter
    except ImportError:
        missing.append('customtkinter')
    
    try:
        from PIL import Image
    except ImportError:
        missing.append('Pillow')
    
    try:
        import requests
    except ImportError:
        missing.append('requests')
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        missing.append('beautifulsoup4')
    
    if missing:
        print("❌ Missing dependencies detected!")
        print("\nPlease install the required packages:")
        print(f"  pip install {' '.join(missing)}")
        print("\nOr install all requirements:")
        print("  pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Main entry point"""
    # Check for demo mode flag
    demo_mode = '--demo' in sys.argv or '-d' in sys.argv
    
    if not check_dependencies():
        sys.exit(1)
    
    print("🚀 Starting FINN.no Deal Finder Pro...")
    
    if demo_mode:
        print("📋 Running in DEMO mode (simulated data)")
        # Patch the scraper to use demo data
        import scraper
        scraper.FinnScraper = scraper.DemoScraper
    
    # Import and run the main application
    from main import FinnDealFinderApp
    
    app = FinnDealFinderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
