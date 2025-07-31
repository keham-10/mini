#!/usr/bin/env python3
"""
Template Error Handler for Flask Application
Provides robust error handling and fixes for Jinja2 template issues
"""

from flask import render_template, jsonify, request, current_app
from jinja2 import TemplateSyntaxError, TemplateNotFound
import traceback
import logging

def setup_template_error_handlers(app):
    """Setup comprehensive template error handlers for the Flask app"""
    
    @app.errorhandler(TemplateSyntaxError)
    def handle_template_syntax_error(error):
        """Handle Jinja2 template syntax errors"""
        error_details = {
            'error_type': 'Template Syntax Error',
            'message': str(error),
            'template': getattr(error, 'name', 'Unknown'),
            'line': getattr(error, 'lineno', 'Unknown'),
            'description': 'There is a syntax error in the Jinja2 template.'
        }
        
        # Log the error for debugging
        current_app.logger.error(f"Template Syntax Error: {error}")
        current_app.logger.error(f"Template: {error_details['template']}, Line: {error_details['line']}")
        
        # Check if it's a break tag error specifically
        if 'break' in str(error).lower():
            error_details['fix_suggestion'] = (
                "The error is caused by using '{% break %}' in a Jinja2 template. "
                "Jinja2 does not support Python break statements. "
                "Please restructure your template logic or use conditional rendering instead."
            )
        
        # Return JSON for API requests, HTML for browser requests
        if request.is_json or 'application/json' in request.headers.get('Accept', ''):
            return jsonify(error_details), 500
        else:
            try:
                return render_template('error.html', error=error_details), 500
            except:
                # Fallback if error template also has issues
                return f"""
                <html>
                <head><title>Template Error</title></head>
                <body>
                    <h1>Template Syntax Error</h1>
                    <p><strong>Error:</strong> {error_details['message']}</p>
                    <p><strong>Template:</strong> {error_details['template']}</p>
                    <p><strong>Line:</strong> {error_details['line']}</p>
                    {f"<p><strong>Fix:</strong> {error_details.get('fix_suggestion', '')}</p>" if 'fix_suggestion' in error_details else ''}
                </body>
                </html>
                """, 500
    
    @app.errorhandler(TemplateNotFound)
    def handle_template_not_found(error):
        """Handle missing template errors"""
        error_details = {
            'error_type': 'Template Not Found',
            'message': f"Template '{error.name}' not found",
            'template': error.name
        }
        
        current_app.logger.error(f"Template Not Found: {error.name}")
        
        if request.is_json or 'application/json' in request.headers.get('Accept', ''):
            return jsonify(error_details), 404
        else:
            return f"""
            <html>
            <head><title>Template Not Found</title></head>
            <body>
                <h1>Template Not Found</h1>
                <p>The template '{error.name}' could not be found.</p>
            </body>
            </html>
            """, 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle general internal server errors"""
        error_traceback = traceback.format_exc()
        
        # Check if it's a template-related error
        if 'jinja2' in error_traceback.lower() or 'template' in error_traceback.lower():
            current_app.logger.error(f"Template-related error: {error_traceback}")
            
            if request.is_json or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({
                    'error_type': 'Template Error',
                    'message': 'A template error occurred',
                    'details': str(error)
                }), 500
            else:
                return f"""
                <html>
                <head><title>Template Error</title></head>
                <body>
                    <h1>Template Error</h1>
                    <p>An error occurred while rendering the template.</p>
                    <p>Please check the application logs for more details.</p>
                </body>
                </html>
                """, 500
        
        # For non-template errors, use default handling
        current_app.logger.error(f"Internal server error: {error_traceback}")
        return "Internal Server Error", 500

def validate_template_data(data):
    """Validate data being passed to templates to prevent injection of template syntax"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and ('{%' in value or '{{' in value):
                # Log potential template injection
                current_app.logger.warning(f"Potential template syntax in data: {key} = {value[:100]}")
                # Escape the template syntax
                data[key] = value.replace('{%', '&#123;&#37;').replace('{{', '&#123;&#123;')
    elif isinstance(data, str) and ('{%' in data or '{{' in data):
        # Escape template syntax in string data
        data = data.replace('{%', '&#123;&#37;').replace('{{', '&#123;&#123;')
    
    return data

def safe_render_template(template_name, **context):
    """Safely render a template with error handling and data validation"""
    try:
        # Validate context data
        for key, value in context.items():
            context[key] = validate_template_data(value)
        
        return render_template(template_name, **context)
    except TemplateSyntaxError as e:
        current_app.logger.error(f"Template syntax error in {template_name}: {e}")
        raise
    except Exception as e:
        current_app.logger.error(f"Error rendering template {template_name}: {e}")
        raise

# Jinja2 custom filters to replace break-like functionality
def setup_custom_filters(app):
    """Setup custom Jinja2 filters to provide break-like functionality"""
    
    @app.template_filter('take')
    def take_filter(items, count):
        """Take first N items from a list (alternative to breaking out of loop)"""
        return list(items)[:count] if items else []
    
    @app.template_filter('skip')
    def skip_filter(items, count):
        """Skip first N items from a list"""
        return list(items)[count:] if items and len(items) > count else []
    
    @app.template_filter('until')
    def until_filter(items, condition_key, condition_value):
        """Take items until a condition is met (alternative to break)"""
        result = []
        for item in items:
            if hasattr(item, condition_key) and getattr(item, condition_key) == condition_value:
                break
            result.append(item)
        return result

if __name__ == "__main__":
    print("Template Error Handler module loaded successfully")
    print("Use setup_template_error_handlers(app) to enable error handling")
    print("Use setup_custom_filters(app) to add break-alternative filters")