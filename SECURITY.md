# Library Management System - Secure Version

A comprehensive library management system with **role-based access control**, **advanced security features**, and **rate limiting**.

## 🔐 Security Features Implemented

### 1. **Authentication & Authorization**

- ✅ User registration and login system
- ✅ Role-based access control (Admin & Student)
- ✅ Session-based authentication with Flask-Session
- ✅ Password hashing using werkzeug PBKDF2 algorithm
- ✅ Secure session cookies (HttpOnly, SameSite)

### 2. **Input Validation & Protection**

- ✅ All form inputs validated on server-side
- ✅ Username validation (3-20 chars, alphanumeric + underscore only)
- ✅ Email validation (RFC standard)
- ✅ Password strength validation (6-128 characters)
- ✅ String length limits on all text fields (prevents buffer overflow)
- ✅ Date format validation
- ✅ **SQL Injection Prevention**: All database queries use parameterized queries with `?` placeholders
- ✅ No direct SQL string concatenation

### 3. **Rate Limiting**

- ✅ Maximum 5 concurrent users system-wide
- ✅ Maximum 2 concurrent Admin users
- ✅ Maximum 3 concurrent Student users
- ✅ Active session tracking in database
- ✅ Automatic login rejection when limits exceeded

### 4. **Secrets Management**

- ✅ All sensitive data moved to `.env` file (not in code)
- ✅ `.env` must be added to `.gitignore` (not committed)
- ✅ Environment variables for:
  - Flask secret key
  - Session cookie settings
  - Rate limiting thresholds
  - Debug mode (ALWAYS False in production)

### 5. **Frontend Security**

- ✅ Disabled autocomplete on password fields
- ✅ Prevented browser context menu on sensitive fields
- ✅ F12/DevTools prevention for admin panel
- ✅ No sensitive data in HTML source
- ✅ CSRF protection via Flask-WTF (enabled globally)

### 6. **Audit Logging**

- ✅ All user actions logged to database
- ✅ Tracks: login, logout, book issues, returns, user creation/deletion
- ✅ Admin can view complete audit logs
- ✅ Timestamps and user information recorded

### 7. **Database Security**

- ✅ Parameterized queries prevent SQL injection
- ✅ Password stored as hashed values (never plain text)
- ✅ Foreign key constraints enforced
- ✅ User roles stored as enum-like values

---

## 📋 User Roles & Permissions

### Admin Panel

- View dashboard with statistics
- Manage users (create, view, delete)
- Manage books (add, view, delete)
- Access complete audit logs
- Issue/return books (if needed)

### Student Panel

- Browse available books
- Issue books to self
- Return issued books
- View personal issue history
- Cannot access other users' data
- Cannot modify system data

---

## 🚀 Installation & Setup

### 1. Install Dependencies

```bash
# Option A: Use the setup script (Windows)
setup.bat

# Option B: Manual installation
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file with your settings:

```
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secret-key-here-minimum-32-chars
SESSION_COOKIE_SECURE=False
MAX_CONCURRENT_USERS=5
MAX_ADMIN_USERS=2
MAX_STUDENT_USERS=3
```

**Important**: Change `SECRET_KEY` in production!

### 3. Run the Application

```bash
python app.py
```

Server starts at `http://localhost:5000`

---

## 👥 Default Test Accounts

After first run, create accounts via the registration page:

**Admin Account** (create one in registration):

- Username: `admin1`
- Role: `Admin`

**Student Account** (create one in registration):

- Username: `student1`
- Role: `Student`

---

## 📊 Features

### Admin Features

- **Dashboard**: View total books, users, and active issues
- **User Management**: Add/remove users, view user list
- **Book Management**: Add new books, delete existing books
- **Audit Logs**: Complete activity log of all user actions
- **Rate Limiting**: System enforces concurrent user limits

### Student Features

- **Browse Books**: View all available books
- **Issue Books**: Issue available books with custom dates
- **Return Books**: Return issued books
- **My History**: View personal book issue/return history
- **Dashboard**: Quick stats on available and issued books

---

## 🔒 Security Checklist

- [x] Debug mode disabled (debug=False)
- [x] All inputs validated server-side
- [x] SQL injection prevention via parameterized queries
- [x] Password hashing with PBKDF2
- [x] Rate limiting enforced
- [x] Secrets in .env (not in code)
- [x] CSRF protection enabled
- [x] Session cookies secure
- [x] Audit logging implemented
- [x] Role-based access control
- [x] No sensitive data in HTML
- [x] Browser dev tools detection

---

## 📁 File Structure

```
LIBRARY MANAGEMENT SYSTEM/
├── app.py                          # Main Flask application (SECURE VERSION)
├── .env                            # Environment variables (gitignored)
├── requirements.txt                # Python dependencies
├── run.bat / run.sh               # Quick start scripts
├── setup.bat                       # Setup script
├── templates/
│   ├── base.html                  # Base template with navbar
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   ├── admin_dashboard.html       # Admin dashboard
│   ├── admin_books.html           # Admin book management
│   ├── admin_add_book.html        # Add book form
│   ├── admin_users.html           # Admin user management
│   ├── admin_logs.html            # Audit logs viewer
│   ├── student_dashboard.html     # Student dashboard
│   ├── student_books.html         # Browse books
│   ├── student_issue_book.html    # Issue book form
│   └── student_return_book.html   # Return book form
└── library.db                      # SQLite database
```

---

## 🗄️ Database Schema

### users table

- id (PRIMARY KEY)
- username (UNIQUE)
- email (UNIQUE)
- password_hash (PBKDF2)
- role (Admin/Student)
- created_at

### books table

- id (PRIMARY KEY)
- title
- author
- status (Available/Issued)
- issued_to (username)
- issue_date
- return_date

### issue_history table

- id (PRIMARY KEY)
- book_id (FOREIGN KEY)
- book_title
- issued_to
- issue_date
- expected_return_date
- returned_by
- actual_return_date
- status (Active/Returned)
- created_at

### active_sessions table

- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- username
- role
- login_time
- last_activity

### audit_log table

- id (PRIMARY KEY)
- user_id (FOREIGN KEY)
- action (login/logout/add_book/etc)
- details (action-specific info)
- timestamp

---

## 🛡️ Input Validation Examples

### Username

- **Valid**: `john_doe`, `user123`, `admin_2024`
- **Invalid**: `jo`, `user@name`, `user#123` (too short, special chars)

### Email

- **Valid**: `user@example.com`, `admin@company.co.uk`
- **Invalid**: `user@`, `@example.com` (missing parts)

### Password

- **Valid**: `MyPass123`, `SecurePassword2024`
- **Invalid**: `pass`, `` (too short, empty)

### Book Title/Author

- **Valid**: `The Great Gatsby`, `F. Scott Fitzgerald`
- **Invalid**: `""` (empty), 201 characters (too long)

---

## ⚠️ Security Notes

### Environment Variables

- **NEVER commit `.env` file**
- **Change `SECRET_KEY` in production**
- Use strong, random secret keys (32+ characters)

### Passwords

- Stored as PBKDF2 hashes (never plain text)
- Minimum 6 characters enforced
- Maximum 128 characters

### Rate Limiting

- Configured for: 2 admins, 3 students simultaneously
- Can be adjusted in `.env`
- New login rejected if limit exceeded

### Audit Logs

- All actions timestamped and logged
- Helps track malicious activity
- Admin can monitor in real-time

---

## 🐛 Troubleshooting

### "Port already in use"

```bash
# Kill process on port 5000
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### "Too many concurrent users"

- Wait for users to logout
- Limits: 2 admins, 3 students
- Check active sessions in admin panel

### Database locked

- Close other app instances
- Delete `library.db` to reset (WARNING: loses data)

---

## 📝 License

This project is for educational purposes.

---

## 🔄 Version History

- **v2.0** (Current): Secure version with auth, admin/student panels, rate limiting
- **v1.0**: Original basic library management system

---

**Last Updated**: 2024
**Status**: Production-Ready (with .env configuration)
