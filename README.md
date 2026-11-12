# Smart Gram Panchayat Complaint Portal with AI-Based Duplicate Complaint Detection

A full-stack web application designed to digitize complaint registration, tracking, resolution, and duplicate detection at the Gram Panchayat level.

---

## 🌟 Key Features

1. **Citizen Portal:**
   - Account registration with Ward selection.
   - Complaint submission with optional evidence image upload.
   - Unique automated Complaint ID generation (`GP-YYYY-NNNNN`).
   - Real-time status tracking with visual timeline history.
   - In-app notifications when status changes or complaints are assigned/resolved.
   - Citizen feedback rating (1–5 stars) & reopening option for resolved grievances.

2. **AI Duplicate Complaint Detection Engine:**
   - NLP-based text preprocessing (punctuation removal, lowercase normalization).
   - Scikit-learn **TF-IDF Vectorization** and **Cosine Similarity** matrix calculation.
   - Domain-specific boosting for matching **Complaint Category** (+15%) and **Ward** (+10%).
   - Automatic background duplicate detection on new complaint submission.
   - Side-by-side comparison interface for administrators to confirm or reject duplicate suggestions.
   - Preserves individual complaint records while linking duplicates to the parent ticket.

3. **Administrative & Officer Operations:**
   - Role-Based Access Control (RBAC): `citizen`, `admin`, `officer`.
   - Admin dashboard with Chart.js analytics (Category-wise and Ward-wise distributions).
   - Complaint verification, department-based officer assignment, and remarks logging.
   - Officer task management: move assigned tickets to "In Progress" and "Resolved" with required field remarks.

---

## 🏗️ Project Architecture

```
gram-panchayat-portal/
├── app.py                  # Flask application factory
├── config.py               # Configuration & domain mappings
├── db.py                   # SQLite connection & database helpers
├── schema.sql              # Database schema (6 relational tables)
├── ai_module.py            # AI TF-IDF + Cosine Similarity engine
├── requirements.txt        # Python dependencies
├── routes/
│   ├── auth.py             # User registration, login, logout & role decorators
│   ├── citizen.py          # Complaint submission, tracking, feedback & notifications
│   ├── admin.py            # Admin dashboard, assignment, status & duplicate verification
│   └── officer.py          # Officer dashboard, task updates & resolution
├── templates/
│   ├── base.html           # Base layout with navbar, alerts & footer
│   ├── home.html           # Landing page with feature highlights & steps
│   ├── auth/               # Login & Registration templates
│   ├── citizen/            # Dashboard, submit complaint, tracking, notifications
│   ├── admin/              # Dashboard (with Chart.js), complaints list, detail, duplicates, officers
│   └── officer/            # Dashboard, assigned complaints, resolution update
├── static/
│   ├── css/style.css       # Clean styling with Indian gov portal color palette
│   ├── js/main.js          # Interactive client-side scripts
│   └── uploads/            # Uploaded complaint images
└── tests/
    ├── test_ai.py          # Standalone NLP & similarity tests
    ├── test_auth.py        # Authentication & RBAC tests
    └── test_complaints.py  # End-to-end complaint lifecycle & duplicate workflow tests
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- pip

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize & Seed Database
```bash
flask init-db
```
*(Or the database will auto-initialize on the first run with `instance/portal.db`)*

### 4. Run the Application
```bash
python app.py
```
Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Default Accounts (Pre-Seeded)

| Role | Mobile / Username | Password | Notes |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Full GP admin privileges |
| **Officer (Public Works)** | `officer1` | `officer123` | Road & Infrastructure issues |
| **Officer (Water Supply)** | `officer2` | `officer123` | Water supply grievances |
| **Officer (Sanitation)** | `officer3` | `officer123` | Drainage & waste management |

*Citizens can register directly through the public registration page.*

---

## 🧪 Running Test Suites

Run all tests:
```bash
python -m unittest discover tests
```

Run specific test modules:
```bash
python -m unittest tests/test_ai.py
python -m unittest tests/test_auth.py
python -m unittest tests/test_complaints.py
```

