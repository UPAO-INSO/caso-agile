from flask import Blueprint

bp = Blueprint('cuotas', __name__, url_prefix='/cuotas', template_folder='templates')

from . import routes  # noqa

def init_app(app):
    app.register_blueprint(bp)
