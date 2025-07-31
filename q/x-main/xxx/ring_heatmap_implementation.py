# Ring Heatmap Implementation and Rejected Questions Workflow
# This module contains the implementation for the 5-level ring-based heatmap
# and the rejected questions workflow

import json
import math
from flask import request, jsonify, session
from datetime import datetime

class RingHeatmapGenerator:
    """Generates data for 5-level ring-based heatmap visualization"""
    
    def __init__(self):
        self.levels = 5
        self.colors = {
            1: '#ff4444',  # Red - Initial
            2: '#ff8800',  # Orange - Developing  
            3: '#ffcc00',  # Yellow - Defined
            4: '#88cc00',  # Light Green - Managed
            5: '#44cc44'   # Green - Optimized
        }
    
    def generate_ring_data(self, subdimension_scores):
        """Generate data structure for ring-based heatmap"""
        ring_data = {
            'levels': [],
            'dimensions': [],
            'center_score': 0
        }
        
        if not subdimension_scores:
            return ring_data
        
        # Calculate overall score
        total_score = sum(data['average_score'] for data in subdimension_scores.values())
        overall_score = total_score / len(subdimension_scores)
        ring_data['center_score'] = round(overall_score)
        
        # Group dimensions by their maturity level (1-5)
        dimensions_by_level = {i: [] for i in range(1, 6)}
        
        for dimension, data in subdimension_scores.items():
            level = max(1, min(5, round(data['average_score'])))
            dimensions_by_level[level].append({
                'name': dimension,
                'score': data['average_score'],
                'level': level
            })
        
        # Generate ring segments for each level
        for level in range(1, 6):
            dimensions = dimensions_by_level[level]
            ring_data['levels'].append({
                'level': level,
                'color': self.colors[level],
                'dimensions': dimensions,
                'count': len(dimensions)
            })
        
        # Flatten dimensions list
        for level_data in ring_data['levels']:
            ring_data['dimensions'].extend(level_data['dimensions'])
        
        return ring_data

class RejectedQuestionsManager:
    """Manages the rejected questions workflow"""
    
    def __init__(self, db):
        self.db = db
    
    def create_rejected_question_entry(self, question_id, product_id, user_id, lead_id, reason=""):
        """Create a new rejected question entry"""
        try:
            # Import here to avoid circular imports
            from app import RejectedQuestion
            
            # Get the response to get question text
            from app import QuestionnaireResponse
            response = QuestionnaireResponse.query.get(question_id)  # question_id is actually response_id
            if not response:
                print('Response not found for question_id:', question_id)
                return None
                
            rejected_question = RejectedQuestion(
                response_id=question_id,  # question_id is actually response_id
                product_id=product_id,
                user_id=user_id,
                lead_id=lead_id,
                question_text=response.question,
                reason=reason,
                status='pending',
                created_at=datetime.utcnow()
            )
            
            self.db.session.add(rejected_question)
            self.db.session.commit()
            return rejected_question
            
        except Exception as e:
            print(f"Error creating rejected question entry: {e}")
            return None
    
    def get_rejected_questions_for_user(self, user_id, product_id):
        """Get all pending rejected questions for a user and product"""
        try:
            from app import RejectedQuestion, Question
            
            from app import QuestionnaireResponse
            rejected_questions = self.db.session.query(RejectedQuestion, QuestionnaireResponse).join(
                QuestionnaireResponse, RejectedQuestion.response_id == QuestionnaireResponse.id
            ).filter(
                RejectedQuestion.user_id == user_id,
                RejectedQuestion.product_id == product_id,
                RejectedQuestion.status == 'pending'
            ).all()
            
            return rejected_questions
            
        except Exception as e:
            print(f"Error getting rejected questions: {e}")
            return []
    
    def update_rejected_question_response(self, rejected_question_id, new_option, user_id):
        """Update the response for a rejected question"""
        try:
            from app import RejectedQuestion, Response
            
            # Get the rejected question
            rejected_question = RejectedQuestion.query.get(rejected_question_id)
            if not rejected_question or rejected_question.user_id != user_id:
                return False
            
            # Update the original response with new option
            from app import QuestionnaireResponse
            response = QuestionnaireResponse.query.get(rejected_question.response_id)
            
            if response:
                response.selected_option = new_option
                response.updated_at = datetime.utcnow()
                
                # Mark rejected question as resolved
                rejected_question.status = 'resolved'
                rejected_question.new_option = new_option
                rejected_question.resolved_at = datetime.utcnow()
                
                self.db.session.commit()
                return True
                
        except Exception as e:
            print(f"Error updating rejected question response: {e}")
            return False
    
    def recalculate_scores_after_update(self, product_id, user_id):
        """Recalculate all scores after a rejected question is updated"""
        try:
            # Import the score calculation function
            from app import calculate_maturity_scores
            
            # This would call the existing score calculation function
            # We need to ensure it recalculates based on the updated responses
            scores = calculate_maturity_scores(product_id, user_id)
            return scores
            
        except Exception as e:
            print(f"Error recalculating scores: {e}")
            return None

def get_dimension_wise_results(subdimension_scores):
    """Convert sub-dimension results to dimension-wise results"""
    dimension_results = {}
    
    for subdimension, data in subdimension_scores.items():
        # Extract main dimension from subdimension name
        # Assuming subdimension names follow pattern like "Access Control - Authentication"
        if " - " in subdimension:
            main_dimension = subdimension.split(" - ")[0]
        else:
            main_dimension = subdimension
        
        if main_dimension not in dimension_results:
            dimension_results[main_dimension] = {
                'subdimensions': [],
                'total_score': 0,
                'count': 0,
                'average_score': 0
            }
        
        dimension_results[main_dimension]['subdimensions'].append({
            'name': subdimension,
            'score': data['average_score']
        })
        dimension_results[main_dimension]['total_score'] += data['average_score']
        dimension_results[main_dimension]['count'] += 1
    
    # Calculate average scores for each dimension
    for dimension in dimension_results:
        if dimension_results[dimension]['count'] > 0:
            dimension_results[dimension]['average_score'] = (
                dimension_results[dimension]['total_score'] / 
                dimension_results[dimension]['count']
            )
    
    return dimension_results
