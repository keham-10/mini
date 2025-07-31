#!/usr/bin/env python3
"""
Database Backup Script
Creates a backup of the current database before running migrations.
"""

import os
import sys
import shutil
from datetime import datetime

def backup_database():
    """Create a backup of the current database"""
    try:
        # Database file paths
        db_path = "instance/securesphere.db"
        backup_dir = "backups"
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"securesphere_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Check if database file exists
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return False
        
        # Create backup
        shutil.copy2(db_path, backup_path)
        
        # Verify backup
        if os.path.exists(backup_path):
            original_size = os.path.getsize(db_path)
            backup_size = os.path.getsize(backup_path)
            
            if original_size == backup_size:
                print(f"✅ Database backup created successfully: {backup_path}")
                print(f"   Original size: {original_size} bytes")
                print(f"   Backup size: {backup_size} bytes")
                return True
            else:
                print(f"❌ Backup verification failed - size mismatch")
                return False
        else:
            print(f"❌ Backup file was not created")
            return False
            
    except Exception as e:
        print(f"❌ Error creating database backup: {e}")
        return False

def main():
    """Main backup function"""
    print("💾 Creating database backup...")
    print("=" * 40)
    
    if backup_database():
        print("\n✅ Backup completed successfully!")
        print("You can now safely run the migration script.")
        return True
    else:
        print("\n❌ Backup failed!")
        print("Please resolve the issue before running migrations.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
