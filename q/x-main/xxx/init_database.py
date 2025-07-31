#!/usr/bin/env python3
"""
Professional Database Initialization Script for SecureSphere
Creates a complete, persistent database with proper structure and sample data.
"""

import os
import sys
from datetime import datetime, timezone
from app import app, db, User, Product, ProductStatus, QuestionnaireResponse, LeadComment, ScoreHistory, SystemSettings, InvitationToken

def reset_database():
    """Completely reset the database by dropping and recreating all tables"""
    print("🔄 Resetting database - dropping all tables...")
    
    with app.app_context():
        try:
            # Drop all tables
            db.drop_all()
            print("✅ All tables dropped successfully")
            
            # Recreate all tables
            db.create_all()
            print("✅ All tables recreated successfully")
            return True
        except Exception as e:
            print(f"❌ Error resetting database: {e}")
            return False

def create_database():
    """Create all database tables"""
    print("Creating database tables...")
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created successfully")
            return True
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            return False

def create_secure_admin():
    """Create admin user with credentials from environment variables"""
    print("Creating secure admin user...")

    with app.app_context():
        try:
            # Get admin credentials from environment variables
            admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'AdminPass123')
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@securesphere.com')
            
            # Remove existing admin if any
            existing_admins = User.query.filter_by(username=admin_username).all()
            for admin_user in existing_admins:
                db.session.delete(admin_user)
            if existing_admins:
                print(f"🗑️  Removed {len(existing_admins)} existing admin user(s)")
                db.session.commit()
            
            # Create new admin
            admin = User(
                username=admin_username,
                email=admin_email,
                role='superuser',
                organization='ACCORIAN',
                first_name='System',
                last_name='Administrator',
                is_active=True,
                first_login=False
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            
            db.session.commit()
            print(f"✅ Created secure admin user: {admin_username}")
            return True

        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            db.session.rollback()
            return False

def create_system_settings():
    """Create system settings for the application"""
    print("Creating system settings...")

    settings_data = [
        {
            'key': 'app_name',
            'value': 'SecureSphere',
            'description': 'Application name displayed in the interface'
        },
        {
            'key': 'app_version',
            'value': '2.0.0',
            'description': 'Current application version'
        },
        {
            'key': 'scoring_enabled',
            'value': 'true',
            'description': 'Enable or disable scoring functionality'
        },
        {
            'key': 'max_file_size',
            'value': '10485760',  # 10MB in bytes
            'description': 'Maximum file upload size in bytes'
        },
        {
            'key': 'session_timeout',
            'value': '3600',  # 1 hour in seconds
            'description': 'User session timeout in seconds'
        },
        {
            'key': 'email_notifications',
            'value': 'true',
            'description': 'Enable email notifications'
        },
        {
            'key': 'maintenance_mode',
            'value': 'false',
            'description': 'Enable maintenance mode'
        },
        {
            'key': 'rate_limit_enabled',
            'value': 'true',
            'description': 'Enable rate limiting for API endpoints'
        },
        {
            'key': 'default_organization',
            'value': 'ACCORIAN',
            'description': 'Default organization for new users'
        }
    ]

    with app.app_context():
        try:
            for setting_data in settings_data:
                existing_setting = SystemSettings.query.filter_by(key=setting_data['key']).first()
                if existing_setting:
                    # Update existing setting
                    existing_setting.value = setting_data['value']
                    existing_setting.description = setting_data['description']
                    print(f"🔄 Updated setting: {setting_data['key']}")
                else:
                    # Create new setting
                    setting = SystemSettings(
                        key=setting_data['key'],
                        value=setting_data['value'],
                        description=setting_data['description']
                    )
                    db.session.add(setting)
                    print(f"✅ Created setting: {setting_data['key']}")

            db.session.commit()
            print("✅ System settings created successfully")
            return True

        except Exception as e:
            print(f"❌ Error creating system settings: {e}")
            db.session.rollback()
            return False

def create_sample_products():
    """Skip sample products creation - products will be created by users"""
    print("Skipping sample products creation - products will be created by users")
    return True

def verify_database():
    """Verify that the database was created correctly"""
    print("Verifying database integrity...")

    with app.app_context():
        try:
            # Check table creation using inspector
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            expected_tables = [
                'users', 'products', 'product_statuses',
                'questionnaire_responses', 'lead_comments',
                'score_history', 'system_settings', 'invitation_tokens'
            ]

            for table in expected_tables:
                if table in tables:
                    print(f"✅ Table exists: {table}")
                else:
                    print(f"❌ Table missing: {table}")
                    return False

            # Check admin user
            admin_count = User.query.filter_by(role='superuser').count()
            settings_count = SystemSettings.query.count()

            print(f"📊 Database Statistics:")
            print(f"   • Admin Users: {admin_count}")
            print(f"   • System Settings: {settings_count}")
            print(f"   • Total Users: {User.query.count()}")

            if admin_count > 0 and settings_count > 0:
                print("✅ Database verification successful")
                return True
            else:
                print("❌ Database verification failed - missing data")
                return False

        except Exception as e:
            print(f"❌ Error verifying database: {e}")
            return False

def backup_existing_database():
    """Backup existing database if it exists"""
    db_path = os.path.join('instance', 'securesphere.db')
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"✅ Existing database backed up to: {backup_path}")
            return True
        except Exception as e:
            print(f"❌ Error backing up database: {e}")
            return False
    return True

def main(reset=False):
    """Main initialization function"""
    print("🚀 Starting SecureSphere Database Initialization")
    print("=" * 60)

    # Ensure instance directory exists
    os.makedirs('instance', exist_ok=True)

    # Reset database if requested
    if reset:
        if not reset_database():
            print("❌ Database reset failed")
            return False
    else:
        # Create database (if not exists)
        if not create_database():
            print("❌ Database initialization failed")
            return False

    # Create secure admin user
    if not create_secure_admin():
        print("❌ Admin user creation failed")
        return False

    # Create system settings
    if not create_system_settings():
        print("❌ System settings creation failed")
        return False

    # Create sample products
    if not create_sample_products():
        print("❌ Product creation failed")
        return False

    # Verify database
    if not verify_database():
        print("❌ Database verification failed")
        return False

    print("=" * 60)
    print("🎉 Database initialization completed successfully!")
    print("\n📋 Admin Login Credentials:")
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    print(f"   • Username: {admin_username}")
    print("   • Password: [From environment variable ADMIN_PASSWORD]")
    print("\n🔒 Security Features Enabled:")
    print("   • Rate limiting")
    print("   • Secure file uploads")
    print("   • Client-specific lead assignments")
    print("\n⚠️  Environment Variables:")
    print("   • ADMIN_USERNAME (default: admin)")
    print("   • ADMIN_PASSWORD (default: AdminPass123)")
    print("   • ADMIN_EMAIL (default: admin@securesphere.com)")
    print("=" * 60)

    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Initialize SecureSphere Database')
    parser.add_argument('--reset', action='store_true', help='Reset database by dropping and recreating all tables')
    args = parser.parse_args()
    
    success = main(reset=args.reset)
    sys.exit(0 if success else 1)