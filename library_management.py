import json
import datetime
import random
import os
import hashlib
import csv
from collections import Counter
from colorama import Fore, Style, init

init(autoreset=True)

FINE_PER_DAY = 5
MAX_BORROW_LIMIT = 5
DUE_DAYS = 14
LOW_STOCK_THRESHOLD = 3
CATEGORIES = ["Fiction", "Science", "Programming", "Mathematics", "History", "Literature", "Other"]
CONDITIONS = ["New", "Good", "Worn", "Damaged", "Lost"]

BOLD = Style.BRIGHT
RESET = Style.RESET_ALL
W = Fore.WHITE
R = Fore.RED
G = Fore.GREEN
Y = Fore.YELLOW
C = Fore.CYAN
M = Fore.MAGENTA
BLUE = Fore.BLUE
LC = Fore.LIGHTCYAN_EX
LY = Fore.LIGHTYELLOW_EX
LG = Fore.LIGHTGREEN_EX
LR = Fore.LIGHTRED_EX
LM = Fore.LIGHTMAGENTA_EX


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def get_positive_float(prompt):
    while True:
        try:
            value = float(input(prompt).strip())
            if value > 0:
                return value
            print(f"{R}  Value must be positive!{RESET}")
        except ValueError:
            print(f"{R}  Invalid number!{RESET}")


def get_positive_int(prompt):
    while True:
        try:
            value = int(input(prompt).strip())
            if value >= 0:
                return value
            print(f"{R}  Value must be 0 or positive!{RESET}")
        except ValueError:
            print(f"{R}  Invalid number!{RESET}")


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_box(lines, width=52, color=C):
    print(f"\n{color}{'=' * width}{RESET}")
    for line in lines:
        print(f"{color}||{RESET} {line:<{width - 5}} {color}||{RESET}")
    print(f"{color}{'=' * width}{RESET}")


def print_header(title, width=52):
    clear_screen()
    print(f"\n{M}{BOLD}{'#' * width}{RESET}")
    padding = (width - len(title) - 4) // 2
    print(f"{M}{BOLD}#{' ' * padding}[ {title} ]{' ' * (width - padding - len(title) - 6)}#{RESET}")
    print(f"{M}{BOLD}{'#' * width}{RESET}")


def print_divider(char='-', length=60, color=C):
    print(f"{color}{char * length}{RESET}")


def print_row(cols, widths, color=Y):
    row = ""
    for col, w in zip(cols, widths):
        row += f"{col:<{w}}"
    print(f"{color}{row}{RESET}")


class Person:
    def __init__(self, name):
        self.name = name.title()


class Member(Person):
    def __init__(self, name, member_id, password):
        super().__init__(name)
        self.member_id = member_id
        self.password = password
        self.borrowed_books = []
        self.fine_due = 0
        self.history = []


class Librarian(Person):
    def __init__(self, name, password):
        super().__init__(name)
        self.password = password

    def add_book(self, library):
        print_header("ADD NEW BOOK")
        title = input("  Enter book name: ").strip().title()
        author = input("  Enter author name: ").strip().title()

        print(f"\n  {C}Available Categories:{RESET}")
        for i, cat in enumerate(CATEGORIES, 1):
            print(f"    {Y}{i}. {cat}{RESET}")
        cat_choice = input(f"  Select category (1-{len(CATEGORIES)}): ").strip()
        try:
            category = CATEGORIES[int(cat_choice) - 1]
        except (ValueError, IndexError):
            category = "Other"

        price = get_positive_float("  Enter book price: $")
        copies = get_positive_int("  Enter available copies: ")

        print(f"\n  {C}Book Condition:{RESET}")
        for i, cond in enumerate(CONDITIONS, 1):
            print(f"    {Y}{i}. {cond}{RESET}")
        cond_choice = input(f"  Select condition (1-{len(CONDITIONS)}): ").strip()
        try:
            condition = CONDITIONS[int(cond_choice) - 1]
        except (ValueError, IndexError):
            condition = "New"

        if title not in library.books:
            library.books[title] = {
                'author': author,
                'price': price,
                'available_copies': copies,
                'total_copies': copies,
                'category': category,
                'condition': condition,
                'added_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            library.save_data()
            print(f"\n  {G}{BOLD}Book '{title}' by {author} added successfully!{RESET}")
        else:
            print(f"\n  {Y}'{title}' already exists in the library.{RESET}")

    def update_book(self, library):
        print_header("UPDATE BOOK")
        library.display_books()
        title = input("\n  Enter book name to update: ").strip().title()
        if title not in library.books:
            print(f"\n  {R}'{title}' not found.{RESET}")
            return

        book = library.books[title]
        print(f"\n  {C}Current details of '{title}':{RESET}")
        print(f"    Author: {book['author']}")
        print(f"    Category: {book.get('category', 'N/A')}")
        print(f"    Price: ${book['price']:.2f}")
        print(f"    Copies: {book['available_copies']}/{book.get('total_copies', '?')}")
        print(f"    Condition: {book.get('condition', 'N/A')}")

        print(f"\n  {Y}1. Update Price")
        print(f"  2. Update Copies")
        print(f"  3. Update Author")
        print(f"  4. Update Category")
        print(f"  5. Update Condition{RESET}")
        choice = input("  Enter choice: ").strip()

        if choice == '1':
            new_price = get_positive_float("  Enter new price: $")
            library.books[title]['price'] = new_price
            print(f"\n  {G}Price updated to ${new_price:.2f}.{RESET}")
        elif choice == '2':
            new_copies = get_positive_int("  Enter new copies: ")
            library.books[title]['available_copies'] = new_copies
            library.books[title]['total_copies'] = new_copies
            print(f"\n  {G}Copies updated to {new_copies}.{RESET}")
        elif choice == '3':
            new_author = input("  Enter new author: ").strip().title()
            library.books[title]['author'] = new_author
            print(f"\n  {G}Author updated to {new_author}.{RESET}")
        elif choice == '4':
            print(f"\n  {C}Categories:{RESET}")
            for i, cat in enumerate(CATEGORIES, 1):
                print(f"    {Y}{i}. {cat}{RESET}")
            c = input("  Select: ").strip()
            try:
                library.books[title]['category'] = CATEGORIES[int(c) - 1]
                print(f"\n  {G}Category updated.{RESET}")
            except (ValueError, IndexError):
                print(f"\n  {R}Invalid choice.{RESET}")
        elif choice == '5':
            print(f"\n  {C}Conditions:{RESET}")
            for i, cond in enumerate(CONDITIONS, 1):
                print(f"    {Y}{i}. {cond}{RESET}")
            c = input("  Select: ").strip()
            try:
                library.books[title]['condition'] = CONDITIONS[int(c) - 1]
                print(f"\n  {G}Condition updated.{RESET}")
            except (ValueError, IndexError):
                print(f"\n  {R}Invalid choice.{RESET}")
        else:
            print(f"\n  {R}Invalid choice!{RESET}")
        library.save_data()

    def delete_book(self, library):
        print_header("DELETE BOOK")
        library.display_books()
        title = input("\n  Enter book name to delete: ").strip().title()
        if title not in library.books:
            print(f"\n  {R}'{title}' not found.{RESET}")
            return
        confirm = input(f"  {R}Delete '{title}'? (y/n): {RESET}").strip().lower()
        if confirm == 'y':
            del library.books[title]
            library.save_data()
            print(f"\n  {G}Book '{title}' deleted.{RESET}")
        else:
            print(f"\n  {Y}Deletion cancelled.{RESET}")


class Library:
    def __init__(self, book_file='books.json', member_file='members.json', transaction_file='transactions.json'):
        self.books = {}
        self.members = {}
        self.librarians = {}
        self.transactions = []
        self.reservations = []
        self.book_file = book_file
        self.member_file = member_file
        self.transaction_file = transaction_file
        self.reservation_file = 'reservations.json'
        self.load_data()

    def save_data(self):
        with open(self.book_file, 'w') as f:
            json.dump(self.books, f, indent=4)
        with open(self.member_file, 'w') as f:
            json.dump({name: {
                'member_id': m.member_id, 'password': m.password,
                'borrowed_books': m.borrowed_books, 'fine_due': m.fine_due,
                'history': m.history
            } for name, m in self.members.items()}, f, indent=4)
        with open(self.transaction_file, 'w') as f:
            json.dump(self.transactions, f, indent=4)
        with open(self.reservation_file, 'w') as f:
            json.dump(self.reservations, f, indent=4)

    def load_data(self):
        if os.path.exists(self.book_file):
            with open(self.book_file, 'r') as f:
                self.books = json.load(f)
                for title, details in self.books.items():
                    if 'category' not in details:
                        details['category'] = 'Other'
                    if 'condition' not in details:
                        details['condition'] = 'New'
                    if 'total_copies' not in details:
                        details['total_copies'] = details['available_copies']
                    if 'added_date' not in details:
                        details['added_date'] = 'N/A'
        if os.path.exists(self.member_file):
            with open(self.member_file, 'r') as f:
                member_data = json.load(f)
                data_changed = False
                for name, details in member_data.items():
                    stored_pw = details['password']
                    if len(stored_pw) != 64:
                        stored_pw = hash_password(stored_pw)
                        details['password'] = stored_pw
                        data_changed = True
                    self.members[name] = Member(name, details['member_id'], stored_pw)
                    self.members[name].fine_due = details.get('fine_due', 0)
                    self.members[name].history = details.get('history', [])
                    self.members[name].borrowed_books = details.get('borrowed_books', [])
                    for b in self.members[name].borrowed_books:
                        if not isinstance(b, dict):
                            idx = self.members[name].borrowed_books.index(b)
                            self.members[name].borrowed_books[idx] = {'title': b, 'due_date': None, 'issue_date': None}
                if data_changed:
                    self.save_data()
                    print(f"  {Y}Old plain-text passwords have been hashed.{RESET}")
        if os.path.exists(self.transaction_file):
            with open(self.transaction_file, 'r') as f:
                self.transactions = json.load(f)
        if os.path.exists(self.reservation_file):
            with open(self.reservation_file, 'r') as f:
                self.reservations = json.load(f)
        if not self.librarians:
            self.librarians = {
                'alice': hash_password('alice123'),
                'bob': hash_password('bob123')
            }

    def get_dashboard(self):
        print_header("DASHBOARD")
        total_books = sum(d.get('total_copies', d['available_copies']) for d in self.books.values())
        available = sum(d['available_copies'] for d in self.books.values())
        total_members = len(self.members)
        total_transactions = len(self.transactions)
        total_fines = sum(t.get('fine', 0) for t in self.transactions)
        total_issues = len([t for t in self.transactions if t['type'] == 'Issue'])
        total_returns = len([t for t in self.transactions if t['type'] == 'Return'])
        total_purchases = len([t for t in self.transactions if t['type'] == 'Purchase'])
        low_stock = [t for t, d in self.books.items() if 0 < d['available_copies'] <= LOW_STOCK_THRESHOLD]
        out_of_stock = [t for t, d in self.books.items() if d['available_copies'] == 0]

        stats = [
            f"{LC}Total Books in Library  : {BOLD}{total_books}",
            f"{LC}Available for Issue    : {BOLD}{available}",
            f"{LC}Total Members          : {BOLD}{total_members}",
            f"{LC}Total Transactions     : {BOLD}{total_transactions}",
            f"",
            f"{LG}Books Issued           : {BOLD}{total_issues}",
            f"{LG}Books Returned         : {BOLD}{total_returns}",
            f"{LG}Books Purchased        : {BOLD}{total_purchases}",
            f"{LR}Total Fine Collected   : ${BOLD}{total_fines:.2f}",
        ]
        print_box(stats, 50, M)

        if low_stock or out_of_stock:
            print(f"\n  {R}{BOLD}LOW STOCK ALERT:{RESET}")
            for book in low_stock:
                print(f"    {Y}  Only {self.books[book]['available_copies']} copy left: {book}{RESET}")
            for book in out_of_stock:
                print(f"    {R}  OUT OF STOCK: {book}{RESET}")

    def display_books(self):
        print_header("LIBRARY BOOKS")
        if not self.books:
            print(f"\n  {R}No books available.{RESET}")
            return

        widths = [25, 18, 10, 8, 15, 12]
        print_row(["  Title", "Author", "Price", "Stock", "Category", "Condition"], widths, LC)
        print_divider('-', 95)
        for title, d in self.books.items():
            stock_color = G if d['available_copies'] > LOW_STOCK_THRESHOLD else (Y if d['available_copies'] > 0 else R)
            cond_color = G if d.get('condition') == 'New' else (Y if d.get('condition') == 'Good' else R)
            print(f"  {LY}{title:<25}{RESET} {W}{d['author']:<18}{RESET} ${d['price']:<9.2f} {stock_color}{d['available_copies']:<8}{RESET} {C}{d.get('category', 'Other'):<15}{RESET} {cond_color}{d.get('condition', 'New'):<12}{RESET}")

        total_copies = sum(d.get('total_copies', d['available_copies']) for d in self.books.values())
        avail = sum(d['available_copies'] for d in self.books.values())
        print_divider('-', 95)
        print(f"  {LC}Total: {total_copies} books | Available: {avail} | Issued: {total_copies - avail}{RESET}")

        low_stock = [t for t, d in self.books.items() if 0 < d['available_copies'] <= LOW_STOCK_THRESHOLD]
        if low_stock:
            print(f"\n  {R}{BOLD}Low Stock Alert:{RESET}")
            for b in low_stock:
                print(f"    {Y}  {b} - {self.books[b]['available_copies']} left{RESET}")

    def search_book(self):
        print_header("SEARCH BOOK")
        print(f"  {C}1. Search by Title{RESET}")
        print(f"  {C}2. Search by Author{RESET}")
        print(f"  {C}3. Search by Category{RESET}")
        print(f"  {C}4. Advanced Search (Price Range + Category){RESET}")
        choice = input("\n  Enter choice: ").strip()

        if choice == '1':
            title = input("  Enter title: ").strip().title()
            if title in self.books:
                d = self.books[title]
                cond_color = G if d.get('condition') == 'New' else (Y if d.get('condition') == 'Good' else R)
                info = [
                    f"  {BOLD}Title{RESET}     : {LY}{title}{RESET}",
                    f"  {BOLD}Author{RESET}    : {W}{d['author']}{RESET}",
                    f"  {BOLD}Price{RESET}     : ${d['price']:.2f}",
                    f"  {BOLD}Stock{RESET}     : {d['available_copies']}/{d.get('total_copies', '?')}",
                    f"  {BOLD}Category{RESET}  : {C}{d.get('category', 'N/A')}{RESET}",
                    f"  {BOLD}Condition{RESET} : {cond_color}{d.get('condition', 'N/A')}{RESET}",
                ]
                print_box(info, 45, G)
            else:
                print(f"\n  {R}Book '{title}' not found.{RESET}")

        elif choice == '2':
            author = input("  Enter author: ").strip().title()
            results = {k: v for k, v in self.books.items() if v['author'].lower() == author.lower()}
            if results:
                print(f"\n  {G}Books by '{author}':{RESET}")
                print_row(["  Title", "Price", "Stock"], [30, 10, 8], LC)
                print_divider('-', 55)
                for t, d in results.items():
                    print(f"  {LY}{t:<30}{RESET} ${d['price']:<9.2f} {G}{d['available_copies']:<8}{RESET}")
            else:
                print(f"\n  {R}No books by '{author}'.{RESET}")

        elif choice == '3':
            print(f"\n  {C}Categories:{RESET}")
            for i, cat in enumerate(CATEGORIES, 1):
                print(f"    {Y}{i}. {cat}{RESET}")
            c = input("  Select category: ").strip()
            try:
                cat = CATEGORIES[int(c) - 1]
                results = {k: v for k, v in self.books.items() if v.get('category') == cat}
                if results:
                    print(f"\n  {G}Books in '{cat}':{RESET}")
                    print_row(["  Title", "Author", "Price", "Stock"], [25, 18, 10, 8], LC)
                    print_divider('-', 68)
                    for t, d in results.items():
                        print(f"  {LY}{t:<25}{RESET} {W}{d['author']:<18}{RESET} ${d['price']:<9.2f} {G}{d['available_copies']:<8}{RESET}")
                else:
                    print(f"\n  {R}No books in '{cat}'.{RESET}")
            except (ValueError, IndexError):
                print(f"\n  {R}Invalid choice.{RESET}")

        elif choice == '4':
            print(f"\n  {C}Advanced Search{RESET}")
            min_price = input("  Min price (or Enter to skip): $").strip()
            max_price = input("  Max price (or Enter to skip): $").strip()
            print(f"  {C}Categories:{RESET} (Enter to skip)")
            for i, cat in enumerate(CATEGORIES, 1):
                print(f"    {Y}{i}. {cat}{RESET}")
            cat_input = input("  Select category: ").strip()

            results = dict(self.books)
            if min_price:
                try:
                    results = {k: v for k, v in results.items() if v['price'] >= float(min_price)}
                except ValueError:
                    pass
            if max_price:
                try:
                    results = {k: v for k, v in results.items() if v['price'] <= float(max_price)}
                except ValueError:
                    pass
            if cat_input:
                try:
                    cat = CATEGORIES[int(cat_input) - 1]
                    results = {k: v for k, v in results.items() if v.get('category') == cat}
                except (ValueError, IndexError):
                    pass

            if results:
                print(f"\n  {G}Found {len(results)} book(s):{RESET}")
                print_row(["  Title", "Price", "Category", "Stock"], [25, 10, 15, 8], LC)
                print_divider('-', 65)
                for t, d in results.items():
                    print(f"  {LY}{t:<25}{RESET} ${d['price']:<9.2f} {C}{d.get('category', 'N/A'):<15}{RESET} {G}{d['available_copies']:<8}{RESET}")
            else:
                print(f"\n  {R}No books match your filters.{RESET}")
        else:
            print(f"\n  {R}Invalid choice.{RESET}")

    def register_member(self):
        print_header("REGISTER NEW MEMBER")
        name = input("  Enter your name: ").strip().title()
        if name in self.members:
            print(f"\n  {Y}'{name}' already registered. Please log in.{RESET}")
            return None

        while True:
            password = input("  Enter password (min 4 chars): ").strip()
            if len(password) < 4:
                print(f"  {R}Password must be at least 4 characters!{RESET}")
                continue
            confirm = input("  Confirm password: ").strip()
            if password != confirm:
                print(f"  {R}Passwords do not match!{RESET}")
                continue
            break

        member_id = random.randint(1000, 9999)
        self.members[name] = Member(name, member_id, hash_password(password))
        self.save_data()
        print(f"\n  {G}{BOLD}Registration successful!{RESET}")
        info = [f"  {BOLD}Name{RESET}  : {LY}{name}{RESET}", f"  {BOLD}ID{RESET}    : {LG}{member_id}{RESET}"]
        print_box(info, 35, G)
        return name

    def login_member(self):
        print_header("MEMBER LOGIN")
        name = input("  Enter your name: ").strip().title()
        password = input("  Enter your password: ").strip()
        if name in self.members and self.members[name].password == hash_password(password):
            print(f"\n  {G}{BOLD}Welcome, {name}!{RESET}")
            return name
        else:
            print(f"\n  {R}Invalid credentials.{RESET}")
            return None

    def login_librarian(self):
        print_header("LIBRARIAN LOGIN")
        name = input("  Enter librarian name: ").strip().lower()
        password = input("  Enter password: ").strip()
        if name in self.librarians and self.librarians[name] == hash_password(password):
            print(f"\n  {G}{BOLD}Welcome, Librarian {name.title()}!{RESET}")
            return True
        else:
            print(f"\n  {R}Invalid credentials.{RESET}")
            return False

    def change_password(self, member_name):
        print_header("CHANGE PASSWORD")
        current = input("  Enter current password: ").strip()
        if self.members[member_name].password != hash_password(current):
            print(f"\n  {R}Incorrect current password.{RESET}")
            return
        while True:
            new_pw = input("  Enter new password (min 4 chars): ").strip()
            if len(new_pw) < 4:
                print(f"  {R}Password must be at least 4 characters!{RESET}")
                continue
            confirm = input("  Confirm new password: ").strip()
            if new_pw != confirm:
                print(f"  {R}Passwords do not match!{RESET}")
                continue
            break
        self.members[member_name].password = hash_password(new_pw)
        self.save_data()
        print(f"\n  {G}Password changed successfully!{RESET}")

    def issue_book(self, member_name):
        if len(self.members[member_name].borrowed_books) >= MAX_BORROW_LIMIT:
            print(f"\n  {R}Borrow limit reached! Max {MAX_BORROW_LIMIT} books allowed.{RESET}")
            return
        print_header("ISSUE BOOK")
        self.display_books()
        book_name = input("\n  Enter book name to borrow: ").strip().title()
        if book_name not in self.books:
            print(f"\n  {R}Book '{book_name}' not found.{RESET}")
            return
        if self.books[book_name]['available_copies'] <= 0:
            print(f"\n  {R}No copies available for '{book_name}'.{RESET}")
            res = input(f"  {Y}Reserve this book? (y/n): {RESET}").strip().lower()
            if res == 'y':
                self.reservations.append({
                    'member': member_name, 'book': book_name,
                    'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                self.save_data()
                print(f"\n  {G}Book '{book_name}' reserved. You'll be notified when available.{RESET}")
            return

        issue_date = datetime.datetime.now()
        due_date = issue_date + datetime.timedelta(days=DUE_DAYS)
        self.books[book_name]['available_copies'] -= 1
        self.members[member_name].borrowed_books.append({
            'title': book_name,
            'issue_date': issue_date.strftime("%Y-%m-%d %H:%M"),
            'due_date': due_date.strftime("%Y-%m-%d %H:%M")
        })

        transaction = {
            'member': member_name, 'book': book_name, 'type': 'Issue',
            'date': issue_date.strftime("%Y-%m-%d %H:%M"),
            'due_date': due_date.strftime("%Y-%m-%d %H:%M")
        }
        self.transactions.append(transaction)
        self.save_data()

        for res in self.reservations[:]:
            if res['book'] == book_name and res['member'] != member_name:
                self.reservations.remove(res)
        self.save_data()

        print(f"\n  {G}{BOLD}Book issued successfully!{RESET}")
        info = [
            f"  {BOLD}Book{RESET}     : {LY}{book_name}{RESET}",
            f"  {BOLD}Member{RESET}   : {LY}{member_name}{RESET}",
            f"  {BOLD}Issue Date{RESET}: {W}{issue_date.strftime('%Y-%m-%d')}{RESET}",
            f"  {BOLD}Due Date{RESET}  : {Y}{due_date.strftime('%Y-%m-%d')}{RESET}",
        ]
        print_box(info, 45, G)

    def return_book(self, member_name):
        print_header("RETURN BOOK")
        self.display_borrowed_books(member_name)
        book_name = input("\n  Enter book name to return: ").strip().title()
        borrowed = None
        for b in self.members[member_name].borrowed_books:
            if isinstance(b, dict) and b.get('title') == book_name:
                borrowed = b
                break
        if not borrowed:
            print(f"\n  {R}You have not borrowed '{book_name}'.{RESET}")
            return

        self.members[member_name].borrowed_books.remove(borrowed)
        self.books[book_name]['available_copies'] += 1

        fine = 0
        if borrowed.get('due_date'):
            due = datetime.datetime.strptime(borrowed['due_date'], "%Y-%m-%d %H:%M")
            now = datetime.datetime.now()
            if now > due:
                days_late = (now - due).days
                fine = days_late * FINE_PER_DAY
                self.members[member_name].fine_due += fine

        self.members[member_name].history.append({
            'title': book_name, 'action': 'Return',
            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            'fine': fine
        })

        transaction = {
            'member': member_name, 'book': book_name, 'type': 'Return',
            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'fine': fine
        }
        self.transactions.append(transaction)
        self.save_data()

        for res in self.reservations[:]:
            if res['book'] == book_name:
                print(f"\n  {Y}Notification: {res['member']} had reserved '{book_name}' - now available!{RESET}")
                break

        if fine > 0:
            print(f"\n  {R}{BOLD}Returned with late fine!{RESET}")
            info = [
                f"  {BOLD}Book{RESET}   : {LY}{book_name}{RESET}",
                f"  {BOLD}Fine{RESET}   : {R}${fine:.2f}{RESET}",
                f"  {BOLD}Total Due{RESET}: {R}${self.members[member_name].fine_due:.2f}{RESET}",
            ]
            print_box(info, 35, R)
        else:
            print(f"\n  {G}{BOLD}Book returned on time. No fine!{RESET}")

    def purchase_book(self, member_name):
        print_header("PURCHASE BOOK")
        self.display_books()
        book_name = input("\n  Enter book name to purchase: ").strip().title()
        if book_name not in self.books:
            print(f"\n  {R}Book '{book_name}' not found.{RESET}")
            return
        if self.books[book_name]['available_copies'] <= 0:
            print(f"\n  {R}No copies available.{RESET}")
            return

        price = self.books[book_name]['price']
        self.books[book_name]['available_copies'] -= 1

        self.members[member_name].history.append({
            'title': book_name, 'action': 'Purchase',
            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'fine': 0
        })

        transaction = {
            'member': member_name, 'book': book_name, 'type': 'Purchase',
            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 'price': price
        }
        self.transactions.append(transaction)
        self.save_data()

        print(f"\n  {G}{BOLD}Book purchased successfully!{RESET}")
        self.generate_receipt(member_name, book_name, price)

    def generate_receipt(self, member_name, book_name, price):
        receipt_id = f"RCP-{random.randint(10000, 99999)}"
        now = datetime.datetime.now()
        print_divider('=', 50, G)
        print(f"{G}{'':>15}RECEIPT{RESET}")
        print_divider('=', 50, G)
        print(f"  {BOLD}Receipt ID{RESET} : {receipt_id}")
        print(f"  {BOLD}Date{RESET}       : {now.strftime('%Y-%m-%d %H:%M')}")
        print(f"  {BOLD}Member{RESET}     : {member_name}")
        print_divider('-', 50, G)
        print(f"  {BOLD}Book{RESET}       : {book_name}")
        print(f"  {BOLD}Price{RESET}      : ${price:.2f}")
        print_divider('-', 50, G)
        print(f"  {BOLD}TOTAL PAID{RESET} : {G}${price:.2f}{RESET}")
        print_divider('=', 50, G)
        print(f"  {LC}Thank you for your purchase!{RESET}\n")

    def display_borrowed_books(self, member_name):
        borrowed = self.members[member_name].borrowed_books
        print_header("YOUR BORROWED BOOKS")
        if not borrowed:
            print(f"\n  {R}You have not borrowed any books.{RESET}")
            return
        now = datetime.datetime.now()
        print_row(["  Title", "Issue Date", "Due Date", "Status"], [25, 18, 18, 22], LC)
        print_divider('-', 90)
        for b in borrowed:
            if isinstance(b, dict):
                title = b.get('title', 'Unknown')
                issue = b.get('issue_date', 'N/A')[:10]
                due = b.get('due_date', 'N/A')[:10]
                if due and due != 'N/A':
                    due_dt = datetime.datetime.strptime(b.get('due_date', ''), "%Y-%m-%d %H:%M")
                    if now > due_dt:
                        days = (now - due_dt).days
                        fine = days * FINE_PER_DAY
                        status = f"{R}OVERDUE {days}d ${fine}{RESET}"
                    else:
                        days_left = (due_dt - now).days
                        status = f"{G}On Time ({days_left}d left){RESET}"
                else:
                    status = f"{Y}Active{RESET}"
                print(f"  {LY}{title:<25}{RESET} {W}{issue:<18}{RESET} {Y}{due:<18}{RESET} {status}")
        print(f"\n  {LC}Total borrowed: {len(borrowed)}/{MAX_BORROW_LIMIT}{RESET}")
        if self.members[member_name].fine_due > 0:
            print(f"  {R}Fine due: ${self.members[member_name].fine_due:.2f}{RESET}")

    def display_borrowing_history(self, member_name):
        print_header("BORROWING HISTORY")
        history = self.members[member_name].history
        if not history:
            print(f"\n  {R}No history yet.{RESET}")
            return
        print_row(["  Date", "Book", "Action", "Fine"], [18, 25, 12, 10], LC)
        print_divider('-', 70)
        for h in history:
            fine_str = f"${h.get('fine', 0):.2f}" if h.get('fine', 0) > 0 else "-"
            print(f"  {W}{h.get('date', 'N/A'):<18}{RESET} {LY}{h.get('title', 'N/A'):<25}{RESET} {C}{h.get('action', 'N/A'):<12}{RESET} {R}{fine_str:<10}{RESET}")

    def pay_fine(self, member_name):
        print_header("PAY FINE")
        fine_due = self.members[member_name].fine_due
        if fine_due <= 0:
            print(f"\n  {G}No fine due. You're all clear!{RESET}")
            return
        print(f"  {R}Fine due: ${fine_due:.2f}{RESET}")
        pay = get_positive_float(f"  Enter amount to pay: $")
        if pay >= fine_due:
            self.members[member_name].fine_due = 0
            print(f"\n  {G}{BOLD}Fine paid in full!{RESET}")
        else:
            self.members[member_name].fine_due -= pay
            print(f"\n  {G}Paid ${pay:.2f}. Remaining: ${self.members[member_name].fine_due:.2f}{RESET}")
        self.save_data()

    def display_transactions(self):
        print_header("TRANSACTIONS")
        if not self.transactions:
            print(f"\n  {R}No transactions.{RESET}")
            return
        print_row(["  Member", "Book", "Type", "Date", "Extra"], [14, 22, 10, 18, 15], LC)
        print_divider('-', 85)
        for t in self.transactions[-20:]:
            extra = ''
            if 'price' in t:
                extra = f"${t['price']:.2f}"
            elif 'fine' in t and t['fine'] > 0:
                extra = f"Fine: ${t['fine']:.2f}"
            elif 'due_date' in t:
                extra = f"Due: {t['due_date'][:10]}"
            print(f"  {W}{t['member']:<14}{RESET} {LY}{t['book']:<22}{RESET} {C}{t['type']:<10}{RESET} {W}{t['date'][:18]:<18}{RESET} {Y}{extra:<15}{RESET}")
        print(f"\n  {LC}Showing last 20 of {len(self.transactions)} transactions{RESET}")

    def export_to_csv(self):
        print_header("EXPORT TO CSV")
        if not self.transactions:
            print(f"\n  {R}No transactions to export.{RESET}")
            return
        filename = f"transactions_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Member', 'Book', 'Type', 'Date', 'Price', 'Fine', 'Due Date'])
                for t in self.transactions:
                    writer.writerow([
                        t.get('member', ''), t.get('book', ''), t.get('type', ''),
                        t.get('date', ''), t.get('price', ''), t.get('fine', ''),
                        t.get('due_date', '')
                    ])
            print(f"\n  {G}{BOLD}Exported {len(self.transactions)} transactions to '{filename}'{RESET}")
        except Exception as e:
            print(f"\n  {R}Export failed: {e}{RESET}")

    def monthly_report(self):
        print_header("MONTHLY REPORT")
        now = datetime.datetime.now()
        month_str = now.strftime("%Y-%m")
        month_transactions = [t for t in self.transactions if t['date'][:7] == month_str]
        issues = [t for t in month_transactions if t['type'] == 'Issue']
        returns = [t for t in month_transactions if t['type'] == 'Return']
        purchases = [t for t in month_transactions if t['type'] == 'Purchase']
        total_fine = sum(t.get('fine', 0) for t in month_transactions)
        total_revenue = sum(t.get('price', 0) for t in purchases)

        stats = [
            f"  {LC}Month{RESET}           : {BOLD}{now.strftime('%B %Y')}{RESET}",
            f"  {LC}Total Issues{RESET}    : {BOLD}{len(issues)}{RESET}",
            f"  {LC}Total Returns{RESET}   : {BOLD}{len(returns)}{RESET}",
            f"  {LC}Total Purchases{RESET} : {BOLD}{len(purchases)}{RESET}",
            f"  {LG}Revenue{RESET}         : ${BOLD}{total_revenue:.2f}{RESET}",
            f"  {LR}Fine Collected{RESET}  : ${BOLD}{total_fine:.2f}{RESET}",
        ]
        print_box(stats, 45, M)

        if issues:
            book_counter = Counter(t['book'] for t in issues)
            print(f"\n  {C}Most Issued Books This Month:{RESET}")
            for book, count in book_counter.most_common(5):
                bar = '█' * count
                print(f"    {LY}{book:<25}{RESET} {G}{bar} {count}{RESET}")

    def popular_books(self):
        print_header("MOST POPULAR BOOKS")
        issue_counts = Counter()
        for t in self.transactions:
            if t['type'] == 'Issue':
                issue_counts[t['book']] += 1
        if not issue_counts:
            print(f"\n  {R}No issue data yet.{RESET}")
            return
        print(f"\n  {C}Most Borrowed Books (All Time):{RESET}")
        print_row(["  Rank", "Title", "Times Issued"], [8, 25, 15], LC)
        print_divider('-', 55)
        for rank, (book, count) in enumerate(issue_counts.most_common(10), 1):
            bar = '█' * min(count, 20)
            medal = f"{G}[1st]{RESET}" if rank == 1 else (f"{Y}[2nd]{RESET}" if rank == 2 else (f"{C}[3rd]{RESET}" if rank == 3 else f"    "))
            print(f"  {medal} {LY}{book:<25}{RESET} {G}{bar} {count}{RESET}")

    def active_members(self):
        print_header("ACTIVE MEMBERS")
        member_counts = Counter()
        for t in self.transactions:
            member_counts[t['member']] += 1
        if not member_counts:
            print(f"\n  {R}No member data yet.{RESET}")
            return
        print_row(["  Rank", "Member", "Total Transactions"], [8, 20, 20], LC)
        print_divider('-', 55)
        for rank, (member, count) in enumerate(member_counts.most_common(10), 1):
            borrowed = len(self.members.get(member, Member('', 0, '')).borrowed_books) if member in self.members else 0
            print(f"  {LY}{rank:<8}{RESET} {W}{member:<20}{RESET} {G}{count:<20}{RESET}")

    def low_stock_alert(self):
        print_header("LOW STOCK ALERT")
        low = {t: d for t, d in self.books.items() if d['available_copies'] <= LOW_STOCK_THRESHOLD}
        out = {t: d for t, d in self.books.items() if d['available_copies'] == 0}
        if not low:
            print(f"\n  {G}All books have sufficient stock.{RESET}")
            return
        if out:
            print(f"\n  {R}{BOLD}OUT OF STOCK:{RESET}")
            for t, d in out.items():
                print(f"    {R}  {t} by {d['author']} (Category: {d.get('category', 'N/A')}){RESET}")
        if low:
            print(f"\n  {Y}{BOLD}LOW STOCK (<= {LOW_STOCK_THRESHOLD} copies):{RESET}")
            for t, d in low.items():
                if d['available_copies'] > 0:
                    bar = '█' * d['available_copies']
                    print(f"    {Y}  {t:<25}{RESET} {R}{bar} {d['available_copies']} left{RESET}")

    def delete_member(self):
        print_header("DELETE MEMBER")
        name = input("  Enter member name to delete: ").strip().title()
        if name not in self.members:
            print(f"\n  {R}Member '{name}' not found.{RESET}")
            return
        if self.members[name].borrowed_books:
            print(f"\n  {R}Cannot delete - '{name}' has borrowed books. Return them first.{RESET}")
            return
        if self.members[name].fine_due > 0:
            print(f"\n  {R}Cannot delete - '{name}' has pending fine of ${self.members[name].fine_due:.2f}.{RESET}")
            return
        confirm = input(f"  {R}Delete '{name}'? (y/n): {RESET}").strip().lower()
        if confirm == 'y':
            del self.members[name]
            self.save_data()
            print(f"\n  {G}Member '{name}' deleted.{RESET}")
        else:
            print(f"\n  {Y}Deletion cancelled.{RESET}")

    def logout_member(self, member_name):
        print(f"\n  {Y}Goodbye, {member_name}!{RESET}")
        return None


def auth_menu(library):
    while True:
        clear_screen()
        lines = [
            f"{BOLD}Welcome to Library Management System{RESET}",
            f"",
            f"{C}1. Register{RESET}",
            f"{C}2. Member Login{RESET}",
            f"{C}3. Librarian Login{RESET}",
            f"{R}4. Exit{RESET}",
        ]
        print_box(lines, 45, M)
        choice = input(f"\n  {BLUE}Enter choice: {RESET}").strip()

        if choice == '1':
            user_name = library.register_member()
            if user_name:
                input("\n  Press Enter to continue...")
        elif choice == '2':
            user_name = library.login_member()
            if user_name:
                return user_name
        elif choice == '3':
            if library.login_librarian():
                return 'librarian'
        elif choice == '4':
            print(f"\n  {R}Exiting... Goodbye!{RESET}")
            exit()
        else:
            print(f"\n  {Y}Invalid choice!{RESET}")
            input("  Press Enter to continue...")


def member_menu(library, user_name):
    while True:
        clear_screen()
        lines = [
            f"{BOLD}Welcome, {user_name.upper()}{RESET}",
            f"",
            f"{C} 1. Display Books{RESET}       {C} 6. My Borrowed Books{RESET}",
            f"{C} 2. Search Book{RESET}         {C} 7. Borrowing History{RESET}",
            f"{C} 3. Issue Book{RESET}          {C} 8. Display Transactions{RESET}",
            f"{C} 4. Return Book{RESET}         {C} 9. Pay Fine{RESET}",
            f"{C} 5. Purchase Book{RESET}       {C}10. Change Password{RESET}",
            f"",
            f"{Y}11. Logout{RESET}              {R}12. Exit{RESET}",
        ]
        print_box(lines, 50, M)

        if library.members.get(user_name) and library.members[user_name].fine_due > 0:
            print(f"\n  {R}{BOLD}Fine Due: ${library.members[user_name].fine_due:.2f}{RESET}")
        borrowed = library.members.get(user_name, Member('', 0, '')).borrowed_books
        print(f"  {LC}Books borrowed: {len(borrowed)}/{MAX_BORROW_LIMIT}{RESET}")

        choice = input(f"\n  {BLUE}Enter choice: {RESET}").strip()

        if choice == '1':
            library.display_books()
        elif choice == '2':
            library.search_book()
        elif choice == '3':
            library.issue_book(user_name)
        elif choice == '4':
            library.return_book(user_name)
        elif choice == '5':
            library.purchase_book(user_name)
        elif choice == '6':
            library.display_borrowed_books(user_name)
        elif choice == '7':
            library.display_borrowing_history(user_name)
        elif choice == '8':
            library.display_transactions()
        elif choice == '9':
            library.pay_fine(user_name)
        elif choice == '10':
            library.change_password(user_name)
        elif choice == '11':
            library.logout_member(user_name)
            return
        elif choice == '12':
            print(f"\n  {R}Exiting... Goodbye!{RESET}")
            exit()
        else:
            print(f"\n  {Y}Invalid choice!{RESET}")
        input("\n  Press Enter to continue...")


def librarian_menu(library):
    while True:
        clear_screen()
        lines = [
            f"{BOLD}LIBRARIAN PANEL{RESET}",
            f"",
            f"{C} 1. Add Book{RESET}          {C} 6. Monthly Report{RESET}",
            f"{C} 2. Update Book{RESET}       {C} 7. Popular Books{RESET}",
            f"{C} 3. Delete Book{RESET}       {C} 8. Active Members{RESET}",
            f"{C} 4. Display Books{RESET}     {C} 9. Low Stock Alert{RESET}",
            f"{C} 5. Search Book{RESET}       {C}10. Export to CSV{RESET}",
            f"",
            f"{C}11. Display Transactions{RESET}  {C}12. Delete Member{RESET}",
            f"",
            f"{Y}13. Logout{RESET}             {R}14. Exit{RESET}",
        ]
        print_box(lines, 50, M)

        choice = input(f"\n  {BLUE}Enter choice: {RESET}").strip()

        if choice == '1':
            lib = Librarian("Admin", "")
            lib.add_book(library)
        elif choice == '2':
            lib = Librarian("Admin", "")
            lib.update_book(library)
        elif choice == '3':
            lib = Librarian("Admin", "")
            lib.delete_book(library)
        elif choice == '4':
            library.display_books()
        elif choice == '5':
            library.search_book()
        elif choice == '6':
            library.monthly_report()
        elif choice == '7':
            library.popular_books()
        elif choice == '8':
            library.active_members()
        elif choice == '9':
            library.low_stock_alert()
        elif choice == '10':
            library.export_to_csv()
        elif choice == '11':
            library.display_transactions()
        elif choice == '12':
            library.delete_member()
        elif choice == '13':
            print(f"\n  {Y}Logged out.{RESET}")
            return
        elif choice == '14':
            print(f"\n  {R}Exiting... Goodbye!{RESET}")
            exit()
        else:
            print(f"\n  {Y}Invalid choice!{RESET}")
        input("\n  Press Enter to continue...")


def main():
    library = Library()
    while True:
        user_name = auth_menu(library)
        if user_name == 'librarian':
            librarian_menu(library)
        else:
            member_menu(library, user_name)


if __name__ == "__main__":
    main()
