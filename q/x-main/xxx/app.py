import os
import csv
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timezone
import hashlib
# Try to import magic for MIME type detection, but make it optional
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

# Add import for generating random tokens
import secrets
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey-change-in-production')

# Import and setup template error handlers
try:
    from template_error_handler import setup_template_error_handlers, setup_custom_filters
    setup_template_error_handlers(app)
    setup_custom_filters(app)
    print("✅ Template error handlers and custom filters loaded")
except ImportError:
    print("⚠️  Template error handler not found, using default error handling")

# Security Configuration
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)
limiter.init_app(app)

# Database Configuration - Professional Setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "securesphere.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_timeout': 20,
    'pool_recycle': -1,
    'pool_pre_ping': True
}
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
ALLOWED_EXTENSIONS = {'csv', 'txt', 'pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xlsx', 'zip'}
ALLOWED_MIME_TYPES = {
    'text/csv', 'text/plain', 'application/pdf', 'image/jpeg', 'image/png',
    'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/zip'
}

# Email Configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@securesphere.com')

# Ensure instance and upload directories exist
os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
mail = Mail(app)

# Custom Jinja2 filter for question numbering
@app.template_filter('question_number')
def question_number_filter(question_text):
    """Get the question number for a given question text"""
    return get_question_number_from_csv(question_text)

# ==================== DATABASE MODELS ====================

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='client')  # client, lead, superuser
    organization = db.Column(db.String(200), default='ACCORIAN')
    assigned_client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # For leads - which client they can review
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    first_login = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    # Relationships
    products = db.relationship('Product', backref='owner', lazy=True, cascade='all, delete-orphan')
    responses = db.relationship('QuestionnaireResponse', backref='user', lazy=True)
    assigned_client = db.relationship('User', remote_side=[id], backref='assigned_leads', foreign_keys=[assigned_client_id])
    
    def can_access_client_data(self, client_id):
        """Check if this user can access data for a specific client"""
        if self.role == 'superuser':
            return True
        elif self.role == 'lead':
            return self.assigned_client_id == client_id
        elif self.role == 'client':
            return self.id == client_id
        return False
    
    def get_accessible_clients(self):
        """Get list of clients this user can access"""
        if self.role == 'superuser':
            return User.query.filter_by(role='client', is_active=True).all()
        elif self.role == 'lead' and self.assigned_client_id:
            client = User.query.filter_by(id=self.assigned_client_id, role='client', is_active=True).first()
            return [client] if client else []
        elif self.role == 'client':
            return [self]
        return []

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    product_url = db.Column(db.String(500), nullable=False)
    programming_language = db.Column(db.String(100), nullable=False)
    cloud_platform = db.Column(db.String(100), nullable=False)
    cloud_platform_other = db.Column(db.String(200))
    cicd_platform = db.Column(db.String(100), nullable=False)
    additional_details = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    responses = db.relationship('QuestionnaireResponse', backref='product', lazy=True, cascade='all, delete-orphan')
    statuses = db.relationship('ProductStatus', backref='product', lazy=True, cascade='all, delete-orphan')
    scores = db.relationship('ScoreHistory', backref='product', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Product {self.name}>'

class ProductStatus(db.Model):
    __tablename__ = 'product_statuses'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='in_progress')  # in_progress, questions_done, under_review, review_done, completed, needs_client_response
    questions_completed = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    completion_percentage = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Composite index for better performance
    __table_args__ = (db.Index('idx_product_user', 'product_id', 'user_id'),)

    def __repr__(self):
        return f'<ProductStatus {self.product_id}-{self.user_id}: {self.status}>'

class QuestionnaireResponse(db.Model):
    __tablename__ = 'questionnaire_responses'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    section = db.Column(db.String(100), nullable=False)
    question = db.Column(db.Text, nullable=False)
    question_index = db.Column(db.Integer)  # For ordering
    answer = db.Column(db.String(500))
    client_comment = db.Column(db.Text)
    evidence_path = db.Column(db.String(500))
    score = db.Column(db.Integer, default=0)
    max_score = db.Column(db.Integer, default=0)
    is_reviewed = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)  # Final approval status for the question
    needs_client_response = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    lead_comments = db.relationship('LeadComment', backref='response', lazy=True, cascade='all, delete-orphan')

    # Composite indexes for better performance
    __table_args__ = (
        db.Index('idx_user_product', 'user_id', 'product_id'),
        db.Index('idx_section', 'section'),
        db.Index('idx_needs_response', 'needs_client_response'),
    )

    def __repr__(self):
        return f'<Response {self.id}: {self.section}>'

class LeadComment(db.Model):
    __tablename__ = 'lead_comments'

    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey('questionnaire_responses.id'))
    lead_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, needs_revision, rejected, client_reply
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('lead_comments.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    parent_comment = db.relationship('LeadComment', remote_side=[id], backref='replies')
    lead = db.relationship('User', foreign_keys=[lead_id], backref='lead_comments_made')
    client = db.relationship('User', foreign_keys=[client_id], backref='lead_comments_received')
    product = db.relationship('Product', backref='lead_comments')

    # Indexes for better performance
    __table_args__ = (
        db.Index('idx_client_read', 'client_id', 'is_read'),
        db.Index('idx_status', 'status'),
    )

    def __repr__(self):
        return f'<LeadComment {self.id}: {self.status}>'

class ScoreHistory(db.Model):
    __tablename__ = 'score_history'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    section_name = db.Column(db.String(100), nullable=False)
    total_score = db.Column(db.Integer, default=0)
    max_score = db.Column(db.Integer, default=0)
    percentage = db.Column(db.Float, default=0.0)
    questions_answered = db.Column(db.Integer, default=0)
    questions_total = db.Column(db.Integer, default=0)
    calculated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Composite index for better performance
    __table_args__ = (db.Index('idx_product_user_section', 'product_id', 'user_id', 'section_name'),)

    def __repr__(self):
        return f'<ScoreHistory {self.product_id}-{self.section_name}: {self.percentage}%>'

class SystemSettings(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<SystemSettings {self.key}: {self.value}>'

class InvitationToken(db.Model):
    __tablename__ = 'invitation_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False)  # client or lead
    organization = db.Column(db.String(200))
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    used_at = db.Column(db.DateTime)

    # Relationships
    inviter = db.relationship('User', backref='sent_invitations')

    def is_expired(self):
        # Ensure both datetimes are timezone-aware for comparison
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at

        # Handle timezone conversion more robustly
        if expires_at is None:
            return True  # If no expiration date, consider it expired

        # If expires_at is naive, make it timezone-aware (assume UTC)
        if expires_at.tzinfo is None or expires_at.tzinfo.utcoffset(expires_at) is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        # Convert both to UTC for comparison
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        else:
            now = now.astimezone(timezone.utc)

        if expires_at.tzinfo != timezone.utc:
            expires_at = expires_at.astimezone(timezone.utc)

        return now > expires_at

    def __repr__(self):
        return f'<InvitationToken {self.email}: {self.role}>'


class RejectedQuestion(db.Model):
    __tablename__ = "rejected_questions"

    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey("questionnaire_responses.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)  # Store question text directly
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")  # pending, resolved, cancelled
    new_option = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = db.Column(db.DateTime)

    # Relationships
    response = db.relationship("QuestionnaireResponse", backref="rejected_questions")
    product = db.relationship("Product", backref="rejected_questions")
    user = db.relationship("User", foreign_keys=[user_id], backref="rejected_questions_as_client")
    lead = db.relationship("User", foreign_keys=[lead_id], backref="rejected_questions_as_lead")

    def __repr__(self):
        return f"<RejectedQuestion {self.id}: {self.question_text[:50]}... by U{self.user_id}>"



def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_security(file):
    """Comprehensive file security validation"""
    if not file or not file.filename:
        return False, "No file provided"
    
    # Check file extension
    if not allowed_file(file.filename):
        return False, "File type not allowed"
    
    # Check file size (additional check beyond Flask's MAX_CONTENT_LENGTH)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > 10 * 1024 * 1024:  # 10MB
        return False, "File too large (max 10MB)"
    
    if file_size == 0:
        return False, "Empty file not allowed"
    
    # Try to detect MIME type
    try:
        # Read first 2048 bytes for MIME detection
        file_data = file.read(2048)
        file.seek(0)  # Reset to beginning
        
        # Basic magic number checks for common file types
        if file.filename.lower().endswith(('.jpg', '.jpeg')):
            if not file_data.startswith(b'\xff\xd8\xff'):
                return False, "Invalid JPEG file"
        elif file.filename.lower().endswith('.png'):
            if not file_data.startswith(b'\x89PNG\r\n\x1a\n'):
                return False, "Invalid PNG file"
        elif file.filename.lower().endswith('.pdf'):
            if not file_data.startswith(b'%PDF'):
                return False, "Invalid PDF file"
        
    except Exception as e:
        print(f"File validation error: {e}")
        return False, "File validation failed"
    
    return True, "File validation passed"

def secure_filename_hash(filename):
    """Generate a secure filename with hash to prevent conflicts"""
    if not filename:
        return None
    
    # Get file extension
    ext = ''
    if '.' in filename:
        ext = '.' + filename.rsplit('.', 1)[1].lower()
    
    # Create hash of original filename + timestamp
    hash_input = f"{filename}_{datetime.now().isoformat()}".encode('utf-8')
    file_hash = hashlib.sha256(hash_input).hexdigest()[:16]
    
    return f"{file_hash}{ext}"

def send_invitation_email(email, role, invitation_link, inviter_name):
    """Send invitation email to new user"""
    try:
        subject = f"Invitation to join SecureSphere as {role.title()}"

        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }}
                .btn {{ display: inline-block; background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; }}
                .btn:hover {{ background: #1e40af; }}
                .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 14px; color: #6b7280; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛡️ SecureSphere</h1>
                    <h2>You're Invited!</h2>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p><strong>{inviter_name}</strong> has invited you to join <strong>SecureSphere</strong> as a <strong>{role.title()}</strong>.</p>
                    <p>SecureSphere is a comprehensive security assessment platform that helps organizations evaluate and improve their security posture.</p>

                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invitation_link}" class="btn">Accept Invitation & Register</a>
                    </div>

                    <p><strong>What happens next?</strong></p>
                    <ul>
                        <li>Click the button above to access the registration page</li>
                        <li>Create your account with your preferred username and password</li>
                        <li>Start using SecureSphere immediately</li>
                    </ul>

                    <p><strong>Note:</strong> This invitation link will expire in 7 days for security purposes.</p>

                    <div class="footer">
                        <p>If you're having trouble with the button above, copy and paste this link into your browser:</p>
                        <p><a href="{invitation_link}">{invitation_link}</a></p>
                        <p>This invitation was sent to {email}. If you didn't expect this invitation, you can safely ignore this email.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        SecureSphere Invitation

        Hello,

        {inviter_name} has invited you to join SecureSphere as a {role.title()}.

        To accept this invitation and create your account, please visit:
        {invitation_link}

        This invitation link will expire in 7 days.

        If you didn't expect this invitation, you can safely ignore this email.

        Best regards,
        The SecureSphere Team
        """

        msg = Message(
            subject=subject,
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[email],
            body=text_body,
            html=html_body
        )

        mail.send(msg)
        return True

    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def load_questionnaire():
    sections = {}
    csv_path = os.path.join(os.path.dirname(__file__), 'devweb.csv')
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        current_dimension = None
        current_question_obj = None
        for row in reader:
            dimension = row['Dimensions'].strip()
            question = row['Questions'].strip()
            description = row['Description'].strip()
            option = row['Options'].strip()
            # New dimension starts
            if dimension:
                current_dimension = dimension
                if current_dimension not in sections:
                    sections[current_dimension] = []
            # New question starts
            if question:
                # Save previous question to section (if exists)
                if current_question_obj:
                    sections[current_dimension].append(current_question_obj)
                current_question_obj = {
                    'question': question,
                    'description': description,
                    'options': []
                }
            # Add option to current question
            if current_question_obj is not None and option:
                current_question_obj['options'].append(option)
        # Add last question
        if current_question_obj:
            sections[current_dimension].append(current_question_obj)
    return sections

# Load questionnaire data
QUESTIONNAIRE = load_questionnaire()
SECTION_IDS = list(QUESTIONNAIRE.keys())

# Database initialization
def init_database():
    """Initialize database and create tables if they don't exist"""
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables initialized")
        except Exception as e:
            print(f"❌ Error initializing database: {e}")

        # Fix any existing naive datetime entries
        try:
            fix_naive_datetimes()
        except Exception as e:
            print(f"⚠️ Warning: Could not fix naive datetimes: {e}")

        # Ensure default admin user exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("Creating default admin user...")
            admin = User(
                username='admin',
                email='admin@securesphere.com',
                role='superuser',
                organization='SecureSphere Inc.',
                first_name='System',
                last_name='Administrator'
            )
            admin.set_password('AdminPass123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin user created")

def fix_naive_datetimes():
    """Fix any naive datetime entries in the database"""
    print("🔧 Checking for naive datetime entries...")

    # Fix InvitationToken entries
    invitations = InvitationToken.query.all()
    fixed_count = 0

    for invitation in invitations:
        needs_update = False

        # Fix expires_at if it's naive
        if invitation.expires_at and (invitation.expires_at.tzinfo is None or
                                    invitation.expires_at.tzinfo.utcoffset(invitation.expires_at) is None):
            invitation.expires_at = invitation.expires_at.replace(tzinfo=timezone.utc)
            needs_update = True

        # Fix created_at if it's naive
        if invitation.created_at and (invitation.created_at.tzinfo is None or
                                    invitation.created_at.tzinfo.utcoffset(invitation.created_at) is None):
            invitation.created_at = invitation.created_at.replace(tzinfo=timezone.utc)
            needs_update = True

        # Fix used_at if it's naive
        if invitation.used_at and (invitation.used_at.tzinfo is None or
                                 invitation.used_at.tzinfo.utcoffset(invitation.used_at) is None):
            invitation.used_at = invitation.used_at.replace(tzinfo=timezone.utc)
            needs_update = True

        if needs_update:
            fixed_count += 1

    if fixed_count > 0:
        db.session.commit()
        print(f"✅ Fixed {fixed_count} naive datetime entries")
    else:
        print("✅ No naive datetime entries found")

def calculate_score_for_answer(question, answer):
    """Calculate score for a specific question-answer pair based on CSV data"""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'devweb.csv')
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            current_question = None
            question_scores = {}

            for row in reader:
                q = row['Questions'].strip()
                option = row['Options'].strip()
                scores_text = row.get('Scores', '').strip()

                # Track current question
                if q:
                    current_question = q
                    question_scores = {}

                # Store score for each option of current question
                if current_question and option and scores_text:
                    try:
                        score = int(scores_text)
                        question_scores[option] = score
                    except (ValueError, TypeError):
                        pass

                # Check if we found a match for our question and answer
                if current_question == question and answer in question_scores:
                    return question_scores[answer] * 20  # Scale 1-5 to 20-100 scoring system

    except FileNotFoundError:
        print("CSV file not found, using default scoring")

    # Default scoring based on option letter if CSV parsing fails
    if answer.startswith('A)'):
        return 20  # Lowest score (1*20)
    elif answer.startswith('B)'):
        return 40  # (2*20)
    elif answer.startswith('C)'):
        return 60  # (3*20)
    elif answer.startswith('D)'):
        return 80  # (4*20)
    elif answer.startswith('E)'):
        return 100  # Highest score (5*20)
    else:
        # Fallback to original logic
        if answer.lower() in ['yes', 'fully implemented', 'high']:
            return 100
        elif answer.lower() in ['partially', 'medium']:
            return 50
        elif answer.lower() in ['no', 'not implemented', 'low']:
            return 20
        else:
            return 25

def update_product_status(product_id, user_id):
    """Update product status based on current responses and reviews"""
    status_record = ProductStatus.query.filter_by(product_id=product_id, user_id=user_id).first()
    if not status_record:
        status_record = ProductStatus(product_id=product_id, user_id=user_id)
        db.session.add(status_record)

    # Count total questions and answered questions
    total_questions = sum(len(questions) for questions in QUESTIONNAIRE.values())
    answered_questions = QuestionnaireResponse.query.filter_by(
        product_id=product_id, user_id=user_id
    ).count()

    # Count reviewed questions (with safety check for is_reviewed column)
    try:
        reviewed_questions = QuestionnaireResponse.query.filter_by(
            product_id=product_id, user_id=user_id, is_reviewed=True
        ).count()
    except Exception:
        # If is_reviewed column doesn't exist yet, assume no questions are reviewed
        reviewed_questions = 0

    # Update status based on progress
    if answered_questions == 0:
        status_record.status = 'in_progress'
    elif answered_questions == total_questions and reviewed_questions == 0:
        status_record.status = 'questions_done'
    elif reviewed_questions > 0 and reviewed_questions < answered_questions:
        status_record.status = 'under_review'
    elif reviewed_questions == answered_questions and answered_questions == total_questions:
        # Check if all reviews are approved
        approved_count = db.session.query(LeadComment).join(QuestionnaireResponse).filter(
            QuestionnaireResponse.product_id == product_id,
            QuestionnaireResponse.user_id == user_id,
            LeadComment.status == 'approved'
        ).count()

        if approved_count == answered_questions:
            status_record.status = 'completed'
        else:
            status_record.status = 'review_done'
    else:
        status_record.status = 'in_progress'

    status_record.questions_completed = answered_questions
    status_record.total_questions = total_questions
    status_record.last_updated = datetime.utcnow()

    db.session.commit()
    return status_record.status

def calculate_and_store_scores(product_id, user_id):
    """Calculate scores for all sections and store in ScoreHistory with proper mathematical logic"""
    responses = QuestionnaireResponse.query.filter_by(
        product_id=product_id, user_id=user_id
    ).all()

    section_data = {}

    # Group responses by section and calculate scores
    for response in responses:
        section = response.section
        if section not in section_data:
            section_data[section] = {
                'scores': [],
                'questions_count': 0,
                'total_score': 0
            }

        # Calculate score for this response (1-5 scale from CSV)
        raw_score = calculate_score_for_answer(response.question, response.answer)
        # Convert from 20-100 scale back to 1-5 scale for proper averaging
        normalized_score = raw_score / 20 if raw_score > 0 else 0
        
        try:
            response.score = raw_score  # Store the raw score for compatibility
        except Exception:
            # If score column doesn't exist yet, skip setting it
            pass
            
        section_data[section]['scores'].append(normalized_score)
        section_data[section]['questions_count'] += 1

    # Calculate average dimension scores using mathematical formula
    section_averages = {}
    for section, data in section_data.items():
        if data['questions_count'] > 0:
            # Average Dimension Score = Sum of scores / Number of questions
            average_score = sum(data['scores']) / data['questions_count']
            section_averages[section] = average_score
            
            # Convert back to percentage (1-5 scale to 0-100%)
            percentage = (average_score / 5.0) * 100
            
            # Remove old score record for this section
            ScoreHistory.query.filter_by(
                product_id=product_id, user_id=user_id, section_name=section
            ).delete()

            # Add new score record
            score_record = ScoreHistory(
                product_id=product_id,
                user_id=user_id,
                section_name=section,
                total_score=int(average_score * 20),  # Store as 20-100 scale for compatibility
                max_score=100,  # Max possible is 5*20 = 100
                percentage=percentage,
                questions_answered=data['questions_count'],
                questions_total=data['questions_count']
            )
            db.session.add(score_record)

    db.session.commit()
    return section_averages

def calculate_overall_maturity_score(product_id, user_id):
    """
    Calculate overall maturity score using proper mathematical formulas:
    1. Average Dimension Score = Sum of scores for all questions in dimension / Number of questions in dimension  
    2. Overall Maturity Score = Sum of average scores of all dimensions / Number of dimensions
    """
    # Get all responses for this product and user
    responses = QuestionnaireResponse.query.filter_by(
        product_id=product_id, user_id=user_id
    ).all()
    
    if not responses:
        return 0, {}
    
    # Group responses by dimension/section
    dimension_questions = {}
    
    for response in responses:
        dimension = response.section
        if dimension not in dimension_questions:
            dimension_questions[dimension] = []
        
        # Calculate score for this question (1-5 scale based on CSV)
        question_score = calculate_question_score_from_csv(response.question, response.answer)
        dimension_questions[dimension].append({
            'question': response.question,
            'answer': response.answer,
            'score': question_score
        })
    
    # Calculate average dimension scores and overall score
    dimension_averages = []
    section_data = {}
    
    for dimension, questions in dimension_questions.items():
        # Average Dimension Score = Sum of scores for all questions in dimension / Number of questions in dimension
        total_score = sum(q['score'] for q in questions)
        num_questions = len(questions)
        average_dimension_score = total_score / num_questions if num_questions > 0 else 0
        
        dimension_averages.append(average_dimension_score)
        section_data[dimension] = {
            'average_score': round(average_dimension_score, 2),
            'maturity_score': round(average_dimension_score, 2),
            'questions_count': num_questions,
            'total_score': total_score,
            'questions': questions
        }
    
    # Overall Maturity Score = Sum of average scores of all dimensions / Number of dimensions
    if len(dimension_averages) > 0:
        overall_score = sum(dimension_averages) / len(dimension_averages)
    else:
        overall_score = 0
    
    return round(overall_score, 2), section_data

def calculate_subdimension_scores(product_id, user_id):
    """
    Calculate scores by sub-dimensions using the same logic: (question score / total questions)
    Returns a dictionary with sub-dimension names as keys and their calculated scores
    """
    # Get all responses for this product and user
    responses = QuestionnaireResponse.query.filter_by(
        product_id=product_id, user_id=user_id
    ).all()
    
    if not responses:
        return {}
    
    # Read CSV to map questions to their sub-dimensions
    csv_map = {}
    subdimension_questions = {}
    
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'devweb.csv')
        with open(csv_path, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            current_dimension = None
            current_subdimension = None
            
            for row in reader:
                dimension = row['Dimensions'].strip()
                subdimension = row['Sub-Dimensions'].strip()
                question = row['Questions'].strip()
                option = row['Options'].strip()
                score_text = row.get('Scores', '').strip()
                
                # Track current dimension and sub-dimension
                if dimension:
                    current_dimension = dimension
                if subdimension:
                    current_subdimension = subdimension
                    
                # Map question to sub-dimension
                if question and current_subdimension:
                    csv_map[question] = current_subdimension
                    
                    # Initialize sub-dimension tracking
                    if current_subdimension not in subdimension_questions:
                        subdimension_questions[current_subdimension] = []
                
                # Store scoring data for later use
                if question and option and score_text and current_subdimension:
                    try:
                        score = int(score_text)
                        # This will be used by calculate_question_score_from_csv
                    except (ValueError, TypeError):
                        pass
                        
    except FileNotFoundError:
        print("CSV file not found")
        return {}
    
    # Group responses by sub-dimension
    for response in responses:
        subdimension = csv_map.get(response.question)
        if subdimension and subdimension in subdimension_questions:
            # Calculate score for this question using existing function
            question_score = calculate_question_score_from_csv(response.question, response.answer)
            subdimension_questions[subdimension].append({
                'question': response.question,
                'answer': response.answer,
                'score': question_score
            })
    
    # Calculate sub-dimension scores using same logic: sum of scores / number of questions
    subdimension_scores = {}
    
    for subdimension, questions in subdimension_questions.items():
        if questions:  # Only process sub-dimensions that have questions
            total_score = sum(q['score'] for q in questions)
            num_questions = len(questions)
            average_score = total_score / num_questions if num_questions > 0 else 0
            
            subdimension_scores[subdimension] = {
                'average_score': round(average_score, 2),
                'question_count': num_questions,
                'total_score': total_score,
                'questions': questions
            }
    
    return subdimension_scores

def get_question_number_from_csv(question):
    """Get the sequential question number from CSV"""
    try:
        with open('devweb.csv', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            question_number = 0
            
            for row in reader:
                q = row['Questions'].strip()
                if q:  # Only count rows that have actual questions
                    question_number += 1
                    if q == question:
                        return question_number
                        
    except FileNotFoundError:
        print("CSV file not found, using default numbering")
    
    return None

def calculate_question_score_from_csv(question, answer):
    """Calculate 1-5 score for a specific question-answer pair based on CSV data"""
    try:

        with open('devweb.csv', encoding='utf-8') as f:

            reader = csv.DictReader(f)
            current_question = None
            
            for row in reader:
                q = row['Questions'].strip()
                option = row['Options'].strip()
                scores_text = row.get('Scores', '').strip()

                # Track current question
                if q:
                    current_question = q

                # Check if we found a match for our question and answer
                if current_question == question and option == answer and scores_text:
                    try:
                        return int(scores_text)  # Return 1-5 score directly from CSV
                    except (ValueError, TypeError):
                        pass

    except FileNotFoundError:
        print("CSV file not found, using default scoring")

    # Default scoring based on option letter if CSV parsing fails (1-5 scale)
    if answer.startswith('A)'):
        return 1
    elif answer.startswith('B)'):
        return 2
    elif answer.startswith('C)'):
        return 3
    elif answer.startswith('D)'):
        return 4
    elif answer.startswith('E)'):
        return 5
    else:
        return 1  # Default to lowest score

def get_maturity_level(maturity_score):
    """Convert maturity score (1-5 scale) to maturity level"""
    if maturity_score >= 4.5:
        return "Level 5 - Optimized"
    elif maturity_score >= 3.5:
        return "Level 4 - Managed" 
    elif maturity_score >= 2.5:
        return "Level 3 - Defined"
    elif maturity_score >= 1.5:
        return "Level 2 - Developing"
    else:
        return "Level 1 - Initial"

def get_maturity_level_number(maturity_score):
    """Convert maturity score to just the level number (1-5)"""
    if maturity_score >= 4.5:
        return 5
    elif maturity_score >= 3.5:
        return 4
    elif maturity_score >= 2.5:
        return 3
    elif maturity_score >= 1.5:
        return 2
    else:
        return 1

def generate_ringwise_heatmap_data(product_id, user_id):
    """Generate ring-wise heatmap data showing only levels up to achieved maturity"""
    # Get all responses for this product and user
    responses = QuestionnaireResponse.query.filter_by(
        product_id=product_id, user_id=user_id
    ).all()
    
    if not responses:
        return {}
    
    # Calculate sub-dimension scores
    subdimension_scores = calculate_subdimension_scores(product_id, user_id)
    
    # Calculate overall maturity score
    overall_score, _ = calculate_overall_maturity_score(product_id, user_id)
    achieved_level = get_maturity_level_number(overall_score)
    
    # Create ring data for each level up to achieved level
    ring_data = {}
    for level in range(1, 6):  # Levels 1-5
        ring_data[f"level_{level}"] = {
            "level": level,
            "is_achieved": level <= achieved_level,
            "subdimensions": []
        }
        
        # Add subdimension data for this level
        for subdim_name, subdim_data in subdimension_scores.items():
            subdim_level = get_maturity_level_number(subdim_data['average_score'])
            ring_data[f"level_{level}"]["subdimensions"].append({
                "name": subdim_name,
                "score": subdim_data['average_score'],
                "is_achieved": level <= subdim_level,
                "percentage": min(100, (subdim_data['average_score'] / level) * 100) if level <= subdim_level else 0
            })
    
    return {
        "overall_score": overall_score,
        "achieved_level": achieved_level,
        "rings": ring_data
    }

def generate_heatmap_data(product_id, user_id):
    """Generate heatmap data for visualization using 1-5 scale scores"""
    # Get all responses for this product and user
    responses = QuestionnaireResponse.query.filter_by(
        product_id=product_id, user_id=user_id
    ).all()
    
    # Group responses by section and calculate scores
    heatmap_data = []
    section_questions = {}
    
    for response in responses:
        section = response.section
        if section not in section_questions:
            section_questions[section] = []
        
        # Calculate score for this response (1-5 scale)
        score = calculate_question_score_from_csv(response.question, response.answer)
        
        section_questions[section].append({
            'question': response.question[:50] + '...' if len(response.question) > 50 else response.question,
            'full_question': response.question,
            'score': score,
            'answer': response.answer,
            'max_score': 5  # Maximum possible score on 1-5 scale
        })
    
    # Convert to heatmap format
    for section, questions in section_questions.items():
        for i, q in enumerate(questions):
            heatmap_data.append({
                'section': section,
                'question_index': i,
                'question': q['question'],
                'full_question': q['full_question'],
                'score': q['score'],
                'max_score': q['max_score'],
                'percentage': (q['score'] / q['max_score']) * 100,
                'answer': q['answer']
            })
    
    return heatmap_data

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Access denied!')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files from the uploads directory"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    # Get invitation token from URL
    token = request.args.get('token')
    invitation = None

    if token:
        invitation = InvitationToken.query.filter_by(token=token, is_used=False).first()
        if not invitation:
            flash('Invalid invitation link.')
            return redirect(url_for('login'))

        # Check if invitation is expired with error handling
        try:
            if invitation.is_expired():
                flash('Expired invitation link.')
                return redirect(url_for('login'))
        except Exception as e:
            print(f"Error checking invitation expiration: {e}")
            # If there's an error checking expiration, try to fix the datetime and check again
            try:
                if invitation.expires_at and invitation.expires_at.tzinfo is None:
                    invitation.expires_at = invitation.expires_at.replace(tzinfo=timezone.utc)
                    db.session.commit()
                if invitation.is_expired():
                    flash('Expired invitation link.')
                    return redirect(url_for('login'))
            except Exception as e2:
                print(f"Could not fix invitation datetime: {e2}")
                flash('There was an issue with your invitation link. Please request a new one.')
                return redirect(url_for('login'))
    else:
        flash('Registration requires a valid invitation.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        organization = request.form.get('organization', '')

        # Validate invitation token
        if not invitation:
            flash('Registration requires a valid invitation.')
            return redirect(url_for('login'))

        # Ensure email matches invitation
        if email != invitation.email:
            flash('Email must match the invitation.')
            return redirect(url_for('register', token=token))

        # Server-side validation
        if not username or not email or not password:
            flash('Please fill in all fields.')
            return redirect(url_for('register', token=token))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.')
            return redirect(url_for('register', token=token))

        import re
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
            flash('Invalid email format.')
            return redirect(url_for('register', token=token))

        if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
            flash('Password must be at least 8 characters and include uppercase, lowercase, and number.')
            return redirect(url_for('register', token=token))

        # Create user with invitation details
        user = User(
            username=username,
            email=email,
            role=invitation.role,  # Use role from invitation
            organization=organization or invitation.organization
        )
        user.set_password(password)
        db.session.add(user)

        # Mark invitation as used
        invitation.is_used = True
        invitation.used_at = datetime.now(timezone.utc)

        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))

    return render_template('register.html', invitation=invitation)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Invalid credentials.')
            return redirect(url_for('login'))
        session['user_id'] = user.id
        session['role'] = user.role
        user.last_login = datetime.now(timezone.utc)
        
        # Check if this is first login for lead users
        if user.role == 'lead' and user.first_login:
            db.session.commit()
            return redirect(url_for('change_password_first_login'))
        
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required()
def dashboard():
    role = session['role']
    user_id = session['user_id']
    if role == 'client':
        products = Product.query.filter_by(owner_id=user_id).all()
        # Check assessment completion for each product
        products_with_status = []
        for product in products:
            # Get product status
            status_record = ProductStatus.query.filter_by(product_id=product.id, user_id=user_id).first()
            if not status_record:
                # Create initial status record
                status_record = ProductStatus(product_id=product.id, user_id=user_id)
                db.session.add(status_record)
                db.session.commit()

            # Get responses and calculate progress
            responses = QuestionnaireResponse.query.filter_by(product_id=product.id, user_id=user_id).all()
            completed_sections = set([r.section for r in responses])
            total_sections = len(SECTION_IDS)
            completed_sections_count = len(completed_sections)

            # Check for rejected questions that need client attention
            rejected_responses = QuestionnaireResponse.query.filter_by(
                product_id=product.id, user_id=user_id, needs_client_response=True
            ).all()
            rejected_count = len(rejected_responses)

            # If there are rejected questions, the assessment status should reflect this
            if rejected_count > 0:
                status_record.status = 'needs_client_response'
            elif completed_sections_count == total_sections and not rejected_count:
                # Check if all questions are reviewed
                all_reviewed = all(r.is_reviewed for r in responses)
                if all_reviewed:
                    status_record.status = 'completed'
                else:
                    status_record.status = 'under_review'

            # Find next section to continue
            next_section_idx = 0
            for i, section in enumerate(SECTION_IDS):
                if section not in completed_sections:
                    next_section_idx = i
                    break

            # Get latest scores and calculate maturity score
            latest_scores = ScoreHistory.query.filter_by(
                product_id=product.id, user_id=user_id
            ).order_by(ScoreHistory.calculated_at.desc()).all()

            # Calculate overall maturity score using dimension averages
            if latest_scores:
                dimension_scores = []
                for score in latest_scores:
                    # Convert percentage back to 1-5 scale
                    dimension_score = (score.percentage / 100) * 5
                    dimension_scores.append(dimension_score)
                overall_maturity_score = sum(dimension_scores) / len(dimension_scores) if dimension_scores else 0
            else:
                overall_maturity_score = 0

            product_info = {
                'id': product.id,
                'name': product.name,
                'owner_id': product.owner_id,
                'status': status_record.status,
                'status_display': status_record.status.replace('_', ' ').title(),
                'completed_sections': completed_sections_count,
                'total_sections': total_sections,
                'next_section_idx': next_section_idx,
                'progress_percentage': round((completed_sections_count / total_sections) * 100, 1),
                'answered_questions': status_record.questions_completed,
                'total_questions': status_record.total_questions,
                'overall_score': round(overall_maturity_score, 2),
                'last_updated': status_record.last_updated,
                'rejected_count': rejected_count
            }
            products_with_status.append(product_info)

        # Get unread comments count for this client
        unread_comments = LeadComment.query.filter_by(client_id=user_id, is_read=False).count()

                # Get rejected questions for this client
        rejected_questions = []
        for product in products:
            product_rejected = db.session.query(RejectedQuestion, QuestionnaireResponse).join(
                QuestionnaireResponse, RejectedQuestion.response_id == QuestionnaireResponse.id
            ).filter(
                RejectedQuestion.user_id == user_id,
                RejectedQuestion.product_id == product.id,
                RejectedQuestion.status == 'pending'
            ).all()
            
            # Convert to format expected by template with question data from CSV
            for rejected_question, response in product_rejected:
                # Find the question data from QUESTIONNAIRE
                question_data = None
                question_number = 1
                for section_name, section_questions in QUESTIONNAIRE.items():
                    for i, q in enumerate(section_questions):
                        if q['question'] == rejected_question.question_text:
                            question_data = {
                                'id': rejected_question.id,
                                'question_text': q['question'],
                                'question_number': question_number,
                                'options': q['options']
                            }
                            break
                        question_number += 1
                    if question_data:
                        break
                
                # Add to rejected questions if found
                if question_data:
                    rejected_questions.append((rejected_question, question_data))

        return render_template('dashboard_client.html', products=products_with_status, unread_comments=unread_comments, rejected_questions=rejected_questions)
    elif role == 'lead':
        # Get the current lead user to check their assigned client
        current_lead = User.query.get(user_id)
        
        if not current_lead.assigned_client_id:
            # Lead not assigned to any client yet
            return render_template('dashboard_lead.html', clients_data={}, error_message="You have not been assigned to review any client yet. Please contact your administrator.")
        
        # Get responses only for the assigned client - only for completed assessments
        resps = db.session.query(QuestionnaireResponse, User, Product).join(
            User, QuestionnaireResponse.user_id == User.id
        ).join(
            Product, QuestionnaireResponse.product_id == Product.id
        ).filter(User.id == current_lead.assigned_client_id).all()

        # Organize responses by client and product - filter for complete assessments only
        clients_data = {}
        for resp, user, product in resps:
            # Check if this product's assessment is complete for this user
            if not is_assessment_complete(product.id, user.id):
                continue  # Skip incomplete assessments

            if user.id not in clients_data:
                clients_data[user.id] = {
                    'user': user,
                    'products': {}
                }
            if product.id not in clients_data[user.id]['products']:
                clients_data[user.id]['products'][product.id] = {
                    'product': product,
                    'responses': []
                }
            clients_data[user.id]['products'][product.id]['responses'].append(resp)

        # Get unread client replies count
        unread_client_replies = LeadComment.query.filter(
            LeadComment.client_id == current_lead.assigned_client_id,
            LeadComment.status == 'client_reply',
            LeadComment.is_read == False
        ).count()

        return render_template('dashboard_lead.html', clients_data=clients_data, assigned_client=current_lead.assigned_client, unread_client_replies=unread_client_replies)
    elif role == 'superuser':
        products = Product.query.all()

        # Get detailed product data with responses and scoring
        products_data = []
        for product in products:
            responses = QuestionnaireResponse.query.filter_by(product_id=product.id).all()

            # Calculate scores by dimension
            dimension_scores = {}
            for resp in responses:
                if resp.section not in dimension_scores:
                    dimension_scores[resp.section] = {'total': 0, 'count': 0}

                # Simple scoring based on answer (this can be made more sophisticated)
                score = 0
                if 'yes' in resp.answer.lower() or 'high' in resp.answer.lower():
                    score = 100
                elif 'partially' in resp.answer.lower() or 'medium' in resp.answer.lower():
                    score = 50
                elif 'no' in resp.answer.lower() or 'low' in resp.answer.lower():
                    score = 0
                else:
                    score = 25  # Default for other answers

                dimension_scores[resp.section]['total'] += score
                dimension_scores[resp.section]['count'] += 1

            # Calculate average scores for each dimension
            for dimension in dimension_scores:
                if dimension_scores[dimension]['count'] > 0:
                    dimension_scores[dimension]['average'] = dimension_scores[dimension]['total'] / dimension_scores[dimension]['count']
                else:
                    dimension_scores[dimension]['average'] = 0

            # Get product owner info
            owner = User.query.get(product.owner_id)

            products_data.append({
                'product': product,
                'owner': owner,
                'responses': responses,
                'dimension_scores': dimension_scores,
                'total_responses': len(responses)
            })

        # Get all responses and comments for admin view
        all_responses = db.session.query(QuestionnaireResponse, User, Product).join(
            User, QuestionnaireResponse.user_id == User.id
        ).join(
            Product, QuestionnaireResponse.product_id == Product.id
        ).order_by(QuestionnaireResponse.created_at.desc()).limit(100).all()
        all_comments = LeadComment.query.options(
            db.joinedload(LeadComment.product), 
            db.joinedload(LeadComment.lead), 
            db.joinedload(LeadComment.client),
            db.joinedload(LeadComment.response)
        ).order_by(LeadComment.created_at.desc()).limit(50).all()

        # Group comments by dimension for better organization
        grouped_admin_comments = {}
        for comment in all_comments:
            if comment.response and comment.response.section:
                section = comment.response.section
                if section not in grouped_admin_comments:
                    grouped_admin_comments[section] = []
                grouped_admin_comments[section].append(comment)
            else:
                if 'General' not in grouped_admin_comments:
                    grouped_admin_comments['General'] = []
                grouped_admin_comments['General'].append(comment)

        return render_template('dashboard_superuser.html', products_data=products_data, all_responses=all_responses, all_comments=all_comments, grouped_admin_comments=grouped_admin_comments)
    return redirect(url_for('index'))

def is_assessment_complete(product_id, user_id):
    """Check if assessment is complete for a product"""
    completed_sections = set([
        r.section for r in QuestionnaireResponse.query.filter_by(
            product_id=product_id, user_id=user_id
        ).all()
    ])
    return len(completed_sections) == len(SECTION_IDS)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required('client')
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        product_url = request.form['product_url']
        programming_language = request.form['programming_language']
        cloud_platform = request.form['cloud_platform']
        cloud_platform_other = request.form.get('cloud_platform_other', '')
        cicd_platform = request.form['cicd_platform']
        additional_details = request.form.get('additional_details', '')


        if not name or not product_url or not programming_language or not cloud_platform or not cicd_platform:
            flash('Please fill in all required fields.')
            return redirect(url_for('add_product'))

        # If cloud_platform is "Other", use the custom value
        if cloud_platform == 'Other' and cloud_platform_other:
            cloud_platform = cloud_platform_other

        product = Product(
            name=name,

            product_url=product_url,
            programming_language=programming_language,
            cloud_platform=cloud_platform,
            cloud_platform_other=cloud_platform_other,
            cicd_platform=cicd_platform,
            additional_details=additional_details,
            owner_id=session['user_id']
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added. Now fill the questionnaire.')
        return redirect(url_for('fill_questionnaire_section', product_id=product.id, section_idx=0))
    return render_template('add_product.html')

@app.route('/fill_questionnaire/<int:product_id>/section/<int:section_idx>', methods=['GET', 'POST'])
@login_required('client')
def fill_questionnaire_section(product_id, section_idx):
    product = Product.query.get_or_404(product_id)
    sections = SECTION_IDS
    if section_idx >= len(sections):
        flash("All sections complete!")
        return redirect(url_for('dashboard'))
    section_name = sections[section_idx]
    questions = QUESTIONNAIRE[section_name]

    # Get existing responses for this section to pre-populate form
    existing_responses = QuestionnaireResponse.query.filter_by(
        product_id=product_id,
        user_id=session['user_id'],
        section=section_name
    ).all()

    # Create a dictionary for quick lookup of existing responses
    existing_answers = {}
    for resp in existing_responses:
        for i, q in enumerate(questions):
            if q['question'] == resp.question:
                existing_answers[i] = resp
                break

    if request.method == 'POST':
        # Get lead comments for validation
        response_ids = [resp.id for resp in existing_responses]
        lead_comments = {}
        if response_ids:
            comments = LeadComment.query.filter(LeadComment.response_id.in_(response_ids)).all()
            for comment in comments:
                lead_comments[comment.response_id] = comment

        # Delete existing responses for this section before adding new ones (except approved ones)
        responses_to_delete = []
        for resp in existing_responses:
            # Don't delete approved responses
            if not getattr(resp, 'is_approved', False):
                responses_to_delete.append(resp.id)

        if responses_to_delete:
            QuestionnaireResponse.query.filter(QuestionnaireResponse.id.in_(responses_to_delete)).delete()

        for i, q in enumerate(questions):
            # Check if this question is approved
            existing_resp = existing_answers.get(i)
            if existing_resp and getattr(existing_resp, 'is_approved', False):
                # Keep the approved response as-is, don't update it
                continue

            answer = request.form.get(f'answer_{i}')
            comment = request.form.get(f'comment_{i}')
            file = request.files.get(f'evidence_{i}')
            evidence_path = ""

            # Keep existing evidence if no new file uploaded
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{product_id}_{section_idx}_{i}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                evidence_path = f"static/uploads/{filename}"
            elif i in existing_answers:
                evidence_path = existing_answers[i].evidence_path or ''

            resp = QuestionnaireResponse(
                user_id=session['user_id'],
                product_id=product_id,
                section=section_name,
                question=q['question'],
                answer=answer,
                client_comment=comment,
                evidence_path=evidence_path,
                is_reviewed=False,  # Reset review status for new/updated responses
                needs_client_response=False  # Reset the client response flag when they respond
            )
            db.session.add(resp)
        db.session.commit()

        # Update product status and calculate scores
        status = update_product_status(product_id, session['user_id'])
        calculate_and_store_scores(product_id, session['user_id'])

        if section_idx + 1 < len(sections):
            return redirect(url_for('fill_questionnaire_section', product_id=product_id, section_idx=section_idx+1))
        else:
            if status == 'questions_done':
                flash("Questions completed! Waiting for review.")
            elif status == 'completed':
                flash("Assessment completed successfully!")
            else:
                flash("Section saved successfully!")
            return redirect(url_for('dashboard'))

    completed_sections = [
        s.section for s in QuestionnaireResponse.query.filter_by(product_id=product_id, user_id=session['user_id']).distinct(QuestionnaireResponse.section)
    ]
    progress = [(i, s, (s in completed_sections)) for i, s in enumerate(sections)]

    # Get review status for questions in this section
    question_review_status = {}
    if existing_responses:
        response_ids = [resp.id for resp in existing_responses]
        lead_comments = LeadComment.query.filter(LeadComment.response_id.in_(response_ids)).all()
        for comment in lead_comments:
            for resp in existing_responses:
                if resp.id == comment.response_id:
                    for i, q in enumerate(questions):
                        if q['question'] == resp.question:
                            question_review_status[i] = comment.status
                            break

    return render_template(
        'fill_questionnaire_section.html',
        product=product,
        section_name=section_name,
        questions=questions,
        section_idx=section_idx,
        total_sections=len(sections),
        progress=progress,
        existing_answers=existing_answers,
        question_review_status=question_review_status
    )

@app.route('/product/<int:product_id>/results')
@login_required('client')
def product_results(product_id):
    try:
        # Get product information
        product = Product.query.get_or_404(product_id)
        
        # Verify user has access to this product
        if not product:
            flash('Product not found.', 'error')
            return redirect(url_for('dashboard'))
        
        # Get all responses for this product and user
        resps = QuestionnaireResponse.query.filter_by(product_id=product_id, user_id=session['user_id']).all()
        
        # Get lead comments with proper serializable data
        lead_comments_query = LeadComment.query.filter_by(product_id=product_id, client_id=session['user_id']).order_by(LeadComment.created_at.desc()).all()
        
        # Convert responses to serializable dictionaries with lead comments
        responses_data = []
        for resp in resps:
            try:
                # Get lead comments for this response
                resp_comments = []
                for comment in lead_comments_query:
                    if comment.response_id == resp.id:
                        resp_comments.append({
                            'id': getattr(comment, 'id', 0),
                            'comment': getattr(comment, 'comment', '') or '',
                            'status': getattr(comment, 'status', 'pending') or 'pending',
                            'created_at': comment.created_at.isoformat() if hasattr(comment, 'created_at') and comment.created_at else None
                        })
                
                responses_data.append({
                    'id': getattr(resp, 'id', 0),
                    'section': getattr(resp, 'section', '') or '',
                    'question': getattr(resp, 'question', '') or '',
                    'answer': getattr(resp, 'answer', '') or '',
                    'score': getattr(resp, 'score', 0) or 0,
                    'max_score': getattr(resp, 'max_score', 5) or 5,
                    'is_reviewed': getattr(resp, 'is_reviewed', False) or False,
                    'needs_client_response': getattr(resp, 'needs_client_response', False) or False,
                    'client_comment': getattr(resp, 'client_comment', '') or '',
                    'evidence_path': getattr(resp, 'evidence_path', '') or '',
                    'created_at': resp.created_at.isoformat() if hasattr(resp, 'created_at') and resp.created_at else None,
                    'updated_at': resp.updated_at.isoformat() if hasattr(resp, 'updated_at') and resp.updated_at else None,
                    'lead_comments': resp_comments
                })
            except Exception as e:
                # Log error but continue processing other responses
                print(f"Error processing response {getattr(resp, 'id', 'unknown')}: {e}")
                continue
        
        # Calculate comprehensive assessment data with error handling
        try:
            overall_score, section_data = calculate_overall_maturity_score(product_id, session['user_id'])
            maturity_score = max(1, min(5, round(overall_score))) if overall_score and overall_score > 0 else 1
        except Exception as e:
            print(f"Error calculating maturity score: {e}")
            overall_score = 0
            section_data = {}
            maturity_score = 1
        
        # Calculate sub-dimension scores with error handling
        subdimension_scores = {}
        dimension_scores = {}  # Keep for backward compatibility
        section_dimensions = {}
        
        try:
            subdimension_scores = calculate_subdimension_scores(product_id, session['user_id'])
        except Exception as e:
            print(f"Error calculating sub-dimension scores: {e}")
            subdimension_scores = {}
        
        # Keep original dimension scores for backward compatibility
        if section_data and isinstance(section_data, dict):
            for section_name, data in section_data.items():
                try:
                    if not isinstance(data, dict):
                        continue
                        
                    avg_score = data.get('average_score', 0)
                    question_count = data.get('questions_count', 0)
                    total_score = data.get('total_score', 0)
                    
                    # Ensure numeric values
                    avg_score = float(avg_score) if avg_score is not None else 0.0
                    question_count = int(question_count) if question_count is not None else 0
                    total_score = float(total_score) if total_score is not None else 0.0
                    
                    dimension_scores[str(section_name)] = {
                        'average_score': round(avg_score, 2),
                        'question_count': question_count,
                        'total_score': round(total_score, 2)
                    }
                    
                    # Calculate section percentage for section_dimensions
                    max_possible = question_count * 5  # Assuming max score of 5 per question
                    percentage = (total_score / max_possible * 100) if max_possible > 0 else 0
                    
                    section_dimensions[str(section_name)] = {
                        'percentage': round(max(0, min(100, percentage)), 1),
                        'question_count': question_count,
                        'total_score': round(total_score, 2),
                        'max_possible_score': max_possible
                    }
                except Exception as e:
                    print(f"Error processing section {section_name}: {e}")
                    continue
        
        # Generate serializable heatmap data with error handling
        try:
            heatmap_data = generate_heatmap_data(product_id, session['user_id'])
            if not isinstance(heatmap_data, list):
                heatmap_data = []
        except Exception as e:
            print(f"Error generating heatmap data: {e}")
            heatmap_data = []
        
        # Create serializable responses JSON for JavaScript
        responses_json = []
        for resp in responses_data:
            try:
                responses_json.append({
                    'section': str(resp.get('section', '')),
                    'question': str(resp.get('question', '')),
                    'answer': str(resp.get('answer', '')),
                    'score': float(resp.get('score', 0)) if resp.get('score') is not None else 0.0,
                    'lead_comments': resp.get('lead_comments', [])
                })
            except Exception as e:
                print(f"Error serializing response: {e}")
                continue
        
        # Calculate dimension-wise results from subdimension scores
        try:
            from ring_heatmap_implementation import get_dimension_wise_results
            dimension_results = get_dimension_wise_results(subdimension_scores)
        except Exception as e:
            print(f'Error calculating dimension-wise results: {e}')
            dimension_results = {}

        # Ensure all template variables are properly defined
        template_vars = {
            'product': product,
            'responses': responses_data,
            'responses_json': responses_json,
            'maturity_score': maturity_score,
            'dimension_scores': dimension_scores,  # Keep for backward compatibility
            'subdimension_scores': subdimension_scores,  # New sub-dimension scores
            'dimension_results': dimension_results,  # New dimension-wise results
            'section_dimensions': section_dimensions,
            'heatmap_data': heatmap_data
        }
        
        return render_template('product_results.html', **template_vars)
        
    except Exception as e:
        # Handle any unexpected errors
        print(f"Error in product_results route: {e}")
        flash('An error occurred while loading the results. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/client/comments')
@login_required('client')
def client_comments():
    comments = LeadComment.query.options(
        db.joinedload(LeadComment.product), 
        db.joinedload(LeadComment.lead),
        db.joinedload(LeadComment.response)
    ).filter(
        LeadComment.client_id == session['user_id'],
        LeadComment.status.in_(['needs_revision', 'rejected', 'pending', 'client_reply'])  # Exclude approved
    ).order_by(LeadComment.created_at.desc()).all()
    
    # Group comments by dimension/section
    grouped_comments = {}
    for comment in comments:
        if comment.response and comment.response.section:
            section = comment.response.section
            if section not in grouped_comments:
                grouped_comments[section] = []
            grouped_comments[section].append(comment)
        else:
            # Comments without associated responses go to 'General'
            if 'General' not in grouped_comments:
                grouped_comments['General'] = []
            grouped_comments['General'].append(comment)
    
    return render_template('client_comments.html', comments=comments, grouped_comments=grouped_comments)

@app.route('/client/comment/<int:comment_id>/read')
@login_required('client')
def mark_comment_read(comment_id):
    comment = LeadComment.query.get_or_404(comment_id)
    if comment.client_id == session['user_id']:
        comment.is_read = True
        db.session.commit()
        flash('Comment marked as read.', 'success')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/client/comment/<int:comment_id>/reply', methods=['POST'])
@login_required('client')
def client_reply_comment(comment_id):
    parent_comment = LeadComment.query.get_or_404(comment_id)
    if parent_comment.client_id != session['user_id']:
        flash('Unauthorized access.')
        return redirect(url_for('dashboard'))

    reply_text = request.form['reply']
    evidence_file = request.files.get('evidence')

    if reply_text.strip():
        evidence_path = None
        # Handle evidence upload if provided
        if evidence_file and evidence_file.filename:
            valid, message = validate_file_security(evidence_file)
            if valid:
                filename = secure_filename_hash(evidence_file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                evidence_file.save(filepath)
                evidence_path = f"static/uploads/{filename}"
            else:
                flash(f'File upload failed: {message}', 'error')
                return redirect(request.referrer or url_for('client_comments'))

        # Create a reply comment
        reply_comment = LeadComment(
            response_id=parent_comment.response_id,
            lead_id=parent_comment.lead_id,  # Send back to the original lead
            client_id=session['user_id'],
            product_id=parent_comment.product_id,
            comment=reply_text,  # Remove the "Client Reply:" prefix for cleaner display
            status='client_reply',
            parent_comment_id=comment_id,
            is_read=False  # Ensure it shows as unread for the lead
        )
        db.session.add(reply_comment)

        # If evidence provided, also update the original response
        if evidence_path and parent_comment.response_id:
            original_response = QuestionnaireResponse.query.get(parent_comment.response_id)
            if original_response:
                original_response.evidence_path = evidence_path
                original_response.client_comment = reply_text

        db.session.commit()
        flash('Reply sent to lead successfully.')

    return redirect(request.referrer or url_for('client_comments'))

@app.route('/lead/comments')
@login_required('lead')
def lead_comments():
    # Get the current lead user to check their assigned client
    current_lead = User.query.get(session['user_id'])
    
    if not current_lead.assigned_client_id:
        # Lead not assigned to any client yet
        return render_template('lead_comments.html', comments=[], error_message="You have not been assigned to review any client yet. Please contact your administrator.")
    
    # Get comments only for this lead's assigned client, excluding approved conversations
    comments = LeadComment.query.options(
        db.joinedload(LeadComment.product),
        db.joinedload(LeadComment.client),
        db.joinedload(LeadComment.response)
    ).filter(
        db.and_(
            LeadComment.client_id == current_lead.assigned_client_id,
            LeadComment.status.in_(['needs_revision', 'rejected', 'pending', 'client_reply']),  # Exclude approved
            db.or_(
                LeadComment.lead_id == session['user_id'],
                db.and_(
                    LeadComment.status == 'client_reply',
                    LeadComment.parent_comment_id.in_(
                        db.session.query(LeadComment.id).filter_by(lead_id=session['user_id'])
                    )
                )
            )
        )
    ).order_by(LeadComment.created_at.desc()).all()
    
    # Mark all client replies as read when lead visits this page
    unread_client_replies = LeadComment.query.filter(
        LeadComment.client_id == current_lead.assigned_client_id,
        LeadComment.status == 'client_reply',
        LeadComment.is_read == False
    ).all()
    
    for reply in unread_client_replies:
        reply.is_read = True
    
    if unread_client_replies:
        db.session.commit()
    
    # Group comments by dimension/section
    grouped_comments = {}
    for comment in comments:
        if comment.response and comment.response.section:
            section = comment.response.section
            if section not in grouped_comments:
                grouped_comments[section] = []
            grouped_comments[section].append(comment)
        else:
            # Comments without associated responses go to 'General'
            if 'General' not in grouped_comments:
                grouped_comments['General'] = []
            grouped_comments['General'].append(comment)
    
    return render_template('lead_comments.html', comments=comments, grouped_comments=grouped_comments)

@app.route('/lead/comment/<int:comment_id>/reply', methods=['POST'])
@login_required('lead')
def lead_reply_comment(comment_id):
    parent_comment = LeadComment.query.get_or_404(comment_id)
    
    # Check if this lead has permission to reply
    if parent_comment.lead_id != session['user_id'] and not (
        parent_comment.status == 'client_reply' and 
        LeadComment.query.filter_by(id=parent_comment.parent_comment_id, lead_id=session['user_id']).first()
    ):
        flash('Unauthorized access.')
        return redirect(url_for('dashboard'))

    reply_text = request.form['reply']

    if reply_text.strip():
        # Create a reply comment
        reply_comment = LeadComment(
            response_id=parent_comment.response_id,
            lead_id=session['user_id'],
            client_id=parent_comment.client_id,
            product_id=parent_comment.product_id,
            comment=reply_text,
            status='lead_reply',
            parent_comment_id=comment_id
        )
        db.session.add(reply_comment)
        db.session.commit()
        flash('Reply sent to client successfully.')

    return redirect(request.referrer or url_for('lead_comments'))

@app.route('/change-password-first-login', methods=['GET', 'POST'])
@login_required('lead')
def change_password_first_login():
    user = User.query.get(session['user_id'])
    
    # Only allow this route for first-time login
    if not user.first_login:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Validate current password
        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('change_password_first_login.html')
        
        # Validate new password
        if len(new_password) < 8:
            flash('New password must be at least 8 characters long.', 'error')
            return render_template('change_password_first_login.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('change_password_first_login.html')
        
        # Update password and mark first login as complete
        user.set_password(new_password)
        user.first_login = False
        db.session.commit()
        
        flash('Password changed successfully! Welcome to SecureSphere.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('change_password_first_login.html')

@app.route('/change-password', methods=['GET', 'POST'])
@login_required()
def change_password():
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Validate current password
        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'error')
            return render_template('change_password.html')
        
        # Validate new password
        if len(new_password) < 8:
            flash('New password must be at least 8 characters long.', 'error')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('change_password.html')
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html')

@app.route('/review/<int:response_id>', methods=['GET', 'POST'])
@login_required('lead')
def review_questionnaire(response_id):
    resp = QuestionnaireResponse.query.get_or_404(response_id)
    
    # Check if the lead is assigned to review this client
    current_lead = User.query.get(session['user_id'])
    if not current_lead.assigned_client_id or current_lead.assigned_client_id != resp.user_id:
        flash('You are not authorized to review this client\'s responses.')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        comment = request.form['lead_comment']
        status = request.form.get('review_status', 'pending')

        # Create lead comment
        lead_comment = LeadComment(
            response_id=response_id,
            lead_id=session['user_id'],
            client_id=resp.user_id,
            product_id=resp.product_id,
            comment=comment,
            status=status
        )
        db.session.add(lead_comment)

        # Mark response as reviewed and set approval status (with safety check)
        try:
            if status == 'rejected':
                resp.is_reviewed = False  # Allow client to modify rejected responses
                resp.needs_client_response = True  # Mark for client attention
                resp.is_approved = False  # Reset approval status
                
                # Create a RejectedQuestion entry for this specific question
                try:
                    rejected_question = RejectedQuestion(
                        response_id=response_id,
                        user_id=resp.user_id,
                        product_id=resp.product_id,
                        lead_id=session['user_id'],
                        question_text=resp.question,
                        original_option=resp.answer,
                        reason=comment,
                        status='pending',
                        created_at=datetime.now(timezone.utc)
                    )
                    db.session.add(rejected_question)
                except Exception as e:
                    print(f"Error creating rejected question: {e}")
                    # Continue without failing the entire process
                    
            elif status == 'approved':
                resp.is_reviewed = True
                resp.is_approved = True  # Mark as finally approved
                resp.needs_client_response = False
            else:
                resp.is_reviewed = True
                resp.is_approved = False  # Not approved yet
        except Exception:
            # If columns don't exist yet, skip setting them
            pass

        db.session.commit()

        # Update product status and recalculate scores
        update_product_status(resp.product_id, resp.user_id)
        calculate_and_store_scores(resp.product_id, resp.user_id)

        flash('Review comment sent to client.')
        return redirect(url_for('dashboard'))
    return render_template('review_questionnaire.html', response=resp)

@app.route('/admin/product/<int:product_id>/details')
@login_required('superuser')
def admin_product_details(product_id):
    # Get all responses for this product
    resps = QuestionnaireResponse.query.filter_by(product_id=product_id).all()
    
    # Get product information
    product = Product.query.get_or_404(product_id)
    
    # Get owner information
    owner = User.query.get(product.owner_id)
    
    # Calculate maturity scores by dimension
    dimension_data = {}
    for resp in resps:
        section = resp.section
        if section not in dimension_data:
            dimension_data[section] = {
                'responses': [],
                'scores': [],
                'questions_count': 0,
                'average_score': 0
            }
        
        # Calculate score for this response (1-5 scale)
        raw_score = calculate_score_for_answer(resp.question, resp.answer)
        normalized_score = raw_score / 20 if raw_score > 0 else 0
        
        dimension_data[section]['responses'].append(resp)
        dimension_data[section]['scores'].append(normalized_score)
        dimension_data[section]['questions_count'] += 1
    
    # Calculate average scores for each dimension
    for section, data in dimension_data.items():
        if data['questions_count'] > 0:
            data['average_score'] = sum(data['scores']) / data['questions_count']
        else:
            data['average_score'] = 0
    
    # Calculate overall maturity score
    if dimension_data:
        overall_score = sum(data['average_score'] for data in dimension_data.values()) / len(dimension_data)
        maturity_level = get_maturity_level(overall_score)
    else:
        overall_score = 0
        maturity_level = "No Data"
    
    return render_template('admin_product_details.html', 
                         responses=resps, 
                         product=product, 
                         owner=owner,
                         dimension_data=dimension_data,
                         overall_score=overall_score,
                         maturity_level=maturity_level,
                         product_id=product_id)

@app.route('/admin/product/<int:product_id>/results')
@login_required('superuser')
def admin_product_results(product_id):
    # Get all responses for this product
    resps = QuestionnaireResponse.query.filter_by(product_id=product_id).all()
    
    # Get product information
    product = Product.query.get_or_404(product_id)
    
    # Get owner information
    owner = User.query.get(product.owner_id)
    
    # Handle case where owner might be None (user deleted)
    if not owner:
        flash('Product owner not found. Cannot display results.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all lead comments for this product
    all_lead_comments = LeadComment.query.filter_by(product_id=product_id, client_id=owner.id).all()
    
    # Create a mapping of response_id to lead_comment
    lead_comment_map = {}
    for comment in all_lead_comments:
        if comment.response_id:
            lead_comment_map[comment.response_id] = comment
    
    # Convert responses to serializable dictionaries
    responses_data = []
    for resp in resps:
        # Get associated lead comment
        lead_comment = lead_comment_map.get(resp.id)
        
        response_data = {
            'id': resp.id,
            'section': resp.section,
            'question': resp.question,
            'answer': resp.answer,
            'score': resp.score,
            'max_score': resp.max_score,
            'is_reviewed': resp.is_reviewed,
            'needs_client_response': resp.needs_client_response,
            'client_comment': resp.client_comment,
            'evidence_path': resp.evidence_path,
            'created_at': resp.created_at.isoformat() if resp.created_at else None,
            'updated_at': resp.updated_at.isoformat() if resp.updated_at else None
        }
        
        # Add lead comment information
        if lead_comment:
            response_data['lead_comments'] = [{
                'id': lead_comment.id,
                'status': lead_comment.status,
                'comment': lead_comment.comment,
                'created_at': lead_comment.created_at.isoformat() if lead_comment.created_at else None
            }]
        else:
            response_data['lead_comments'] = []
            
        responses_data.append(response_data)
    
    # Calculate overall maturity score and section details
    overall_score, section_data = calculate_overall_maturity_score(product_id, owner.id)
    maturity_level = get_maturity_level(overall_score)
    
    # Calculate sub-dimension scores
    try:
        subdimension_scores = calculate_subdimension_scores(product_id, owner.id)
    except Exception as e:
        print(f"Error calculating sub-dimension scores: {e}")
        subdimension_scores = {}
    
    # Generate heatmap data
    heatmap_data = generate_heatmap_data(product_id, owner.id)
    
    # Generate ring-wise heatmap data
    ringwise_heatmap_data = generate_ringwise_heatmap_data(product_id, owner.id)
    
    # Get lead comments for this product
    lead_comments = LeadComment.query.options(
        db.joinedload(LeadComment.product), 
        db.joinedload(LeadComment.lead)
    ).filter_by(product_id=product_id, client_id=owner.id).order_by(LeadComment.created_at.desc()).all()
    
    # Calculate dimension-wise results from subdimension scores
    try:
        from ring_heatmap_implementation import get_dimension_wise_results
        dimension_results = get_dimension_wise_results(subdimension_scores)
    except Exception as e:
        print(f'Error calculating dimension-wise results: {e}')
        dimension_results = {}

    return render_template('product_results.html', 
                         responses=responses_data, 
                         lead_comments=lead_comments,
                         overall_score=overall_score,
                         maturity_score=max(1, min(5, round(overall_score))) if overall_score and overall_score > 0 else 1,
                         maturity_level=maturity_level,
                         section_data=section_data,
                         subdimension_scores=subdimension_scores,
                         dimension_results=dimension_results,
                         heatmap_data=heatmap_data,
                         ringwise_heatmap_data=ringwise_heatmap_data,
                         product=product,
                         owner=owner,
                         is_admin_view=True)

@app.route('/admin/create_product', methods=['GET', 'POST'])
@login_required('superuser')
def admin_create_product():
    if request.method == 'POST':
        product_name = request.form['product_name']
        client_id = request.form['client_id']

        # Verify client exists
        client = User.query.filter_by(id=client_id, role='client').first()
        if not client:
            flash('Invalid client selected.')
            return redirect(url_for('admin_create_product'))

        # Create product
        product = Product(name=product_name, owner_id=client_id)
        db.session.add(product)
        db.session.commit()

        flash(f'Product "{product_name}" created successfully for {client.username}.')
        return redirect(url_for('dashboard'))

    # Get all clients for the form
    clients = User.query.filter_by(role='client').all()
    return render_template('admin_create_product.html', clients=clients)

@app.route('/admin/analytics')
@login_required('superuser')
def admin_analytics():
    # Get all products and their scores for analytics
    products = Product.query.all()
    analytics_data = []

    for product in products:
        responses = QuestionnaireResponse.query.filter_by(product_id=product.id).all()
        if responses:
            # Calculate average score for this product
            total_score = 0
            total_questions = 0
            section_scores = {}

            for response in responses:
                if response.answer.isdigit():
                    score = int(response.answer)
                    total_score += score
                    total_questions += 1

                    if response.section not in section_scores:
                        section_scores[response.section] = []
                    section_scores[response.section].append(score)

            if total_questions > 0:
                avg_score = total_score / total_questions
                owner = User.query.get(product.owner_id)

                analytics_data.append({
                    'product': product,
                    'owner': owner,
                    'avg_score': avg_score,
                    'total_responses': len(responses),
                    'section_scores': {k: sum(v)/len(v) for k, v in section_scores.items()}
                })

    return render_template('admin_analytics.html', analytics_data=analytics_data)

@app.route('/admin/products/delete/<int:product_id>')
@login_required('superuser')
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    QuestionnaireResponse.query.filter_by(product_id=product_id).delete()
    db.session.delete(product)
    db.session.commit()
    flash('Product and all responses deleted.')
    return redirect(url_for('dashboard'))

@app.route('/api/product/<int:product_id>/scores')
@login_required()
def api_product_scores(product_id):
    resps = QuestionnaireResponse.query.filter_by(product_id=product_id).all()
    section_scores = {}
    section_max_scores = {}
    section_counts = {}
    total_score = 0
    total_max_score = 0
    csv_map = {}

    # Build scoring map from CSV
    csv_path = os.path.join(os.path.dirname(__file__), 'devweb.csv')
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        current_question = None
        current_dimension = None
        question_options = {}

        for row in reader:
            dimension = row['Dimensions'].strip()
            question = row['Questions'].strip()
            option = row['Options'].strip()
            score_text = row.get('Scores', '').strip()

            # Track current dimension and question
            if dimension:
                current_dimension = dimension
            if question:
                current_question = question
                question_options = {}
                if current_dimension not in section_max_scores:
                    section_max_scores[current_dimension] = 0

            # Store option and score for current question
            if current_question and option and score_text:
                try:
                    score = int(score_text)
                    question_options[option] = score
                    csv_map[current_question] = question_options.copy()
                except (ValueError, TypeError):
                    pass

        # Calculate max scores per section
        for question, options in csv_map.items():
            if options:
                max_score = max(options.values())
                # Find dimension for this question
                for dimension in section_max_scores:
                    if any(resp.question == question and resp.section == dimension for resp in resps):
                        if section_max_scores[dimension] == 0:  # Only add once per question
                            section_max_scores[dimension] += max_score
                            total_max_score += max_score
                        break

    # Calculate actual scores
    question_scores = {}
    for r in resps:
        sec = r.section
        if sec not in section_scores:
            section_scores[sec] = 0
            section_counts[sec] = 0

        score = csv_map.get(r.question, {}).get(r.answer, 0)
        section_scores[sec] += score
        section_counts[sec] += 1
        total_score += score

        # Store individual question scores
        question_scores[f"{r.question}:{r.answer}"] = score

    # Calculate percentages
    section_labels = list(section_scores.keys())
    section_values = [section_scores[k] for k in section_labels]
    section_percentages = []

    for section in section_labels:
        max_section_score = section_max_scores.get(section, 1)
        percentage = (section_scores[section] / max_section_score * 100) if max_section_score > 0 else 0
        section_percentages.append(round(percentage, 1))

    overall_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0

    return jsonify({
        "section_labels": section_labels,
        "section_scores": section_values,
        "section_percentages": section_percentages,
        "section_max_scores": [section_max_scores.get(k, 0) for k in section_labels],
        "total_score": total_score,
        "max_score": total_max_score,
        "overall_percentage": round(overall_percentage, 1),
        "sections_count": len(section_labels),
        "question_scores": question_scores
    })

@app.route('/api/superuser/all_scores')
@login_required('superuser')
def api_all_scores():
    products = Product.query.all()
    all_scores = []

    for product in products:
        product_data = {}
        resps = QuestionnaireResponse.query.filter_by(product_id=product.id).all()

        if resps:
            # Get scores for this product
            section_scores = {}
            section_max_scores = {}
            total_score = 0
            total_max_score = 0
            csv_map = {}

            # Build scoring map
            csv_path = os.path.join(os.path.dirname(__file__), 'devweb.csv')
            with open(csv_path, encoding='utf-8') as f:
                reader = csv.DictReader(f)
                current_question = None
                current_dimension = None
                question_options = {}

                for row in reader:
                    dimension = row['Dimensions'].strip()
                    question = row['Questions'].strip()
                    option = row['Options'].strip()
                    score_text = row.get('Scores', '').strip()

                    # Track current dimension and question
                    if dimension:
                        current_dimension = dimension
                    if question:
                        current_question = question
                        question_options = {}
                        if current_dimension not in section_max_scores:
                            section_max_scores[current_dimension] = 0

                    # Store option and score for current question
                    if current_question and option and score_text:
                        try:
                            score = int(score_text)
                            question_options[option] = score
                            csv_map[current_question] = question_options.copy()
                        except (ValueError, TypeError):
                            pass

                # Calculate max scores per section
                for question, options in csv_map.items():
                    if options:
                        max_score = max(options.values())
                        # Find dimension for this question
                        for dimension in section_max_scores:
                            if any(resp.question == question and resp.section == dimension for resp in resps):
                                section_max_scores[dimension] += max_score
                                total_max_score += max_score
                                break

            # Calculate scores
            for r in resps:
                sec = r.section
                if sec not in section_scores:
                    section_scores[sec] = 0

                score = csv_map.get(r.question, {}).get(r.answer, 0)
                section_scores[sec] += score
                total_score += score

            overall_percentage = (total_score / total_max_score * 100) if total_max_score > 0 else 0

            # Get owner info
            owner = User.query.get(product.owner_id)

            product_data = {
                'id': product.id,
                'name': product.name,
                'owner': owner.username if owner else 'Unknown',
                'organization': owner.organization if owner else 'Unknown',
                'total_score': total_score,
                'max_score': total_max_score,
                'percentage': round(overall_percentage, 1),
                'section_scores': section_scores,
                'section_percentages': {k: round((v / section_max_scores.get(k, 1) * 100), 1)
                                       for k, v in section_scores.items()}
            }
        else:
            product_data = {
                'id': product.id,
                'name': product.name,
                'owner': 'Unknown',
                'organization': 'Unknown',
                'total_score': 0,
                'max_score': 0,
                'percentage': 0,
                'section_scores': {},
                'section_percentages': {}
            }

        all_scores.append(product_data)

    return jsonify(all_scores)

@app.route('/api/admin/review_response', methods=['POST'])
@login_required('superuser')
def api_admin_review_response():
    try:
        data = request.get_json()
        response_id = data.get('response_id')
        action = data.get('action')  # 'approved', 'needs_revision', 'rejected'
        comment = data.get('comment', '')
        
        # Validate input
        if not response_id or action not in ['approved', 'needs_revision', 'rejected']:
            return jsonify({'success': False, 'message': 'Invalid input parameters'}), 400
            
        # Get the questionnaire response
        response = QuestionnaireResponse.query.get(response_id)
        if not response:
            return jsonify({'success': False, 'message': 'Response not found'}), 404
            
        # Get the product and owner information
        product = Product.query.get(response.product_id)
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404
            
        owner = User.query.get(product.owner_id)
        if not owner:
            return jsonify({'success': False, 'message': 'Product owner not found'}), 404
            
        # Check if there's already a lead comment for this response
        existing_comment = LeadComment.query.filter_by(
            response_id=response_id,
            product_id=product.id,
            client_id=owner.id
        ).first()
        
        if existing_comment:
            # Update existing comment
            existing_comment.status = action
            existing_comment.comment = comment
            existing_comment.lead_id = current_user.id
            existing_comment.created_at = datetime.now(timezone.utc)
        else:
            # Create new lead comment
            lead_comment = LeadComment(
                product_id=product.id,
                client_id=owner.id,
                lead_id=current_user.id,
                response_id=response_id,
                status=action,
                comment=comment,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(lead_comment)
        
        # Update the response status if needed
        response.is_reviewed = True
        if action == 'needs_revision':
            response.needs_client_response = True
        else:
            response.needs_client_response = False
            
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Response {action} successfully',
            'action': action
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in admin review: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/admin/invite_user', methods=['GET', 'POST'])
@login_required('superuser')
def invite_user():
    if request.method == 'POST':
        email = request.form['email']
        role = request.form.get('role', 'client')  # Default to client
        organization = request.form.get('organization', '')

        # Validate inputs
        if not email:
            flash('Email is required.')
            return redirect(url_for('invite_user'))

        # Ensure role is always client for this invitation form
        if role != 'client':
            role = 'client'

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('User with this email already exists.')
            return redirect(url_for('invite_user'))

        # Check if there's already a pending invitation
        existing_invitation = InvitationToken.query.filter_by(email=email, is_used=False).first()
        if existing_invitation:
            try:
                if not existing_invitation.is_expired():
                    flash('There is already a pending invitation for this email.')
                    return redirect(url_for('invite_user'))
            except Exception as e:
                print(f"Error checking existing invitation expiration: {e}")
                # If there's an error, assume it's expired and continue with new invitation
                pass

        # Generate invitation token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days to accept

        invitation = InvitationToken(
            token=token,
            email=email,
            role=role,
            organization=organization,
            invited_by=session['user_id'],
            expires_at=expires_at
        )

        db.session.add(invitation)
        db.session.commit()

        # Generate invitation link
        invitation_link = url_for('register', token=token, _external=True)

        # Get inviter's name
        inviter = User.query.get(session['user_id'])
        inviter_name = f"{inviter.first_name} {inviter.last_name}".strip() or inviter.username

        # Try to send email invitation
        email_sent = send_invitation_email(email, role, invitation_link, inviter_name)

        if email_sent:
            flash(f'Invitation email sent successfully to {email}! They will receive a registration link via email.', 'success')
        else:
            flash(f'Invitation created but email could not be sent. Registration link: {invitation_link}', 'warning')

        return redirect(url_for('invite_user'))

    # Get all clients for the dropdown in lead creation form
    clients = User.query.filter_by(role='client').order_by(User.username).all()
    return render_template('admin_invite_user.html', clients=clients)

@app.route('/admin/manage_users')
@login_required('superuser')
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    pending_invitations = InvitationToken.query.filter_by(is_used=False).order_by(InvitationToken.created_at.desc()).all()
    # Get all active clients for lead assignment dropdown
    clients = User.query.filter_by(role='client', is_active=True).order_by(User.username).all()
    return render_template('admin_manage_users.html', users=users, pending_invitations=pending_invitations, clients=clients)

@app.route('/admin/create_lead', methods=['POST'])
@login_required('superuser')
def create_lead():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    assigned_client_id = request.form.get('assigned_client_id')

    # Validate inputs
    if not username or not email or not password:
        flash('Username, email, and password are required.')
        return redirect(url_for('manage_users'))

    if not assigned_client_id:
        flash('Please select a client to assign to this lead.')
        return redirect(url_for('manage_users'))

    if User.query.filter_by(username=username).first():
        flash('Username already exists.')
        return redirect(url_for('manage_users'))

    if User.query.filter_by(email=email).first():
        flash('Email already exists.')
        return redirect(url_for('manage_users'))

    # Validate assigned client exists and is a client
    assigned_client = User.query.get(assigned_client_id)
    if not assigned_client or assigned_client.role != 'client':
        flash('Invalid client selection.')
        return redirect(url_for('manage_users'))

    # Create lead user
    user = User(
        username=username,
        email=email,
        role='lead',
        organization='ACCORIAN',  # Default organization as requested
        assigned_client_id=int(assigned_client_id)
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash(f'Lead user {username} created successfully and assigned to client {assigned_client.username}. Password: {password}')
    return redirect(url_for('manage_users'))

@app.route('/admin/revoke_invitation/<int:invitation_id>')
@login_required('superuser')
def revoke_invitation(invitation_id):
    invitation = InvitationToken.query.get_or_404(invitation_id)
    invitation.is_used = True  # Mark as used to effectively revoke it
    db.session.commit()
    flash('Invitation revoked successfully.')
    return redirect(url_for('manage_users'))

@app.route('/communication/<int:product_id>')
@login_required()
def unified_communication(product_id):
    """Unified communication interface for lead-client conversations without repetition"""
    current_user_role = session.get('role')
    user_id = session['user_id']
    
    # Get product to verify access
    product = Product.query.get_or_404(product_id)
    
    # Get all conversations for this product, grouped by question/response
    # Filter out approved conversations (only show needs revision ones)
    if current_user_role == 'lead':
        # Lead can see conversations for all clients on this product
        conversations = db.session.query(LeadComment).filter(
            LeadComment.product_id == product_id,
            LeadComment.parent_comment_id.is_(None),  # Only root comments
            LeadComment.status.in_(['needs_revision', 'rejected', 'pending'])  # Exclude approved
        ).order_by(LeadComment.created_at.desc()).all()
    elif current_user_role == 'client':
        # Client can only see their own conversations
        conversations = db.session.query(LeadComment).filter(
            LeadComment.product_id == product_id,
            LeadComment.client_id == user_id,
            LeadComment.parent_comment_id.is_(None),  # Only root comments
            LeadComment.status.in_(['needs_revision', 'rejected', 'pending'])  # Exclude approved
        ).order_by(LeadComment.created_at.desc()).all()
    else:
        # Admin/superuser can see all conversations
        conversations = db.session.query(LeadComment).filter(
            LeadComment.product_id == product_id,
            LeadComment.parent_comment_id.is_(None),  # Only root comments
            LeadComment.status.in_(['needs_revision', 'rejected', 'pending'])  # Exclude approved
        ).order_by(LeadComment.created_at.desc()).all()
    
    # Group conversations and build conversation threads
    conversation_threads = []
    for conv in conversations:
        # Get all replies for this conversation
        replies = db.session.query(LeadComment).filter(
            LeadComment.parent_comment_id == conv.id
        ).order_by(LeadComment.created_at.asc()).all()
        
        conversation_threads.append({
            'root_comment': conv,
            'replies': replies,
            'unread_count': len([r for r in replies if not r.is_read and 
                               ((current_user_role == 'client' and r.lead_id == user_id) or
                                (current_user_role == 'lead' and r.client_id == user_id))]),
            'last_activity': replies[-1].created_at if replies else conv.created_at
        })
    
    # Sort by last activity
    conversation_threads.sort(key=lambda x: x['last_activity'], reverse=True)
    
    return render_template('unified_communication.html', 
                         product=product,
                         conversations=conversation_threads,
                         current_user_role=current_user_role,
                         user_id=user_id)

@app.route('/communication/<int:product_id>/new', methods=['POST'])
@login_required('lead')
def create_new_conversation(product_id):
    """Create a new conversation thread"""
    product = Product.query.get_or_404(product_id)
    
    response_id = request.form.get('response_id')
    client_id = request.form.get('client_id')
    comment_text = request.form.get('comment')
    status = request.form.get('status', 'pending')
    
    if not comment_text or not client_id:
        flash('Comment and client are required.', 'error')
        return redirect(url_for('unified_communication', product_id=product_id))
    
    # Create new conversation
    new_comment = LeadComment(
        response_id=response_id,
        lead_id=session['user_id'],
        client_id=client_id,
        product_id=product_id,
        comment=comment_text,
        status=status,
        parent_comment_id=None  # This is a root comment
    )
    
    db.session.add(new_comment)
    db.session.commit()
    
    flash('New conversation started successfully.', 'success')
    return redirect(url_for('unified_communication', product_id=product_id))


@app.route('/lead/approve_client_reply/<int:comment_id>', methods=['POST'])
@login_required('lead')
def approve_client_reply(comment_id):
    """Allow lead to approve a client reply and mark the question as finally approved"""
    client_reply = LeadComment.query.get_or_404(comment_id)
    
    # Verify the lead is authorized to approve this reply
    current_lead = User.query.get(session['user_id'])
    if not current_lead.assigned_client_id or current_lead.assigned_client_id != client_reply.client_id:
        flash('You are not authorized to approve this reply.', 'error')
        return redirect(request.referrer or url_for('dashboard'))
    
    # Update the client reply status to approved
    client_reply.status = 'approved'
    
    # If this reply is related to a specific response, mark that response as approved
    if client_reply.response_id:
        response = QuestionnaireResponse.query.get(client_reply.response_id)
        if response:
            response.is_approved = True
            response.is_reviewed = True
            response.needs_client_response = False
    
    db.session.commit()
    flash('Client reply approved successfully.', 'success')
    return redirect(request.referrer or url_for('lead_comments'))


@app.route('/communication/reply/<int:comment_id>', methods=['POST'])
@login_required()
def reply_to_conversation(comment_id):
    """Reply to an existing conversation"""
    parent_comment = LeadComment.query.get_or_404(comment_id)
    reply_text = request.form.get('reply')
    
    if not reply_text:
        flash('Reply cannot be empty.', 'error')
        return redirect(url_for('unified_communication', product_id=parent_comment.product_id))
    
    current_user_role = session.get('role')
    user_id = session['user_id']
    
    # Determine the reply structure based on user role
    if current_user_role == 'lead':
        reply = LeadComment(
            response_id=parent_comment.response_id,
            lead_id=user_id,
            client_id=parent_comment.client_id,
            product_id=parent_comment.product_id,
            comment=reply_text,
            status='client_reply',  # Lead replying to client
            parent_comment_id=parent_comment.id if parent_comment.parent_comment_id is None else parent_comment.parent_comment_id
        )
    else:  # client
        reply = LeadComment(
            response_id=parent_comment.response_id,
            lead_id=parent_comment.lead_id,
            client_id=user_id,
            product_id=parent_comment.product_id,
            comment=reply_text,
            status='client_response',  # Client replying to lead
            parent_comment_id=parent_comment.id if parent_comment.parent_comment_id is None else parent_comment.parent_comment_id
        )
    
    db.session.add(reply)
    db.session.commit()
    
    flash('Reply sent successfully.', 'success')
    return redirect(url_for('unified_communication', product_id=parent_comment.product_id))


# Rejected Questions Routes
@app.route("/reject_question", methods=["POST"])
@login_required()
def reject_question():
    """Lead rejects a question and sends it back to client"""
    if session.get("role") != "lead":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    question_id = data.get("question_id")
    product_id = data.get("product_id")
    user_id = data.get("user_id")
    reason = data.get("reason", "")
    
    try:
        # Get the response to get question text
        response = QuestionnaireResponse.query.get(question_id)  # question_id is actually response_id
        if not response:
            return jsonify({"error": "Response not found"}), 404
            
        # Create rejected question entry
        rejected_question = RejectedQuestion(
            response_id=question_id,  # question_id is actually response_id
            product_id=product_id,
            user_id=user_id,
            lead_id=session["user_id"],
            question_text=response.question,
            reason=reason,
            status="pending",
            created_at=datetime.now(timezone.utc)
        )
        
        db.session.add(rejected_question)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Question sent back to client for revision"})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/submit_rejected_question_response", methods=["POST"])
@login_required()
def submit_rejected_question_response():
    """Client submits updated response for rejected question"""
    if session.get("role") != "client":
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    rejected_question_id = data.get("rejected_question_id")
    new_option = data.get("new_option")
    
    try:
        # Get the rejected question
        rejected_question = RejectedQuestion.query.get(rejected_question_id)
        if not rejected_question or rejected_question.user_id != session["user_id"]:
            return jsonify({"error": "Invalid request"}), 400
        
        # Update the original response
        response = QuestionnaireResponse.query.get(rejected_question.response_id)
        
        if response:
            response.answer = new_option
            response.updated_at = datetime.now(timezone.utc)
        
        # Mark rejected question as resolved
        rejected_question.status = "resolved"
        rejected_question.new_option = new_option
        rejected_question.resolved_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        # Recalculate scores
        try:
            from ring_heatmap_implementation import RejectedQuestionsManager
            rq_manager = RejectedQuestionsManager(db)
            scores = rq_manager.recalculate_scores_after_update(
                rejected_question.product_id, 
                session["user_id"]
            )
        except Exception as score_error:
            print(f"Error recalculating scores: {score_error}")
            scores = None
        
        return jsonify({
            "success": True, 
            "message": "Response updated successfully",
            "scores": scores
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/get_rejected_questions/<int:product_id>")
@login_required()
def get_rejected_questions(product_id):
    """Get rejected questions for current user and product"""
    try:
        rejected_questions = db.session.query(RejectedQuestion, QuestionnaireResponse).join(
            QuestionnaireResponse, RejectedQuestion.response_id == QuestionnaireResponse.id
        ).filter(
            RejectedQuestion.user_id == session["user_id"],
            RejectedQuestion.product_id == product_id,
            RejectedQuestion.status == "pending"
        ).all()
        
        return render_template("dashboard_client.html", 
                             rejected_questions=rejected_questions,
                             product_id=product_id)
        
    except Exception as e:
        flash(f"Error loading rejected questions: {str(e)}", "error")
        return redirect(url_for("dashboard_client"))

if __name__ == '__main__':
    print("🚀 Starting SecureSphere Application")
    print("Initializing database...")
    init_database()
    print("✅ Application ready")
    app.run(debug=True, port=5001, host='0.0.0.0')