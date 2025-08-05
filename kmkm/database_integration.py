"""
Database Integration Helper for SecureSphere
Integrates the comprehensive DatabaseManager with existing Flask app
"""

from database_manager import DatabaseManager
from flask import request, session, flash
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class DatabaseIntegration:
    """
    Integration layer between Flask app and DatabaseManager
    Provides convenient methods for common operations
    """
    
    def __init__(self, app=None):
        self.db_manager = DatabaseManager()
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        app.db_integration = self
    
    def save_questionnaire_response(self, form_data, product_id, user_id):
        """
        Save questionnaire response from form data
        
        Args:
            form_data: Form data from request
            product_id: Product ID
            user_id: User ID
            
        Returns:
            Response ID if successful, None otherwise
        """
        try:
            # Extract client data from form
            client_data = {
                'product_id': product_id,
                'user_id': user_id,
                'question': form_data.get('question', ''),
                'answer': form_data.get('answer', ''),
                'section': form_data.get('section', ''),
                'dimension': form_data.get('dimension', ''),
                'maturity_score': self._calculate_maturity_score(form_data.get('answer', '')),
                'comment': form_data.get('comment', ''),
                'evidence_path': self._handle_file_upload(request.files.get('evidence'))
            }
            
            response_id = self.db_manager.save_client_response(client_data)
            flash('Response saved successfully!', 'success')
            return response_id
            
        except Exception as e:
            logger.error(f"Error saving questionnaire response: {e}")
            flash('Error saving response. Please try again.', 'error')
            return None
    
    def update_questionnaire_response(self, response_id, form_data, user_id):
        """
        Update existing questionnaire response
        
        Args:
            response_id: Response ID to update
            form_data: Updated form data
            user_id: User making the update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            updates = {}
            
            if 'answer' in form_data:
                updates['answer'] = form_data['answer']
                updates['maturity_score'] = self._calculate_maturity_score(form_data['answer'])
            
            if 'comment' in form_data:
                updates['comment'] = form_data['comment']
            
            if 'evidence' in request.files:
                evidence_path = self._handle_file_upload(request.files['evidence'])
                if evidence_path:
                    updates['evidence_path'] = evidence_path
            
            if updates:
                self.db_manager.update_client_response(response_id, updates, user_id)
                flash('Response updated successfully!', 'success')
                return True
            
        except Exception as e:
            logger.error(f"Error updating questionnaire response: {e}")
            flash('Error updating response. Please try again.', 'error')
            return False
    
    def save_lead_comment(self, form_data, product_id, lead_id, client_id):
        """
        Save lead comment/communication
        
        Args:
            form_data: Form data from request
            product_id: Product ID
            lead_id: Lead user ID
            client_id: Client user ID
            
        Returns:
            Comment ID if successful, None otherwise
        """
        try:
            comm_data = {
                'product_id': product_id,
                'lead_id': lead_id,
                'client_id': client_id,
                'comment': form_data.get('comment', ''),
                'status': form_data.get('status', 'pending'),
                'response_id': form_data.get('response_id'),
                'parent_comment_id': form_data.get('parent_comment_id')
            }
            
            comment_id = self.db_manager.save_communication(comm_data)
            flash('Comment saved successfully!', 'success')
            return comment_id
            
        except Exception as e:
            logger.error(f"Error saving lead comment: {e}")
            flash('Error saving comment. Please try again.', 'error')
            return None
    
    def get_product_responses(self, product_id, user_id=None, section=None):
        """
        Get responses for a product with optional filters
        
        Args:
            product_id: Product ID
            user_id: Optional user filter
            section: Optional section filter
            
        Returns:
            List of responses
        """
        try:
            return self.db_manager.get_client_responses(product_id, user_id, section)
        except Exception as e:
            logger.error(f"Error retrieving product responses: {e}")
            return []
    
    def get_product_communications(self, product_id, client_id=None):
        """
        Get communications for a product
        
        Args:
            product_id: Product ID
            client_id: Optional client filter
            
        Returns:
            List of communications
        """
        try:
            return self.db_manager.get_communications(product_id, client_id)
        except Exception as e:
            logger.error(f"Error retrieving communications: {e}")
            return []
    
    def calculate_product_maturity(self, product_id, user_id):
        """
        Calculate maturity scores for a product
        
        Args:
            product_id: Product ID
            user_id: User ID
            
        Returns:
            Dictionary with maturity data
        """
        try:
            dimension_scores = self.db_manager.calculate_maturity_scores(product_id, user_id)
            overall_score = self.db_manager.get_overall_maturity_score(product_id, user_id)
            
            return {
                'dimension_scores': dimension_scores,
                'overall_score': overall_score,
                'maturity_level': self._get_maturity_level_name(overall_score)
            }
        except Exception as e:
            logger.error(f"Error calculating maturity scores: {e}")
            return {'dimension_scores': {}, 'overall_score': 1.0, 'maturity_level': 'Initial'}
    
    def get_dashboard_data(self, user_role, user_id=None):
        """
        Get dashboard data based on user role
        
        Args:
            user_role: User role (client, lead, superuser)
            user_id: User ID for filtering
            
        Returns:
            Dictionary with dashboard data
        """
        try:
            if user_role == 'superuser':
                return self._get_superuser_dashboard_data()
            elif user_role == 'lead':
                return self._get_lead_dashboard_data(user_id)
            else:  # client
                return self._get_client_dashboard_data(user_id)
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {}
    
    def get_audit_trail(self, user_id=None, table_name=None, limit=50):
        """
        Get audit trail for monitoring
        
        Args:
            user_id: Optional user filter
            table_name: Optional table filter
            limit: Number of records to return
            
        Returns:
            List of audit entries
        """
        try:
            return self.db_manager.get_audit_log(user_id, table_name, limit)
        except Exception as e:
            logger.error(f"Error retrieving audit trail: {e}")
            return []
    
    def backup_database(self):
        """
        Create database backup
        
        Returns:
            Backup file path if successful, None otherwise
        """
        try:
            backup_path = self.db_manager.backup_database()
            flash('Database backup created successfully!', 'success')
            return backup_path
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            flash('Error creating backup. Please try again.', 'error')
            return None
    
    def get_system_stats(self):
        """
        Get system statistics
        
        Returns:
            Dictionary with system stats
        """
        try:
            return self.db_manager.get_database_stats()
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    def _calculate_maturity_score(self, answer):
        """
        Calculate maturity score based on answer content
        Simple implementation - can be enhanced with ML/NLP
        
        Args:
            answer: Answer text
            
        Returns:
            Maturity score (1-5)
        """
        if not answer or len(answer.strip()) < 10:
            return 1
        
        answer_lower = answer.lower()
        
        # Score based on keywords and content length
        score = 1
        
        # Check for maturity indicators
        advanced_keywords = ['automated', 'continuous', 'monitoring', 'integrated', 'comprehensive']
        intermediate_keywords = ['documented', 'standardized', 'reviewed', 'tested', 'implemented']
        basic_keywords = ['basic', 'manual', 'ad-hoc', 'informal', 'limited']
        
        if any(keyword in answer_lower for keyword in advanced_keywords):
            score = max(score, 4)
        elif any(keyword in answer_lower for keyword in intermediate_keywords):
            score = max(score, 3)
        elif any(keyword in answer_lower for keyword in basic_keywords):
            score = max(score, 2)
        
        # Adjust based on length and detail
        if len(answer) > 200:
            score = min(5, score + 1)
        elif len(answer) > 100:
            score = min(5, score)
        
        return score
    
    def _handle_file_upload(self, file):
        """
        Handle file upload for evidence
        
        Args:
            file: Uploaded file
            
        Returns:
            File path if successful, None otherwise
        """
        if not file or not file.filename:
            return None
        
        try:
            # This would integrate with existing file upload logic
            # For now, return a placeholder
            filename = f"evidence_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
            return f"uploads/{filename}"
        except Exception as e:
            logger.error(f"Error handling file upload: {e}")
            return None
    
    def _get_maturity_level_name(self, score):
        """Get maturity level name from score"""
        if score >= 4.5:
            return 'Optimized'
        elif score >= 3.5:
            return 'Managed'
        elif score >= 2.5:
            return 'Defined'
        elif score >= 1.5:
            return 'Developing'
        else:
            return 'Initial'
    
    def _get_superuser_dashboard_data(self):
        """Get dashboard data for superuser"""
        stats = self.db_manager.get_database_stats()
        
        # Get recent activity
        recent_audit = self.db_manager.get_audit_log(limit=10)
        
        return {
            'total_users': stats.get('users_count', 0),
            'total_products': stats.get('products_count', 0),
            'total_responses': stats.get('questionnaire_responses_count', 0),
            'total_communications': stats.get('lead_comments_count', 0),
            'recent_activity': recent_audit,
            'database_size': stats.get('database_size_bytes', 0)
        }
    
    def _get_lead_dashboard_data(self, user_id):
        """Get dashboard data for lead"""
        # This would get lead-specific data
        return {
            'assigned_clients': [],  # Would query assigned clients
            'pending_reviews': [],   # Would query pending reviews
            'recent_communications': []  # Would query recent communications
        }
    
    def _get_client_dashboard_data(self, user_id):
        """Get dashboard data for client"""
        # This would get client-specific data
        return {
            'my_products': [],       # Would query client's products
            'pending_responses': [], # Would query pending responses
            'recent_feedback': []    # Would query recent feedback
        }

# Flask route integration examples
def integrate_with_routes(app, db_integration):
    """
    Example of how to integrate with Flask routes
    """
    
    @app.route('/api/save_response', methods=['POST'])
    def api_save_response():
        """API endpoint to save questionnaire response"""
        if 'user_id' not in session:
            return {'error': 'Not authenticated'}, 401
        
        product_id = request.form.get('product_id')
        if not product_id:
            return {'error': 'Product ID required'}, 400
        
        response_id = db_integration.save_questionnaire_response(
            request.form, product_id, session['user_id']
        )
        
        if response_id:
            return {'success': True, 'response_id': response_id}
        else:
            return {'error': 'Failed to save response'}, 500
    
    @app.route('/api/get_responses/<int:product_id>')
    def api_get_responses(product_id):
        """API endpoint to get product responses"""
        if 'user_id' not in session:
            return {'error': 'Not authenticated'}, 401
        
        user_id = request.args.get('user_id')
        section = request.args.get('section')
        
        responses = db_integration.get_product_responses(product_id, user_id, section)
        return {'responses': responses}
    
    @app.route('/api/maturity_scores/<int:product_id>/<int:user_id>')
    def api_maturity_scores(product_id, user_id):
        """API endpoint to get maturity scores"""
        if 'user_id' not in session:
            return {'error': 'Not authenticated'}, 401
        
        maturity_data = db_integration.calculate_product_maturity(product_id, user_id)
        return maturity_data
    
    @app.route('/api/audit_trail')
    def api_audit_trail():
        """API endpoint to get audit trail"""
        if session.get('role') != 'superuser':
            return {'error': 'Unauthorized'}, 403
        
        user_id = request.args.get('user_id')
        table_name = request.args.get('table_name')
        limit = int(request.args.get('limit', 50))
        
        audit_entries = db_integration.get_audit_trail(user_id, table_name, limit)
        return {'audit_entries': audit_entries}

# Usage example
if __name__ == "__main__":
    # Initialize database integration
    db_integration = DatabaseIntegration()
    
    # Example usage
    print("Database integration initialized successfully!")
    print("System stats:", db_integration.get_system_stats())