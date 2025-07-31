#!/usr/bin/env python3
"""
Database Migration Script for Rejected Questions Feature
This script adds the rejected_questions table to the existing database.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, RejectedQuestion

def create_rejected_questions_table():
    """Create the rejected questions table"""
    try:
        with app.app_context():
            # Create the table
            db.create_all()
            print("✅ Rejected questions table created successfully")
            return True
    except Exception as e:
        print(f"❌ Error creating rejected questions table: {e}")
        return False

def verify_table_creation():
    """Verify that the table was created correctly"""
    try:
        with app.app_context():
            # Try to query the table
            count = RejectedQuestion.query.count()
            print(f"✅ Table verification successful. Current rejected questions count: {count}")
            return True
    except Exception as e:
        print(f"❌ Error verifying table: {e}")
        return False

def add_sample_data():
    """Add sample data for testing (optional)"""
    try:
        with app.app_context():
            # Check if we already have sample data
            existing_count = RejectedQuestion.query.count()
            if existing_count > 0:
                print(f"ℹ️  Sample data already exists ({existing_count} records)")
                return True
            
            print("ℹ️  No sample data added - table is ready for production use")
            return True
    except Exception as e:
        print(f"❌ Error checking sample data: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Starting database migration for Rejected Questions feature...")
    print("=" * 60)
    
    # Step 1: Create the table
    print("Step 1: Creating rejected_questions table...")
    if not create_rejected_questions_table():
        print("❌ Migration failed at table creation step")
        return False
    
    # Step 2: Verify table creation
    print("\nStep 2: Verifying table creation...")
    if not verify_table_creation():
        print("❌ Migration failed at verification step")
        return False
    
    # Step 3: Check sample data
    print("\nStep 3: Checking sample data...")
    if not add_sample_data():
        print("❌ Migration failed at sample data step")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Migration completed successfully!")
    print("\nThe rejected questions feature is now ready to use.")
    print("\nFeatures added:")
    print("- RejectedQuestion model for tracking rejected questions")
    print("- Database table: rejected_questions")
    print("- Support for lead-client question revision workflow")
    print("- Dynamic score recalculation after question updates")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
