"""
Comprehensive Database Manager for SecureSphere
Handles all client data operations with proper ID-based relationships
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Comprehensive database manager for SecureSphere application
    Handles all CRUD operations with proper relationships and data integrity
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            basedir = os.path.abspath(os.path.dirname(__file__))
            db_path = os.path.join(basedir, "instance", "securesphere.db")
        
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Ensure database and all required tables exist"""
        # Only create directories for file-based databases, not in-memory
        if self.db_path != ':memory:' and self.db_path:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            self.create_tables(conn)
    
    def create_tables(self, conn):
        """Create all required tables with proper relationships"""
        
        # Users table (clients, leads, superusers)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'client',
                organization TEXT DEFAULT 'ACCORIAN',
                assigned_client_id INTEGER,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assigned_client_id) REFERENCES users(id)
            )
        ''')
        
        # Products table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                owner_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        ''')
        
        # Questionnaire responses table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS questionnaire_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT,
                section TEXT,
                dimension TEXT,
                maturity_score INTEGER DEFAULT 1,
                comment TEXT,
                evidence_path TEXT,
                is_approved BOOLEAN DEFAULT 0,
                is_reviewed BOOLEAN DEFAULT 0,
                needs_client_response BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Lead comments table (for communication)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS lead_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                response_id INTEGER,
                lead_id INTEGER NOT NULL,
                client_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                parent_comment_id INTEGER,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (response_id) REFERENCES questionnaire_responses(id),
                FOREIGN KEY (lead_id) REFERENCES users(id),
                FOREIGN KEY (client_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (parent_comment_id) REFERENCES lead_comments(id)
            )
        ''')
        
        # User invitations table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                role TEXT NOT NULL,
                organization TEXT,
                token TEXT UNIQUE NOT NULL,
                inviter_id INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inviter_id) REFERENCES users(id)
            )
        ''')
        
        # Audit log table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                table_name TEXT NOT NULL,
                record_id INTEGER,
                old_values TEXT,
                new_values TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Maturity scores table (for detailed tracking)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS maturity_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                dimension TEXT NOT NULL,
                subdimension TEXT,
                score INTEGER NOT NULL,
                max_score INTEGER DEFAULT 5,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Create indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX IF NOT EXISTS idx_products_owner ON products(owner_id)",
            "CREATE INDEX IF NOT EXISTS idx_responses_product_user ON questionnaire_responses(product_id, user_id)",
            "CREATE INDEX IF NOT EXISTS idx_responses_section ON questionnaire_responses(section)",
            "CREATE INDEX IF NOT EXISTS idx_comments_product ON lead_comments(product_id)",
            "CREATE INDEX IF NOT EXISTS idx_comments_status ON lead_comments(status)",
            "CREATE INDEX IF NOT EXISTS idx_maturity_scores_product ON maturity_scores(product_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
        
        conn.commit()
        logger.info("Database tables and indexes created successfully")
    
    def save_client_response(self, client_data: Dict[str, Any]) -> int:
        """
        Save client questionnaire response with proper validation
        
        Args:
            client_data: Dictionary containing response data
            
        Returns:
            int: ID of saved response
        """
        required_fields = ['product_id', 'user_id', 'question', 'answer']
        for field in required_fields:
            if field not in client_data:
                raise ValueError(f"Required field '{field}' missing from client data")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Validate foreign keys exist
            self._validate_foreign_keys(conn, client_data)
            
            cursor = conn.cursor()
            
            # Insert response
            cursor.execute('''
                INSERT INTO questionnaire_responses 
                (product_id, user_id, question, answer, section, dimension, 
                 maturity_score, comment, evidence_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                client_data['product_id'],
                client_data['user_id'],
                client_data['question'],
                client_data['answer'],
                client_data.get('section'),
                client_data.get('dimension'),
                client_data.get('maturity_score', 1),
                client_data.get('comment'),
                client_data.get('evidence_path'),
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            ))
            
            response_id = cursor.lastrowid
            
            # Log the action
            self._log_action(conn, client_data['user_id'], 'INSERT', 
                           'questionnaire_responses', response_id, None, client_data)
            
            # Update maturity scores if applicable
            if client_data.get('dimension') and client_data.get('maturity_score'):
                self._update_maturity_score(conn, client_data['product_id'], 
                                          client_data['user_id'], client_data['dimension'],
                                          client_data.get('subdimension'), 
                                          client_data['maturity_score'])
            
            conn.commit()
            logger.info(f"Saved client response with ID: {response_id}")
            return response_id
    
    def update_client_response(self, response_id: int, updates: Dict[str, Any], user_id: int) -> bool:
        """
        Update existing client response
        
        Args:
            response_id: ID of response to update
            updates: Dictionary of fields to update
            user_id: ID of user making the update
            
        Returns:
            bool: True if update successful
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            # Get old values for audit
            cursor.execute('SELECT * FROM questionnaire_responses WHERE id = ?', (response_id,))
            old_record = cursor.fetchone()
            if not old_record:
                raise ValueError(f"Response with ID {response_id} not found")
            
            # Build update query
            set_clause = ', '.join([f"{key} = ?" for key in updates.keys()])
            set_clause += ', updated_at = ?'
            
            values = list(updates.values()) + [datetime.now(timezone.utc), response_id]
            
            cursor.execute(f'''
                UPDATE questionnaire_responses 
                SET {set_clause}
                WHERE id = ?
            ''', values)
            
            # Log the action
            self._log_action(conn, user_id, 'UPDATE', 'questionnaire_responses', 
                           response_id, dict(zip([desc[0] for desc in cursor.description], old_record)), updates)
            
            conn.commit()
            logger.info(f"Updated response ID: {response_id}")
            return True
    
    def get_client_responses(self, product_id: int, user_id: int = None, 
                           section: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve client responses with filters
        
        Args:
            product_id: Product ID to filter by
            user_id: Optional user ID filter
            section: Optional section filter
            
        Returns:
            List of response dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT qr.*, u.username, u.organization, p.name as product_name
                FROM questionnaire_responses qr
                JOIN users u ON qr.user_id = u.id
                JOIN products p ON qr.product_id = p.id
                WHERE qr.product_id = ?
            '''
            params = [product_id]
            
            if user_id:
                query += ' AND qr.user_id = ?'
                params.append(user_id)
            
            if section:
                query += ' AND qr.section = ?'
                params.append(section)
            
            query += ' ORDER BY qr.created_at DESC'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_communication(self, comm_data: Dict[str, Any]) -> int:
        """
        Save lead-client communication
        
        Args:
            comm_data: Communication data dictionary
            
        Returns:
            int: ID of saved communication
        """
        required_fields = ['lead_id', 'client_id', 'product_id', 'comment']
        for field in required_fields:
            if field not in comm_data:
                raise ValueError(f"Required field '{field}' missing from communication data")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO lead_comments 
                (response_id, lead_id, client_id, product_id, comment, status, 
                 parent_comment_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                comm_data.get('response_id'),
                comm_data['lead_id'],
                comm_data['client_id'],
                comm_data['product_id'],
                comm_data['comment'],
                comm_data.get('status', 'pending'),
                comm_data.get('parent_comment_id'),
                datetime.now(timezone.utc),
                datetime.now(timezone.utc)
            ))
            
            comment_id = cursor.lastrowid
            
            # Log the action
            self._log_action(conn, comm_data['lead_id'], 'INSERT', 
                           'lead_comments', comment_id, None, comm_data)
            
            conn.commit()
            logger.info(f"Saved communication with ID: {comment_id}")
            return comment_id
    
    def get_communications(self, product_id: int, client_id: int = None) -> List[Dict[str, Any]]:
        """
        Retrieve communications for a product
        
        Args:
            product_id: Product ID
            client_id: Optional client ID filter
            
        Returns:
            List of communication dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT lc.*, 
                       l.username as lead_username, l.email as lead_email,
                       c.username as client_username, c.email as client_email,
                       qr.question, qr.section, qr.dimension
                FROM lead_comments lc
                JOIN users l ON lc.lead_id = l.id
                JOIN users c ON lc.client_id = c.id
                LEFT JOIN questionnaire_responses qr ON lc.response_id = qr.id
                WHERE lc.product_id = ?
            '''
            params = [product_id]
            
            if client_id:
                query += ' AND lc.client_id = ?'
                params.append(client_id)
            
            query += ' ORDER BY lc.created_at DESC'
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def calculate_maturity_scores(self, product_id: int, user_id: int) -> Dict[str, float]:
        """
        Calculate maturity scores by dimension for a user's product
        
        Args:
            product_id: Product ID
            user_id: User ID
            
        Returns:
            Dictionary of dimension scores
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT dimension, AVG(CAST(maturity_score as FLOAT)) as avg_score,
                       COUNT(*) as response_count
                FROM questionnaire_responses 
                WHERE product_id = ? AND user_id = ? AND dimension IS NOT NULL
                GROUP BY dimension
            ''', (product_id, user_id))
            
            results = cursor.fetchall()
            return {row[0]: {'average': row[1], 'count': row[2]} for row in results}
    
    def get_overall_maturity_score(self, product_id: int, user_id: int) -> float:
        """
        Calculate overall maturity score for a user's product
        
        Args:
            product_id: Product ID
            user_id: User ID
            
        Returns:
            Overall maturity score (1-5 scale)
        """
        dimension_scores = self.calculate_maturity_scores(product_id, user_id)
        if not dimension_scores:
            return 1.0
        
        total_score = sum(data['average'] for data in dimension_scores.values())
        return round(total_score / len(dimension_scores), 2)
    
    def _validate_foreign_keys(self, conn, data: Dict[str, Any]):
        """Validate that foreign key references exist"""
        cursor = conn.cursor()
        
        if 'product_id' in data:
            cursor.execute('SELECT id FROM products WHERE id = ?', (data['product_id'],))
            if not cursor.fetchone():
                raise ValueError(f"Product with ID {data['product_id']} does not exist")
        
        if 'user_id' in data:
            cursor.execute('SELECT id FROM users WHERE id = ?', (data['user_id'],))
            if not cursor.fetchone():
                raise ValueError(f"User with ID {data['user_id']} does not exist")
    
    def _update_maturity_score(self, conn, product_id: int, user_id: int, 
                              dimension: str, subdimension: str = None, score: int = 1):
        """Update or insert maturity score record"""
        cursor = conn.cursor()
        
        # Check if record exists
        cursor.execute('''
            SELECT id FROM maturity_scores 
            WHERE product_id = ? AND user_id = ? AND dimension = ? AND subdimension = ?
        ''', (product_id, user_id, dimension, subdimension))
        
        if cursor.fetchone():
            # Update existing
            cursor.execute('''
                UPDATE maturity_scores 
                SET score = ?, calculated_at = ?
                WHERE product_id = ? AND user_id = ? AND dimension = ? AND subdimension = ?
            ''', (score, datetime.now(timezone.utc), product_id, user_id, dimension, subdimension))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO maturity_scores 
                (product_id, user_id, dimension, subdimension, score, calculated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (product_id, user_id, dimension, subdimension, score, datetime.now(timezone.utc)))
    
    def _log_action(self, conn, user_id: int, action: str, table_name: str, 
                   record_id: int, old_values: Dict = None, new_values: Dict = None):
        """Log action to audit table"""
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_log 
            (user_id, action, table_name, record_id, old_values, new_values, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, action, table_name, record_id,
            json.dumps(old_values) if old_values else None,
            json.dumps(new_values) if new_values else None,
            datetime.now(timezone.utc)
        ))
    
    def get_audit_log(self, user_id: int = None, table_name: str = None, 
                     limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve audit log entries
        
        Args:
            user_id: Optional user filter
            table_name: Optional table filter
            limit: Maximum number of records
            
        Returns:
            List of audit log entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT al.*, u.username 
                FROM audit_log al
                LEFT JOIN users u ON al.user_id = u.id
                WHERE 1=1
            '''
            params = []
            
            if user_id:
                query += ' AND al.user_id = ?'
                params.append(user_id)
            
            if table_name:
                query += ' AND al.table_name = ?'
                params.append(table_name)
            
            query += ' ORDER BY al.timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def backup_database(self, backup_path: str = None) -> str:
        """
        Create a backup of the database
        
        Args:
            backup_path: Optional custom backup path
            
        Returns:
            Path to backup file
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}.backup_{timestamp}"
        
        with sqlite3.connect(self.db_path) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dictionary with database statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Get list of existing tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            # Table counts
            tables = ['users', 'products', 'questionnaire_responses', 
                     'lead_comments', 'user_invitations', 'audit_log', 'maturity_scores']
            
            for table in tables:
                if table in existing_tables:
                    cursor.execute(f'SELECT COUNT(*) FROM {table}')
                    stats[f'{table}_count'] = cursor.fetchone()[0]
                else:
                    stats[f'{table}_count'] = 0
            
            # Database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            stats['database_size_bytes'] = cursor.fetchone()[0]
            
            # Recent activity (only if audit_log table exists)
            if 'audit_log' in existing_tables:
                cursor.execute('SELECT COUNT(*) FROM audit_log WHERE timestamp > datetime("now", "-24 hours")')
                stats['recent_activity_24h'] = cursor.fetchone()[0]
            else:
                stats['recent_activity_24h'] = 0
            
            return stats

# Example usage and testing
if __name__ == "__main__":
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Example client data
    sample_client_data = {
        'product_id': 1,
        'user_id': 1,
        'question': 'What security measures do you have in place?',
        'answer': 'We have firewalls and antivirus software',
        'section': 'Build and Deployment',
        'dimension': 'Infrastructure Security',
        'maturity_score': 3,
        'comment': 'Basic security measures implemented'
    }
    
    try:
        # Test saving client response
        response_id = db_manager.save_client_response(sample_client_data)
        print(f"Saved response with ID: {response_id}")
        
        # Test retrieving responses
        responses = db_manager.get_client_responses(product_id=1)
        print(f"Retrieved {len(responses)} responses")
        
        # Test maturity score calculation
        scores = db_manager.calculate_maturity_scores(product_id=1, user_id=1)
        print(f"Maturity scores: {scores}")
        
        # Test database stats
        stats = db_manager.get_database_stats()
        print(f"Database stats: {stats}")
        
    except Exception as e:
        logger.error(f"Error testing database operations: {e}")