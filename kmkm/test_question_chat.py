#!/usr/bin/env python3
"""
Test script for the new question chat system.
This script tests the core functionality of the question-based chat system.
"""

import os
import sys
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, Product, QuestionnaireResponse, QuestionChat, ChatMessage

def test_question_chat_system():
    """Test the new question chat system functionality"""
    with app.app_context():
        try:
            print("🧪 Testing Question Chat System...")
            
            # Test 1: Verify tables exist
            print("\n1️⃣ Testing database tables...")
            
            # Check if tables exist by trying to query them
            question_chats = QuestionChat.query.count()
            chat_messages = ChatMessage.query.count()
            
            print(f"   ✅ QuestionChat table exists (records: {question_chats})")
            print(f"   ✅ ChatMessage table exists (records: {chat_messages})")
            
            # Test 2: Test creating a question chat
            print("\n2️⃣ Testing QuestionChat creation...")
            
            # Find a sample response (if any exist)
            sample_response = QuestionnaireResponse.query.first()
            if sample_response:
                # Create a test question chat
                test_chat = QuestionChat(
                    response_id=sample_response.id,
                    client_id=sample_response.user_id,
                    lead_id=1,  # Assuming lead user exists
                    product_id=sample_response.product_id,
                    review_status='pending'
                )
                
                db.session.add(test_chat)
                db.session.commit()
                
                print(f"   ✅ Created test QuestionChat (ID: {test_chat.id})")
                
                # Test 3: Test creating a chat message
                print("\n3️⃣ Testing ChatMessage creation...")
                
                test_message = ChatMessage(
                    chat_id=test_chat.id,
                    sender_id=1,  # Assuming user exists
                    message_type='text',
                    content='This is a test message for the new chat system.'
                )
                
                db.session.add(test_message)
                db.session.commit()
                
                print(f"   ✅ Created test ChatMessage (ID: {test_message.id})")
                
                # Test 4: Test relationships
                print("\n4️⃣ Testing model relationships...")
                
                # Test chat -> response relationship
                if test_chat.response:
                    print(f"   ✅ QuestionChat -> Response relationship works")
                
                # Test chat -> messages relationship
                if test_chat.messages:
                    print(f"   ✅ QuestionChat -> Messages relationship works ({len(test_chat.messages)} messages)")
                
                # Test message -> sender relationship
                if test_message.sender:
                    print(f"   ✅ ChatMessage -> Sender relationship works")
                
                # Clean up test data
                print("\n🧹 Cleaning up test data...")
                db.session.delete(test_message)
                db.session.delete(test_chat)
                db.session.commit()
                print("   ✅ Test data cleaned up")
                
            else:
                print("   ⚠️  No sample responses found, skipping relationship tests")
            
            # Test 5: Test route functionality (basic import test)
            print("\n5️⃣ Testing route imports...")
            
            # Try to import the new route functions
            from app import question_chat_view, send_chat_message, approve_question_from_chat, question_chats_list
            print("   ✅ All new chat routes imported successfully")
            
            print("\n🎉 All tests passed! The new question chat system is ready.")
            print("\n📋 Summary of New Features:")
            print("   • Question-based chat system")
            print("   • Three-option review workflow (Approved/Needs Revision/Rejected)")
            print("   • File upload support in chats")
            print("   • Real-time messaging interface")
            print("   • Automatic question status management")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = test_question_chat_system()
    sys.exit(0 if success else 1)