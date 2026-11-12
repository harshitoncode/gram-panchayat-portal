import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from db import init_db, seed_data, close_db, get_db


class TestComplaintsWorkflow(unittest.TestCase):
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

    def test_full_complaint_and_duplicate_lifecycle(self):
        # 1. Register and login Citizen A
        self.client.post('/auth/register', data={
            'name': 'Citizen Amit',
            'mobile': '9111111111',
            'password': 'password123',
            'confirm_password': 'password123',
            'ward': 'Ward 1'
        })
        self.client.post('/auth/login', data={
            'mobile': '9111111111',
            'password': 'password123'
        })

        # 2. Citizen A submits road complaint
        resp1 = self.client.post('/complaint/new', data={
            'title': 'Dangerous road potholes near temple',
            'description': 'Main temple road in Ward 1 has massive potholes causing severe traffic and bike accidents.',
            'category': 'Road & Infrastructure',
            'ward': 'Ward 1',
            'location_detail': 'Near Shiva Temple'
        }, follow_redirects=True)
        self.assertEqual(resp1.status_code, 200)
        self.assertIn(b'GP-2026-00001', resp1.data)

        # Verify My Complaints page renders with the new complaint
        my_comp_resp = self.client.get('/complaints')
        self.assertEqual(my_comp_resp.status_code, 200)
        self.assertIn(b'GP-2026-00001', my_comp_resp.data)
        self.assertIn(b'Dangerous road potholes near temple', my_comp_resp.data)

        # Verify Complaint Detail page renders
        detail_resp = self.client.get('/complaint/1')
        self.assertEqual(detail_resp.status_code, 200)
        self.assertIn(b'Dangerous road potholes near temple', detail_resp.data)

        # Logout Citizen A
        self.client.get('/auth/logout')

        # 3. Register and login Citizen B
        self.client.post('/auth/register', data={
            'name': 'Citizen Brijesh',
            'mobile': '9222222222',
            'password': 'password123',
            'confirm_password': 'password123',
            'ward': 'Ward 1'
        })
        self.client.post('/auth/login', data={
            'mobile': '9222222222',
            'password': 'password123'
        })

        # 4. Citizen B submits highly similar complaint in same ward
        resp2 = self.client.post('/complaint/new', data={
            'title': 'Road potholes near temple area',
            'description': 'Severe potholes on the road near temple causing road accidents in Ward 1.',
            'category': 'Road & Infrastructure',
            'ward': 'Ward 1',
            'location_detail': 'Temple road'
        }, follow_redirects=True)
        self.assertEqual(resp2.status_code, 200)
        self.assertIn(b'GP-2026-00002', resp2.data)

        # Verify duplicate was detected in database
        with self.app.app_context():
            db = get_db()
            dup = db.execute('SELECT * FROM duplicate_relationships').fetchone()
            self.assertIsNotNone(dup)
            self.assertEqual(dup['parent_complaint_id'], 1)
            self.assertEqual(dup['duplicate_complaint_id'], 2)
            self.assertEqual(dup['verification_status'], 'pending')
            self.assertGreater(dup['similarity_score'], 0.4)

        # Logout Citizen B
        self.client.get('/auth/logout')

        # 5. Admin Login
        self.client.post('/auth/login', data={
            'mobile': 'admin',
            'password': 'admin123'
        })

        # Check duplicate page
        dup_page = self.client.get('/admin/duplicates')
        self.assertIn(b'GP-2026-00002', dup_page.data)
        self.assertIn(b'GP-2026-00001', dup_page.data)

        # Admin confirms duplicate
        verify_resp = self.client.post('/admin/duplicate/1/verify', data={
            'action': 'confirm'
        }, follow_redirects=True)
        self.assertEqual(verify_resp.status_code, 200)

        # Verify complaint 2 now has parent_complaint_id = 1
        with self.app.app_context():
            db = get_db()
            c2 = db.execute('SELECT * FROM complaints WHERE id = 2').fetchone()
            self.assertEqual(c2['parent_complaint_id'], 1)

        # 6. Admin assigns complaint 1 to Public Works officer (officer id=2 in seed_data)
        assign_resp = self.client.post('/admin/complaint/1', data={
            'action': 'assign_officer',
            'officer_id': '2'
        }, follow_redirects=True)
        self.assertEqual(assign_resp.status_code, 200)

        with self.app.app_context():
            db = get_db()
            c1 = db.execute('SELECT * FROM complaints WHERE id = 1').fetchone()
            self.assertEqual(c1['status'], 'Assigned')
            self.assertEqual(c1['assigned_officer_id'], 2)

        # Logout Admin
        self.client.get('/auth/logout')

        # 7. Officer Login (Public Works officer: mobile='officer1', password='officer123')
        self.client.post('/auth/login', data={
            'mobile': 'officer1',
            'password': 'officer123'
        })

        # Officer views assigned complaints
        assigned_page = self.client.get('/officer/complaints')
        self.assertIn(b'GP-2026-00001', assigned_page.data)

        # Officer moves status to 'In Progress'
        self.client.post('/officer/complaint/1', data={
            'new_status': 'In Progress',
            'remarks': 'Site inspection conducted. Road repair crew dispatched.'
        }, follow_redirects=True)

        with self.app.app_context():
            db = get_db()
            c1 = db.execute('SELECT * FROM complaints WHERE id = 1').fetchone()
            self.assertEqual(c1['status'], 'In Progress')

        # Officer marks as 'Resolved'
        self.client.post('/officer/complaint/1', data={
            'new_status': 'Resolved',
            'remarks': 'Potholes filled and bitumen road leveled successfully.'
        }, follow_redirects=True)

        with self.app.app_context():
            db = get_db()
            c1 = db.execute('SELECT * FROM complaints WHERE id = 1').fetchone()
            self.assertEqual(c1['status'], 'Resolved')

        # Logout Officer
        self.client.get('/auth/logout')

        # 8. Citizen A logs in and submits feedback
        self.client.post('/auth/login', data={
            'mobile': '9111111111',
            'password': 'password123'
        })

        feedback_resp = self.client.post('/complaint/1/feedback', data={
            'rating': '5',
            'comments': 'Excellent rapid response from the Panchayat team!'
        }, follow_redirects=True)
        self.assertEqual(feedback_resp.status_code, 200)

        with self.app.app_context():
            db = get_db()
            fb = db.execute('SELECT * FROM feedback WHERE complaint_id = 1').fetchone()
            self.assertIsNotNone(fb)
            self.assertEqual(fb['rating'], 5)
            self.assertEqual(fb['comments'], 'Excellent rapid response from the Panchayat team!')


if __name__ == '__main__':
    unittest.main()
