#!/usr/bin/env python3
"""
SecureSphere Application Startup Script
Ensures proper initialization and error checking before starting the app.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all required files and dependencies exist."""
    print("🔍 Checking requirements...")
    
    # Check if devweb.csv exists
    if not os.path.exists('devweb.csv'):
        print("❌ Error: devweb.csv file not found!")
        return False
    print("✅ devweb.csv found")
    
    # Check if instance directory exists
    if not os.path.exists('instance'):
        print("📁 Creating instance directory...")
        os.makedirs('instance', exist_ok=True)
    print("✅ instance directory ready")
    
    # Check if static/uploads directory exists
    uploads_dir = os.path.join('static', 'uploads')
    if not os.path.exists(uploads_dir):
        print("📁 Creating uploads directory...")
        os.makedirs(uploads_dir, exist_ok=True)
    print("✅ uploads directory ready")
    
    return True

def initialize_database():
    """Initialize the database if needed."""
    print("🗄️ Initializing database...")
    try:
        # Run database initialization
        result = subprocess.run([sys.executable, 'init_database.py'], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"❌ Database initialization failed: {result.stderr}")
            return False
        print("✅ Database initialized successfully")
        return True
    except subprocess.TimeoutExpired:
        print("❌ Database initialization timed out")
        return False
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return False

def test_import():
    """Test if the app module can be imported without errors."""
    print("📦 Testing app import...")
    try:
        import app
        print("✅ App module imports successfully")
        return True
    except Exception as e:
        print(f"❌ App import failed: {e}")
        return False

def main():
    """Main startup function."""
    print("🚀 SecureSphere Application Startup")
    print("=" * 50)
    
    # Change to the script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Run all checks
    if not check_requirements():
        print("❌ Requirements check failed!")
        sys.exit(1)
    
    if not test_import():
        print("❌ Import test failed!")
        sys.exit(1)
    
    if not initialize_database():
        print("❌ Database initialization failed!")
        sys.exit(1)
    
    print("=" * 50)
    print("✅ All checks passed! Starting application...")
    print("🌐 Application will be available at: http://127.0.0.1:5001")
    print("👤 Default admin credentials:")
    print("   Username: admin")
    print("   Password: AdminPass123")
    print("=" * 50)
    
    # Start the application
    try:
        import app
        app.app.run(debug=True, port=5001, host='0.0.0.0')
    except KeyboardInterrupt:
        print("\n🛑 Application stopped by user")
    except Exception as e:
        print(f"❌ Application failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()