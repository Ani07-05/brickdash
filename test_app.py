"""
BrickDash Application Test Suite
"""
import requests
import json

BASE = 'http://127.0.0.1:5000'

def test_all():
    session = requests.Session()
    passed = 0
    failed = 0
    
    def check(name, condition):
        nonlocal passed, failed
        if condition:
            print(f'  ✓ {name}')
            passed += 1
        else:
            print(f'  ✗ {name}')
            failed += 1
    
    print('='*60)
    print('BRICKDASH APPLICATION TESTING')
    print('='*60)

    # Test 1: Login Page
    print('\n[TEST 1] Login Page')
    try:
        r = session.get(f'{BASE}/login')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Contains login form', 'Sign In' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 2: Register Page
    print('\n[TEST 2] Register Page')
    try:
        r = session.get(f'{BASE}/register')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Contains register form', 'Create Account' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 3: Login as Admin (Manager)
    print('\n[TEST 3] Login as Manager')
    try:
        r = session.post(f'{BASE}/login', data={
            'username': 'admin',
            'password': 'admin123',
            'role': 'Manager'
        }, allow_redirects=True)
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Login successful', 'Dashboard' in r.text or 'admin' in r.text.lower())
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 4: Dashboard
    print('\n[TEST 4] Dashboard')
    try:
        r = session.get(f'{BASE}/')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Shows Manager role', 'Manager' in r.text)
        check('Has stats', 'stat-card' in r.text or 'Total' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 5: Products Page
    print('\n[TEST 5] Products Page')
    try:
        r = session.get(f'{BASE}/products')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Shows products', 'Bricks' in r.text or 'Products' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 6: Orders Page
    print('\n[TEST 6] Orders Page')
    try:
        r = session.get(f'{BASE}/orders')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Orders page loads', 'Order' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 7: Inventory Page
    print('\n[TEST 7] Inventory Page')
    try:
        r = session.get(f'{BASE}/inventory')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Shows inventory', 'Inventory' in r.text or 'Stock' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 8: Employees Page
    print('\n[TEST 8] Employees Page')
    try:
        r = session.get(f'{BASE}/employees')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Shows employees', 'BRK' in r.text or 'Murugan' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 9: Tasks Page
    print('\n[TEST 9] Tasks Page')
    try:
        r = session.get(f'{BASE}/employees/tasks')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Tasks page loads', 'Task' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 10: Task Rotation Page
    print('\n[TEST 10] Task Rotation Matrix')
    try:
        r = session.get(f'{BASE}/employees/tasks/rotation')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Shows rotation matrix', 'Rotation' in r.text or 'Matrix' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 11: Attendance Page
    print('\n[TEST 11] Attendance Registry')
    try:
        r = session.get(f'{BASE}/employees/attendance')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Shows attendance', 'Attendance' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 12: Payroll Page
    print('\n[TEST 12] Payroll Page')
    try:
        r = session.get(f'{BASE}/employees/payroll')
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Shows payroll', 'Payroll' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 13: API - Dashboard Stats
    print('\n[TEST 13] API - Dashboard Stats')
    try:
        r = session.get(f'{BASE}/api/dashboard-stats')
        check(f'Status {r.status_code}', r.status_code == 200)
        data = r.json()
        check('Returns valid JSON', isinstance(data, dict))
        check('Has attendance data', 'attendance' in data)
        check('Has orders data', 'orders' in data)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 14: API - Task Rotation Suggest
    print('\n[TEST 14] API - Task Rotation Suggest')
    try:
        r = session.get(f'{BASE}/api/task-rotation/suggest?type=Loading')
        check(f'Status {r.status_code}', r.status_code == 200)
        data = r.json()
        check('Suggests employee', 'suggested_employee' in data)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 15: Create a Task
    print('\n[TEST 15] Create Task')
    try:
        r = session.post(f'{BASE}/employees/tasks/add', data={
            'title': 'Test Loading Task',
            'description': 'Test task for verification',
            'assigned_to': '1',
            'priority': 'High',
            'status': 'Not Started',
            'progress': '0',
            'task_type': 'Loading'
        }, allow_redirects=True)
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Task created', 'success' in r.text.lower() or 'Test Loading' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 16: Logout
    print('\n[TEST 16] Logout')
    try:
        r = session.get(f'{BASE}/logout', allow_redirects=True)
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Redirected to login', 'Sign In' in r.text or 'Login' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 17: Login as Supervisor
    print('\n[TEST 17] Login as Supervisor')
    try:
        r = session.post(f'{BASE}/login', data={
            'username': 'supervisor',
            'password': 'super123',
            'role': 'Supervisor'
        }, allow_redirects=True)
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Login successful', 'Supervisor' in r.text or 'Dashboard' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 18: Supervisor cannot see Payroll
    print('\n[TEST 18] Supervisor Role Restrictions')
    try:
        r = session.get(f'{BASE}/')
        has_payroll_link = 'href="/employees/payroll"' in r.text
        check('Payroll hidden from nav', not has_payroll_link)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    session.get(f'{BASE}/logout')

    # Test 19: Login as Employee
    print('\n[TEST 19] Login as Employee')
    try:
        r = session.post(f'{BASE}/login', data={
            'username': 'employee',
            'password': 'emp123',
            'role': 'Employee'
        }, allow_redirects=True)
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Login successful', 'Employee' in r.text or 'Dashboard' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 20: Employee Role Restrictions
    print('\n[TEST 20] Employee Role Restrictions')
    try:
        r = session.get(f'{BASE}/')
        # Check only in sidebar nav section
        nav_section = r.text[r.text.find('sidebar-nav'):r.text.find('sidebar-footer')]
        has_payroll = '/employees/payroll' in nav_section
        has_inventory = '/inventory' in nav_section
        has_employees_mgmt = 'Workforce Management' in nav_section
        check('Payroll hidden', not has_payroll)
        check('Inventory hidden', not has_inventory)
        check('Workforce section hidden', not has_employees_mgmt)
        check('My Tasks visible', 'My Tasks' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    session.get(f'{BASE}/logout')

    # Test 21: Register new user
    print('\n[TEST 21] Register New Employee')
    try:
        session2 = requests.Session()
        r = session2.post(f'{BASE}/register', data={
            'name': 'New Test Worker',
            'username': 'newtestworker',
            'phone': '9876543288',
            'password': 'newtest123',
            'confirm_password': 'newtest123'
        }, allow_redirects=True)
        check(f'Status {r.status_code}', r.status_code == 200)
        check('Registration successful', 'Account created' in r.text or 'Login' in r.text or 'BRK' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Test 22: Login with new account
    print('\n[TEST 22] Login with New Account')
    try:
        r = session2.post(f'{BASE}/login', data={
            'username': 'newtestworker',
            'password': 'newtest123',
            'role': 'Employee'
        }, allow_redirects=True)
        check(f'Status {r.status_code}', r.status_code == 200)
        check('New user can login', 'newtestworker' in r.text or 'Dashboard' in r.text)
    except Exception as e:
        print(f'  ✗ Error: {e}')
        failed += 1

    # Summary
    print('\n' + '='*60)
    print(f'TEST RESULTS: {passed} passed, {failed} failed')
    print('='*60)
    
    return failed == 0

if __name__ == '__main__':
    test_all()
