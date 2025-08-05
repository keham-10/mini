# Question Chat System Implementation

## Overview

This document describes the implementation of the new question-based chat system that replaces the old unified communication interface. The new system implements a three-option review workflow (Approved/Needs Revision/Rejected) with integrated chat functionality as requested.

## Key Features Implemented

### 1. Three-Option Review Workflow
- **APPROVED**: Question is frozen and finalized, no further changes allowed
- **NEEDS REVISION**: Opens chat for client to provide more evidence
- **REJECTED**: Client must re-select answer option, all 5 options become available again

### 2. Question-Based Chat System
- Each question gets its own dedicated chat thread
- Real-time messaging between client and lead
- File upload support in chat messages
- Automatic status management based on review decisions

### 3. Modern Chat Interface
- WhatsApp-style chat interface based on reference images
- Message bubbles with timestamps
- File attachment support
- Status indicators (pending, approved, needs revision, rejected)
- Auto-scroll to latest messages

## Database Changes

### New Tables Added

#### `question_chats`
- `id` (Primary Key)
- `response_id` (Foreign Key to questionnaire_responses)
- `client_id` (Foreign Key to users)
- `lead_id` (Foreign Key to users)
- `product_id` (Foreign Key to products)
- `review_status` (pending, approved, needs_revision, rejected)
- `is_active` (Boolean - false when approved/resolved)
- `created_at`, `updated_at`

#### `chat_messages`
- `id` (Primary Key)
- `chat_id` (Foreign Key to question_chats)
- `sender_id` (Foreign Key to users)
- `message_type` (text, status_change, file_upload)
- `content` (Message text)
- `file_path` (Optional file attachment path)
- `is_read` (Boolean)
- `created_at`

## Files Modified/Created

### New Templates
- `templates/question_chat.html` - Individual chat interface
- `templates/question_chats_list.html` - Chat list interface

### Modified Templates
- `templates/review_questionnaire.html` - Updated with new three-option interface
- `templates/dashboard_lead.html` - Updated links to new chat system
- `templates/dashboard_client.html` - Updated links to new chat system

### Modified Backend
- `app.py` - Added new models, routes, and modified review workflow
- Added new routes:
  - `/question-chat/<chat_id>` - View individual chat
  - `/question-chat/<chat_id>/send` - Send message
  - `/question-chat/<chat_id>/approve` - Approve from chat
  - `/question-chats/<product_id>` - List all chats for product

### Migration Scripts
- `migrate_question_chat.py` - Database migration script
- `test_question_chat.py` - Test script for new functionality

## Workflow Implementation

### 1. Question Submission (Client)
1. Client fills questionnaire as before
2. Questions are submitted for review

### 2. Review Process (Lead)
1. Lead reviews question in new interface
2. Three options available:
   - **Approved**: Freezes question, no chat needed
   - **Needs Revision**: Creates chat, sends message requesting more evidence
   - **Rejected**: Creates chat, allows client to re-select answer

### 3. Chat Communication
1. If "Needs Revision" or "Rejected" selected, chat is automatically created
2. Lead and client can exchange messages
3. Client can upload additional evidence files
4. Lead can approve question directly from chat interface

### 4. Question Resolution
1. **Approved**: Question is frozen, chat becomes inactive
2. **Needs Revision → Approved**: After evidence provided, lead approves via chat
3. **Rejected → Re-submission**: Client re-selects answer, new review cycle begins

## Key Differences from Old System

### Old System (Disabled)
- General communication interface
- Comments tied to responses
- Limited workflow options
- Mixed conversation threads

### New System
- Question-specific chat threads
- Clear three-option workflow
- File upload in chat
- Automatic status management
- Modern chat interface

## User Experience Improvements

### For Leads
- Clear review options with explicit consequences
- Dedicated chat per question for focused discussion
- Ability to approve directly from chat
- Better organization of conversations

### For Clients
- Clear understanding of what's needed
- Dedicated space to provide additional evidence
- Real-time chat interface
- File upload support for evidence

## Technical Implementation Details

### Security Features
- File upload validation
- User access control per chat
- Secure filename handling
- MIME type validation

### Performance Optimizations
- Database indexes on frequently queried fields
- Efficient relationship loading
- Pagination support for large chat lists

### UI/UX Features
- Responsive design for mobile and desktop
- Auto-scroll to latest messages
- Real-time message status indicators
- Keyboard shortcuts (Enter to send)

## Migration Process

1. Run `migrate_question_chat.py` to create new tables
2. Old communication routes are disabled (commented out)
3. Dashboard links updated to use new system
4. No data loss - old communication data preserved

## Testing

The implementation includes comprehensive testing:
- Database table creation
- Model relationships
- Route functionality
- File upload handling
- User permission checks

Run `python3 test_question_chat.py` to verify installation.

## Future Enhancements

Potential improvements that could be added:
- Real-time notifications
- Message search functionality
- Chat export features
- Bulk approval tools
- Mobile app integration

## Deployment Notes

1. Ensure all requirements are installed: `pip3 install -r requirements.txt`
2. Run database migration: `python3 migrate_question_chat.py`
3. Test functionality: `python3 test_question_chat.py`
4. Start application normally

The new system is fully backward compatible and doesn't affect existing questionnaire data.