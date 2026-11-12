import sqlite3
from datetime import datetime

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    """Return a database connection for the current request, creating one if needed."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Create all tables from schema.sql."""
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf-8'))


def seed_data():
    """Insert default admin and officer accounts."""
    db = get_db()

    # Admin user
    db.execute(
        'INSERT OR IGNORE INTO users (name, mobile, email, password_hash, ward, role, department) '
        'VALUES (?, ?, ?, ?, ?, ?, ?)',
        (
            'Administrator',
            'admin',
            'admin@grampanchayat.gov.in',
            generate_password_hash('admin123'),
            None,
            'admin',
            'General Administration',
        ),
    )

    # Officers – one per major department
    officers = [
        ('Ramesh Kumar', 'officer1', 'ramesh@grampanchayat.gov.in', 'Ward 1', 'officer', 'Public Works Department'),
        ('Suresh Patil', 'officer2', 'suresh@grampanchayat.gov.in', 'Ward 2', 'officer', 'Water Supply Department'),
        ('Priya Sharma', 'officer3', 'priya@grampanchayat.gov.in', 'Ward 3', 'officer', 'Health & Sanitation Department'),
    ]
    for name, mobile, email, ward, role, department in officers:
        db.execute(
            'INSERT OR IGNORE INTO users (name, mobile, email, password_hash, ward, role, department) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (name, mobile, email, generate_password_hash('officer123'), ward, role, department),
        )

    db.commit()


def generate_complaint_uid():
    """Generate a unique complaint ID in the format GP-YYYY-NNNNN."""
    db = get_db()
    year = datetime.now().year
    prefix = f'GP-{year}-'

    row = db.execute(
        "SELECT complaint_uid FROM complaints "
        "WHERE complaint_uid LIKE ? ORDER BY id DESC LIMIT 1",
        (f'{prefix}%',),
    ).fetchone()

    if row:
        last_num = int(row['complaint_uid'].split('-')[-1])
        next_num = last_num + 1
    else:
        next_num = 1

    return f'{prefix}{next_num:05d}'


@click.command('init-db')
def init_db_command():
    """Clear existing data and create fresh tables, then seed default users."""
    init_db()
    seed_data()
    click.echo('Database initialised and seeded.')


def init_app(app):
    """Register database helpers with the Flask application."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
