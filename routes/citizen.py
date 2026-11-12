import os

from flask import (
    Blueprint, current_app, flash, redirect, render_template, request,
    session, url_for,
)
from werkzeug.utils import secure_filename

from db import get_db, generate_complaint_uid
from ai_module import find_duplicates
from routes.auth import login_required
from routes import create_notification

citizen_bp = Blueprint('citizen', __name__, url_prefix='')


def _allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower()
        in current_app.config['ALLOWED_EXTENSIONS']
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@citizen_bp.route('/dashboard')
@login_required
def dashboard():
    """Citizen dashboard with complaint counts and recent complaints."""
    db = get_db()
    user_id = session['user_id']

    total = db.execute(
        'SELECT COUNT(*) FROM complaints WHERE user_id = ?', (user_id,)
    ).fetchone()[0]
    submitted = db.execute(
        'SELECT COUNT(*) FROM complaints WHERE user_id = ? AND status = ?',
        (user_id, 'Submitted'),
    ).fetchone()[0]
    in_progress = db.execute(
        'SELECT COUNT(*) FROM complaints WHERE user_id = ? AND status = ?',
        (user_id, 'In Progress'),
    ).fetchone()[0]
    resolved = db.execute(
        'SELECT COUNT(*) FROM complaints WHERE user_id = ? AND status = ?',
        (user_id, 'Resolved'),
    ).fetchone()[0]

    recent = db.execute(
        'SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC LIMIT 5',
        (user_id,),
    ).fetchall()

    notifications = db.execute(
        'SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 '
        'ORDER BY created_at DESC',
        (user_id,),
    ).fetchall()

    stats = {
        'total': total,
        'submitted': submitted,
        'in_progress': in_progress,
        'resolved': resolved,
        'pending': submitted,
    }

    return render_template(
        'citizen/dashboard.html',
        total=total,
        submitted=submitted,
        in_progress=in_progress,
        resolved=resolved,
        stats=stats,
        recent=recent,
        complaints=recent,
        notifications=notifications,
    )


# ---------------------------------------------------------------------------
# New complaint
# ---------------------------------------------------------------------------

@citizen_bp.route('/complaint/new', methods=['GET', 'POST'], endpoint='new_complaint')
@citizen_bp.route('/complaint/new', methods=['GET', 'POST'], endpoint='submit_complaint')
@login_required
def new_complaint():
    """Create a new complaint."""
    categories = current_app.config['COMPLAINT_CATEGORIES']
    wards = current_app.config['WARDS']

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        ward = request.form.get('ward', '').strip()
        location_detail = request.form.get('location_detail', '').strip() or None

        error = None
        if not title:
            error = 'Title is required.'
        elif not description:
            error = 'Description is required.'
        elif not category:
            error = 'Category is required.'
        elif not ward:
            error = 'Ward is required.'

        if error:
            flash(error, 'danger')
            return render_template(
                'citizen/submit_complaint.html',
                categories=categories, wards=wards,
            )

        # Handle optional image upload
        image_path = None
        file = request.files.get('image')
        if file and file.filename:
            if _allowed_file(file.filename):
                filename = secure_filename(file.filename)
                upload_folder = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_folder, exist_ok=True)
                file.save(os.path.join(upload_folder, filename))
                image_path = 'uploads/' + filename
            else:
                flash('Invalid file type. Allowed: png, jpg, jpeg, gif.', 'danger')
                return render_template(
                    'citizen/submit_complaint.html',
                    categories=categories, wards=wards,
                )

        db = get_db()
        complaint_uid = generate_complaint_uid()
        user_id = session['user_id']

        cursor = db.execute(
            'INSERT INTO complaints '
            '(complaint_uid, user_id, title, description, category, ward, location_detail, image_path) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (complaint_uid, user_id, title, description, category, ward,
             location_detail, image_path),
        )
        complaint_id = cursor.lastrowid

        # History entry
        db.execute(
            'INSERT INTO complaint_history (complaint_id, old_status, new_status, updated_by) '
            'VALUES (?, ?, ?, ?)',
            (complaint_id, None, 'Submitted', user_id),
        )
        db.commit()

        # --- Duplicate detection ---
        existing = db.execute(
            "SELECT id, complaint_uid, title, description, category, ward "
            "FROM complaints WHERE id != ? AND status NOT IN ('Closed', 'Rejected')",
            (complaint_id,),
        ).fetchall()
        existing_dicts = [dict(row) for row in existing]

        new_complaint_dict = {
            'title': title,
            'description': description,
            'category': category,
            'ward': ward,
        }

        matches = find_duplicates(
            new_complaint_dict,
            existing_dicts,
            threshold=current_app.config['SIMILARITY_THRESHOLD'],
            category_boost=current_app.config['CATEGORY_BOOST'],
            ward_boost=current_app.config['WARD_BOOST'],
            max_results=current_app.config['MAX_DUPLICATE_RESULTS'],
        )

        if matches:
            for match in matches:
                db.execute(
                    'INSERT INTO duplicate_relationships '
                    '(parent_complaint_id, duplicate_complaint_id, similarity_score) '
                    'VALUES (?, ?, ?)',
                    (match['complaint_id'], complaint_id, match['similarity_score']),
                )
            db.commit()

            # Notify all admins about potential duplicates
            admins = db.execute(
                "SELECT id FROM users WHERE role = 'admin'"
            ).fetchall()
            for admin in admins:
                create_notification(
                    admin['id'],
                    f'Potential duplicate detected for complaint {complaint_uid}.',
                    url_for('admin.duplicates'),
                )

        # Notification for the citizen
        create_notification(
            user_id,
            f'Your complaint {complaint_uid} has been submitted successfully.',
            url_for('citizen.complaint_detail', id=complaint_id),
        )

        flash(f'Complaint submitted successfully! Your complaint ID is {complaint_uid}.', 'success')
        return redirect(url_for('citizen.complaint_detail', id=complaint_id))

    return render_template(
        'citizen/submit_complaint.html',
        categories=categories, wards=wards,
    )


# ---------------------------------------------------------------------------
# Complaint detail
# ---------------------------------------------------------------------------

@citizen_bp.route('/complaint/<int:id>')
@login_required
def complaint_detail(id):
    """View a single complaint's full details."""
    db = get_db()
    complaint = db.execute(
        'SELECT * FROM complaints WHERE id = ?', (id,)
    ).fetchone()

    if complaint is None:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('citizen.dashboard'))

    # Access check: owner, admin, or officer
    if (complaint['user_id'] != session['user_id']
            and session.get('role') not in ('admin', 'officer')):
        flash('You do not have permission to view this complaint.', 'danger')
        return redirect(url_for('citizen.dashboard'))

    history = db.execute(
        'SELECT ch.*, u.name AS updated_by_name '
        'FROM complaint_history ch LEFT JOIN users u ON ch.updated_by = u.id '
        'WHERE ch.complaint_id = ? ORDER BY ch.updated_at DESC',
        (id,),
    ).fetchall()

    feedback = db.execute(
        'SELECT * FROM feedback WHERE complaint_id = ?', (id,)
    ).fetchone()

    parent = None
    if complaint['parent_complaint_id']:
        parent = db.execute(
            'SELECT * FROM complaints WHERE id = ?',
            (complaint['parent_complaint_id'],),
        ).fetchone()

    return render_template(
        'citizen/complaint_detail.html',
        complaint=complaint,
        history=history,
        feedback=feedback,
        parent=parent,
        parent_complaint=parent,
    )


# ---------------------------------------------------------------------------
# List complaints
# ---------------------------------------------------------------------------

@citizen_bp.route('/complaints', endpoint='complaints')
@citizen_bp.route('/complaints', endpoint='my_complaints')
@login_required
def complaints():
    """List all complaints for the current user, with optional status filter."""
    db = get_db()
    user_id = session['user_id']
    status_filter = request.args.get('status', '').strip()

    if status_filter:
        rows = db.execute(
            'SELECT * FROM complaints WHERE user_id = ? AND status = ? '
            'ORDER BY created_at DESC',
            (user_id, status_filter),
        ).fetchall()
    else:
        rows = db.execute(
            'SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,),
        ).fetchall()

    return render_template(
        'citizen/my_complaints.html',
        complaints=rows,
        status_filter=status_filter,
    )


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

@citizen_bp.route('/complaint/<int:id>/feedback', methods=['POST'])
@login_required
def submit_feedback(id):
    """Submit feedback (rating + comments) for a resolved complaint."""
    db = get_db()
    complaint = db.execute(
        'SELECT * FROM complaints WHERE id = ?', (id,)
    ).fetchone()

    if complaint is None or complaint['user_id'] != session['user_id']:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('citizen.dashboard'))

    if complaint['status'] != 'Resolved':
        flash('Feedback can only be submitted for resolved complaints.', 'warning')
        return redirect(url_for('citizen.complaint_detail', id=id))

    rating = request.form.get('rating', type=int)
    comments = request.form.get('comments', '').strip() or None

    if rating is None or rating < 1 or rating > 5:
        flash('Please provide a valid rating between 1 and 5.', 'danger')
        return redirect(url_for('citizen.complaint_detail', id=id))

    db.execute(
        'INSERT INTO feedback (complaint_id, user_id, rating, comments) '
        'VALUES (?, ?, ?, ?)',
        (id, session['user_id'], rating, comments),
    )
    db.commit()
    flash('Thank you for your feedback!', 'success')
    return redirect(url_for('citizen.complaint_detail', id=id))


# ---------------------------------------------------------------------------
# Reopen
# ---------------------------------------------------------------------------

@citizen_bp.route('/complaint/<int:id>/reopen', methods=['POST'])
@login_required
def reopen_complaint(id):
    """Reopen a resolved complaint."""
    db = get_db()
    complaint = db.execute(
        'SELECT * FROM complaints WHERE id = ?', (id,)
    ).fetchone()

    if complaint is None or complaint['user_id'] != session['user_id']:
        flash('Complaint not found.', 'danger')
        return redirect(url_for('citizen.dashboard'))

    if complaint['status'] != 'Resolved':
        flash('Only resolved complaints can be reopened.', 'warning')
        return redirect(url_for('citizen.complaint_detail', id=id))

    reason = request.form.get('reason', '').strip()

    db.execute(
        'UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        ('Reopened', id),
    )
    db.execute(
        'INSERT INTO complaint_history (complaint_id, old_status, new_status, remarks, updated_by) '
        'VALUES (?, ?, ?, ?, ?)',
        (id, 'Resolved', 'Reopened', reason, session['user_id']),
    )
    db.commit()

    # Notify admins
    admins = db.execute("SELECT id FROM users WHERE role = 'admin'").fetchall()
    for admin in admins:
        create_notification(
            admin['id'],
            f'Complaint {complaint["complaint_uid"]} has been reopened.',
            url_for('admin.complaint_detail', id=id),
        )

    flash('Complaint has been reopened.', 'success')
    return redirect(url_for('citizen.complaint_detail', id=id))


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@citizen_bp.route('/notifications')
@login_required
def notifications():
    """List all notifications for the current user."""
    db = get_db()
    rows = db.execute(
        'SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],),
    ).fetchall()
    return render_template('citizen/notifications.html', notifications=rows)


@citizen_bp.route('/notification/<int:id>/read', methods=['POST'])
@login_required
def mark_notification_read(id):
    """Mark a notification as read and redirect to its link."""
    db = get_db()
    notification = db.execute(
        'SELECT * FROM notifications WHERE id = ? AND user_id = ?',
        (id, session['user_id']),
    ).fetchone()

    if notification is None:
        flash('Notification not found.', 'danger')
        return redirect(url_for('citizen.notifications'))

    db.execute('UPDATE notifications SET is_read = 1 WHERE id = ?', (id,))
    db.commit()

    if notification['link']:
        return redirect(notification['link'])
    return redirect(url_for('citizen.notifications'))
