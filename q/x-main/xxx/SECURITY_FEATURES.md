# SecureSphere Security Features Documentation

## Overview
SecureSphere is a comprehensive security assessment platform with enhanced security features, client-specific lead assignments, and mathematical scoring algorithms.

## 🔒 Security Features Implemented

### 1. Authentication & Authorization
- **Role-based Access Control**: Three distinct roles with specific permissions
  - `superuser`: Full admin access to all data and functionality
  - `lead`: Limited access to assigned client data only
  - `client`: Access to own data and products only

- **Secure Password Management**:
  - Passwords hashed using Werkzeug's secure hash functions
  - Minimum password requirements (8+ chars, uppercase, lowercase, numbers)
  - First-time login password change requirement for leads

### 2. Rate Limiting
- **Flask-Limiter** implementation with configurable limits
- Default limits: 200 requests/day, 50 requests/hour
- Login endpoint: 10 attempts/minute
- Registration endpoint: 5 attempts/minute
- Memory-based storage for development (can be upgraded to Redis for production)

### 3. CSRF Protection
- **Flask-WTF CSRF Protection** enabled globally
- CSRF tokens automatically generated and validated
- All forms protected with `{{ csrf_token() }}` template function
- Prevents cross-site request forgery attacks

### 4. File Upload Security
- **Comprehensive file validation**:
  - Extension whitelist: csv, txt, pdf, jpg, jpeg, png, doc, docx, xlsx, zip
  - File size limits (10MB maximum)
  - Magic number validation for common file types
  - Secure filename generation with hash-based naming
  - Upload path sanitization

### 5. Database Security
- **Environment-based Configuration**:
  - Admin credentials from environment variables
  - No hardcoded passwords in source code
  - Secure database initialization

- **SQL Injection Prevention**:
  - SQLAlchemy ORM with parameterized queries
  - Input validation and sanitization

### 6. Client-Specific Data Isolation
- **Lead Assignment System**:
  - Leads can only access data for their assigned client
  - Admin can see all client data
  - Strict access control validation on all data access

## 🧮 Mathematical Scoring Implementation

### Scoring Algorithm
The application implements proper mathematical averaging as specified:

#### 1. Average Dimension Score
```
Average Dimension Score = Sum of scores for all questions in dimension / Number of questions in dimension
```

**Example:**
- Leadership Dimension: Q1=4, Q2=3, Q3=5
- Average = (4+3+5)/3 = 4.0

#### 2. Overall Maturity Score
```
Overall Maturity Score = Sum of average scores of all dimensions / Number of dimensions
```

**Example:**
- Leadership: 4.0
- Strategy: 3.0  
- Technology: 4.67
- Overall = (4.0+3.0+4.67)/3 = 3.89

### Maturity Levels
- **Level 5 - Optimized**: 90%+ score
- **Level 4 - Managed**: 75-89% score
- **Level 3 - Defined**: 60-74% score
- **Level 2 - Developing**: 40-59% score  
- **Level 1 - Initial**: Below 40% score

## 🚀 Installation & Setup

### Prerequisites
```bash
Python 3.8+
Flask and dependencies (see requirements.txt)
```

### Environment Variables
Set these environment variables for secure operation:
```bash
export ADMIN_USERNAME=admin                    # Default: admin
export ADMIN_PASSWORD=AdminPass123            # Default: AdminPass123
export ADMIN_EMAIL=admin@securesphere.com     # Default: admin@securesphere.com
export SECRET_KEY=your-secret-key-here        # Required for production
export MAIL_SERVER=smtp.gmail.com             # For email notifications
export MAIL_USERNAME=your-email@domain.com    # SMTP username
export MAIL_PASSWORD=your-app-password        # SMTP password
```

### Database Setup
```bash
# Reset database (will create clean admin-only setup)
python3 init_database.py --reset

# Regular initialization (preserves existing data)
python3 init_database.py
```

### Running the Application
```bash
# Development
python3 app.py

# Production (use WSGI server like Gunicorn)
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

## 🏗️ Architecture Overview

### User Roles & Permissions

#### Superuser (Admin)
- Create and manage all users
- Access all client data and products
- System configuration and analytics
- User invitation management
- Lead assignment to specific clients

#### Lead Reviewer
- Access only assigned client's data
- Review client questionnaire responses
- Communicate with assigned client only
- Cannot see other clients' information

#### Client
- Manage own products and assessments
- Complete questionnaires
- View own results and scores
- Communicate with assigned lead reviewer

### Client-Specific Lead Assignment
1. **Admin creates lead**: Selects specific client during lead creation
2. **Data isolation**: Lead can only access assigned client's data
3. **Secure validation**: All data access checks client assignment
4. **Communication**: Lead-client conversations are isolated

### Workflow
1. **Admin setup**: Create clients via invitation system
2. **Lead assignment**: Admin creates leads and assigns to specific clients
3. **Assessment process**: Clients complete questionnaires for their products
4. **Review process**: Assigned leads review and communicate with clients
5. **Results**: Mathematical scoring provides maturity levels and insights

## 🛡️ Security Best Practices Implemented

### Input Validation
- All user inputs validated server-side
- Email format validation with regex
- Password strength requirements
- File type and size validation

### Session Management
- Secure session handling with Flask sessions
- Role-based access checks on every request
- Session timeout configuration

### Error Handling
- Graceful error handling without information disclosure
- Secure error messages that don't reveal system details
- Proper exception logging

### Data Privacy
- Client data completely isolated per lead assignment
- No cross-client data leakage
- Admin-only global data access

## 📋 Default Admin Credentials
- **Username**: `admin` (configurable via ADMIN_USERNAME)
- **Password**: `AdminPass123` (configurable via ADMIN_PASSWORD)
- **Role**: `superuser`
- **Organization**: `ACCORIAN`

⚠️ **Important**: Change these credentials in production by setting environment variables!

## 🔄 Maintenance

### Database Backup
The system automatically backs up existing databases during reset operations.

### Security Updates
- Regularly update dependencies in requirements.txt
- Monitor security advisories for Flask and related packages
- Review and update rate limiting as needed

### Monitoring
- Application logs for security events
- Rate limiting alerts
- Failed login attempt monitoring

## 🚨 Production Considerations

### Security Hardening
1. Use HTTPS/TLS encryption
2. Set strong SECRET_KEY from environment
3. Use production WSGI server (Gunicorn/uWSGI)
4. Configure proper firewall rules
5. Regular security audits and updates
6. Use Redis for rate limiting storage
7. Implement log monitoring and alerting

### Scalability
- Database can be migrated to PostgreSQL/MySQL
- Redis for session storage and rate limiting
- Load balancer for multiple app instances
- CDN for static assets

---

**Version**: 2.0.0  
**Last Updated**: July 2025  
**Maintainer**: SecureSphere Development Team