# Quick Start Guide

## Installation

### Step 1: Run Setup

```bash
setup.bat
```

This will:

- Create a virtual environment if needed
- Install all dependencies

### Step 2: Verify Files

Check that you have:

- ✅ `app.py` (new secure version)
- ✅ `.env` (with SECRET_KEY and config)
- ✅ All template files in `templates/`
- ✅ `requirements.txt` updated

### Step 3: Start Server

```bash
python app.py
```

Open browser to: `http://localhost:5000`

---

## First Time Setup

### Create Admin Account

1. Go to register page
2. Username: `admin123`
3. Email: `admin@example.com`
4. Password: `Admin@123`
5. Role: **Admin**
6. Click Register

### Create Student Account

1. Go to register page
2. Username: `student123`
3. Email: `student@example.com`
4. Password: `Student@123`
5. Role: **Student**
6. Click Register

### Login & Test

1. Login with admin account
2. Go to Admin Dashboard
3. Add some test books
4. Create more student accounts
5. Test student book borrowing

---

## Security Features to Test

### 1. Rate Limiting

- Login with 2 admin accounts simultaneously
- Try to login with 3rd admin → should be rejected
- Try to login with 3 student accounts → should all work
- Try to login 4th student → should be rejected

### 2. Input Validation

- Try registering with username `ab` (too short) → rejected
- Try registering with email `invalid@` → rejected
- Try registering with password `123` (too short) → rejected
- Try adding book with empty title → rejected

### 3. SQL Injection Prevention

- Try entering SQL in book title: `'; DROP TABLE books; --` → should be treated as text
- Try entering SQL in username field → should be rejected by validation
- Check database - no tables deleted = SECURE ✅

### 4. Secrets Protection

- Open DevTools (F12) → should not see password fields
- Check HTML source → should not see SECRET_KEY or passwords
- Check .env file → NOT committed to git ✅

### 5. Audit Logging

- Admin: Go to Audit Logs
- Perform actions (add book, issue book, etc.)
- Check logs appear with timestamp ✅

### 6. Role-Based Access

- Logout from admin
- Login as student
- Try to access `/admin` → redirected to student dashboard
- Student cannot manage users/books ✅

---

## Database

### Reset Database (if needed)

```bash
# Delete the old database
del library.db

# Restart app - new database created
python app.py
```

### View Database

```bash
# Install DB browser
pip install db-browser

# Or use SQLite CLI
sqlite3 library.db
.tables
SELECT * FROM users;
SELECT * FROM audit_log;
```

---

## Troubleshooting

### Issue: "Port 5000 already in use"

```bash
# Find process
netstat -ano | findstr :5000

# Kill it
taskkill /PID <PID> /F
```

### Issue: "ModuleNotFoundError"

```bash
# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Issue: "Too many concurrent users"

- Logout from extra accounts
- Or wait a few minutes for sessions to expire

### Issue: "Database is locked"

- Close all browser tabs
- Restart Flask app
- Delete `flask_session` folder

---

## Environment Variables (.env)

```
FLASK_ENV=production              # Production mode
FLASK_DEBUG=False                 # Debug OFF
SECRET_KEY=your-key-here          # Change this! (32+ chars)
SESSION_COOKIE_SECURE=False       # True in HTTPS
SESSION_COOKIE_HTTPONLY=True      # Always True
MAX_CONCURRENT_USERS=5            # Total limit
MAX_ADMIN_USERS=2                 # Admin limit
MAX_STUDENT_USERS=3               # Student limit
PASSWORD_RESET_OTP_MINUTES=10     # OTP expiry window
SMTP_HOST=smtp.gmail.com          # Email server for OTP
SMTP_PORT=587                     # Email server port
SMTP_USE_TLS=True                 # Use TLS for SMTP
SMTP_USERNAME=your@email.com      # SMTP login
SMTP_PASSWORD=your-app-password   # SMTP password/app password
SMTP_FROM_EMAIL=your@email.com    # Sender address
```

---

## Performance Notes

- Database: SQLite (single-file, no setup needed)
- Sessions: File-based (stored in `flask_session/`)
- Concurrent users: Max 5 (configurable)
- Database queries: All parameterized (safe)

---

## What's New (vs Old Version)

| Feature                  | Old        | New                     |
| ------------------------ | ---------- | ----------------------- |
| Authentication           | ❌ No      | ✅ Yes (login/register) |
| Admin Panel              | ❌ No      | ✅ Yes (full control)   |
| Student Panel            | ❌ No      | ✅ Yes (limited access) |
| SQL Injection Protection | ⚠️ Partial | ✅ Full (parameterized) |
| Input Validation         | ❌ No      | ✅ Yes (all fields)     |
| Rate Limiting            | ❌ No      | ✅ Yes (5 concurrent)   |
| Secrets Management       | ❌ In code | ✅ In .env              |
| Debug Mode               | ⚠️ ON      | ✅ OFF                  |
| Audit Logging            | ❌ No      | ✅ Yes (complete)       |
| Password Hashing         | ❌ No      | ✅ Yes (PBKDF2)         |
| CSRF Protection          | ❌ No      | ✅ Yes (Flask-WTF)      |

---

## Support

All security measures implemented. Report issues to development team.

**Security Contact**: Keep .env file secure!
