# BrickDash - Brick Industry Management System

A comprehensive workforce, order, and inventory management system designed for the brick industry.

## Features

### Dashboard
- Overview of key metrics (employees, products, orders, inventory)
- Quick actions for common tasks
- Recent orders and low stock alerts

### Products
- Add, edit, and delete products
- Track product categories, prices, and stock
- Support for multiple units (pieces, kg, ton, bag, truck load)

### Orders (Order Book)
- Create and manage customer orders
- Track order status (Pending, Processing, Completed, Cancelled)
- View order details and delivery information
- Filter orders by status

### Inventory
- Real-time stock tracking
- Add/deduct inventory with reason logging
- Activity history for all inventory changes
- Low stock alerts

### Employees
- Employee management with roles
- Employee profiles with contact details
- Active/inactive status tracking

### Attendance
- Daily attendance registry
- Mark all present/absent with one click
- Individual status per employee (Present, Absent, Half-day, Leave)
- Shift tracking (Day/Night)
- View historical attendance records

### Tasks
- Create and assign tasks to employees
- Priority levels (Low, Medium, High)
- Progress tracking (0-100%)
- Due date management
- Filter by status

### Salary
- Auto-generate salary based on attendance
- Monthly salary records
- Gross/Deductions/Net calculation
- CSV export for reports

## Tech Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript (Jinja2 templates)
- **Icons**: Font Awesome

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Access the dashboard:**
   Open your browser and go to `http://localhost:5000`

## Project Structure

```
brickdash/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── brickdash.db          # SQLite database (auto-created)
├── static/
│   └── css/
│       └── style.css     # Stylesheet
└── templates/
    ├── base.html         # Base template with sidebar
    ├── dashboard.html    # Dashboard page
    ├── products.html     # Products list
    ├── product_form.html # Add/Edit product
    ├── orders.html       # Orders list
    ├── order_form.html   # Add/Edit order
    ├── order_view.html   # Order details
    ├── inventory.html    # Inventory management
    ├── employees.html    # Employees list
    ├── employee_form.html# Add/Edit employee
    ├── employee_view.html# Employee details
    ├── attendance_registry.html  # Mark attendance
    ├── attendance_records.html   # View attendance
    ├── tasks.html        # Tasks list
    ├── task_form.html    # Add/Edit task
    ├── salary.html       # Salary management
    └── salary_report.html# Salary report
```

## Date Format

All dates are displayed in **dd-mm-yyyy** format as requested.

## Currency Format

- Amounts are shown in ₹ (Indian Rupees)
- Large amounts displayed in Lakhs (L) format
- Example: ₹1,50,000 = ₹1.50L

## Sample Data

The application comes pre-loaded with sample data:
- 5 products (Red Bricks, Fly Ash Bricks, Cement Blocks, etc.)
- 10 employees with various roles

## Notes

- The database file (`brickdash.db`) is created automatically on first run
- All data is stored locally in SQLite
- No external database server required

## Light Theme

The application uses a clean, light theme with:
- Pink/magenta gradient header
- White sidebar and cards
- Clear typography and spacing
- Color-coded status badges

## Support

For any issues or feature requests, please contact the development team.
