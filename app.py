"""
BrickDash - Workforce, Order and Inventory Management System for Brick Industry
Flask Application with SQLite Database (No external dependencies beyond Flask)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, g, session
from functools import wraps
import sqlite3
from datetime import datetime, date, timedelta
import csv
import io
import os
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'brickdash-secret-key-2025')
# Session configuration for production
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RENDER', False)  # True on Render (HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'brickdash.db')

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def format_indian_currency(amount):
    """Format amount in Indian numbering system (lakhs, thousands)
    Example: 750253 -> 7,50,253
    """
    if amount is None:
        amount = 0
    amount = int(round(amount))
    if amount < 0:
        return '-₹' + format_indian_currency(-amount)[1:]
    
    s = str(amount)
    if len(s) <= 3:
        return '₹' + s
    
    # Last 3 digits
    result = s[-3:]
    s = s[:-3]
    
    # Add remaining digits in groups of 2
    while s:
        result = s[-2:] + ',' + result
        s = s[:-2]
    
    return '₹' + result

# ==================== AUTHENTICATION DECORATOR ====================

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """Decorator to require specific roles for routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_role' not in session:
                flash('Please login to access this page.', 'warning')
                return redirect(url_for('login'))
            if session['user_role'] not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== DATE ADAPTERS (Python 3.12+) ====================
# Register adapters and converters for date/datetime handling
def adapt_date(val):
    """Adapt date to ISO format string"""
    return val.isoformat()

def adapt_datetime(val):
    """Adapt datetime to ISO format string"""
    return val.isoformat()

def convert_date(val):
    """Convert ISO format string to date"""
    return datetime.strptime(val.decode(), "%Y-%m-%d").date()

def convert_datetime(val):
    """Convert ISO format string to datetime"""
    return datetime.fromisoformat(val.decode())

# Register the adapters and converters
sqlite3.register_adapter(date, adapt_date)
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("DATE", convert_date)
sqlite3.register_converter("TIMESTAMP", convert_datetime)

# ==================== DATABASE HELPERS ====================

def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database tables"""
    db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    cursor = db.cursor()
    
    # Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price_per_unit REAL NOT NULL,
            unit TEXT DEFAULT 'piece',
            stock_quantity INTEGER DEFAULT 0,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Employees table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            salary REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            joined_date DATE DEFAULT CURRENT_DATE
        )
    ''')
    
    # Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date DATE NOT NULL,
            status TEXT DEFAULT 'Present',
            shift TEXT DEFAULT 'Day',
            notes TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees (id),
            UNIQUE (employee_id, date)
        )
    ''')
    
    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            customer_address TEXT,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Pending',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            delivery_date DATE,
            notes TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Inventory logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            assigned_to INTEGER,
            order_id TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Not Started',
            progress INTEGER DEFAULT 0,
            due_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assigned_to) REFERENCES employees (id)
        )
    ''')
    
    # Salary records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS salary_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            gross_salary REAL DEFAULT 0,
            deductions REAL DEFAULT 0,
            allowances REAL DEFAULT 0,
            net_salary REAL DEFAULT 0,
            paid INTEGER DEFAULT 0,
            FOREIGN KEY (employee_id) REFERENCES employees (id),
            UNIQUE (employee_id, month, year)
        )
    ''')
    
    # Task rotation log table - tracks assignment history for fair rotation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_rotation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            task_type TEXT DEFAULT 'General',
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')
    
    # Users table for authentication
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Employee',
            employee_id INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')
    
    # Check if default admin user exists
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        # Create default users
        admin_password = hash_password('admin123')
        cursor.execute('''
            INSERT INTO users (username, password, role) VALUES (?, ?, ?)
        ''', ('admin', admin_password, 'Manager'))
        cursor.execute('''
            INSERT INTO users (username, password, role) VALUES (?, ?, ?)
        ''', ('supervisor', hash_password('super123'), 'Supervisor'))
        # Employee user will be linked after sample employees are created
    
    # Check if sample data exists
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        # Insert sample products
        products = [
            ('Red Bricks (Standard)', 'Bricks', 8, 'piece', 50000, 'Standard red clay bricks'),
            ('Fly Ash Bricks', 'Bricks', 6, 'piece', 30000, 'Eco-friendly fly ash bricks'),
            ('Cement Blocks', 'Blocks', 45, 'piece', 10000, 'Heavy duty cement blocks'),
            ('Paver Blocks', 'Blocks', 35, 'piece', 15000, 'Interlocking paver blocks'),
            ('Fire Bricks', 'Bricks', 25, 'piece', 5000, 'Heat resistant fire bricks'),
        ]
        cursor.executemany('''
            INSERT INTO products (name, category, price_per_unit, unit, stock_quantity, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', products)
        
        # Insert sample employees
        employees = [
            ('BRK020', 'Murugan', 'Security', '9876543210', 'Chennai', 12000, 1),
            ('BRK019', 'Kumar', 'Loader', '9876543211', 'Chennai', 22000, 0),
            ('BRK018', 'Dinesh', 'Loader', '9876543212', 'Chennai', 16000, 1),
            ('BRK017', 'Vinoth', 'Security', '9876543213', 'Chennai', 25000, 1),
            ('BRK016', 'Illa', 'Supervisor', '9876543214', 'Chennai', 14000, 0),
            ('BRK015', 'Saravanan', 'Quality Checker', '9876543215', 'Chennai', 12000, 1),
            ('BRK014', 'Gopi', 'Supervisor', '9876543216', 'Chennai', 16000, 1),
            ('BRK013', 'Selvam', 'Truck Driver', '9876543217', 'Chennai', 17000, 1),
            ('BRK012', 'Ramesh', 'Worker', '9876543218', 'Chennai', 15000, 1),
            ('BRK011', 'Ravi', 'Worker', '9876543219', 'Chennai', 15000, 1),
        ]
        cursor.executemany('''
            INSERT INTO employees (employee_id, name, role, phone, address, salary, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', employees)
        
        # Now create default employee user linked to Ravi (BRK011)
        ravi_id = cursor.execute("SELECT id FROM employees WHERE employee_id = 'BRK011'").fetchone()[0]
        cursor.execute('''
            INSERT INTO users (username, password, role, employee_id) VALUES (?, ?, ?, ?)
        ''', ('employee', hash_password('emp123'), 'Employee', ravi_id))
    
    db.commit()
    db.close()


# ==================== HELPER FUNCTIONS ====================

def format_date(d):
    """Format date as dd-mm-yyyy"""
    if d:
        if isinstance(d, str):
            try:
                d = datetime.strptime(d, '%Y-%m-%d').date()
            except ValueError:
                return d
        return d.strftime('%d-%m-%Y')
    return ''

def parse_date(date_str):
    """Parse date from various formats"""
    if date_str:
        for fmt in ['%d-%m-%Y', '%Y-%m-%d']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
    return None

def format_currency(amount):
    """Format amount in rupees/lakhs"""
    if amount is None:
        amount = 0
    if amount >= 100000:
        return f"₹{amount/100000:.2f}L"
    elif amount >= 1000:
        return f"₹{amount/1000:.2f}K"
    return f"₹{amount:.2f}"

def generate_order_number():
    """Generate unique order number"""
    db = get_db()
    cursor = db.execute("SELECT order_number FROM orders WHERE order_number LIKE 'ORD%'")
    rows = cursor.fetchall()
    if rows:
        max_num = 1000
        for row in rows:
            try:
                num = int(row['order_number'].replace('ORD', ''))
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
        return f"ORD{max_num + 1}"
    else:
        return "ORD1001"

def generate_employee_id():
    """Generate unique employee ID"""
    db = get_db()
    # Find the maximum employee ID number to avoid conflicts
    cursor = db.execute("SELECT employee_id FROM employees WHERE employee_id LIKE 'BRK%'")
    rows = cursor.fetchall()
    if rows:
        max_num = 0
        for row in rows:
            try:
                num = int(row['employee_id'].replace('BRK', ''))
                if num > max_num:
                    max_num = num
            except ValueError:
                continue
        return f"BRK{max_num + 1:03d}"
    else:
        return "BRK001"


# Register template filters
app.jinja_env.filters['format_date'] = format_date
app.jinja_env.filters['format_currency'] = format_currency
app.jinja_env.filters['indian_currency'] = format_indian_currency
app.jinja_env.filters['format_inr'] = format_indian_currency


# ==================== AUTHENTICATION ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'Employee')
        
        if not username or not password:
            flash('Please enter username and password.', 'danger')
            return render_template('login.html')
        
        db = get_db()
        user = db.execute('''
            SELECT * FROM users WHERE username = ? AND is_active = 1
        ''', (username,)).fetchone()
        
        if user and user['password'] == hash_password(password):
            if user['role'] != role:
                flash(f'Invalid role selected. You are registered as {user["role"]}.', 'danger')
                return render_template('login.html')
            
            session.permanent = True  # Make session persistent
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['role']
            session['employee_id'] = user['employee_id']
            
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register new employee account"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    db = get_db()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Validation
        if not username or not password or not name:
            flash('Username, password, and name are required.', 'danger')
            return render_template('register.html')
        
        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        
        # Check if username exists
        existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            flash('Username already taken. Please choose another.', 'danger')
            return render_template('register.html')
        
        # Create employee record first
        employee_id = generate_employee_id()
        db.execute('''
            INSERT INTO employees (employee_id, name, role, phone, salary, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (employee_id, name, 'Worker', phone, 0, 1))
        
        emp_row = db.execute('SELECT id FROM employees WHERE employee_id = ?', (employee_id,)).fetchone()
        
        # Create user account (always as Employee role)
        db.execute('''
            INSERT INTO users (username, password, role, employee_id, is_active)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hash_password(password), 'Employee', emp_row['id'], 1))
        
        db.commit()
        flash(f'Account created successfully! Your Employee ID is {employee_id}. Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


# ==================== EMPLOYEE SELF-SERVICE ROUTES ====================

@app.route('/my-profile')
@login_required
def my_profile():
    """Employee's own profile view"""
    db = get_db()
    employee_id = session.get('employee_id')
    
    if not employee_id:
        flash('No employee profile linked to your account.', 'warning')
        return redirect(url_for('dashboard'))
    
    employee = db.execute('SELECT * FROM employees WHERE id = ?', (employee_id,)).fetchone()
    
    if not employee:
        flash('Employee profile not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get recent tasks
    tasks = db.execute('''
        SELECT * FROM tasks WHERE assigned_to = ? ORDER BY created_at DESC LIMIT 5
    ''', (employee_id,)).fetchall()
    
    return render_template('my_profile.html', employee=employee, tasks=tasks)


@app.route('/my-attendance')
@login_required
def my_attendance():
    """Employee's own attendance view"""
    db = get_db()
    employee_id = session.get('employee_id')
    
    if not employee_id:
        flash('No employee profile linked to your account.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Get attendance records for current month
    current_month = date.today().strftime('%Y-%m')
    records = db.execute('''
        SELECT * FROM attendance 
        WHERE employee_id = ? AND strftime('%Y-%m', date) = ?
        ORDER BY date DESC
    ''', (employee_id, current_month)).fetchall()
    
    # Calculate stats
    present_count = sum(1 for r in records if r['status'] == 'Present')
    absent_count = sum(1 for r in records if r['status'] == 'Absent')
    half_day_count = sum(1 for r in records if r['status'] == 'Half-day')
    
    return render_template('my_attendance.html', 
                         records=records,
                         present_count=present_count,
                         absent_count=absent_count,
                         half_day_count=half_day_count)


# ==================== ROUTES ====================

@app.route('/')
def dashboard():
    db = get_db()
    
    total_employees = db.execute('SELECT COUNT(*) FROM employees WHERE is_active = 1').fetchone()[0]
    total_products = db.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    total_orders = db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    pending_orders = db.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'").fetchone()[0]
    
    today = date.today().strftime('%Y-%m-%d')
    present_today = db.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Present'", (today,)).fetchone()[0]
    
    recent_orders = db.execute('''
        SELECT o.*, p.name as product_name FROM orders o 
        JOIN products p ON o.product_id = p.id 
        ORDER BY o.order_date DESC LIMIT 5
    ''').fetchall()
    
    low_stock = db.execute('SELECT * FROM products WHERE stock_quantity < 100').fetchall()
    
    pending_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status != 'Completed'").fetchone()[0]
    
    inventory_value = db.execute('SELECT SUM(price_per_unit * stock_quantity) FROM products').fetchone()[0] or 0
    
    return render_template('dashboard.html', 
                         total_employees=total_employees,
                         total_products=total_products,
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         present_today=present_today,
                         recent_orders=recent_orders,
                         low_stock=low_stock,
                         pending_tasks=pending_tasks,
                         inventory_value=inventory_value)


# ==================== PRODUCTS ====================

@app.route('/products')
def products():
    db = get_db()
    all_products = db.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    return render_template('products.html', products=all_products)

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        db = get_db()
        db.execute('''
            INSERT INTO products (name, category, price_per_unit, unit, stock_quantity, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            request.form['name'],
            request.form['category'],
            float(request.form['price']),
            request.form['unit'],
            int(request.form['stock']),
            request.form.get('description', '')
        ))
        db.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products'))
    return render_template('product_form.html', product=None)

@app.route('/products/edit/<int:id>', methods=['GET', 'POST'])
def edit_product(id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('products'))
    
    if request.method == 'POST':
        db.execute('''
            UPDATE products SET name=?, category=?, price_per_unit=?, unit=?, stock_quantity=?, description=?
            WHERE id=?
        ''', (
            request.form['name'],
            request.form['category'],
            float(request.form['price']),
            request.form['unit'],
            int(request.form['stock']),
            request.form.get('description', ''),
            id
        ))
        db.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('products'))
    return render_template('product_form.html', product=product)

@app.route('/products/delete/<int:id>')
def delete_product(id):
    db = get_db()
    db.execute('DELETE FROM products WHERE id = ?', (id,))
    db.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('products'))


# ==================== ORDERS ====================

@app.route('/orders')
def orders():
    db = get_db()
    status_filter = request.args.get('status', '')
    
    if status_filter:
        all_orders = db.execute('''
            SELECT o.*, p.name as product_name FROM orders o 
            JOIN products p ON o.product_id = p.id 
            WHERE o.status = ?
            ORDER BY o.order_date DESC
        ''', (status_filter,)).fetchall()
    else:
        all_orders = db.execute('''
            SELECT o.*, p.name as product_name FROM orders o 
            JOIN products p ON o.product_id = p.id 
            ORDER BY o.order_date DESC
        ''').fetchall()
    
    return render_template('orders.html', orders=all_orders, current_status=status_filter)

@app.route('/orders/add', methods=['GET', 'POST'])
def add_order():
    db = get_db()
    products_list = db.execute('SELECT * FROM products').fetchall()
    
    if request.method == 'POST':
        product = db.execute('SELECT * FROM products WHERE id = ?', (int(request.form['product_id']),)).fetchone()
        quantity = int(request.form['quantity'])
        total = product['price_per_unit'] * quantity
        
        delivery_date = parse_date(request.form.get('delivery_date', ''))
        
        db.execute('''
            INSERT INTO orders (order_number, customer_name, customer_phone, customer_address, 
                              product_id, quantity, total_amount, status, delivery_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            generate_order_number(),
            request.form['customer_name'],
            request.form.get('customer_phone', ''),
            request.form.get('customer_address', ''),
            product['id'],
            quantity,
            total,
            request.form.get('status', 'Pending'),
            delivery_date,
            request.form.get('notes', '')
        ))
        db.commit()
        flash('Order created successfully!', 'success')
        return redirect(url_for('orders'))
    
    return render_template('order_form.html', order=None, products=products_list)

@app.route('/orders/edit/<int:id>', methods=['GET', 'POST'])
def edit_order(id):
    db = get_db()
    order = db.execute('SELECT * FROM orders WHERE id = ?', (id,)).fetchone()
    products_list = db.execute('SELECT * FROM products').fetchall()
    
    if not order:
        flash('Order not found', 'danger')
        return redirect(url_for('orders'))
    
    if request.method == 'POST':
        product = db.execute('SELECT * FROM products WHERE id = ?', (int(request.form['product_id']),)).fetchone()
        quantity = int(request.form['quantity'])
        total = product['price_per_unit'] * quantity
        
        delivery_date = parse_date(request.form.get('delivery_date', ''))
        
        db.execute('''
            UPDATE orders SET customer_name=?, customer_phone=?, customer_address=?,
                            product_id=?, quantity=?, total_amount=?, status=?, delivery_date=?, notes=?
            WHERE id=?
        ''', (
            request.form['customer_name'],
            request.form.get('customer_phone', ''),
            request.form.get('customer_address', ''),
            product['id'],
            quantity,
            total,
            request.form.get('status', 'Pending'),
            delivery_date,
            request.form.get('notes', ''),
            id
        ))
        db.commit()
        flash('Order updated successfully!', 'success')
        return redirect(url_for('orders'))
    
    return render_template('order_form.html', order=order, products=products_list)

@app.route('/orders/view/<int:id>')
def view_order(id):
    db = get_db()
    order = db.execute('''
        SELECT o.*, p.name as product_name, p.price_per_unit FROM orders o 
        JOIN products p ON o.product_id = p.id 
        WHERE o.id = ?
    ''', (id,)).fetchone()
    
    if not order:
        flash('Order not found', 'danger')
        return redirect(url_for('orders'))
    
    return render_template('order_view.html', order=order)

@app.route('/orders/delete/<int:id>')
def delete_order(id):
    db = get_db()
    db.execute('DELETE FROM orders WHERE id = ?', (id,))
    db.commit()
    flash('Order deleted successfully!', 'success')
    return redirect(url_for('orders'))


# ==================== INVENTORY ====================

@app.route('/inventory')
def inventory():
    db = get_db()
    products_list = db.execute('SELECT * FROM products').fetchall()
    logs = db.execute('''
        SELECT l.*, p.name as product_name FROM inventory_logs l
        JOIN products p ON l.product_id = p.id
        ORDER BY l.timestamp DESC LIMIT 20
    ''').fetchall()
    return render_template('inventory.html', products=products_list, logs=logs)

@app.route('/inventory/update/<int:id>', methods=['POST'])
def update_inventory(id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    
    change_type = request.form['change_type']
    quantity = int(request.form['quantity'])
    reason = request.form.get('reason', '')
    
    if change_type == 'Addition':
        new_stock = product['stock_quantity'] + quantity
    else:
        new_stock = max(0, product['stock_quantity'] - quantity)
    
    db.execute('UPDATE products SET stock_quantity = ? WHERE id = ?', (new_stock, id))
    db.execute('''
        INSERT INTO inventory_logs (product_id, change_type, quantity, reason)
        VALUES (?, ?, ?, ?)
    ''', (id, change_type, quantity, reason))
    db.commit()
    
    flash('Inventory updated successfully!', 'success')
    return redirect(url_for('inventory'))


# ==================== EMPLOYEES ====================

@app.route('/employees')
def employees():
    db = get_db()
    all_employees = db.execute('SELECT * FROM employees ORDER BY id DESC').fetchall()
    return render_template('employees.html', employees=all_employees)

@app.route('/employees/add', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        db = get_db()
        db.execute('''
            INSERT INTO employees (employee_id, name, role, phone, address, salary, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            generate_employee_id(),
            request.form['name'],
            request.form['role'],
            request.form.get('phone', ''),
            request.form.get('address', ''),
            float(request.form.get('salary', 0)),
            1 if request.form.get('is_active') == 'on' else 0
        ))
        db.commit()
        flash('Employee added successfully!', 'success')
        return redirect(url_for('employees'))
    return render_template('employee_form.html', employee=None)

@app.route('/employees/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    db = get_db()
    employee = db.execute('SELECT * FROM employees WHERE id = ?', (id,)).fetchone()
    
    if not employee:
        flash('Employee not found', 'danger')
        return redirect(url_for('employees'))
    
    if request.method == 'POST':
        db.execute('''
            UPDATE employees SET name=?, role=?, phone=?, address=?, salary=?, is_active=?
            WHERE id=?
        ''', (
            request.form['name'],
            request.form['role'],
            request.form.get('phone', ''),
            request.form.get('address', ''),
            float(request.form.get('salary', 0)),
            1 if request.form.get('is_active') == 'on' else 0,
            id
        ))
        db.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employees'))
    
    return render_template('employee_form.html', employee=employee)

@app.route('/employees/view/<int:id>')
def view_employee(id):
    db = get_db()
    employee = db.execute('SELECT * FROM employees WHERE id = ?', (id,)).fetchone()
    
    if not employee:
        flash('Employee not found', 'danger')
        return redirect(url_for('employees'))
    
    return render_template('employee_view.html', employee=employee)

@app.route('/employees/delete/<int:id>')
def delete_employee(id):
    db = get_db()
    db.execute('DELETE FROM employees WHERE id = ?', (id,))
    db.commit()
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('employees'))


# ==================== ATTENDANCE ====================

@app.route('/employees/attendance')
def attendance_registry():
    db = get_db()
    selected_date = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    
    try:
        attendance_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        attendance_date = date.today()
    
    employees_list = db.execute('SELECT * FROM employees WHERE is_active = 1').fetchall()
    
    attendance_records = {}
    for record in db.execute('SELECT * FROM attendance WHERE date = ?', (attendance_date,)).fetchall():
        attendance_records[record['employee_id']] = record
    
    return render_template('attendance_registry.html', 
                         employees=employees_list, 
                         attendance_records=attendance_records,
                         selected_date=attendance_date)

@app.route('/employees/attendance/save', methods=['POST'])
def save_attendance():
    db = get_db()
    attendance_date = parse_date(request.form.get('attendance_date', '')) or date.today()
    
    employees_list = db.execute('SELECT * FROM employees WHERE is_active = 1').fetchall()
    
    for emp in employees_list:
        status = request.form.get(f'status_{emp["id"]}', 'Present')
        shift = request.form.get(f'shift_{emp["id"]}', 'Day')
        notes = request.form.get(f'notes_{emp["id"]}', '')
        
        existing = db.execute('SELECT id FROM attendance WHERE employee_id = ? AND date = ?', 
                             (emp['id'], attendance_date)).fetchone()
        
        if existing:
            db.execute('''
                UPDATE attendance SET status=?, shift=?, notes=? 
                WHERE employee_id=? AND date=?
            ''', (status, shift, notes, emp['id'], attendance_date))
        else:
            db.execute('''
                INSERT INTO attendance (employee_id, date, status, shift, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (emp['id'], attendance_date, status, shift, notes))
    
    db.commit()
    flash('Attendance saved successfully!', 'success')
    return redirect(url_for('attendance_registry', date=attendance_date.strftime('%Y-%m-%d')))

@app.route('/employees/attendance/records')
def attendance_records():
    db = get_db()
    selected_date = request.args.get('date', '')
    
    if selected_date:
        try:
            filter_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            records = db.execute('''
                SELECT a.*, e.name as employee_name FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                WHERE a.date = ?
            ''', (filter_date,)).fetchall()
        except ValueError:
            records = db.execute('''
                SELECT a.*, e.name as employee_name FROM attendance a
                JOIN employees e ON a.employee_id = e.id
                ORDER BY a.date DESC LIMIT 50
            ''').fetchall()
    else:
        records = db.execute('''
            SELECT a.*, e.name as employee_name FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            ORDER BY a.date DESC LIMIT 50
        ''').fetchall()
    
    return render_template('attendance_records.html', records=records, selected_date=selected_date)

@app.route('/employees/attendance/mark-all', methods=['POST'])
def mark_all_attendance():
    db = get_db()
    attendance_date = parse_date(request.form.get('attendance_date', '')) or date.today()
    status = request.form.get('status', 'Present')
    
    employees_list = db.execute('SELECT * FROM employees WHERE is_active = 1').fetchall()
    
    for emp in employees_list:
        existing = db.execute('SELECT id FROM attendance WHERE employee_id = ? AND date = ?', 
                             (emp['id'], attendance_date)).fetchone()
        
        if existing:
            db.execute('UPDATE attendance SET status = ? WHERE employee_id = ? AND date = ?',
                      (status, emp['id'], attendance_date))
        else:
            db.execute('''
                INSERT INTO attendance (employee_id, date, status, shift)
                VALUES (?, ?, ?, ?)
            ''', (emp['id'], attendance_date, status, 'Day'))
    
    db.commit()
    flash(f'All employees marked as {status}!', 'success')
    return redirect(url_for('attendance_registry', date=attendance_date.strftime('%Y-%m-%d')))


# ==================== TASKS ====================

@app.route('/employees/tasks')
def tasks():
    db = get_db()
    status_filter = request.args.get('status', '')
    
    if status_filter:
        all_tasks = db.execute('''
            SELECT t.*, e.name as employee_name FROM tasks t
            LEFT JOIN employees e ON t.assigned_to = e.id
            WHERE t.status = ?
            ORDER BY t.created_at DESC
        ''', (status_filter,)).fetchall()
    else:
        all_tasks = db.execute('''
            SELECT t.*, e.name as employee_name FROM tasks t
            LEFT JOIN employees e ON t.assigned_to = e.id
            ORDER BY t.created_at DESC
        ''').fetchall()
    
    return render_template('tasks.html', tasks=all_tasks, current_status=status_filter)

@app.route('/employees/tasks/add', methods=['GET', 'POST'])
def add_task():
    db = get_db()
    employees_list = db.execute('SELECT * FROM employees WHERE is_active = 1').fetchall()
    
    if request.method == 'POST':
        due_date = parse_date(request.form.get('due_date', ''))
        assigned_to = request.form.get('assigned_to')
        order_id = request.form.get('order_id', '').strip() or None
        
        db.execute('''
            INSERT INTO tasks (title, description, assigned_to, order_id, priority, status, progress, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['title'],
            request.form.get('description', ''),
            int(assigned_to) if assigned_to else None,
            order_id,
            request.form.get('priority', 'Medium'),
            request.form.get('status', 'Not Started'),
            int(request.form.get('progress', 0)),
            due_date
        ))
        db.commit()
        flash('Task created successfully!', 'success')
        return redirect(url_for('tasks'))
    
    return render_template('task_form.html', task=None, employees=employees_list)

@app.route('/employees/tasks/edit/<int:id>', methods=['GET', 'POST'])
def edit_task(id):
    db = get_db()
    task = db.execute('SELECT * FROM tasks WHERE id = ?', (id,)).fetchone()
    employees_list = db.execute('SELECT * FROM employees WHERE is_active = 1').fetchall()
    
    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('tasks'))
    
    if request.method == 'POST':
        due_date = parse_date(request.form.get('due_date', ''))
        assigned_to = request.form.get('assigned_to')
        order_id = request.form.get('order_id', '').strip() or None
        
        db.execute('''
            UPDATE tasks SET title=?, description=?, assigned_to=?, order_id=?, priority=?, status=?, progress=?, due_date=?
            WHERE id=?
        ''', (
            request.form['title'],
            request.form.get('description', ''),
            int(assigned_to) if assigned_to else None,
            order_id,
            request.form.get('priority', 'Medium'),
            request.form.get('status', 'Not Started'),
            int(request.form.get('progress', 0)),
            due_date,
            id
        ))
        db.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('tasks'))
    
    return render_template('task_form.html', task=task, employees=employees_list)

@app.route('/employees/tasks/delete/<int:id>')
def delete_task(id):
    db = get_db()
    db.execute('DELETE FROM tasks WHERE id = ?', (id,))
    db.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('tasks'))


# ==================== TASK ROTATION MATRIX ====================

@app.route('/employees/tasks/rotation')
def task_rotation():
    """Display task rotation matrix showing fair distribution"""
    db = get_db()
    
    # Get all active employees
    employees_list = db.execute('''
        SELECT * FROM employees WHERE is_active = 1 ORDER BY name
    ''').fetchall()
    
    # Get task types (priorities as task categories)
    task_types = ['Loading', 'Delivery', 'Quality Check', 'Packaging', 'Maintenance', 'General']
    
    # Build rotation matrix - count tasks per employee per type (last 7 days - weekly rotation)
    rotation_matrix = []
    for emp in employees_list:
        emp_data = {
            'id': emp['id'],
            'name': emp['name'],
            'role': emp['role'],
            'counts': {},
            'total': 0,
            'last_assigned': None
        }
        
        # Count tasks by type from rotation log (weekly window)
        for task_type in task_types:
            count = db.execute('''
                SELECT COUNT(*) FROM task_rotation_log 
                WHERE employee_id = ? AND task_type = ?
                AND assigned_at >= datetime('now', '-7 days')
            ''', (emp['id'], task_type)).fetchone()[0]
            emp_data['counts'][task_type] = count
            emp_data['total'] += count
        
        # Also count from actual tasks table
        task_count = db.execute('''
            SELECT COUNT(*) FROM tasks WHERE assigned_to = ?
        ''', (emp['id'],)).fetchone()[0]
        emp_data['task_count'] = task_count
        
        # Get last assignment date
        last = db.execute('''
            SELECT MAX(assigned_at) FROM task_rotation_log WHERE employee_id = ?
        ''', (emp['id'],)).fetchone()[0]
        emp_data['last_assigned'] = last
        
        rotation_matrix.append(emp_data)
    
    # Sort by total assignments (ascending) to show who should be next
    rotation_matrix.sort(key=lambda x: (x['total'], x['last_assigned'] or ''))
    
    # Get suggested next employee for each task type
    suggestions = {}
    for task_type in task_types:
        # Find employee with least assignments of this type
        min_count = float('inf')
        suggested = None
        for emp in rotation_matrix:
            if emp['counts'].get(task_type, 0) < min_count:
                min_count = emp['counts'].get(task_type, 0)
                suggested = emp
        suggestions[task_type] = suggested
    
    return render_template('task_rotation.html', 
                         employees=employees_list,
                         rotation_matrix=rotation_matrix,
                         task_types=task_types,
                         suggestions=suggestions)


@app.route('/api/task-rotation/suggest')
def suggest_task_assignment():
    """API to suggest next employee for a task based on rotation"""
    db = get_db()
    task_type = request.args.get('type', 'General')
    
    # Get active employees with their assignment counts (weekly window)
    employees = db.execute('''
        SELECT e.id, e.name, e.role,
               COALESCE((SELECT COUNT(*) FROM task_rotation_log 
                        WHERE employee_id = e.id AND task_type = ?
                        AND assigned_at >= datetime('now', '-7 days')), 0) as type_count,
               COALESCE((SELECT COUNT(*) FROM task_rotation_log 
                        WHERE employee_id = e.id
                        AND assigned_at >= datetime('now', '-7 days')), 0) as total_count,
               (SELECT MAX(assigned_at) FROM task_rotation_log WHERE employee_id = e.id) as last_assigned
        FROM employees e
        WHERE e.is_active = 1
        ORDER BY type_count ASC, total_count ASC, last_assigned ASC NULLS FIRST
    ''', (task_type,)).fetchall()
    
    if not employees:
        return jsonify({'error': 'No active employees found'}), 404
    
    # First employee is the best candidate
    suggested = employees[0]
    
    return jsonify({
        'suggested_employee': {
            'id': suggested['id'],
            'name': suggested['name'],
            'role': suggested['role'],
            'type_assignments': suggested['type_count'],
            'total_assignments': suggested['total_count']
        },
        'all_candidates': [{
            'id': e['id'],
            'name': e['name'],
            'role': e['role'],
            'type_assignments': e['type_count'],
            'total_assignments': e['total_count']
        } for e in employees[:5]]
    })


@app.route('/api/task-rotation/log', methods=['POST'])
def log_task_assignment():
    """Log a task assignment for rotation tracking"""
    db = get_db()
    data = request.get_json() if request.is_json else request.form
    
    employee_id = data.get('employee_id')
    task_type = data.get('task_type', 'General')
    
    if not employee_id:
        return jsonify({'error': 'Employee ID required'}), 400
    
    db.execute('''
        INSERT INTO task_rotation_log (employee_id, task_type)
        VALUES (?, ?)
    ''', (int(employee_id), task_type))
    db.commit()
    
    return jsonify({'success': True, 'message': 'Assignment logged'})


@app.route('/api/task-rotation/matrix')
def get_rotation_matrix():
    """API to get the full rotation matrix data"""
    db = get_db()
    
    task_types = ['Loading', 'Delivery', 'Quality Check', 'Packaging', 'Maintenance', 'General']
    
    employees = db.execute('''
        SELECT * FROM employees WHERE is_active = 1 ORDER BY name
    ''').fetchall()
    
    matrix = []
    for emp in employees:
        emp_data = {
            'id': emp['id'],
            'name': emp['name'],
            'role': emp['role'],
            'assignments': {}
        }
        
        for task_type in task_types:
            count = db.execute('''
                SELECT COUNT(*) FROM task_rotation_log 
                WHERE employee_id = ? AND task_type = ?
                AND assigned_at >= datetime('now', '-7 days')
            ''', (emp['id'], task_type)).fetchone()[0]
            emp_data['assignments'][task_type] = count
        
        matrix.append(emp_data)
    
    return jsonify({
        'task_types': task_types,
        'matrix': matrix
    })


# ==================== SALARY ====================

@app.route('/employees/salary')
def salary():
    db = get_db()
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    
    records = db.execute('''
        SELECT s.*, e.employee_id as emp_id, e.name, e.role FROM salary_records s
        JOIN employees e ON s.employee_id = e.id
        WHERE s.month = ? AND s.year = ?
    ''', (month, year)).fetchall()
    
    employees_list = db.execute('SELECT * FROM employees WHERE is_active = 1').fetchall()
    
    return render_template('salary.html', records=records, employees=employees_list, 
                         current_month=month, current_year=year)

@app.route('/employees/salary/generate', methods=['POST'])
def generate_salary():
    db = get_db()
    month = int(request.form.get('month', date.today().month))
    year = int(request.form.get('year', date.today().year))
    
    employees_list = db.execute('SELECT * FROM employees WHERE is_active = 1').fetchall()
    
    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]
    
    for emp in employees_list:
        existing = db.execute('''
            SELECT id FROM salary_records WHERE employee_id = ? AND month = ? AND year = ?
        ''', (emp['id'], month, year)).fetchone()
        
        if not existing:
            # Count present days
            present_count = db.execute('''
                SELECT COUNT(*) FROM attendance 
                WHERE employee_id = ? AND status IN ('Present', 'Half-day')
                AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
            ''', (emp['id'], f'{month:02d}', str(year))).fetchone()[0]
            
            half_day_count = db.execute('''
                SELECT COUNT(*) FROM attendance 
                WHERE employee_id = ? AND status = 'Half-day'
                AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
            ''', (emp['id'], f'{month:02d}', str(year))).fetchone()[0]
            
            effective_days = present_count - (half_day_count * 0.5)
            daily_rate = emp['salary'] / days_in_month if days_in_month > 0 else 0
            gross = daily_rate * effective_days
            
            db.execute('''
                INSERT INTO salary_records (employee_id, month, year, gross_salary, deductions, net_salary)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (emp['id'], month, year, gross, 0, gross))
    
    db.commit()
    flash('Salary records generated!', 'success')
    return redirect(url_for('salary', month=month, year=year))

@app.route('/employees/salary/report')
def salary_report():
    db = get_db()
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    
    records = db.execute('''
        SELECT s.*, e.employee_id as emp_id, e.name, e.role FROM salary_records s
        JOIN employees e ON s.employee_id = e.id
        WHERE s.month = ? AND s.year = ?
    ''', (month, year)).fetchall()
    
    total_gross = sum(r['gross_salary'] for r in records)
    total_deductions = sum(r['deductions'] for r in records)
    total_net = sum(r['net_salary'] for r in records)
    
    from calendar import month_name
    month_str = month_name[month]
    
    return render_template('salary_report.html', 
                         records=records,
                         month=month, year=year, month_name=month_str,
                         total_gross=total_gross, total_deductions=total_deductions,
                         total_net=total_net)

@app.route('/employees/salary/download-csv')
def download_salary_csv():
    db = get_db()
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    
    records = db.execute('''
        SELECT s.*, e.employee_id as emp_id, e.name, e.role FROM salary_records s
        JOIN employees e ON s.employee_id = e.id
        WHERE s.month = ? AND s.year = ?
    ''', (month, year)).fetchall()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Employee ID', 'Name', 'Role', 'Gross Salary', 'Deductions', 'Net Salary', 'Status'])
    
    for r in records:
        writer.writerow([
            r['emp_id'],
            r['name'],
            r['role'],
            f"{r['gross_salary']:.2f}",
            f"{r['deductions']:.2f}",
            f"{r['net_salary']:.2f}",
            'Paid' if r['paid'] else 'Pending'
        ])
    
    output.seek(0)
    from calendar import month_name
    filename = f"salary_report_{month_name[month]}_{year}.csv"
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# ==================== PAYROLL ====================

@app.route('/employees/payroll')
def payroll():
    db = get_db()
    month = int(request.args.get('month', date.today().month))
    year = int(request.args.get('year', date.today().year))
    
    records = db.execute('''
        SELECT s.*, e.employee_id as emp_id, e.name, e.role FROM salary_records s
        JOIN employees e ON s.employee_id = e.id
        WHERE s.month = ? AND s.year = ?
        ORDER BY e.name
    ''', (month, year)).fetchall()
    
    employees_list = db.execute('SELECT * FROM employees WHERE is_active = 1 ORDER BY name').fetchall()
    
    return render_template('payroll.html', records=records, employees=employees_list, 
                         current_month=month, current_year=year)

@app.route('/employees/payroll/view/<int:id>')
def view_payroll(id):
    db = get_db()
    record = db.execute('''
        SELECT s.*, e.employee_id as emp_id, e.name, e.role, e.salary as base_salary 
        FROM salary_records s
        JOIN employees e ON s.employee_id = e.id
        WHERE s.id = ?
    ''', (id,)).fetchone()
    
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    
    return jsonify({
        'id': record['id'],
        'emp_id': record['emp_id'],
        'name': record['name'],
        'role': record['role'],
        'month': record['month'],
        'year': record['year'],
        'gross_salary': record['gross_salary'],
        'deductions': record['deductions'],
        'allowances': record['allowances'] if record['allowances'] else 0,
        'net_salary': record['net_salary'],
        'paid': record['paid'],
        'base_salary': record['base_salary']
    })

@app.route('/employees/payroll/update/<int:id>', methods=['POST'])
def update_payroll(id):
    db = get_db()
    data = request.get_json() if request.is_json else request.form
    
    gross = float(data.get('gross_salary', 0))
    deductions = float(data.get('deductions', 0))
    allowances = float(data.get('allowances', 0))
    net_salary = gross - deductions + allowances
    paid = 1 if data.get('paid') in [True, 'true', '1', 1, 'on'] else 0
    
    db.execute('''
        UPDATE salary_records 
        SET gross_salary=?, deductions=?, allowances=?, net_salary=?, paid=?
        WHERE id=?
    ''', (gross, deductions, allowances, net_salary, paid, id))
    db.commit()
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Payroll updated successfully'})
    
    flash('Payroll record updated!', 'success')
    return redirect(url_for('payroll'))

@app.route('/employees/payroll/generate', methods=['POST'])
def generate_payroll():
    db = get_db()
    data = request.get_json() if request.is_json else request.form
    
    month = int(data.get('month', date.today().month))
    year = int(data.get('year', date.today().year))
    employee_id = data.get('employee_id', '')
    
    # Handle 'all', empty string, or None - all mean "all employees"
    if not employee_id or employee_id == 'all' or employee_id == '':
        employees_list = db.execute('SELECT * FROM employees WHERE is_active = 1').fetchall()
    else:
        employees_list = db.execute('SELECT * FROM employees WHERE id = ?', (int(employee_id),)).fetchall()
    
    from calendar import monthrange
    days_in_month = monthrange(year, month)[1]
    
    generated_count = 0
    
    for emp in employees_list:
        existing = db.execute('''
            SELECT id FROM salary_records WHERE employee_id = ? AND month = ? AND year = ?
        ''', (emp['id'], month, year)).fetchone()
        
        if not existing:
            # Count present days
            present_count = db.execute('''
                SELECT COUNT(*) FROM attendance 
                WHERE employee_id = ? AND status IN ('Present', 'Half-day')
                AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
            ''', (emp['id'], f'{month:02d}', str(year))).fetchone()[0]
            
            half_day_count = db.execute('''
                SELECT COUNT(*) FROM attendance 
                WHERE employee_id = ? AND status = 'Half-day'
                AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
            ''', (emp['id'], f'{month:02d}', str(year))).fetchone()[0]
            
            effective_days = present_count - (half_day_count * 0.5)
            daily_rate = emp['salary'] / days_in_month if days_in_month > 0 else 0
            gross = daily_rate * effective_days
            
            db.execute('''
                INSERT INTO salary_records (employee_id, month, year, gross_salary, deductions, allowances, net_salary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (emp['id'], month, year, gross, 0, 0, gross))
            generated_count += 1
    
    db.commit()
    
    if request.is_json:
        return jsonify({'success': True, 'message': f'Payroll generated for {generated_count} employees'})
    
    flash(f'Payroll generated for {generated_count} employees!', 'success')
    return redirect(url_for('payroll', month=month, year=year))


# ==================== API ENDPOINTS ====================

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    db = get_db()
    
    today = date.today()
    today_str = today.strftime('%Y-%m-%d')
    
    # Basic counts
    total_employees = db.execute('SELECT COUNT(*) FROM employees WHERE is_active = 1').fetchone()[0]
    present_today = db.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Present'", (today_str,)).fetchone()[0]
    absent_today = db.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Absent'", (today_str,)).fetchone()[0]
    half_day_today = db.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'Half-day'", (today_str,)).fetchone()[0]
    
    # Orders by status
    pending_orders = db.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'").fetchone()[0]
    processing_orders = db.execute("SELECT COUNT(*) FROM orders WHERE status = 'Processing'").fetchone()[0]
    completed_orders = db.execute("SELECT COUNT(*) FROM orders WHERE status = 'Completed'").fetchone()[0]
    
    # Monthly order stats (last 6 months)
    monthly_orders = []
    for i in range(5, -1, -1):
        month_date = today - timedelta(days=i*30)
        month_str = month_date.strftime('%Y-%m')
        count = db.execute('''
            SELECT COUNT(*) FROM orders 
            WHERE strftime('%Y-%m', order_date) = ?
        ''', (month_str,)).fetchone()[0]
        revenue = db.execute('''
            SELECT COALESCE(SUM(total_amount), 0) FROM orders 
            WHERE strftime('%Y-%m', order_date) = ?
        ''', (month_str,)).fetchone()[0]
        monthly_orders.append({
            'month': month_date.strftime('%b'),
            'count': count,
            'revenue': revenue
        })
    
    # Task completion stats
    total_tasks = db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
    completed_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Completed'").fetchone()[0]
    in_progress_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'In Progress'").fetchone()[0]
    
    return jsonify({
        'attendance': {
            'present': present_today,
            'absent': absent_today,
            'half_day': half_day_today,
            'total': total_employees
        },
        'orders': {
            'pending': pending_orders,
            'processing': processing_orders,
            'completed': completed_orders
        },
        'monthly_orders': monthly_orders,
        'tasks': {
            'total': total_tasks,
            'completed': completed_tasks,
            'in_progress': in_progress_tasks
        }
    })


# ==================== INITIALIZE ====================

# Initialize database on startup
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
