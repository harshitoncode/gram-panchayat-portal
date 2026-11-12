from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for,
)

from db import get_db
from routes.auth import login_required, role_required
from routes import create_notification

officer_bp = Blueprint('officer', __name__, url_prefix='/officer')


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@officer_bp.route('/dashboard')
@role_required('officer')
def dashboard():
    """Officer dashboard with counts of assigned complaints by status."""
    db = get_db()
    officer_id = session['user_id']

    status_rows = db.execute(
        'SELECT status, COUNT(*) AS cnt FROM complaints '
        'WHERE assigned_officer_id = ? GROUP BY status',
        (officer_id,),
    ).fetchall()
    status_counts = {row['status']: row['cnt'] for row in status_rows}

    return render_template(
        'officer/dashboard.html',
        status_counts=status_counts,
    )


# ---------------------------------------------------------------------------
# Assigned complaints
# ---------------------------------------------------------------------------

@officer_bp.route('/complaints', endpoint='complaints')
@officer_bp.route('/complaints', endpoint='assigned_complaints')
@role_required('officer')
def complaints():
    """List complaints assigned to this officer with optional status filter."""
    db = get_db()
    officer_id = session['user_id']
    status_filter = request.args.get('status', '').strip()

    if status_filter:
        rows = db.execute(
            'SELECT * FROM complaints WHERE assigned_officer_id = ? AND status = ? '
            'ORDER BY created_at DESC',
            (officer_id, status_filter),
        ).fetchall()
    else:
        rows = db.execute(
            'SELECT * FROM complaints WHERE assigned_officer_id = ? '
            'ORDER BY created_at DESC',
            (officer_id,),
        ).fetchall()

    return render_template(
        'officer/assigned_complaints.html',
        complaints=rows,
        status_filter=status_filter,
    )


# ---------------------------------------------------------------------------
# Complaint detail (view + update)
# ---------------------------------------------------------------------------

@officer_bp.route('/complaint/<int:id>', methods=['GET', 'POST'])
@role_required('officer')
def complaint_detail(id):
    """View and update an assigned complaint."""
    db = get_db()
    complaint = db.execute(
        'SELECT * FROM complaints WHERE id = ?', (id,)
    ).fetchone()

    if complaint is None:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('officer.complaints'))

    if complaint['assigned_officer_id'] != session['user_id']:
        flash('This complaint is not assigned to you.', 'danger')
        return redirect(url_for('officer.complaints'))

    if request.method == 'POST':
        new_status = request.form.get('new_status', '').strip()
        remarks = request.form.get('remarks', '').strip()
        current_status = complaint['status']

        # Officers can move to In Progress or Resolved
        allowed = []
        if current_status == 'Assigned':
            allowed = ['In Progress']
        elif current_status == 'In Progress':
            allowed = ['Resolved']

        if new_status not in allowed:
            flash(
                f'Invalid status transition from "{current_status}" to "{new_status}".',
                'danger',
            )
            return redirect(url_for('officer.complaint_detail', id=id))

        if new_status == 'Resolved' and not remarks:
            flash('Remarks are required when resolving a complaint.', 'danger')
            return redirect(url_for('officer.complaint_detail', id=id))

        db.execute(
            'UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP '
            'WHERE id = ?',
            (new_status, id),
        )
        db.execute(
            'INSERT INTO complaint_history '
            '(complaint_id, old_status, new_status, remarks, updated_by) '
            'VALUES (?, ?, ?, ?, ?)',
            (id, current_status, new_status, remarks or None, session['user_id']),
        )
        db.commit()

        # Notify citizen
        create_notification(
            complaint['user_id'],
            f'Your complaint {complaint["complaint_uid"]} status changed to {new_status}.',
            url_for('citizen.complaint_detail', id=id),
        )
        flash(f'Status updated to {new_status}.', 'success')
        return redirect(url_for('officer.complaint_detail', id=id))

    # GET
    history = db.execute(
        'SELECT ch.*, u.name AS updated_by_name '
        'FROM complaint_history ch LEFT JOIN users u ON ch.updated_by = u.id '
        'WHERE ch.complaint_id = ? ORDER BY ch.updated_at DESC',
        (id,),
    ).fetchall()

    return render_template(
        'officer/complaint_detail.html',
        complaint=complaint,
        history=history,
    )
