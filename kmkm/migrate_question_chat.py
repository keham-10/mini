#!/usr/bin/env python3
"""
Migration script to add new question chat system tables.
This script adds the QuestionChat and ChatMessage tables to support
the new question-based chat system.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, QuestionChat, ChatMessage

def migrate_question_chat_system():
    """Add the new question chat system tables"""
    with app.app_context():
        try:
            print("🔄 Starting question chat system migration...")
            
            # Create the new tables
            print("📋 Creating QuestionChat table...")
            db.create_all()
            
            print("✅ Migration completed successfully!")
            print("\n📊 New tables created:")
            print("   - question_chats")
            print("   - chat_messages")
            
            print("\n🎯 New Features Available:")
            print("   - Question-based chat system")
            print("   - Three-option review workflow (Approved/Needs Revision/Rejected)")
            print("   - File uploads in chat")
            print("   - Real-time messaging")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_question_chat_system()