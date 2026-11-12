from flask import (
    Blueprint, current_app, flash, redirect, render_template, request,
    session, url_for,
)
from werkzeug.security import generate_password_hash

from db import get_db
from routes.auth import login_required, role_required
from routes import create_notification

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

VALID_TRANSITIONS = {
    'Submitted': ['Under Review'],
    'Under Review': ['Assigned', 'Rejected'],
    'Assigned': ['In Progress'],
    'In Progress': ['Resolved'],
    'Resolved': ['Reopened', 'Closed'],
    'Reopened': ['Under Review'],
    'Closed': [],
    'Rejected': [],
}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    """Admin dashboard with aggregate stats."""
    db = get_db()

    total = db.execute('SELECT COUNT(*) FROM complaints').fetchone()[0]

    # Count by status
    status_rows = db.execute(
        'SELECT status, COUNT(*) AS cnt FROM complaints GROUP BY status'
    ).fetchall()
    status_counts = {row['status']: row['cnt'] for row in status_rows}

    # Count by category
    category_rows = db.execute(
        'SELECT category, COUNT(*) AS cnt FROM complaints GROUP BY category'
    ).fetchall()
    category_counts = {row['category']: row['cnt'] for row in category_rows}

    # Count by ward
    ward_rows = db.execute(
        'SELECT ward, COUNT(*) AS cnt FROM complaints GROUP BY ward'
    ).fetchall()
    ward_counts = {row['ward']: row['cnt'] for row in ward_rows}

    # Duplicate stats
    dup_pending = db.execute(
        "SELECT COUNT(*) FROM duplicate_relationships WHERE verification_status = 'pending'"
    ).fetchone()[0]
    dup_confirmed = db.execute(
        "SELECT COUNT(*) FROM duplicate_relationships WHERE verification_status = 'confirmed'"
    ).fetchone()[0]
    dup_rejected = db.execute(
        "SELECT COUNT(*) FROM duplicate_relationships WHERE verification_status = 'rejected'"
    ).fetchone()[0]

    return render_template(
        'admin/dashboard.html',
        total=total,
        status_counts=status_counts,
        category_counts=category_counts,
        ward_counts=ward_counts,
        dup_pending=dup_pending,
        dup_confirmed=dup_confirmed,
        dup_rejected=dup_rejected,
    )


# ---------------------------------------------------------------------------
# List complaints
# ---------------------------------------------------------------------------

@admin_bp.route('/complaints')
@role_required('admin')
def complaints():
    """List all complaints with optional filters and search."""
    db = get_db()
    status_filter = request.args.get('status', '').strip()
    category_filter = request.args.get('category', '').strip()
    ward_filter = request.args.get('ward', '').strip()
    search_q = request.args.get('q', '').strip()

    query = 'SELECT * FROM complaints WHERE 1=1'
    params = []

    if status_filter:
        query += ' AND status = ?'
        params.append(status_filter)
    if category_filter:
        query += ' AND category = ?'
        params.append(category_filter)
    if ward_filter:
        query += ' AND ward = ?'
        params.append(ward_filter)
    if search_q:
        query += ' AND (complaint_uid LIKE ? OR title LIKE ?)'
        like = f'%{search_q}%'
        params.extend([like, like])

    query += ' ORDER BY created_at DESC'
    rows = db.execute(query, params).fetchall()

    return render_template(
        'admin/complaints.html',
        complaints=rows,
        status_filter=status_filter,
        category_filter=category_filter,
        ward_filter=ward_filter,
        search_q=search_q,
        categories=current_app.config['COMPLAINT_CATEGORIES'],
        wards=current_app.config['WARDS'],
    )


# ---------------------------------------------------------------------------
# Complaint detail (view + actions)
# ---------------------------------------------------------------------------

@admin_bp.route('/complaint/<int:id>', methods=['GET', 'POST'])
@role_required('admin')
def complaint_detail(id):
    """View complaint detail and handle admin actions."""
    db = get_db()
    complaint = db.execute(
        'SELECT * FROM complaints WHERE id = ?', (id,)
    ).fetchone()

    if complaint is None:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('admin.complaints'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'change_status':
            new_status = request.form.get('new_status', '').strip()
            current_status = complaint['status']
            allowed = VALID_TRANSITIONS.get(current_status, [])

            if new_status not in allowed:
                flash(
                    f'Invalid status transition from "{current_status}" to "{new_status}".',
                    'danger',
                )
            else:
                db.execute(
                    'UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP '
                    'WHERE id = ?',
                    (new_status, id),
                )
                db.execute(
                    'INSERT INTO complaint_history '
                    '(complaint_id, old_status, new_status, updated_by) '
                    'VALUES (?, ?, ?, ?)',
                    (id, current_status, new_status, session['user_id']),
                )
                db.commit()

                # Notify citizen
                create_notification(
                    complaint['user_id'],
                    f'Your complaint {complaint["complaint_uid"]} status changed to {new_status}.',
                    url_for('citizen.complaint_detail', id=id),
                )
                flash(f'Status updated to {new_status}.', 'success')

        elif action == 'assign_officer':
            officer_id = request.form.get('officer_id', type=int)
            if officer_id is None:
                flash('Please select an officer.', 'danger')
            else:
                db.execute(
                    'UPDATE complaints SET assigned_officer_id = ?, status = ?, '
                    'updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                    (officer_id, 'Assigned', id),
                )
                db.execute(
                    'INSERT INTO complaint_history '
                    '(complaint_id, old_status, new_status, remarks, updated_by) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (id, complaint['status'], 'Assigned',
                     f'Assigned to officer id {officer_id}', session['user_id']),
                )
                db.commit()

                # Notify the assigned officer
                create_notification(
                    officer_id,
                    f'You have been assigned complaint {complaint["complaint_uid"]}.',
                    url_for('officer.complaint_detail', id=id),
                )
                # Notify citizen
                create_notification(
                    complaint['user_id'],
                    f'Your complaint {complaint["complaint_uid"]} has been assigned to an officer.',
                    url_for('citizen.complaint_detail', id=id),
                )
                flash('Officer assigned successfully.', 'success')

        elif action == 'add_remarks':
            remarks = request.form.get('remarks', '').strip()
            if remarks:
                db.execute(
                    'INSERT INTO complaint_history '
                    '(complaint_id, old_status, new_status, remarks, updated_by) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (id, complaint['status'], complaint['status'],
                     remarks, session['user_id']),
                )
                db.commit()
                flash('Remarks added.', 'success')
            else:
                flash('Remarks cannot be empty.', 'danger')

        return redirect(url_for('admin.complaint_detail', id=id))

    # GET – prepare data for the template
    history = db.execute(
        'SELECT ch.*, u.name AS updated_by_name '
        'FROM complaint_history ch LEFT JOIN users u ON ch.updated_by = u.id '
        'WHERE ch.complaint_id = ? ORDER BY ch.updated_at DESC',
        (id,),
    ).fetchall()

    assigned_officer = None
    if complaint['assigned_officer_id']:
        assigned_officer = db.execute(
            'SELECT * FROM users WHERE id = ?',
            (complaint['assigned_officer_id'],),
        ).fetchone()

    # Officers whose department matches the complaint category
    department_map = current_app.config['DEPARTMENT_MAP']
    target_dept = department_map.get(complaint['category'])
    if target_dept:
        available_officers = db.execute(
            "SELECT * FROM users WHERE role = 'officer' AND department = ? AND is_active = 1",
            (target_dept,),
        ).fetchall()
    else:
        available_officers = db.execute(
            "SELECT * FROM users WHERE role = 'officer' AND is_active = 1"
        ).fetchall()

    valid_next = VALID_TRANSITIONS.get(complaint['status'], [])

    return render_template(
        'admin/complaint_detail.html',
        complaint=complaint,
        history=history,
        assigned_officer=assigned_officer,
        available_officers=available_officers,
        valid_next=valid_next,
    )


# ---------------------------------------------------------------------------
# Duplicates
# ---------------------------------------------------------------------------

@admin_bp.route('/duplicates')
@role_required('admin')
def duplicates():
    """List pending duplicate relationships."""
    db = get_db()
    rows = db.execute(
        "SELECT dr.*, "
        "p.complaint_uid AS parent_uid, p.title AS parent_title, "
        "p.category AS parent_category, p.ward AS parent_ward, "
        "d.complaint_uid AS dup_uid, d.title AS dup_title, "
        "d.category AS dup_category, d.ward AS dup_ward "
        "FROM duplicate_relationships dr "
        "JOIN complaints p ON dr.parent_complaint_id = p.id "
        "JOIN complaints d ON dr.duplicate_complaint_id = d.id "
        "WHERE dr.verification_status = 'pending' "
        "ORDER BY dr.similarity_score DESC"
    ).fetchall()
    return render_template('admin/duplicates.html', duplicates=rows)


@admin_bp.route('/duplicate/<int:id>/verify', methods=['POST'])
@role_required('admin')
def verify_duplicate(id):
    """Confirm or reject a duplicate relationship."""
    db = get_db()
    action = request.form.get('action', '').strip()

    dup_rel = db.execute(
        'SELECT * FROM duplicate_relationships WHERE id = ?', (id,)
    ).fetchone()

    if dup_rel is None:
        flash('Duplicate relationship not found.', 'danger')
        return redirect(url_for('admin.duplicates'))

    if action == 'confirm':
        db.execute(
            'UPDATE duplicate_relationships SET verification_status = ?, '
            'verified_by = ?, verified_at = CURRENT_TIMESTAMP WHERE id = ?',
            ('confirmed', session['user_id'], id),
        )
        # Link duplicate to parent
        db.execute(
            'UPDATE complaints SET parent_complaint_id = ? WHERE id = ?',
            (dup_rel['parent_complaint_id'], dup_rel['duplicate_complaint_id']),
        )
        db.commit()

        # Notify the citizen who filed the duplicate
        dup_complaint = db.execute(
            'SELECT * FROM complaints WHERE id = ?',
            (dup_rel['duplicate_complaint_id'],),
        ).fetchone()
        if dup_complaint:
            create_notification(
                dup_complaint['user_id'],
                f'Your complaint {dup_complaint["complaint_uid"]} has been identified as a duplicate.',
                url_for('citizen.complaint_detail', id=dup_complaint['id']),
            )
        flash('Duplicate confirmed.', 'success')

    elif action == 'reject':
        db.execute(
            'UPDATE duplicate_relationships SET verification_status = ?, '
            'verified_by = ?, verified_at = CURRENT_TIMESTAMP WHERE id = ?',
            ('rejected', session['user_id'], id),
        )
        db.commit()
        flash('Duplicate rejected.', 'info')
    else:
        flash('Invalid action.', 'danger')

    return redirect(url_for('admin.duplicates'))


# ---------------------------------------------------------------------------
# Officer management
# ---------------------------------------------------------------------------

@admin_bp.route('/officers', endpoint='officers')
@admin_bp.route('/officers', endpoint='manage_officers')
@role_required('admin')
def officers():
    """List all officers."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM users WHERE role = 'officer' ORDER BY name"
    ).fetchall()
    return render_template('admin/manage_officers.html', officers=rows)


@admin_bp.route('/officer/new', methods=['GET', 'POST'])
@role_required('admin')
def new_officer():
    """Create a new officer account."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        password = request.form.get('password', '')
        department = request.form.get('department', '').strip()

        error = None
        if not name:
            error = 'Name is required.'
        elif not mobile:
            error = 'Mobile is required.'
        elif not password:
            error = 'Password is required.'
        elif not department:
            error = 'Department is required.'

        if error is None:
            db = get_db()
            existing = db.execute(
                'SELECT id FROM users WHERE mobile = ?', (mobile,)
            ).fetchone()
            if existing:
                error = 'Mobile number already in use.'

        if error:
            flash(error, 'danger')
            return render_template('admin/officer_form.html', officer=None)

        db = get_db()
        db.execute(
            'INSERT INTO users (name, mobile, password_hash, role, department) '
            'VALUES (?, ?, ?, ?, ?)',
            (name, mobile, generate_password_hash(password), 'officer', department),
        )
        db.commit()
        flash('Officer account created successfully.', 'success')
        return redirect(url_for('admin.officers'))

    return render_template('admin/officer_form.html', officer=None)


@admin_bp.route('/officer/<int:id>/edit', methods=['GET', 'POST'])
@role_required('admin')
def edit_officer(id):
    """Edit an existing officer's details."""
    db = get_db()
    officer = db.execute('SELECT * FROM users WHERE id = ?', (id,)).fetchone()

    if officer is None or officer['role'] != 'officer':
        flash('Officer not found.', 'danger')
        return redirect(url_for('admin.officers'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        department = request.form.get('department', '').strip()
        password = request.form.get('password', '')

        error = None
        if not name:
            error = 'Name is required.'
        elif not mobile:
            error = 'Mobile is required.'
        elif not department:
            error = 'Department is required.'

        if error is None and mobile != officer['mobile']:
            existing = db.execute(
                'SELECT id FROM users WHERE mobile = ?', (mobile,)
            ).fetchone()
            if existing:
                error = 'Mobile number already in use.'

        if error:
            flash(error, 'danger')
            return render_template('admin/officer_form.html', officer=officer)

        if password:
            db.execute(
                'UPDATE users SET name = ?, mobile = ?, department = ?, '
                'password_hash = ? WHERE id = ?',
                (name, mobile, department,
                 generate_password_hash(password), id),
            )
        else:
            db.execute(
                'UPDATE users SET name = ?, mobile = ?, department = ? WHERE id = ?',
                (name, mobile, department, id),
            )
        db.commit()
        flash('Officer updated successfully.', 'success')
        return redirect(url_for('admin.officers'))

    return render_template('admin/officer_form.html', officer=officer)
