import json
import datetime
import random
import os
import hashlib
import csv
import secrets
import string
import io
import base64
from collections import Counter
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from flask_wtf.csrf import generate_csrf
import bcrypt
import qrcode

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=2)
app.config['WTF_CSRF_ENABLED'] = True
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'covers')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


@app.context_processor
def inject_csrf():
    return dict(csrf_token=generate_csrf)


@app.context_processor
def inject_translations():
    lang = session.get('lang', 'en')
    return dict(t=TRANSLATIONS.get(lang, TRANSLATIONS['en']), lang=lang)


FINE_PER_DAY = 5
MAX_BORROW_LIMIT = 5
DUE_DAYS = 14
LOW_STOCK_THRESHOLD = 3
CATEGORIES = ["Fiction", "Science", "Programming", "Mathematics", "History", "Literature", "Other"]
CONDITIONS = ["New", "Good", "Worn", "Damaged", "Lost"]


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


BOOK_FILE = 'books.json'
MEMBER_FILE = 'members.json'
TRANSACTION_FILE = 'transactions.json'
RESERVATION_FILE = 'reservations.json'
AUDIT_FILE = 'audit_log.json'
LIBRARIAN_FILE = 'librarians.json'


def bcrypt_hash(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def bcrypt_check(pw, hashed):
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def hash_password(pw):
    return bcrypt_hash(pw)


def check_password(pw, hashed):
    if len(hashed) == 64:
        return hashed == hashlib.sha256(pw.encode()).hexdigest()
    return bcrypt_check(pw, hashed)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session and 'librarian' not in session:
            flash('Please login first.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def librarian_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'librarian' not in session:
            flash('Librarian access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def load_books():
    if os.path.exists(BOOK_FILE):
        with open(BOOK_FILE, 'r') as f:
            books = json.load(f)
            for t, d in books.items():
                d.setdefault('category', 'Other')
                d.setdefault('condition', 'New')
                d.setdefault('total_copies', d['available_copies'])
                d.setdefault('added_date', 'N/A')
                d.setdefault('isbn', '')
                d.setdefault('cover', '')
            return books
    return {}


def save_books(books):
    with open(BOOK_FILE, 'w') as f:
        json.dump(books, f, indent=4)


def load_members():
    members = {}
    if os.path.exists(MEMBER_FILE):
        with open(MEMBER_FILE, 'r') as f:
            data = json.load(f)
            changed = False
            for name, d in data.items():
                pw = d['password']
                if len(pw) != 64 and not pw.startswith('$2'):
                    pw = bcrypt_hash(pw)
                    d['password'] = pw
                    changed = True
                m = {'name': name, 'member_id': d['member_id'], 'password': pw,
                     'borrowed_books': d.get('borrowed_books', []),
                     'fine_due': d.get('fine_due', 0), 'history': d.get('history', [])}
                for b in m['borrowed_books']:
                    if not isinstance(b, dict):
                        idx = m['borrowed_books'].index(b)
                        m['borrowed_books'][idx] = {'title': b, 'due_date': None, 'issue_date': None}
                members[name] = m
            if changed:
                save_members(members)
    return members


def save_members(members):
    with open(MEMBER_FILE, 'w') as f:
        json.dump({name: {
            'member_id': m['member_id'], 'password': m['password'],
            'borrowed_books': m['borrowed_books'], 'fine_due': m['fine_due'],
            'history': m['history']
        } for name, m in members.items()}, f, indent=4)


def load_librarians():
    if os.path.exists(LIBRARIAN_FILE):
        with open(LIBRARIAN_FILE, 'r') as f:
            return json.load(f)
    default = {
        'alice': {'password': bcrypt_hash('alice123'), 'name': 'Alice', 'role': 'admin'},
        'bob': {'password': bcrypt_hash('bob123'), 'name': 'Bob', 'role': 'librarian'}
    }
    save_librarians(default)
    return default


def save_librarians(librarians):
    with open(LIBRARIAN_FILE, 'w') as f:
        json.dump(librarians, f, indent=4)


def load_transactions():
    if os.path.exists(TRANSACTION_FILE):
        with open(TRANSACTION_FILE, 'r') as f:
            return json.load(f)
    return []


def save_transactions(txns):
    with open(TRANSACTION_FILE, 'w') as f:
        json.dump(txns, f, indent=4)


def load_reservations():
    if os.path.exists(RESERVATION_FILE):
        with open(RESERVATION_FILE, 'r') as f:
            return json.load(f)
    return []


def save_reservations(res):
    with open(RESERVATION_FILE, 'w') as f:
        json.dump(res, f, indent=4)


def load_audit():
    if os.path.exists(AUDIT_FILE):
        with open(AUDIT_FILE, 'r') as f:
            return json.load(f)
    return []


def save_audit(logs):
    with open(AUDIT_FILE, 'w') as f:
        json.dump(logs, f, indent=4)


def log_action(user, action, details=''):
    logs = load_audit()
    logs.append({
        'user': user, 'action': action, 'details': details,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    if len(logs) > 1000:
        logs = logs[-1000:]
    save_audit(logs)


@app.route('/lang/<lang_code>')
def set_language(lang_code):
    if lang_code in TRANSLATIONS:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('index'))


@app.before_request
def before_request():
    session.permanent = True


@app.route('/')
def index():
    books = load_books()
    members = load_members()
    txns = load_transactions()
    total_copies = sum(d.get('total_copies', d['available_copies']) for d in books.values())
    available_copies = sum(d['available_copies'] for d in books.values())
    return render_template('index.html',
        total_unique_books=len(books),
        total_copies=total_copies,
        total_members=len(members), total_transactions=len(txns),
        available_copies=available_copies)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_type = request.form['login_type']
        name = request.form['name'].strip().title()
        password = request.form['password']

        if login_type == 'member':
            members = load_members()
            if name in members and check_password(password, members[name]['password']):
                session['user'] = name
                log_action(name, 'Member Login')
                flash(f'Welcome back, {name}!', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid credentials.', 'danger')
        else:
            librarians = load_librarians()
            name_lower = name.lower()
            if name_lower in librarians and check_password(password, librarians[name_lower]['password']):
                session['librarian'] = name_lower
                log_action(name_lower, 'Librarian Login')
                flash(f'Welcome, Librarian {name}!', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip().title()
        password = request.form['password']
        confirm = request.form['confirm']
        if len(password) < 4:
            flash('Password must be at least 4 characters.', 'danger')
            return redirect(url_for('register'))
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        members = load_members()
        if name in members:
            flash('Name already registered.', 'warning')
            return redirect(url_for('login'))
        member_id = random.randint(1000, 9999)
        members[name] = {
            'name': name, 'member_id': member_id, 'password': bcrypt_hash(password),
            'borrowed_books': [], 'fine_due': 0, 'history': []
        }
        save_members(members)
        log_action(name, 'Registered', f'ID: {member_id}')
        flash(f'Registration successful! Your ID: {member_id}', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    user = session.get('user') or session.get('librarian', 'Unknown')
    log_action(user, 'Logout')
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    books = load_books()
    members = load_members()
    txns = load_transactions()
    low = [(t, d['available_copies']) for t, d in books.items() if 0 < d['available_copies'] <= LOW_STOCK_THRESHOLD]
    out = [t for t, d in books.items() if d['available_copies'] == 0]
    total_fine = sum(t.get('fine', 0) for t in txns)
    total_unique_books = len(books)
    total_copies = sum(d.get('total_copies', d['available_copies']) for d in books.values())
    available_copies = sum(d['available_copies'] for d in books.values())
    issued_copies = total_copies - available_copies
    return render_template('dashboard.html',
        total_unique_books=total_unique_books,
        total_copies=total_copies,
        available_copies=available_copies,
        issued_copies=issued_copies,
        total_members=len(members), total_transactions=len(txns),
        total_fine=total_fine, low_stock=low, out_of_stock=out,
        recent_transactions=list(reversed(txns)))


@app.route('/books')
def books():
    books = load_books()
    search = request.args.get('search', '').strip().title()
    cat_filter = request.args.get('category', '')
    condition_filter = request.args.get('condition', '')
    stock_filter = request.args.get('stock', '')
    sort_by = request.args.get('sort', 'name')
    if search:
        books = {k: v for k, v in books.items() if search in k or search in v['author'] or search in v.get('isbn', '')}
    if cat_filter:
        books = {k: v for k, v in books.items() if v.get('category') == cat_filter}
    if condition_filter:
        books = {k: v for k, v in books.items() if v.get('condition') == condition_filter}
    if stock_filter == 'available':
        books = {k: v for k, v in books.items() if v['available_copies'] > LOW_STOCK_THRESHOLD}
    elif stock_filter == 'low':
        books = {k: v for k, v in books.items() if 0 < v['available_copies'] <= LOW_STOCK_THRESHOLD}
    elif stock_filter == 'out':
        books = {k: v for k, v in books.items() if v['available_copies'] == 0}
    if sort_by == 'price_low':
        books = dict(sorted(books.items(), key=lambda x: x[1]['price']))
    elif sort_by == 'price_high':
        books = dict(sorted(books.items(), key=lambda x: x[1]['price'], reverse=True))
    elif sort_by == 'stock':
        books = dict(sorted(books.items(), key=lambda x: x[1]['available_copies'], reverse=True))
    elif sort_by == 'newest':
        books = dict(sorted(books.items(), key=lambda x: x[1].get('date_added', ''), reverse=True))
    return render_template('books.html', books=books, categories=CATEGORIES, conditions=CONDITIONS,
        search_query=search, cat_filter=cat_filter, condition_filter=condition_filter,
        stock_filter=stock_filter, sort_by=sort_by,
        total_books=len(books), total_copies=sum(d.get('total_copies', d['available_copies']) for d in books.values()),
        available_copies=sum(d['available_copies'] for d in books.values()))


@app.route('/issue/<title>', methods=['POST'])
@login_required
def issue_book(title):
    members = load_members()
    books = load_books()
    user = session['user']
    if len(members[user]['borrowed_books']) >= MAX_BORROW_LIMIT:
        flash('Borrow limit reached! Max 5 books.', 'danger')
        return redirect(url_for('books'))
    if title not in books:
        flash('Book not found.', 'danger')
        return redirect(url_for('books'))
    if books[title]['available_copies'] <= 0:
        reservations = load_reservations()
        reservations.append({'member': user, 'book': title, 'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
        save_reservations(reservations)
        flash('No copies available. Book reserved for you.', 'warning')
        return redirect(url_for('books'))
    issue_date = datetime.datetime.now()
    due_date = issue_date + datetime.timedelta(days=DUE_DAYS)
    books[title]['available_copies'] -= 1
    members[user]['borrowed_books'].append({
        'title': title, 'issue_date': issue_date.strftime("%Y-%m-%d %H:%M"),
        'due_date': due_date.strftime("%Y-%m-%d %H:%M")})
    txns = load_transactions()
    txns.append({'member': user, 'book': title, 'type': 'Issue',
        'date': issue_date.strftime("%Y-%m-%d %H:%M"),
        'due_date': due_date.strftime("%Y-%m-%d %H:%M")})
    save_books(books)
    save_members(members)
    save_transactions(txns)
    log_action(user, 'Book Issued', f'Book: {title}, Due: {due_date.strftime("%Y-%m-%d")}')
    flash(f'Book "{title}" issued! Due: {due_date.strftime("%Y-%m-%d")}', 'success')
    return redirect(url_for('member_profile', name=user))


@app.route('/return/<title>', methods=['POST'])
@login_required
def return_book(title):
    members = load_members()
    books = load_books()
    user = session['user']
    borrowed = None
    for b in members[user]['borrowed_books']:
        if isinstance(b, dict) and b.get('title') == title:
            borrowed = b
            break
    if not borrowed:
        flash(f'You have not borrowed "{title}".', 'danger')
        return redirect(url_for('member_profile', name=user))
    members[user]['borrowed_books'].remove(borrowed)
    books[title]['available_copies'] += 1
    fine = 0
    if borrowed.get('due_date'):
        due = datetime.datetime.strptime(borrowed['due_date'], "%Y-%m-%d %H:%M")
        if datetime.datetime.now() > due:
            days_late = (datetime.datetime.now() - due).days
            fine = days_late * FINE_PER_DAY
            members[user]['fine_due'] += fine
    members[user]['history'].append({
        'title': title, 'action': 'Return',
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'fine': fine})
    txns = load_transactions()
    txns.append({'member': user, 'book': title, 'type': 'Return',
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'fine': fine})
    save_books(books)
    save_members(members)
    save_transactions(txns)
    log_action(user, 'Book Returned', f'Book: {title}, Fine: ${fine:.2f}')
    if fine > 0:
        flash(f'Book returned {days_late} day(s) late. Fine: ${fine:.2f}', 'warning')
    else:
        flash('Book returned on time!', 'success')
    return redirect(url_for('member_profile', name=user))


@app.route('/purchase/<title>', methods=['POST'])
@login_required
def purchase_book(title):
    members = load_members()
    books = load_books()
    user = session['user']
    if title not in books or books[title]['available_copies'] <= 0:
        flash('Book not available.', 'danger')
        return redirect(url_for('books'))
    price = books[title]['price']
    books[title]['available_copies'] -= 1
    members[user]['history'].append({
        'title': title, 'action': 'Purchase',
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'fine': 0})
    txns = load_transactions()
    txns.append({'member': user, 'book': title, 'type': 'Purchase',
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'price': price})
    save_books(books)
    save_members(members)
    save_transactions(txns)
    log_action(user, 'Book Purchased', f'Book: {title}, Price: ${price:.2f}')
    flash(f'Book "{title}" purchased for ${price:.2f}!', 'success')
    return redirect(url_for('receipt', txn_idx=len(txns)-1))


@app.route('/reserve/<title>', methods=['POST'])
@login_required
def reserve_book(title):
    reservations = load_reservations()
    reservations.append({'member': session['user'], 'book': title,
        'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
    save_reservations(reservations)
    log_action(session['user'], 'Book Reserved', f'Book: {title}')
    flash(f'Book "{title}" reserved.', 'info')
    return redirect(url_for('books'))


@app.route('/receipt/<int:txn_idx>')
@login_required
def receipt(txn_idx):
    txns = load_transactions()
    if txn_idx >= len(txns):
        flash('Transaction not found.', 'danger')
        return redirect(url_for('dashboard'))
    t = txns[txn_idx]
    return render_template('receipt.html', txn=t, idx=txn_idx)


@app.route('/member/<name>')
@login_required
def member_profile(name):
    if session.get('user') != name and 'librarian' not in session:
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    members = load_members()
    txns = load_transactions()
    now = datetime.datetime.now()
    member = members.get(name)
    if not member:
        flash('Member not found.', 'danger')
        return redirect(url_for('dashboard'))
    for b in member['borrowed_books']:
        if b.get('due_date'):
            due = datetime.datetime.strptime(b['due_date'], "%Y-%m-%d %H:%M")
            b['overdue'] = now > due
        else:
            b['overdue'] = False
    return render_template('member_profile.html', member=member, transactions=txns)


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        members = load_members()
        user = session.get('user')
        current = request.form['current']
        new_pw = request.form['new_password']
        confirm = request.form['confirm']
        if not check_password(current, members[user]['password']):
            flash('Incorrect current password.', 'danger')
        elif len(new_pw) < 4:
            flash('Password must be at least 4 characters.', 'danger')
        elif new_pw != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            members[user]['password'] = bcrypt_hash(new_pw)
            save_members(members)
            log_action(user, 'Password Changed')
            flash('Password changed successfully!', 'success')
            return redirect(url_for('member_profile', name=user))
    return render_template('change_password.html')


@app.route('/pay-fine', methods=['GET', 'POST'])
@login_required
def pay_fine():
    members = load_members()
    user = session.get('user')
    fine_due = members[user]['fine_due']
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
        except (ValueError, KeyError):
            flash('Invalid amount.', 'danger')
            return redirect(url_for('pay_fine'))
        if amount <= 0:
            flash('Amount must be positive.', 'danger')
        elif amount >= fine_due:
            members[user]['fine_due'] = 0
            save_members(members)
            log_action(user, 'Fine Paid', f'Amount: ${fine_due:.2f}')
            flash('Fine paid in full!', 'success')
            return redirect(url_for('member_profile', name=user))
        else:
            members[user]['fine_due'] -= amount
            save_members(members)
            log_action(user, 'Fine Paid', f'Amount: ${amount:.2f}')
            flash(f'Paid ${amount:.2f}. Remaining: ${members[user]["fine_due"]:.2f}', 'info')
    return render_template('pay_fine.html', fine_due=fine_due)


@app.route('/transactions')
@login_required
def transactions():
    txns = load_transactions()
    type_filter = request.args.get('type', '')
    member_filter = request.args.get('member', '').strip().title()
    page = int(request.args.get('page', 1))
    per_page = 20
    if type_filter:
        txns = [t for t in txns if t['type'] == type_filter]
    if member_filter:
        txns = [t for t in txns if t['member'] == member_filter]
    total = len(txns)
    total_pages = max(1, (total + per_page - 1) // per_page)
    txns_page = txns[(page-1)*per_page : page*per_page]
    return render_template('transactions.html', transactions=list(reversed(txns_page)),
        type_filter=type_filter, member_filter=member_filter,
        page=page, total_pages=total_pages, total=total)


@app.route('/librarian')
@librarian_required
def librarian():
    books = load_books()
    members = load_members()
    txns = load_transactions()
    popular = Counter(t['book'] for t in txns if t['type'] == 'Issue').most_common(5)
    active = [(m, sum(1 for t in txns if t['member'] == m), len(d['borrowed_books'])) for m, d in members.items()]
    active.sort(key=lambda x: x[1], reverse=True)
    revenue = sum(t.get('price', 0) for t in txns if t['type'] == 'Purchase')
    return render_template('librarian.html',
        total_books=sum(d.get('total_copies', d['available_copies']) for d in books.values()),
        total_members=len(members), total_transactions=len(txns),
        total_revenue=revenue, popular_books=popular, active_members=active[:10])


@app.route('/librarian/add-book', methods=['GET', 'POST'])
@librarian_required
def add_book():
    if request.method == 'POST':
        books = load_books()
        title = request.form['title'].strip().title()
        if title in books:
            flash(f'"{title}" already exists.', 'warning')
            return redirect(url_for('books'))
        cover_url = request.form.get('cover', '').strip()
        if 'cover_file' in request.files:
            file = request.files['cover_file']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{title.replace(' ', '_')}_{secrets.token_hex(4)}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cover_url = f"/static/covers/{filename}"
        books[title] = {
            'author': request.form['author'].strip().title(),
            'price': float(request.form['price']),
            'available_copies': int(request.form['copies']),
            'total_copies': int(request.form['copies']),
            'category': request.form['category'],
            'condition': request.form['condition'],
            'isbn': request.form.get('isbn', '').strip(),
            'cover': cover_url,
            'added_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
        save_books(books)
        log_action(session['librarian'], 'Book Added', title)
        flash(f'Book "{title}" added!', 'success')
        return redirect(url_for('books'))
    return render_template('add_book.html', categories=CATEGORIES, conditions=CONDITIONS)


@app.route('/librarian/edit-book/<title>', methods=['GET', 'POST'])
@librarian_required
def edit_book(title):
    books = load_books()
    if title not in books:
        flash('Book not found.', 'danger')
        return redirect(url_for('books'))
    if request.method == 'POST':
        books[title]['author'] = request.form['author'].strip().title()
        books[title]['price'] = float(request.form['price'])
        books[title]['available_copies'] = int(request.form['copies'])
        books[title]['total_copies'] = int(request.form['total_copies'])
        books[title]['category'] = request.form['category']
        books[title]['condition'] = request.form['condition']
        books[title]['isbn'] = request.form.get('isbn', '').strip()
        cover_url = request.form.get('cover', '').strip()
        if 'cover_file' in request.files:
            file = request.files['cover_file']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{title.replace(' ', '_')}_{secrets.token_hex(4)}.{ext}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cover_url = f"/static/covers/{filename}"
        books[title]['cover'] = cover_url
        save_books(books)
        log_action(session['librarian'], 'Book Updated', title)
        flash(f'Book "{title}" updated!', 'success')
        return redirect(url_for('books'))
    return render_template('edit_book.html', title=title, book=books[title],
        categories=CATEGORIES, conditions=CONDITIONS)


@app.route('/librarian/delete-book/<title>', methods=['POST'])
@librarian_required
def delete_book(title):
    books = load_books()
    if title in books:
        del books[title]
        save_books(books)
        log_action(session['librarian'], 'Book Deleted', title)
        flash(f'Book "{title}" deleted.', 'success')
    return redirect(url_for('books'))


@app.route('/librarian/members')
@librarian_required
def manage_members():
    return render_template('members.html', members=load_members())


@app.route('/librarian/delete-member/<name>', methods=['POST'])
@librarian_required
def delete_member(name):
    members = load_members()
    if name in members and not members[name]['borrowed_books'] and members[name]['fine_due'] == 0:
        del members[name]
        save_members(members)
        log_action(session['librarian'], 'Member Deleted', name)
        flash(f'Member "{name}" deleted.', 'success')
    else:
        flash('Cannot delete member.', 'danger')
    return redirect(url_for('manage_members'))


@app.route('/librarian/send-reminder/<name>', methods=['POST'])
@librarian_required
def send_reminder(name):
    members = load_members()
    if name not in members:
        flash('Member not found.', 'danger')
        return redirect(url_for('manage_members'))
    member = members[name]
    overdue = sum(1 for b in member['borrowed_books'] if b.get('due_date') and datetime.datetime.now() > datetime.datetime.strptime(b['due_date'], "%Y-%m-%d %H:%M"))
    log_action(session['librarian'], 'Reminder Sent', f'To: {name}, Overdue: {overdue}')
    flash(f'Reminder sent to {name} ({overdue} overdue books).', 'success')
    return redirect(url_for('manage_members'))


@app.route('/librarian/export')
@librarian_required
def export_csv():
    txns = load_transactions()
    filename = f"transactions_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Member', 'Book', 'Type', 'Date', 'Price', 'Fine', 'Due Date'])
        for t in txns:
            writer.writerow([t.get('member', ''), t.get('book', ''), t.get('type', ''),
                t.get('date', ''), t.get('price', ''), t.get('fine', ''), t.get('due_date', '')])
    log_action(session['librarian'], 'CSV Exported', f'{len(txns)} records')
    flash(f'Exported {len(txns)} transactions to {filename}', 'success')
    return redirect(url_for('librarian'))


@app.route('/librarian/report')
@librarian_required
def monthly_report():
    txns = load_transactions()
    now = datetime.datetime.now()
    month_str = now.strftime("%Y-%m")
    month_txns = [t for t in txns if t['date'][:7] == month_str]
    issues = len([t for t in month_txns if t['type'] == 'Issue'])
    returns = len([t for t in month_txns if t['type'] == 'Return'])
    purchases = len([t for t in month_txns if t['type'] == 'Purchase'])
    revenue = sum(t.get('price', 0) for t in month_txns if t['type'] == 'Purchase')
    popular = Counter(t['book'] for t in month_txns if t['type'] == 'Issue').most_common(5)
    return render_template('report.html', month_name=now.strftime("%B %Y"),
        issues=issues, returns=returns, purchases=purchases,
        revenue=revenue, popular=popular)


@app.route('/librarian/audit-log')
@librarian_required
def audit_log():
    return render_template('audit_log.html', logs=list(reversed(load_audit())))


@app.route('/librarian/settings')
@librarian_required
def settings():
    backup_dir = 'backups'
    backups = []
    if os.path.exists(backup_dir):
        for f in sorted(os.listdir(backup_dir), reverse=True):
            if f.endswith('.zip'):
                size = os.path.getsize(os.path.join(backup_dir, f))
                backups.append({'name': f, 'size': f'{size/1024:.1f} KB'})
    return render_template('settings.html', backups=backups)


@app.route('/librarian/backup', methods=['POST'])
@librarian_required
def backup_data():
    import zipfile
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f'backup_{timestamp}.zip')
    with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in [BOOK_FILE, MEMBER_FILE, TRANSACTION_FILE, RESERVATION_FILE, AUDIT_FILE, LIBRARIAN_FILE]:
            if os.path.exists(f):
                zf.write(f, f)
    log_action(session['librarian'], 'Backup Created', backup_file)
    flash(f'Backup created!', 'success')
    return redirect(url_for('settings'))


@app.route('/librarian/restore', methods=['POST'])
@librarian_required
def restore_data():
    import zipfile
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        flash('No backups found.', 'danger')
        return redirect(url_for('settings'))
    backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.zip')], reverse=True)
    if not backups:
        flash('No backups found.', 'danger')
        return redirect(url_for('settings'))
    latest = os.path.join(backup_dir, backups[0])
    with zipfile.ZipFile(latest, 'r') as zf:
        for member in zf.namelist():
            if not member.startswith('/') and '..' not in member:
                zf.extract(member, '.')
    log_action(session['librarian'], 'Data Restored', latest)
    flash(f'Data restored from {backups[0]}', 'success')
    return redirect(url_for('settings'))


@app.route('/librarian/download-backup/<filename>')
@librarian_required
def download_backup(filename):
    filepath = os.path.join('backups', filename)
    if os.path.exists(filepath) and '..' not in filename:
        log_action(session['librarian'], 'Backup Downloaded', filename)
        return send_file(filepath, as_attachment=True)
    flash('Backup not found.', 'danger')
    return redirect(url_for('settings'))


@app.route('/librarian/delete-backup/<filename>', methods=['POST'])
@librarian_required
def delete_backup(filename):
    filepath = os.path.join('backups', filename)
    if os.path.exists(filepath) and '..' not in filename:
        os.remove(filepath)
        log_action(session['librarian'], 'Backup Deleted', filename)
        flash(f'Backup deleted.', 'success')
    return redirect(url_for('settings'))


@app.route('/librarian/email-templates')
@librarian_required
def email_templates():
    return render_template('email_templates.html')


@app.route('/qr/<title>')
def generate_qr(title):
    books = load_books()
    if title not in books:
        flash('Book not found.', 'danger')
        return redirect(url_for('books'))
    book = books[title]
    qr_data = f"Title: {title}\nAuthor: {book['author']}\nISBN: {book.get('isbn', 'N/A')}\nPrice: ${book['price']:.2f}\nCategory: {book.get('category', 'N/A')}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1e293b", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', download_name=f'qr_{title}.png')


@app.route('/api/stats')
@login_required
def api_stats():
    books = load_books()
    members = load_members()
    txns = load_transactions()
    categories = Counter(b.get('category', 'Other') for b in books.values())
    monthly = Counter(t['date'][:7] for t in txns)
    popular = Counter(t['book'] for t in txns if t['type'] == 'Issue').most_common(5)
    return jsonify({
        'total_books': sum(d.get('total_copies', d['available_copies']) for d in books.values()),
        'total_members': len(members),
        'categories': dict(categories),
        'monthly': dict(sorted(monthly.items())),
        'popular': popular,
        'revenue': sum(t.get('price', 0) for t in txns if t['type'] == 'Purchase')
    })


@app.route('/api/notifications')
@login_required
def api_notifications():
    user = session.get('user')
    if not user:
        return jsonify([])
    members = load_members()
    if user not in members:
        return jsonify([])
    notifications = []
    now = datetime.datetime.now()
    for b in members[user]['borrowed_books']:
        if b.get('due_date'):
            due = datetime.datetime.strptime(b['due_date'], "%Y-%m-%d %H:%M")
            days_left = (due - now).days
            if days_left < 0:
                notifications.append({'type': 'overdue', 'book': b['title'], 'message': f'"{b["title"]}" is {abs(days_left)} days overdue!', 'color': 'danger'})
            elif days_left <= 3:
                notifications.append({'type': 'due_soon', 'book': b['title'], 'message': f'"{b["title"]}" due in {days_left} days', 'color': 'warning'})
    return jsonify(notifications)


@app.route('/librarian/charts')
@librarian_required
def charts():
    books = load_books()
    txns = load_transactions()
    categories = Counter(b.get('category', 'Other') for b in books.values())
    conditions = Counter(b.get('condition', 'New') for b in books.values())
    monthly_issues = Counter()
    monthly_revenue = Counter()
    for t in txns:
        month = t['date'][:7]
        if t['type'] == 'Issue':
            monthly_issues[month] += 1
        if t['type'] == 'Purchase':
            monthly_revenue[month] += t.get('price', 0)
    popular = Counter(t['book'] for t in txns if t['type'] == 'Issue').most_common(10)
    stock_status = {'Available': 0, 'Low Stock': 0, 'Out of Stock': 0}
    for b in books.values():
        if b['available_copies'] == 0:
            stock_status['Out of Stock'] += 1
        elif b['available_copies'] <= LOW_STOCK_THRESHOLD:
            stock_status['Low Stock'] += 1
        else:
            stock_status['Available'] += 1
    return render_template('charts.html',
        categories=dict(categories), conditions=dict(conditions),
        monthly_issues=dict(sorted(monthly_issues.items())),
        monthly_revenue=dict(sorted(monthly_revenue.items())),
        popular=popular, stock_status=stock_status)


@app.route('/librarian/book-label/<title>')
@librarian_required
def book_label(title):
    books = load_books()
    if title not in books:
        flash('Book not found.', 'danger')
        return redirect(url_for('books'))
    return render_template('book_label.html', title=title, book=books[title])


if __name__ == '__main__':
    app.run(debug=True, port=5000)
