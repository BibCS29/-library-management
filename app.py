import sqlite3
import os
import re
import secrets
import smtplib
from email.message import EmailMessage
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_session import Session
from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-insecure-key')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
# Ensure cookies become invalid when the server is restarted.
# We store a server restart token in the session; if it doesn't match
# current token stored in the app, user is forced to log in again.
# Unique token for this running process. Used to invalidate any stale
# Flask-Session data after server restart/quit.
app.config['SESSION_RESTART_EPOCH'] = str(secrets.token_hex(16))

app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

Session(app)
csrf = CSRFProtect(app)
# Ensure {{ csrf_token() }} is always available in templates
app.jinja_env.globals['csrf_token'] = generate_csrf


MAX_CONCURRENT_USERS = int(os.getenv('MAX_CONCURRENT_USERS', '5'))
MAX_ADMIN_USERS = int(os.getenv('MAX_ADMIN_USERS', '2'))
MAX_STUDENT_USERS = int(os.getenv('MAX_STUDENT_USERS', '3'))
PASSWORD_RESET_OTP_MINUTES = int(os.getenv('PASSWORD_RESET_OTP_MINUTES', '10'))
NOTICE_UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'notices')
ALLOWED_NOTICE_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'}


def get_db_connection():
    conn = sqlite3.connect('library.db')
    conn.row_factory = sqlite3.Row
    return conn


def ensure_column(conn, table, column, definition):
    columns = [row['name'] for row in conn.execute(f'PRAGMA table_info({table})').fetchall()]
    if column not in columns:
        conn.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')


def allowed_notice_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_NOTICE_EXTENSIONS


def save_notice_upload(file_storage):
    if not file_storage or not file_storage.filename:
        return None, None

    if not allowed_notice_file(file_storage.filename):
        return None, "Only PDF and image files are allowed."

    os.makedirs(NOTICE_UPLOAD_FOLDER, exist_ok=True)
    original_name = secure_filename(file_storage.filename)
    extension = original_name.rsplit('.', 1)[1].lower()
    stored_name = f"{secrets.token_hex(8)}_{original_name}"
    file_storage.save(os.path.join(NOTICE_UPLOAD_FOLDER, stored_name))

    return {
        'file_name': original_name,
        'file_path': f"uploads/notices/{stored_name}",
        'file_type': extension,
    }, None


def get_active_login_notices():
    try:
        conn = get_db_connection()
        notices = conn.execute(
            '''SELECT * FROM login_notifications
               WHERE is_active = 1
               ORDER BY created_at DESC'''
        ).fetchall()
        conn.close()
        return notices
    except sqlite3.Error:
        return []


@app.context_processor
def inject_admin_message_count():
    unread_admin_messages = 0
    if session.get('role') == 'Admin':
        conn = None
        try:
            conn = get_db_connection()
            unread_admin_messages = conn.execute(
                'SELECT COUNT(*) as count FROM admin_messages WHERE status = ?',
                ('Unread',)
            ).fetchone()['count']
        except sqlite3.Error:
            unread_admin_messages = 0
        finally:
            if conn:
                conn.close()

    return {
        'unread_admin_messages': unread_admin_messages,
        'current_display_name': session.get('display_name') or session.get('username'),
        'login_notices': get_active_login_notices(),
    }


def init_db():
    conn = get_db_connection()
    os.makedirs(NOTICE_UPLOAD_FOLDER, exist_ok=True)
    
    # Create users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'Student',
            full_name TEXT,
            department TEXT,
            programme TEXT,
            semester TEXT,
            academic_year TEXT,
            contact_number TEXT,
            gender TEXT,
            caste TEXT,
            profile_completed INTEGER DEFAULT 0,
            profile_edit_allowed INTEGER DEFAULT 1,
            is_restricted INTEGER DEFAULT 0,
            restriction_reason TEXT,
            restricted_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    user_columns = {
        'full_name': 'TEXT',
        'department': 'TEXT',
        'programme': 'TEXT',
        'semester': 'TEXT',
        'academic_year': 'TEXT',
        'contact_number': 'TEXT',
        'gender': 'TEXT',
        'caste': 'TEXT',
        'profile_completed': 'INTEGER DEFAULT 0',
        'profile_edit_allowed': 'INTEGER DEFAULT 1',
        'is_restricted': 'INTEGER DEFAULT 0',
        'restriction_reason': 'TEXT',
        'restricted_at': 'TEXT',
    }
    for column, definition in user_columns.items():
        ensure_column(conn, 'users', column, definition)
    
    # Create books table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            status TEXT DEFAULT 'Available',
            issued_to TEXT,
            issue_date TEXT,
            return_date TEXT
        )
    ''')
    
    # Create issue_history table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS issue_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            book_title TEXT NOT NULL,
            issued_to TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            expected_return_date TEXT NOT NULL,
            returned_by TEXT,
            actual_return_date TEXT,
            status TEXT DEFAULT 'Active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id)
        )
    ''')
    
    # Create audit log table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Create active sessions table for rate limiting
    conn.execute('''
        CREATE TABLE IF NOT EXISTS active_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            login_time TEXT NOT NULL,
            last_activity TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create book request table for admin approval workflow
    conn.execute('''
        CREATE TABLE IF NOT EXISTS book_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            student_username TEXT NOT NULL,
            request_date TEXT NOT NULL,
            expected_return_date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            admin_id INTEGER,
            admin_action_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (admin_id) REFERENCES users(id)
        )
    ''')

    # Create student notifications for login/dashboard dialogs
    conn.execute('''
        CREATE TABLE IF NOT EXISTS student_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create password reset OTP table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS password_reset_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Create student-to-admin messages table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS admin_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            student_username TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'Unread',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            read_at TEXT,
            admin_reply TEXT,
            replied_by INTEGER,
            replied_at TEXT,
            FOREIGN KEY (student_id) REFERENCES users(id)
        )
    ''')

    message_columns = {
        'admin_reply': 'TEXT',
        'replied_by': 'INTEGER',
        'replied_at': 'TEXT',
    }
    for column, definition in message_columns.items():
        ensure_column(conn, 'admin_messages', column, definition)

    # Create public login notifications table for notices and attachments
    conn.execute('''
        CREATE TABLE IF NOT EXISTS login_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT,
            file_name TEXT,
            file_path TEXT,
            file_type TEXT,
            is_active INTEGER DEFAULT 1,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')

    conn.execute('CREATE INDEX IF NOT EXISTS idx_reset_otps_user ON password_reset_otps(user_id, used)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_admin_messages_status ON admin_messages(status, created_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_book_requests_status ON book_requests(status, created_at)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_book_requests_student ON book_requests(student_id, status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_student_notifications_user ON student_notifications(user_id, is_read)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_login_notifications_active ON login_notifications(is_active, created_at)')
    
    conn.commit()
    conn.close()


# Input validation functions
def validate_username(username):
    if not username or len(username) < 3 or len(username) > 20:
        return False, "Username must be 3-20 characters"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username must contain only alphanumeric characters and underscores"
    return True, ""

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not email or not re.match(pattern, email):
        return False, "Invalid email format"
    if len(email) > 100:
        return False, "Email too long"
    return True, ""

def validate_password(password):
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters"
    if len(password) > 128:
        return False, "Password too long"
    return True, ""

def validate_string(value, field_name, min_len=1, max_len=200):
    if not value or not isinstance(value, str):
        return False, f"{field_name} is required"
    value = value.strip()
    if len(value) < min_len or len(value) > max_len:
        return False, f"{field_name} must be {min_len}-{max_len} characters"
    return True, ""

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True, ""
    except:
        return False, "Invalid date format (use YYYY-MM-DD)"

def validate_optional_field(value, field_name, max_len=100):
    value = (value or '').strip()
    if len(value) > max_len:
        return False, f"{field_name} must be {max_len} characters or less"
    return True, ""

def collect_profile_form(role='Student'):
    if role == 'Admin':
        # Professional Librarian fields
        return {
            'full_name': request.form.get('full_name', '').strip(),
            'department': request.form.get('department', '').strip(),
            'grade': request.form.get('grade', '').strip(),  # Changed from programme
            'email': request.form.get('email', '').strip(),   # Changed from semester
            'contact_number': request.form.get('contact_number', '').strip(),
            'gender': request.form.get('gender', '').strip(),
        }
    else:
        # Student fields (unchanged)
        return {
            'full_name': request.form.get('full_name', '').strip(),
            'department': request.form.get('department', '').strip(),
            'programme': request.form.get('programme', '').strip(),
            'semester': request.form.get('semester', '').strip(),
            'academic_year': request.form.get('academic_year', '').strip(),
            'contact_number': request.form.get('contact_number', '').strip(),
            'gender': request.form.get('gender', '').strip(),
            'caste': request.form.get('caste', '').strip(),
        }

def validate_profile_data(profile, role='Student'):
    valid, msg = validate_string(profile['full_name'], 'Name', 2, 100)
    if not valid:
        return False, msg

    if role == 'Admin':
        limits = {
            'department': ('Department', 100),
            'grade': ('Grade', 100),
            'email': ('Email', 100),
            'contact_number': ('Contact number', 20),
            'gender': ('Gender', 30),
        }
    else:
        limits = {
            'department': ('Department', 100),
            'programme': ('Programme', 100),
            'semester': ('Semester', 30),
            'academic_year': ('Year', 30),
            'contact_number': ('Contact number', 20),
            'gender': ('Gender', 30),
            'caste': ('Caste', 50),
        }
    
    for key, (label, max_len) in limits.items():
        if key not in profile:
            continue
        valid, msg = validate_optional_field(profile[key], label, max_len)
        if not valid:
            return False, msg

    if profile.get('contact_number') and not re.match(r'^[0-9+\-\s]{7,20}$', profile['contact_number']):
        return False, "Contact number can contain only digits, spaces, +, and -"
    
    if role == 'Admin' and profile.get('email'):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', profile['email']):
            return False, "Please enter a valid email address"

    return True, ""

def get_student_request_block(conn, user_id, username):
    pending_request = conn.execute(
        '''SELECT br.id, b.title FROM book_requests br
           JOIN books b ON br.book_id = b.id
           WHERE br.student_id = ? AND br.status = ?
           ORDER BY br.created_at DESC LIMIT 1''',
        (user_id, 'Pending')
    ).fetchone()

    if pending_request:
        return f"Your request for '{pending_request['title']}' is waiting for admin approval."

    active_issue = conn.execute(
        '''SELECT book_title, status FROM issue_history
           WHERE issued_to = ? AND status IN (?, ?)
           ORDER BY created_at DESC LIMIT 1''',
        (username, 'Active', 'Return Pending')
    ).fetchone()

    if active_issue and active_issue['status'] == 'Return Pending':
        return f"Your return for '{active_issue['book_title']}' is waiting for admin confirmation."

    if active_issue:
        return f"You already have '{active_issue['book_title']}' issued to you. Return it and wait for admin confirmation before booking another book."

    return ""

def add_student_notification(user_id, message):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO student_notifications (user_id, message) VALUES (?, ?)',
        (user_id, message)
    )
    conn.commit()
    conn.close()

def generate_otp():
    return ''.join(secrets.choice('0123456789') for _ in range(6))

def send_password_reset_otp(user, otp):
    smtp_host = os.getenv('SMTP_HOST', '').strip()
    try:
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
    except ValueError:
        smtp_port = 587
    smtp_username = os.getenv('SMTP_USERNAME', '').strip()
    smtp_password = os.getenv('SMTP_PASSWORD', '')
    smtp_from = os.getenv('SMTP_FROM_EMAIL', '').strip() or smtp_username
    smtp_use_tls = os.getenv('SMTP_USE_TLS', 'True') == 'True'

    if not smtp_host or not smtp_from:
        return False, "Email is not configured. Add SMTP settings in .env before using password reset."

    message = EmailMessage()
    message['Subject'] = 'Library Management System Password Reset OTP'
    message['From'] = smtp_from
    message['To'] = user['email']
    message.set_content(
        f"Hello {user['username']},\n\n"
        f"Your password reset OTP is: {otp}\n\n"
        f"This code expires in {PASSWORD_RESET_OTP_MINUTES} minutes.\n"
        "If you did not request this reset, you can ignore this email.\n"
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            if smtp_use_tls:
                server.starttls()
            if smtp_username:
                server.login(smtp_username, smtp_password)
            server.send_message(message)
        return True, "OTP sent to your registered email."
    except Exception:
        return False, "Could not send the OTP email. Check SMTP settings and try again."

# Rate limiting check
def check_rate_limit(role=None):
    role = role or session.get('role')
    conn = get_db_connection()
    
    admin_count = conn.execute(
        'SELECT COUNT(*) as count FROM active_sessions WHERE role = ?',
        ('Admin',)
    ).fetchone()['count']
    
    student_count = conn.execute(
        'SELECT COUNT(*) as count FROM active_sessions WHERE role = ?',
        ('Student',)
    ).fetchone()['count']
    
    conn.close()
    
    if admin_count >= MAX_ADMIN_USERS and role == 'Admin':
        return False, f"Maximum {MAX_ADMIN_USERS} admins logged in"
    if student_count >= MAX_STUDENT_USERS and role == 'Student':
        return False, f"Maximum {MAX_STUDENT_USERS} students logged in"
    
    return True, ""

# Decorators for authentication
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Force re-login after server restart/quit (prevents stale cookies/sessions).
        # The token is generated per running server process.
        if 'server_restart_token' not in session or session.get('server_restart_token') != app.config.get('SESSION_RESTART_EPOCH'):
            session.clear()
            return redirect(url_for('login'))

        if 'user_id' not in session:
            session.clear()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Force re-login after server restart/quit (same as login_required)
        if 'server_restart_token' not in session or session.get('server_restart_token') != app.config.get('SESSION_RESTART_EPOCH'):
            session.clear()
            return redirect(url_for('index'))
        if 'user_id' not in session or session.get('role') != 'Admin':
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Force re-login after server restart/quit (same as login_required)
        if 'server_restart_token' not in session or session.get('server_restart_token') != app.config.get('SESSION_RESTART_EPOCH'):
            session.clear()
            return redirect(url_for('index'))
        if 'user_id' not in session or session.get('role') != 'Student':
            return redirect(url_for('index'))
        conn = get_db_connection()
        user = conn.execute(
            'SELECT is_restricted FROM users WHERE id = ?',
            (session.get('user_id'),)
        ).fetchone()
        conn.close()
        if user and user['is_restricted']:
            session.clear()
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return decorated_function

# Audit logging
def log_action(user_id, action, details=""):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO audit_log (user_id, action, details) VALUES (?, ?, ?)',
        (user_id, action, details)
    )
    conn.commit()
    conn.close()


# ============= AUTHENTICATION ROUTES =============

def complete_login(user):
    # Token invalidates sessions after server restarts.
    session['server_restart_token'] = app.config.get('SESSION_RESTART_EPOCH')
    session['user_id'] = user['id']

    session['username'] = user['username']
    session['role'] = user['role']
    session['display_name'] = user['full_name'] or user['username']
    session.permanent = True

    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO active_sessions (user_id, username, role, login_time, last_activity)
           VALUES (?, ?, ?, ?, ?)''',
        (user['id'], user['username'], user['role'],
         datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
         datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    conn.commit()
    conn.close()

    log_action(user['id'], 'login', f'Role: {user["role"]}')

    if user['role'] == 'Admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('student_dashboard'))


def role_login(expected_role):
    login_endpoint = 'admin_login' if expected_role == 'Admin' else 'student_login'
    success = None
    if request.args.get('reset') == '1':
        success = "Password reset successfully. You can log in with your new password."

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template(
                'login.html',
                role=expected_role,
                login_endpoint=login_endpoint,
                error="Username and password required"
            )

        conn = get_db_connection()
        user = conn.execute(
            '''SELECT id, username, password_hash, role, full_name, is_restricted, restriction_reason
               FROM users
               WHERE lower(username) = lower(?) AND role = ?''',
            (username, expected_role)
        ).fetchone()
        conn.close()

        if not user or not check_password_hash(user['password_hash'], password):
            return render_template(
                'login.html',
                role=expected_role,
                login_endpoint=login_endpoint,
                error=f"Invalid {expected_role.lower()} username or password"
            )

        if user['is_restricted']:
            reason = user['restriction_reason'] or "Contact the library admin."
            return render_template(
                'login.html',
                role=expected_role,
                login_endpoint=login_endpoint,
                error=f"Your account is restricted. {reason}"
            )

        allowed, msg = check_rate_limit(user['role'])
        if not allowed:
            return render_template(
                'login.html',
                role=expected_role,
                login_endpoint=login_endpoint,
                error=msg
            )

        return complete_login(user)

    return render_template('login.html', role=expected_role, login_endpoint=login_endpoint, success=success)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'Student')
        
        # Validate inputs
        valid, msg = validate_username(username)
        if not valid:
            return render_template('register.html', error=msg)
        
        valid, msg = validate_email(email)
        if not valid:
            return render_template('register.html', error=msg)
        
        valid, msg = validate_password(password)
        if not valid:
            return render_template('register.html', error=msg)
        
        if role not in ['Admin', 'Student']:
            role = 'Student'
        
        conn = get_db_connection()
        
        # Check if user exists
        existing = conn.execute(
            'SELECT id FROM users WHERE lower(username) = lower(?) OR lower(email) = lower(?)',
            (username, email)
        ).fetchone()
        
        if existing:
            conn.close()
            return render_template('register.html', error="Username or email already exists")
        
        # Create user
        try:
            password_hash = generate_password_hash(password)
            conn.execute(
                'INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                (username, email, password_hash, role)
            )
            conn.commit()
            conn.close()
            
            log_action(None, 'user_registered', f'Username: {username}')
            if role == 'Admin':
                return redirect(url_for('admin_login'))
            return redirect(url_for('student_login'))
        except Exception as e:
            conn.close()
            return render_template('register.html', error="Registration failed")
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('role') == 'Admin':
        return redirect(url_for('admin_dashboard'))
    if session.get('role') == 'Student':
        return redirect(url_for('student_dashboard'))

    return render_template('login.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    return role_login('Admin')


@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    return role_login('Student')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    selected_role = request.args.get('role', 'Student')
    if selected_role not in ['Admin', 'Student']:
        selected_role = 'Student'

    if request.method == 'POST':
        selected_role = request.form.get('role', 'Student')
        identifier = request.form.get('identifier', '').strip()

        if selected_role not in ['Admin', 'Student']:
            return render_template('forgot_password.html', role='Student', error="Select a valid account type")

        if not identifier:
            return render_template(
                'forgot_password.html',
                role=selected_role,
                error="Enter your username or registered email"
            )

        conn = get_db_connection()
        user = conn.execute(
            '''SELECT id, username, email, role FROM users
               WHERE (lower(username) = lower(?) OR lower(email) = lower(?)) AND role = ?''',
            (identifier, identifier, selected_role)
        ).fetchone()
        conn.close()

        if not user:
            return render_template(
                'forgot_password.html',
                role=selected_role,
                identifier=identifier,
                error="No matching account found"
            )

        otp = generate_otp()
        sent, message = send_password_reset_otp(user, otp)
        if not sent:
            return render_template(
                'forgot_password.html',
                role=selected_role,
                identifier=identifier,
                error=message
            )

        expires_at = (datetime.now() + timedelta(minutes=PASSWORD_RESET_OTP_MINUTES)).strftime('%Y-%m-%d %H:%M:%S')
        conn = get_db_connection()
        conn.execute(
            'UPDATE password_reset_otps SET used = 1 WHERE user_id = ? AND used = 0',
            (user['id'],)
        )
        conn.execute(
            '''INSERT INTO password_reset_otps (user_id, otp_hash, expires_at)
               VALUES (?, ?, ?)''',
            (user['id'], generate_password_hash(otp), expires_at)
        )
        conn.commit()
        conn.close()

        session['password_reset_user_id'] = user['id']
        session['password_reset_role'] = selected_role
        log_action(user['id'], 'password_reset_otp_sent', f'Role: {selected_role}')
        return redirect(url_for('reset_password'))

    return render_template('forgot_password.html', role=selected_role)


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    user_id = session.get('password_reset_user_id')
    selected_role = session.get('password_reset_role', 'Student')

    if not user_id:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not re.match(r'^\d{6}$', otp):
            return render_template('reset_password.html', role=selected_role, error="Enter the 6-digit OTP")

        if password != confirm_password:
            return render_template('reset_password.html', role=selected_role, error="Passwords do not match")

        valid, msg = validate_password(password)
        if not valid:
            return render_template('reset_password.html', role=selected_role, error=msg)

        conn = get_db_connection()
        reset_otp = conn.execute(
            '''SELECT id, otp_hash, expires_at FROM password_reset_otps
               WHERE user_id = ? AND used = 0
               ORDER BY created_at DESC LIMIT 1''',
            (user_id,)
        ).fetchone()

        if not reset_otp:
            conn.close()
            return render_template('reset_password.html', role=selected_role, error="OTP expired. Request a new one.")

        expires_at = datetime.strptime(reset_otp['expires_at'], '%Y-%m-%d %H:%M:%S')
        if expires_at < datetime.now():
            conn.execute('UPDATE password_reset_otps SET used = 1 WHERE id = ?', (reset_otp['id'],))
            conn.commit()
            conn.close()
            return render_template('reset_password.html', role=selected_role, error="OTP expired. Request a new one.")

        if not check_password_hash(reset_otp['otp_hash'], otp):
            conn.close()
            return render_template('reset_password.html', role=selected_role, error="Invalid OTP")

        conn.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (generate_password_hash(password), user_id)
        )
        conn.execute('UPDATE password_reset_otps SET used = 1 WHERE id = ?', (reset_otp['id'],))
        conn.commit()
        conn.close()

        session.pop('password_reset_user_id', None)
        session.pop('password_reset_role', None)
        log_action(user_id, 'password_reset_completed', f'Role: {selected_role}')

        if selected_role == 'Admin':
            return redirect(url_for('admin_login', reset='1'))
        return redirect(url_for('student_login', reset='1'))

    return render_template('reset_password.html', role=selected_role)


@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    username = session.get('username')

    # Remove ALL server-tracked sessions (admin + student) when any user logs out.
    # This matches the requirement: "logout all sessions after it has been logout".
    conn = get_db_connection()
    conn.execute('DELETE FROM active_sessions')
    conn.commit()
    conn.close()

    if user_id is not None:
        log_action(user_id, 'logout_all_sessions', f'Username: {username}')

    session.clear()
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db_connection()
    user = conn.execute(
        '''SELECT id, username, email, role, full_name, department, programme,
                  semester, academic_year, contact_number, gender, caste,
                  profile_completed, profile_edit_allowed, is_restricted
           FROM users WHERE id = ?''',
        (session.get('user_id'),)
    ).fetchone()

    if not user:
        conn.close()
        session.clear()
        return redirect(url_for('login'))

    if user['role'] == 'Student' and user['is_restricted']:
        conn.close()
        session.clear()
        return redirect(url_for('student_login'))

    can_edit = user['role'] == 'Admin' or not user['profile_completed'] or user['profile_edit_allowed']

    if request.method == 'POST':
        if not can_edit:
            conn.close()
            return render_template('profile.html', user=user, can_edit=False, error="Profile editing is locked. Ask admin to allow edits.")

        profile_data = collect_profile_form(user['role'])
        valid, msg = validate_profile_data(profile_data, user['role'])
        if not valid:
            conn.close()
            return render_template('profile.html', user=user, can_edit=True, form=profile_data, error=msg)

        profile_edit_allowed = 1 if user['role'] == 'Admin' else 0
        
        if user['role'] == 'Admin':
            # Professional Librarian profile update
            conn.execute(
                '''UPDATE users
                   SET full_name = ?, department = ?, programme = ?, semester = ?,
                       academic_year = ?, contact_number = ?, gender = ?, caste = ?,
                       profile_completed = 1, profile_edit_allowed = ?
                   WHERE id = ?''',
                (
                    profile_data['full_name'],
                    profile_data['department'],
                    profile_data['grade'],  # Store in programme column
                    profile_data['email'],  # Store in semester column
                    '',  # academic_year blank for admin
                    profile_data['contact_number'],
                    profile_data['gender'],
                    '',  # caste blank for admin
                    profile_edit_allowed,
                    user['id']
                )
            )
        else:
            # Student profile update
            conn.execute(
                '''UPDATE users
                   SET full_name = ?, department = ?, programme = ?, semester = ?,
                       academic_year = ?, contact_number = ?, gender = ?, caste = ?,
                       profile_completed = 1, profile_edit_allowed = ?
                   WHERE id = ?''',
                (
                    profile_data['full_name'],
                    profile_data['department'],
                    profile_data['programme'],
                    profile_data['semester'],
                    profile_data['academic_year'],
                    profile_data['contact_number'],
                    profile_data['gender'],
                    profile_data['caste'],
                    profile_edit_allowed,
                    user['id']
                )
            )
        
        conn.commit()
        conn.close()

        session['display_name'] = profile_data['full_name']
        log_action(session.get('user_id'), 'profile_updated', f'Username: {user["username"]}')
        return redirect(url_for('profile'))

    conn.close()
    return render_template('profile.html', user=user, can_edit=can_edit)



# ============= ADMIN ROUTES =============

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    
    books_count = conn.execute('SELECT COUNT(*) as count FROM books').fetchone()['count']
    users_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
    active_issues = conn.execute(
        'SELECT COUNT(*) as count FROM issue_history WHERE status = "Active"'
    ).fetchone()['count']

    unread_messages = conn.execute(
        'SELECT COUNT(*) as count FROM admin_messages WHERE status = "Unread"'
    ).fetchone()['count']

    pending_requests = conn.execute(
        'SELECT COUNT(*) as count FROM book_requests WHERE status = "Pending"'
    ).fetchone()['count']

    pending_returns = conn.execute(
        'SELECT COUNT(*) as count FROM issue_history WHERE status = "Return Pending"'
    ).fetchone()['count']
    
    recent_logs = conn.execute(
        '''SELECT a.*, u.username FROM audit_log a 
           LEFT JOIN users u ON a.user_id = u.id 
           ORDER BY a.timestamp DESC LIMIT 10'''
    ).fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         books_count=books_count,
                         users_count=users_count,
                         active_issues=active_issues,
                         unread_messages=unread_messages,
                         pending_requests=pending_requests,
                         pending_returns=pending_returns,
                         recent_logs=recent_logs)


@app.route('/admin/users')
@admin_required
def admin_users():
    conn = get_db_connection()
    users = conn.execute(
        '''SELECT id, username, email, role, full_name, department, programme,
                  semester, academic_year, contact_number, gender, caste,
                  profile_completed, profile_edit_allowed, is_restricted,
                  restriction_reason, created_at
           FROM users ORDER BY created_at DESC'''
    ).fetchall()
    conn.close()
    
    return render_template('admin_users.html', users=users)


@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session.get('user_id'):
        return redirect(url_for('admin_users'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if user:
        conn.execute('DELETE FROM student_notifications WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM password_reset_otps WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM active_sessions WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        log_action(session.get('user_id'), 'delete_user', f'Deleted: {user["username"]}')
    
    conn.close()
    return redirect(url_for('admin_users'))


@app.route('/admin/user/<int:user_id>/allow-profile-edit', methods=['POST'])
@admin_required
def allow_profile_edit(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT username, role FROM users WHERE id = ?', (user_id,)).fetchone()

    if user and user['role'] == 'Student':
        conn.execute('UPDATE users SET profile_edit_allowed = 1 WHERE id = ?', (user_id,))
        conn.commit()
        log_action(session.get('user_id'), 'allow_profile_edit', f'Student: {user["username"]}')

    conn.close()
    return redirect(url_for('admin_users'))


@app.route('/admin/user/<int:user_id>/restrict', methods=['POST'])
@admin_required
def restrict_user(user_id):
    reason = request.form.get('restriction_reason', '').strip() or "Restricted by admin."
    conn = get_db_connection()
    user = conn.execute('SELECT username, role FROM users WHERE id = ?', (user_id,)).fetchone()

    if user and user['role'] == 'Student':
        conn.execute(
            '''UPDATE users
               SET is_restricted = 1, restriction_reason = ?, restricted_at = ?
               WHERE id = ?''',
            (reason, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)
        )
        conn.execute('DELETE FROM active_sessions WHERE user_id = ?', (user_id,))
        conn.commit()
        log_action(session.get('user_id'), 'restrict_student', f'Student: {user["username"]}')

    conn.close()
    return redirect(url_for('admin_users'))


@app.route('/admin/user/<int:user_id>/unrestrict', methods=['POST'])
@admin_required
def unrestrict_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT username, role FROM users WHERE id = ?', (user_id,)).fetchone()

    if user and user['role'] == 'Student':
        conn.execute(
            '''UPDATE users
               SET is_restricted = 0, restriction_reason = NULL, restricted_at = NULL
               WHERE id = ?''',
            (user_id,)
        )
        conn.commit()
        log_action(session.get('user_id'), 'unrestrict_student', f'Student: {user["username"]}')

    conn.close()
    return redirect(url_for('admin_users'))


@app.route('/admin/books')
@admin_required
def admin_books():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books ORDER BY title').fetchall()
    conn.close()
    
    return render_template('admin_books.html', books=books)


@app.route('/admin/book-requests')
@admin_required
def admin_book_requests():
    conn = get_db_connection()
    requests = conn.execute(
        '''SELECT br.*, b.title, b.author
           FROM book_requests br
           JOIN books b ON br.book_id = b.id
           ORDER BY CASE WHEN br.status = "Pending" THEN 0 ELSE 1 END, br.created_at DESC'''
    ).fetchall()
    pending_returns = conn.execute(
        '''SELECT ih.*, b.author
           FROM issue_history ih
           JOIN books b ON ih.book_id = b.id
           WHERE ih.status = ?
           ORDER BY ih.created_at DESC''',
        ('Return Pending',)
    ).fetchall()
    conn.close()

    return render_template(
        'admin_book_requests.html',
        requests=requests,
        pending_returns=pending_returns
    )


@app.route('/admin/book-request/<int:request_id>/approve', methods=['POST'])
@admin_required
def approve_book_request(request_id):
    conn = get_db_connection()
    book_request = conn.execute(
        '''SELECT br.*, b.title, b.status as book_status, b.issued_to
           FROM book_requests br
           JOIN books b ON br.book_id = b.id
           WHERE br.id = ?''',
        (request_id,)
    ).fetchone()

    if not book_request or book_request['status'] != 'Pending':
        conn.close()
        return redirect(url_for('admin_book_requests'))

    active_issue = conn.execute(
        '''SELECT id FROM issue_history
           WHERE issued_to = ? AND status IN (?, ?)
           LIMIT 1''',
        (book_request['student_username'], 'Active', 'Return Pending')
    ).fetchone()

    book_is_reserved_for_student = (
        book_request['book_status'] == 'Pending Approval'
        and book_request['issued_to'] == book_request['student_username']
    )

    if active_issue or (book_request['book_status'] != 'Available' and not book_is_reserved_for_student):
        conn.execute(
            '''UPDATE book_requests
               SET status = ?, admin_id = ?, admin_action_at = ?
               WHERE id = ?''',
            ('Rejected', session.get('user_id'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id)
        )
        if book_is_reserved_for_student:
            conn.execute(
                '''UPDATE books
                   SET status = ?, issued_to = NULL, issue_date = NULL, return_date = NULL
                   WHERE id = ?''',
                ('Available', book_request['book_id'])
            )
        conn.commit()
        conn.close()
        return redirect(url_for('admin_book_requests'))

    issue_date = datetime.now().strftime('%Y-%m-%d')
    conn.execute(
        '''UPDATE books
           SET status = ?, issued_to = ?, issue_date = ?, return_date = ?
           WHERE id = ?''',
        ('Issued', book_request['student_username'], issue_date, book_request['expected_return_date'], book_request['book_id'])
    )
    conn.execute(
        '''INSERT INTO issue_history
           (book_id, book_title, issued_to, issue_date, expected_return_date, status)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (
            book_request['book_id'],
            book_request['title'],
            book_request['student_username'],
            issue_date,
            book_request['expected_return_date'],
            'Active'
        )
    )
    conn.execute(
        '''UPDATE book_requests
           SET status = ?, admin_id = ?, admin_action_at = ?
           WHERE id = ?''',
        ('Approved', session.get('user_id'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id)
    )
    conn.commit()
    conn.close()

    add_student_notification(
        book_request['student_id'],
        "The book you have applied for, has been issued to you. You can now collect the book from the library."
    )
    log_action(session.get('user_id'), 'approve_book_request', f'Book: {book_request["title"]}, Student: {book_request["student_username"]}')
    return redirect(url_for('admin_book_requests'))


@app.route('/admin/book-request/<int:request_id>/reject', methods=['POST'])
@admin_required
def reject_book_request(request_id):
    conn = get_db_connection()
    book_request = conn.execute(
        '''SELECT br.*, b.title, b.status as book_status, b.issued_to
           FROM book_requests br
           JOIN books b ON br.book_id = b.id
           WHERE br.id = ?''',
        (request_id,)
    ).fetchone()

    if book_request and book_request['status'] == 'Pending':
        conn.execute(
            '''UPDATE book_requests
               SET status = ?, admin_id = ?, admin_action_at = ?
               WHERE id = ?''',
            ('Rejected', session.get('user_id'), datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id)
        )
        if book_request['book_status'] == 'Pending Approval' and book_request['issued_to'] == book_request['student_username']:
            conn.execute(
                '''UPDATE books
                   SET status = ?, issued_to = NULL, issue_date = NULL, return_date = NULL
                   WHERE id = ?''',
                ('Available', book_request['book_id'])
            )
        conn.commit()
        add_student_notification(
            book_request['student_id'],
            f"Your request for '{book_request['title']}' was not approved by the admin."
        )
        log_action(session.get('user_id'), 'reject_book_request', f'Book: {book_request["title"]}, Student: {book_request["student_username"]}')

    conn.close()
    return redirect(url_for('admin_book_requests'))


@app.route('/admin/return/<int:history_id>/confirm', methods=['POST'])
@admin_required
def confirm_book_return(history_id):
    conn = get_db_connection()
    history = conn.execute(
        '''SELECT ih.*, b.title
           FROM issue_history ih
           JOIN books b ON ih.book_id = b.id
           WHERE ih.id = ? AND ih.status = ?''',
        (history_id, 'Return Pending')
    ).fetchone()

    if history:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            '''UPDATE books
               SET status = ?, issued_to = NULL, issue_date = NULL, return_date = NULL
               WHERE id = ?''',
            ('Available', history['book_id'])
        )
        conn.execute(
            '''UPDATE issue_history
               SET status = ?, returned_by = ?, actual_return_date = ?
               WHERE id = ?''',
            ('Returned', history['issued_to'], now, history_id)
        )
        conn.execute(
            '''UPDATE book_requests
               SET status = ?, admin_id = ?, admin_action_at = ?
               WHERE book_id = ? AND student_username = ? AND status = ?''',
            ('Returned', session.get('user_id'), now, history['book_id'], history['issued_to'], 'Approved')
        )
        conn.commit()
        log_action(session.get('user_id'), 'confirm_book_return', f'Book: {history["book_title"]}, Student: {history["issued_to"]}')

    conn.close()
    return redirect(url_for('admin_book_requests'))


@app.route('/admin/book/add', methods=['GET', 'POST'])
@admin_required
def admin_add_book():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        
        valid, msg = validate_string(title, 'Title', 1, 200)
        if not valid:
            return render_template('admin_add_book.html', error=msg)
        
        valid, msg = validate_string(author, 'Author', 1, 200)
        if not valid:
            return render_template('admin_add_book.html', error=msg)
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO books (title, author) VALUES (?, ?)',
            (title, author)
        )
        conn.commit()
        conn.close()
        
        log_action(session.get('user_id'), 'add_book', f'Title: {title}')
        return redirect(url_for('admin_books'))
    
    return render_template('admin_add_book.html')


@app.route('/admin/book/<int:book_id>/delete', methods=['POST'])
@admin_required
def admin_delete_book(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT title FROM books WHERE id = ?', (book_id,)).fetchone()
    
    if book:
        conn.execute('DELETE FROM book_requests WHERE book_id = ?', (book_id,))
        conn.execute('DELETE FROM issue_history WHERE book_id = ?', (book_id,))
        conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        log_action(session.get('user_id'), 'delete_book', f'Deleted: {book["title"]}')
    
    conn.close()
    return redirect(url_for('admin_books'))


@app.route('/admin/logs')
@admin_required
def admin_logs():
    conn = get_db_connection()
    logs = conn.execute(
        '''SELECT a.*, u.username FROM audit_log a 
           LEFT JOIN users u ON a.user_id = u.id 
           ORDER BY a.timestamp DESC LIMIT 100'''
    ).fetchall()
    conn.close()
    
    return render_template('admin_logs.html', logs=logs)


@app.route('/admin/messages')
@admin_required
def admin_messages():
    conn = get_db_connection()
    messages = conn.execute(
        '''SELECT * FROM admin_messages
           ORDER BY CASE WHEN status = "Unread" THEN 0 ELSE 1 END, created_at DESC'''
    ).fetchall()
    conn.close()

    return render_template('admin_messages.html', messages=messages)


@app.route('/admin/message/<int:message_id>/delete', methods=['POST'])
@admin_required
def delete_admin_message(message_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM admin_messages WHERE id = ?', (message_id,))
    conn.commit()
    conn.close()
    if session.get('user_id') is not None:
        log_action(session.get('user_id'), 'delete_admin_message', f'Message ID: {message_id}')
    return redirect(url_for('admin_messages'))



@app.route('/admin/message/<int:message_id>/read', methods=['POST'])
@admin_required
def mark_admin_message_read(message_id):
    conn = get_db_connection()
    message = conn.execute(
        'SELECT subject FROM admin_messages WHERE id = ?',
        (message_id,)
    ).fetchone()

    if message:
        conn.execute(
            '''UPDATE admin_messages
               SET status = ?, read_at = ?
               WHERE id = ?''',
            ('Read', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message_id)
        )
        conn.commit()
        log_action(session.get('user_id'), 'read_admin_message', f'Subject: {message["subject"]}')

    conn.close()
    return redirect(url_for('admin_messages'))


@app.route('/admin/message/<int:message_id>/reply', methods=['POST'])
@admin_required
def reply_admin_message(message_id):

    reply = request.form.get('reply', '').strip()
    if not reply:
        return redirect(url_for('admin_messages'))

    valid, msg = validate_string(reply, 'Reply', 2, 1000)
    if not valid:
        return redirect(url_for('admin_messages'))

    conn = get_db_connection()
    message = conn.execute(
        'SELECT student_id, student_username, subject FROM admin_messages WHERE id = ?',
        (message_id,)
    ).fetchone()

    if message:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            '''UPDATE admin_messages
               SET admin_reply = ?, replied_by = ?, replied_at = ?,
                   status = ?, read_at = COALESCE(read_at, ?)
               WHERE id = ?''',
            (reply, session.get('user_id'), now, 'Replied', now, message_id)
        )
        conn.commit()
        log_action(session.get('user_id'), 'reply_admin_message', f'Student: {message["student_username"]}, Subject: {message["subject"]}')
        conn.close()
        add_student_notification(
            message['student_id'],
            f"Admin replied to your message '{message['subject']}': {reply}"
        )
        return redirect(url_for('admin_messages'))

    conn.close()
    return redirect(url_for('admin_messages'))


@app.route('/admin/notifications', methods=['GET', 'POST'])
@admin_required
def admin_notifications():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()

        valid, msg = validate_string(title, 'Title', 2, 120)
        if not valid:
            notices = get_active_login_notices()
            return render_template('admin_notifications.html', notices=notices, error=msg)

        valid, msg = validate_optional_field(message, 'Message', 1000)
        if not valid:
            notices = get_active_login_notices()
            return render_template('admin_notifications.html', notices=notices, error=msg)

        upload_info, upload_error = save_notice_upload(request.files.get('attachment'))
        if upload_error:
            notices = get_active_login_notices()
            return render_template('admin_notifications.html', notices=notices, error=upload_error)

        upload_info = upload_info or {}
        conn = get_db_connection()
        conn.execute(
            '''INSERT INTO login_notifications
               (title, message, file_name, file_path, file_type, created_by)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (
                title,
                message,
                upload_info.get('file_name'),
                upload_info.get('file_path'),
                upload_info.get('file_type'),
                session.get('user_id')
            )
        )
        conn.commit()
        conn.close()
        log_action(session.get('user_id'), 'add_login_notification', f'Title: {title}')
        return redirect(url_for('admin_notifications'))

    conn = get_db_connection()
    notices = conn.execute(
        'SELECT * FROM login_notifications ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return render_template('admin_notifications.html', notices=notices)


@app.route('/admin/notification/<int:notice_id>/toggle', methods=['POST'])
@admin_required
def toggle_admin_notification(notice_id):
    conn = get_db_connection()
    notice = conn.execute(
        'SELECT title, is_active FROM login_notifications WHERE id = ?',
        (notice_id,)
    ).fetchone()

    if notice:
        new_state = 0 if notice['is_active'] else 1
        conn.execute(
            'UPDATE login_notifications SET is_active = ? WHERE id = ?',
            (new_state, notice_id)
        )
        conn.commit()
        log_action(session.get('user_id'), 'toggle_login_notification', f'Title: {notice["title"]}')

    conn.close()
    return redirect(url_for('admin_notifications'))


@app.route('/admin/notification/<int:notice_id>/delete', methods=['POST'])
@admin_required
def delete_admin_notification(notice_id):
    conn = get_db_connection()
    notice = conn.execute(
        'SELECT title, file_path FROM login_notifications WHERE id = ?',
        (notice_id,)
    ).fetchone()

    if notice:
        if notice['file_path']:
            file_path = os.path.join(app.root_path, 'static', notice['file_path'].replace('/', os.sep))
            upload_root = os.path.abspath(NOTICE_UPLOAD_FOLDER)
            target_path = os.path.abspath(file_path)
            if os.path.commonpath([upload_root, target_path]) == upload_root and os.path.exists(target_path):
                os.remove(target_path)

        conn.execute('DELETE FROM login_notifications WHERE id = ?', (notice_id,))
        conn.commit()
        log_action(session.get('user_id'), 'delete_login_notification', f'Title: {notice["title"]}')

    conn.close()
    return redirect(url_for('admin_notifications'))


# ============= STUDENT ROUTES =============

@app.route('/student')
@student_required
def student_dashboard():
    conn = get_db_connection()
    
    available_books = conn.execute(
        'SELECT COUNT(*) as count FROM books WHERE status = "Available"'
    ).fetchone()['count']
    
    issued_books = conn.execute(
        '''SELECT COUNT(*) as count FROM issue_history 
           WHERE issued_to = ? AND status IN (?, ?)''',
        (session.get('username'), 'Active', 'Return Pending')
    ).fetchone()['count']
    
    history = conn.execute(
        '''SELECT * FROM issue_history 
           WHERE issued_to = ? 
           ORDER BY created_at DESC LIMIT 10''',
        (session.get('username'),)
    ).fetchall()

    pending_request = conn.execute(
        '''SELECT br.*, b.title FROM book_requests br
           JOIN books b ON br.book_id = b.id
           WHERE br.student_id = ? AND br.status = ?
           ORDER BY br.created_at DESC LIMIT 1''',
        (session.get('user_id'), 'Pending')
    ).fetchone()

    notifications = conn.execute(
        '''SELECT id, message FROM student_notifications
           WHERE user_id = ? AND is_read = 0
           ORDER BY created_at''',
        (session.get('user_id'),)
    ).fetchall()

    if notifications:
        notification_ids = [notification['id'] for notification in notifications]
        placeholders = ','.join('?' for _ in notification_ids)
        conn.execute(
            f'UPDATE student_notifications SET is_read = 1 WHERE id IN ({placeholders})',
            notification_ids
        )
        conn.commit()
    
    conn.close()
    
    return render_template('student_dashboard.html',
                         available_books=available_books,
                         issued_books=issued_books,
                         history=history,
                         pending_request=pending_request,
                         notifications=notifications)


@app.route('/student/books')
@student_required
def student_books():
    conn = get_db_connection()
    books = conn.execute('SELECT * FROM books WHERE status = "Available" ORDER BY title').fetchall()
    request_block_message = get_student_request_block(
        conn,
        session.get('user_id'),
        session.get('username')
    )
    conn.close()
    
    return render_template(
        'student_books.html',
        books=books,
        can_request=not request_block_message,
        request_block_message=request_block_message
    )


@app.route('/student/message', methods=['GET', 'POST'])
@student_required
def student_message_admin():
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        valid, msg = validate_string(subject, 'Subject', 3, 100)
        if not valid:
            return render_template('student_message_admin.html', error=msg, subject=subject, message=message)

        valid, msg = validate_string(message, 'Message', 5, 1000)
        if not valid:
            return render_template('student_message_admin.html', error=msg, subject=subject, message=message)

        conn = get_db_connection()
        conn.execute(
            '''INSERT INTO admin_messages (student_id, student_username, subject, message)
               VALUES (?, ?, ?, ?)''',
            (session.get('user_id'), session.get('username'), subject, message)
        )
        conn.commit()
        conn.close()

        log_action(session.get('user_id'), 'send_admin_message', f'Subject: {subject}')
        return render_template('student_message_admin.html', success="Your message was sent to the admin.")

    return render_template('student_message_admin.html')


@app.route('/student/issue/<int:book_id>', methods=['GET', 'POST'])
@student_required
def student_issue_book(book_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        return_date = request.form.get('return_date', (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')).strip()

        valid, msg = validate_date(return_date)
        if not valid:
            book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
            conn.close()
            return render_template('student_issue_book.html', book=book, error=msg)

        request_block_message = get_student_request_block(
            conn,
            session.get('user_id'),
            session.get('username')
        )
        if request_block_message:
            book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
            conn.close()
            return render_template('student_issue_book.html', book=book, error=request_block_message)
        
        book = conn.execute('SELECT title, author, status FROM books WHERE id = ?', (book_id,)).fetchone()
        
        if not book or book['status'] != 'Available':
            conn.close()
            return redirect(url_for('student_books'))
        
        username = session.get('username')
        request_date = datetime.now().strftime('%Y-%m-%d')
        conn.execute(
            '''UPDATE books SET status = ?, issued_to = ?, issue_date = ?, return_date = ?
               WHERE id = ?''',
            ('Pending Approval', username, None, return_date, book_id)
        )
        conn.execute(
            '''INSERT INTO book_requests
               (book_id, student_id, student_username, request_date, expected_return_date, status)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (book_id, session.get('user_id'), username, request_date, return_date, 'Pending')
        )
        
        conn.commit()
        conn.close()
        
        log_action(session.get('user_id'), 'request_book', f'Book: {book["title"]}')
        return render_template(
            'student_issue_book.html',
            book={'id': book_id, 'title': book['title'], 'author': book['author']},
            success="Your book request was sent to the admin for approval."
        )
    
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    
    if not book or book['status'] != 'Available':
        return redirect(url_for('student_books'))
    
    return render_template('student_issue_book.html', book=book)


@app.route('/student/return/<int:book_id>', methods=['GET', 'POST'])
@student_required
def student_return_book(book_id):
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()

    if not book or book['issued_to'] != session.get('username'):
        conn.close()
        return redirect(url_for('student_dashboard'))
    
    if request.method == 'POST':
        if book and book['issued_to'] == session.get('username') and book['status'] == 'Return Pending':
            conn.close()
            return render_template('student_return_book.html', book=book, success="Your return is already waiting for admin confirmation.")

        active_issue = conn.execute(
            '''SELECT id FROM issue_history
               WHERE book_id = ? AND issued_to = ? AND status = ?
               ORDER BY created_at DESC LIMIT 1''',
            (book_id, session.get('username'), 'Active')
        ).fetchone()

        if book and book['issued_to'] == session.get('username') and active_issue:
            conn.execute(
                '''UPDATE books SET status = ?
                   WHERE id = ?''',
                ('Return Pending', book_id)
            )
            conn.execute(
                '''UPDATE issue_history SET status = ?
                   WHERE id = ?''',
                ('Return Pending', active_issue['id'])
            )
            conn.commit()
            log_action(session.get('user_id'), 'request_return_book', f'Book: {book["title"]}')
        
        conn.close()
        return render_template('student_return_book.html', book=book, success="Your return request was sent to the admin for confirmation.")
    
    conn.close()
    
    return render_template('student_return_book.html', book=book)


# ============= PUBLIC ROUTE (REDIRECT BASED ON ROLE) =============

@app.route('/view-notice/<path:filename>')
@login_required
def view_notice_file(filename):
    # Serve attachments inline (especially PDFs) so browsers open them in a new tab instead of downloading.
    full_path = os.path.join(NOTICE_UPLOAD_FOLDER, filename)
    if not os.path.isfile(full_path):
        return "File not found", 404

    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    resp = send_from_directory(
        NOTICE_UPLOAD_FOLDER,
        filename,
        as_attachment=False
    )

    # For PDFs, explicitly force inline rendering.
    if ext == 'pdf':
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = f'inline; filename="{os.path.basename(filename)}"'
    else:
        # For images, inline is also preferred.
        resp.headers.pop('Content-Disposition', None)

    return resp
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') == 'Admin':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))


# ============= ERROR HANDLERS =============

@app.errorhandler(404)
def not_found(error):
    return redirect(url_for('index')), 404


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    message = "Your form session expired or the security token was missing. Please try again."
    if session.get('user_id'):
        return render_template('base.html', error=message), 400
    return render_template('login.html', error=message), 400


import atexit
import signal

def _server_shutdown_cleanup(*_args, **_kwargs):
    """Best-effort cleanup on process termination.

    We cannot reliably force-logout users on every possible shutdown scenario,
    but invalidating the server restart token handles most restart/quit cases.
    This also clears rate-limit tracking table so old logins don't block.
    """
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM active_sessions')
        conn.commit()
        conn.close()
    except Exception:
        # Never crash shutdown handler.
        pass

if __name__ == '__main__':
    init_db()

    # Clear active_sessions when the process ends (SIGINT/SIGTERM/normal exit).
    atexit.register(_server_shutdown_cleanup)
    try:
        signal.signal(signal.SIGINT, lambda signum, frame: (_server_shutdown_cleanup(), signal.default_int_handler(signum, frame)))
        signal.signal(signal.SIGTERM, lambda signum, frame: (_server_shutdown_cleanup(), signal.default_int_handler(signum, frame)))
    except Exception:
        pass

    app.run(debug=False)

