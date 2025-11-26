"""
BrickDash - Workforce, Order and Inventory Management System for Brick Industry
Flask Application with SQLite Database (No external dependencies beyond Flask)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, g
import sqlite3
from datetime import datetime, date
import csv
import io
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'brickdash-secret-key-2025'
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'brickdash.db')

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
            net_salary REAL DEFAULT 0,
            paid INTEGER DEFAULT 0,
            FOREIGN KEY (employee_id) REFERENCES employees (id),
            UNIQUE (employee_id, month, year)
        )
    ''')
    
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
        
        db.execute('''
            INSERT INTO tasks (title, description, assigned_to, priority, status, progress, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form['title'],
            request.form.get('description', ''),
            int(assigned_to) if assigned_to else None,
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
        
        db.execute('''
            UPDATE tasks SET title=?, description=?, assigned_to=?, priority=?, status=?, progress=?, due_date=?
            WHERE id=?
        ''', (
            request.form['title'],
            request.form.get('description', ''),
            int(assigned_to) if assigned_to else None,
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


# ==================== INITIALIZE ====================

# Initialize database on startup
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
