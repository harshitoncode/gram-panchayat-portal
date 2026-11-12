import functools

from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def login_required(f):
    """Redirect anonymous users to the login page."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(role):
    """Return 403 if the logged-in user does not have the required role."""
    def decorator(f):
        @functools.wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if session.get('role') != role:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('auth.login')), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Show registration form / process registration."""
    from flask import current_app
    wards = current_app.config['WARDS']

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        ward = request.form.get('ward', '').strip()
        email = request.form.get('email', '').strip() or None

        error = None
        if not name:
            error = 'Name is required.'
        elif not mobile:
            error = 'Mobile number is required.'
        elif not password:
            error = 'Password is required.'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        elif not ward:
            error = 'Ward is required.'

        if error is None:
            db = get_db()
            existing = db.execute(
                'SELECT id FROM users WHERE mobile = ?', (mobile,)
            ).fetchone()
            if existing:
                error = 'Mobile number is already registered.'

        if error:
            flash(error, 'danger')
            return render_template('auth/register.html', wards=wards)

        db = get_db()
        db.execute(
            'INSERT INTO users (name, mobile, email, password_hash, ward, role) '
            'VALUES (?, ?, ?, ?, ?, ?)',
            (name, mobile, email, generate_password_hash(password), ward, 'citizen'),
        )
        db.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', wards=wards)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Show login form / authenticate user."""
    if request.method == 'POST':
        mobile = request.form.get('mobile', '').strip()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE mobile = ?', (mobile,)
        ).fetchone()

        error = None
        if user is None:
            error = 'Invalid mobile number.'
        elif not check_password_hash(user['password_hash'], password):
            error = 'Incorrect password.'

        if error:
            flash(error, 'danger')
            return render_template('auth/login.html')

        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['role'] = user['role']

        if user['role'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user['role'] == 'officer':
            return redirect(url_for('officer.dashboard'))
        else:
            return redirect(url_for('citizen.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to home."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))
