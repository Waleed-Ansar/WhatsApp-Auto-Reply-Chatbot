#!/usr/bin/env python3
"""
Test script to verify the modular structure without requiring dependencies
"""

import os
import sys

def test_file_structure():
    """Test that all required files exist"""
    required_files = [
        'main.py',
        'config.py',
        'models.py',
        'llm_setup.py',
        'datetime_utils.py',
        'memory_service.py',
        'mcp_services.py',
        "mcp_client.py",
        "mcp_server.py",
        "call_tools.py",
        "token_manager.py",
        "tools.py",
        "session.py",
        'chat_system.py',
        'api_routes.py',
        'requirements.txt',
        'README.md',
        '.env.example'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_file_contents():
    """Test basic file contents"""
    tests = [
        ('main.py', 'uvicorn'),
        ('config.py', 'class Config'),
        ('models.py', 'BaseModel'),
        ('api_routes.py', 'FastAPI'),
        ('requirements.txt', 'fastapi'),
    ]
    
    for filename, expected_content in tests:
        try:
            with open(filename, 'r') as f:
                content = f.read()
                if expected_content in content:
                    print(f"✅ {filename} contains expected content")
                else:
                    print(f"❌ {filename} missing expected content: {expected_content}")
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")

if __name__ == "__main__":
    print("Testing RTD LLM Modular Project Structure...")
    print("=" * 50)
    
    structure_ok = test_file_structure()
    print()
    test_file_contents()
    
    print("\n" + "=" * 50)
    if structure_ok:
        print("✅ Project structure test completed successfully!")
        print("\nTo run the application:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set up .env file with your API keys")
        print("3. Run: python main.py")
    else:
        print("❌ Project structure test failed!")
        sys.exit(1)