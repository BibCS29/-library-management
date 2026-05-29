# Library Management System

A simple Flask-based library management system for managing books, issuing, and returning them.

## Features

- ✅ Add new books
- ✅ Issue books to students
- ✅ Return books
- ✅ Delete books
- ✅ View all books with their status

## Quick Start

### Windows
Simply run:
```bash
run.bat
```

### macOS/Linux
Run:
```bash
bash run.sh
```

### Manual Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment:**
   - Windows: `venv\Scripts\activate.bat`
   - macOS/Linux: `source venv/bin/activate`

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Open your browser and go to:**
   ```
   http://localhost:5000
   ```

## Project Structure

```
.
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── run.bat               # Quick start for Windows
├── run.sh                # Quick start for macOS/Linux
├── library.db            # SQLite database (created automatically)
├── static/
│   └── style.css         # Styling
└── templates/
    ├── index.html        # Main page
    ├── add_book.html     # Add book form
    ├── issue_book.html   # Issue book form
    └── return_book.html  # Return book confirmation
```

## Database

The application uses SQLite for data persistence. The database file `library.db` is created automatically when you run the app for the first time.

### Database Schema

```sql
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    status TEXT DEFAULT 'Available',
    issued_to TEXT
)
```

## API Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | View all books |
| `/add` | GET, POST | Add a new book |
| `/issue/<id>` | GET, POST | Issue a book |
| `/return/<id>` | GET | Return a book |
| `/delete/<id>` | GET | Delete a book |

## Development

To run in development mode with auto-reload:

```bash
python app.py
```

The app is set to debug mode by default, which enables:
- Auto-reloading on code changes
- Detailed error pages
- Interactive debugger

## Troubleshooting

**Port 5000 already in use?**
- Modify the port in `app.py`: Change `app.run(debug=True)` to `app.run(debug=True, port=5001)`

**Database errors?**
- Delete `library.db` and restart the app to create a fresh database

**Flask not found?**
- Make sure your virtual environment is activated
- Run `pip install -r requirements.txt` again

## Notes

- Books are stored in SQLite database
- Status can be either "Available" or "Issued"
- When returning a book, the `issued_to` field is cleared
