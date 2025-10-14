from flask import Blueprint

# blueprint ahora usa template_folder local
bp = Blueprint('clients', __name__, url_prefix='/clients', template_folder='templates')

from . import routes  # noqa: E402,F401

def init_app(app):
    app.register_blueprint(bp)
