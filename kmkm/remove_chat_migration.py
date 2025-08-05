#!/usr/bin/env python3
"""
Database migration script to remove chat functionality
This script removes QuestionChat and ChatMessage tables and cleans up related data.
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def migrate_remove_chat_tables():
    """Remove chat tables and clean up database"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'securesphere.db')
    
    if not os.path.exists(db_path):
        print("❌ Database not found at:", db_path)
        return False
    
    print("🔄 Starting chat removal migration...")
    print(f"📍 Database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if chat tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('question_chats', 'chat_messages')
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if existing_tables:
            print(f"📋 Found chat tables to remove: {existing_tables}")
            
            # Remove chat_messages table first (has foreign key to question_chats)
            if 'chat_messages' in existing_tables:
                print("🗑️  Dropping chat_messages table...")
                cursor.execute("DROP TABLE IF EXISTS chat_messages")
                print("   ✅ chat_messages table removed")
            
            # Remove question_chats table
            if 'question_chats' in existing_tables:
                print("🗑️  Dropping question_chats table...")
                cursor.execute("DROP TABLE IF EXISTS question_chats")
                print("   ✅ question_chats table removed")
        else:
            print("ℹ️  No chat tables found to remove")
        
        # Check if there are any indexes related to chat tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE '%chat%'
        """)
        chat_indexes = [row[0] for row in cursor.fetchall()]
        
        if chat_indexes:
            print(f"🗑️  Removing chat-related indexes: {chat_indexes}")
            for index in chat_indexes:
                try:
                    cursor.execute(f"DROP INDEX IF EXISTS {index}")
                    print(f"   ✅ Removed index: {index}")
                except Exception as e:
                    print(f"   ⚠️  Could not remove index {index}: {e}")
        
        # Commit changes
        conn.commit()
        print("💾 Changes committed to database")
        
        # Verify tables are removed
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('question_chats', 'chat_messages')
        """)
        remaining_tables = [row[0] for row in cursor.fetchall()]
        
        if remaining_tables:
            print(f"⚠️  Some chat tables still exist: {remaining_tables}")
            return False
        else:
            print("✅ All chat tables successfully removed")
        
        # Close connection
        conn.close()
        
        print("🎉 Chat removal migration completed successfully!")
        print("\n📋 Summary:")
        print("   • Removed QuestionChat and ChatMessage tables")
        print("   • Removed related indexes")
        print("   • Simplified approval workflow is now active")
        print("   • Only APPROVED option available for leads")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        try:
            conn.rollback()
            conn.close()
        except:
            pass
        return False

if __name__ == "__main__":
    print("🚀 SecureSphere Chat Removal Migration")
    print("=" * 50)
    
    success = migrate_remove_chat_tables()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("The application now uses simplified approval workflow.")
    else:
        print("\n❌ Migration failed!")
        print("Please check the error messages above.")
        sys.exit(1)