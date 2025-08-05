#!/usr/bin/env python3
"""
Migration script for new chat system
This script creates the QuestionChat and ChatMessage tables for the lead-client communication system
"""

import sys
import os

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db, QuestionChat, ChatMessage
from sqlalchemy import text

def migrate_chat_system():
    """Create new chat system tables"""
    
    print("🚀 Starting Chat System Migration")
    
    with app.app_context():
        try:
            # Create all tables
            print("📋 Creating QuestionChat table...")
            print("📋 Creating ChatMessage table...")
            
            # Create tables with error handling for existing indexes
            try:
                db.create_all()
            except Exception as create_error:
                if "already exists" in str(create_error):
                    print("   ⚠️  Some tables/indexes already exist, continuing...")
                else:
                    raise create_error
            
            print("✅ Database tables created successfully")
            
            # Test table creation
            print("\n🧪 Testing table creation...")
            
            # Check if tables exist
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='question_chats'"))
            if result.fetchone():
                print("   ✅ QuestionChat table exists")
            else:
                print("   ❌ QuestionChat table missing")
                return False
                
            result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='chat_messages'"))
            if result.fetchone():
                print("   ✅ ChatMessage table exists")
            else:
                print("   ❌ ChatMessage table missing")
                return False
            
            # Test basic functionality
            print("\n🧪 Testing basic operations...")
            
            # Count existing records
            question_chats = QuestionChat.query.count()
            chat_messages = ChatMessage.query.count()
            
            print(f"   ✅ QuestionChat table accessible (records: {question_chats})")
            print(f"   ✅ ChatMessage table accessible (records: {chat_messages})")
            
            print("\n✅ Chat System Migration completed successfully!")
            print("\n📝 Migration Summary:")
            print("   • Created QuestionChat table for tracking question review chats")
            print("   • Created ChatMessage table for storing chat messages")
            print("   • Added indexes for better performance")
            print("   • Tables support 3-option review workflow (APPROVED, NEEDS REVISION, REJECTED)")
            print("\n🎯 Next Steps:")
            print("   • Leads can now review questions with 3 options")
            print("   • APPROVED: Freezes question")
            print("   • NEEDS REVISION: Creates chat for more evidence")
            print("   • REJECTED: Allows client to re-select answer")
            print("   • All communications are visible to admin users")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = migrate_chat_system()
    if success:
        print("\n🎉 Chat system is ready for use!")
        sys.exit(0)
    else:
        print("\n💥 Migration failed. Please check the errors above.")
        sys.exit(1)