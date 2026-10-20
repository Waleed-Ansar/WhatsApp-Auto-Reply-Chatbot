#!/usr/bin/env python3
"""
Setup script for RTD LLM Modular Project
"""

import os
import subprocess
import sys

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_env_file():
    """Setup environment file"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            print("📝 Creating .env file from .env.example...")
            with open('.env.example', 'r') as src, open('.env', 'w') as dst:
                dst.write(src.read())
            print("✅ .env file created! Please edit it with your actual API keys.")
        else:
            print("❌ .env.example not found!")
            return False
    else:
        print("✅ .env file already exists")
    return True

def create_data_directory():
    """Create data directory for vector database"""
    data_dir = "data/rtd_project_vectordb"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        print(f"✅ Created directory: {data_dir}")
    else:
        print(f"✅ Directory already exists: {data_dir}")

def main():
    print("🚀 Setting up RTD LLM Modular Project...")
    print("=" * 50)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed during dependency installation")
        sys.exit(1)
    
    print()
    
    # Setup environment file
    if not setup_env_file():
        print("❌ Setup failed during environment file creation")
        sys.exit(1)
    
    print()
    
    # Create data directory
    create_data_directory()
    
    print("\n" + "=" * 50)
    print("✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your actual API keys")
    print("2. Ensure you have vector database data in data/rtd_project_vectordb/")
    print("3. Run the application: python main.py")

if __name__ == "__main__":
    main()