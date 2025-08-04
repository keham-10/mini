#!/usr/bin/env python3
"""
Database Migration Script for SecureSphere
Handles schema updates and data migrations.
"""

import os
import sys
from datetime import datetime, timezone
from app import app, db, User, Product, ProductStatus, QuestionnaireResponse, LeadComment, ScoreHistory, SystemSettings

def migrate_database():
    """Migrate database schema to the latest version"""
    print("🔄 Starting database migration...")
    
    with app.app_context():
        try:
            # Check if we need to add the assigned_client_id column
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            # Check users table
            user_columns = [col['name'] for col in inspector.get_columns('users')]
            if 'assigned_client_id' not in user_columns:
                print("Adding assigned_client_id column to users table...")
                with db.engine.connect() as connection:
                    connection.execute(db.text('ALTER TABLE users ADD COLUMN assigned_client_id INTEGER'))
                    connection.commit()
                print("✅ Added assigned_client_id column")
            
            # Check questionnaire_responses table
            response_columns = [col['name'] for col in inspector.get_columns('questionnaire_responses')]
            if 'is_approved' not in response_columns:
                print("Adding is_approved column to questionnaire_responses table...")
                with db.engine.connect() as connection:
                    connection.execute(db.text('ALTER TABLE questionnaire_responses ADD COLUMN is_approved BOOLEAN DEFAULT 0'))
                    connection.commit()
                print("✅ Added is_approved column")
                
            # Update organization field to have ACCORIAN as default for existing records
            print("Setting default organization to ACCORIAN for existing users...")
            users_without_org = User.query.filter(User.organization.is_(None)).all()
            for user in users_without_org:
                user.organization = 'ACCORIAN'
            
            leads_without_org = User.query.filter_by(role='lead').filter(User.organization != 'ACCORIAN').all()
            for lead in leads_without_org:
                lead.organization = 'ACCORIAN'
                
            db.session.commit()
            print("✅ Updated organization field")
            
            print("✅ Database migration completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error during database migration: {e}")
            db.session.rollback()
            return False

def main():
    """Main migration function"""
    print("🚀 Starting SecureSphere Database Migration")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        print("=" * 60)
        print("🎉 Database migration completed successfully!")
    else:
        print("=" * 60)
        print("❌ Database migration failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)