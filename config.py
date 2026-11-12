import os


class Config:
    """Application configuration."""

    # Flask core
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
    DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'portal.db')
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB

    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # AI duplicate-detection config
    SIMILARITY_THRESHOLD = 0.3
    CATEGORY_BOOST = 0.15
    WARD_BOOST = 0.10
    MAX_DUPLICATE_RESULTS = 5

    # Complaint categories
    COMPLAINT_CATEGORIES = [
        'Road & Infrastructure',
        'Water Supply',
        'Drainage & Sanitation',
        'Electricity & Street Lights',
        'Waste Management',
        'Public Property Damage',
        'Other',
    ]

    # Wards
    WARDS = ['Ward 1', 'Ward 2', 'Ward 3', 'Ward 4', 'Ward 5']

    # Category → Department mapping
    DEPARTMENT_MAP = {
        'Road & Infrastructure': 'Public Works Department',
        'Water Supply': 'Water Supply Department',
        'Drainage & Sanitation': 'Health & Sanitation Department',
        'Electricity & Street Lights': 'Electrical Department',
        'Waste Management': 'Health & Sanitation Department',
        'Public Property Damage': 'Public Works Department',
        'Other': 'General Administration',
    }
