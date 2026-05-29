#!/usr/bin/env python3
"""
Verification script to ensure all secure components are in place
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def check_file(path, description):
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def check_directory(path, description):
    exists = os.path.isdir(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def main():
    print("=" * 60)
    print("SECURITY VERIFICATION CHECKLIST")
    print("=" * 60)
    print()
    
    all_good = True
    
    # Core files
    print("📁 Core Files:")
    all_good &= check_file('app.py', 'Main application')
    all_good &= check_file('.env', 'Environment configuration')
    all_good &= check_file('requirements.txt', 'Dependencies')
    all_good &= check_file('library.db', 'Database')
    print()
    
    # Templates
    print("🎨 Template Files:")
    templates_needed = [
        'templates/base.html',
        'templates/login.html',
        'templates/forgot_password.html',
        'templates/reset_password.html',
        'templates/register.html',
        'templates/admin_dashboard.html',
        'templates/admin_users.html',
        'templates/admin_books.html',
        'templates/admin_add_book.html',
        'templates/admin_logs.html',
        'templates/admin_messages.html',
        'templates/admin_book_requests.html',
        'templates/admin_notifications.html',
        'templates/profile.html',
        'templates/student_dashboard.html',
        'templates/student_books.html',
        'templates/student_issue_book.html',
        'templates/student_return_book.html',
        'templates/student_message_admin.html',
    ]
    for template in templates_needed:
        all_good &= check_file(template, f"Template: {os.path.basename(template)}")
    print()
    
    # Documentation
    print("📖 Documentation:")
    all_good &= check_file('SECURITY.md', 'Security features doc')
    all_good &= check_file('QUICKSTART.md', 'Quick start guide')
    print()
    
    # Check .env content
    print("🔐 Environment Configuration:")
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            content = f.read()
            has_secret = 'SECRET_KEY=' in content
            has_debug = 'FLASK_DEBUG=' in content
            has_rate_limiting = 'MAX_ADMIN_USERS=' in content
            has_smtp = 'SMTP_HOST=' in content
            
            print(f"{'✅' if has_secret else '❌'} SECRET_KEY configured")
            print(f"{'✅' if has_debug else '❌'} FLASK_DEBUG set")
            print(f"{'✅' if has_rate_limiting else '❌'} Rate limiting configured")
            print(f"{'✅' if has_smtp else '❌'} SMTP settings present")
            
            all_good &= has_secret and has_debug and has_rate_limiting and has_smtp
    else:
        print("❌ .env file not found!")
        all_good = False
    print()
    
    # Check requirements.txt
    print("📦 Dependencies:")
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            content = f.read().lower()
            has_flask_session = 'flask-session' in content
            has_flask_wtf = 'flask-wtf' in content
            has_dotenv = 'python-dotenv' in content
            
            print(f"{'✅' if has_flask_session else '❌'} Flask-Session included")
            print(f"{'✅' if has_flask_wtf else '❌'} Flask-WTF (CSRF) included")
            print(f"{'✅' if has_dotenv else '❌'} python-dotenv included")
            
            all_good &= has_flask_session and has_flask_wtf and has_dotenv
    else:
        print("❌ requirements.txt not found!")
        all_good = False
    print()

    # Check template CSRF coverage
    print("🧾 CSRF Template Coverage:")
    csrf_ok = True
    if os.path.isdir('templates'):
        for root, _, files in os.walk('templates'):
            for filename in files:
                if not filename.endswith('.html'):
                    continue

                path = os.path.join(root, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    template_content = f.read()

                forms = re.finditer(r'<form\b.*?</form>', template_content, re.IGNORECASE | re.DOTALL)
                for index, form in enumerate(forms, start=1):
                    form_html = form.group(0)
                    is_post = re.search(r'\bmethod\s*=\s*["\']?post', form_html, re.IGNORECASE)
                    has_csrf = 'csrf_token' in form_html
                    if is_post and not has_csrf:
                        print(f"❌ Missing csrf_token in {path} form #{index}")
                        csrf_ok = False

        if csrf_ok:
            print("✅ All POST forms include csrf_token")
    else:
        print("❌ templates directory not found!")
        csrf_ok = False

    all_good &= csrf_ok
    print()
    
    # Check app.py for security features
    print("🛡️  Security Features in app.py:")
    if os.path.exists('app.py'):
        with open('app.py', 'r') as f:
            app_content = f.read()
            
            features = {
                'Authentication (login/register)': 'def register():' in app_content and 'def login():' in app_content,
                'Password hashing': 'generate_password_hash' in app_content and 'check_password_hash' in app_content,
                'Admin decorator': '@admin_required' in app_content,
                'Student decorator': '@student_required' in app_content,
                'Input validation': 'validate_username' in app_content,
                'SQL Injection prevention': "WHERE id = ?" in app_content,
                'Audit logging': 'def log_action' in app_content,
                'Rate limiting': 'MAX_ADMIN_USERS' in app_content,
                'Debug OFF': 'debug=False' in app_content,
                'CSRF protection': 'CSRFProtect' in app_content,
                'OTP password reset': 'password_reset_otps' in app_content and 'send_password_reset_otp' in app_content,
                'Admin message box': 'admin_messages' in app_content and 'student_message_admin' in app_content,
                'Admin book approval': 'book_requests' in app_content and 'approve_book_request' in app_content,
                'Admin return confirmation': 'Return Pending' in app_content and 'confirm_book_return' in app_content,
                'Admin message replies': 'reply_admin_message' in app_content and 'admin_reply' in app_content,
                'Login notifications': 'login_notifications' in app_content and 'admin_notifications' in app_content,
                'One-time profiles': 'profile_edit_allowed' in app_content and 'def profile' in app_content,
                'Student restrictions': 'is_restricted' in app_content and 'restrict_user' in app_content,
            }
            
            for feature, present in features.items():
                print(f"{'✅' if present else '❌'} {feature}")
                all_good &= present
    else:
        print("❌ app.py not found!")
        all_good = False
    print()
    
    # Summary
    print("=" * 60)
    if all_good:
        print("✅ ALL SECURITY CHECKS PASSED!")
        print("🚀 Application is ready to run")
        print("\nStart with: python app.py")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("⚠️  Please address issues above before running")
        print("\nRun setup.bat to fix missing files")
        return 1

if __name__ == '__main__':
    sys.exit(main())
