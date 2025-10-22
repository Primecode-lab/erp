#!/usr/bin/env python3
"""
Test script to verify ERP Device Processor setup
"""

import sys
import subprocess
import importlib

def test_python_version():
    """Test if Python version is compatible"""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required")
        return False
    else:
        print("✅ Python version compatible")
        return True

def test_dependencies():
    """Test if all required packages are installed"""
    required_packages = [
        'flask',
        'flask_socketio',
        'pandas',
        'openpyxl',
        'playwright',
        'python_dotenv',
        'werkzeug'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} missing")
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages

def test_playwright_browser():
    """Test if Playwright browser is installed"""
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("✅ Playwright Chromium browser available")
                return True
            except Exception as e:
                print(f"❌ Playwright browser not installed: {e}")
                return False
    except ImportError:
        print("❌ Playwright not installed")
        return False

def test_file_structure():
    """Test if all required files exist"""
    import os
    
    required_files = [
        'app.py',
        'templates/index.html',
        'requirements.txt',
        'README.md'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            missing_files.append(file_path)
    
    return len(missing_files) == 0, missing_files

def test_directory_permissions():
    """Test if output directory can be created"""
    import os
    from pathlib import Path
    
    try:
        desktop_path = Path.home() / "Desktop"
        output_dir = desktop_path / "ERP DATA"
        output_dir.mkdir(exist_ok=True)
        
        # Test write permission
        test_file = output_dir / "test_write.txt"
        test_file.write_text("test")
        test_file.unlink()
        
        print(f"✅ Output directory accessible: {output_dir}")
        return True
    except Exception as e:
        print(f"❌ Cannot create output directory: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 ERP Device Processor - Setup Verification\n")
    
    tests_passed = 0
    total_tests = 5
    
    # Test 1: Python version
    if test_python_version():
        tests_passed += 1
    print()
    
    # Test 2: Dependencies
    deps_ok, missing = test_dependencies()
    if deps_ok:
        tests_passed += 1
    elif missing:
        print(f"💡 Install missing packages: pip install {' '.join(missing)}")
    print()
    
    # Test 3: Playwright browser
    if test_playwright_browser():
        tests_passed += 1
    else:
        print("💡 Install browser: playwright install chromium")
    print()
    
    # Test 4: File structure
    files_ok, missing_files = test_file_structure()
    if files_ok:
        tests_passed += 1
    elif missing_files:
        print(f"💡 Missing files: {', '.join(missing_files)}")
    print()
    
    # Test 5: Directory permissions
    if test_directory_permissions():
        tests_passed += 1
    print()
    
    # Final result
    print("=" * 50)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Ready to run the application.")
        print("\nTo start the application:")
        print("  python app.py")
        print("\nThen open: http://localhost:5000")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
        print("\nQuick setup commands:")
        print("  pip install -r requirements.txt")
        print("  playwright install chromium")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)