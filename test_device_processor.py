#!/usr/bin/env python3
"""
Test script to verify DeviceProcessor class functionality
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_device_processor():
    """Test DeviceProcessor class creation and method availability"""
    try:
        # Import the DeviceProcessor class
        from app import DeviceProcessor
        print("✅ Successfully imported DeviceProcessor")
        
        # Create an instance
        processor = DeviceProcessor("test_user", "test_pass")
        print("✅ Successfully created DeviceProcessor instance")
        
        # Check if close_browser method exists
        if hasattr(processor, 'close_browser'):
            print("✅ close_browser method exists")
        else:
            print("❌ close_browser method NOT found")
            return False
        
        # Check if method is callable
        if callable(getattr(processor, 'close_browser')):
            print("✅ close_browser method is callable")
        else:
            print("❌ close_browser method is not callable")
            return False
        
        # Test calling the method
        try:
            processor.close_browser()
            print("✅ close_browser method executed successfully")
        except Exception as e:
            print(f"❌ Error calling close_browser: {e}")
            return False
        
        # List all methods of the processor
        methods = [method for method in dir(processor) if not method.startswith('_')]
        print(f"📋 Available methods: {', '.join(methods)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing DeviceProcessor: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🔍 Testing DeviceProcessor Class\n")
    
    success = test_device_processor()
    
    if success:
        print("\n🎉 All tests passed! DeviceProcessor class is working correctly.")
    else:
        print("\n❌ Tests failed! There are issues with the DeviceProcessor class.")
    
    sys.exit(0 if success else 1)