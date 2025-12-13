"""Insert sample data into Supabase Postgres database."""
import os
import hashlib
from pathlib import Path

# Load .env
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

from db import DB

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def seed_data():
    """Insert sample data into database"""
    db = DB()
    
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            # Check if users already exist
            cur.execute('SELECT COUNT(*) as cnt FROM users WHERE username = %s', ('admin',))
            result = cur.fetchone()
            if result and result.get('cnt', 0) > 0:
                print("Sample data already exists. Skipping.")
                return
            
            print("Inserting sample data...")
            
            # Create default users
            admin_password = hash_password('admin123')
            cur.execute('''
                INSERT INTO users (username, password, role) VALUES (%s, %s, %s)
            ''', ('admin', admin_password, 'Manager'))
            
            cur.execute('''
                INSERT INTO users (username, password, role) VALUES (%s, %s, %s)
            ''', ('supervisor', hash_password('super123'), 'Supervisor'))
            
            # Insert sample products
            products = [
                ('Red Bricks (Standard)', 'Bricks', 8, 'piece', 50000, 'Standard red clay bricks'),
                ('Fly Ash Bricks', 'Bricks', 6, 'piece', 30000, 'Eco-friendly fly ash bricks'),
                ('Cement Blocks', 'Blocks', 45, 'piece', 10000, 'Heavy duty cement blocks'),
                ('Paver Blocks', 'Blocks', 35, 'piece', 15000, 'Interlocking paver blocks'),
                ('Fire Bricks', 'Bricks', 25, 'piece', 5000, 'Heat resistant fire bricks'),
            ]
            for p in products:
                cur.execute('''
                    INSERT INTO products (name, category, price_per_unit, unit, stock_quantity, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', p)
            
            # Insert sample employees
            employees = [
                ('BRK020', 'Murugan', 'Security', '9876543210', 'Chennai', 12000, True),
                ('BRK019', 'Kumar', 'Loader', '9876543211', 'Chennai', 22000, False),
                ('BRK018', 'Dinesh', 'Loader', '9876543212', 'Chennai', 16000, True),
                ('BRK017', 'Vinoth', 'Security', '9876543213', 'Chennai', 25000, True),
                ('BRK016', 'Illa', 'Supervisor', '9876543214', 'Chennai', 14000, False),
                ('BRK015', 'Saravanan', 'Quality Checker', '9876543215', 'Chennai', 12000, True),
                ('BRK014', 'Gopi', 'Supervisor', '9876543216', 'Chennai', 16000, True),
                ('BRK013', 'Selvam', 'Truck Driver', '9876543217', 'Chennai', 17000, True),
                ('BRK012', 'Ramesh', 'Worker', '9876543218', 'Chennai', 15000, True),
                ('BRK011', 'Ravi', 'Worker', '9876543219', 'Chennai', 15000, True),
            ]
            for e in employees:
                cur.execute('''
                    INSERT INTO employees (employee_id, name, role, phone, address, salary, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', e)
            
            # Get Ravi's ID and create employee user
            cur.execute("SELECT id FROM employees WHERE employee_id = %s", ('BRK011',))
            ravi_row = cur.fetchone()
            if ravi_row:
                ravi_id = ravi_row.get('id') if isinstance(ravi_row, dict) else ravi_row[0]
                cur.execute('''
                    INSERT INTO users (username, password, role, employee_id) VALUES (%s, %s, %s, %s)
                ''', ('employee', hash_password('emp123'), 'Employee', ravi_id))
            
        conn.commit()
    
    print("✅ Sample data inserted successfully!")
    print("\nDefault credentials:")
    print("  Manager: admin / admin123")
    print("  Supervisor: supervisor / super123")
    print("  Employee: employee / emp123")

if __name__ == "__main__":
    seed_data()
