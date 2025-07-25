#!/usr/bin/env python3
"""
Quick start script for ERP Device Processor
Handles setup verification and launches the application
"""

import sys
import subprocess
import os
from pathlib import Path

def check_and_install_dependencies():
    """Check and install required dependencies"""
    print("🔧 Checking dependencies...")
    
    try:
        import flask
        import flask_socketio
        import pandas
        import playwright
        print("✅ All dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("📦 Installing dependencies...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            return False

def check_playwright_browser():
    """Check and install Playwright browser"""
    print("🌐 Checking Playwright browser...")
    
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print("✅ Playwright browser available")
        return True
    except Exception:
        print("📦 Installing Playwright browser...")
        try:
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            print("✅ Playwright browser installed")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install Playwright browser")
            return False

def setup_output_directory():
    """Create output directory"""
    print("📁 Setting up output directory...")
    
    try:
        output_dir = Path.home() / "Desktop" / "ERP DATA"
        output_dir.mkdir(exist_ok=True)
        print(f"✅ Output directory ready: {output_dir}")
        return True
    except Exception as e:
        print(f"❌ Failed to create output directory: {e}")
        return False

def launch_application():
    """Launch the Flask application"""
    print("🚀 Starting ERP Device Processor...")
    print("📱 Application will be available at: http://localhost:5000")
    print("⚠️  Do not close this terminal while using the application")
    print("🔄 Press Ctrl+C to stop the application\n")
    
    try:
        # Import and run the app
        from app import app, socketio, logger
        logger.info("Application started via quick start script")
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Application error: {e}")
        return False
    
    return True

def main():
    """Main setup and launch sequence"""
    print("🎯 ERP Device Processor - Quick Start\n")
    
    # Check file structure
    required_files = ['app.py', 'requirements.txt', 'templates/index.html']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        print("Please ensure all application files are present")
        return False
    
    # Setup sequence
    steps = [
        ("Dependencies", check_and_install_dependencies),
        ("Playwright Browser", check_playwright_browser),
        ("Output Directory", setup_output_directory)
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 Step: {step_name}")
        if not step_func():
            print(f"❌ Setup failed at: {step_name}")
            return False
    
    print("\n✅ Setup completed successfully!")
    print("=" * 50)
    
    # Launch application
    return launch_application()

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the setup and try again")
        sys.exit(1)