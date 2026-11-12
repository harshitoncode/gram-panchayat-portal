import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from db import init_db, seed_data, close_db


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['DATABASE'] = self.db_path
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db()
            seed_data()

    def tearDown(self):
        with self.app.app_context():
            close_db()
        os.close(self.db_fd)
        try:
            os.unlink(self.db_path)
        except PermissionError:
            pass

    def test_citizen_registration_and_login(self):
        # Register new citizen
        reg_response = self.client.post('/auth/register', data={
            'name': 'Ramesh Kumar',
            'mobile': '9876543210',
            'email': 'ramesh@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'ward': 'Ward 1'
        }, follow_redirects=True)
        self.assertEqual(reg_response.status_code, 200)

        # Login with newly registered citizen
        login_response = self.client.post('/auth/login', data={
            'mobile': '9876543210',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_response.status_code, 200)
        self.assertIn(b'Welcome, Ramesh Kumar!', login_response.data)
        self.assertIn(b'Total Complaints', login_response.data)

    def test_admin_login(self):
        # Default seeded admin: mobile='admin', password='admin123'
        response = self.client.post('/auth/login', data={
            'mobile': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Administrative Dashboard', response.data)

    def test_invalid_login(self):
        response = self.client.post('/auth/login', data={
            'mobile': 'admin',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b'Incorrect password' in response.data or b'Invalid' in response.data)

    def test_unauthorized_admin_access(self):
        # Access admin dashboard without logging in
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 302)  # Redirects to login


if __name__ == '__main__':
    unittest.main()
