#!/usr/bin/env python3
"""
Migration script to add review_status column to questionnaire_responses table
"""

import os
import sys
import sqlite3
from datetime import datetime

def migrate_database():
    """Add review_status column to existing database"""
    
    # Get database path
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'instance', 'securesphere.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if review_status column already exists
        cursor.execute("PRAGMA table_info(questionnaire_responses)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'review_status' in columns:
            print("✅ review_status column already exists")
            conn.close()
            return True
        
        print("🔄 Adding review_status column to questionnaire_responses table...")
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE questionnaire_responses 
            ADD COLUMN review_status VARCHAR(20) DEFAULT 'pending'
        """)
        
        # Update existing records based on current status
        print("🔄 Updating existing records...")
        
        # Set approved records
        cursor.execute("""
            UPDATE questionnaire_responses 
            SET review_status = 'approved' 
            WHERE is_approved = 1
        """)
        
        # Set records that need client response to needs_revision
        cursor.execute("""
            UPDATE questionnaire_responses 
            SET review_status = 'needs_revision' 
            WHERE needs_client_response = 1 AND is_approved = 0
        """)
        
        # Set reviewed but not approved as rejected (if they exist)
        cursor.execute("""
            UPDATE questionnaire_responses 
            SET review_status = 'rejected' 
            WHERE is_reviewed = 1 AND is_approved = 0 AND needs_client_response = 0
        """)
        
        # Commit changes
        conn.commit()
        
        # Verify the changes
        cursor.execute("SELECT COUNT(*) FROM questionnaire_responses")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT review_status, COUNT(*) FROM questionnaire_responses GROUP BY review_status")
        status_counts = cursor.fetchall()
        
        print(f"✅ Successfully migrated {total_count} questionnaire responses")
        print("📊 Status distribution:")
        for status, count in status_counts:
            print(f"   - {status}: {count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("🚀 Starting review status migration...")
    success = migrate_database()
    if success:
        print("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1)