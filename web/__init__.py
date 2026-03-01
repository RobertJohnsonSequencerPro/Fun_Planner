from flask import Flask
import os

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.secret_key = os.urandom(24)

    from db.database import init_db
    init_db()

    from web.routes import bp
    app.register_blueprint(bp)

    return app
