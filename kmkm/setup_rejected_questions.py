#!/usr/bin/env python3
"""
Complete Setup Script for Rejected Questions Feature
This script handles backup, migration, and verification.
"""

import os
import sys
import subprocess
from datetime import datetime

def run_script(script_name, description):
    """Run a Python script and return success status"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"❌ Error running {script_name}:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Exception running {script_name}: {e}")
        return False

def check_prerequisites():
    """Check if all required files exist"""
    required_files = [
        'app.py',
        'backup_database.py',
        'migrate_rejected_questions.py',
        'ring_heatmap_implementation.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files found")
    return True

def main():
    """Main setup function"""
    print("🚀 Setting up Rejected Questions Feature")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Check prerequisites
    print("Step 1: Checking prerequisites...")
    if not check_prerequisites():
        print("❌ Setup failed at prerequisites check")
        return False
    
    # Step 2: Create backup
    print("\nStep 2: Creating database backup...")
    if not run_script('backup_database.py', 'Creating database backup'):
        print("❌ Setup failed at backup step")
        print("Please resolve backup issues before continuing")
        return False
    
    # Step 3: Run migration
    print("\nStep 3: Running database migration...")
    if not run_script('migrate_rejected_questions.py', 'Running database migration'):
        print("❌ Setup failed at migration step")
        print("Database backup is available in the 'backups' directory")
        return False
    
    # Step 4: Final verification
    print("\nStep 4: Final verification...")
    try:
        # Import and test the new functionality
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from ring_heatmap_implementation import RejectedQuestionsManager, RingHeatmapGenerator
        from app import app, db, RejectedQuestion
        
        with app.app_context():
            # Test database connection
            count = RejectedQuestion.query.count()
            print(f"✅ Database connection successful")
            print(f"✅ RejectedQuestion table accessible (current count: {count})")
            
            # Test ring heatmap generator
            generator = RingHeatmapGenerator()
            print(f"✅ Ring heatmap generator initialized")
            
            # Test rejected questions manager
            manager = RejectedQuestionsManager(db)
            print(f"✅ Rejected questions manager initialized")
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    
    # Success message
    print("\n" + "=" * 50)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("\nNew features available:")
    print("✅ 5-level ring-based heatmap visualization")
    print("✅ Rejected questions workflow (lead ↔ client)")
    print("✅ Dynamic score recalculation")
    print("✅ Dimension-wise results display")
    print("✅ Admin dashboard with same results")
    print("✅ Enhanced client-lead communication")
    
    print("\nNext steps:")
    print("1. Restart your Flask application")
    print("2. Test the new features in the web interface")
    print("3. Check the ring heatmap visualization")
    print("4. Test the rejected questions workflow")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
