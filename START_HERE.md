# 🚀 STEP-BY-STEP STARTUP GUIDE

## COMPLETE GUIDE TO START THE LIBRARY MANAGEMENT SYSTEM

---

## ⚠️ IMPORTANT: BEFORE YOU START

Make sure you have:

- ✅ Python installed (version 3.7+)
- ✅ Internet connection (for downloading dependencies)
- ✅ Administrator access (for running setup)
- ✅ All files in the correct folder

---

## 📍 STEP 1: OPEN COMMAND PROMPT

### Windows Users:

**Option A: Using File Explorer (Easiest)**

1. Open File Explorer
2. Navigate to: `C:\Users\dextr\OneDrive\Desktop\LIBRARY MANAGEMENT SYSTEM`
3. Click the address bar at the top
4. Type: `cmd`
5. Press Enter
6. A command prompt window will open in your project folder

**Option B: Using Command Prompt Directly**

1. Press `Win + R`
2. Type: `cmd`
3. Press Enter
4. Copy and paste this command:
   ```
   cd "C:\Users\dextr\OneDrive\Desktop\LIBRARY MANAGEMENT SYSTEM"
   ```
5. Press Enter

---

## 📍 STEP 2: RUN THE SETUP SCRIPT

In the command prompt, type:

```bash
setup.bat
```

Press Enter.

### What this does:

- ✅ Removes old app.py file
- ✅ Renames app_final.py to app.py (the new secure version)
- ✅ Installs all required Python packages (Flask, Flask-Session, etc.)
- ✅ Shows progress as it installs

### Expected Output:

```
Replacing app.py with secure version...
Done!

Installing dependencies...
Collecting Flask==3.0.0
Collecting Werkzeug==3.0.1
Collecting Flask-Session==0.5.0
...
Successfully installed all packages!

Setup complete! Ready to run.
```

⏱️ **Wait Time**: 2-5 minutes (depends on internet speed)

---

## 📍 STEP 3: VERIFY SECURITY (OPTIONAL BUT RECOMMENDED)

After setup completes, verify everything is correct:

```bash
python verify_security.py
```

Press Enter.

### Expected Output:

```
============================================================
SECURITY VERIFICATION CHECKLIST
============================================================

✅ Main application: app.py
✅ Environment configuration: .env
✅ Dependencies: requirements.txt
✅ Database: library.db
✅ Template: templates/base.html
✅ Template: templates/login.html
... (more files)

============================================================
✅ ALL SECURITY CHECKS PASSED!
🚀 Application is ready to run

Start with: python app.py
```

If you see ❌ errors, go back to STEP 2 and run setup.bat again.

---

## 📍 STEP 4: CONFIGURE SECRETS (.env FILE)

### What is .env?

The `.env` file contains secret information that should NOT be shared:

- SECRET_KEY (encryption key)
- Database settings
- Rate limiting configuration

### Edit .env File:

**Method 1: Using Notepad (Easiest)**

1. In File Explorer, go to your project folder
2. Right-click on `.env` file
3. Click "Open with"
4. Select "Notepad"

**Method 2: Using Command Prompt**

```bash
notepad .env
```

### What to Change:

Find this line:

```
SECRET_KEY=your-super-secret-key-change-this-in-production-12345678901234567890
```

Replace it with a random secret (at least 32 characters):

```
SECRET_KEY=aB3d9Kx7mP2nQ5vR8tY1wZ4cH6jF9sL0dE5mN3tY7bU2kP9qW6sX8vA1cD4fE
```

### Example of Updated .env:

```
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=aB3d9Kx7mP2nQ5vR8tY1wZ4cH6jF9sL0dE5mN3tY7bU2kP9qW6sX8vA1cD4fE
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
MAX_CONCURRENT_USERS=5
MAX_ADMIN_USERS=2
MAX_STUDENT_USERS=3
```

✅ Save the file (Ctrl + S)

---

## 📍 STEP 5: START THE SERVER

In the command prompt (if closed, repeat STEP 1), type:

```bash
python app.py
```

Press Enter.

### Expected Output:

```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in production code directly.
Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

✅ **Server is now RUNNING!**

---

## 📍 STEP 6: OPEN IN WEB BROWSER

### Method 1: Click the Link (Easiest)

- Hold Ctrl and click on: `http://127.0.0.1:5000`
- It will open in your default browser

### Method 2: Manual Entry

1. Open any web browser (Chrome, Firefox, Edge, etc.)
2. In the address bar, type:
   ```
   http://localhost:5000
   ```
3. Press Enter

### Expected Screen:

You should see the **Login Page** with:

- Username field
- Password field
- "Don't have an account? Register here" link

🎉 **Congratulations! The server is running!**

---

## 📍 STEP 7: REGISTER ADMIN ACCOUNT

### First, Create an Admin Account:

Click on "Register here" link.

Fill in the form:

```
Username:     admin123
Email:        admin@example.com
Password:     Admin@123456
Role:         Admin (select from dropdown)
```

Click "Register" button.

### Result:

✅ You'll be redirected to login page
✅ Account created successfully

---

## 📍 STEP 8: LOGIN AS ADMIN

### Fill in the login form:

```
Username:     admin123
Password:     Admin@123456
```

Click "Login" button.

### Result:

✅ You'll see the **Admin Dashboard**
✅ Shows: Total Books, Registered Users, Active Issues

---

## 📍 STEP 9: TEST ADMIN FEATURES

### From Admin Dashboard, you can:

**1. Manage Books:**

- Click "Books" in top menu
- Click "Add New Book"
- Fill in: Title and Author
- Click "Add Book"
- Book appears in the list

**2. Manage Users:**

- Click "Users" in top menu
- See all registered users
- Delete users if needed

**3. View Audit Logs:**

- Click "Logs" in top menu
- See all system activities with timestamps

---

## 📍 STEP 10: REGISTER & TEST STUDENT ACCOUNT

### Go back and create a Student Account:

1. Click "Logout" in top right
2. Click "Register here"
3. Fill in:
   ```
   Username:     student1
   Email:        student@example.com
   Password:     Student@123456
   Role:         Student (select from dropdown)
   ```
4. Click "Register"

---

## 📍 STEP 11: LOGIN AS STUDENT

```
Username:     student1
Password:     Student@123456
```

Click "Login"

### Student Dashboard shows:

- Available Books
- Books Issued to You
- Your Activity History

---

## 📍 STEP 12: TEST STUDENT FEATURES

### From Student Dashboard:

**1. Browse Books:**

- Click "Browse Books" button
- See all available books
- Click "Issue This Book"
- Select dates and confirm

**2. Return Books:**

- From dashboard, click Return button
- Confirm return
- Book becomes available again

**3. View History:**

- Dashboard shows all your activity
- Issued books, return dates, status

---

## 📍 STEP 13: TEST RATE LIMITING

### Verify 5-User Limit Works:

**Open 3 browser tabs/windows:**

**Tab 1:** Login as Admin1

```
Username: admin_a
Password: Admin@123456
Role: Admin
```

**Tab 2:** Login as Admin2

```
Username: admin_b
Password: Admin@123456
Role: Admin
```

**Tab 3:** Try to login as Admin3

```
Username: admin_c
Password: Admin@123456
Role: Admin
```

### Result:

✅ Admin3 gets error: "Maximum 2 admins logged in"
✅ Rate limiting is WORKING!

---

## 📍 STEP 14: TEST SQL INJECTION PROTECTION

Try these in input fields:

**In Username field:**

```
' OR '1'='1
```

**Result:**
❌ Rejected with message: "Invalid format"
✅ SQL Injection prevented!

**In Book Title:**

```
'; DROP TABLE books; --
```

**Result:**
✅ Safely stored as text
✅ Database remains intact
✅ Protected!

---

## 🛑 HOW TO STOP THE SERVER

In the command prompt window where it's running:

Press: `Ctrl + C`

### You should see:

```
^C
Shutting down
Server stopped
```

---

## 🔄 HOW TO RESTART THE SERVER

1. Press `Ctrl + C` to stop (if running)
2. Type: `python app.py`
3. Press Enter

---

## ⚠️ COMMON ISSUES & SOLUTIONS

### Issue 1: "Port 5000 already in use"

**Solution:**

```bash
# This command kills the process
taskkill /IM python.exe /F
```

Then try again: `python app.py`

### Issue 2: "ModuleNotFoundError: No module named 'flask'"

**Solution:**
Run setup again:

```bash
setup.bat
```

### Issue 3: ".env file not found"

**Solution:**

1. Make sure you're in the correct folder
2. The .env file should be created automatically
3. Check if file is hidden:
   - In File Explorer: View → Hidden items (check the box)

### Issue 4: "Cannot connect to http://localhost:5000"

**Solution:**

1. Make sure server is running (see output in command prompt)
2. Try different browser
3. Try: `http://127.0.0.1:5000` instead
4. Check if firewall is blocking

### Issue 5: "Database is locked"

**Solution:**

```bash
# Delete the session folder
rmdir /s flask_session

# Restart server
python app.py
```

---

## ✅ CHECKLIST - YOU'RE DONE IF:

- [x] setup.bat ran successfully
- [x] verify_security.py showed all checks passed
- [x] .env file was edited with SECRET_KEY
- [x] Server started with `python app.py`
- [x] Browser opened to localhost:5000
- [x] Login page loaded
- [x] Admin account created and logged in
- [x] Student account created and logged in
- [x] Could add books in admin panel
- [x] Could browse and issue books in student panel
- [x] Rate limiting test passed
- [x] SQL injection test passed

🎉 **CONGRATULATIONS! System is fully operational and secure!**

---

## 📞 QUICK COMMAND REFERENCE

```bash
# Setup
setup.bat

# Verify security
python verify_security.py

# Start server
python app.py

# Stop server
Ctrl + C

# Edit .env file
notepad .env

# Check if Python is installed
python --version

# Check if all packages installed
pip list
```

---

## 🌐 ACCESSING FROM OTHER COMPUTERS

If you want to access from another computer on the same network:

1. Find your computer's IP:

   ```bash
   ipconfig
   ```

   Look for "IPv4 Address" (example: 192.168.1.100)

2. From other computer, open:
   ```
   http://192.168.1.100:5000
   ```

**Note:** Only works if on same network!

---

## 📖 NEXT RESOURCES

- `SECURITY.md` - All security features explained
- `QUICKSTART.md` - Detailed feature walkthrough
- `IMPLEMENTATION_SUMMARY.md` - Technical overview
- `NEXT_STEPS.md` - Production deployment

---

**Version**: 2.0 (Secure)
**Last Updated**: 2024

**You're all set! Enjoy your secure Library Management System! 🎉**
