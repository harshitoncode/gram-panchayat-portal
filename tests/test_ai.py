import unittest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_module import preprocess_text, find_duplicates


class TestAIModule(unittest.TestCase):
    def test_preprocess_text(self):
        text = "Broken Road & Potholes near Temple! #Emergency 123"
        cleaned = preprocess_text(text)
        self.assertNotIn('&', cleaned)
        self.assertNotIn('!', cleaned)
        self.assertNotIn('#', cleaned)
        self.assertIn('broken', cleaned)
        self.assertIn('road', cleaned)
        self.assertIn('potholes', cleaned)

    def test_duplicate_detection_similar(self):
        existing = [
            {
                'id': 1,
                'complaint_uid': 'GP-2026-00001',
                'title': 'Broken road with dangerous potholes',
                'description': 'The road near the primary school in Ward 1 has massive potholes causing frequent bike accidents.',
                'category': 'Road & Infrastructure',
                'ward': 'Ward 1'
            },
            {
                'id': 2,
                'complaint_uid': 'GP-2026-00002',
                'title': 'Low water pressure in morning',
                'description': 'Water supply pressure is very low for the past three days in Ward 3 residential area.',
                'category': 'Water Supply',
                'ward': 'Ward 3'
            }
        ]

        new_complaint = {
            'title': 'Potholes on road near school',
            'description': 'Dangerous large potholes on school road causing accidents in Ward 1.',
            'category': 'Road & Infrastructure',
            'ward': 'Ward 1'
        }

        matches = find_duplicates(new_complaint, existing, threshold=0.3)
        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0]['complaint_id'], 1)
        self.assertEqual(matches[0]['complaint_uid'], 'GP-2026-00001')
        self.assertGreater(matches[0]['similarity_score'], 0.4)

    def test_unrelated_complaint(self):
        existing = [
            {
                'id': 1,
                'complaint_uid': 'GP-2026-00001',
                'title': 'Broken street light',
                'description': 'Street light pole #4 is dark since Sunday.',
                'category': 'Electricity & Street Lights',
                'ward': 'Ward 2'
            }
        ]

        new_complaint = {
            'title': 'Garbage overflow near market',
            'description': 'Waste collection bin is full and spilling on road in market area.',
            'category': 'Waste Management',
            'ward': 'Ward 4'
        }

        matches = find_duplicates(new_complaint, existing, threshold=0.3)
        self.assertEqual(len(matches), 0)

    def test_empty_existing(self):
        new_complaint = {
            'title': 'Any issue',
            'description': 'Description of issue.',
            'category': 'Other',
            'ward': 'Ward 1'
        }
        matches = find_duplicates(new_complaint, [])
        self.assertEqual(matches, [])


if __name__ == '__main__':
    unittest.main()

