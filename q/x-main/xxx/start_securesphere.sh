#!/bin/bash

# SecureSphere Startup Script
# Professional deployment script with security checks

set -e  # Exit on any error

echo "🚀 Starting SecureSphere Deployment..."

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/workspace/xxx"
PYTHON_CMD="python3"
REQUIREMENTS_FILE="requirements.txt"
LOG_FILE="securesphere.log"

# Functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Change to app directory
cd "$APP_DIR"

# Check Python version
print_status "Checking Python version..."
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
print_success "Using $PYTHON_VERSION"

# Check if virtual environment should be used
if command -v python3-venv &> /dev/null; then
    print_status "Python venv available for isolated environment"
fi

# Install dependencies
print_status "Installing/updating dependencies..."
if [ -f "$REQUIREMENTS_FILE" ]; then
    $PYTHON_CMD -m pip install -r "$REQUIREMENTS_FILE" --break-system-packages --quiet
    print_success "Dependencies installed successfully"
else
    print_error "Requirements file not found!"
    exit 1
fi

# Environment variables check
print_status "Checking environment variables..."

# Set default values if not set
export ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-AdminPass123}
export ADMIN_EMAIL=${ADMIN_EMAIL:-admin@securesphere.com}
export SECRET_KEY=${SECRET_KEY:-supersecretkey-change-in-production}

if [ "$ADMIN_PASSWORD" == "AdminPass123" ]; then
    print_warning "Using default admin password! Set ADMIN_PASSWORD environment variable for production."
fi

if [ "$SECRET_KEY" == "supersecretkey-change-in-production" ]; then
    print_warning "Using default secret key! Set SECRET_KEY environment variable for production."
fi

print_success "Environment configuration ready"

# Database check and initialization
print_status "Checking database..."
if [ -f "instance/securesphere.db" ]; then
    print_success "Database exists"
    
    # Ask user if they want to reset the database
    if [ "$1" == "--reset-db" ]; then
        print_warning "Resetting database as requested..."
        $PYTHON_CMD init_database.py --reset
        print_success "Database reset completed"
    else
        print_status "Use --reset-db flag to reset database if needed"
        $PYTHON_CMD init_database.py
    fi
else
    print_status "Initializing new database..."
    $PYTHON_CMD init_database.py
    print_success "Database initialized"
fi

# Security check
print_status "Running security checks..."

# Check file permissions
if [ "$(stat -c '%a' app.py 2>/dev/null)" == "644" ] || [ "$(stat -c '%a' app.py 2>/dev/null)" == "755" ]; then
    print_success "File permissions look secure"
else
    print_warning "Consider checking file permissions for security"
fi

# Check for debug mode
if grep -q "debug=True" app.py; then
    print_warning "Debug mode detected in app.py - disable for production!"
fi

print_success "Security checks completed"

# Start the application
print_status "Starting SecureSphere Application..."

if [ "$1" == "--production" ]; then
    print_status "Starting in production mode..."
    if command -v gunicorn &> /dev/null; then
        print_success "Using Gunicorn WSGI server"
        gunicorn -w 4 -b 0.0.0.0:5001 --access-logfile "$LOG_FILE" --error-logfile "$LOG_FILE" app:app
    else
        print_warning "Gunicorn not available, using development server"
        $PYTHON_CMD app.py 2>&1 | tee "$LOG_FILE"
    fi
elif [ "$1" == "--background" ]; then
    print_status "Starting in background mode..."
    nohup $PYTHON_CMD app.py > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > securesphere.pid
    print_success "SecureSphere started in background (PID: $PID)"
    print_status "Log file: $LOG_FILE"
    print_status "To stop: kill $PID or use stop_securesphere.sh"
else
    print_status "Starting in development mode..."
    print_status "Use --production for production deployment"
    print_status "Use --background to run in background"
    print_status "Use --reset-db to reset database"
    $PYTHON_CMD app.py
fi

print_success "SecureSphere startup script completed!"

# Display connection information
echo ""
echo "============================================================"
echo "🎉 SecureSphere is ready!"
echo "============================================================"
echo "📱 Access URL: http://localhost:5001"
echo "👤 Admin Login: $ADMIN_USERNAME / [password from env]"
echo "📁 Organization: ACCORIAN"
echo "🔒 Security Features: ✅ Enabled"
echo "📋 Documentation: SECURITY_FEATURES.md"
echo "============================================================"
echo ""