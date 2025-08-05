#!/usr/bin/env python3
"""
Safe startup script for SecureSphere webapp
Handles common startup issues and provides helpful error messages
"""

import os
import sys
import subprocess
import traceback
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    print("Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required dependencies are available"""
    print("\nChecking dependencies...")
    
    required_packages = [
        'flask', 'flask_sqlalchemy', 'flask_mail', 
        'flask_limiter', 'werkzeug'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_').lower())
            print(f"✓ {package}")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ Missing packages: {', '.join(missing_packages)}")
        print("To install missing packages, run:")
        print("pip3 install -r requirements.txt")
        return False
    
    print("✓ All required packages are available")
    return True

def check_database():
    """Check database components"""
    print("\nChecking database components...")
    
    try:
        from database_manager import DatabaseManager
        print("✓ Database manager available")
        
        from database_integration import DatabaseIntegration
        print("✓ Database integration available")
        
        # Test database initialization
        db_manager = DatabaseManager()
        print("✓ Database initialized successfully")
        
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        traceback.print_exc()
        return False

def check_templates():
    """Check that all templates exist"""
    print("\nChecking templates...")
    
    template_dir = Path("templates")
    if not template_dir.exists():
        print("❌ Templates directory not found")
        return False
    
    critical_templates = [
        'base.html',
        'index.html',
        'login.html',
        'dashboard_superuser.html',
        'dashboard_client.html',
        'dashboard_lead.html'
    ]
    
    missing_templates = []
    for template in critical_templates:
        template_path = template_dir / template
        if template_path.exists():
            print(f"✓ {template}")
        else:
            print(f"❌ {template} - Missing")
            missing_templates.append(template)
    
    if missing_templates:
        print(f"\n❌ Missing critical templates: {', '.join(missing_templates)}")
        return False
    
    return True

def check_static_files():
    """Check static files directory"""
    print("\nChecking static files...")
    
    static_dir = Path("static")
    if not static_dir.exists():
        print("❌ Static directory not found")
        return False
    
    print("✓ Static directory exists")
    
    # Check for uploads directory
    uploads_dir = static_dir / "uploads"
    if not uploads_dir.exists():
        print("Creating uploads directory...")
        uploads_dir.mkdir(exist_ok=True)
        print("✓ Uploads directory created")
    else:
        print("✓ Uploads directory exists")
    
    return True

def setup_environment():
    """Setup environment variables and configuration"""
    print("\nSetting up environment...")
    
    # Set default environment variables if not present
    env_vars = {
        'FLASK_ENV': 'development',
        'FLASK_DEBUG': '1',
        'SECRET_KEY': 'dev-secret-key-change-in-production'
    }
    
    for key, default_value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value
            print(f"✓ Set {key} = {default_value}")
        else:
            print(f"✓ {key} already set")
    
    return True

def start_app():
    """Start the Flask application"""
    print("\n" + "="*50)
    print("Starting SecureSphere Application...")
    print("="*50)
    
    try:
        # Import and run the app
        from app import app
        
        print("✓ Flask app imported successfully")
        print("\n🚀 Starting server...")
        print("📍 URL: http://127.0.0.1:5001")
        print("⏹️  Press Ctrl+C to stop the server")
        print("-" * 50)
        
        # Start the app
        app.run(
            host='127.0.0.1',
            port=5001,
            debug=True,
            use_reloader=False  # Avoid double startup in debug mode
        )
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Server stopped by user")
        return True
    except Exception as e:
        print(f"\n❌ Error starting app: {e}")
        traceback.print_exc()
        return False

def main():
    """Main startup routine"""
    print("SecureSphere Safe Startup")
    print("=" * 40)
    
    # Run all checks
    checks = [
        check_python_version,
        check_dependencies,
        check_database,
        check_templates,
        check_static_files,
        setup_environment
    ]
    
    for check in checks:
        if not check():
            print(f"\n❌ Startup failed at: {check.__name__}")
            print("Please fix the issues above and try again.")
            return 1
    
    print("\n✅ All checks passed!")
    print("🎉 Ready to start the application!")
    
    # Ask user if they want to start the app
    try:
        response = input("\nStart the application now? (y/n): ").lower().strip()
        if response in ['y', 'yes', '']:
            return 0 if start_app() else 1
        else:
            print("App startup cancelled by user.")
            return 0
    except KeyboardInterrupt:
        print("\nStartup cancelled by user.")
        return 0

if __name__ == "__main__":
    sys.exit(main())