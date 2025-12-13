import os
from typing import Optional
import psycopg
from psycopg.rows import dict_row
from pathlib import Path

_SUPABASE_URL_ENV = "SUPABASE_DB_URL"

# Load .env file if present
def load_env():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

class DB:
    """Simple Postgres connection helper using psycopg3.
    - Reads connection string from env SUPABASE_DB_URL
    - Provides get_conn() and get_cursor() context helpers
    """
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.environ.get(_SUPABASE_URL_ENV)
        if not self.dsn:
            raise RuntimeError(f"Environment variable '{_SUPABASE_URL_ENV}' is not set.")
        print(f"[DB] Using connection string: {self.dsn[:30]}...")

    def connect(self):
        # autocommit off; use explicit commit/rollback
        # Add connection timeout and ensure sslmode is set
        try:
            conn_params = self.dsn
            if '?' not in conn_params:
                conn_params += '?sslmode=require&connect_timeout=10'
            elif 'sslmode' not in conn_params:
                conn_params += '&sslmode=require&connect_timeout=10'
            
            return psycopg.connect(conn_params, row_factory=dict_row)
        except Exception as e:
            print(f"[DB] Connection failed: {e}")
            print(f"[DB] Check your SUPABASE_DB_URL and network connectivity")
            print(f"[DB] Common issues: firewall blocking port 5432, VPN required, or IPv6 connectivity")
            raise

    def get_conn(self):
        return self.connect()

    def get_cursor(self):
        conn = self.connect()
        return conn, conn.cursor()


def init_schema():
    """Create tables if they do not exist (Postgres syntax)."""
    db = DB()
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            # Products
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price_per_unit NUMERIC NOT NULL,
                    unit TEXT DEFAULT 'piece',
                    stock_quantity INTEGER DEFAULT 0,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Employees
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS employees (
                    id SERIAL PRIMARY KEY,
                    employee_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    phone TEXT,
                    address TEXT,
                    salary NUMERIC DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    joined_date DATE DEFAULT CURRENT_DATE
                )
                """
            )

            # Attendance
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id),
                    date DATE NOT NULL,
                    status TEXT DEFAULT 'Present',
                    shift TEXT DEFAULT 'Day',
                    notes TEXT,
                    CONSTRAINT uniq_attendance UNIQUE (employee_id, date)
                )
                """
            )

            # Orders
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    order_number TEXT UNIQUE NOT NULL,
                    customer_name TEXT NOT NULL,
                    customer_phone TEXT,
                    customer_address TEXT,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    quantity INTEGER NOT NULL,
                    total_amount NUMERIC NOT NULL,
                    status TEXT DEFAULT 'Pending',
                    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivery_date DATE,
                    notes TEXT
                )
                """
            )

            # Inventory logs
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_logs (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    change_type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Tasks
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    assigned_to INTEGER REFERENCES employees(id),
                    status TEXT DEFAULT 'Pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    due_date DATE
                )
                """
            )

            # Payroll
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payroll (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id),
                    month TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    total_days INTEGER DEFAULT 0,
                    present_days INTEGER DEFAULT 0,
                    absent_days INTEGER DEFAULT 0,
                    overtime_hours INTEGER DEFAULT 0,
                    amount NUMERIC DEFAULT 0,
                    status TEXT DEFAULT 'Unpaid',
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (employee_id, month, year)
                )
                """
            )

            # Users (authentication)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'Employee',
                    employee_id INTEGER REFERENCES employees(id),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Task rotation log
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_rotation_log (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id),
                    task_type TEXT DEFAULT 'General',
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Inventory stages
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_stages (
                    id SERIAL PRIMARY KEY,
                    stage_number INTEGER NOT NULL,
                    stage_name TEXT NOT NULL,
                    capacity INTEGER DEFAULT 1000,
                    current_quantity INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stage_number)
                )
                """
            )

            # Inventory batches
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_batches (
                    id SERIAL PRIMARY KEY,
                    batch_id TEXT UNIQUE NOT NULL,
                    stage_id INTEGER NOT NULL REFERENCES inventory_stages(id),
                    product_id INTEGER REFERENCES products(id),
                    units INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reserved_for TEXT,
                    notes TEXT
                )
                """
            )

            # Batch orders
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS batch_orders (
                    id SERIAL PRIMARY KEY,
                    batch_id INTEGER NOT NULL REFERENCES inventory_batches(id),
                    order_number TEXT NOT NULL
                )
                """
            )

            # Inventory settings
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_settings (
                    id SERIAL PRIMARY KEY,
                    setting_key TEXT UNIQUE NOT NULL,
                    setting_value TEXT NOT NULL
                )
                """
            )

            # Task types
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_types (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    sort_order INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE
                )
                """
            )

            # Salary records
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS salary_records (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES employees(id),
                    month INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    gross_salary NUMERIC DEFAULT 0,
                    deductions NUMERIC DEFAULT 0,
                    allowances NUMERIC DEFAULT 0,
                    net_salary NUMERIC DEFAULT 0,
                    paid BOOLEAN DEFAULT FALSE,
                    UNIQUE (employee_id, month, year)
                )
                """
            )

        conn.commit()

if __name__ == "__main__":
    init_schema()
    print("Postgres schema ensured.")
