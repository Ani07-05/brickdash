# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BrickDash is a comprehensive workforce, order, and inventory management system for the brick industry. It's a Flask-based monolith application using SQLite as the database, with server-rendered HTML templates (Jinja2).

## Development Commands

### Running the Application
```bash
python app.py
```
The app runs on `http://localhost:5000` with debug mode enabled.

### Running Tests
```bash
pytest test_app.py
```
Run tests with verbose output:
```bash
pytest test_app.py -v
```
Run a specific test class:
```bash
pytest test_app.py::TestAuthentication
```
Run a specific test:
```bash
pytest test_app.py::TestAuthentication::test_login_page_loads
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

Dependencies include:
- `Flask>=2.0.0` - Web framework
- `gunicorn>=20.1.0` - WSGI server for production
- `reportlab>=4.0.0` - PDF generation library
- `pytest` - Testing framework (dev dependency)

## Architecture Overview

### Monolithic Structure
All application logic resides in a single `app.py` file (~2050 lines). The application is organized into sections marked by comment headers:

- **Authentication** (lines ~53-78): `@login_required` and `@role_required` decorators for route protection
- **Database Helpers** (lines ~104-386): Connection management, initialization, and schema setup
- **Helper Functions** (lines ~387-464): Utilities like `format_currency()`, `generate_order_number()`, `generate_employee_id()`
- **Routes** grouped by feature: Products, Orders, Inventory, Employees, Attendance, Tasks, Salary, Payroll
- **API Endpoints** (lines ~1789+): JSON endpoints for dynamic interactions

### Database Architecture
SQLite database (`brickdash.db`) with the following core tables:

**Core Tables:**
- `users` - Authentication (Manager, Supervisor, Employee roles)
- `products` - Product catalog with pricing, units, stock
- `employees` - Employee records with roles and contact info
- `orders` - Customer orders with status tracking
- `inventory_logs` - Audit trail for inventory changes
- `attendance` - Daily attendance with shift tracking
- `tasks` - Task assignments with progress tracking
- `salary_records` - Monthly salary calculations
- `task_rotation_log` - Task rotation history

**Inventory Stage System:**
- `inventory_stages` - Three-stage workflow: Forming (1) → Drying (2) → Finishing (3)
- `inventory_batches` - Individual batches in each stage with product_id and units tracking
- `batch_orders` - Links batches to orders for reservation

### Python 3.12+ Date Handling
The app registers custom SQLite adapters/converters for date/datetime objects (lines 80-101) to handle Python 3.12+ compatibility issues. This is critical for proper date serialization.

### Authentication & Authorization
Three role levels:
- **Manager**: Full access to all features
- **Supervisor**: Limited access (can view most data, restricted modifications)
- **Employee**: Self-service only (profile, attendance, tasks)

Routes use `@login_required` and `@role_required(*roles)` decorators for access control.

### Session Management
- Sessions configured for production deployment on Render
- `SECRET_KEY` from environment variable (defaults for local dev)
- Session cookies: HttpOnly, SameSite=Lax, 7-day lifetime
- Secure cookies enabled on HTTPS (Render deployment)

### Key Features

**Inventory Stage Workflow:**
The system tracks bricks through three production stages:
1. **Forming** (capacity: 2000 units)
2. **Drying** (capacity: 1500 units)
3. **Finishing** (capacity: 1000 units)

Batches move through stages and can be reserved for orders. The inventory page displays all stages with batch details.

**Batch Management Operations:**
- **Add Batch** (`/inventory/add-batch`) - Create new batch in a specific stage with auto-generated batch ID (B001, B002, etc.)
- **Transfer Batch** (`/inventory/transfer-batch`) - Move batch between stages
- **Adjust Batch** (`/inventory/adjust-batch`) - Modify batch quantities
- **Reserve Batch** (`/inventory/reserve-batch`) - Link batch to order numbers
- **Delete Batch** (`/inventory/delete-batch/<id>`) - Remove batch from system

**Payroll System:**
Auto-generates salary based on attendance records. Uses a configurable per-day rate to calculate:
- Gross salary = days_present × daily_rate
- Deductions (configurable)
- Net salary = Gross - Deductions

**Task Rotation Matrix:**
Assigns tasks to employees based on rotation schedules. Tracks rotation history in `task_rotation_log`.

**Report Generation:**
- **PDF Inventory Report** (`/inventory/report/pdf`) - Manager-only feature using ReportLab to generate comprehensive PDF inventory reports with branded styling (pink/magenta theme)
- **CSV Salary Export** (`/employees/salary/download-csv`) - Download monthly salary records as CSV files with filename format: `salary_report_{Month}_{Year}.csv`

## Code Patterns

### Database Connection Pattern
```python
db = get_db()  # Gets connection from Flask's g object
cursor = db.execute("SELECT ...")
rows = cursor.fetchall()
db.commit()  # For INSERT/UPDATE/DELETE
```
Database connections are automatically closed via `@app.teardown_appcontext`.

### Form Handling Pattern
Forms are submitted via POST, processed in route handlers, and redirect on success:
```python
if request.method == 'POST':
    # Extract form data
    data = request.form.get('field_name')
    # Validate and insert/update
    db.execute("INSERT INTO ...")
    db.commit()
    flash('Success message', 'success')
    return redirect(url_for('view_name'))
# GET request renders form
return render_template('form.html', data=data)
```

### Date Format Convention
Display format: **dd-mm-yyyy** (e.g., 29-11-2025)
Database format: **YYYY-MM-DD** (ISO format via date adapters)

Use `parse_date()` helper to parse user input from multiple formats.

### Currency Formatting
- `format_indian_currency(amount)`: Returns Indian numbering format (e.g., ₹7,50,253)
- `format_currency(amount)`: Returns abbreviated format (₹1.50L for lakhs, ₹7.50K for thousands)

### Batch ID Generation Pattern
Batch IDs are auto-generated with format `B{number:03d}` (e.g., B001, B002, B123):
```python
last_batch = db.execute("SELECT batch_id FROM inventory_batches WHERE batch_id LIKE 'B%' ORDER BY id DESC LIMIT 1").fetchone()
if last_batch:
    num = int(last_batch['batch_id'].replace('B', ''))
    new_batch_id = f"B{num + 1:03d}"
else:
    new_batch_id = "B001"
```

## Testing

The test suite (`test_app.py`, 289 lines) includes 25 comprehensive tests organized into classes:
- `TestAuthentication` - Login/logout/registration flows for all roles
- `TestPageAccess` - Page load and role-based access restrictions
- Additional tests for API endpoints and utility functions

**Test Fixtures:**
- `client` - Test client with database initialization
- `logged_in_manager` - Pre-authenticated manager session
- `logged_in_supervisor` - Pre-authenticated supervisor session
- `logged_in_employee` - Pre-authenticated employee session

## Templates

Templates use Jinja2 with a `base.html` layout that includes:
- Sidebar navigation (role-based visibility)
- Pink/magenta gradient header
- Flash message display
- Font Awesome icons

All templates extend `base.html` and fill the `{% block content %}` section.

## Production Deployment

The app is configured for deployment on Render:
- `gunicorn` as WSGI server (in requirements.txt)
- Environment-based `SECRET_KEY` configuration
- Session security settings conditional on `RENDER` environment variable
- Host: `0.0.0.0`, Port: `5000`

## Important Notes

- **Single-file application**: All routes, models, and business logic are in `app.py`
- **Auto-initialization**: `init_db()` runs on startup and is idempotent (uses `CREATE TABLE IF NOT EXISTS`)
- **Sample data**: Database includes pre-seeded users (admin/supervisor/employee), products, inventory batches, and stages
- **No ORM**: Uses raw SQLite queries with `sqlite3.Row` for dict-like access
- **SHA256 password hashing**: Uses `hashlib.sha256` (not bcrypt/argon2)
- **PDF generation**: ReportLab is imported conditionally in routes - gracefully handles missing library with flash message
- **Batch operations**: All batch modifications go through dedicated routes (add/transfer/adjust/reserve/delete) that maintain referential integrity with `batch_orders` junction table
