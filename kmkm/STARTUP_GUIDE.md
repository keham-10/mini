# SecureSphere - Quick Startup Guide

## 🚀 Quick Start

### Option 1: Safe Startup (Recommended)
```bash
python3 start_app_safe.py
```

This script will:
- ✅ Check all dependencies
- ✅ Verify database components
- ✅ Validate templates and static files
- ✅ Set up environment variables
- ✅ Start the application safely

### Option 2: Direct Start
```bash
python3 app.py
```

## 📋 Prerequisites

- Python 3.8 or higher
- Required packages (see requirements.txt)

## 🔧 Installation

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Run the safe startup:**
   ```bash
   python3 start_app_safe.py
   ```

## 🌐 Access the Application

Once started, access the application at:
- **URL:** http://127.0.0.1:5001
- **Default Port:** 5001

## 👥 Default Users

The application comes with default users for testing:

### Superuser (Admin)
- **Username:** admin
- **Password:** admin123
- **Role:** Full system access

### Lead Reviewer
- **Username:** lead1
- **Password:** lead123
- **Role:** Review client assessments

### Client
- **Username:** client1
- **Password:** client123
- **Role:** Submit security assessments

## 🗂️ Key Features

### ✅ Completed Improvements
- 🎨 **Modern Chat Interface** - Enhanced lead-client communication
- 📊 **Maturity Score Dashboard** - Removed percentages, focus on 1-5 scale
- 🔄 **Horizontal Maturity Levels** - Better visual layout
- 📝 **Dimension Dropdowns** - Filter communications by dimension
- 🏢 **ACCORIAN Branding** - Updated registration invitations
- 💾 **Comprehensive Database** - ID-based relationships with audit trails

### 🎯 Database Features
- **Audit Logging** - Complete change tracking
- **Maturity Scoring** - Automatic calculation and tracking
- **Data Integrity** - Foreign key constraints
- **Backup System** - Automated database backups
- **Performance** - Optimized indexes and queries

## 🛠️ Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill process using port 5001
   sudo lsof -ti:5001 | xargs kill -9
   ```

2. **Missing Dependencies**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Database Issues**
   - Database files are created automatically in `instance/` directory
   - For fresh start, delete `instance/securesphere.db`

4. **Template Errors**
   - All templates are validated on startup
   - Check browser console for JavaScript errors

### Debug Mode

To run with additional debugging:
```bash
export FLASK_DEBUG=1
python3 start_app_safe.py
```

### Test Database Components
```bash
python3 test_startup.py
```

## 📁 File Structure

```
kmkm/
├── app.py                      # Main Flask application
├── database_manager.py         # Core database operations
├── database_integration.py     # Flask integration layer
├── start_app_safe.py          # Safe startup script
├── test_startup.py            # Test suite
├── templates/                 # HTML templates
├── static/                    # CSS, JS, images
├── instance/                  # Database files (auto-created)
└── requirements.txt           # Dependencies
```

## 🔒 Security Notes

- Change default passwords in production
- Update SECRET_KEY for production deployment
- Review and configure email settings
- Set up proper SSL/TLS for production

## 📊 Database Schema

The application uses a comprehensive database schema with:
- **Users** - Client, Lead, Superuser roles
- **Products** - Security assessment projects
- **Responses** - Client questionnaire answers
- **Communications** - Lead-client interactions
- **Audit Log** - Complete change tracking
- **Maturity Scores** - Detailed scoring by dimension

## 🎨 UI Improvements

### Communication Interface
- Modern chat-like interface
- Real-time message animations
- Improved message bubbles
- Enhanced input area with focus effects

### Admin Dashboard
- Maturity score-based charts (1-5 scale)
- Removed percentage displays
- Better data visualization
- Dimension filtering

### Registration
- Updated invitation text
- ACCORIAN branding
- Simplified role display

## 📞 Support

If you encounter issues:

1. **Check the logs** - Look for error messages in the terminal
2. **Run tests** - Use `python3 test_startup.py`
3. **Review documentation** - Check `DATABASE_USAGE.md`
4. **Restart fresh** - Delete `instance/` directory and restart

## 🎉 Success!

When everything is working correctly, you should see:
- ✅ All startup checks pass
- 🚀 Server starts on http://127.0.0.1:5001
- 🔐 Login page loads properly
- 📊 Dashboards display correctly
- 💬 Communication interface works smoothly

---

**Happy coding! 🚀**