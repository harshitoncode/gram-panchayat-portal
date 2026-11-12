import os
from datetime import datetime

from flask import Flask, render_template, session

from config import Config
import db as database


def create_app():
    """Application factory."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    # Ensure the instance and upload folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Initialise database helpers
    database.init_app(app)

    # ------------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------------
    from routes.auth import auth_bp
    from routes.citizen import citizen_bp
    from routes.admin import admin_bp
    from routes.officer import officer_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(citizen_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(officer_bp)

    # ------------------------------------------------------------------
    # Home route
    # ------------------------------------------------------------------
    @app.route('/')
    def home():
        return render_template('home.html')

    # ------------------------------------------------------------------
    # Context processor – available in every template
    # ------------------------------------------------------------------
    @app.context_processor
    def inject_globals():
        ctx = {'current_year': datetime.now().year}
        if 'user_id' in session:
            db_conn = database.get_db()
            count = db_conn.execute(
                'SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0',
                (session['user_id'],),
            ).fetchone()[0]
            ctx['unread_notifications'] = count
            ctx['unread_count'] = count
        else:
            ctx['unread_notifications'] = 0
            ctx['unread_count'] = 0
        return ctx

    return app


if __name__ == '__main__':
    create_app().run(debug=True)
