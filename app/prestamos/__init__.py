from flask import Blueprint

bp = Blueprint('prestamos', __name__, url_prefix='/prestamos', template_folder='templates')

from . import routes  # noqa

def init_app(app):
    app.register_blueprint(bp)
