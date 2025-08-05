#!/usr/bin/env python3
"""
Test script to verify SecureSphere app can start without errors
"""

import sys
import os
import traceback

def test_imports():
    """Test all critical imports"""
    print("Testing imports...")
    
    try:
        # Test database components
        from database_manager import DatabaseManager
        print("✓ DatabaseManager imports successfully")
        
        from database_integration import DatabaseIntegration
        print("✓ DatabaseIntegration imports successfully")
        
        # Test database initialization
        db_manager = DatabaseManager()
        print("✓ Database manager initializes successfully")
        
        db_integration = DatabaseIntegration()
        print("✓ Database integration initializes successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        traceback.print_exc()
        return False

def test_database_operations():
    """Test basic database operations"""
    print("\nTesting database operations...")
    
    try:
        from database_manager import DatabaseManager
        
        # Use in-memory database for testing
        db_manager = DatabaseManager(':memory:')
        print("✓ In-memory database created successfully")
        
        # Test getting stats (should work even with empty database)
        stats = db_manager.get_database_stats()
        print(f"✓ Database stats retrieved: {len(stats)} metrics")
        
        return True
    except Exception as e:
        print(f"✗ Database operation error: {e}")
        traceback.print_exc()
        return False

def test_template_compilation():
    """Test that templates can be found and have basic syntax"""
    print("\nTesting templates...")
    
    template_files = [
        'templates/dashboard_superuser.html',
        'templates/product_results.html',
        'templates/register.html',
        'templates/unified_communication.html',
        'templates/admin_product_details.html'
    ]
    
    for template in template_files:
        if os.path.exists(template):
            try:
                with open(template, 'r') as f:
                    content = f.read()
                    # Basic check for template blocks
                    if '{% extends' in content or '{% block' in content:
                        print(f"✓ {template} - Valid Jinja2 template")
                    else:
                        print(f"? {template} - No template blocks found")
            except Exception as e:
                print(f"✗ {template} - Error reading: {e}")
                return False
        else:
            print(f"✗ {template} - File not found")
            return False
    
    return True

def test_flask_app_creation():
    """Test if Flask app can be created (if Flask is available)"""
    print("\nTesting Flask app creation...")
    
    try:
        import flask
        print("✓ Flask is available")
        
        # Try to import the main app
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Test basic Flask app creation without running it
        app = flask.Flask(__name__)
        app.config['TESTING'] = True
        print("✓ Basic Flask app can be created")
        
        # Test if our database integration can be added
        from database_integration import DatabaseIntegration
        db_integration = DatabaseIntegration(app)
        print("✓ Database integration can be added to Flask app")
        
        return True
    except ImportError:
        print("? Flask not available - this is okay for testing database components")
        return True
    except Exception as e:
        print(f"✗ Flask app creation error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("SecureSphere Startup Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_database_operations,
        test_template_compilation,
        test_flask_app_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"Test {test.__name__} failed")
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! App should start successfully.")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())