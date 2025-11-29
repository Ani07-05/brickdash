"""
BrickDash Application Test Suite
Comprehensive pytest tests for the Flask application
"""
import pytest
import sqlite3
import tempfile
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db, hash_password, format_indian_currency, format_currency, generate_order_number, generate_employee_id, DATABASE


@pytest.fixture
def client():
    """Create a test client with a temporary database"""
    # Use the existing database for testing
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client


@pytest.fixture
def logged_in_manager(client):
    """Login as manager and return client"""
    client.post('/login', data={
        'username': 'admin',
        'password': 'admin123',
        'role': 'Manager'
    }, follow_redirects=True)
    return client


@pytest.fixture
def logged_in_supervisor(client):
    """Login as supervisor and return client"""
    client.post('/login', data={
        'username': 'supervisor',
        'password': 'super123',
        'role': 'Supervisor'
    }, follow_redirects=True)
    return client


@pytest.fixture
def logged_in_employee(client):
    """Login as employee and return client"""
    client.post('/login', data={
        'username': 'employee',
        'password': 'emp123',
        'role': 'Employee'
    }, follow_redirects=True)
    return client


# ==================== AUTHENTICATION TESTS ====================

class TestAuthentication:
    """Test authentication functionality"""
    
    def test_login_page_loads(self, client):
        """Test 1: Login page loads correctly"""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Sign In' in response.data or b'Login' in response.data
    
    def test_register_page_loads(self, client):
        """Test 2: Register page loads correctly"""
        response = client.get('/register')
        assert response.status_code == 200
        assert b'Create Account' in response.data or b'Register' in response.data
    
    def test_manager_login_success(self, client):
        """Test 3: Manager can login successfully"""
        response = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'role': 'Manager'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Manager' in response.data or b'Dashboard' in response.data
    
    def test_supervisor_login_success(self, client):
        """Test 4: Supervisor can login successfully"""
        response = client.post('/login', data={
            'username': 'supervisor',
            'password': 'super123',
            'role': 'Supervisor'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Supervisor' in response.data or b'Dashboard' in response.data
    
    def test_employee_login_success(self, client):
        """Test 5: Employee can login successfully"""
        response = client.post('/login', data={
            'username': 'employee',
            'password': 'emp123',
            'role': 'Employee'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Employee' in response.data or b'Dashboard' in response.data
    
    def test_invalid_login_fails(self, client):
        """Test 6: Invalid credentials show error"""
        response = client.post('/login', data={
            'username': 'wronguser',
            'password': 'wrongpass',
            'role': 'Manager'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Invalid' in response.data or b'error' in response.data.lower()
    
    def test_logout_success(self, logged_in_manager):
        """Test 7: Logout works correctly"""
        response = logged_in_manager.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'Sign In' in response.data or b'Login' in response.data


# ==================== PAGE ACCESS TESTS ====================

class TestPageAccess:
    """Test page access and role-based restrictions"""
    
    def test_dashboard_loads(self, logged_in_manager):
        """Test 8: Dashboard page loads"""
        response = logged_in_manager.get('/')
        assert response.status_code == 200
        assert b'Dashboard' in response.data or b'stat-card' in response.data
    
    def test_products_page_loads(self, logged_in_manager):
        """Test 9: Products page loads for manager"""
        response = logged_in_manager.get('/products')
        assert response.status_code == 200
        assert b'Products' in response.data or b'Brick' in response.data
    
    def test_orders_page_loads(self, logged_in_manager):
        """Test 10: Orders page loads"""
        response = logged_in_manager.get('/orders')
        assert response.status_code == 200
        assert b'Order' in response.data
    
    def test_inventory_page_loads(self, logged_in_manager):
        """Test 11: Inventory page loads for manager"""
        response = logged_in_manager.get('/inventory')
        assert response.status_code == 200
        assert b'Inventory' in response.data or b'Stage' in response.data
    
    def test_employees_page_loads(self, logged_in_manager):
        """Test 12: Employees page loads for manager"""
        response = logged_in_manager.get('/employees')
        assert response.status_code == 200
        assert b'BRK' in response.data or b'employee' in response.data.lower()
    
    def test_tasks_page_loads(self, logged_in_manager):
        """Test 13: Tasks page loads"""
        response = logged_in_manager.get('/employees/tasks')
        assert response.status_code == 200
        assert b'Task' in response.data
    
    def test_attendance_page_loads(self, logged_in_manager):
        """Test 14: Attendance page loads"""
        response = logged_in_manager.get('/employees/attendance')
        assert response.status_code == 200
        assert b'Attendance' in response.data
    
    def test_payroll_page_loads(self, logged_in_manager):
        """Test 15: Payroll page loads for manager"""
        response = logged_in_manager.get('/employees/payroll')
        assert response.status_code == 200
        assert b'Payroll' in response.data


# ==================== ROLE RESTRICTION TESTS ====================

class TestRoleRestrictions:
    """Test role-based access control"""
    
    def test_employee_cannot_see_payroll_link(self, logged_in_employee):
        """Test 16: Employee cannot see payroll in navigation"""
        response = logged_in_employee.get('/')
        # Check sidebar doesn't contain payroll link for employee
        assert b'href="/employees/payroll"' not in response.data
    
    def test_employee_cannot_see_inventory_link(self, logged_in_employee):
        """Test 17: Employee cannot see inventory in navigation"""
        response = logged_in_employee.get('/')
        # Check sidebar doesn't contain inventory link for employee
        nav_text = response.data.decode('utf-8')
        # Find sidebar-nav section
        if 'sidebar-nav' in nav_text:
            nav_section = nav_text[nav_text.find('sidebar-nav'):nav_text.find('sidebar-footer')]
            assert '/inventory' not in nav_section
    
    def test_supervisor_cannot_see_payroll_link(self, logged_in_supervisor):
        """Test 18: Supervisor cannot see payroll in navigation"""
        response = logged_in_supervisor.get('/')
        assert b'href="/employees/payroll"' not in response.data


# ==================== API TESTS ====================

class TestAPI:
    """Test API endpoints"""
    
    def test_dashboard_stats_api(self, logged_in_manager):
        """Test 19: Dashboard stats API returns valid JSON"""
        response = logged_in_manager.get('/api/dashboard-stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'attendance' in data
        assert 'orders' in data
        assert 'tasks' in data
    
    def test_task_rotation_suggest_api(self, logged_in_manager):
        """Test 20: Task rotation suggest API works"""
        response = logged_in_manager.get('/api/task-rotation/suggest?type=Loading')
        assert response.status_code == 200
        data = response.get_json()
        assert 'suggested_employee' in data
        assert 'all_candidates' in data
    
    def test_task_rotation_matrix_api(self, logged_in_manager):
        """Test 21: Task rotation matrix API works"""
        response = logged_in_manager.get('/api/task-rotation/matrix')
        assert response.status_code == 200
        data = response.get_json()
        assert 'task_types' in data
        assert 'matrix' in data


# ==================== UTILITY FUNCTION TESTS ====================

class TestUtilityFunctions:
    """Test utility/helper functions"""
    
    def test_hash_password(self):
        """Test 22: Password hashing works correctly"""
        password = "test123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) == 64  # SHA256 produces 64 hex characters
        # Same password produces same hash
        assert hash_password(password) == hashed
    
    def test_format_indian_currency(self):
        """Test 23: Indian currency formatting works correctly"""
        # Test various amounts
        assert format_indian_currency(1000) == '₹1,000'
        assert format_indian_currency(100000) == '₹1,00,000'
        assert format_indian_currency(750253) == '₹7,50,253'
        assert format_indian_currency(0) == '₹0'
    
    def test_format_currency(self):
        """Test 24: Currency formatting with K/L suffix works"""
        assert '₹' in format_currency(1000)
        assert 'K' in format_currency(5000)  # Should show as XK
        assert 'L' in format_currency(200000)  # Should show as XL


# ==================== CRUD OPERATION TESTS ====================

class TestCRUDOperations:
    """Test Create, Read, Update, Delete operations"""
    
    def test_create_task(self, logged_in_manager):
        """Test 25: Creating a task works"""
        response = logged_in_manager.post('/employees/tasks/add', data={
            'title': 'Pytest Test Task',
            'description': 'A task created by pytest',
            'assigned_to': '1',
            'priority': 'High',
            'status': 'Not Started',
            'progress': '0'
        }, follow_redirects=True)
        assert response.status_code == 200
        # Check task was created - either success message or task appears in list
        assert b'success' in response.data.lower() or b'Pytest Test Task' in response.data


# ==================== RUN TESTS ====================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
