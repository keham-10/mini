#!/usr/bin/env python3
"""
Migration script to add lead_client_associations table for many-to-many relationships
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

# Add the current directory to Python path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "securesphere.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def migrate_database():
    """Add the lead_client_associations table"""
    try:
        with app.app_context():
            # Create the association table
            print("Creating lead_client_associations table...")
            
            with db.engine.connect() as connection:
                connection.execute(db.text("""
                    CREATE TABLE IF NOT EXISTS lead_client_associations (
                        lead_id INTEGER NOT NULL,
                        client_id INTEGER NOT NULL,
                        created_at DATETIME,
                        PRIMARY KEY (lead_id, client_id),
                        FOREIGN KEY(lead_id) REFERENCES users (id),
                        FOREIGN KEY(client_id) REFERENCES users (id)
                    )
                """))
                
                # Migrate existing assignments from assigned_client_id to the new table
                print("Migrating existing client assignments...")
                
                # Get all leads with assigned clients
                result = connection.execute(db.text("""
                    SELECT id as lead_id, assigned_client_id as client_id 
                    FROM users 
                    WHERE role = 'lead' AND assigned_client_id IS NOT NULL
                """))
                existing_assignments = result.fetchall()
                
                # Insert into the new association table
                for assignment in existing_assignments:
                    try:
                        connection.execute(db.text("""
                            INSERT OR IGNORE INTO lead_client_associations (lead_id, client_id, created_at)
                            VALUES (:lead_id, :client_id, :created_at)
                        """), {
                            'lead_id': assignment.lead_id,
                            'client_id': assignment.client_id,
                            'created_at': datetime.now(timezone.utc)
                        })
                        print(f"Migrated assignment: Lead {assignment.lead_id} -> Client {assignment.client_id}")
                    except Exception as e:
                        print(f"Error migrating assignment {assignment.lead_id} -> {assignment.client_id}: {e}")
                        continue
                
                connection.commit()
            
            print("✅ Migration completed successfully!")
            print(f"✅ Migrated {len(existing_assignments)} existing assignments")
            print("✅ Lead-client assignments now support many-to-many relationships")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    print("Starting lead-client assignment migration...")
    migrate_database()
    print("Migration finished.")