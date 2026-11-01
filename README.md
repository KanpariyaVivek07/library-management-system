# 📚 Library Management System

A complete library management web application built with **Python + Flask**. It handles books, members, transactions, fines, reports and staff roles from a single dashboard.

## ✨ Features

- **Book management** — add, edit, delete books with cover images and QR code labels
- **Member management** — registration, profiles, membership status
- **Issue / return** — due dates, automatic fine calculation (₹5 per day)
- **Fine payments** — receipt generation and payment history
- **Role-based access** — Admin and Librarian roles
- **Dashboard & charts** — live statistics and visual reports
- **Audit log** — every important action is recorded
- **CSV export** — download transaction data
- **Email templates** — ready-to-use notification templates
- **Multi-language UI**
- **Secure auth** — bcrypt password hashing, CSRF protection, HTTP-only session cookies

A command-line version of the same system is included as `library_management.py`.

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3, Flask |
| Templates | Jinja2 (21 templates) |
| Auth | bcrypt, Flask-WTF (CSRF) |
| Extras | qrcode, CSV export |
| Storage | JSON files (`books.json`, `members.json`, `transactions.json`) |

## 🚀 Getting Started

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Open **http://127.0.0.1:5000**

Librarian accounts and their bcrypt password hashes are stored in `librarians.json`.
Change the seeded accounts before using the app for anything real.

## 📁 Project Structure

```
404_PYTOHN/
├── app.py                 # Flask application
├── library_management.py  # CLI version
├── templates/             # 21 Jinja2 templates
├── static/                # CSS, JS, covers, QR codes
├── backups/               # JSON backups
├── books.json             # Book records
├── members.json           # Member records
├── transactions.json      # Issue/return records
├── librarians.json        # Staff accounts (hashed passwords)
└── requirements.txt
```

## ⚙️ Configuration

Set a fixed secret key in production instead of the random per-start key:

```bash
set SECRET_KEY=your-strong-secret
```

Uploads are limited to 2 MB (image files only).

## 📌 Notes

- This project was built as a Semester 4 (404) Python project.
- Data is stored in JSON files, so there is no database setup required.
